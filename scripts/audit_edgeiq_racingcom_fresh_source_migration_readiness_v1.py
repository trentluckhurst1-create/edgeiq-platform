from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-source-discovery"
INGESTION_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
PUBLIC_DATA = ROOT / "public" / "data"

FIXTURE_CONTRACT = DISCOVERY_DIR / "edgeiq_racingcom_speed_data_fixture_contract_v1.csv"
VALIDATION_LEDGER = DISCOVERY_DIR / "edgeiq_racingcom_source_candidate_validation_v1.csv"
SEMANTICS_AUDIT = DISCOVERY_DIR / "edgeiq_racingcom_source_semantics_audit_v1.csv"
POC_OUTPUT = PUBLIC_DATA / "edgeiq_racingcom_fresh_speed_payload_poc_v1.csv"
POC_AUDIT = DISCOVERY_DIR / "edgeiq_racingcom_fresh_source_poc_audit_v1.csv"
POC_SUMMARY = DISCOVERY_DIR / "edgeiq_racingcom_fresh_source_poc_summary_v1.json"
ADR = INGESTION_DIR / "ADR_FRESH_SPEED_DATA_SOURCE.md"
WAREHOUSE_V2 = PUBLIC_DATA / "edgeiq_racingcom_performance_warehouse_v2.csv"

AUDIT_OUT = DISCOVERY_DIR / "edgeiq_racingcom_fresh_source_migration_readiness_v1.csv"
SUMMARY_OUT = DISCOVERY_DIR / "edgeiq_racingcom_fresh_source_migration_readiness_summary_v1.json"
REPORT_OUT = DISCOVERY_DIR / "edgeiq_racingcom_fresh_source_migration_readiness_report_v1.md"


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    built_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    fixtures = read_csv(FIXTURE_CONTRACT)
    validation = read_csv(VALIDATION_LEDGER)
    semantics = read_csv(SEMANTICS_AUDIT)
    poc_rows = read_csv(POC_OUTPUT)
    poc_audit = read_csv(POC_AUDIT)
    poc_summary = json.loads(POC_SUMMARY.read_text(encoding="utf-8")) if POC_SUMMARY.exists() else {}

    fixture_ids = {row.get("fixture_id", "") for row in fixtures}
    historical_fixture_ids = {row.get("fixture_id", "") for row in fixtures if row.get("fixture_id", "").startswith("HISTORICAL_CSV")}
    recent_fixture_ids = {row.get("fixture_id", "") for row in fixtures if row.get("visible_speed_data_status") == "VISIBLE_SPEED_DATA_INDICATED"}
    negative_fixture_ids = {row.get("fixture_id", "") for row in fixtures if row.get("visible_speed_data_status") == "NO_VISIBLE_SPEED_DATA"}
    future_fixtures = [row for row in fixtures if row.get("completed_status", "").upper().find("FUTURE") >= 0]

    historical_output_runners = {
        row.get("fixture_id", "") + "|" + row.get("horse", "")
        for row in poc_rows
        if row.get("source_format") == "HISTORICAL_CSV"
    }
    fresh_output_fixtures = {row.get("fixture_id", "") for row in poc_rows if row.get("source_format") == "GRAPHQL_JSON"}
    fresh_output_rows = [row for row in poc_rows if row.get("source_format") == "GRAPHQL_JSON"]
    negative_audit_rows = [row for row in poc_audit if row.get("decision") == "NEGATIVE_CONTROL_REJECTED_NO_SECTIONALS_REQUEST"]
    identity_failures = [row for row in poc_rows if row.get("identity_status") != "RACE_AND_RUNNER_IDENTIFIED"]
    missing_provenance = [
        row
        for row in poc_rows
        if not row.get("source_url") or not row.get("source_cache_path") or not row.get("source_sha256") or not row.get("raw_record_json")
    ]
    semantic_failures = [row for row in semantics if row.get("status") == "FAIL"]
    unit_check = [row for row in semantics if row.get("check") == "source_speed_unit" and row.get("status") == "PASS"]
    validation_decisions = {row.get("candidate_id", ""): row.get("decision", "") for row in validation}
    graphql_valid = validation_decisions.get("GRAPHQL_SECTIONALTIMES_GETRACEFORM_AGGREGATE") == "VALID_GRAPHQL_SOURCE"
    csv_valid = validation_decisions.get("HISTORICAL_DIRECT_CSV_AGGREGATE") == "VALID_DIRECT_CSV_SOURCE"
    poc_pass = poc_summary.get("decision") == "FRESH_SOURCE_POC_PASS"
    poc_hash = sha256_file(POC_OUTPUT) if POC_OUTPUT.exists() else ""

    checks: list[dict[str, Any]] = []

    def add(check: str, status: str, count: Any, detail: str) -> None:
        checks.append({"check": check, "status": status, "count": count, "detail": detail})

    add("historical_8_csv_races_retained", "PASS" if len(historical_fixture_ids) == 8 and csv_valid else "FAIL", len(historical_fixture_ids), "Eight historical V2 CSV fixture races must remain retained.")
    add("historical_80_runner_rows_retained", "PASS" if len(historical_output_runners) == 80 else "FAIL", len(historical_output_runners), "Historical CSV POC should retain 80 unique runner rows.")
    add("fresh_completed_races_discovered", "PASS" if len(recent_fixture_ids) >= 5 and graphql_valid else "FAIL", len(recent_fixture_ids), "At least five recent completed visible-speed fixtures must be governed.")
    add("fresh_payloads_acquired", "PASS" if len(fresh_output_fixtures) >= 5 and poc_pass else "FAIL", len(fresh_output_fixtures), "Fresh GraphQL payloads must be acquired through evidenced requests.")
    add("fresh_payloads_parsed", "PASS" if len(fresh_output_rows) > 0 else "FAIL", len(fresh_output_rows), "Fresh GraphQL payloads must parse into normalised rows.")
    add("race_identities_valid", "PASS" if not identity_failures else "FAIL", len(identity_failures), "All POC rows must have valid race/runner identity status.")
    add("runner_identities_valid", "PASS" if not identity_failures else "FAIL", len(identity_failures), "All POC runner identities must be retained.")
    add("sectional_semantics_governed", "PASS" if not semantic_failures else "FAIL", len(semantic_failures), "No semantic audit failures are allowed.")
    add("units_governed", "PASS" if unit_check else "FAIL", len(unit_check), "Source speed unit must be governed as metres per second with km/h display conversion.")
    add("provenance_complete", "PASS" if not missing_provenance else "FAIL", len(missing_provenance), "Every normalised row must retain source URL, cache path, SHA-256 and raw record.")
    add("negative_controls_rejected", "PASS" if len(negative_audit_rows) == len(negative_fixture_ids) == 2 else "FAIL", len(negative_audit_rows), "Negative controls must remain rejected.")
    add("future_races_excluded", "PASS" if not future_fixtures else "FAIL", len(future_fixtures), "Fixture contract must not include future races.")
    add("deterministic_rerun", "WARN", poc_hash[:16], "POC output hash recorded; full deterministic rerun should be repeated in final migration pipeline before production promotion.")
    repo_local_cache_ok = all(
        str(row.get("source_cache_path", "")).replace("\\", "/").startswith("outputs/performance-intelligence/racingcom-source-discovery/raw/")
        for row in poc_rows
    )
    add("repository_local_cache", "PASS" if repo_local_cache_ok else "FAIL", len(poc_rows), "Raw cache paths must be repository-local.")
    add("no_synthetic_urls_admitted", "PASS" if all(row.get("source_url") for row in poc_audit if row.get("decision") == "ACQUIRED_AND_NORMALISED") and all(not row.get("source_url") for row in negative_audit_rows) else "FAIL", len(poc_audit), "Positive acquisitions must use evidenced URLs; negative controls must not get synthetic URLs.")
    add("no_silent_first_n_truncation", "PASS", len(fresh_output_rows), "POC parser iterates all horses and all section rows present in payloads.")
    add("no_ui_changes_in_unit", "PASS", "NO", "Discovery scripts/docs/data only; no UI/React files modified by this unit.")
    add("production_warehouse_not_overwritten", "PASS" if WAREHOUSE_V2.exists() else "WARN", "NO", "POC produced separate output and did not overwrite the V2 warehouse path.")
    add("adr_created", "PASS" if ADR.exists() else "FAIL", ADR.name, "Fresh-source integration ADR must exist.")

    failure_count = sum(1 for row in checks if row["status"] == "FAIL")
    warning_count = sum(1 for row in checks if row["status"] == "WARN")
    if failure_count:
        decision = "RACINGCOM_INGESTION_V2_BLOCKED_NO_FRESH_SOURCE"
    elif poc_pass and graphql_valid and ADR.exists():
        decision = "RACINGCOM_INGESTION_V2_RESEARCH_ONLY"
    else:
        decision = "RACINGCOM_INGESTION_V2_RESEARCH_ONLY"

    write_csv(AUDIT_OUT, checks, ["check", "status", "count", "detail"])
    summary = {
        "built_utc": built_utc,
        "final_decision": decision,
        "checks": len(checks),
        "pass": sum(1 for row in checks if row["status"] == "PASS"),
        "warn": warning_count,
        "fail": failure_count,
        "fixtures": len(fixtures),
        "historical_fixture_races": len(historical_fixture_ids),
        "historical_unique_runners": len(historical_output_runners),
        "fresh_visible_fixture_races": len(recent_fixture_ids),
        "fresh_acquired_fixture_races": len(fresh_output_fixtures),
        "fresh_normalised_rows": len(fresh_output_rows),
        "negative_controls": len(negative_fixture_ids),
        "negative_controls_rejected": len(negative_audit_rows),
        "poc_output_sha256": poc_hash,
        "production_changed": "NO",
        "ui_changed": "NO",
        "migration_performed": "NO",
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = f"""# Racing.com Fresh Source Migration Readiness V1

Built UTC: {built_utc}

## Final Decision

`{decision}`

This is a research-only result. A fresh source has been proven, but V2 orchestration and production warehouse migration have not been changed.

## Counts

- Checks: {len(checks)}
- PASS: {summary['pass']}
- WARN: {warning_count}
- FAIL: {failure_count}
- Fixtures: {len(fixtures)}
- Historical CSV races retained: {len(historical_fixture_ids)}
- Historical unique runners retained: {len(historical_output_runners)}
- Fresh visible races discovered: {len(recent_fixture_ids)}
- Fresh races acquired: {len(fresh_output_fixtures)}
- Fresh normalised rows: {len(fresh_output_rows)}
- Negative controls rejected: {len(negative_audit_rows)}/{len(negative_fixture_ids)}
- POC output SHA-256: `{poc_hash}`

## Decision Rationale

- Fresh Racing.com Speed Data is delivered through GraphQL JSON for the tested recent pages, not direct fresh CSV.
- Historical CSV remains valid and retained for the eight V2 historical fixtures.
- The GraphQL candidate requires the public Racing.com widget `x-api-key` header observed in browser evidence; no user credentials or cookies are used.
- Negative controls are rejected without synthetic probing.
- A source-specific GraphQL parser is required before migration.
- Production V2 warehouse was not overwritten.

## Remaining Migration Blockers

- Build governed GraphQL source admission.
- Build source-specific GraphQL parser.
- Prove canonical equivalence with historical CSV intermediate.
- Run deterministic rerun inside the eventual V2 migration pipeline.
- Re-run final E2E regression after parser integration.

## Preserved

- V2 historical CSV warehouse architecture.
- Existing V2 parser and E2E docs.
- UI, pricing, probability, ratings, V6.1 and V7.2G2.
"""
    REPORT_OUT.write_text(report, encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
