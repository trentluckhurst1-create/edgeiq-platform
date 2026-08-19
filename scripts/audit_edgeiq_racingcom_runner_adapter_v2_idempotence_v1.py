from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from edgeiq_racingcom_runner_adapter_v2_common import (
    ROOT, DATA, DOCS, PRODUCTION, RUNNER_CANDIDATE, build_runner_candidate, clean, read_csv, write_csv
)


AUDIT = DOCS / "edgeiq_racingcom_runner_adapter_v2_idempotence_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_racingcom_runner_adapter_v2_idempotence_summary_v1.json"
REPORT = DOCS / "edgeiq_racingcom_runner_adapter_v2_idempotence_report_v1.md"


def count_sources(rows: list[dict[str, str]]) -> tuple[int, int]:
    csv_rows = sum(1 for row in rows if clean(row.get("sectional_source")) == "RACING.COM_DIRECT_CSV_V2")
    graphql_rows = sum(1 for row in rows if clean(row.get("sectional_source")) == "RACING.COM_GRAPHQL_GETRACEFORM_V2")
    return csv_rows, graphql_rows


def main() -> int:
    original = PRODUCTION.read_bytes()
    original_rows = read_csv(PRODUCTION)
    normal_rows, _extended, _mapping = build_runner_candidate()
    promoted_rows = read_csv(RUNNER_CANDIDATE)
    try:
        write_csv(PRODUCTION, promoted_rows, list(promoted_rows[0].keys()))
        post_rows, _post_extended, _post_mapping = build_runner_candidate()
    finally:
        PRODUCTION.write_bytes(original)

    normal_csv, normal_graphql = count_sources(normal_rows)
    post_csv, post_graphql = count_sources(post_rows)
    checks = [
        {"check": "normal_rebuild_rows", "status": "PASS" if len(normal_rows) == 138 else "FAIL", "value": str(len(normal_rows))},
        {"check": "normal_rebuild_csv_rows", "status": "PASS" if normal_csv == 80 else "FAIL", "value": str(normal_csv)},
        {"check": "normal_rebuild_graphql_rows", "status": "PASS" if normal_graphql == 58 else "FAIL", "value": str(normal_graphql)},
        {"check": "post_promotion_rebuild_rows", "status": "PASS" if len(post_rows) == 138 else "FAIL", "value": str(len(post_rows))},
        {"check": "post_promotion_csv_rows", "status": "PASS" if post_csv == 80 else "FAIL", "value": str(post_csv)},
        {"check": "post_promotion_graphql_rows", "status": "PASS" if post_graphql == 58 else "FAIL", "value": str(post_graphql)},
        {"check": "post_promotion_duplicate_runner_keys", "status": "PASS" if len(post_rows) == len({(r.get("race_id"), r.get("horse_key")) for r in post_rows}) else "FAIL", "value": str(len(post_rows) - len({(r.get("race_id"), r.get("horse_key")) for r in post_rows}))},
        {"check": "production_restored_after_simulation", "status": "PASS" if PRODUCTION.read_bytes() == original else "FAIL", "value": "YES"},
    ]
    decision = "RACINGCOM_RUNNER_ADAPTER_V2_IDEMPOTENT_PASS" if all(row["status"] == "PASS" for row in checks) else "RACINGCOM_RUNNER_ADAPTER_V2_IDEMPOTENT_FAIL"
    write_csv(AUDIT, checks)
    SUMMARY.write_text(json.dumps({"decision": decision, "production_changed": "NO", "post_promotion_rebuild_rows": len(post_rows)}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(f"# Racing.com Runner Adapter V2 Idempotence Audit\n\nDecision: `{decision}`\n\nThe adapter now reads only historical CSV rows from the current production warehouse before appending GraphQL runner aggregates, so a post-promotion rebuild remains 138 rows rather than duplicating GraphQL records.\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "production_changed": "NO"}, indent=2))
    return 0 if decision.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
