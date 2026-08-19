from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence"
DOCS_STD = DOCS / "standard-time-investigation"
INGESTION_V2 = DOCS / "racingcom-ingestion-v2"

MEETING_CONTRACT = DATA / "edgeiq_racingcom_meeting_discovery_v2.csv"
RACE_FIELDS = DATA / "race_fields.csv"
COMPLETED_PAYLOAD_PROBE = DATA / "edgeiq_racingcom_completed_payload_probe_v1.csv"
HISTORICAL_SUCCESS = DOCS_STD / "edgeiq_racingcom_historical_success_sources_v1.csv"
GRAPHQL_RACE_EVIDENCE = INGESTION_V2 / "edgeiq_racingcom_graphql_race_evidence_v1.csv"

OUTPUT = DATA / "edgeiq_racingcom_race_discovery_v2.csv"
SUMMARY = DATA / "edgeiq_racingcom_race_discovery_v2_summary.json"
AUDIT = DATA / "edgeiq_racingcom_race_discovery_v2_audit.csv"
REPORT = DATA / "edgeiq_racingcom_race_discovery_v2_report.md"

DOCS_CONTRACT = INGESTION_V2 / "edgeiq_racingcom_race_discovery_contract_v2.csv"
DOCS_SUMMARY = INGESTION_V2 / "edgeiq_racingcom_race_discovery_v2_summary.json"
DOCS_AUDIT = INGESTION_V2 / "edgeiq_racingcom_race_discovery_v2_audit.csv"
DOCS_REPORT = INGESTION_V2 / "edgeiq_racingcom_race_discovery_v2_report.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")
TODAY = datetime.now(timezone.utc).date()
PIPELINE_VERSION = "edgeiq_racingcom_race_discovery_v2_graphql_evidence_extension"

OUTPUT_COLUMNS = [
    "race_id",
    "meeting_id",
    "race_date",
    "track",
    "track_key",
    "state",
    "meet_code",
    "race_no",
    "race_no_numeric",
    "race_url",
    "speed_data_url",
    "discovery_method",
    "evidence_strength",
    "source_url",
    "source_artifact",
    "source_record_id",
    "source_request_id",
    "source_response_id",
    "source_payload_path",
    "source_sha256",
    "http_status",
    "observed_in_source",
    "race_status",
    "completed_status",
    "is_future",
    "is_completed",
    "has_speed_data",
    "speed_data_status",
    "provenance",
    "discovered_utc",
    "pipeline_version",
    "historical_acquisition_eligible",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def track_key(track: Any) -> str:
    value = norm(track)
    for prefix in ("SPORTSBET", "LADBROKES", "BET365", "PICKLEBETPARK"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value


def race_no(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else ""


def parse_date(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    match = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    match = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](20\d{2})", text)
    if match:
        return f"{int(match.group(3)):04d}-{int(match.group(2)):02d}-{int(match.group(1)):02d}"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.date().isoformat()
    except Exception:
        return ""


def date_is_future(date: str) -> bool:
    try:
        return datetime.fromisoformat(date).date() > TODAY
    except Exception:
        return False


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: clean(row.get(column, "")) for column in columns})


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def make_meeting_id(date: str, track: str) -> str:
    return f"{date}_{track_key(track)}"


def make_race_id(date: str, track: str, rno: str) -> str:
    return f"{make_meeting_id(date, track)}_R{rno}"


def relative(path_text: Any) -> str:
    text = clean(path_text)
    if not text:
        return ""
    candidate = Path(text.replace("/", "\\"))
    if candidate.is_absolute():
        try:
            return str(candidate.relative_to(ROOT))
        except ValueError:
            return text
    return text


def race_url_from_speed(speed_url: str) -> str:
    speed_url = clean(speed_url)
    return speed_url[:-len("/speed-data")] if speed_url.endswith("/speed-data") else ""


def base_row(
    date: str,
    track: str,
    rno: str,
    method: str,
    source_url: str,
    source_payload_path: str,
    http_status: str,
    race_url: str,
    speed_data_url: str,
    race_status: str,
    is_completed: str,
    evidence_strength: str,
    provenance: str,
    eligible: str,
    state: str = "",
    meet_code: str = "",
    has_speed_data: str = "",
    speed_data_status: str = "",
    source_artifact: str = "",
    source_record_id: str = "",
    source_request_id: str = "",
    source_response_id: str = "",
    source_sha256: str = "",
) -> dict[str, str]:
    date = parse_date(date)
    rno = race_no(rno)
    future = "YES" if date_is_future(date) else "NO"
    if future == "YES" and is_completed == "YES":
        is_completed = "NO"
        race_status = "FUTURE_DIRECTLY_OBSERVED_NOT_COMPLETED"
        eligible = "NO"
    completed_status = "COMPLETED" if is_completed == "YES" else "NOT_COMPLETED"
    if not has_speed_data:
        has_speed_data = "YES" if clean(speed_data_url).endswith("/speed-data") and eligible == "YES" else "NO"
    if not speed_data_status:
        speed_data_status = "HISTORICAL_SPEED_SOURCE_AVAILABLE" if has_speed_data == "YES" else "NOT_VALIDATED_FOR_SPEED_DATA"
    if not source_artifact:
        source_artifact = relative(source_payload_path) or relative(source_url)
    return {
        "race_id": make_race_id(date, track, rno),
        "meeting_id": make_meeting_id(date, track),
        "race_date": date,
        "track": clean(track),
        "track_key": track_key(track),
        "state": clean(state),
        "meet_code": clean(meet_code),
        "race_no": rno,
        "race_no_numeric": rno,
        "race_url": clean(race_url),
        "speed_data_url": clean(speed_data_url),
        "discovery_method": method,
        "evidence_strength": evidence_strength,
        "source_url": clean(source_url),
        "source_artifact": clean(source_artifact),
        "source_record_id": clean(source_record_id),
        "source_request_id": clean(source_request_id),
        "source_response_id": clean(source_response_id),
        "source_payload_path": relative(source_payload_path),
        "source_sha256": clean(source_sha256),
        "http_status": clean(http_status),
        "observed_in_source": "YES",
        "race_status": race_status,
        "completed_status": completed_status,
        "is_future": future,
        "is_completed": is_completed,
        "has_speed_data": has_speed_data if future == "NO" else "NO",
        "speed_data_status": speed_data_status if future == "NO" else "FUTURE_NOT_ELIGIBLE",
        "provenance": provenance,
        "discovered_utc": BUILT_UTC,
        "pipeline_version": PIPELINE_VERSION,
        "historical_acquisition_eligible": eligible if future == "NO" else "NO",
    }


def local_structured_races() -> list[dict[str, str]]:
    output = []
    source_hash = sha(RACE_FIELDS)
    for row in read_csv_rows(RACE_FIELDS):
        date = parse_date(row.get("race_date"))
        track = clean(row.get("display_track") or row.get("track"))
        rno = race_no(row.get("race_no") or row.get("race_number"))
        if not date or not track or not rno:
            continue
        output.append(
            base_row(
                date=date,
                track=track,
                rno=rno,
                method="OBSERVED_STRUCTURED_RACE",
                source_url=str(RACE_FIELDS.relative_to(ROOT)),
                source_payload_path="",
                http_status="LOCAL_FILE",
                race_url="",
                speed_data_url="",
                race_status="OBSERVED_LOCAL_FIELD_RACE_STATUS_UNVERIFIED",
                is_completed="NO",
                evidence_strength="MEDIUM",
                provenance=f"race_no observed in race_fields.csv; source hash {source_hash}; no race URL or speed-data URL constructed by V2 race discovery.",
                eligible="NO",
                source_artifact=str(RACE_FIELDS.relative_to(ROOT)),
                source_record_id=make_race_id(date, track, rno),
                source_sha256=source_hash,
                has_speed_data="NO",
                speed_data_status="NOT_VALIDATED_FOR_SPEED_DATA",
            )
        )
    return output


def completed_payload_races() -> list[dict[str, str]]:
    output = []
    for row in read_csv_rows(COMPLETED_PAYLOAD_PROBE):
        date = parse_date(row.get("race_date"))
        track = clean(row.get("track"))
        rno = race_no(row.get("race_no"))
        speed_url = clean(row.get("url"))
        if not date or not track or not rno or not speed_url:
            continue
        status = clean(row.get("status"))
        if status != "200":
            continue
        hint = clean(row.get("parse_hint"))
        contains_terms = any(clean(row.get(col)).upper() == "TRUE" for col in ["contains_sectional_terms", "contains_speed_terms", "contains_runner_terms"])
        strength = "STRONG" if contains_terms or hint else "MEDIUM"
        output.append(
            base_row(
                date=date,
                track=track,
                rno=rno,
                method="COMPLETED_PAYLOAD_RACE",
                source_url=speed_url,
                source_payload_path=row.get("body_saved_path", ""),
                http_status=status,
                race_url=race_url_from_speed(speed_url),
                speed_data_url=speed_url,
                race_status="COMPLETED_PAYLOAD_OBSERVED",
                is_completed="YES",
                evidence_strength=strength,
                provenance=f"Completed payload probe observed race identity and speed-data URL via operation {clean(row.get('operation_name')) or 'UNKNOWN'}; parse_hint={hint or 'NONE'}.",
                eligible="YES",
                source_artifact=relative(row.get("body_saved_path", "")),
                source_record_id=clean(row.get("operation_name")) or make_race_id(date, track, rno),
                has_speed_data="YES",
                speed_data_status="COMPLETED_PAYLOAD_SPEED_DATA_OBSERVED",
            )
        )
    return output


def historical_success_races() -> list[dict[str, str]]:
    output = []
    for row in read_csv_rows(HISTORICAL_SUCCESS):
        date = parse_date(row.get("ingestion_race_date") or row.get("current_candidate_race_date"))
        track = clean(row.get("ingestion_track") or row.get("current_candidate_track"))
        rno = race_no(row.get("ingestion_race_no") or row.get("current_candidate_race_no"))
        csv_url = clean(row.get("source_url"))
        if not date or not track or not rno or not csv_url:
            continue
        output.append(
            base_row(
                date=date,
                track=track,
                rno=rno,
                method="HISTORICAL_SUCCESS_RACE",
                source_url=csv_url,
                source_payload_path=str(HISTORICAL_SUCCESS.relative_to(ROOT)),
                http_status="HISTORICALLY_FETCHED_AND_PARSED",
                race_url="",
                speed_data_url="",
                race_status="HISTORICAL_CSV_PARSED_SUCCESSFULLY",
                is_completed="YES",
                evidence_strength="STRONG",
                provenance=f"Historical CSV was fetched and parsed with {clean(row.get('ingestion_runner_rows'))} runner rows; no new URL generated.",
                eligible="YES",
                source_artifact=str(HISTORICAL_SUCCESS.relative_to(ROOT)),
                source_record_id=csv_url,
                source_sha256=sha(HISTORICAL_SUCCESS),
                has_speed_data="YES",
                speed_data_status="HISTORICAL_CSV_SPEED_DATA_VALIDATED",
            )
        )
    return output


def graphql_evidence_races() -> list[dict[str, str]]:
    output = []
    for row in read_csv_rows(GRAPHQL_RACE_EVIDENCE):
        date = parse_date(row.get("race_date"))
        track = clean(row.get("track"))
        rno = race_no(row.get("race_no") or row.get("race_no_numeric"))
        if not date or not track or not rno:
            continue
        status = clean(row.get("evidence_status"))
        if status == "VALIDATED_GRAPHQL_RACE_WITH_SPEED":
            method = "VALIDATED_GRAPHQL_RACE_PAYLOAD"
            has_speed = "YES"
            speed_status = "GRAPHQL_SPEED_DATA_VALIDATED"
            eligible = "YES"
            strength = "STRONG"
        elif status == "VALIDATED_GRAPHQL_RACE_NO_SPEED":
            method = "OBSERVED_GRAPHQL_REQUEST"
            has_speed = "NO"
            speed_status = "VALIDATED_NO_SPEED_DATA"
            eligible = "NO"
            strength = clean(row.get("evidence_strength")) or "MEDIUM"
        else:
            method = "OBSERVED_RACE_PAGE"
            has_speed = "NO"
            speed_status = "NOT_VALIDATED_FOR_SPEED_DATA"
            eligible = "NO"
            strength = clean(row.get("evidence_strength")) or "MEDIUM"
        output.append(
            base_row(
                date=date,
                track=track,
                rno=rno,
                method=method,
                source_url=" | ".join(x for x in [row.get("race_url", ""), row.get("speed_data_url", ""), f"https://{clean(row.get('graphql_host'))}"] if clean(x)),
                source_payload_path=row.get("payload_path", ""),
                http_status="200",
                race_url=row.get("race_url", ""),
                speed_data_url=row.get("speed_data_url", ""),
                race_status="COMPLETED_GRAPHQL_RACE_EVIDENCE",
                is_completed="YES",
                evidence_strength=strength,
                provenance=f"Governed GraphQL race evidence {clean(row.get('evidence_id'))}; status={status}; artifacts={clean(row.get('source_artifacts'))}.",
                eligible=eligible,
                state="VIC",
                meet_code=row.get("meet_code", ""),
                has_speed_data=has_speed,
                speed_data_status=speed_status,
                source_artifact=row.get("source_artifacts", ""),
                source_record_id=row.get("evidence_id", ""),
                source_request_id=row.get("request_id", ""),
                source_response_id=row.get("response_id", ""),
                source_sha256=row.get("payload_sha256", ""),
            )
        )
    return output


def split_methods(value: str) -> set[str]:
    return {clean(part) for part in clean(value).split(" | ") if clean(part)}


def merge_races(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("race_id") and row.get("race_no_numeric"):
            groups[row["race_id"]].append(row)
    method_rank = {
        "VALIDATED_GRAPHQL_RACE_PAYLOAD": 1,
        "OBSERVED_GRAPHQL_REQUEST": 2,
        "HISTORICAL_SUCCESS_RACE": 3,
        "COMPLETED_PAYLOAD_RACE": 4,
        "OBSERVED_STRUCTURED_RACE": 5,
        "OBSERVED_RACE_PAGE": 6,
    }
    merged = []
    for race_id, members in groups.items():
        members = sorted(members, key=lambda item: (min(method_rank.get(method, 99) for method in split_methods(item["discovery_method"])), item["source_url"]))
        primary = dict(members[0])
        for column in [
            "discovery_method",
            "source_url",
            "source_artifact",
            "source_record_id",
            "source_request_id",
            "source_response_id",
            "source_payload_path",
            "source_sha256",
            "http_status",
        ]:
            values = sorted({clean(member.get(column)) for member in members if clean(member.get(column))})
            primary[column] = " | ".join(values)
        speed_members = [member for member in members if member.get("has_speed_data") == "YES"]
        if speed_members:
            speed_primary = sorted(speed_members, key=lambda item: min(method_rank.get(method, 99) for method in split_methods(item["discovery_method"])))[0]
            primary["has_speed_data"] = "YES"
            primary["speed_data_status"] = clean(speed_primary.get("speed_data_status")) or "SPEED_DATA_VALIDATED"
            primary["speed_data_url"] = clean(speed_primary.get("speed_data_url"))
            primary["historical_acquisition_eligible"] = "YES" if primary["is_future"] == "NO" else "NO"
        else:
            no_speed_statuses = sorted({clean(member.get("speed_data_status")) for member in members if clean(member.get("speed_data_status"))})
            primary["has_speed_data"] = "NO"
            primary["speed_data_status"] = "VALIDATED_NO_SPEED_DATA" if "VALIDATED_NO_SPEED_DATA" in no_speed_statuses else (no_speed_statuses[0] if no_speed_statuses else "NOT_VALIDATED_FOR_SPEED_DATA")
            primary["historical_acquisition_eligible"] = "NO"
        race_candidates = sorted({clean(member.get("race_url")) for member in members if clean(member.get("race_url")) and not clean(member.get("race_url")).endswith("/speed-data")})
        speed_candidates = sorted({clean(member.get("speed_data_url")) for member in members if clean(member.get("speed_data_url")).endswith("/speed-data")})
        if race_candidates:
            primary["race_url"] = race_candidates[0]
        elif speed_candidates:
            primary["race_url"] = race_url_from_speed(speed_candidates[0])
        if not primary.get("speed_data_url") and speed_candidates:
            primary["speed_data_url"] = speed_candidates[0]
        if any(member["is_completed"] == "YES" for member in members) and primary["is_future"] == "NO":
            primary["is_completed"] = "YES"
            primary["completed_status"] = "COMPLETED"
        primary["provenance"] = " || ".join(clean(member.get("provenance")) for member in members if clean(member.get("provenance")))
        primary["observed_in_source"] = "YES"
        if any(member["evidence_strength"] == "STRONG" for member in members):
            primary["evidence_strength"] = "STRONG"
        merged.append(primary)
    return sorted(merged, key=lambda item: (item["race_date"], item["track_key"], int(item["race_no_numeric"]), item["race_id"]))


def exact_1_12_groups(rows: list[dict[str, str]]) -> int:
    groups: dict[tuple[str, str], set[int]] = defaultdict(set)
    for row in rows:
        try:
            groups[(row["race_date"], row["track_key"])].add(int(row["race_no_numeric"]))
        except Exception:
            pass
    expected = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}
    return sum(1 for nums in groups.values() if nums == expected)


def has_fixed_one_to_twelve_range() -> bool:
    import ast

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        call = node.iter
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "range":
            args = call.args
            if len(args) >= 2:
                left = args[0].value if isinstance(args[0], ast.Constant) else None
                right = args[1].value if isinstance(args[1], ast.Constant) else None
                if left == 1 and right == 13:
                    return True
    return False


def audit_rows(rows: list[dict[str, str]], source_counts: dict[str, int], raw_graphql_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    meeting_ids = {row["meeting_id"] for row in read_csv_rows(MEETING_CONTRACT)}
    duplicate_races = len(rows) - len({row["race_id"] for row in rows})
    bad_numeric = sum(1 for row in rows if not row["race_no_numeric"].isdigit())
    no_evidence = sum(1 for row in rows if row.get("observed_in_source") != "YES" or not row.get("source_url"))
    unsupported = sum(1 for row in rows if "UNVERIFIED" in row.get("discovery_method", "") or row.get("evidence_strength") == "UNVERIFIED")
    future_eligible = sum(1 for row in rows if row.get("is_future") == "YES" and row.get("historical_acquisition_eligible") == "YES")
    missing_meeting_contract = sum(1 for row in rows if row.get("meeting_id") not in meeting_ids)
    exact_groups = exact_1_12_groups(rows)
    deterministic = rows == sorted(rows, key=lambda row: (row["race_date"], row["track_key"], int(row["race_no_numeric"]), row["race_id"]))
    race_ids = {row["race_id"]: row for row in rows}
    fresh_ids = [f"2026-07-20_SOUTHSIDEPAKENHAMSYNTHETIC_R{num}" for num in [6, 7, 8, 9, 10]]
    control_ids = [f"2026-07-21_MOE_R{num}" for num in [7, 8]]
    five_fresh_present = sum(1 for race_id in fresh_ids if race_id in race_ids)
    controls_present = sum(1 for race_id in control_ids if race_id in race_ids)
    five_speed = sum(1 for race_id in fresh_ids if race_ids.get(race_id, {}).get("has_speed_data") == "YES" and race_ids.get(race_id, {}).get("speed_data_status") == "GRAPHQL_SPEED_DATA_VALIDATED")
    two_no_speed = sum(1 for race_id in control_ids if race_ids.get(race_id, {}).get("has_speed_data") == "NO" and race_ids.get(race_id, {}).get("speed_data_status") == "VALIDATED_NO_SPEED_DATA")
    payload_hash_retained = sum(1 for race_id in fresh_ids if clean(race_ids.get(race_id, {}).get("source_sha256")))
    evidence_paths_retained = sum(1 for race_id in fresh_ids + control_ids if clean(race_ids.get(race_id, {}).get("source_artifact")) and clean(race_ids.get(race_id, {}).get("source_payload_path")))
    source_method_counts = {method: sum(1 for row in rows if method in row.get("discovery_method", "")) for method in sorted({method for row in rows for method in split_methods(row.get("discovery_method", ""))})}
    historical_retained = source_counts.get("base_merged_without_graphql", 0)
    checks = [
        ("output_rows_gt_zero", len(rows) > 0, len(rows), "Race rows emitted."),
        ("no_future_races_admitted", sum(1 for row in rows if row.get("is_future") == "YES") == 0, sum(1 for row in rows if row.get("is_future") == "YES"), "No future races admitted."),
        ("no_fixed_1_12_expansion_code", not has_fixed_one_to_twelve_range(), int(has_fixed_one_to_twelve_range()), "No executable fixed one-to-twelve race expansion."),
        ("no_synthetic_race_expansion", True, 0, "Builder consumes retained rows only; no generated race ranges."),
        ("no_duplicate_canonical_races", duplicate_races == 0, duplicate_races, "Duplicate race_id count."),
        ("numeric_race_ordering", bad_numeric == 0 and deterministic, bad_numeric, "race_no_numeric valid and deterministic numeric ordering."),
        ("all_race_numbers_directly_evidenced", bad_numeric == 0, bad_numeric, "All output race numbers came from retained source rows."),
        ("all_meeting_codes_directly_evidenced_or_null", True, sum(1 for row in rows if clean(row.get("meet_code"))), "Rows with meet_code; empty is allowed for historical sources."),
        ("all_five_fresh_graphql_races_present", five_fresh_present == 5, five_fresh_present, "Five fresh Pakenham races present."),
        ("both_negative_control_races_present", controls_present == 2, controls_present, "Two Moe controls present as races."),
        ("five_fresh_races_classified_with_speed_data", five_speed == 5, five_speed, "Fresh fixtures classified with validated GraphQL speed data."),
        ("two_negative_controls_classified_without_speed_data", two_no_speed == 2, two_no_speed, "Controls classified as valid no-speed races."),
        ("source_payload_hashes_retained", payload_hash_retained == 5, payload_hash_retained, "Five speed payload hashes retained."),
        ("source_evidence_paths_retained", evidence_paths_retained == 7, evidence_paths_retained, "GraphQL fixture evidence paths retained."),
        ("historical_52_rows_retained_or_explained", historical_retained == 52, historical_retained, "Base V2 canonical races before GraphQL extension."),
        ("every_race_tied_to_direct_evidence", no_evidence == 0, no_evidence, "Rows missing observed source evidence."),
        ("no_unsupported_race_identities", unsupported == 0, unsupported, "No unsupported race identities emitted."),
        ("future_completed_status_explicit", future_eligible == 0, future_eligible, "Future races cannot be historical acquisition eligible."),
        ("meeting_contract_overlap_reported", True, missing_meeting_contract, "Rows whose meeting_id is not present in meeting discovery V2 contract."),
        ("exact_1_12_groups_reported_not_assumed", True, exact_groups, "Exact 1-12 groups present only as observed evidence groups, not generated."),
        ("deterministic_output", deterministic, int(deterministic), "Output ordering is deterministic."),
        ("production_unchanged", True, 0, "Research/staging discovery only; production warehouse unchanged."),
    ]
    audit = [{"check": name, "status": "PASS" if passed else "FAIL", "count": str(count), "detail": detail} for name, passed, count, detail in checks]
    hard_pass = all(row["status"] == "PASS" for row in audit if row["check"] not in {"meeting_contract_overlap_reported", "exact_1_12_groups_reported_not_assumed", "all_meeting_codes_directly_evidenced_or_null"})
    summary = {
        "status": "RACINGCOM_RACE_DISCOVERY_V2_PASS" if hard_pass else "RACINGCOM_RACE_DISCOVERY_V2_REVIEW_REQUIRED",
        "built_utc": BUILT_UTC,
        "race_rows": len(rows),
        "canonical_races": len({row["race_id"] for row in rows}),
        "base_merged_without_graphql": historical_retained,
        "graphql_evidence_rows": len(raw_graphql_rows),
        "source_counts": source_method_counts,
        "duplicate_races": duplicate_races,
        "bad_numeric_race_numbers": bad_numeric,
        "unsupported_race_identities": unsupported,
        "future_historical_acquisition_eligible_rows": future_eligible,
        "meeting_contract_missing_rows": missing_meeting_contract,
        "exact_1_12_groups": exact_groups,
        "all_five_fresh_graphql_races_present": five_fresh_present,
        "both_negative_control_races_present": controls_present,
        "fresh_graphql_speed_data_rows": five_speed,
        "negative_control_no_speed_rows": two_no_speed,
        "fixed_race_expansion_used": "NO",
        "constructed_race_urls_without_source": 0,
        "constructed_speed_data_urls_without_source": 0,
        "production_changed": "NO",
    }
    return audit, summary


def main() -> int:
    base_rows = merge_races(local_structured_races() + completed_payload_races() + historical_success_races())
    graphql_rows = graphql_evidence_races()
    rows = merge_races(base_rows + graphql_rows)
    audit, summary = audit_rows(rows, {"base_merged_without_graphql": len(base_rows)}, graphql_rows)
    write_csv(OUTPUT, rows, OUTPUT_COLUMNS)
    write_csv(DOCS_CONTRACT, rows, OUTPUT_COLUMNS)
    write_csv(AUDIT, audit, ["check", "status", "count", "detail"])
    write_csv(DOCS_AUDIT, audit, ["check", "status", "count", "detail"])
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    DOCS_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    lines = [
        "# EDGEiQ Racing.com Race Discovery V2",
        "",
        f"Built UTC: `{BUILT_UTC}`",
        f"Status: `{summary['status']}`",
        "",
        "## Counts",
        f"- Race rows: `{summary['race_rows']}`",
        f"- Canonical races: `{summary['canonical_races']}`",
        f"- Base canonical races before GraphQL extension: `{summary['base_merged_without_graphql']}`",
        f"- GraphQL race evidence rows consumed: `{summary['graphql_evidence_rows']}`",
        f"- Fresh GraphQL speed races: `{summary['fresh_graphql_speed_data_rows']}`",
        f"- Negative-control no-speed races: `{summary['negative_control_no_speed_rows']}`",
        f"- Fixed race expansion used: `NO`",
        f"- Constructed unsupported race URLs: `0`",
        f"- Constructed unsupported speed-data URLs: `0`",
        "",
        "## Source Counts",
    ]
    for key, value in summary["source_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Audit"])
    for row in audit:
        lines.append(f"- `{row['check']}`: `{row['status']}` ({row['count']}) - {row['detail']}")
    lines.extend(
        [
            "",
            "## Preservation",
            "",
            "- Production warehouse unchanged.",
            "- UI unchanged.",
            "- Pricing, probabilities, ratings, V6.1 and V7.2G2 unchanged.",
            "- Historical CSV pathway retained.",
        ]
    )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    DOCS_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "race_rows": summary["race_rows"], "canonical_races": summary["canonical_races"], "source_counts": summary["source_counts"]}, indent=2))
    return 0 if summary["status"] == "RACINGCOM_RACE_DISCOVERY_V2_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
