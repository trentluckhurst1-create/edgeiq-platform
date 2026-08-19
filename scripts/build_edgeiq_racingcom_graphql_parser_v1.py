from pathlib import Path
from datetime import datetime, timezone
import hashlib
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
RAW_CACHE = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_graphql"
LEGACY_PROBE_PAYLOADS = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_network_probe"
FULL_PAYLOADS = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_full_payloads"
COMPLETED_PAYLOADS = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_completed_payloads"

NETWORK_PROBE = DATA / "edgeiq_racingcom_speed_network_probe_v1.csv"
VIC_DIAGNOSTICS = DATA / "edgeiq_vic_racingcom_speed_data_diagnostics_v1.csv"
RACE_FIELDS = DATA / "race_fields.csv"
OFFICIAL_RUNS = DATA / "edgeiq_official_runs_master_v1.csv"

OUT = DATA / "edgeiq_racingcom_graphql_parser_v1.csv"
DIAG_OUT = DATA / "edgeiq_racingcom_graphql_diagnostics_v1.csv"

MAX_FETCHES = int(os.environ.get("EDGEIQ_RACINGCOM_GRAPHQL_MAX_FETCHES", "20"))
SLEEP_SECONDS = float(os.environ.get("EDGEIQ_RACINGCOM_GRAPHQL_SLEEP_SECONDS", "0.5"))

OUTPUT_COLUMNS = [
    "horse_key",
    "horse",
    "race_date",
    "track",
    "state",
    "race_no",
    "distance",
    "has_sectionals",
    "has_speed_map",
    "speed_value",
    "top_speed",
    "distance_travelled",
    "race_time",
    "runner_fields_json",
    "sectional_fields_json",
    "source_operation",
    "source_url",
    "parse_status",
    "missing_fields",
]

DIAG_COLUMNS = ["metric", "value", "notes"]

ALLOWED_OPERATIONS = {
    "getRaceNumberList_CD",
    "getRaceEntriesForField_CD",
    "getRaceResults_CD",
    "getMeeting_CD",
}


def log(message: str) -> None:
    print(f"[racingcom_graphql_v1] {message}")


def clean(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def has_value(value) -> bool:
    return bool(clean(value))


def norm(value) -> str:
    text = re.sub(r"\([^)]*\)", "", clean(value).upper())
    return re.sub(r"[^A-Z0-9]+", "", text)


def compact_json(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    except Exception:
        return "{}"


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


def operation_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if query.get("operationName"):
        return clean(query["operationName"][0])
    graphql_query = unquote(query.get("query", [""])[0])
    match = re.search(r"\bquery\s+([A-Za-z0-9_]+)", graphql_query)
    return match.group(1) if match else ""


def variables_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return unquote(query.get("variables", ["{}"])[0])


def candidate_urls() -> pd.DataFrame:
    probe = read_csv(NETWORK_PROBE)
    rows = []
    if not probe.empty and "response_url" in probe.columns:
        for _, row in probe.iterrows():
            url = clean(row.get("response_url", ""))
            if "graphql.rmdprod.racing.com" not in url:
                continue
            op = operation_from_url(url)
            if op not in ALLOWED_OPERATIONS:
                continue
            rows.append({
                "source_url": url,
                "source_operation": op,
                "variables": variables_from_url(url),
                "raw_sample_file": clean(row.get("raw_sample_file", "")),
                "source": "network_probe",
            })
    if not rows:
        return pd.DataFrame(columns=["source_url", "source_operation", "variables", "raw_sample_file", "source"])
    out = pd.DataFrame(rows).drop_duplicates(subset=["source_url"])
    priority = {
        "getRaceNumberList_CD": 0,
        "getRaceEntriesForField_CD": 1,
        "getRaceResults_CD": 2,
        "getMeeting_CD": 3,
    }
    out["_priority"] = out["source_operation"].map(priority).fillna(9)
    return out.sort_values(["_priority", "source_url"]).drop(columns=["_priority"])


def raw_path_for(url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:18]
    operation = operation_from_url(url) or "graphql"
    return RAW_CACHE / f"{operation}_{digest}.json"


def fetch_json(url: str) -> tuple[dict | list | None, str, int, Path | None]:
    RAW_CACHE.mkdir(parents=True, exist_ok=True)
    request = Request(
        url,
        headers={
            "User-Agent": "EDGEiQ-Racing/1.0 graphql-parser",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.racing.com/",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
            raw_path = raw_path_for(url)
            raw_path.write_text(body, encoding="utf-8")
            return json.loads(body), "FETCHED", int(response.status), raw_path
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raw_path = raw_path_for(url)
        raw_path.write_text(body, encoding="utf-8")
        return None, f"HTTP_{exc.code}", int(exc.code), raw_path
    except URLError as exc:
        return None, f"URL_ERROR_{clean(exc.reason)}", 0, None
    except Exception as exc:
        return None, f"ERROR_{exc.__class__.__name__}", 0, None


def read_local_sample(raw_sample_file: str) -> tuple[dict | list | None, str, Path | None]:
    if not has_value(raw_sample_file):
        return None, "NO_LOCAL_SAMPLE", None
    path = Path(raw_sample_file)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        return None, "LOCAL_SAMPLE_MISSING", path
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return json.loads(text), "LOCAL_PROBE_SAMPLE", path
    except Exception:
        return None, "LOCAL_SAMPLE_UNPARSEABLE", path


def read_json_file(path: Path) -> tuple[dict | list | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace")), "READ"
    except Exception:
        return None, "UNPARSEABLE"


def nested_get(data, path: list[str], default=None):
    cur = data
    for item in path:
        if isinstance(cur, dict):
            cur = cur.get(item, default)
        else:
            return default
    return cur


def race_no(value) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def date_from_text(*values) -> str:
    for value in values:
        match = re.search(r"\d{4}-\d{2}-\d{2}", clean(value))
        if match:
            return match.group(0)
    return ""


def race_context_from_race(race: dict, fallback: dict | None = None) -> dict:
    fallback = fallback or {}
    meet = race.get("meet") if isinstance(race.get("meet"), dict) else {}
    venue = race.get("venue") if isinstance(race.get("venue"), dict) else {}
    race_date = clean(fallback.get("race_date") or meet.get("date") or race.get("date") or "")
    if not race_date:
        race_date = date_from_text(meet.get("meetUrlSegment"), meet.get("meetUrl"), race.get("meetUrl"), race.get("url"))
    return {
        "race_date": race_date,
        "track": clean(fallback.get("track") or meet.get("venue") or venue.get("venueName") or race.get("location") or race.get("venue") or ""),
        "state": clean(fallback.get("state") or venue.get("state") or race.get("venueState") or meet.get("state") or "VIC"),
        "race_no": race_no(fallback.get("race_no") or race.get("raceNumber") or ""),
        "distance": clean(fallback.get("distance") or race.get("distance") or ""),
        "race_time": clean(fallback.get("race_time") or race.get("time") or race.get("raceTime") or ""),
        "has_sectionals": clean(fallback.get("has_sectionals") or race.get("hasSectionals") or ""),
        "has_speed_map": clean(fallback.get("has_speed_map") or race.get("hasSpeedMap") or ""),
    }


def race_timing_fields(race: dict) -> dict:
    names = [
        "toEightHundredMetresSeconds",
        "standardTimeTo800Difference",
        "eightHundredToFourHundredMetresSeconds",
        "standardTime800To400Difference",
        "fourHundredToFinishMetresSeconds",
        "standardTime400ToFinishDifference",
        "raceTime",
        "standardTimeDifference",
        "standardTimeId",
        "winningTime",
        "trackRecordTime",
    ]
    return {name: race.get(name) for name in names if race.get(name) not in [None, ""]}


def runner_fields(entry: dict) -> dict:
    names = [
        "id",
        "meetCode",
        "raceCode",
        "raceNumber",
        "raceEntryNumber",
        "barrierNumber",
        "liveBarrierNumber",
        "jockeyName",
        "jockeyCode",
        "trainerName",
        "trainerCode",
        "horseName",
        "horseCode",
        "horseCountry",
        "weight",
        "position",
        "finish",
        "finishAbv",
        "margin",
        "winningTime",
        "startingPrice",
        "speedValue",
        "topSpeed",
        "distanceTravelled",
        "trackDistanceStats",
        "trackStats",
        "distanceStats",
        "jockeyStats",
        "atThisClassStats",
        "comment",
        "commentShort",
        "commentStewards",
    ]
    return {name: entry.get(name) for name in names if entry.get(name) not in [None, ""]}


def walk_relevant_fields(value, prefix: str = "") -> dict:
    found = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            if any(term in lowered for term in [
                "sectional",
                "last200",
                "last400",
                "last600",
                "speed",
                "topspeed",
                "distancetravelled",
                "split",
                "time",
            ]) and child not in [None, ""]:
                found[path] = child
            if isinstance(child, (dict, list)):
                found.update(walk_relevant_fields(child, path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            if isinstance(child, (dict, list)):
                found.update(walk_relevant_fields(child, f"{prefix}[{idx}]"))
    return found


def sectional_like_fields(entry: dict, race: dict | None = None) -> dict:
    found = {}
    for source in [race or {}, entry]:
        found.update(walk_relevant_fields(source))
    return found


def first_nested(entry: dict, names: list[str]) -> str:
    for name in names:
        if has_value(entry.get(name, "")):
            return clean(entry.get(name, ""))
    for value in entry.values():
        if isinstance(value, dict):
            result = first_nested(value, names)
            if has_value(result):
                return result
    return ""


def output_row(entry: dict, context: dict, operation: str, url: str, status: str, race: dict | None = None) -> dict:
    horse = clean(entry.get("horseName") or nested_get(entry, ["horse", "name"], "") or entry.get("runnerName") or "")
    horse_key = norm(entry.get("horseCode") or nested_get(entry, ["horse", "id"], "") or horse)
    sectionals = sectional_like_fields(entry, race)
    missing = ["last200", "last400", "last600"]
    return {
        "horse_key": horse_key,
        "horse": horse,
        "race_date": clean(context.get("race_date", "")),
        "track": clean(context.get("track", "")),
        "state": clean(context.get("state", "VIC")) or "VIC",
        "race_no": clean(context.get("race_no", "")),
        "distance": clean(context.get("distance", "")),
        "has_sectionals": clean(context.get("has_sectionals", "")),
        "has_speed_map": clean(context.get("has_speed_map", "")),
        "speed_value": clean(entry.get("speedValue", "")),
        "top_speed": first_nested(entry, ["topSpeed", "top_speed", "maxSpeed", "peakSpeed"]),
        "distance_travelled": first_nested(entry, ["distanceTravelled", "distance_travelled", "distanceCovered"]),
        "race_time": clean(context.get("race_time", "")),
        "runner_fields_json": compact_json(runner_fields(entry)),
        "sectional_fields_json": compact_json(sectionals),
        "source_operation": operation,
        "source_url": url,
        "parse_status": status,
        "missing_fields": ",".join(missing),
    }


def parse_get_race_number_list(data: dict, operation: str, url: str) -> list[dict]:
    races = nested_get(data, ["data", "getNoCacheRacesForMeet"], [])
    rows = []
    for race in races if isinstance(races, list) else []:
        context = race_context_from_race(race)
        sectionals = race_timing_fields(race)
        for entry in race.get("formRaceEntries", []) or []:
            if not isinstance(entry, dict):
                continue
            row = output_row(entry, context, operation, url, "PARSED_RACE_LIST", race)
            row["sectional_fields_json"] = compact_json({**sectionals, **sectional_like_fields(entry, race)})
            rows.append(row)
    return rows


def parse_get_race_form(data: dict, operation: str, url: str) -> list[dict]:
    race = nested_get(data, ["data", "getRaceForm"], {})
    if not isinstance(race, dict) or not race:
        return []
    context = race_context_from_race(race)
    sectionals = race_timing_fields(race)
    rows = []
    for entry in race.get("formRaceEntries", []) or []:
        if not isinstance(entry, dict):
            continue
        row = output_row(entry, context, operation, url, "PARSED_RACE_FORM", race)
        row["sectional_fields_json"] = compact_json({**sectionals, **sectional_like_fields(entry, race)})
        rows.append(row)
    return rows


def parse_response(data, operation: str, url: str) -> list[dict]:
    if not isinstance(data, dict):
        return []
    if operation == "getRaceNumberList_CD":
        return parse_get_race_number_list(data, operation, url)
    if operation in {"getRaceEntriesForField_CD", "getRaceResults_CD"}:
        return parse_get_race_form(data, operation, url)
    return []


def operation_from_payload(data, path: Path) -> str:
    name = path.name
    for operation in ALLOWED_OPERATIONS:
        if operation in name:
            return operation
    if isinstance(data, dict):
        payload = data.get("data", {})
        if isinstance(payload, dict):
            if "getNoCacheRacesForMeet" in payload:
                return "getRaceNumberList_CD"
            if "getRaceForm" in payload:
                return "getRaceEntriesForField_CD"
            if "getMeeting" in payload:
                return "getMeeting_CD"
    return ""


def parse_payload_directory(directory: Path, label: str) -> tuple[list[dict], list[dict]]:
    rows = []
    records = []
    if not directory.exists():
        return rows, records
    for path in sorted(directory.glob("*.json")):
        data, status = read_json_file(path)
        operation = operation_from_payload(data, path)
        if operation not in ALLOWED_OPERATIONS:
            records.append({
                "source_url": path.relative_to(PROJECT_ROOT).as_posix(),
                "operation": operation or "UNKNOWN",
                "fetch_status": f"{label}_{status}",
                "http_status": 0,
                "rows": 0,
                "raw_file": path.relative_to(PROJECT_ROOT).as_posix(),
            })
            continue
        parsed = parse_response(data, operation, path.relative_to(PROJECT_ROOT).as_posix()) if status == "READ" else []
        for row in parsed:
            row["parse_status"] = f"{row.get('parse_status', 'PARSED')}_{label}"
        rows.extend(parsed)
        records.append({
            "source_url": path.relative_to(PROJECT_ROOT).as_posix(),
            "operation": operation,
            "fetch_status": f"{label}_{status}",
            "http_status": 0,
            "rows": len(parsed),
            "raw_file": path.relative_to(PROJECT_ROOT).as_posix(),
        })
    return rows, records


def dedupe_rows(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS).fillna("")
    df["_priority"] = df["source_operation"].map({
        "getRaceEntriesForField_CD": 0,
        "getRaceResults_CD": 1,
        "getRaceNumberList_CD": 2,
    }).fillna(9)
    df = df.sort_values(["_priority", "source_url"])
    df = df.drop_duplicates(subset=["horse_key", "race_date", "track", "race_no", "source_operation"], keep="first")
    return df.drop(columns=["_priority"])[OUTPUT_COLUMNS]


def build_diagnostics(candidates: pd.DataFrame, rows: pd.DataFrame, fetch_records: list[dict]) -> pd.DataFrame:
    speed_count = int(rows["speed_value"].astype(str).str.len().gt(0).sum()) if not rows.empty else 0
    top_speed_count = int(rows["top_speed"].astype(str).str.len().gt(0).sum()) if not rows.empty and "top_speed" in rows.columns else 0
    distance_travelled_count = int(rows["distance_travelled"].astype(str).str.len().gt(0).sum()) if not rows.empty and "distance_travelled" in rows.columns else 0
    has_sectionals_count = int(rows["has_sectionals"].astype(str).str.upper().isin(["1", "TRUE", "YES"]).sum()) if not rows.empty else 0
    genuine_splits = 0
    if not rows.empty:
        genuine_splits = int(rows["sectional_fields_json"].astype(str).str.contains("last200|last400|last600", case=False, regex=True).sum())
    operations = rows["source_operation"].value_counts().to_dict() if not rows.empty else {}
    summary = [
        {"metric": "candidate_requests", "value": str(len(candidates)), "notes": "Unique captured GraphQL request URLs"},
        {"metric": "fetch_cap", "value": str(MAX_FETCHES), "notes": "EDGEIQ_RACINGCOM_GRAPHQL_MAX_FETCHES"},
        {"metric": "requests_fetched", "value": str(sum(1 for r in fetch_records if r["fetch_status"] == "FETCHED")), "notes": "HTTP 200 JSON responses"},
        {"metric": "operations_replayed", "value": ", ".join(sorted({r["operation"] for r in fetch_records})), "notes": compact_json(operations)},
        {"metric": "rows_parsed", "value": str(len(rows)), "notes": "Runner metadata rows parsed"},
        {"metric": "speed_value_count", "value": str(speed_count), "notes": "Rows with Racing.com speedValue"},
        {"metric": "top_speed_count", "value": str(top_speed_count), "notes": "Rows with Racing.com topSpeed"},
        {"metric": "distance_travelled_count", "value": str(distance_travelled_count), "notes": "Rows with Racing.com distanceTravelled"},
        {"metric": "has_sectionals_count", "value": str(has_sectionals_count), "notes": "Rows from races with hasSectionals true"},
        {"metric": "genuine_last200_400_600_count", "value": str(genuine_splits), "notes": "Rows where explicit last200/last400/last600 keys were observed"},
        {"metric": "latest_fetch_time", "value": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": "UTC"},
    ]
    details = [
        {
            "metric": "FETCH",
            "value": r["source_url"],
            "notes": f"operation={r['operation']}; http_status={r['http_status']}; fetch_status={r['fetch_status']}; rows={r['rows']}; raw_file={r['raw_file']}",
        }
        for r in fetch_records
    ]
    return pd.DataFrame(summary + details, columns=DIAG_COLUMNS)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    candidates = candidate_urls()
    rows = []
    fetch_records = []
    limited = candidates.head(MAX_FETCHES)
    total = len(limited)
    for position, (_, candidate) in enumerate(limited.iterrows(), start=1):
        url = clean(candidate["source_url"])
        operation = clean(candidate["source_operation"])
        data, fetch_status, http_status, raw_path = fetch_json(url)
        parsed = parse_response(data, operation, url) if fetch_status == "FETCHED" else []
        if not parsed:
            local_data, local_status, local_path = read_local_sample(clean(candidate.get("raw_sample_file", "")))
            local_rows = parse_response(local_data, operation, url) if local_status == "LOCAL_PROBE_SAMPLE" else []
            if local_rows:
                parsed = local_rows
                fetch_status = f"{fetch_status}+{local_status}"
                raw_path = local_path or raw_path
        rows.extend(parsed)
        raw_file = raw_path.relative_to(PROJECT_ROOT).as_posix() if raw_path else ""
        fetch_records.append({
            "source_url": url,
            "operation": operation,
            "fetch_status": fetch_status,
            "http_status": http_status,
            "rows": len(parsed),
            "raw_file": raw_file,
        })
        log(f"{position}/{total} {operation} {fetch_status} rows={len(parsed)}")
        if position < total:
            time.sleep(SLEEP_SECONDS)

    for directory, label in [
        (LEGACY_PROBE_PAYLOADS, "LOCAL_PROBE_DIR"),
        (FULL_PAYLOADS, "FULL_PAYLOAD"),
        (COMPLETED_PAYLOADS, "COMPLETED_PAYLOAD"),
    ]:
        payload_rows, payload_records = parse_payload_directory(directory, label)
        if payload_records:
            rows.extend(payload_rows)
            fetch_records.extend(payload_records)
            log(f"{label.lower()} files parsed: {len(payload_records)} rows={len(payload_rows)}")

    output = dedupe_rows(rows)
    diagnostics = build_diagnostics(candidates, output, fetch_records)
    output.to_csv(OUT, index=False, encoding="utf-8")
    diagnostics.to_csv(DIAG_OUT, index=False, encoding="utf-8")

    speed_count = diagnostics.loc[diagnostics["metric"] == "speed_value_count", "value"].iloc[0]
    has_sectionals = diagnostics.loc[diagnostics["metric"] == "has_sectionals_count", "value"].iloc[0]
    genuine_splits = diagnostics.loc[diagnostics["metric"] == "genuine_last200_400_600_count", "value"].iloc[0]
    log(f"operations replayed: {diagnostics.loc[diagnostics['metric'] == 'operations_replayed', 'value'].iloc[0]}")
    log(f"rows parsed: {len(output)}")
    log(f"speedValue coverage: {speed_count}")
    log(f"hasSectionals count: {has_sectionals}")
    log(f"genuine last200/400/600 coverage: {genuine_splits}")
    log(f"wrote {OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAG_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
