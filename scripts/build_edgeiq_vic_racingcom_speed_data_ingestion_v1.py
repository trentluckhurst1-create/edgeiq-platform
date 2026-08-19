from pathlib import Path
from datetime import datetime, timezone
import html
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
CONFIG = APP_ROOT / "config" / "sectional_sources.csv"
RAW_CACHE = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_speed_data"

RACE_FIELDS = DATA / "race_fields.csv"
LIVE_BOARD = DATA / "edgeiq_execution_board_live.csv"
OFFICIAL_RUNS = DATA / "edgeiq_official_runs_master_v1.csv"
DISCOVERED_LINKS = DATA / "edgeiq_sectional_discovered_links_v1.csv"

OUT = DATA / "edgeiq_vic_racingcom_speed_data_ingestion_v1.csv"
DIAG_OUT = DATA / "edgeiq_vic_racingcom_speed_data_diagnostics_v1.csv"

MAX_FETCHES = int(os.environ.get("EDGEIQ_VIC_SPEED_MAX_FETCHES", "40"))
SLEEP_SECONDS = float(os.environ.get("EDGEIQ_VIC_SPEED_SLEEP_SECONDS", "0.5"))

OUTPUT_COLUMNS = [
    "horse",
    "horse_key",
    "race_date",
    "track",
    "state",
    "race_no",
    "distance",
    "last_600",
    "last_400",
    "last_200",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "top_speed",
    "distance_travelled",
    "sectional_rank",
    "source_url",
    "source_file",
    "parse_method",
    "data_quality_grade",
    "missing_fields",
]

DIAG_COLUMNS = [
    "metric",
    "value",
    "notes",
]

TRACK_ALIASES = {
    "FLEMINGTON": "flemington",
    "CAULFIELD": "caulfield",
    "SANDOWN": "sandown",
    "SANDOWN HILLSIDE": "sandown-hillside",
    "SANDOWN-HILLSIDE": "sandown-hillside",
    "SANDOWN LAKESIDE": "sandown-lakeside",
    "SANDOWN-LAKESIDE": "sandown-lakeside",
    "BENDIGO": "bendigo",
    "BALLARAT": "ballarat",
    "GEELONG": "geelong",
    "LADBROKES GEELONG": "geelong",
    "PAKENHAM": "pakenham",
    "CRANBOURNE": "cranbourne",
    "MOONEE VALLEY": "moonee-valley",
    "MORNINGTON": "mornington",
    "WARRNAMBOOL": "warrnambool",
    "SALE": "sale",
    "SEYMOUR": "seymour",
    "KILMORE": "kilmore",
    "KYNETON": "kyneton",
    "WANGARATTA": "wangaratta",
    "WERRIBEE": "werribee",
}


def log(message: str) -> None:
    print(f"[vic_racingcom_speed_v1] {message}")


def clean(value) -> str:
    text = str(value or "").strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def has_value(value) -> bool:
    return bool(clean(value))


def norm(value) -> str:
    text = re.sub(r"\([^)]*\)", "", clean(value).upper())
    return re.sub(r"[^A-Z0-9]+", "", text)


def race_no_key(value) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def date_key(value) -> str:
    raw = clean(value)
    if not raw:
        return ""
    parsed = pd.to_datetime(pd.Series([raw]), errors="coerce", dayfirst=not bool(re.match(r"^\d{4}-", raw))).iloc[0]
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def slug_track(track: str) -> str:
    raw = clean(track)
    key = norm(raw)
    if key in {norm(k) for k in TRACK_ALIASES}:
        for alias, slug in TRACK_ALIASES.items():
            if norm(alias) == key:
                return slug
    text = raw.lower().replace("'", "")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def is_vic_track(track: str) -> bool:
    slug = slug_track(track)
    return slug in set(TRACK_ALIASES.values())


def is_vic_row(row: pd.Series) -> bool:
    state = first_existing(row, ["state", "jurisdiction"])
    if state and "VIC" in state.upper():
        return True
    return is_vic_track(first_existing(row, ["track", "meeting", "venue"]))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        log(f"missing {path.relative_to(PROJECT_ROOT)}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
        log(f"read {path.relative_to(PROJECT_ROOT)}: {len(df)} rows")
        return df
    except Exception as exc:
        log(f"warning: failed to read {path}: {exc}")
        return pd.DataFrame()


def first_existing(row: pd.Series | dict, names: list[str]) -> str:
    for name in names:
        if name in row and has_value(row.get(name, "")):
            return clean(row.get(name, ""))
    return ""


def speed_url(race_date: str, track: str, race_no: str) -> str:
    return f"https://www.racing.com/form/{race_date}/{slug_track(track)}/race/{race_no_key(race_no)}/speed-data"


def candidate_rows_from(df: pd.DataFrame, source: str, max_rows: int | None = None) -> list[dict[str, str]]:
    if df.empty:
        return []
    rows = []
    work = df.copy()
    work = work[work.apply(is_vic_row, axis=1)]
    for _, row in work.iterrows():
        race_date = date_key(first_existing(row, ["race_date", "date", "run_date", "meeting_date"]))
        track = first_existing(row, ["track", "meeting", "venue"])
        race_no = race_no_key(first_existing(row, ["race_no", "race_number", "race"]))
        if not race_date or not track or not race_no:
            continue
        rows.append({
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "source_pool": source,
            "source_url": speed_url(race_date, track, race_no),
        })
        if max_rows and len(rows) >= max_rows:
            break
    return rows


def discovered_speed_urls(df: pd.DataFrame) -> list[dict[str, str]]:
    if df.empty or "discovered_url" not in df.columns:
        return []
    rows = []
    subset = df[df["discovered_url"].astype(str).str.contains("racing.com", case=False, na=False)]
    subset = subset[subset["discovered_url"].astype(str).str.contains("speed-data", case=False, na=False)]
    for _, row in subset.iterrows():
        url = clean(row.get("discovered_url", ""))
        info = parse_speed_url(url)
        if not info:
            continue
        info["source_pool"] = "discovered_links"
        info["source_url"] = url
        rows.append(info)
    return rows


def parse_speed_url(url: str) -> dict[str, str] | None:
    match = re.search(r"/form/(\d{4}-\d{2}-\d{2})/([^/]+)/race/(\d+)/speed-data", url)
    if not match:
        return None
    return {
        "race_date": match.group(1),
        "track": match.group(2).replace("-", " ").title(),
        "race_no": match.group(3),
    }


def build_candidates() -> pd.DataFrame:
    candidates: list[dict[str, str]] = []
    candidates.extend(candidate_rows_from(read_csv(LIVE_BOARD), "live_execution_board"))
    candidates.extend(candidate_rows_from(read_csv(RACE_FIELDS), "race_fields"))
    official = read_csv(OFFICIAL_RUNS)
    if not official.empty:
        official = official[official.apply(is_vic_row, axis=1)]
        official["_date_sort"] = pd.to_datetime(official.get("race_date", ""), errors="coerce")
        official = official.sort_values("_date_sort", ascending=False).drop(columns=["_date_sort"], errors="ignore")
        candidates.extend(candidate_rows_from(official, "official_runs_recent_vic", max_rows=500))
    candidates.extend(discovered_speed_urls(read_csv(DISCOVERED_LINKS)))

    if not candidates:
        return pd.DataFrame(columns=["race_date", "track", "race_no", "source_pool", "source_url"])
    out = pd.DataFrame(candidates)
    out["_race_no_sort"] = pd.to_numeric(out["race_no"], errors="coerce").fillna(999)
    out["_date_sort"] = pd.to_datetime(out["race_date"], errors="coerce")
    priority = {
        "live_execution_board": 0,
        "race_fields": 1,
        "discovered_links": 2,
        "official_runs_recent_vic": 3,
    }
    out["_priority"] = out["source_pool"].map(priority).fillna(9)
    out = out.sort_values(["_priority", "_date_sort", "_race_no_sort"], ascending=[True, False, True])
    out = out.drop_duplicates(subset=["source_url"], keep="first")
    return out.drop(columns=["_priority", "_date_sort", "_race_no_sort"])


def cache_path_for(url: str) -> Path:
    parsed = parse_speed_url(url)
    if parsed:
        name = f"{parsed['race_date']}_{slug_track(parsed['track'])}_R{race_no_key(parsed['race_no'])}.html"
    else:
        safe = re.sub(r"[^A-Za-z0-9]+", "_", urlparse(url).path).strip("_") or "speed_data"
        name = f"{safe}.html"
    return RAW_CACHE / name


def fetch_url(url: str) -> tuple[str, str, int]:
    request = Request(
        url,
        headers={
            "User-Agent": "EDGEiQ-Racing/1.0 public-data-audit",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=25) as response:
            body = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return body.decode(charset, errors="replace"), "FETCHED", int(response.status)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return body, f"HTTP_{exc.code}", int(exc.code)
    except URLError as exc:
        return "", f"URL_ERROR_{clean(exc.reason)}", 0
    except Exception as exc:
        return "", f"ERROR_{exc.__class__.__name__}", 0


def scalar(value) -> str:
    if isinstance(value, (dict, list, tuple)):
        return ""
    return clean(value)


def value_from_dict(data: dict, names: list[str]) -> str:
    lower = {str(k).lower().replace("_", "").replace("-", ""): v for k, v in data.items()}
    for name in names:
        key = name.lower().replace("_", "").replace("-", "")
        if key in lower and has_value(lower[key]):
            return scalar(lower[key])
    return ""


def normalise_row(data: dict, context: dict[str, str], source_file: Path, method: str) -> dict[str, str] | None:
    horse = value_from_dict(data, ["horse", "horseName", "runner", "runnerName", "name", "runner_name"])
    if not horse:
        return None
    out = {
        "horse": html.unescape(horse),
        "horse_key": norm(value_from_dict(data, ["horse_key", "horseKey"]) or horse),
        "race_date": context.get("race_date", ""),
        "track": context.get("track", ""),
        "state": "VIC",
        "race_no": context.get("race_no", ""),
        "distance": value_from_dict(data, ["distance", "raceDistance", "distanceM", "distance_m"]),
        "last_600": value_from_dict(data, ["last_600", "last600", "last600m", "last_600m", "final600", "final_600"]),
        "last_400": value_from_dict(data, ["last_400", "last400", "last400m", "last_400m", "final400", "final_400"]),
        "last_200": value_from_dict(data, ["last_200", "last200", "last200m", "last_200m", "final200", "final_200"]),
        "early_speed": value_from_dict(data, ["early_speed", "earlySpeed", "earlySpeedRating"]),
        "mid_speed": value_from_dict(data, ["mid_speed", "midSpeed", "midraceSpeed"]),
        "late_speed": value_from_dict(data, ["late_speed", "lateSpeed", "closingSpeed"]),
        "peak_speed": value_from_dict(data, ["peak_speed", "peakSpeed", "speedFigure", "speedRating"]),
        "top_speed": value_from_dict(data, ["top_speed", "topSpeed", "maxSpeed"]),
        "distance_travelled": value_from_dict(data, ["distance_travelled", "distanceTravelled"]),
        "sectional_rank": value_from_dict(data, ["sectional_rank", "sectionalRank", "rank"]),
        "source_url": context.get("source_url", ""),
        "source_file": source_file.relative_to(PROJECT_ROOT).as_posix(),
        "parse_method": method,
        "data_quality_grade": "",
        "missing_fields": "",
    }
    out["data_quality_grade"] = grade_row(out)
    out["missing_fields"] = missing_fields(out)
    if out["data_quality_grade"] == "EMPTY":
        return None
    return out


def grade_row(row: dict[str, str]) -> str:
    splits = sum(1 for field in ["last_600", "last_400", "last_200"] if has_value(row.get(field, "")))
    speeds = sum(1 for field in ["early_speed", "mid_speed", "late_speed", "peak_speed", "top_speed"] if has_value(row.get(field, "")))
    if splits == 3 and speeds:
        return "ELITE"
    if splits >= 2:
        return "GOOD"
    if splits >= 1 or speeds >= 1:
        return "THIN"
    return "EMPTY"


def missing_fields(row: dict[str, str]) -> str:
    required = ["distance", "last_600", "last_400", "last_200", "peak_speed"]
    return ", ".join(field for field in required if not has_value(row.get(field, "")))


def records_from_json(obj) -> list[dict]:
    found = []
    if isinstance(obj, dict):
        keys = {str(k).lower() for k in obj.keys()}
        has_runner = bool(keys.intersection({"horse", "horsename", "runner", "runnername", "name"}))
        has_speed = any("speed" in k or "last" in k or "sectional" in k for k in keys)
        if has_runner and has_speed:
            found.append(obj)
        for value in obj.values():
            found.extend(records_from_json(value))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(records_from_json(value))
    return found


def parse_json_scripts(page: str, context: dict[str, str], source_file: Path) -> tuple[list[dict[str, str]], int]:
    rows = []
    json_blobs = []
    next_match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        page,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if next_match:
        json_blobs.append(html.unescape(next_match.group(1)).strip())
    for match in re.finditer(r"<script[^>]*>(.*?)</script>", page, flags=re.IGNORECASE | re.DOTALL):
        script = html.unescape(match.group(1)).strip()
        if "speed" not in script.lower() and "sectional" not in script.lower():
            continue
        assign = re.search(r"=\s*(\{.*\})\s*;?\s*$", script, flags=re.DOTALL)
        if script.startswith("{") or script.startswith("["):
            json_blobs.append(script)
        elif assign:
            json_blobs.append(assign.group(1))

    parsed_blobs = 0
    for blob in json_blobs:
        try:
            data = json.loads(blob)
        except Exception:
            continue
        parsed_blobs += 1
        for record in records_from_json(data):
            row = normalise_row(record, context, source_file, "embedded_json")
            if row:
                rows.append(row)
    return rows, parsed_blobs


def parse_html_tables(page: str, context: dict[str, str], source_file: Path) -> tuple[list[dict[str, str]], str]:
    try:
        tables = pd.read_html(page)
    except Exception as exc:
        return [], clean(exc)
    rows = []
    for table in tables:
        table.columns = [clean(c).lower().replace(" ", "_") for c in table.columns]
        table = table.fillna("")
        for _, record in table.iterrows():
            row = normalise_row(record.to_dict(), context, source_file, "html_table")
            if row:
                rows.append(row)
    return rows, ""


def parse_page(page: str, context: dict[str, str], source_file: Path) -> tuple[list[dict[str, str]], str, str]:
    json_rows, json_blobs = parse_json_scripts(page, context, source_file)
    table_rows, table_error = parse_html_tables(page, context, source_file)
    rows = json_rows + table_rows
    if rows:
        return rows, "PARSED", f"embedded_json_blobs={json_blobs}; table_error={table_error}"
    lower = page.lower()
    if "speed-data" in context.get("source_url", "").lower() or "speed-data" in lower or "speed data" in lower or "__next_data__" in lower:
        return [], "DYNAMIC_PAGE_NO_STATIC_DATA", f"embedded_json_blobs={json_blobs}; table_error={table_error}"
    return [], "NO_SPEED_DATA_MARKERS", f"embedded_json_blobs={json_blobs}; table_error={table_error}"


def fetch_and_parse(candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    RAW_CACHE.mkdir(parents=True, exist_ok=True)
    rows = []
    diagnostics = []
    limited = candidates.head(MAX_FETCHES).copy()
    total = len(limited)
    for position, (_, candidate) in enumerate(limited.iterrows(), start=1):
        context = {
            "race_date": clean(candidate.get("race_date", "")),
            "track": clean(candidate.get("track", "")),
            "race_no": race_no_key(candidate.get("race_no", "")),
            "source_url": clean(candidate.get("source_url", "")),
        }
        url = context["source_url"]
        html_text, fetch_status, http_status = fetch_url(url)
        cache_path = cache_path_for(url)
        if html_text:
            cache_path.write_text(html_text, encoding="utf-8")
        parsed_rows = []
        parse_status = "NOT_FETCHED"
        parse_notes = ""
        if fetch_status == "FETCHED" and html_text:
            parsed_rows, parse_status, parse_notes = parse_page(html_text, context, cache_path)
            rows.extend(parsed_rows)
        diagnostics.append({
            "metric": "FETCH",
            "value": url,
            "notes": f"source_pool={clean(candidate.get('source_pool', ''))}; http_status={http_status}; fetch_status={fetch_status}; parse_status={parse_status}; rows={len(parsed_rows)}; {parse_notes}",
        })
        log(f"{position}/{total} {fetch_status} {parse_status} rows={len(parsed_rows)} {url}")
        if position < total:
            time.sleep(SLEEP_SECONDS)
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS), pd.DataFrame(diagnostics, columns=DIAG_COLUMNS)


def add_summary_diagnostics(diag: pd.DataFrame, candidates: pd.DataFrame, parsed_rows: pd.DataFrame) -> pd.DataFrame:
    notes = "\n".join(diag["notes"].astype(str).tolist()) if not diag.empty else ""
    dynamic_failures = notes.count("parse_status=DYNAMIC_PAGE_NO_STATIC_DATA")
    fetched = notes.count("fetch_status=FETCHED")
    parsed_pages = notes.count("parse_status=PARSED")
    rows = [
        {"metric": "candidate_urls_generated", "value": str(len(candidates)), "notes": "Unique Racing.com speed-data URL candidates"},
        {"metric": "fetch_cap", "value": str(MAX_FETCHES), "notes": "EDGEIQ_VIC_SPEED_MAX_FETCHES"},
        {"metric": "pages_fetched", "value": str(fetched), "notes": "HTTP fetch_status=FETCHED"},
        {"metric": "pages_parsed", "value": str(parsed_pages), "notes": "Pages with extractable static speed data"},
        {"metric": "dynamic_failures", "value": str(dynamic_failures), "notes": "Fetched pages where data was not present in static HTML"},
        {"metric": "rows_parsed", "value": str(len(parsed_rows)), "notes": "Rows written to VIC speed-data ingestion"},
        {"metric": "latest_fetch_time", "value": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": "UTC"},
    ]
    return pd.concat([pd.DataFrame(rows, columns=DIAG_COLUMNS), diag], ignore_index=True)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    candidates = build_candidates()
    parsed_rows, fetch_diag = fetch_and_parse(candidates)
    diag = add_summary_diagnostics(fetch_diag, candidates, parsed_rows)

    parsed_rows.to_csv(OUT, index=False, encoding="utf-8")
    diag.to_csv(DIAG_OUT, index=False, encoding="utf-8")

    dynamic = int(diag.loc[diag["metric"] == "dynamic_failures", "value"].iloc[0]) if not diag.empty else 0
    fetched = int(diag.loc[diag["metric"] == "pages_fetched", "value"].iloc[0]) if not diag.empty else 0
    parsed_pages = int(diag.loc[diag["metric"] == "pages_parsed", "value"].iloc[0]) if not diag.empty else 0
    log(f"candidate URLs generated: {len(candidates)}")
    log(f"pages fetched: {fetched}")
    log(f"pages parsed: {parsed_pages}")
    log(f"dynamic failures: {dynamic}")
    log(f"rows parsed: {len(parsed_rows)}")
    log(f"wrote {OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAG_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
