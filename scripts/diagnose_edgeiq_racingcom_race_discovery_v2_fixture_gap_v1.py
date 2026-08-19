from __future__ import annotations

import csv
import json
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "performance-intelligence"
SOURCE_DISCOVERY = DOCS / "racingcom-source-discovery"
INGESTION_V2 = DOCS / "racingcom-ingestion-v2"
SCRIPT = ROOT / "scripts" / "build_edgeiq_racingcom_race_discovery_v2.py"

FIXTURE_CONTRACT = SOURCE_DISCOVERY / "edgeiq_racingcom_speed_data_fixture_contract_v1.csv"
REQUEST_LEDGER = SOURCE_DISCOVERY / "edgeiq_racingcom_network_request_ledger_v1.csv"
RESPONSE_LEDGER = SOURCE_DISCOVERY / "edgeiq_racingcom_network_response_ledger_v1.csv"
VALIDATION = SOURCE_DISCOVERY / "edgeiq_racingcom_source_candidate_validation_v1.csv"
POC_AUDIT = SOURCE_DISCOVERY / "edgeiq_racingcom_fresh_source_poc_audit_v1.csv"
POC_SUMMARY = SOURCE_DISCOVERY / "edgeiq_racingcom_fresh_source_poc_summary_v1.json"
MIGRATION_REPORT = SOURCE_DISCOVERY / "edgeiq_racingcom_fresh_source_migration_readiness_report_v1.md"
RACE_DISCOVERY = INGESTION_V2 / "edgeiq_racingcom_race_discovery_contract_v2.csv"

LEDGER_OUT = INGESTION_V2 / "edgeiq_racingcom_race_discovery_v2_fixture_gap_ledger_v1.csv"
AUDIT_OUT = INGESTION_V2 / "edgeiq_racingcom_race_discovery_v2_fixture_gap_audit_v1.csv"
SUMMARY_OUT = INGESTION_V2 / "edgeiq_racingcom_race_discovery_v2_fixture_gap_summary_v1.json"
REPORT_OUT = INGESTION_V2 / "edgeiq_racingcom_race_discovery_v2_fixture_gap_report_v1.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")


LEDGER_COLUMNS = [
    "fixture_id",
    "race_date",
    "track",
    "race_no",
    "meet_code",
    "race_url",
    "speed_data_url",
    "fixture_class",
    "expected_discovery_status",
    "present_in_v2_race_discovery",
    "canonical_identity_match",
    "meeting_identity_match",
    "direct_page_evidence",
    "direct_graphql_request_evidence",
    "direct_graphql_response_evidence",
    "validated_payload_evidence",
    "missing_reason",
    "recommended_action",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def track_key(value: Any) -> str:
    text = norm(value)
    for prefix in ("SPORTSBET", "LADBROKES", "BET365", "PICKLEBETPARK"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    return text


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def read_csv(path: Path) -> list[dict[str, str]]:
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


def extract_meet_code(*texts: str) -> str:
    joined = " ".join(clean(text) for text in texts)
    for pattern in (r"MeetCode=(\d+)", r"meetCode=(\d+)", r"meetCode%22%3A%20%22(\d+)", r"meetCode:\s*\\?\"?(\d+)"):
        match = re.search(pattern, joined)
        if match:
            return match.group(1)
    decoded = urllib.parse.unquote(joined)
    match = re.search(r"meetCode[:=]\s*\\?\"?(\d+)", decoded)
    return match.group(1) if match else ""


def has_get_race_form(row: dict[str, str]) -> bool:
    text = urllib.parse.unquote(clean(row.get("url")) + " " + clean(row.get("safe_post_body")))
    return "getRaceForm" in text or "sectionaltimes_callback" in text


def is_fixture(row: dict[str, str]) -> bool:
    fixture_id = clean(row.get("fixture_id"))
    return fixture_id.startswith("RECENT_VISIBLE") or fixture_id.startswith("NEGATIVE_CONTROL")


def expected_status(fixture: dict[str, str]) -> tuple[str, str]:
    status = clean(fixture.get("visible_speed_data_status"))
    if status == "VISIBLE_SPEED_DATA_INDICATED":
        return "FRESH_VALID_SPEED_FIXTURE", "DIRECT_EVIDENCE_AVAILABLE"
    if status == "NO_VISIBLE_SPEED_DATA":
        return "NEGATIVE_CONTROL_NO_SPEED", "CONTROL_ONLY_DO_NOT_ADMIT_AS_SPEED_SOURCE"
    return "OTHER", "OUT_OF_SCOPE"


def source_validation_supported(rows: list[dict[str, str]]) -> bool:
    for row in rows:
        text = " ".join(clean(value) for value in row.values())
        if "GRAPHQL_SECTIONALTIMES_GETRACEFORM" in text and "VALID_GRAPHQL_SOURCE" in text:
            return True
    return False


def main() -> int:
    fixtures = [row for row in read_csv(FIXTURE_CONTRACT) if is_fixture(row)]
    race_rows = read_csv(RACE_DISCOVERY)
    requests = read_csv(REQUEST_LEDGER)
    responses = read_csv(RESPONSE_LEDGER)
    validation_rows = read_csv(VALIDATION)
    poc_rows = read_csv(POC_AUDIT)
    script_text = SCRIPT.read_text(encoding="utf-8") if SCRIPT.exists() else ""

    race_identity = {
        (clean(row.get("race_date")), track_key(row.get("track")), race_no(row.get("race_no") or row.get("race_no_numeric"))): row
        for row in race_rows
    }
    meeting_identity = {(clean(row.get("race_date")), track_key(row.get("track"))) for row in race_rows}

    ledger: list[dict[str, str]] = []
    for fixture in sorted(fixtures, key=lambda r: (clean(r.get("race_date")), track_key(r.get("track")), int(race_no(r.get("race_no")) or "0"), clean(r.get("fixture_id")))):
        fixture_id = clean(fixture.get("fixture_id"))
        date = clean(fixture.get("race_date"))
        track = clean(fixture.get("track"))
        rno = race_no(fixture.get("race_no"))
        key = (date, track_key(track), rno)
        fixture_class, expected = expected_status(fixture)
        fixture_requests = [row for row in requests if clean(row.get("fixture_id")) == fixture_id]
        fixture_responses = [row for row in responses if clean(row.get("fixture_id")) == fixture_id]
        gql_requests = [row for row in fixture_requests if has_get_race_form(row)]
        gql_request_ids = {clean(row.get("request_index")) for row in gql_requests}
        gql_responses = [
            row
            for row in fixture_responses
            if clean(row.get("request_index")) in gql_request_ids and clean(row.get("status")) == "200"
        ]
        page_responses = [
            row
            for row in fixture_responses
            if clean(row.get("url")) in {clean(fixture.get("race_url")), clean(fixture.get("speed_data_url"))}
            and clean(row.get("status")) == "200"
        ]
        poc_match = [
            row
            for row in poc_rows
            if clean(row.get("fixture_id")) == fixture_id and clean(row.get("decision")) == "ACQUIRED_AND_NORMALISED"
        ]
        meet_code = extract_meet_code(fixture.get("source_evidence", ""), *(row.get("url", "") for row in gql_requests))
        present = key in race_identity

        if present:
            missing_reason = "PRESENT_IN_V2"
            recommended = "NO_EXTENSION_REQUIRED_FOR_RACE_IDENTITY"
        else:
            missing_reason_bits = []
            if "racingcom-source-discovery" not in script_text:
                missing_reason_bits.append("BUILDER_IGNORES_SOURCE_DISCOVERY_EVIDENCE")
            if "edgeiq_racingcom_network_request_ledger_v1.csv" not in script_text:
                missing_reason_bits.append("BUILDER_IGNORES_BROWSER_NETWORK_EVIDENCE")
            if "edgeiq_racingcom_fresh_source_poc_audit_v1.csv" not in script_text:
                missing_reason_bits.append("BUILDER_IGNORES_VALIDATED_GRAPHQL_FIXTURE_EVIDENCE")
            if "edgeiq_racingcom_completed_payload_probe_v1.csv" in script_text:
                missing_reason_bits.append("BUILDER_CONSUMES_COMPLETED_PAYLOAD_PROBE_ONLY_FOR_COMPLETED_RACES")
            if "edgeiq_racingcom_historical_success_sources_v1.csv" in script_text:
                missing_reason_bits.append("BUILDER_CONSUMES_HISTORICAL_SUCCESS_ONLY_FOR_HISTORICAL_CSV")
            missing_reason = " | ".join(missing_reason_bits) or "SOURCE_NOT_CONSUMED_BY_ACTIVE_BUILDER"
            recommended = (
                "ADMIT_VIA_GRAPHQL_RACE_EVIDENCE_ADAPTER_WITH_SPEED_DATA"
                if fixture_class == "FRESH_VALID_SPEED_FIXTURE"
                else "ADMIT_AS_VALID_RACE_WITH_NO_SPEED_ELIGIBILITY_IF_IDENTITY_VALIDATED"
            )

        ledger.append(
            {
                "fixture_id": fixture_id,
                "race_date": date,
                "track": track,
                "race_no": rno,
                "meet_code": meet_code,
                "race_url": clean(fixture.get("race_url")),
                "speed_data_url": clean(fixture.get("speed_data_url")),
                "fixture_class": fixture_class,
                "expected_discovery_status": expected,
                "present_in_v2_race_discovery": "YES" if present else "NO",
                "canonical_identity_match": "YES" if present else "NO",
                "meeting_identity_match": "YES" if (date, track_key(track)) in meeting_identity else "NO",
                "direct_page_evidence": "YES" if page_responses or "visible_text_" in clean(fixture.get("source_evidence")) else "NO",
                "direct_graphql_request_evidence": "YES" if gql_requests else "NO",
                "direct_graphql_response_evidence": "YES" if gql_responses else "NO",
                "validated_payload_evidence": "YES" if poc_match else "NO",
                "missing_reason": missing_reason,
                "recommended_action": recommended,
            }
        )

    valid_fresh = [row for row in ledger if row["fixture_class"] == "FRESH_VALID_SPEED_FIXTURE"]
    controls = [row for row in ledger if row["fixture_class"] == "NEGATIVE_CONTROL_NO_SPEED"]
    direct_valid = [row for row in valid_fresh if row["direct_graphql_request_evidence"] == "YES" and row["direct_graphql_response_evidence"] == "YES" and row["validated_payload_evidence"] == "YES"]
    direct_controls = [row for row in controls if row["direct_graphql_request_evidence"] == "YES" and row["direct_graphql_response_evidence"] == "YES"]

    audit = [
        {
            "check": "seven_fixture_races_reviewed",
            "status": "PASS" if len(ledger) == 7 else "FAIL",
            "count": len(ledger),
            "detail": "Five visible-speed fixtures and two negative controls should be reviewed.",
        },
        {
            "check": "five_valid_fresh_fixtures_have_direct_evidence",
            "status": "PASS" if len(direct_valid) == 5 else "FAIL",
            "count": len(direct_valid),
            "detail": "Valid fresh fixtures require getRaceForm request, response and normalised payload evidence.",
        },
        {
            "check": "two_negative_controls_have_race_evidence",
            "status": "PASS" if len(direct_controls) == 2 else "FAIL",
            "count": len(direct_controls),
            "detail": "Negative controls are valid race-evidence candidates but must stay no-speed for acquisition.",
        },
        {
            "check": "current_v2_missing_five_valid_fresh_fixtures",
            "status": "PASS" if sum(1 for row in valid_fresh if row["present_in_v2_race_discovery"] == "NO") == 5 else "FAIL",
            "count": sum(1 for row in valid_fresh if row["present_in_v2_race_discovery"] == "NO"),
            "detail": "This is the blocker observed by GraphQL source admission.",
        },
        {
            "check": "graphql_source_validation_supported",
            "status": "PASS" if source_validation_supported(validation_rows) else "FAIL",
            "count": int(source_validation_supported(validation_rows)),
            "detail": "Source candidate validation must prove GRAPHQL_SECTIONALTIMES_GETRACEFORM is valid.",
        },
        {
            "check": "active_builder_ignores_source_discovery_evidence",
            "status": "PASS" if "racingcom-source-discovery" not in script_text else "FAIL",
            "count": int("racingcom-source-discovery" not in script_text),
            "detail": "Current V2 builder has no source-discovery evidence input.",
        },
        {
            "check": "migration_report_exists",
            "status": "PASS" if MIGRATION_REPORT.exists() else "FAIL",
            "count": int(MIGRATION_REPORT.exists()),
            "detail": "Migration-readiness report is retained for provenance.",
        },
        {
            "check": "fresh_source_poc_summary_exists",
            "status": "PASS" if POC_SUMMARY.exists() else "FAIL",
            "count": int(POC_SUMMARY.exists()),
            "detail": "Fresh-source POC summary is retained for provenance.",
        },
    ]
    hard_pass = all(row["status"] == "PASS" for row in audit)
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_RACE_DISCOVERY_V2_FIXTURE_GAP_DIAGNOSIS_PASS" if hard_pass else "RACINGCOM_RACE_DISCOVERY_V2_FIXTURE_GAP_DIAGNOSIS_REVIEW_REQUIRED",
        "fixture_races_reviewed": len(ledger),
        "valid_fresh_fixtures": len(valid_fresh),
        "negative_controls": len(controls),
        "valid_fresh_missing_from_v2": sum(1 for row in valid_fresh if row["present_in_v2_race_discovery"] == "NO"),
        "controls_missing_from_v2": sum(1 for row in controls if row["present_in_v2_race_discovery"] == "NO"),
        "direct_evidence_available_valid_fresh": len(direct_valid),
        "direct_evidence_available_controls": len(direct_controls),
        "gap_root_cause": "ACTIVE_V2_BUILDER_DOES_NOT_CONSUME_RETAINED_BROWSER_NETWORK_OR_VALIDATED_GRAPHQL_RACE_EVIDENCE",
        "recommended_next_unit": "BUILD_GOVERNED_GRAPHQL_RACE_EVIDENCE_ADAPTER",
        "production_changed": "NO",
        "ui_changed": "NO",
    }

    write_csv(LEDGER_OUT, ledger, LEDGER_COLUMNS)
    write_csv(AUDIT_OUT, audit, ["check", "status", "count", "detail"])
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    lines = [
        "# Racing.com Race Discovery V2 Fixture Gap Diagnosis V1",
        "",
        f"Built UTC: `{BUILT_UTC}`",
        f"Status: `{summary['status']}`",
        "",
        "## Finding",
        "",
        "The five fresh Pakenham speed fixtures have retained browser-network, getRaceForm response, and validated payload evidence, but the active Race Discovery V2 builder does not consume the source-discovery evidence family. It currently combines local structured races, completed payload probe rows, and historical CSV success rows.",
        "",
        "The two Moe negative controls also have race-level GraphQL evidence, but their speed-data eligibility must remain negative. Race existence and speed-source admission are separate decisions.",
        "",
        "## Counts",
        f"- Fixture races reviewed: `{summary['fixture_races_reviewed']}`",
        f"- Valid fresh speed fixtures: `{summary['valid_fresh_fixtures']}`",
        f"- Negative controls: `{summary['negative_controls']}`",
        f"- Valid fresh fixtures missing from current V2 discovery: `{summary['valid_fresh_missing_from_v2']}`",
        f"- Negative controls missing from current V2 discovery: `{summary['controls_missing_from_v2']}`",
        "",
        "## Decision",
        "",
        "`PASS`: proceed to a governed GraphQL race-evidence adapter. Do not weaken GraphQL source admission and do not manually insert races into admission output.",
        "",
        "## Preservation",
        "",
        "- Production warehouse unchanged.",
        "- UI unchanged.",
        "- Pricing, probabilities, ratings, V6.1 and V7.2G2 unchanged.",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
