from __future__ import annotations

import json

from edgeiq_racingcom_runner_adapter_v2_common import (
    RUNNER_CANDIDATE, RUNNER_EXTENDED, PRODUCTION_COLUMNS, build_runner_candidate, write_csv
)


def main() -> int:
    rows, extended, _mapping = build_runner_candidate()
    write_csv(RUNNER_CANDIDATE, rows, PRODUCTION_COLUMNS)
    extra_cols = PRODUCTION_COLUMNS + ["source_format", "source_adapter", "segment_count", "sectional_segment_count", "split_segment_count", "source_payload_sha256", "aggregation_version", "aggregation_trace"]
    write_csv(RUNNER_EXTENDED, extended, extra_cols)
    historical = sum(1 for r in rows if r.get("sectional_source") == "RACING.COM_DIRECT_CSV_V2")
    graphql = sum(1 for r in rows if r.get("sectional_source") == "RACING.COM_GRAPHQL_GETRACEFORM_V2")
    duplicate = len(rows) - len({(r["race_id"], r["horse_key"]) for r in rows})
    status = "RACINGCOM_RUNNER_AGGREGATE_ADAPTER_V2_PASS" if historical == 80 and graphql == 58 and duplicate == 0 and list(rows[0].keys()) == PRODUCTION_COLUMNS else "RACINGCOM_RUNNER_AGGREGATE_ADAPTER_V2_REVIEW"
    print(json.dumps({"status": status, "rows": len(rows), "historical_rows": historical, "graphql_rows": graphql, "duplicates": duplicate}, indent=2))
    return 0 if status.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
