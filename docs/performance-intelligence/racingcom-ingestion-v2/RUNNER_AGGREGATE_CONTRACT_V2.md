# Racing.com Runner Aggregate Contract V2

This contract defines the production-compatible runner aggregate surface for Racing.com performance intelligence.

## Architecture

`RAW GRAPHQL SEGMENTS -> CANONICAL SEGMENT CONTRACT -> RUNNER AGGREGATE ADAPTER -> PRODUCTION-COMPATIBLE CANDIDATE`

The canonical segment warehouse is retained as research/source truth. The runner aggregate adapter is the only layer permitted to convert segment rows into the 35-column production-compatible runner warehouse surface.

## Hard Contract

- Grain: one row per `race_id + horse_key`.
- Core candidate columns: exact production V2 column names and order.
- Historical CSV rows: field-level pass-through from existing production warehouse.
- GraphQL rows: deterministic derived-equivalent aggregation from source split/sectional segments.
- Production overwrite: not permitted by this contract.

## GraphQL Derived-Equivalent Rules

- `last200`: `200m-FINISH` split time.
- `last400`: `400m-200m + 200m-FINISH`.
- `last600`: `600m-400m + 400m-200m + 200m-FINISH`.
- `early_speed`, `mid_speed`, `late_speed`: ordered split speed thirds from race start to finish.
- `peak_speed`: max split average speed.
- `avg_speed`: distance run divided by race time when available.

These GraphQL rules are source-specific adapter semantics, not evidence that the historical CSV builder performed the same calculation.
