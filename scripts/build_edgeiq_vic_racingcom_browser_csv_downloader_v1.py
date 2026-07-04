from __future__ import annotations

import csv
import json
import os
import re
import shutil
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - runtime dependency check
    PlaywrightTimeoutError = Exception
    sync_playwright = None

APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
RAW_VIC = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC"
DOWNLOAD_DIR = RAW_VIC / "racingcom_browser_csv_downloads"
SPEED_HTML = RAW_VIC / "racingcom_speed_data"

CALENDAR = DATA / "edgeiq_racingcom_calendar_discovery_v1.csv"
REGISTRY_V2 = DATA / "edgeiq_vic_confirmed_csv_registry_v2.csv"
PROBE_403 = DATA / "edgeiq_vic_csv_403_probe_v1.csv"
OUT = DATA / "edgeiq_vic_browser_csv_downloader_v1.csv"
DIAG_OUT = DATA / "edgeiq_vic_browser_csv_downloader_diagnostics_v1.csv"

MAX_PAGES = int(os.environ.get("EDGEIQ_VIC_BROWSER_CSV_MAX_PAGES", "20"))
HEADLESS = os.environ.get("EDGEIQ_VIC_BROWSER_HEADLESS", "false").strip().lower() in {"1", "true", "yes"}
SLEEP_SECONDS = float(os.environ.get("EDGEIQ_VIC_BROWSER_CSV_SLEEP_SECONDS", "0.75"))

OUT_COLUMNS = [
    "speed_data_url",
    "race_date",
    "track",
    "race_no",
    "meeting_id",
    "page_status",
    "csv_control_visible",
    "download_status",
    "download_filename",
    "cached_file",
    "rows_parsed",
    "has_last200",
    "has_last400",
    "has_last600",
    "parse_status",
    "failure_reason",
]
DIAG_COLUMNS = ["metric", "value", "notes"]


def log(message: str) -> None:
    print(f"[vic_browser_csv_downloader_v1] {message}")


def clean(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-", "UNKNOWN"} else text


def norm_track(value: str) -> str:
    return re.sub(r"\s+", " ", clean(value).replace("-", " ")).strip().title()


def date_key(value) -> str:
    raw = clean(value)
    if not raw:
        return ""
    parsed = pd.to_datetime(pd.Series([raw]), errors="coerce", dayfirst=not bool(re.match(r"^\d{4}-", raw))).iloc[0]
    return "" if pd.isna(parsed) else parsed.strftime("%Y-%m-%d")


def race_no_key(value) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
    except Exception:
        return pd.DataFrame()


def to_seconds(value: str):
    text = clean(value)
    if not text:
        return None
    try:
        parts = [float(part) for part in text.split(":" )]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return parts[0]
    except Exception:
        try:
            return float(text)
        except Exception:
            return None


def parse_racingcom_csv(path: Path) -> dict[str, str]:
    result = {
        "rows_parsed": "0",
        "has_last200": "FALSE",
        "has_last400": "FALSE",
        "has_last600": "FALSE",
        "parse_status": "NOT_PARSED",
    }
    if not path.exists() or path.stat().st_size <= 0:
        result["parse_status"] = "MISSING_OR_EMPTY_FILE"
        return result
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=";"))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=";"))
    except Exception as exc:
        result["parse_status"] = f"CSV_READ_FAILED:{type(exc).__name__}"
        return result
    if len(rows) < 2:
        result["parse_status"] = "CSV_EMPTY"
        return result
    runner_rows = 0
    has200 = has400 = has600 = False
    for row in rows[1:]:
        if len(row) < 5 or not clean(row[0]):
            continue
        splits = []
        idx = 2
        while idx + 2 < len(row):
            seconds = to_seconds(row[idx + 2])
            if seconds is not None:
                splits.append(seconds)
            idx += 3
        if splits:
            runner_rows += 1
        has200 = has200 or len(splits) >= 1
        has400 = has400 or len(splits) >= 2
        has600 = has600 or len(splits) >= 3
    result["rows_parsed"] = str(runner_rows)
    result["has_last200"] = str(has200).upper()
    result["has_last400"] = str(has400).upper()
    result["has_last600"] = str(has600).upper()
    result["parse_status"] = "PARSED_SECTIONAL_CSV" if runner_rows > 0 and has200 and has400 and has600 else "NO_SECTIONAL_COLUMNS"
    return result


def infer_from_speed_url(url: str) -> dict[str, str]:
    match = re.search(r"/form/(\d{4}-\d{2}-\d{2})/([^/]+)/race/(\d+)/speed-data", clean(url), re.IGNORECASE)
    if not match:
        return {"race_date": "", "track": "", "race_no": ""}
    return {"race_date": match.group(1), "track": norm_track(match.group(2)), "race_no": str(int(match.group(3)))}


def csv_filename_from_download(download, page_meta: dict[str, str]) -> str:
    suggested = clean(getattr(download, "suggested_filename", ""))
    if suggested and suggested.lower().endswith(".csv"):
        return Path(suggested).name
    date = clean(page_meta.get("race_date", "")).replace("-", "") or "unknown"
    track = re.sub(r"[^A-Za-z0-9]+", "_", clean(page_meta.get("track", "")).lower()).strip("_") or "track"
    race_no = race_no_key(page_meta.get("race_no", "")) or "0"
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    return f"browser_{date}_{track}_R{int(race_no):02d}_{stamp}.csv"


def track_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", clean(value).lower()).strip("-")


def load_candidate_pages() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    registry = read_csv(REGISTRY_V2)
    if not registry.empty:
        promoted = registry[registry.get("promote_to_fetch", pd.Series(dtype=str)).astype(str).str.upper() == "TRUE"].copy()
        for _, row in promoted.iterrows():
            date = date_key(row.get("race_date", ""))
            track = clean(row.get("track", ""))
            race_no = race_no_key(row.get("race_no", ""))
            if date and track and race_no:
                records.append({
                    "speed_data_url": f"https://www.racing.com/form/{date}/{track_slug(track)}/race/{race_no}/speed-data",
                    "race_date": date,
                    "track": track,
                    "race_no": race_no,
                    "meeting_id": clean(row.get("meeting_id", "")),
                    "_source_priority": "0",
                })
    for race_no in range(1, 13):
        records.append({
            "speed_data_url": f"https://www.racing.com/form/2026-05-01/southside-pakenham/race/{race_no}/speed-data",
            "race_date": "2026-05-01",
            "track": "Southside Pakenham",
            "race_no": str(race_no),
            "meeting_id": "",
            "_source_priority": "1",
        })
    calendar = read_csv(CALENDAR)
    if not calendar.empty and "speed_data_url" in calendar.columns:
        for _, row in calendar.iterrows():
            if clean(row.get("state", "")).upper() not in {"", "VIC"}:
                continue
            url = clean(row.get("speed_data_url", ""))
            if not url or "/speed-data" not in url:
                continue
            meta = infer_from_speed_url(url)
            records.append({
                "speed_data_url": url,
                "race_date": date_key(row.get("race_date", "")) or meta["race_date"],
                "track": clean(row.get("track", "")) or meta["track"],
                "race_no": race_no_key(row.get("race_no", "")) or meta["race_no"],
                "meeting_id": "",
            })
    probe = read_csv(PROBE_403)
    if not probe.empty:
        for _, row in probe.iterrows():
            date = date_key(row.get("race_date", ""))
            track = clean(row.get("track", ""))
            race_no = race_no_key(row.get("race_no", ""))
            if date and track and race_no:
                slug = re.sub(r"[^a-z0-9]+", "-", track.lower()).strip("-")
                records.append({
                    "speed_data_url": f"https://www.racing.com/form/{date}/{slug}/race/{race_no}/speed-data",
                    "race_date": date,
                    "track": track,
                    "race_no": race_no,
                    "meeting_id": clean(row.get("meeting_id", "")),
                })
    if SPEED_HTML.exists():
        for path in sorted(SPEED_HTML.glob("*.html")):
            meta = infer_from_speed_url(path.name.replace("_", "/"))
            file_match = re.search(r"(\d{4}-\d{2}-\d{2})_([^_]+)_R(\d+)", path.name, re.IGNORECASE)
            if file_match:
                date, file_track_slug, race_no = file_match.groups()
                slug = file_track_slug.lower().replace("_", "-")
                records.append({
                    "speed_data_url": f"https://www.racing.com/form/{date}/{slug}/race/{int(race_no)}/speed-data",
                    "race_date": date,
                    "track": norm_track(slug),
                    "race_no": str(int(race_no)),
                    "meeting_id": "",
                })
    seen = set()
    unique = []
    today = pd.Timestamp(datetime.now().date())
    for row in records:
        url = row["speed_data_url"]
        if url in seen:
            continue
        seen.add(url)
        row["_date_sort"] = date_key(row.get("race_date", ""))
        unique.append(row)
    def sort_key(row):
        parsed = pd.to_datetime(row.get("_date_sort", ""), errors="coerce")
        is_completed = 0 if pd.notna(parsed) and parsed <= today else 1
        return (int(row.get("_source_priority", "9") or 9), is_completed, "" if pd.isna(parsed) else -parsed.timestamp(), row.get("track", ""), int(race_no_key(row.get("race_no", "")) or 999))
    unique = sorted(unique, key=sort_key)
    for row in unique:
        row.pop("_date_sort", None)
        row.pop("_source_priority", None)
    return unique[:MAX_PAGES]



def accept_cookie_panel(page) -> None:
    selectors = [
        "button:has-text('Accept All Cookies')",
        "text=Accept All Cookies",
        "button:has-text('Accept')",
        "text=Accept all cookies",
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0 and loc.is_visible(timeout=1200):
                loc.click(timeout=4000)
                page.wait_for_timeout(1500)
                return
        except Exception:
            continue
def find_and_download_csv(page, meta: dict[str, str]) -> tuple[bool, str, str, str]:
    selectors = [
        "a[href*='.csv']",
        "a:has-text('CSV')",
        "button:has-text('CSV')",
        "text=CSV",
    ]
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1200)
    except Exception:
        pass
    visible = False
    last_error = ""
    for selector in selectors:
        try:
            loc = page.locator(selector).last
            if loc.count() <= 0:
                continue
            loc.scroll_into_view_if_needed(timeout=1200)
            visible = loc.is_visible(timeout=700)
            if not visible:
                continue
            with page.expect_download(timeout=5000) as download_info:
                loc.click(timeout=1500)
            download = download_info.value
            filename = csv_filename_from_download(download, meta)
            DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
            target = DOWNLOAD_DIR / filename
            download.save_as(str(target))
            return True, filename, target.as_posix(), ""
        except PlaywrightTimeoutError as exc:
            last_error = f"timeout:{selector}:{type(exc).__name__}"
        except Exception as exc:
            last_error = f"{selector}:{type(exc).__name__}"
    return visible, "", "", last_error or "CSV_CONTROL_NOT_FOUND"


def run_downloader() -> list[dict[str, str]]:
    pages = load_candidate_pages()
    rows = []
    if sync_playwright is None:
        for meta in pages:
            rows.append({**meta, "page_status": "PLAYWRIGHT_NOT_AVAILABLE", "csv_control_visible": "FALSE", "download_status": "FAILED", "download_filename": "", "cached_file": "", "rows_parsed": "0", "has_last200": "FALSE", "has_last400": "FALSE", "has_last600": "FALSE", "parse_status": "NOT_PARSED", "failure_reason": "playwright import failed"})
        return rows
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        for meta in pages:
            row = {k: clean(meta.get(k, "")) for k in ["speed_data_url", "race_date", "track", "race_no", "meeting_id"]}
            row.update({"page_status": "", "csv_control_visible": "FALSE", "download_status": "FAILED", "download_filename": "", "cached_file": "", "rows_parsed": "0", "has_last200": "FALSE", "has_last400": "FALSE", "has_last600": "FALSE", "parse_status": "NOT_PARSED", "failure_reason": ""})
            try:
                response = page.goto(row["speed_data_url"], wait_until="domcontentloaded", timeout=45000)
                row["page_status"] = str(response.status if response else "NO_RESPONSE")
                visible_or_success, filename, cached, failure = find_and_download_csv(page, row)
                row["csv_control_visible"] = str(bool(visible_or_success)).upper()
                if cached:
                    parse = parse_racingcom_csv(Path(cached))
                    row.update(parse)
                    if parse["parse_status"] == "PARSED_SECTIONAL_CSV":
                        row["download_status"] = "SUCCESS"
                        row["download_filename"] = filename
                        row["cached_file"] = Path(cached).relative_to(PROJECT_ROOT).as_posix()
                    else:
                        row["download_status"] = "REJECTED_PARSE_FAILED"
                        row["download_filename"] = filename
                        row["cached_file"] = Path(cached).relative_to(PROJECT_ROOT).as_posix()
                        row["failure_reason"] = parse["parse_status"]
                else:
                    row["failure_reason"] = failure
            except Exception as exc:
                row["page_status"] = row["page_status"] or "PAGE_FAILED"
                row["failure_reason"] = type(exc).__name__
            rows.append(row)
            time.sleep(SLEEP_SECONDS)
        context.close()
        browser.close()
    return rows


def diagnostics(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    success = [r for r in rows if r.get("download_status") == "SUCCESS"]
    parsed = [r for r in rows if r.get("parse_status") == "PARSED_SECTIONAL_CSV"]
    final_rows = 0
    final_meetings = final_races = final_tracks = "0"
    final_last200 = final_last400 = final_last600 = "0.00"
    wh_diag = DATA / "edgeiq_vic_sectional_diagnostics_v1.csv"
    if wh_diag.exists():
        diag_rows = read_csv(wh_diag)
        if not diag_rows.empty:
            values = dict(zip(diag_rows["metric"], diag_rows["value"]))
            final_rows = values.get("total_rows", "0")
            final_meetings = values.get("meetings_covered", "0")
            final_races = values.get("races_covered", "0")
            final_last200 = values.get("last200_coverage_pct", "0.00")
            final_last400 = values.get("last400_coverage_pct", "0.00")
            final_last600 = values.get("last600_coverage_pct", "0.00")
    return [
        {"metric": "run_timestamp_utc", "value": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": "UTC run timestamp"},
        {"metric": "max_pages", "value": str(MAX_PAGES), "notes": "Configured page cap"},
        {"metric": "headless", "value": str(HEADLESS).upper(), "notes": "Playwright Chromium headless mode"},
        {"metric": "pages_attempted", "value": str(len(rows)), "notes": "Speed-data pages visited"},
        {"metric": "pages_with_visible_csv_control", "value": str(sum(r.get("csv_control_visible") == "TRUE" for r in rows)), "notes": "Pages where a CSV control was visible or download succeeded"},
        {"metric": "downloads_successful", "value": str(len(success)), "notes": "Downloads accepted as parsed sectional CSVs"},
        {"metric": "downloads_failed", "value": str(len(rows) - len(success)), "notes": "Pages without accepted CSV downloads"},
        {"metric": "csvs_parsed", "value": str(len(parsed)), "notes": "Downloaded CSVs parsed with sectional fields"},
        {"metric": "rows_parsed", "value": str(sum(int(r.get("rows_parsed", "0") or 0) for r in parsed)), "notes": "Runner rows parsed from accepted downloads"},
        {"metric": "meetings_covered", "value": str(len({r.get("meeting_id") or r.get("race_date") + '|' + r.get("track") for r in success})), "notes": "Successful downloaded meeting/date-track groups"},
        {"metric": "races_covered", "value": str(len({r.get("speed_data_url") for r in success})), "notes": "Successful downloaded race pages"},
        {"metric": "tracks_covered", "value": str(len({r.get("track") for r in success if r.get("track")})), "notes": "Successful downloaded tracks"},
        {"metric": "failure_reasons", "value": json.dumps(Counter(r.get("failure_reason", "") or "none" for r in rows), sort_keys=True), "notes": "Download failures by reason"},
        {"metric": "final_warehouse_rows", "value": str(final_rows), "notes": "VIC warehouse rows after rebuild if available"},
        {"metric": "final_last200_coverage_pct", "value": str(final_last200), "notes": "VIC warehouse last200 coverage after rebuild if available"},
        {"metric": "final_last400_coverage_pct", "value": str(final_last400), "notes": "VIC warehouse last400 coverage after rebuild if available"},
        {"metric": "final_last600_coverage_pct", "value": str(final_last600), "notes": "VIC warehouse last600 coverage after rebuild if available"},
    ]


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    rows = run_downloader()
    pd.DataFrame(rows, columns=OUT_COLUMNS).to_csv(OUT, index=False, encoding="utf-8")
    diag = diagnostics(rows)
    pd.DataFrame(diag, columns=DIAG_COLUMNS).to_csv(DIAG_OUT, index=False, encoding="utf-8")
    values = {row["metric"]: row["value"] for row in diag}
    log(f"pages_attempted: {values.get('pages_attempted', '0')}")
    log(f"pages_with_visible_csv_control: {values.get('pages_with_visible_csv_control', '0')}")
    log(f"downloads_successful: {values.get('downloads_successful', '0')}")
    log(f"csvs_parsed: {values.get('csvs_parsed', '0')}")
    log(f"rows_parsed: {values.get('rows_parsed', '0')}")
    log(f"wrote {OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAG_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())






