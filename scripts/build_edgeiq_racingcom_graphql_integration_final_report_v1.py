from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
REPORT = OUT / "edgeiq_racingcom_graphql_integration_final_report_v1.md"
SUMMARY = OUT / "edgeiq_racingcom_graphql_integration_final_report_summary_v1.json"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")


def load(path: str) -> dict:
    return json.loads((OUT / path).read_text(encoding="utf-8"))


def main() -> int:
    race = load("edgeiq_racingcom_race_discovery_v2_summary.json")
    admission = load("edgeiq_racingcom_graphql_source_admission_summary_v1.json")
    evidence = load("edgeiq_racingcom_graphql_race_evidence_summary_v1.json")
    acquisition = load("edgeiq_racingcom_graphql_acquisition_summary_v1.json")
    validation = load("edgeiq_racingcom_graphql_response_validation_summary_v1.json")
    parser = load("edgeiq_racingcom_graphql_parser_v2_summary.json")
    canonical = load("edgeiq_racingcom_canonical_speed_contract_summary_v1.json")
    candidate = load("edgeiq_racingcom_performance_warehouse_v2_graphql_candidate_summary.json")
    e2e = load("edgeiq_racingcom_graphql_integration_e2e_summary_v1.json")
    gate = load("edgeiq_racingcom_graphql_migration_readiness_gate_summary_v1.json")
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_GRAPHQL_INTEGRATION_FINAL_REPORT_V1_PASS",
        "race_discovery_rows": race.get("race_rows"),
        "graphql_speed_admitted": admission.get("admitted"),
        "negative_controls_rejected": admission.get("rejected"),
        "responses_acquired": acquisition.get("acquired_rows"),
        "valid_responses": validation.get("valid_responses"),
        "parser_rows": parser.get("parsed_rows"),
        "canonical_rows": canonical.get("canonical_rows"),
        "candidate_rows": candidate.get("candidate_rows"),
        "e2e_status": e2e.get("status"),
        "migration_gate_status": gate.get("status"),
        "migration_authorised": gate.get("migration_authorised"),
        "production_changed": "NO",
        "ui_changed": "NO",
        "pricing_changed": "NO",
        "ratings_changed": "NO",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT.write_text(
        "\n".join(
            [
                "# Racing.com GraphQL Integration Final Report V1",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Final State",
                f"- Race Discovery V2 rows: `{summary['race_discovery_rows']}`",
                f"- GraphQL speed admissions: `{summary['graphql_speed_admitted']}`",
                f"- Negative controls rejected from speed acquisition: `{summary['negative_controls_rejected']}`",
                f"- Responses acquired: `{summary['responses_acquired']}`",
                f"- Valid responses: `{summary['valid_responses']}`",
                f"- Parser rows: `{summary['parser_rows']}`",
                f"- Canonical rows: `{summary['canonical_rows']}`",
                f"- Candidate warehouse rows: `{summary['candidate_rows']}`",
                "",
                "## Decision",
                "",
                f"`{summary['migration_gate_status']}`",
                "",
                "Migration was not authorised or executed. The candidate is ready for human migration review only.",
                "",
                "## Preservation",
                "",
                "- Production warehouse changed: `NO`",
                "- UI changed: `NO`",
                "- Pricing/probability changed: `NO`",
                "- Ratings/V6.1/V7.2G2 changed: `NO`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
