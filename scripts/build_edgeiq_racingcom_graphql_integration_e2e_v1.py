from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
E2E_OUT = OUT / "edgeiq_racingcom_graphql_integration_e2e_v1.csv"
SUMMARY_OUT = OUT / "edgeiq_racingcom_graphql_integration_e2e_summary_v1.json"
REPORT_OUT = OUT / "edgeiq_racingcom_graphql_integration_e2e_report_v1.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")

EXPECTED = [
    ("race_discovery", OUT / "edgeiq_racingcom_race_discovery_v2_summary.json", "RACINGCOM_RACE_DISCOVERY_V2_PASS"),
    ("source_admission", OUT / "edgeiq_racingcom_graphql_source_admission_summary_v1.json", "RACINGCOM_GRAPHQL_SOURCE_ADMISSION_V1_PASS"),
    ("request_contract", OUT / "edgeiq_racingcom_graphql_request_contract_summary_v1.json", "RACINGCOM_GRAPHQL_REQUEST_CONTRACT_V1_PASS"),
    ("api_key_governance", OUT / "edgeiq_racingcom_graphql_api_key_governance_summary_v1.json", "RACINGCOM_GRAPHQL_API_KEY_GOVERNANCE_V1_PASS"),
    ("acquisition", OUT / "edgeiq_racingcom_graphql_acquisition_summary_v1.json", "RACINGCOM_GRAPHQL_ACQUISITION_V1_PASS"),
    ("response_validation", OUT / "edgeiq_racingcom_graphql_response_validation_summary_v1.json", "RACINGCOM_GRAPHQL_RESPONSE_VALIDATION_V1_PASS"),
    ("parser", OUT / "edgeiq_racingcom_graphql_parser_v2_summary.json", "RACINGCOM_GRAPHQL_PARSER_V2_PASS"),
    ("canonical_contract", OUT / "edgeiq_racingcom_canonical_speed_contract_summary_v1.json", "RACINGCOM_CANONICAL_SPEED_CONTRACT_V1_PASS"),
    ("integration_tests", OUT / "edgeiq_racingcom_graphql_integration_tests_summary_v1.json", "RACINGCOM_GRAPHQL_INTEGRATION_TESTS_V1_PASS"),
    ("candidate_warehouse", OUT / "edgeiq_racingcom_performance_warehouse_v2_graphql_candidate_summary.json", "RACINGCOM_GRAPHQL_CANDIDATE_WAREHOUSE_V1_PASS"),
]


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["unit", "expected_status", "actual_status", "artifact_path", "artifact_exists", "e2e_status", "detail"], extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    rows = []
    for unit, path, expected_status in EXPECTED:
        exists = path.exists()
        actual = ""
        detail = ""
        if exists:
            try:
                actual = clean(json.loads(path.read_text(encoding="utf-8")).get("status"))
            except Exception as exc:
                detail = str(exc)
        passed = exists and actual == expected_status
        rows.append(
            {
                "unit": unit,
                "expected_status": expected_status,
                "actual_status": actual,
                "artifact_path": str(path.relative_to(ROOT)),
                "artifact_exists": "YES" if exists else "NO",
                "e2e_status": "PASS" if passed else "FAIL",
                "detail": detail or ("Status matched." if passed else "Status mismatch or missing artifact."),
            }
        )
    hard_pass = all(row["e2e_status"] == "PASS" for row in rows)
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_GRAPHQL_INTEGRATION_E2E_V1_PASS" if hard_pass else "RACINGCOM_GRAPHQL_INTEGRATION_E2E_V1_FAIL",
        "units_checked": len(rows),
        "pass": sum(1 for row in rows if row["e2e_status"] == "PASS"),
        "fail": sum(1 for row in rows if row["e2e_status"] == "FAIL"),
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    write_csv(E2E_OUT, rows)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT_OUT.write_text(
        "\n".join(
            [
                "# Racing.com GraphQL Integration E2E V1",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Counts",
                f"- Units checked: `{summary['units_checked']}`",
                f"- Pass: `{summary['pass']}`",
                f"- Fail: `{summary['fail']}`",
                "",
                "## Decision",
                "",
                "The governed GraphQL source path is internally consistent and remains candidate-only.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
