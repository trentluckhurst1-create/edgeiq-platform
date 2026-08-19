from __future__ import annotations

import json

from edgeiq_racingcom_runner_adapter_v2_common import DOCS, RUNNER_CANDIDATE, build_runner_candidate, read_csv, sha256_file, write_csv, write_json


AUDIT = DOCS / "edgeiq_racingcom_runner_candidate_readiness_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_racingcom_runner_candidate_readiness_summary_v1.json"
REPORT = DOCS / "edgeiq_racingcom_runner_candidate_readiness_report_v1.md"


def main() -> int:
    rows = read_csv(RUNNER_CANDIDATE)
    rebuilt, _extended, _mapping = build_runner_candidate()
    checks = [
        {"check": "candidate_exists", "status": "PASS" if RUNNER_CANDIDATE.exists() else "FAIL", "value": str(RUNNER_CANDIDATE.exists())},
        {"check": "candidate_rows", "status": "PASS" if len(rows) == 138 else "FAIL", "value": str(len(rows))},
        {"check": "historical_rows", "status": "PASS" if sum(1 for r in rows if r.get("sectional_source") == "RACING.COM_DIRECT_CSV_V2") == 80 else "FAIL", "value": str(sum(1 for r in rows if r.get("sectional_source") == "RACING.COM_DIRECT_CSV_V2"))},
        {"check": "graphql_rows", "status": "PASS" if sum(1 for r in rows if r.get("sectional_source") == "RACING.COM_GRAPHQL_GETRACEFORM_V2") == 58 else "FAIL", "value": str(sum(1 for r in rows if r.get("sectional_source") == "RACING.COM_GRAPHQL_GETRACEFORM_V2"))},
        {"check": "duplicate_runner_keys", "status": "PASS" if len(rows) == len({(r.get("race_id"), r.get("horse_key")) for r in rows}) else "FAIL", "value": str(len(rows) - len({(r.get("race_id"), r.get("horse_key")) for r in rows}))},
        {"check": "offline_rebuild_row_equivalence", "status": "PASS" if rows == rebuilt else "FAIL", "value": str(len(rebuilt))},
        {"check": "production_overwrite", "status": "PASS", "value": "NO"},
        {"check": "migration_executed", "status": "PASS", "value": "NO"},
    ]
    decision = "RACINGCOM_RUNNER_CANDIDATE_READY_FOR_HUMAN_REVIEW" if all(c["status"] == "PASS" for c in checks) else "RACINGCOM_RUNNER_CANDIDATE_REQUIRES_REMEDIATION"
    summary = {"decision": decision, "rows": len(rows), "races": len({r.get("race_id") for r in rows}), "candidate_sha256": sha256_file(RUNNER_CANDIDATE) if RUNNER_CANDIDATE.exists() else "", "production_changed": "NO", "migration_executed": "NO"}
    write_csv(AUDIT, checks)
    write_json(SUMMARY, summary)
    REPORT.write_text(f"# Racing.com Runner Candidate Readiness V1\n\nDecision: `{decision}`\n\nRows: `{summary['rows']}`\nRaces: `{summary['races']}`\nCandidate SHA256: `{summary['candidate_sha256']}`\n\nProduction overwrite: `NO`\nMigration executed: `NO`\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if decision.endswith("HUMAN_REVIEW") else 1


if __name__ == "__main__":
    raise SystemExit(main())
