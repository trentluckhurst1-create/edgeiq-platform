from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
LEDGER = DOCS / "edgeiq_racingcom_production_orchestration_dependency_ledger_v1.csv"
SUMMARY = DOCS / "edgeiq_racingcom_production_orchestration_dependency_summary_v1.json"
REPORT = DOCS / "edgeiq_racingcom_production_orchestration_dependency_report_v1.md"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stage_order", "stage", "script", "inputs", "outputs", "network", "api_key", "wired_status", "notes"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rows = [
        {"stage_order": "1", "stage": "Meeting Discovery V2", "script": "scripts/build_edgeiq_racingcom_meeting_discovery_v2.py", "inputs": "public/data/race_fields.csv and governed references", "outputs": "public/data/edgeiq_racingcom_meeting_discovery_v2.csv", "network": "NO", "api_key": "NO", "wired_status": "WIRED_EXISTING", "notes": "Active discovery foundation."},
        {"stage_order": "2", "stage": "Race Discovery V2", "script": "scripts/build_edgeiq_racingcom_race_discovery_v2.py", "inputs": "meeting discovery, race_fields, GraphQL race evidence", "outputs": "public/data/edgeiq_racingcom_race_discovery_v2.csv and docs contract copy", "network": "NO", "api_key": "NO", "wired_status": "WIRED_EXISTING", "notes": "GraphQL evidence extension already patched."},
        {"stage_order": "3", "stage": "GraphQL Race Evidence", "script": "scripts/build_edgeiq_racingcom_graphql_race_evidence_v1.py", "inputs": "race discovery contract", "outputs": "docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_graphql_race_evidence_v1.csv", "network": "NO", "api_key": "NO", "wired_status": "WIRED_EXISTING", "notes": "Direct evidence only."},
        {"stage_order": "4", "stage": "GraphQL Source Admission", "script": "scripts/build_edgeiq_racingcom_graphql_source_admission_v1.py", "inputs": "GraphQL race evidence", "outputs": "edgeiq_racingcom_graphql_source_admission_v1.csv", "network": "NO", "api_key": "NO", "wired_status": "WIRED_EXISTING", "notes": "Negative controls excluded."},
        {"stage_order": "5", "stage": "GraphQL Request Contract", "script": "scripts/build_edgeiq_racingcom_graphql_request_contract_v1.py", "inputs": "admitted GraphQL source rows", "outputs": "edgeiq_racingcom_graphql_request_contract_v1.csv", "network": "NO", "api_key": "NO", "wired_status": "WIRED_EXISTING", "notes": "Request shape only; no secret."},
        {"stage_order": "6", "stage": "GraphQL Acquisition", "script": "scripts/build_edgeiq_racingcom_graphql_acquisition_v1.py", "inputs": "request contract and EDGEIQ_RACINGCOM_WIDGET_API_KEY mapped into child process", "outputs": "raw payload cache and edgeiq_racingcom_graphql_acquisition_v1.csv", "network": "YES_NETWORK_MODE_ONLY", "api_key": "EDGEIQ_RACINGCOM_WIDGET_API_KEY", "wired_status": "WIRED_WITH_GUARD", "notes": "Offline mode reuses existing cache/acquisition ledger."},
        {"stage_order": "7", "stage": "GraphQL Response Validation", "script": "scripts/validate_edgeiq_racingcom_graphql_response_v1.py", "inputs": "acquisition ledger and cached payloads", "outputs": "edgeiq_racingcom_graphql_response_validation_v1.csv", "network": "NO", "api_key": "NO", "wired_status": "WIRED_EXISTING", "notes": "Validates cache payload semantics."},
        {"stage_order": "8", "stage": "GraphQL Segment Parser", "script": "scripts/build_edgeiq_racingcom_graphql_parser_v2.py", "inputs": "validated acquisition payloads", "outputs": "edgeiq_racingcom_graphql_parser_output_v2.csv", "network": "NO", "api_key": "NO", "wired_status": "WIRED_EXISTING", "notes": "Segment-level canonical feed."},
        {"stage_order": "9", "stage": "Canonical Segment Contract", "script": "scripts/build_edgeiq_racingcom_canonical_speed_contract_v1.py", "inputs": "historical CSV parser and GraphQL parser", "outputs": "edgeiq_racingcom_canonical_speed_contract_v1.csv", "network": "NO", "api_key": "NO", "wired_status": "WIRED_EXISTING", "notes": "Preserves mixed segment research warehouse."},
        {"stage_order": "10", "stage": "Runner Aggregate Adapter", "script": "scripts/build_edgeiq_racingcom_runner_aggregate_adapter_v2.py", "inputs": "canonical GraphQL segments and historical production CSV source rows", "outputs": "public/data/edgeiq_racingcom_performance_warehouse_v2_RUNNER_CANDIDATE.csv", "network": "NO", "api_key": "NO", "wired_status": "WIRED_EXISTING", "notes": "Idempotent after promotion."},
        {"stage_order": "11", "stage": "Candidate Gates", "script": "audit_edgeiq_racingcom_runner_candidate_*", "inputs": "runner candidate and production warehouse", "outputs": "readiness/downstream/regression audits", "network": "NO", "api_key": "NO", "wired_status": "WIRED_EXISTING", "notes": "Blocks promotion on failures."},
        {"stage_order": "12", "stage": "Atomic Promotion", "script": "scripts/run_edgeiq_racingcom_ingestion_v2_production.py", "inputs": "runner candidate", "outputs": "production warehouse after backup", "network": "NO", "api_key": "NO", "wired_status": "NEW_ORCHESTRATOR", "notes": "No-op when candidate hash matches production."},
    ]
    write_csv(LEDGER, rows)
    summary = {
        "active_production_ingestion_entry_point": "scripts/run_edgeiq_racingcom_ingestion_v2_production.py",
        "active_schedulable_command": "python -u scripts/run_edgeiq_racingcom_ingestion_v2_production.py --offline",
        "current_warehouse_writer": "scripts/build_edgeiq_racingcom_runner_aggregate_adapter_v2.py plus orchestrator atomic promotion",
        "manual_candidate_promotion_required_after_orchestrator": "NO",
        "continuation_state": "docs/performance-intelligence/racingcom-ingestion-v2/edgeiq_racingcom_production_orchestration_state_v1.json",
        "network_acquisition_enabled_by": "--network with EDGEIQ_RACINGCOM_WIDGET_API_KEY",
        "offline_cache_mode_enabled_by": "--offline",
        "api_key_environment_variable": "EDGEIQ_RACINGCOM_WIDGET_API_KEY",
        "api_key_value_written": "NO",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text("# Racing.com Production Orchestration Dependency Ledger V1\n\nThe ledger records the active governed production path and shows acquisition as the only network/API-key stage. Offline mode reuses existing cached payloads and acquisition ledgers.\n", encoding="utf-8")
    print(json.dumps({"status": "RACINGCOM_PRODUCTION_ORCHESTRATION_DEPENDENCY_LEDGER_BUILT", "stages": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
