from pathlib import Path
from datetime import datetime, timezone
import csv
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
RAW_VIC = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC"
RAW_CSV = RAW_VIC / "racingcom_csv"
PROBE_403_CACHE = RAW_VIC / "racingcom_csv_403_probe"
BROWSER_DOWNLOAD_CACHE = RAW_VIC / "racingcom_browser_csv_downloads"
RAW_SPEED_DATA = RAW_VIC / "racingcom_speed_data"
RAW_GRAPHQL = RAW_VIC / "racingcom_graphql"

CSV_INGESTION = DATA / "edgeiq_racingcom_csv_ingestion_v1.csv"
NETWORK_PROBE = DATA / "edgeiq_racingcom_speed_network_probe_v1.csv"
COMPLETED_PROBE = DATA / "edgeiq_racingcom_completed_payload_probe_v1.csv"
GRAPHQL_PARSER = DATA / "edgeiq_racingcom_graphql_parser_v1.csv"
CALENDAR_DISCOVERY = DATA / "edgeiq_racingcom_calendar_discovery_v1.csv"

OUT = DATA / "edgeiq_vic_confirmed_csv_registry_v2.csv"
DIAG_OUT = DATA / "edgeiq_vic_confirmed_csv_registry_v2_diagnostics.csv"

CLOUDFRONT_BASE = "https://d3qmfyv6ad9vwv.cloudfront.net"
MAX_FETCHES = int(os.environ.get("EDGEIQ_VIC_CONFIRMED_CSV_MAX_FETCHES", "100"))
SLEEP_SECONDS = float(os.environ.get("EDGEIQ_VIC_CONFIRMED_CSV_SLEEP_SECONDS", "0.35"))

REGISTRY_COLUMNS = [
    "csv_url",
    "source_discovered_from",
    "meeting_id",
    "race_no",
    "race_date",
    "track",
    "url_status",
    "http_status",
    "rows_if_cached",
    "has_last200",
    "has_last400",
    "has_last600",
    "confidence",
    "promote_to_fetch",
    "evidence_type",
    "failure_reason",
]

DIAG_COLUMNS = ["metric", "value", "notes"]


def log(message: str) -> None:
    print(f"[vic_confirmed_csv_registry_v2] {message}")


def clean(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-", "UNKNOWN"} else text


def has_value(value) -> bool:
    return bool(clean(value))


def date_key(value) -> str:
    if not has_value(value):
        return ""
    raw = clean(value)
    dayfirst = not bool(re.match(r"^\d{4}-\d{1,2}-\d{1,2}", raw))
    parsed = pd.to_datetime(pd.Series([raw]), errors="coerce", dayfirst=dayfirst).iloc[0]
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def race_no_key(value) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def track_from_slug(slug: str) -> str:
    return clean(slug).replace("-", " ").title()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
    except Exception:
        return pd.DataFrame()


def fetch_url(url: str) -> tuple[str, bytes]:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            "Accept": "text/csv,text/plain,*/*",
            "Referer": "https://www.racing.com/",
        },
    )
    with urlopen(req, timeout=25) as response:
        return str(getattr(response, "status", 200)), response.read()


def csv_filename_from_url(url: str) -> str:
    return Path(clean(url).split("?", 1)[0]).name


def cached_path(url: str) -> Path:
    primary = RAW_CSV / csv_filename_from_url(url)
    if primary.exists():
        return primary
    probe = PROBE_403_CACHE / csv_filename_from_url(url)
    return probe if probe.exists() else primary


def csv_url(meeting_id: str, race_no: str) -> str:
    return f"{CLOUDFRONT_BASE}/{clean(meeting_id)}_{int(race_no):02d}.csv"


def meeting_race_from_url(url: str) -> tuple[str, str]:
    match = re.search(r"/(\d+)_(\d{2})\.csv(?:\?|$)", clean(url), flags=re.IGNORECASE)
    if not match:
        return "", ""
    return match.group(1), str(int(match.group(2)))


def to_seconds(value: str):
    text = clean(value)
    if not text:
        return None
    try:
        parts = [float(part) for part in text.split(":")]
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


def parse_cached_csv(path: Path) -> dict[str, str]:
    result = {
        "rows_if_cached": "0",
        "has_last200": "FALSE",
        "has_last400": "FALSE",
        "has_last600": "FALSE",
        "race_date": "",
        "track": "",
        "race_no": "",
    }
    if not path.exists() or path.stat().st_size <= 0:
        return result
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=";"))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=";"))
    except Exception:
        return result
    if len(rows) < 2:
        return result
    header = rows[0]
    result["race_date"] = date_key(header[0] if len(header) > 0 else "")
    meeting = clean(header[1] if len(header) > 1 else "")
    result["track"] = meeting.split("-")[0].strip() if meeting else ""
    match = re.search(r"_(\d{2})\.csv$", path.name, flags=re.IGNORECASE)
    result["race_no"] = str(int(match.group(1))) if match else ""
    runner_rows = 0
    has200 = has400 = has600 = False
    for row in rows[1:]:
        if len(row) < 5 or not clean(row[0]):
            continue
        runner_rows += 1
        splits = []
        idx = 2
        while idx + 2 < len(row):
            seconds = to_seconds(row[idx + 2])
            if seconds is not None:
                splits.append(seconds)
            idx += 3
        has200 = has200 or len(splits) >= 1
        has400 = has400 or len(splits) >= 2
        has600 = has600 or len(splits) >= 3
    result["rows_if_cached"] = str(runner_rows)
    result["has_last200"] = str(has200).upper()
    result["has_last400"] = str(has400).upper()
    result["has_last600"] = str(has600).upper()
    return result


def source_files() -> list[Path]:
    files = []
    for root in [RAW_SPEED_DATA, RAW_GRAPHQL, RAW_CSV, PROBE_403_CACHE, BROWSER_DOWNLOAD_CACHE, RAW_VIC / "racingcom_completed_payloads", RAW_VIC / "racingcom_full_payloads", RAW_VIC / "racingcom_network_probe"]:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(set(files))


def csv_links_from_text(text: str) -> set[str]:
    links = set()
    for match in re.finditer(r"https?://[^\"'\s<>]+?\.csv(?:\?[^\"'\s<>]*)?", text, flags=re.IGNORECASE):
        links.add(match.group(0).replace("\\u0026", "&"))
    for match in re.finditer(r"cloudfront\.net/([^\"'\s<>]+?\.csv)", text, flags=re.IGNORECASE):
        links.add(f"{CLOUDFRONT_BASE}/{match.group(1).split('/')[-1]}")
    return links


def extract_payload_candidates() -> list[dict[str, str]]:
    candidates = []
    for path in source_files():
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            continue
        for url in csv_links_from_text(text):
            meeting_id, race_no = meeting_race_from_url(url)
            candidates.append({
                "csv_url": url,
                "source_discovered_from": path.relative_to(PROJECT_ROOT).as_posix(),
                "meeting_id": meeting_id,
                "race_no": race_no,
                "race_date": "",
                "track": "",
                "evidence_type": "EXPLICIT_CSV_LINK_IN_PAYLOAD",
            })
        try:
            payload = json.loads(text)
        except Exception:
            payload = None
        if payload is not None:
            stack = [payload]
            while stack:
                item = stack.pop()
                if isinstance(item, dict):
                    meet_id = clean(item.get("id", "")) or clean(item.get("MeetCode", "")) or clean(item.get("meetCode", ""))
                    venue = clean(item.get("venueName", "")) or clean(item.get("Venue", "")) or clean(item.get("venue", ""))
                    date = date_key(item.get("date", "")) or date_key(item.get("Date", ""))
                    meet_url = clean(item.get("meetUrl", "")) or clean(item.get("UrlSegment", ""))
                    status = clean(item.get("status", "")) or clean(item.get("FullStatus", "")) or clean(item.get("MeetStatus", ""))
                    if meet_id and venue and date:
                        for race_no in range(1, 13):
                            candidates.append({
                                "csv_url": csv_url(meet_id, str(race_no)),
                                "source_discovered_from": path.relative_to(PROJECT_ROOT).as_posix(),
                                "meeting_id": meet_id,
                                "race_no": str(race_no),
                                "race_date": date,
                                "track": track_from_slug(venue),
                                "evidence_type": f"PAYLOAD_MEET_ID_{status or 'UNKNOWN'}",
                            })
                    stack.extend(item.values())
                elif isinstance(item, list):
                    stack.extend(item)
    return candidates


def extract_probe_candidates() -> list[dict[str, str]]:
    records = []
    for source_path in [NETWORK_PROBE, COMPLETED_PROBE]:
        df = read_csv(source_path)
        if df.empty:
            continue
        for _, row in df.iterrows():
            page_url = clean(row.get("page_url", "")) or clean(row.get("url", ""))
            response_url = clean(row.get("response_url", ""))
            text = " ".join([clean(row.get("short_body_sample", "")), response_url])
            for url in csv_links_from_text(text):
                meeting_id, race_no = meeting_race_from_url(url)
                records.append({
                    "csv_url": url,
                    "source_discovered_from": source_path.relative_to(PROJECT_ROOT).as_posix(),
                    "meeting_id": meeting_id,
                    "race_no": race_no,
                    "race_date": "",
                    "track": "",
                    "evidence_type": "PROBE_EXPLICIT_CSV_LINK",
                })
            race_match = re.search(r"/form/(\d{4}-\d{2}-\d{2})/([^/]+)/race/(\d+)", page_url, flags=re.IGNORECASE)
            if not race_match:
                continue
            date = race_match.group(1)
            track = track_from_slug(race_match.group(2))
            race_no = race_match.group(3)
            meet_ids = set()
            if response_url:
                parsed = urlparse(response_url)
                query = parse_qs(parsed.query)
                variables = query.get("variables", [""])[0]
                try:
                    payload = json.loads(unquote(variables))
                    if has_value(payload.get("meetCode", "")):
                        meet_ids.add(clean(payload.get("meetCode", "")))
                except Exception:
                    pass
            for meet_id in re.findall(r'"id"\s*:\s*"?(\d{6,})"?', clean(row.get("short_body_sample", ""))):
                meet_ids.add(meet_id)
            for meet_id in sorted(meet_ids):
                records.append({
                    "csv_url": csv_url(meet_id, race_no),
                    "source_discovered_from": source_path.relative_to(PROJECT_ROOT).as_posix(),
                    "meeting_id": meet_id,
                    "race_no": race_no_key(race_no),
                    "race_date": date,
                    "track": track,
                    "evidence_type": "PROBE_MEET_ID_AND_RACE_PAGE",
                })
    return records


def extract_ingestion_candidates() -> list[dict[str, str]]:
    df = read_csv(CSV_INGESTION)
    if df.empty or "source_url" not in df.columns:
        return []
    records = []
    for url, group in df.groupby("source_url", dropna=False):
        url = clean(url)
        if not url:
            continue
        meeting_id, race_no = meeting_race_from_url(url)
        records.append({
            "csv_url": url,
            "source_discovered_from": CSV_INGESTION.relative_to(PROJECT_ROOT).as_posix(),
            "meeting_id": meeting_id,
            "race_no": race_no or race_no_key(group["race_no"].iloc[0] if "race_no" in group else ""),
            "race_date": date_key(group["race_date"].iloc[0] if "race_date" in group else ""),
            "track": clean(group["track"].iloc[0] if "track" in group else ""),
            "evidence_type": "PRIOR_PARSED_INGESTION",
        })
    return records


def extract_probe_cache_candidates() -> list[dict[str, str]]:
    if not PROBE_403_CACHE.exists():
        return []
    records = []
    for path in sorted(PROBE_403_CACHE.glob("*.csv")):
        meeting_id, race_no = meeting_race_from_url(f"{CLOUDFRONT_BASE}/{path.name}")
        parsed = parse_cached_csv(path)
        records.append({
            "csv_url": f"{CLOUDFRONT_BASE}/{path.name}",
            "source_discovered_from": path.relative_to(PROJECT_ROOT).as_posix(),
            "meeting_id": meeting_id,
            "race_no": parsed.get("race_no", "") or race_no,
            "race_date": parsed.get("race_date", ""),
            "track": parsed.get("track", ""),
            "evidence_type": "SUCCESSFUL_403_PROBE_CACHE",
        })
    return records



def extract_browser_download_cache_candidates() -> list[dict[str, str]]:
    if not BROWSER_DOWNLOAD_CACHE.exists():
        return []
    records = []
    for path in sorted(BROWSER_DOWNLOAD_CACHE.glob("*.csv")):
        meeting_id, race_no = meeting_race_from_url(f"{CLOUDFRONT_BASE}/{path.name}")
        parsed = parse_cached_csv(path)
        rows = int(parsed.get("rows_if_cached", "0") or 0)
        if rows <= 0:
            continue
        records.append({
            "csv_url": f"{CLOUDFRONT_BASE}/{path.name}",
            "source_discovered_from": path.relative_to(PROJECT_ROOT).as_posix(),
            "meeting_id": meeting_id,
            "race_no": parsed.get("race_no", "") or race_no,
            "race_date": parsed.get("race_date", ""),
            "track": parsed.get("track", ""),
            "evidence_type": "SUCCESSFUL_BROWSER_DOWNLOAD_CACHE",
        })
    return records

def extract_calendar_candidates() -> list[dict[str, str]]:
    # Calendar rows alone are not enough to promote. Keep these only if another payload confirms same meet/race.
    _ = read_csv(CALENDAR_DISCOVERY)
    return []


def build_candidate_frame() -> pd.DataFrame:
    records = []
    records.extend(extract_probe_cache_candidates())
    records.extend(extract_browser_download_cache_candidates())
    records.extend(extract_ingestion_candidates())
    records.extend(extract_payload_candidates())
    records.extend(extract_probe_candidates())
    records.extend(extract_calendar_candidates())
    if not records:
        return pd.DataFrame(columns=REGISTRY_COLUMNS)
    df = pd.DataFrame(records).fillna("")
    df = df[df["csv_url"].astype(str).str.contains(r"\.csv", case=False, na=False)].copy()
    df["_is_known_good"] = df["evidence_type"].eq("PRIOR_PARSED_INGESTION")
    df["_is_explicit"] = df["evidence_type"].astype(str).str.contains("EXPLICIT", case=False, na=False)
    priority = {
        "SUCCESSFUL_BROWSER_DOWNLOAD_CACHE": 0,
        "SUCCESSFUL_403_PROBE_CACHE": 0,
        "PRIOR_PARSED_INGESTION": 0,
        "EXPLICIT_CSV_LINK_IN_PAYLOAD": 1,
        "PROBE_EXPLICIT_CSV_LINK": 1,
        "PROBE_MEET_ID_AND_RACE_PAGE": 2,
    }
    df["_priority"] = df["evidence_type"].map(priority).fillna(3)
    df = df.sort_values(["_priority", "race_date", "track", "race_no"], ascending=[True, False, True, True])
    return df.drop_duplicates(subset=["csv_url"], keep="first")


def evaluate_candidate(row: pd.Series, fetch_budget: dict[str, int]) -> dict[str, str]:
    url = clean(row.get("csv_url", ""))
    path = cached_path(url)
    meeting_id, race_no = meeting_race_from_url(url)
    record = {
        "csv_url": url,
        "source_discovered_from": clean(row.get("source_discovered_from", "")),
        "meeting_id": clean(row.get("meeting_id", "")) or meeting_id,
        "race_no": race_no_key(row.get("race_no", "")) or race_no,
        "race_date": date_key(row.get("race_date", "")),
        "track": clean(row.get("track", "")),
        "url_status": "NOT_FETCHED",
        "http_status": "",
        "rows_if_cached": "0",
        "has_last200": "FALSE",
        "has_last400": "FALSE",
        "has_last600": "FALSE",
        "confidence": "LOW",
        "promote_to_fetch": "FALSE",
        "evidence_type": clean(row.get("evidence_type", "")),
        "failure_reason": "",
    }

    if path.exists() and path.stat().st_size > 0:
        parsed = parse_cached_csv(path)
        record.update({k: parsed[k] for k in ["rows_if_cached", "has_last200", "has_last400", "has_last600"]})
        record["race_date"] = record["race_date"] or parsed.get("race_date", "")
        record["track"] = record["track"] or parsed.get("track", "")
        record["race_no"] = record["race_no"] or parsed.get("race_no", "")
        if int(record["rows_if_cached"] or 0) > 0:
            record["url_status"] = "CONFIRMED_CACHED"
            record["http_status"] = "200"
            record["confidence"] = "HIGH"
            record["promote_to_fetch"] = "TRUE"
            return record

    evidence = record["evidence_type"]
    should_fetch = (
        evidence in {"EXPLICIT_CSV_LINK_IN_PAYLOAD", "PROBE_EXPLICIT_CSV_LINK", "PROBE_MEET_ID_AND_RACE_PAGE", "PRIOR_PARSED_INGESTION", "SUCCESSFUL_BROWSER_DOWNLOAD_CACHE"}
        and fetch_budget["used"] < MAX_FETCHES
    )
    if not should_fetch:
        record["url_status"] = "REJECTED_NOT_STRONG_ENOUGH"
        record["failure_reason"] = "not cached and not eligible under conservative evidence/fetch cap"
        return record

    try:
        status, body = fetch_url(url)
        fetch_budget["used"] += 1
        record["http_status"] = status
        if status == "200" and body:
            RAW_CSV.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            parsed = parse_cached_csv(path)
            record.update({k: parsed[k] for k in ["rows_if_cached", "has_last200", "has_last400", "has_last600"]})
            record["race_date"] = record["race_date"] or parsed.get("race_date", "")
            record["track"] = record["track"] or parsed.get("track", "")
            record["race_no"] = record["race_no"] or parsed.get("race_no", "")
            if int(record["rows_if_cached"] or 0) > 0:
                record["url_status"] = "CONFIRMED_FETCHED"
                record["confidence"] = "HIGH"
                record["promote_to_fetch"] = "TRUE"
            else:
                record["url_status"] = "REJECTED_EMPTY_CSV"
                record["failure_reason"] = "fetched but no runner rows parsed"
        else:
            record["url_status"] = "REJECTED_HTTP"
            record["failure_reason"] = f"http {status}"
        time.sleep(SLEEP_SECONDS)
    except HTTPError as exc:
        fetch_budget["used"] += 1
        record["http_status"] = str(exc.code)
        record["url_status"] = "REJECTED_HTTP"
        record["failure_reason"] = f"http {exc.code}"
        time.sleep(SLEEP_SECONDS)
    except (URLError, TimeoutError, OSError) as exc:
        fetch_budget["used"] += 1
        record["url_status"] = "REJECTED_FETCH_ERROR"
        record["failure_reason"] = type(exc).__name__
        time.sleep(SLEEP_SECONDS)
    return record


def build_registry() -> tuple[pd.DataFrame, int]:
    candidates = build_candidate_frame()
    rows = []
    budget = {"used": 0}
    for _, row in candidates.iterrows():
        rows.append(evaluate_candidate(row, budget))
    registry = pd.DataFrame(rows, columns=REGISTRY_COLUMNS) if rows else pd.DataFrame(columns=REGISTRY_COLUMNS)
    if not registry.empty:
        priority = {"CONFIRMED_CACHED": 0, "CONFIRMED_FETCHED": 1}
        registry["_priority"] = registry["url_status"].map(priority).fillna(9)
        registry["_rows"] = pd.to_numeric(registry["rows_if_cached"], errors="coerce").fillna(0)
        registry = registry.sort_values(["_priority", "_rows", "csv_url"], ascending=[True, False, True])
        registry = registry.drop(columns=["_priority", "_rows"])
    return registry, len(candidates)


def diagnostics(registry: pd.DataFrame, candidates: int) -> pd.DataFrame:
    promoted = registry[registry["promote_to_fetch"] == "TRUE"] if not registry.empty else registry
    rejected = registry[registry["promote_to_fetch"] != "TRUE"] if not registry.empty else registry
    cached = promoted[promoted["url_status"].isin(["CONFIRMED_CACHED", "CONFIRMED_FETCHED"])] if not promoted.empty else promoted
    rows_available = int(pd.to_numeric(promoted.get("rows_if_cached", pd.Series(dtype=str)), errors="coerce").fillna(0).sum()) if not promoted.empty else 0
    coverage = {}
    if not promoted.empty:
        grouped = promoted.groupby(["race_date", "track", "meeting_id", "race_no"], dropna=False).size().reset_index(name="urls")
        coverage = {
            "|".join([clean(row["race_date"]), clean(row["track"]), clean(row["meeting_id"]), f"R{clean(row['race_no'])}"]): int(row["urls"])
            for _, row in grouped.iterrows()
        }
    failure_counts = rejected["failure_reason"].replace("", "not promoted").value_counts().to_dict() if not rejected.empty else {}
    status_counts = registry["url_status"].value_counts().to_dict() if not registry.empty else {}
    rows = [
        {"metric": "run_timestamp_utc", "value": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": "UTC run timestamp"},
        {"metric": "csv_candidates_found", "value": str(candidates), "notes": "Unique CSV candidates from explicit links, cached records, and meet-code/race payload evidence"},
        {"metric": "csvs_fetched", "value": str(int((registry["url_status"] == "CONFIRMED_FETCHED").sum()) if not registry.empty else 0), "notes": "Candidates newly fetched and parsed successfully"},
        {"metric": "csvs_cached", "value": str(len(cached)), "notes": "Promoted confirmed CSVs available in local cache"},
        {"metric": "promoted_urls", "value": str(len(promoted)), "notes": "Confirmed URLs promoted to warehouse"},
        {"metric": "rejected_urls", "value": str(len(rejected)), "notes": "Candidates rejected due HTTP/error/no rows/low confidence"},
        {"metric": "rows_available", "value": str(rows_available), "notes": "Runner rows available from promoted URLs"},
        {"metric": "status_counts", "value": json.dumps(status_counts, sort_keys=True), "notes": "Registry URL status distribution"},
        {"metric": "failure_counts", "value": json.dumps(failure_counts, sort_keys=True), "notes": "Rejected URL failure reasons"},
        {"metric": "last200_url_coverage_pct", "value": f"{(promoted['has_last200'].eq('TRUE').mean() * 100):.2f}" if not promoted.empty else "0.00", "notes": "Promoted URLs with last200 data"},
        {"metric": "last400_url_coverage_pct", "value": f"{(promoted['has_last400'].eq('TRUE').mean() * 100):.2f}" if not promoted.empty else "0.00", "notes": "Promoted URLs with last400 data"},
        {"metric": "last600_url_coverage_pct", "value": f"{(promoted['has_last600'].eq('TRUE').mean() * 100):.2f}" if not promoted.empty else "0.00", "notes": "Promoted URLs with last600 data"},
        {"metric": "coverage_by_meeting_race", "value": json.dumps(coverage, sort_keys=True), "notes": "Promoted coverage by date/track/meeting/race"},
    ]
    return pd.DataFrame(rows, columns=DIAG_COLUMNS)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    registry, candidate_count = build_registry()
    diag = diagnostics(registry, candidate_count)
    registry.to_csv(OUT, index=False, encoding="utf-8")
    diag.to_csv(DIAG_OUT, index=False, encoding="utf-8")
    values = {row["metric"]: row["value"] for _, row in diag.iterrows()}
    log(f"CSV candidates found: {values.get('csv_candidates_found', '0')}")
    log(f"CSVs fetched: {values.get('csvs_fetched', '0')}")
    log(f"CSVs cached: {values.get('csvs_cached', '0')}")
    log(f"promoted URLs: {values.get('promoted_urls', '0')}")
    log(f"rejected URLs: {values.get('rejected_urls', '0')}")
    log(f"rows available: {values.get('rows_available', '0')}")
    log(f"wrote {OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAG_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


