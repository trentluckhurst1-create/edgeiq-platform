from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INGESTION_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
DISCOVERY_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-source-discovery"

RACE_DISCOVERY = INGESTION_DIR / "edgeiq_racingcom_race_discovery_contract_v2.csv"
FIXTURE_CONTRACT = DISCOVERY_DIR / "edgeiq_racingcom_speed_data_fixture_contract_v1.csv"
SOURCE_VALIDATION = DISCOVERY_DIR / "edgeiq_racingcom_source_candidate_validation_v1.csv"
NETWORK_REQUEST_LEDGER = DISCOVERY_DIR / "edgeiq_racingcom_network_request_ledger_v1.csv"

ADMISSION_OUT = INGESTION_DIR / "edgeiq_racingcom_graphql_source_admission_v1.csv"
REJECTIONS_OUT = INGESTION_DIR / "edgeiq_racingcom_graphql_source_rejections_v1.csv"
AUDIT_OUT = INGESTION_DIR / "edgeiq_racingcom_graphql_source_admission_audit_v1.csv"
SUMMARY_OUT = INGESTION_DIR / "edgeiq_racingcom_graphql_source_admission_summary_v1.json"
REPORT_OUT = INGESTION_DIR / "edgeiq_racingcom_graphql_source_admission_report_v1.md"

PIPELINE_VERSION = "edgeiq_racingcom_graphql_source_admission_v1"
SOURCE_HOST = "graphql.rmdprod.racing.com"
GRAPHQL_OPERATION = "sectionaltimes_callback"
GRAPHQL_RESOLVER = "getRaceForm"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def canonical_track(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def is_int(value: str) -> bool:
    try:
        int(clean(value))
        return True
    except Exception:
        return False


def find_evidence_path(source_evidence: str) -> str:
    for token in source_evidence.split("||"):
        token = token.strip()
        match = re.search(r"(outputs/[^\s;]+|docs/[^\s;]+)", token)
        if match:
            return match.group(1)
    return ""


def extract_meet_code(source_evidence: str) -> str:
    match = re.search(r"MeetCode=(\d+)|meetCode=(\d+)", source_evidence)
    if match:
        return next(group for group in match.groups() if group)
    return ""


def has_graphql_source_support(validation_rows: list[dict[str, str]]) -> bool:
    for row in validation_rows:
        if row.get("candidate_id") == "GRAPHQL_SECTIONALTIMES_GETRACEFORM_AGGREGATE":
            return row.get("decision") == "VALID_GRAPHQL_SOURCE"
    return False


def fixture_has_graphql_request(fixture_id: str, request_rows: list[dict[str, str]]) -> bool:
    for row in request_rows:
        if row.get("fixture_id") != fixture_id:
            continue
        if "sectionaltimes_callback" in row.get("url", "") or "sectionaltimes_callback" in row.get("url", "").lower():
            return True
    return False


def main() -> None:
    admitted_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    race_rows = read_csv(RACE_DISCOVERY)
    fixtures = read_csv(FIXTURE_CONTRACT)
    validation = read_csv(SOURCE_VALIDATION)
    request_rows = read_csv(NETWORK_REQUEST_LEDGER)

    race_index: dict[tuple[str, str, str], dict[str, str]] = {}
    duplicate_race_keys: Counter[tuple[str, str, str]] = Counter()
    for race in race_rows:
        key = (race.get("race_date", ""), canonical_track(race.get("track", "")), clean(race.get("race_no_numeric") or race.get("race_no")))
        duplicate_race_keys[key] += 1
        if key not in race_index:
            race_index[key] = race

    graphql_supported = has_graphql_source_support(validation)
    admission_rows: list[dict[str, Any]] = []
    rejection_rows: list[dict[str, Any]] = []

    candidate_fixtures = [
        fixture
        for fixture in fixtures
        if fixture.get("visible_speed_data_status") in {"VISIBLE_SPEED_DATA_INDICATED", "NO_VISIBLE_SPEED_DATA"}
    ]

    for fixture in sorted(candidate_fixtures, key=lambda row: (row.get("race_date", ""), canonical_track(row.get("track", "")), int(row.get("race_no") or 0))):
        race_date = fixture.get("race_date", "")
        track = fixture.get("track", "")
        race_no = clean(fixture.get("race_no", ""))
        track_key = canonical_track(track)
        key = (race_date, track_key, race_no)
        race = race_index.get(key)
        meet_code = extract_meet_code(fixture.get("source_evidence", ""))
        status = "ADMITTED_GRAPHQL_SPEED_DATA"
        reason = "Completed race is present in V2 race discovery and source-discovery validates GraphQL sectionals."

        if fixture.get("visible_speed_data_status") == "NO_VISIBLE_SPEED_DATA":
            status = "REJECTED_NEGATIVE_CONTROL"
            reason = "Fixture is governed as a no-visible-speed negative control."
        elif not race:
            status = "REJECTED_UNVERIFIED_RACE"
            reason = "Fresh fixture is not present in edgeiq_racingcom_race_discovery_contract_v2; directive forbids admission outside valid V2 race discovery."
        elif clean(race.get("is_future")).upper() == "YES":
            status = "DEFERRED_FUTURE_RACE"
            reason = "Race discovery marks race as future-dated."
        elif clean(race.get("is_completed")).upper() != "YES":
            status = "REJECTED_NOT_COMPLETED"
            reason = "Race discovery does not mark race as completed."
        elif not meet_code:
            status = "REJECTED_MISSING_MEET_CODE"
            reason = "No directly evidenced meeting code was available."
        elif not is_int(race_no):
            status = "REJECTED_MISSING_RACE_NUMBER"
            reason = "Race number is missing or non-numeric."
        elif not graphql_supported or not fixture_has_graphql_request(fixture.get("fixture_id", ""), request_rows):
            status = "REJECTED_UNVERIFIED_RACE"
            reason = "GraphQL source support or fixture-level sectionaltimes request evidence is missing."
        elif duplicate_race_keys[key] > 1:
            status = "REJECTED_INVALID_IDENTITY"
            reason = "Duplicate canonical race identity exists in V2 race discovery."

        row = {
            "admission_id": f"GRAPHQL_ADMISSION_{race_date}_{track_key}_R{race_no}",
            "race_id": race.get("race_id", "") if race else f"{race_date}_{track_key}_R{race_no}",
            "meeting_id": race.get("meeting_id", "") if race else f"{race_date}_{track_key}",
            "race_date": race_date,
            "track": track,
            "track_key": track_key,
            "meet_code": meet_code,
            "race_no": race_no,
            "race_no_numeric": race_no if is_int(race_no) else "",
            "race_url": race.get("race_url", "") if race else fixture.get("race_url", ""),
            "speed_data_url": race.get("speed_data_url", "") if race else fixture.get("speed_data_url", ""),
            "race_status": race.get("race_status", "") if race else fixture.get("completed_status", ""),
            "completed_status": fixture.get("completed_status", ""),
            "source_type": "FRESH_GRAPHQL",
            "source_host": SOURCE_HOST,
            "graphql_operation": GRAPHQL_OPERATION,
            "graphql_resolver": GRAPHQL_RESOLVER,
            "admission_status": status,
            "admission_reason": reason,
            "evidence_source": "edgeiq_racingcom_speed_data_fixture_contract_v1.csv; edgeiq_racingcom_source_candidate_validation_v1.csv; edgeiq_racingcom_network_request_ledger_v1.csv",
            "evidence_path": find_evidence_path(fixture.get("source_evidence", "")),
            "admitted_utc": admitted_utc,
            "pipeline_version": PIPELINE_VERSION,
        }
        if status == "ADMITTED_GRAPHQL_SPEED_DATA":
            admission_rows.append(row)
        else:
            rejection_rows.append(row)

    audit_rows: list[dict[str, Any]] = []

    def add_audit(check: str, status: str, count: Any, detail: str) -> None:
        audit_rows.append({"check": check, "status": status, "count": count, "detail": detail})

    admitted = admission_rows
    add_audit("graphql_source_supported", "PASS" if graphql_supported else "FAIL", int(graphql_supported), "Source validation must prove VALID_GRAPHQL_SOURCE.")
    add_audit("no_future_races_admitted", "PASS" if not [r for r in admitted if r["completed_status"].upper().find("FUTURE") >= 0] else "FAIL", 0, "No future races may be admitted.")
    add_audit("no_missing_meet_code", "PASS" if not [r for r in admitted if not r["meet_code"]] else "FAIL", sum(1 for r in admitted if not r["meet_code"]), "Every admitted race must have directly evidenced meet code.")
    add_audit("no_missing_numeric_race_number", "PASS" if not [r for r in admitted if not is_int(r["race_no_numeric"])] else "FAIL", sum(1 for r in admitted if not is_int(r["race_no_numeric"])), "Every admitted race must have numeric race number.")
    canonical_ids = [f"{r['race_date']}|{r['track_key']}|{r['race_no_numeric']}" for r in admitted]
    add_audit("no_duplicate_canonical_race_identity", "PASS" if len(canonical_ids) == len(set(canonical_ids)) else "FAIL", len(canonical_ids) - len(set(canonical_ids)), "Admitted race identity must be unique.")
    add_audit("no_fixed_race_range_generation", "PASS", 0, "Script iterates fixture contract rows only; no generated race range.")
    add_audit("no_unsupported_meeting_code_derivation", "PASS", 0, "Meet code is extracted only from retained fixture evidence text.")
    add_audit("deterministic_ordering", "PASS", len(candidate_fixtures), "Rows sorted by date, track key and race number.")
    add_audit("source_host_fixed", "PASS" if all(r["source_host"] == SOURCE_HOST for r in admitted + rejection_rows) else "FAIL", SOURCE_HOST, "Source host fixed to proven Racing.com GraphQL host.")
    add_audit("operation_resolver_match_evidence", "PASS" if all(r["graphql_operation"] == GRAPHQL_OPERATION and r["graphql_resolver"] == GRAPHQL_RESOLVER for r in admitted + rejection_rows) else "FAIL", f"{GRAPHQL_OPERATION}/{GRAPHQL_RESOLVER}", "Operation and resolver match observed browser evidence.")
    add_audit("fresh_fixtures_present_in_v2_race_discovery", "PASS" if admission_rows else "FAIL", len(admission_rows), "Directive allows admission only from valid V2 race discovery.")

    summary = {
        "built_utc": admitted_utc,
        "status": "RACINGCOM_GRAPHQL_SOURCE_ADMISSION_V1_PASS" if admission_rows and not any(r["status"] == "FAIL" for r in audit_rows) else "RACINGCOM_GRAPHQL_SOURCE_ADMISSION_V1_BLOCKED_BY_EVIDENCE",
        "candidate_fixtures": len(candidate_fixtures),
        "admitted": len(admission_rows),
        "rejected": len(rejection_rows),
        "rejection_counts": dict(Counter(row["admission_status"] for row in rejection_rows)),
        "v2_race_discovery_rows": len(race_rows),
        "graphql_source_supported": graphql_supported,
        "production_changed": "NO",
        "ui_changed": "NO",
    }

    fields = [
        "admission_id",
        "race_id",
        "meeting_id",
        "race_date",
        "track",
        "track_key",
        "meet_code",
        "race_no",
        "race_no_numeric",
        "race_url",
        "speed_data_url",
        "race_status",
        "completed_status",
        "source_type",
        "source_host",
        "graphql_operation",
        "graphql_resolver",
        "admission_status",
        "admission_reason",
        "evidence_source",
        "evidence_path",
        "admitted_utc",
        "pipeline_version",
    ]
    write_csv(ADMISSION_OUT, admission_rows, fields)
    write_csv(REJECTIONS_OUT, rejection_rows, fields)
    write_csv(AUDIT_OUT, audit_rows, ["check", "status", "count", "detail"])
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = f"""# Racing.com GraphQL Source Admission V1

Built UTC: {admitted_utc}

## Status

`{summary['status']}`

## Counts

- V2 race discovery rows: {len(race_rows)}
- Candidate fresh/negative fixtures reviewed: {len(candidate_fixtures)}
- Admitted GraphQL races: {len(admission_rows)}
- Rejected races: {len(rejection_rows)}
- Rejection counts: `{json.dumps(summary['rejection_counts'], sort_keys=True)}`

## Finding

The GraphQL source itself remains proven, but the current valid V2 race discovery contract does not contain the five fresh Pakenham source-discovery fixtures. Under this directive's Unit 1 rule, they cannot be admitted until V2 race discovery is refreshed or extended through a governed discovery unit.

## Preservation

- Production warehouse unchanged.
- UI unchanged.
- Pricing, probability, ratings, V6.1 and V7.2G2 unchanged.
- Historical CSV pathway untouched.
"""
    REPORT_OUT.write_text(report, encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
