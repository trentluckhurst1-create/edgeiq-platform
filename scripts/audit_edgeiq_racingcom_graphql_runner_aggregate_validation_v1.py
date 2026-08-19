from __future__ import annotations

import json
from collections import Counter

from edgeiq_racingcom_runner_adapter_v2_common import DOCS, GRAPHQL_PARSER, RUNNER_CANDIDATE, build_runner_candidate, clean, read_csv, write_csv


VALIDATION = DOCS / "edgeiq_racingcom_graphql_runner_aggregate_validation_v1.csv"
MAPPING = DOCS / "edgeiq_racingcom_graphql_runner_segment_mapping_v1.csv"
AUDIT = DOCS / "edgeiq_racingcom_graphql_runner_aggregate_audit_v1.csv"
REPORT = DOCS / "edgeiq_racingcom_graphql_runner_aggregate_report_v1.md"


def main() -> int:
    candidate = [r for r in read_csv(RUNNER_CANDIDATE) if clean(r.get("sectional_source")) == "RACING.COM_GRAPHQL_GETRACEFORM_V2"]
    parser = read_csv(GRAPHQL_PARSER)
    _, _, mapping = build_runner_candidate()
    validation = []
    for row in candidate:
        runner_segments = [m for m in mapping if m["aggregate_record_id"] == row["warehouse_record_id"]]
        validation.append({
            "warehouse_record_id": row["warehouse_record_id"],
            "race_id": row["race_id"],
            "horse": row["horse"],
            "segment_rows": str(len(runner_segments)),
            "last200_available": "YES" if clean(row.get("last200")) else "NO",
            "last400_available": "YES" if clean(row.get("last400")) else "NO",
            "last600_available": "YES" if clean(row.get("last600")) else "NO",
            "speed_available": "YES" if clean(row.get("avg_speed")) else "NO",
            "barrier_available": "YES" if clean(row.get("barrier")) else "NO",
        })
    missing_core = sum(1 for r in validation if "NO" in [r["last200_available"], r["last400_available"], r["last600_available"], r["speed_available"], r["barrier_available"]])
    dup = len(candidate) - len({(r["race_id"], r["horse_key"]) for r in candidate})
    races = len({r["race_id"] for r in candidate})
    audit = [
        {"check": "graphql_parser_segment_rows", "status": "PASS" if len(parser) == 898 else "FAIL", "value": str(len(parser))},
        {"check": "graphql_runner_rows", "status": "PASS" if len(candidate) == 58 else "FAIL", "value": str(len(candidate))},
        {"check": "graphql_races", "status": "PASS" if races == 5 else "FAIL", "value": str(races)},
        {"check": "duplicate_runner_keys", "status": "PASS" if dup == 0 else "FAIL", "value": str(dup)},
        {"check": "missing_core_aggregate_fields", "status": "PASS" if missing_core == 0 else "FAIL", "value": str(missing_core)},
    ]
    status = "RACINGCOM_GRAPHQL_RUNNER_AGGREGATE_VALIDATION_PASS" if all(r["status"] == "PASS" for r in audit) else "RACINGCOM_GRAPHQL_RUNNER_AGGREGATE_VALIDATION_REVIEW"
    write_csv(VALIDATION, validation)
    write_csv(MAPPING, mapping)
    write_csv(AUDIT, audit)
    REPORT.write_text(f"# Racing.com GraphQL Runner Aggregate Validation V1\n\nStatus: `{status}`\n\nValidated `{len(candidate)}` runner aggregates from `{len(parser)}` segment rows across `{races}` races. Negative-control races remain excluded from candidate output.\n", encoding="utf-8")
    print(json.dumps({"status": status, "graphql_runner_rows": len(candidate), "segment_rows": len(parser)}, indent=2))
    return 0 if status.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
