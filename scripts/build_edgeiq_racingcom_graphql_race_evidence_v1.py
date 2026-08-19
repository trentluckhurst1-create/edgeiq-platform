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
SOURCE = DOCS / "racingcom-source-discovery"
OUT = DOCS / "racingcom-ingestion-v2"

FIXTURE_CONTRACT = SOURCE / "edgeiq_racingcom_speed_data_fixture_contract_v1.csv"
REQUEST_LEDGER = SOURCE / "edgeiq_racingcom_network_request_ledger_v1.csv"
RESPONSE_LEDGER = SOURCE / "edgeiq_racingcom_network_response_ledger_v1.csv"
VALIDATION = SOURCE / "edgeiq_racingcom_source_candidate_validation_v1.csv"
POC_AUDIT = SOURCE / "edgeiq_racingcom_fresh_source_poc_audit_v1.csv"
POC_SUMMARY = SOURCE / "edgeiq_racingcom_fresh_source_poc_summary_v1.json"
MIGRATION_REPORT = SOURCE / "edgeiq_racingcom_fresh_source_migration_readiness_report_v1.md"

EVIDENCE_OUT = OUT / "edgeiq_racingcom_graphql_race_evidence_v1.csv"
REJECTIONS_OUT = OUT / "edgeiq_racingcom_graphql_race_evidence_rejections_v1.csv"
AUDIT_OUT = OUT / "edgeiq_racingcom_graphql_race_evidence_audit_v1.csv"
SUMMARY_OUT = OUT / "edgeiq_racingcom_graphql_race_evidence_summary_v1.json"
REPORT_OUT = OUT / "edgeiq_racingcom_graphql_race_evidence_report_v1.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")
GRAPHQL_HOST = "graphql.rmdprod.racing.com"
GRAPHQL_OPERATION = "sectionaltimes_callback"
GRAPHQL_RESOLVER = "getRaceForm"
PIPELINE_VERSION = "edgeiq_racingcom_graphql_race_evidence_v1"

EVIDENCE_COLUMNS = [
    "evidence_id",
    "fixture_id",
    "race_date",
    "track",
    "track_key",
    "meet_code",
    "race_no",
    "race_no_numeric",
    "race_url",
    "speed_data_url",
    "graphql_host",
    "graphql_operation",
    "graphql_resolver",
    "request_id",
    "response_id",
    "payload_path",
    "payload_sha256",
    "race_identity_validated",
    "runner_population_present",
    "sectional_population_present",
    "negative_control",
    "evidence_status",
    "evidence_strength",
    "source_artifacts",
    "created_utc",
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


def decoded_request_text(row: dict[str, str]) -> str:
    return urllib.parse.unquote(clean(row.get("url")) + " " + clean(row.get("safe_post_body")))


def is_sectional_request(row: dict[str, str]) -> bool:
    return "sectionaltimes_callback" in decoded_request_text(row)


def is_get_race_form_request(row: dict[str, str]) -> bool:
    return "getRaceForm" in decoded_request_text(row)


def extract_meet_code(*texts: str) -> str:
    joined = " ".join(clean(text) for text in texts)
    decoded = urllib.parse.unquote(joined)
    for pattern in (r"MeetCode=(\d+)", r"meetCode=(\d+)", r'meetCode:\s*"?(\d+)"?', r'meetCode%22%3A%20%22(\d+)'):
        match = re.search(pattern, decoded)
        if match:
            return match.group(1)
    return ""


def source_supported(rows: list[dict[str, str]]) -> bool:
    for row in rows:
        text = " ".join(clean(value) for value in row.values())
        if "GRAPHQL_SECTIONALTIMES_GETRACEFORM" in text and "VALID_GRAPHQL_SOURCE" in text:
            return True
    return False


def first_response_for_request(responses: list[dict[str, str]], request_id: str) -> dict[str, str] | None:
    matches = [row for row in responses if clean(row.get("request_index")) == request_id and clean(row.get("status")) == "200"]
    return sorted(matches, key=lambda row: int(clean(row.get("response_index")) or "0"))[0] if matches else None


def main() -> int:
    fixtures = [
        row
        for row in read_csv(FIXTURE_CONTRACT)
        if clean(row.get("fixture_id")).startswith("RECENT_VISIBLE") or clean(row.get("fixture_id")).startswith("NEGATIVE_CONTROL")
    ]
    requests = read_csv(REQUEST_LEDGER)
    responses = read_csv(RESPONSE_LEDGER)
    validation = read_csv(VALIDATION)
    poc_rows = read_csv(POC_AUDIT)
    validation_ok = source_supported(validation)

    evidence: list[dict[str, str]] = []
    rejections: list[dict[str, str]] = []

    for fixture in sorted(fixtures, key=lambda r: (clean(r.get("race_date")), track_key(r.get("track")), int(race_no(r.get("race_no")) or "0"), clean(r.get("fixture_id")))):
        fixture_id = clean(fixture.get("fixture_id"))
        date = clean(fixture.get("race_date"))
        track = clean(fixture.get("track"))
        rno = race_no(fixture.get("race_no"))
        fixture_requests = [row for row in requests if clean(row.get("fixture_id")) == fixture_id]
        fixture_responses = [row for row in responses if clean(row.get("fixture_id")) == fixture_id]
        sectional_requests = [row for row in fixture_requests if is_sectional_request(row)]
        race_form_requests = [row for row in fixture_requests if is_get_race_form_request(row)]
        selected_request = sorted(sectional_requests or race_form_requests, key=lambda row: int(clean(row.get("request_index")) or "0"))[0] if (sectional_requests or race_form_requests) else None
        selected_response = first_response_for_request(fixture_responses, clean(selected_request.get("request_index")) if selected_request else "") if selected_request else None
        poc_match = [
            row
            for row in poc_rows
            if clean(row.get("fixture_id")) == fixture_id and clean(row.get("decision")) == "ACQUIRED_AND_NORMALISED"
        ]
        negative_control = "YES" if clean(fixture.get("visible_speed_data_status")) == "NO_VISIBLE_SPEED_DATA" else "NO"
        speed_payload = bool(poc_match and sectional_requests and validation_ok)
        race_identity_validated = bool(selected_request and selected_response)
        meet_code = extract_meet_code(fixture.get("source_evidence", ""), clean(selected_request.get("url")) if selected_request else "")

        if speed_payload:
            payload_path = clean(poc_match[0].get("cache_path"))
            payload_sha = clean(poc_match[0].get("sha256"))
            runner_population = "YES" if int(clean(poc_match[0].get("runner_count")) or "0") > 0 else "NO"
            sectional_population = "YES" if int(clean(poc_match[0].get("sectional_count")) or "0") > 0 else "NO"
            evidence_status = "VALIDATED_GRAPHQL_RACE_WITH_SPEED"
            evidence_strength = "STRONG"
        elif race_identity_validated and negative_control == "YES":
            payload_path = clean(selected_response.get("cache_path")) if selected_response else ""
            payload_sha = clean(selected_response.get("sha256")) if selected_response else ""
            runner_population = "UNKNOWN"
            sectional_population = "NO"
            evidence_status = "VALIDATED_GRAPHQL_RACE_NO_SPEED"
            evidence_strength = "MEDIUM"
        elif race_identity_validated:
            payload_path = clean(selected_response.get("cache_path")) if selected_response else ""
            payload_sha = clean(selected_response.get("sha256")) if selected_response else ""
            runner_population = "UNKNOWN"
            sectional_population = "UNKNOWN"
            evidence_status = "VALIDATED_RACE_PAGE_ONLY"
            evidence_strength = "MEDIUM"
        else:
            rejections.append(
                {
                    "fixture_id": fixture_id,
                    "race_date": date,
                    "track": track,
                    "race_no": rno,
                    "rejection_status": "REJECTED_MISSING_SOURCE_EVIDENCE",
                    "rejection_reason": "No retained getRaceForm request/response pair was found.",
                }
            )
            continue

        source_artifacts = [
            str(FIXTURE_CONTRACT.relative_to(ROOT)),
            str(REQUEST_LEDGER.relative_to(ROOT)),
            str(RESPONSE_LEDGER.relative_to(ROOT)),
        ]
        if poc_match:
            source_artifacts.append(str(POC_AUDIT.relative_to(ROOT)))
        if POC_SUMMARY.exists():
            source_artifacts.append(str(POC_SUMMARY.relative_to(ROOT)))
        if MIGRATION_REPORT.exists():
            source_artifacts.append(str(MIGRATION_REPORT.relative_to(ROOT)))

        evidence.append(
            {
                "evidence_id": f"{date}_{track_key(track)}_R{rno}_{evidence_status}",
                "fixture_id": fixture_id,
                "race_date": date,
                "track": track,
                "track_key": track_key(track),
                "meet_code": meet_code,
                "race_no": rno,
                "race_no_numeric": rno,
                "race_url": clean(fixture.get("race_url")),
                "speed_data_url": clean(fixture.get("speed_data_url")),
                "graphql_host": GRAPHQL_HOST,
                "graphql_operation": GRAPHQL_OPERATION,
                "graphql_resolver": GRAPHQL_RESOLVER,
                "request_id": clean(selected_request.get("request_index")) if selected_request else "",
                "response_id": clean(selected_response.get("response_index")) if selected_response else "",
                "payload_path": payload_path,
                "payload_sha256": payload_sha,
                "race_identity_validated": "YES" if race_identity_validated else "NO",
                "runner_population_present": runner_population,
                "sectional_population_present": sectional_population,
                "negative_control": negative_control,
                "evidence_status": evidence_status,
                "evidence_strength": evidence_strength,
                "source_artifacts": " | ".join(source_artifacts),
                "created_utc": BUILT_UTC,
            }
        )

    audit = [
        {
            "check": "evidence_rows_expected",
            "status": "PASS" if len(evidence) == 7 else "FAIL",
            "count": len(evidence),
            "detail": "Seven fixture races should emit governed race evidence.",
        },
        {
            "check": "five_validated_graphql_races_with_speed",
            "status": "PASS" if sum(1 for row in evidence if row["evidence_status"] == "VALIDATED_GRAPHQL_RACE_WITH_SPEED") == 5 else "FAIL",
            "count": sum(1 for row in evidence if row["evidence_status"] == "VALIDATED_GRAPHQL_RACE_WITH_SPEED"),
            "detail": "Five Pakenham fixtures should have validated speed payload evidence.",
        },
        {
            "check": "two_validated_graphql_races_no_speed",
            "status": "PASS" if sum(1 for row in evidence if row["evidence_status"] == "VALIDATED_GRAPHQL_RACE_NO_SPEED") == 2 else "FAIL",
            "count": sum(1 for row in evidence if row["evidence_status"] == "VALIDATED_GRAPHQL_RACE_NO_SPEED"),
            "detail": "Two Moe controls should be valid races but no-speed for acquisition.",
        },
        {
            "check": "all_evidence_has_meet_code",
            "status": "PASS" if all(row["meet_code"] for row in evidence) else "FAIL",
            "count": sum(1 for row in evidence if row["meet_code"]),
            "detail": "Meet code must be directly evidenced.",
        },
        {
            "check": "all_evidence_has_request_response",
            "status": "PASS" if all(row["request_id"] and row["response_id"] for row in evidence) else "FAIL",
            "count": sum(1 for row in evidence if row["request_id"] and row["response_id"]),
            "detail": "Every evidence race must preserve request and response IDs.",
        },
        {
            "check": "speed_payload_hashes_retained",
            "status": "PASS" if all(row["payload_sha256"] for row in evidence if row["evidence_status"] == "VALIDATED_GRAPHQL_RACE_WITH_SPEED") else "FAIL",
            "count": sum(1 for row in evidence if row["evidence_status"] == "VALIDATED_GRAPHQL_RACE_WITH_SPEED" and row["payload_sha256"]),
            "detail": "Validated speed payloads must retain SHA256.",
        },
        {
            "check": "no_rejections",
            "status": "PASS" if not rejections else "FAIL",
            "count": len(rejections),
            "detail": "No fixture evidence should be rejected in this adapter.",
        },
    ]
    hard_pass = all(row["status"] == "PASS" for row in audit)
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_GRAPHQL_RACE_EVIDENCE_V1_PASS" if hard_pass else "RACINGCOM_GRAPHQL_RACE_EVIDENCE_V1_REVIEW_REQUIRED",
        "evidence_rows": len(evidence),
        "rejections": len(rejections),
        "validated_graphql_race_with_speed": sum(1 for row in evidence if row["evidence_status"] == "VALIDATED_GRAPHQL_RACE_WITH_SPEED"),
        "validated_graphql_race_no_speed": sum(1 for row in evidence if row["evidence_status"] == "VALIDATED_GRAPHQL_RACE_NO_SPEED"),
        "graphql_host": GRAPHQL_HOST,
        "graphql_operation": GRAPHQL_OPERATION,
        "graphql_resolver": GRAPHQL_RESOLVER,
        "production_changed": "NO",
        "ui_changed": "NO",
    }

    write_csv(EVIDENCE_OUT, evidence, EVIDENCE_COLUMNS)
    write_csv(REJECTIONS_OUT, rejections, ["fixture_id", "race_date", "track", "race_no", "rejection_status", "rejection_reason"])
    write_csv(AUDIT_OUT, audit, ["check", "status", "count", "detail"])
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    lines = [
        "# Racing.com GraphQL Race Evidence V1",
        "",
        f"Built UTC: `{BUILT_UTC}`",
        f"Status: `{summary['status']}`",
        "",
        "## Counts",
        f"- Evidence rows: `{summary['evidence_rows']}`",
        f"- Rejections: `{summary['rejections']}`",
        f"- `VALIDATED_GRAPHQL_RACE_WITH_SPEED`: `{summary['validated_graphql_race_with_speed']}`",
        f"- `VALIDATED_GRAPHQL_RACE_NO_SPEED`: `{summary['validated_graphql_race_no_speed']}`",
        "",
        "## Governance",
        "",
        "The adapter emits race evidence only. Speed-data acquisition eligibility remains separate and is controlled by GraphQL source admission.",
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
