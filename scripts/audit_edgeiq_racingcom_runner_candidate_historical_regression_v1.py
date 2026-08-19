from __future__ import annotations

import json
from pathlib import Path

from edgeiq_racingcom_runner_adapter_v2_common import DATA, DOCS, PRODUCTION, PRODUCTION_COLUMNS, RUNNER_CANDIDATE, clean, key, read_csv, write_csv


OUT = DOCS / "edgeiq_racingcom_runner_candidate_historical_regression_v1.csv"
CHANGES = DOCS / "edgeiq_racingcom_runner_candidate_historical_changes_v1.csv"
AUDIT = DOCS / "edgeiq_racingcom_runner_candidate_historical_audit_v1.csv"
REPORT = DOCS / "edgeiq_racingcom_runner_candidate_historical_report_v1.md"


def main() -> int:
    prod_all = read_csv(PRODUCTION)
    prod = [row for row in prod_all if row.get("sectional_source") == "RACING.COM_DIRECT_CSV_V2"]
    cand = read_csv(RUNNER_CANDIDATE)
    cand_by_key = {key(r): r for r in cand if clean(r.get("sectional_source")) == "RACING.COM_DIRECT_CSV_V2"}
    rows = []
    changes = []
    for row in prod:
        c = cand_by_key.get(key(row))
        matched = c is not None
        diffs = 0
        if c:
            for col in PRODUCTION_COLUMNS:
                if clean(row.get(col)) != clean(c.get(col)):
                    diffs += 1
                    changes.append({"race_id": row["race_id"], "horse_key": row["horse_key"], "column": col, "production_value": clean(row.get(col)), "candidate_value": clean(c.get(col))})
        rows.append({"race_id": row.get("race_id"), "horse_key": row.get("horse_key"), "matched": "YES" if matched else "NO", "changed_columns": str(diffs)})
    audit = [
        {"check": "production_historical_rows", "status": "PASS" if len(prod) == 80 else "FAIL", "value": str(len(prod))},
        {"check": "production_total_rows_supported", "status": "PASS" if len(prod_all) in {80, 138} else "FAIL", "value": str(len(prod_all))},
        {"check": "historical_candidate_rows", "status": "PASS" if len(cand_by_key) == 80 else "FAIL", "value": str(len(cand_by_key))},
        {"check": "changed_fields", "status": "PASS" if len(changes) == 0 else "FAIL", "value": str(len(changes))},
        {"check": "column_order", "status": "PASS" if list(read_csv(RUNNER_CANDIDATE)[0].keys()) == PRODUCTION_COLUMNS else "FAIL", "value": "35"},
    ]
    status = "RACINGCOM_HISTORICAL_RUNNER_COMPATIBILITY_PASS" if all(r["status"] == "PASS" for r in audit) else "RACINGCOM_HISTORICAL_RUNNER_COMPATIBILITY_FAIL"
    write_csv(OUT, rows)
    write_csv(CHANGES, changes, ["race_id", "horse_key", "column", "production_value", "candidate_value"])
    write_csv(AUDIT, audit)
    REPORT.write_text(f"# Racing.com Runner Candidate Historical Regression V1\n\nStatus: `{status}`\n\nHistorical production rows are retained field-for-field in the runner candidate. Changed fields: `{len(changes)}`.\n", encoding="utf-8")
    print(json.dumps({"status": status, "changed_fields": len(changes)}, indent=2))
    return 0 if status.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
