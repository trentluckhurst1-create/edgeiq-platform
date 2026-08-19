# EDGEiQ Target 002 Standard Time Source Decision V1

## Decision

Keep the benchmark accumulation path as primary. When it has zero ready groups, bridge canonical `edgeiq_standard_time_fact_v1.csv` from `edgeiq_historical_results_warehouse_v2_graphql.csv` using winner race times grouped by track and distance.

## Guardrails

- Minimum sample remains 20.
- No condition/course/surface adjustment is added.
- Course, surface and track condition remain `NOT_AVAILABLE_IN_SOURCE` in the canonical contract.
- No fake benchmark rows are created.
- Historical warehouse rows are used only where a winner time, track and distance are present.
