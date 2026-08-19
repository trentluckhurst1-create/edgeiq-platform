from __future__ import annotations

import json

from edgeiq_racingcom_runner_adapter_v2_common import DOCS, PRODUCTION, PRODUCTION_COLUMNS, RUNNER_CANDIDATE, columns, read_csv, write_csv


OUT = DOCS / "edgeiq_racingcom_runner_candidate_downstream_compatibility_v1.csv"
AUDIT = DOCS / "edgeiq_racingcom_runner_candidate_downstream_audit_v1.csv"
REPORT = DOCS / "edgeiq_racingcom_runner_candidate_downstream_report_v1.md"


def main() -> int:
    prod_cols = columns(PRODUCTION)
    cand_cols = columns(RUNNER_CANDIDATE)
    cand = read_csv(RUNNER_CANDIDATE)
    checks = [
        {"check": "exact_column_order", "status": "PASS" if cand_cols == prod_cols == PRODUCTION_COLUMNS else "FAIL", "value": str(len(cand_cols))},
        {"check": "runner_only_grain", "status": "PASS" if len(cand) == len({(r.get("race_id"), r.get("horse_key")) for r in cand}) else "FAIL", "value": str(len(cand))},
        {"check": "historical_plus_graphql_rows", "status": "PASS" if len(cand) == 138 else "FAIL", "value": str(len(cand))},
        {"check": "no_additive_core_columns", "status": "PASS" if len(cand_cols) == 35 else "FAIL", "value": str(len(cand_cols))},
    ]
    rows = [{"consumer_surface": "production_warehouse_drop_in", "compatibility": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL", "detail": "Core runner candidate uses exact production column order and runner grain."}]
    status = "RACINGCOM_RUNNER_CANDIDATE_DROP_IN_COMPATIBLE" if all(c["status"] == "PASS" for c in checks) else "RACINGCOM_RUNNER_CANDIDATE_DROP_IN_REVIEW"
    write_csv(OUT, rows)
    write_csv(AUDIT, checks)
    REPORT.write_text(f"# Racing.com Runner Candidate Downstream Compatibility V1\n\nStatus: `{status}`\n\nThe core candidate is a 35-column runner-only CSV. Extended segment trace data is written separately and is not part of the drop-in surface.\n", encoding="utf-8")
    print(json.dumps({"status": status, "candidate_rows": len(cand)}, indent=2))
    return 0 if status.endswith("COMPATIBLE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
