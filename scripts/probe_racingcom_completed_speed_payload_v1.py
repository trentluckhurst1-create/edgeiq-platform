from pathlib import Path
from datetime import datetime, timezone
import hashlib
import os
import re
from urllib.parse import parse_qs, unquote, urlparse

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
RAW_OUT = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_completed_payloads"

CALENDAR = DATA / "edgeiq_racingcom_calendar_discovery_v1.csv"
OFFICIAL_RUNS = DATA / "edgeiq_official_runs_master_v1.csv"
OUT = DATA / "edgeiq_racingcom_completed_payload_probe_v1.csv"

MAX_PAGES = int(os.environ.get("EDGEIQ_RACINGCOM_COMPLETED_MAX_PAGES", "8"))
LOOKBACK_DAYS = int(os.environ.get("EDGEIQ_RACINGCOM_COMPLETED_LOOKBACK_DAYS", "90"))

OUTPUT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "url",
    "operation_name",
    "status",
    "content_type",
    "body_saved_path",
    "contains_sectional_terms",
    "contains_speed_terms",
    "contains_runner_terms",
    "contains_last200",
    "contains_last400",
    "contains_last600",
    "contains_top_speed",
    "contains_distance_travelled",
    "contains_speed_value",
    "payload_size",
    "parse_hint",
]

RELEVANT_OPERATIONS = {
    "getRaceResults_CD",
    "getRaceEntriesForField_CD",
    "getRaceNumberList_CD",
    "getMeeting_CD",
}

VIC_TRACK_HINTS = {
    "ARARAT", "AVOCA", "BAIRNSDALE", "BALLARAT", "BENDIGO", "BENALLA", "CAULFIELD",
    "COLAC", "CRANBOURNE", "DONALD", "ECHUCA", "EDENHOPE", "FLEMINGTON", "GEELONG",
    "GREATWESTERN", "HAMILTON", "HANGINGROCK", "HEALESVILLE", "HORSHAM", "KERANG",
    "KILMORE", "KYNETON", "MOE", "MOONEEVALLEY", "MORNINGTON", "MURTOA", "NHILL",
    "PAKENHAM", "PENSHURST", "SALE", "SANDOWN", "SEYMOUR", "STARNAUD", "STAWELL",
    "SWANHILL", "TERANG", "TOWONG", "TRARALGON", "WANGARATTA", "WARRACKNABEAL",
    "WARRNAMBOOL", "WERRIBEE", "WODONGA", "YARRAVALLEY",
}


def log(message: str) -> None:
    print(f"[racingcom_completed_payload_v1] {message}")


def clean(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def has_value(value) -> bool:
    return bool(clean(value))


def norm(value) -> str:
    text = re.sub(r"\([^)]*\)", "", clean(value).upper())
    return re.sub(r"[^A-Z0-9]+", "", text)


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


def date_key(value) -> str:
    if not has_value(value):
        return ""
    parsed = pd.to_datetime(pd.Series([value]), errors="coerce", dayfirst=False).iloc[0]
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def race_no_key(value) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def is_likely_vic_track(track: str) -> bool:
    normalised = norm(track)
    return any(hint in normalised for hint in VIC_TRACK_HINTS)


def racingcom_track_slug(track: str) -> str:
    text = clean(track).lower()
    text = text.replace("&", "and")
    text = re.sub(r"[']", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def racingcom_urls(date: str, track: str, race_no: str) -> tuple[str, str]:
    slug = racingcom_track_slug(track)
    race_url = f"https://www.racing.com/form/{date}/{slug}/race/{race_no}"
    return race_url, f"{race_url}/speed-data"


def operation_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if query.get("operationName"):
        return clean(query["operationName"][0])
    graphql_query = unquote(query.get("query", [""])[0])
    match = re.search(r"\bquery\s+([A-Za-z0-9_]+)", graphql_query)
    return match.group(1) if match else ""


def official_keys(official: pd.DataFrame) -> set[tuple[str, str, str]]:
    if official.empty:
        return set()
    keys = set()
    for _, row in official.iterrows():
        date = date_key(row.get("race_date", ""))
        track = norm(row.get("track", ""))
        rno = race_no_key(row.get("race_no", ""))
        flag = clean(row.get("official_run_flag", "")).upper()
        if date and track and rno and flag in {"TRUE", "1", "YES", ""}:
            keys.add((date, track, rno))
    return keys


def candidate_pages(calendar: pd.DataFrame, official: pd.DataFrame) -> pd.DataFrame:
    today = pd.Timestamp(datetime.now().date())
    earliest = today - pd.Timedelta(days=LOOKBACK_DAYS)
    official_key_set = official_keys(official)
    rows = []

    if not calendar.empty:
        for _, row in calendar.iterrows():
            date = date_key(row.get("race_date", ""))
            track = clean(row.get("track", ""))
            rno = race_no_key(row.get("race_no", ""))
            speed_url = clean(row.get("speed_data_url", ""))
            race_url = clean(row.get("race_url", ""))
            state = clean(row.get("state", "")).upper()
            if state and state != "VIC":
                continue
            if not date or not track or not rno or not speed_url:
                continue
            dt = pd.to_datetime(date, errors="coerce")
            if pd.isna(dt) or dt >= today or dt < earliest:
                continue
            has_official = (date, norm(track), rno) in official_key_set
            rows.append({
                "race_date": date,
                "track": track,
                "race_no": rno,
                "race_url": race_url,
                "speed_data_url": speed_url,
                "has_official_results": str(bool(has_official)).upper(),
                "_priority": 0 if has_official else 1,
                "_date_sort": dt,
            })

    if not official.empty:
        official_races = official.copy()
        if "official_run_flag" in official_races.columns:
            flags = official_races["official_run_flag"].fillna("").astype(str).str.upper().str.strip()
            official_races = official_races[flags.isin(["TRUE", "1", "YES", ""])]
        available_cols = [col for col in ["race_date", "track", "race_no"] if col in official_races.columns]
        if available_cols:
            official_races = official_races.drop_duplicates(subset=available_cols)
        for _, row in official_races.iterrows():
            date = date_key(row.get("race_date", ""))
            track = clean(row.get("track", ""))
            rno = race_no_key(row.get("race_no", ""))
            if not date or not track or not rno or not is_likely_vic_track(track):
                continue
            flag_value = clean(row.get("official_run_flag", "")).upper()
            if flag_value and flag_value not in {"TRUE", "1", "YES"}:
                continue
            dt = pd.to_datetime(date, errors="coerce")
            if pd.isna(dt) or dt >= today or dt < earliest:
                continue
            race_url, speed_url = racingcom_urls(date, track, rno)
            rows.append({
                "race_date": date,
                "track": track,
                "race_no": rno,
                "race_url": race_url,
                "speed_data_url": speed_url,
                "has_official_results": "TRUE",
                "_priority": 0,
                "_date_sort": dt,
            })

    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out = out.drop_duplicates(subset=["race_date", "track", "race_no"], keep="first")
    return out.sort_values(["_priority", "_date_sort", "track", "race_no"], ascending=[True, False, True, True]).head(MAX_PAGES)


def flag(text: str, pattern: str) -> str:
    return str(bool(re.search(pattern, text or "", flags=re.IGNORECASE))).upper()


def payload_path(page_url: str, response_url: str, operation: str, content_type: str) -> Path:
    digest = hashlib.sha1(f"{page_url}|{response_url}".encode("utf-8")).hexdigest()[:18]
    prefix = operation or "response"
    ext = ".json" if "json" in content_type.lower() else ".txt"
    return RAW_OUT / f"{prefix}_{digest}{ext}"


def parse_hint(operation: str, text: str) -> str:
    hints = []
    if operation:
        hints.append(operation)
    if re.search(r"formRaceEntries", text, flags=re.IGNORECASE):
        hints.append("FORM_RACE_ENTRIES")
    if re.search(r"speedValue|topSpeed|distanceTravelled", text, flags=re.IGNORECASE):
        hints.append("SPEED_METADATA")
    if re.search(r"last200|last400|last600", text, flags=re.IGNORECASE):
        hints.append("RUNNER_SPLITS")
    return "|".join(hints) if hints else "NO_PARSE_HINT"


def probe_with_playwright(candidates: pd.DataFrame) -> pd.DataFrame:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except Exception:
        return pd.DataFrame([{
            "race_date": "",
            "track": "",
            "race_no": "",
            "url": "",
            "operation_name": "",
            "status": "",
            "content_type": "",
            "body_saved_path": "",
            "contains_sectional_terms": "FALSE",
            "contains_speed_terms": "FALSE",
            "contains_runner_terms": "FALSE",
            "contains_last200": "FALSE",
            "contains_last400": "FALSE",
            "contains_last600": "FALSE",
            "contains_top_speed": "FALSE",
            "contains_distance_travelled": "FALSE",
            "contains_speed_value": "FALSE",
            "payload_size": "0",
            "parse_hint": "PLAYWRIGHT_NOT_AVAILABLE",
        }], columns=OUTPUT_COLUMNS)

    RAW_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    pages_opened = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="EDGEiQ-Racing/1.0 completed-payload-probe",
            viewport={"width": 1280, "height": 900},
        )
        for _, candidate in candidates.iterrows():
            if pages_opened >= MAX_PAGES:
                break
            urls = [clean(candidate.get("speed_data_url", "")), clean(candidate.get("race_url", ""))]
            urls = [url for url in urls if url]
            for page_url in urls[:2]:
                if pages_opened >= MAX_PAGES:
                    break
                pages_opened += 1
                log(f"probing {page_url}")
                page = context.new_page()

                def handle_response(response):
                    resource_type = response.request.resource_type
                    if resource_type not in {"xhr", "fetch"}:
                        return
                    content_type = (response.headers or {}).get("content-type", "")
                    operation = operation_from_url(response.url)
                    relevant_operation = operation in RELEVANT_OPERATIONS
                    text = ""
                    try:
                        text = response.text()
                    except Exception:
                        return
                    relevant_terms = bool(re.search(
                        r"sectional|speed|runner|horse|distanceTravelled|topSpeed|speedValue|last200|last400|last600",
                        text,
                        flags=re.IGNORECASE,
                    ))
                    if not (relevant_operation or relevant_terms):
                        return
                    saved = payload_path(page_url, response.url, operation, content_type)
                    saved.write_text(text, encoding="utf-8")
                    rows.append({
                        "race_date": clean(candidate.get("race_date", "")),
                        "track": clean(candidate.get("track", "")),
                        "race_no": clean(candidate.get("race_no", "")),
                        "url": page_url,
                        "operation_name": operation,
                        "status": str(response.status),
                        "content_type": content_type,
                        "body_saved_path": saved.relative_to(PROJECT_ROOT).as_posix(),
                        "contains_sectional_terms": flag(text, r"sectional"),
                        "contains_speed_terms": flag(text, r"speed|topSpeed|speedValue"),
                        "contains_runner_terms": flag(text, r"runner|formRaceEntries|horseName"),
                        "contains_last200": flag(text, r"last200"),
                        "contains_last400": flag(text, r"last400"),
                        "contains_last600": flag(text, r"last600"),
                        "contains_top_speed": flag(text, r"topSpeed"),
                        "contains_distance_travelled": flag(text, r"distanceTravelled"),
                        "contains_speed_value": flag(text, r"speedValue"),
                        "payload_size": str(len(text)),
                        "parse_hint": parse_hint(operation, text),
                    })

                page.on("response", handle_response)
                try:
                    page.goto(page_url, wait_until="networkidle", timeout=45000)
                    page.wait_for_timeout(3000)
                except PlaywrightTimeoutError:
                    log(f"timeout while probing {page_url}")
                except Exception as exc:
                    log(f"warning: failed probing {page_url}: {exc}")
                finally:
                    page.close()
        context.close()
        browser.close()

    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    calendar = read_csv(CALENDAR)
    official = read_csv(OFFICIAL_RUNS)
    candidates = candidate_pages(calendar, official)
    log(f"completed candidate pages: {len(candidates)}")
    if candidates.empty:
        output = pd.DataFrame(columns=OUTPUT_COLUMNS)
    else:
        output = probe_with_playwright(candidates)
    output.to_csv(OUT, index=False, encoding="utf-8")
    operations = output["operation_name"].value_counts().to_dict() if not output.empty else {}
    log(f"completed pages probed: {len(candidates)}")
    log(f"payload rows saved: {len(output)}")
    log(f"operations captured: {operations}")
    log(f"wrote {OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
