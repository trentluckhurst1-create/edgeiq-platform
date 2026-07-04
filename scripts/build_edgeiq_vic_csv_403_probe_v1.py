from pathlib import Path
from datetime import datetime, timezone
import csv
import gzip
import json
import re
import time
import zlib
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
RAW_VIC = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC"
PROBE_CACHE = RAW_VIC / "racingcom_csv_403_probe"

REGISTRY_V2 = DATA / "edgeiq_vic_confirmed_csv_registry_v2.csv"
REGISTRY_V2_DIAG = DATA / "edgeiq_vic_confirmed_csv_registry_v2_diagnostics.csv"
COMPLETED_PROBE = DATA / "edgeiq_racingcom_completed_payload_probe_v1.csv"
NETWORK_PROBE = DATA / "edgeiq_racingcom_speed_network_probe_v1.csv"

OUT = DATA / "edgeiq_vic_csv_403_probe_v1.csv"
DIAG_OUT = DATA / "edgeiq_vic_csv_403_probe_diagnostics_v1.csv"

MAX_CANDIDATES = 70
SLEEP_SECONDS = 0.45

OUT_COLUMNS = [
    "csv_url",
    "meeting_id",
    "race_no",
    "race_date",
    "track",
    "url_pattern",
    "strategy",
    "attempted",
    "http_status",
    "fetch_status",
    "rows_parsed",
    "has_last200",
    "has_last400",
    "has_last600",
    "cached_file",
    "failure_reason",
]

DIAG_COLUMNS = ["metric", "value", "notes"]


def log(message: str) -> None:
    print(f"[vic_csv_403_probe_v1] {message}")


def clean(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-", "UNKNOWN"} else text


def has_value(value) -> bool:
    return bool(clean(value))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
    except Exception:
        return pd.DataFrame()


def csv_filename(url: str) -> str:
    return Path(clean(url).split("?", 1)[0]).name


def no_query(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def url_pattern(url: str) -> str:
    parsed = urlparse(url)
    path = re.sub(r"\d", "0", parsed.path)
    return f"{parsed.netloc}{path}"


def matching_speed_page(row: pd.Series) -> str:
    race_date = clean(row.get("race_date", ""))
    track = clean(row.get("track", "")).lower()
    race_no = clean(row.get("race_no", ""))
    if not race_date or not track or not race_no:
        return "https://www.racing.com/"
    slug = re.sub(r"[^a-z0-9]+", "-", track).strip("-")
    return f"https://www.racing.com/form/{race_date}/{slug}/race/{int(race_no)}/speed-data"


def request_strategies(row: pd.Series) -> list[dict[str, str]]:
    referer = matching_speed_page(row)
    base = clean(row.get("csv_url", ""))
    stripped = no_query(base)
    strategies = [
        {
            "name": "normal_urllib_headers",
            "url": base,
            "headers": {"User-Agent": "Python-urllib/3.11", "Accept": "*/*"},
        },
        {
            "name": "racingcom_referer",
            "url": base,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
                "Accept": "*/*",
                "Referer": referer,
            },
        },
        {
            "name": "accept_text_csv",
            "url": base,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
                "Accept": "text/csv,text/plain,*/*",
                "Referer": referer,
            },
        },
        {
            "name": "gzip_deflate_br",
            "url": base,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
                "Accept": "text/csv,text/plain,*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": referer,
            },
        },
    ]
    if stripped != base:
        strategies.append({
            "name": "no_querystring",
            "url": stripped,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
                "Accept": "text/csv,text/plain,*/*",
                "Referer": referer,
            },
        })
    return strategies


def decode_body(body: bytes, encoding: str) -> bytes:
    encoding = clean(encoding).lower()
    if "gzip" in encoding:
        return gzip.decompress(body)
    if "deflate" in encoding:
        return zlib.decompress(body)
    # urllib cannot decode br without optional brotli dependency; leave as-is and parser will reject if not text.
    return body


def fetch(strategy: dict[str, str]) -> tuple[str, bytes, str]:
    req = Request(strategy["url"], headers=strategy["headers"])
    with urlopen(req, timeout=20) as response:
        status = str(getattr(response, "status", 200))
        encoding = response.headers.get("Content-Encoding", "")
        body = decode_body(response.read(), encoding)
        return status, body, encoding


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


def parse_csv_bytes(body: bytes) -> dict[str, str]:
    result = {"rows": "0", "has_last200": "FALSE", "has_last400": "FALSE", "has_last600": "FALSE"}
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = body.decode("latin-1")
        except Exception:
            return result
    lines = text.splitlines()
    if len(lines) < 2:
        return result
    rows = list(csv.reader(lines, delimiter=";"))
    parsed = 0
    has200 = has400 = has600 = False
    for row in rows[1:]:
        if len(row) < 5 or not clean(row[0]):
            continue
        parsed += 1
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
    result["rows"] = str(parsed)
    result["has_last200"] = str(has200).upper()
    result["has_last400"] = str(has400).upper()
    result["has_last600"] = str(has600).upper()
    return result


def registry_403_candidates() -> pd.DataFrame:
    df = read_csv(REGISTRY_V2)
    if df.empty:
        return pd.DataFrame()
    mask = (df.get("url_status", "") == "REJECTED_HTTP") & (df.get("http_status", "") == "403")
    out = df[mask].copy()
    return out.head(MAX_CANDIDATES)


def probe() -> pd.DataFrame:
    PROBE_CACHE.mkdir(parents=True, exist_ok=True)
    candidates = registry_403_candidates()
    rows = []
    for _, candidate in candidates.iterrows():
        success = False
        for strategy in request_strategies(candidate):
            if success:
                break
            status = ""
            body = b""
            failure = ""
            try:
                status, body, _encoding = fetch(strategy)
                parsed = parse_csv_bytes(body) if status == "200" else {"rows": "0", "has_last200": "FALSE", "has_last400": "FALSE", "has_last600": "FALSE"}
                rows_count = int(parsed["rows"])
                cached_file = ""
                fetch_status = "HTTP_OK_NO_ROWS"
                if status == "200" and rows_count > 0 and parsed["has_last200"] == "TRUE" and parsed["has_last400"] == "TRUE" and parsed["has_last600"] == "TRUE":
                    cache_path = PROBE_CACHE / csv_filename(candidate.get("csv_url", ""))
                    cache_path.write_bytes(body)
                    cached_file = cache_path.relative_to(PROJECT_ROOT).as_posix()
                    fetch_status = "SUCCESS_PARSED_CSV"
                    success = True
                elif status != "200":
                    fetch_status = "HTTP_REJECTED"
                    failure = f"http {status}"
                rows.append({
                    "csv_url": clean(candidate.get("csv_url", "")),
                    "meeting_id": clean(candidate.get("meeting_id", "")),
                    "race_no": clean(candidate.get("race_no", "")),
                    "race_date": clean(candidate.get("race_date", "")),
                    "track": clean(candidate.get("track", "")),
                    "url_pattern": url_pattern(candidate.get("csv_url", "")),
                    "strategy": strategy["name"],
                    "attempted": "TRUE",
                    "http_status": status,
                    "fetch_status": fetch_status,
                    "rows_parsed": parsed["rows"],
                    "has_last200": parsed["has_last200"],
                    "has_last400": parsed["has_last400"],
                    "has_last600": parsed["has_last600"],
                    "cached_file": cached_file,
                    "failure_reason": failure,
                })
            except HTTPError as exc:
                rows.append({
                    "csv_url": clean(candidate.get("csv_url", "")),
                    "meeting_id": clean(candidate.get("meeting_id", "")),
                    "race_no": clean(candidate.get("race_no", "")),
                    "race_date": clean(candidate.get("race_date", "")),
                    "track": clean(candidate.get("track", "")),
                    "url_pattern": url_pattern(candidate.get("csv_url", "")),
                    "strategy": strategy["name"],
                    "attempted": "TRUE",
                    "http_status": str(exc.code),
                    "fetch_status": "HTTP_REJECTED",
                    "rows_parsed": "0",
                    "has_last200": "FALSE",
                    "has_last400": "FALSE",
                    "has_last600": "FALSE",
                    "cached_file": "",
                    "failure_reason": f"http {exc.code}",
                })
            except (URLError, TimeoutError, OSError, ValueError, zlib.error, gzip.BadGzipFile) as exc:
                rows.append({
                    "csv_url": clean(candidate.get("csv_url", "")),
                    "meeting_id": clean(candidate.get("meeting_id", "")),
                    "race_no": clean(candidate.get("race_no", "")),
                    "race_date": clean(candidate.get("race_date", "")),
                    "track": clean(candidate.get("track", "")),
                    "url_pattern": url_pattern(candidate.get("csv_url", "")),
                    "strategy": strategy["name"],
                    "attempted": "TRUE",
                    "http_status": "",
                    "fetch_status": "FETCH_ERROR",
                    "rows_parsed": "0",
                    "has_last200": "FALSE",
                    "has_last400": "FALSE",
                    "has_last600": "FALSE",
                    "cached_file": "",
                    "failure_reason": type(exc).__name__,
                })
            time.sleep(SLEEP_SECONDS)
    return pd.DataFrame(rows, columns=OUT_COLUMNS)


def diagnostics(results: pd.DataFrame) -> pd.DataFrame:
    candidates = registry_403_candidates()
    successful = results[results["fetch_status"] == "SUCCESS_PARSED_CSV"] if not results.empty else results
    parsed_csvs = int(successful["csv_url"].nunique()) if not successful.empty else 0
    total_rows = int(pd.to_numeric(successful.get("rows_parsed", pd.Series(dtype=str)), errors="coerce").fillna(0).sum()) if not successful.empty else 0
    attempts = len(results)
    by_strategy = successful["strategy"].value_counts().to_dict() if not successful.empty else {}
    failure_by_status = results[results["fetch_status"] != "SUCCESS_PARSED_CSV"]["http_status"].replace("", "FETCH_ERROR").value_counts().to_dict() if not results.empty else {}
    failure_by_pattern = results[results["fetch_status"] != "SUCCESS_PARSED_CSV"]["url_pattern"].value_counts().head(20).to_dict() if not results.empty else {}
    if parsed_csvs > 0:
        action = "PROMOTE_SUCCESSFUL_PROBE_CACHE_IN_V2_REGISTRY"
    elif int((results["http_status"] == "403").sum()) if not results.empty else 0:
        action = "DO_NOT_PROMOTE_403_URLS; FIND EXPLICIT DOWNLOAD LINKS FROM COMPLETED SPEED-DATA HTML"
    else:
        action = "REVIEW_NETWORK_ERRORS_AND_SOURCE_EVIDENCE"
    rows = [
        {"metric": "run_timestamp_utc", "value": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": "UTC run timestamp"},
        {"metric": "total_403_candidates", "value": str(len(candidates)), "notes": "Evidence-backed registry v2 candidates with HTTP 403"},
        {"metric": "attempted", "value": str(attempts), "notes": "Total strategy attempts across candidates"},
        {"metric": "successful_200", "value": str(int((results["http_status"] == "200").sum()) if not results.empty else 0), "notes": "HTTP 200 attempts"},
        {"metric": "parsed_csvs", "value": str(parsed_csvs), "notes": "Unique CSV URLs that parsed with rows and split columns"},
        {"metric": "total_rows_parsed", "value": str(total_rows), "notes": "Runner rows parsed from successful probe CSVs"},
        {"metric": "success_by_strategy", "value": json.dumps(by_strategy, sort_keys=True), "notes": "Successful parsed CSVs by request strategy"},
        {"metric": "failure_by_http_status", "value": json.dumps(failure_by_status, sort_keys=True), "notes": "Failed attempts by HTTP status/error"},
        {"metric": "failure_by_pattern", "value": json.dumps(failure_by_pattern, sort_keys=True), "notes": "Failed attempts by URL pattern"},
        {"metric": "recommended_next_action", "value": action, "notes": "Conservative next acquisition action"},
        {"metric": "inputs_audited", "value": ",".join([
            REGISTRY_V2.relative_to(PROJECT_ROOT).as_posix(),
            REGISTRY_V2_DIAG.relative_to(PROJECT_ROOT).as_posix(),
            RAW_VIC.joinpath("racingcom_speed_data").relative_to(PROJECT_ROOT).as_posix(),
            RAW_VIC.joinpath("racingcom_graphql").relative_to(PROJECT_ROOT).as_posix(),
            COMPLETED_PROBE.relative_to(PROJECT_ROOT).as_posix(),
            NETWORK_PROBE.relative_to(PROJECT_ROOT).as_posix(),
        ]), "notes": "VIC-only inputs"},
    ]
    return pd.DataFrame(rows, columns=DIAG_COLUMNS)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    results = probe()
    diag = diagnostics(results)
    results.to_csv(OUT, index=False, encoding="utf-8")
    diag.to_csv(DIAG_OUT, index=False, encoding="utf-8")
    values = {row["metric"]: row["value"] for _, row in diag.iterrows()}
    log(f"total_403_candidates: {values.get('total_403_candidates', '0')}")
    log(f"attempted: {values.get('attempted', '0')}")
    log(f"successful_200: {values.get('successful_200', '0')}")
    log(f"parsed_csvs: {values.get('parsed_csvs', '0')}")
    log(f"total_rows_parsed: {values.get('total_rows_parsed', '0')}")
    log(f"recommended_next_action: {values.get('recommended_next_action', '')}")
    log(f"wrote {OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAG_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
