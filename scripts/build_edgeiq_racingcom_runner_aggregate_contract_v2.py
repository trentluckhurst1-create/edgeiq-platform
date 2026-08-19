from __future__ import annotations

import json
from pathlib import Path

from edgeiq_racingcom_runner_adapter_v2_common import DOCS, PRODUCTION_COLUMNS, write_csv


DOC = DOCS / "RUNNER_AGGREGATE_CONTRACT_V2.md"
CSV = DOCS / "edgeiq_racingcom_runner_aggregate_field_contract_v2.csv"


def main() -> int:
    rows = []
    for col in PRODUCTION_COLUMNS:
        if col in {"warehouse_record_id", "race_id", "race_date", "track", "state", "race_no", "distance", "horse", "horse_key", "barrier"}:
            family = "IDENTITY"
            csv_rule = "SOURCE_PROVIDED_RUNNER_AGGREGATE"
            graphql_rule = "SOURCE_OR_GROUP_IDENTITY"
        elif col in {"last200", "last400", "last600", "last_200", "last_400", "last_600"}:
            family = "SECTIONAL"
            csv_rule = "SOURCE_PROVIDED_RUNNER_AGGREGATE"
            graphql_rule = "DERIVED_EQUIVALENT_FROM_FINAL_SPLIT_SUMS"
        elif col in {"early_speed", "mid_speed", "late_speed", "peak_speed", "avg_speed", "race_time"}:
            family = "SPEED"
            csv_rule = "SOURCE_PROVIDED_RUNNER_AGGREGATE"
            graphql_rule = "DERIVED_EQUIVALENT_FROM_SPLIT_SPEEDS_AND_RACE_TIME"
        elif col in {"tempo_grade", "pace_profile"}:
            family = "STATUS"
            csv_rule = "SOURCE_OR_BLANK"
            graphql_rule = "SOURCE_SPECIFIC_STATUS_OR_BLANK"
        else:
            family = "PROVENANCE"
            csv_rule = "BUILDER_PROVENANCE"
            graphql_rule = "GRAPHQL_ACQUISITION_PROVENANCE"
        rows.append({
            "column_name": col,
            "production_order": str(len(rows) + 1),
            "field_family": family,
            "runner_grain_required": "YES",
            "historical_csv_rule": csv_rule,
            "graphql_runner_adapter_rule": graphql_rule,
            "drop_in_required": "YES",
            "unresolved": "NO",
        })
    write_csv(CSV, rows)
    DOC.write_text("\n".join([
        "# Racing.com Runner Aggregate Contract V2",
        "",
        "This contract defines the production-compatible runner aggregate surface for Racing.com performance intelligence.",
        "",
        "## Architecture",
        "",
        "`RAW GRAPHQL SEGMENTS -> CANONICAL SEGMENT CONTRACT -> RUNNER AGGREGATE ADAPTER -> PRODUCTION-COMPATIBLE CANDIDATE`",
        "",
        "The canonical segment warehouse is retained as research/source truth. The runner aggregate adapter is the only layer permitted to convert segment rows into the 35-column production-compatible runner warehouse surface.",
        "",
        "## Hard Contract",
        "",
        "- Grain: one row per `race_id + horse_key`.",
        "- Core candidate columns: exact production V2 column names and order.",
        "- Historical CSV rows: field-level pass-through from existing production warehouse.",
        "- GraphQL rows: deterministic derived-equivalent aggregation from source split/sectional segments.",
        "- Production overwrite: not permitted by this contract.",
        "",
        "## GraphQL Derived-Equivalent Rules",
        "",
        "- `last200`: `200m-FINISH` split time.",
        "- `last400`: `400m-200m + 200m-FINISH`.",
        "- `last600`: `600m-400m + 400m-200m + 200m-FINISH`.",
        "- `early_speed`, `mid_speed`, `late_speed`: ordered split speed thirds from race start to finish.",
        "- `peak_speed`: max split average speed.",
        "- `avg_speed`: distance run divided by race time when available.",
        "",
        "These GraphQL rules are source-specific adapter semantics, not evidence that the historical CSV builder performed the same calculation.",
    ]) + "\n", encoding="utf-8")
    print(json.dumps({"status": "RUNNER_AGGREGATE_CONTRACT_V2_BUILT", "fields": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
