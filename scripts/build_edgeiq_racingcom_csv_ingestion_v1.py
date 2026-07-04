from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
OUTPUTS = PROJECT_ROOT / "outputs"
RAW_CACHE = OUTPUTS / "sectionals" / "raw" / "VIC" / "racingcom_csv"

CALENDAR_DISCOVERY = DATA / "edgeiq_racingcom_calendar_discovery_v1.csv"
COMPLETED_PROBE = DATA / "edgeiq_racingcom_completed_payload_probe_v1.csv"
INGESTION_OUT = DATA / "edgeiq_racingcom_csv_ingestion_v1.csv"
DIAGNOSTICS_OUT = DATA / "edgeiq_racingcom_csv_ingestion_diagnostics_v1.csv"

MAX_FETCHES = int(os.environ.get("EDGEIQ_RACINGCOM_CSV_MAX_FETCHES", "50"))
REQUEST_SLEEP_SECONDS = float(os.environ.get("EDGEIQ_RACINGCOM_CSV_SLEEP_SECONDS", "0.5"))
CLOUDFRONT_BASE = "https://d3qmfyv6ad9vwv.cloudfront.net"

OUT_COLUMNS = [
    "horse",
    "horse_key",
    "race_date",
    "track",
    "state",
    "race_no",
    "distance",
    "barrier",
    "last200",
    "last400",
    "last600",
    "last_200",
    "last_400",
    "last_600",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "avg_speed",
    "race_time",
    "tempo_grade",
    "pace_profile",
    "sectional_source",
    "source_url",
]

DIAG_COLUMNS = ["metric", "value", "notes"]


def log(message: str) -> None:
    print(f"[racingcom_csv_v1] {message}")


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
        log(f"warning: failed to read {path.name}: {exc}")
        return pd.DataFrame()


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


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00"
    return f"{(numerator / denominator) * 100:.2f}"


def fetch_text(url: str, timeout: int = 25) -> tuple[int, str, bytes]:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            "Accept": "text/html,text/csv,application/json;q=0.9,*/*;q=0.8",
            "Referer": "https://www.racing.com/",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        body = response.read()
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = body.decode("latin-1", errors="replace")
    return int(status), text, body


def local_payload_files() -> list[Path]:
    roots = [
        OUTPUTS / "sectionals" / "raw" / "VIC" / "racingcom_network_probe",
        OUTPUTS / "sectionals" / "raw" / "VIC" / "racingcom_full_payloads",
        OUTPUTS / "sectionals" / "raw" / "VIC" / "racingcom_completed_payloads",
    ]
    files = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".txt", ".html"})
    files.extend(path for path in (OUTPUTS / "sectionals" / "raw" / "VIC").glob("*.html") if path.is_file())
    return sorted(set(files))


def csv_links_from_text(text: str, base_url: str = "") -> set[str]:
    links = set()
    for match in re.finditer(r"https?://[^\"'\s<>]+?\.csv(?:\?[^\"'\s<>]*)?", text, flags=re.IGNORECASE):
        links.add(match.group(0).replace("\\u0026", "&"))
    for match in re.finditer(r"(?:href|src)\s*=\s*[\"']([^\"']+?\.csv(?:\?[^\"']*)?)[\"']", text, flags=re.IGNORECASE):
        links.add(urljoin(base_url, match.group(1)))
    for match in re.finditer(r"cloudfront\.net/([^\"'\s<>]+?\.csv)", text, flags=re.IGNORECASE):
        links.add("https://d3qmfyv6ad9vwv.cloudfront.net/" + match.group(1).split("/")[-1])
    return links


def calendar_entries_from_payloads() -> list[dict[str, str]]:
    entries = []
    for path in local_payload_files():
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            continue
        try:
            payload = json.loads(text)
            stack = [payload]
            while stack:
                item = stack.pop()
                if isinstance(item, dict):
                    meet_code = clean(item.get("MeetCode", ""))
                    url_segment = clean(item.get("UrlSegment", ""))
                    if meet_code and url_segment:
                        entries.append({
                            "meet_code": meet_code,
                            "url_segment": url_segment,
                            "race_date": date_key(item.get("Date", "")) or date_key(url_segment[:10]),
                            "track": clean(item.get("Venue", "")) or clean(item.get("Track", "")),
                            "status": clean(item.get("FullStatus", "")) or clean(item.get("MeetStatus", "")),
                            "source": path.relative_to(PROJECT_ROOT).as_posix(),
                        })
                    stack.extend(item.values())
                elif isinstance(item, list):
                    stack.extend(item)
        except Exception:
            pass
        for match in re.finditer(r"\{[^{}]*\"MeetCode\"\s*:\s*\"?(\d+)\"?[^{}]*\"UrlSegment\"\s*:\s*\"([^\"]+)\"[^{}]*\}", text):
            blob = match.group(0)
            meet_code = match.group(1)
            url_segment = match.group(2)
            venue_match = re.search(r"\"Venue\"\s*:\s*\"([^\"]+)\"", blob)
            date_match = re.search(r"\"Date\"\s*:\s*\"([^\"]+)\"", blob)
            status_match = re.search(r"\"FullStatus\"\s*:\s*\"([^\"]+)\"", blob)
            track = venue_match.group(1) if venue_match else ""
            race_date = date_key(date_match.group(1)) if date_match else date_key(url_segment[:10])
            status = status_match.group(1) if status_match else ""
            if meet_code and url_segment:
                entries.append({
                    "meet_code": meet_code,
                    "url_segment": url_segment,
                    "race_date": race_date,
                    "track": track,
                    "status": status,
                    "source": path.relative_to(PROJECT_ROOT).as_posix(),
                })
    seen = set()
    unique = []
    for entry in entries:
        key = (entry["meet_code"], entry["url_segment"])
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return unique


def race_number_from_url(url: str) -> str:
    match = re.search(r"/race/(\d+)", clean(url), flags=re.IGNORECASE)
    return str(int(match.group(1))) if match else ""


def discover_candidates() -> pd.DataFrame:
    rows = []
    calendar = read_csv(CALENDAR_DISCOVERY)
    completed = read_csv(COMPLETED_PROBE)
    today = pd.Timestamp(datetime.now().date())

    # Confirmed public Racing.com direct CSV meeting pattern from the supplied breakthrough URL.
    for race_no in range(1, 13):
        rows.append({
            "race_date": "2026-05-01",
            "track": "Ladbrokes Geelong",
            "race_no": str(race_no),
            "speed_data_url": f"https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/{race_no}/speed-data",
            "csv_url": f"{CLOUDFRONT_BASE}/5191125_{race_no:02d}.csv",
            "discovery_method": "KNOWN_DIRECT_CSV_MEETING",
            "_priority": 0,
            "_date_sort": pd.Timestamp("2026-05-01"),
        })

    for _, row in calendar.iterrows() if not calendar.empty else []:
        speed_url = clean(row.get("speed_data_url", ""))
        race_no = race_no_key(row.get("race_no", "")) or race_number_from_url(speed_url)
        dkey = date_key(row.get("race_date", ""))
        dt = pd.to_datetime(dkey, errors="coerce")
        rows.append({
            "race_date": dkey,
            "track": clean(row.get("track", "")),
            "race_no": race_no,
            "speed_data_url": speed_url,
            "csv_url": "",
            "discovery_method": "CALENDAR_SPEED_PAGE",
            "_priority": 5 if pd.notna(dt) and dt < today else 9,
            "_date_sort": dt,
        })

    for _, row in completed.iterrows() if not completed.empty else []:
        page_url = clean(row.get("url", ""))
        race_no = race_no_key(row.get("race_no", "")) or race_number_from_url(page_url)
        dkey = date_key(row.get("race_date", ""))
        dt = pd.to_datetime(dkey, errors="coerce")
        rows.append({
            "race_date": dkey,
            "track": clean(row.get("track", "")),
            "race_no": race_no,
            "speed_data_url": page_url if page_url.endswith("/speed-data") else f"{page_url}/speed-data",
            "csv_url": "",
            "discovery_method": "COMPLETED_PROBE_SPEED_PAGE",
            "_priority": 4,
            "_date_sort": dt,
        })

    for entry in calendar_entries_from_payloads():
        dkey = date_key(entry["race_date"])
        dt = pd.to_datetime(dkey, errors="coerce")
        status = clean(entry.get("status", "")).upper()
        if pd.isna(dt):
            continue
        if dt >= today and "RESULT" not in status:
            continue
        priority = 1 if "RESULT" in status else 2
        for race_no in range(1, 13):
            rows.append({
                "race_date": dkey,
                "track": entry["track"],
                "race_no": str(race_no),
                "speed_data_url": f"https://www.racing.com/form/{entry['url_segment']}/race/{race_no}/speed-data",
                "csv_url": f"{CLOUDFRONT_BASE}/{entry['meet_code']}_{race_no:02d}.csv",
                "discovery_method": "MEETCODE_DERIVED_CLOUDFRONT",
                "_priority": priority,
                "_date_sort": dt,
            })

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["race_date", "track", "race_no", "speed_data_url", "csv_url", "discovery_method"])
    out = out.drop_duplicates(subset=["race_date", "track", "race_no", "csv_url", "speed_data_url"], keep="first")
    out = out.sort_values(["_priority", "_date_sort", "track", "race_no"], ascending=[True, False, True, True])
    return out


def discover_page_csv_links(candidates: pd.DataFrame, remaining_fetches: int) -> tuple[list[dict[str, str]], int, int]:
    rows = []
    page_fetches = 0
    page_csv_links = 0
    if remaining_fetches <= 0:
        return rows, page_fetches, page_csv_links
    seen_pages = set()
    for _, row in candidates.iterrows():
        if page_fetches >= remaining_fetches:
            break
        page_url = clean(row.get("speed_data_url", ""))
        if not page_url or page_url in seen_pages:
            continue
        seen_pages.add(page_url)
        try:
            status, text, _ = fetch_text(page_url)
            page_fetches += 1
            links = csv_links_from_text(text, page_url)
            page_csv_links += len(links)
            for link in links:
                rows.append({
                    "race_date": clean(row.get("race_date", "")),
                    "track": clean(row.get("track", "")),
                    "race_no": clean(row.get("race_no", "")),
                    "speed_data_url": page_url,
                    "csv_url": link,
                    "discovery_method": f"HTML_CSV_LINK_HTTP_{status}",
                })
            time.sleep(REQUEST_SLEEP_SECONDS)
        except Exception:
            page_fetches += 1
            time.sleep(REQUEST_SLEEP_SECONDS)
            continue
    return rows, page_fetches, page_csv_links


def cache_path_for_url(url: str) -> Path:
    name = Path(url.split("?", 1)[0]).name
    if not name.lower().endswith(".csv"):
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        name = f"racingcom_{digest}.csv"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    return RAW_CACHE / safe


def to_seconds(value: str):
    text = clean(value)
    if not text:
        return None
    parts = text.split(":")
    try:
        nums = [float(part) for part in parts]
        if len(nums) == 3:
            return nums[0] * 3600 + nums[1] * 60 + nums[2]
        if len(nums) == 2:
            return nums[0] * 60 + nums[1]
        return nums[0]
    except Exception:
        try:
            return float(text)
        except Exception:
            return None


def fmt_number(value, decimals: int = 3) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")


def parse_metadata(first_row: list[str], fallback: dict[str, str]) -> dict[str, str]:
    race_date = date_key(first_row[0] if len(first_row) > 0 else "") or clean(fallback.get("race_date", ""))
    meeting = clean(first_row[1] if len(first_row) > 1 else "")
    track = clean(fallback.get("track", "")) or meeting.split("-")[0].strip()
    race_time = clean(first_row[3] if len(first_row) > 3 else "")
    distance = ""
    if len(first_row) > 4:
        match = re.search(r"_(\d+)m_", clean(first_row[4]), flags=re.IGNORECASE)
        if match:
            distance = match.group(1)
    return {
        "race_date": race_date,
        "track": track,
        "race_no": clean(fallback.get("race_no", "")),
        "race_time": race_time,
        "distance": distance,
    }


def parse_racingcom_csv(path: Path, source_url: str, fallback: dict[str, str]) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            records = list(csv.reader(f, delimiter=";"))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as f:
            records = list(csv.reader(f, delimiter=";"))
    if not records:
        return []

    metadata = parse_metadata(records[0], fallback)
    rows = []
    for record in records[1:]:
        if len(record) < 5:
            continue
        horse = clean(record[0])
        if not horse:
            continue
        barrier = clean(record[1])
        segments = []
        idx = 2
        while idx + 2 < len(record):
            marker = clean(record[idx])
            speed = clean(record[idx + 1])
            split = clean(record[idx + 2])
            if marker:
                try:
                    marker_value = float(marker)
                except Exception:
                    marker_value = None
                try:
                    speed_value = float(speed)
                except Exception:
                    speed_value = None
                split_seconds = to_seconds(split)
                segments.append({"marker": marker_value, "speed": speed_value, "split_seconds": split_seconds})
            idx += 3

        valid_splits = [s["split_seconds"] for s in segments if s["split_seconds"] is not None]
        valid_speeds = [s["speed"] for s in segments if s["speed"] is not None]
        last200 = valid_splits[-1] if valid_splits else None
        last400 = sum(valid_splits[-2:]) if len(valid_splits) >= 2 else None
        last600 = sum(valid_splits[-3:]) if len(valid_splits) >= 3 else None
        peak_speed = max(valid_speeds) if valid_speeds else None
        avg_speed = sum(valid_speeds) / len(valid_speeds) if valid_speeds else None

        early_speed = mid_speed = late_speed = None
        if valid_speeds:
            third = max(1, len(valid_speeds) // 3)
            early = valid_speeds[:third]
            middle = valid_speeds[third:-third] if len(valid_speeds) > third * 2 else valid_speeds[third:]
            late = valid_speeds[-third:]
            early_speed = sum(early) / len(early) if early else None
            mid_speed = sum(middle) / len(middle) if middle else None
            late_speed = sum(late) / len(late) if late else None

        distance = metadata["distance"] or fmt_number(max([s["marker"] for s in segments if s["marker"] is not None], default=None), 0)
        pace_profile = "SPRINT_HOME" if late_speed and early_speed and late_speed > early_speed + 0.4 else ""
        if late_speed and early_speed and late_speed < early_speed - 0.4:
            pace_profile = "SLOW_FINISH"
        tempo_grade = ""
        if has_value(last600):
            if float(last600) <= 34:
                tempo_grade = "FAST_LAST600"
            elif float(last600) >= 37:
                tempo_grade = "SLOW_LAST600"
            else:
                tempo_grade = "STANDARD_LAST600"

        rows.append({
            "horse": horse,
            "horse_key": norm(horse),
            "race_date": metadata["race_date"],
            "track": metadata["track"],
            "state": "VIC",
            "race_no": metadata["race_no"],
            "distance": distance,
            "barrier": barrier,
            "last200": fmt_number(last200),
            "last400": fmt_number(last400),
            "last600": fmt_number(last600),
            "last_200": fmt_number(last200),
            "last_400": fmt_number(last400),
            "last_600": fmt_number(last600),
            "early_speed": fmt_number(early_speed),
            "mid_speed": fmt_number(mid_speed),
            "late_speed": fmt_number(late_speed),
            "peak_speed": fmt_number(peak_speed),
            "avg_speed": fmt_number(avg_speed),
            "race_time": metadata["race_time"],
            "tempo_grade": tempo_grade,
            "pace_profile": pace_profile,
            "sectional_source": "RACING.COM_DIRECT_CSV",
            "source_url": source_url,
        })
    return rows


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    RAW_CACHE.mkdir(parents=True, exist_ok=True)

    candidates = discover_candidates()
    direct_candidates = candidates[candidates["csv_url"].map(has_value)].copy() if not candidates.empty else pd.DataFrame()
    page_rows, page_fetches, page_csv_links = discover_page_csv_links(candidates, max(0, min(10, MAX_FETCHES // 5)))
    if page_rows:
        candidates = pd.concat([candidates, pd.DataFrame(page_rows)], ignore_index=True)
    csv_candidates = candidates[candidates["csv_url"].map(has_value)].drop_duplicates(subset=["csv_url"]).copy() if not candidates.empty else pd.DataFrame()

    output_rows = []
    fetch_attempts = fetched = failed = parsed_files = 0
    status_counts: dict[str, int] = {}
    for _, candidate in csv_candidates.iterrows():
        if fetch_attempts >= MAX_FETCHES:
            break
        url = clean(candidate.get("csv_url", ""))
        if not url.lower().endswith(".csv"):
            continue
        fetch_attempts += 1
        cache_path = cache_path_for_url(url)
        try:
            if cache_path.exists() and cache_path.stat().st_size > 0:
                status = 200
            else:
                status, _, body = fetch_text(url)
                cache_path.write_bytes(body)
                time.sleep(REQUEST_SLEEP_SECONDS)
            status_counts[str(status)] = status_counts.get(str(status), 0) + 1
            fetched += 1
            parsed = parse_racingcom_csv(cache_path, url, candidate.to_dict())
            if parsed:
                parsed_files += 1
                output_rows.extend(parsed)
        except HTTPError as exc:
            failed += 1
            status_counts[f"HTTP_{exc.code}"] = status_counts.get(f"HTTP_{exc.code}", 0) + 1
            time.sleep(REQUEST_SLEEP_SECONDS)
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            failed += 1
            key = type(exc).__name__
            status_counts[key] = status_counts.get(key, 0) + 1
            time.sleep(REQUEST_SLEEP_SECONDS)

    parsed_cache_urls = {clean(row.get("source_url", "")) for row in output_rows}
    for cache_file in RAW_CACHE.glob("*.csv"):
        source_url = f"{CLOUDFRONT_BASE}/{cache_file.name}"
        if source_url in parsed_cache_urls:
            continue
        parsed = parse_racingcom_csv(cache_file, source_url, {})
        if parsed:
            parsed_files += 1
            output_rows.extend(parsed)
            parsed_cache_urls.add(source_url)

    output = pd.DataFrame(output_rows, columns=OUT_COLUMNS)
    if not output.empty:
        output = output.drop_duplicates(subset=["horse_key", "race_date", "track", "race_no", "source_url"], keep="first")
    else:
        output = pd.DataFrame(columns=OUT_COLUMNS)
    output.to_csv(INGESTION_OUT, index=False, encoding="utf-8")

    total = len(output)
    diag_rows = [
        {"metric": "run_timestamp_utc", "value": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": "UTC run timestamp"},
        {"metric": "candidate_rows", "value": str(len(candidates)), "notes": "Candidate speed pages/direct CSV rows considered"},
        {"metric": "direct_csv_candidates", "value": str(len(direct_candidates)), "notes": "CSV URLs derived before page-link discovery"},
        {"metric": "page_fetches_for_discovery", "value": str(page_fetches), "notes": "Speed-data pages fetched to find embedded CSV links"},
        {"metric": "page_csv_links_discovered", "value": str(page_csv_links), "notes": "Explicit CSV href/cloudfront links discovered in HTML"},
        {"metric": "unique_csv_urls", "value": str(len(csv_candidates)), "notes": "Unique direct CSV URLs available to fetch"},
        {"metric": "fetch_attempts", "value": str(fetch_attempts), "notes": f"Max fetches {MAX_FETCHES}"},
        {"metric": "csvs_fetched_or_cached", "value": str(fetched), "notes": json.dumps(status_counts, sort_keys=True)},
        {"metric": "csv_fetch_failures", "value": str(failed), "notes": "HTTP/network failures"},
        {"metric": "csvs_parsed", "value": str(parsed_files), "notes": "CSV files with at least one parsed runner"},
        {"metric": "rows_parsed", "value": str(total), "notes": "Normalised runner sectional rows"},
        {"metric": "last200_coverage_pct", "value": pct(int(output["last200"].map(has_value).sum()) if total else 0, total), "notes": "Racing.com CSV rows with final 200m split"},
        {"metric": "last400_coverage_pct", "value": pct(int(output["last400"].map(has_value).sum()) if total else 0, total), "notes": "Racing.com CSV rows with final 400m aggregate"},
        {"metric": "last600_coverage_pct", "value": pct(int(output["last600"].map(has_value).sum()) if total else 0, total), "notes": "Racing.com CSV rows with final 600m aggregate"},
        {"metric": "raw_cache_dir", "value": RAW_CACHE.relative_to(PROJECT_ROOT).as_posix(), "notes": "Raw CSV cache directory"},
    ]
    diagnostics = pd.DataFrame(diag_rows, columns=DIAG_COLUMNS)
    diagnostics.to_csv(DIAGNOSTICS_OUT, index=False, encoding="utf-8")

    log(f"CSV links discovered: {len(csv_candidates)}")
    log(f"CSVs fetched or cached: {fetched}")
    log(f"rows parsed: {total}")
    log(f"last200 coverage: {diag_rows[-4]['value']}%")
    log(f"last400 coverage: {diag_rows[-3]['value']}%")
    log(f"last600 coverage: {diag_rows[-2]['value']}%")
    log(f"wrote {INGESTION_OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAGNOSTICS_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
