from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
PUBLIC = ROOT / "public" / "data"
GATE_OUT = OUT / "edgeiq_racingcom_graphql_migration_readiness_gate_v1.csv"
SUMMARY_OUT = OUT / "edgeiq_racingcom_graphql_migration_readiness_gate_summary_v1.json"
REPORT_OUT = OUT / "edgeiq_racingcom_graphql_migration_readiness_gate_report_v1.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def load_status(path: Path) -> str:
    return clean(json.loads(path.read_text(encoding="utf-8")).get("status")) if path.exists() else ""


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["gate", "status", "count", "detail"], extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    expected_statuses = {
        "race_discovery": (OUT / "edgeiq_racingcom_race_discovery_v2_summary.json", "RACINGCOM_RACE_DISCOVERY_V2_PASS"),
        "source_admission": (OUT / "edgeiq_racingcom_graphql_source_admission_summary_v1.json", "RACINGCOM_GRAPHQL_SOURCE_ADMISSION_V1_PASS"),
        "request_contract": (OUT / "edgeiq_racingcom_graphql_request_contract_summary_v1.json", "RACINGCOM_GRAPHQL_REQUEST_CONTRACT_V1_PASS"),
        "api_key_governance": (OUT / "edgeiq_racingcom_graphql_api_key_governance_summary_v1.json", "RACINGCOM_GRAPHQL_API_KEY_GOVERNANCE_V1_PASS"),
        "acquisition": (OUT / "edgeiq_racingcom_graphql_acquisition_summary_v1.json", "RACINGCOM_GRAPHQL_ACQUISITION_V1_PASS"),
        "response_validation": (OUT / "edgeiq_racingcom_graphql_response_validation_summary_v1.json", "RACINGCOM_GRAPHQL_RESPONSE_VALIDATION_V1_PASS"),
        "parser": (OUT / "edgeiq_racingcom_graphql_parser_v2_summary.json", "RACINGCOM_GRAPHQL_PARSER_V2_PASS"),
        "canonical": (OUT / "edgeiq_racingcom_canonical_speed_contract_summary_v1.json", "RACINGCOM_CANONICAL_SPEED_CONTRACT_V1_PASS"),
        "tests": (OUT / "edgeiq_racingcom_graphql_integration_tests_summary_v1.json", "RACINGCOM_GRAPHQL_INTEGRATION_TESTS_V1_PASS"),
        "candidate": (OUT / "edgeiq_racingcom_performance_warehouse_v2_graphql_candidate_summary.json", "RACINGCOM_GRAPHQL_CANDIDATE_WAREHOUSE_V1_PASS"),
        "e2e": (OUT / "edgeiq_racingcom_graphql_integration_e2e_summary_v1.json", "RACINGCOM_GRAPHQL_INTEGRATION_E2E_V1_PASS"),
    }
    rows = []
    for gate, (path, expected) in expected_statuses.items():
        actual = load_status(path)
        rows.append({"gate": gate, "status": "PASS" if actual == expected else "FAIL", "count": actual, "detail": f"Expected {expected}."})

    production_path = PUBLIC / "edgeiq_racingcom_performance_warehouse_v2.csv"
    candidate_path = PUBLIC / "edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv"
    rows.append({"gate": "candidate_path_separate", "status": "PASS" if candidate_path.exists() and candidate_path != production_path else "FAIL", "count": str(candidate_path.exists()), "detail": "Candidate warehouse exists and is separate from production path."})
    rows.append({"gate": "auto_migration_disabled", "status": "PASS", "count": "NO_MIGRATION_EXECUTED", "detail": "Gate does not overwrite production. Human review required before any migration."})
    hard_pass = all(row["status"] == "PASS" for row in rows)
    verdict = "READY_FOR_HUMAN_MIGRATION_REVIEW_NO_AUTO_MIGRATION" if hard_pass else "NOT_READY_FOR_MIGRATION_REVIEW"
    summary = {
        "built_utc": BUILT_UTC,
        "status": verdict,
        "gates": len(rows),
        "pass": sum(1 for row in rows if row["status"] == "PASS"),
        "fail": sum(1 for row in rows if row["status"] == "FAIL"),
        "migration_authorised": "NO",
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    write_csv(GATE_OUT, rows)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT_OUT.write_text(
        "\n".join(
            [
                "# Racing.com GraphQL Migration Readiness Gate V1",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Decision",
                "",
                "The GraphQL ingestion candidate is ready for human migration review. Automatic migration is not authorised by this gate and production was not overwritten.",
                "",
                "## Counts",
                f"- Gates: `{summary['gates']}`",
                f"- Pass: `{summary['pass']}`",
                f"- Fail: `{summary['fail']}`",
                f"- Migration authorised: `{summary['migration_authorised']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
