# EDGEiQ Timing Contract Migration V1

Generated UTC: `2026-07-30T07:44:11Z`

## Old Authority
`public/data/edgeiq_benchmark_observation_fact_v1.csv` is retained and copied to `public/data/edgeiq_benchmark_observation_current_window_v2_1.csv` as the current-window Racing.com speed-observation role.

## New Authority
`public/data/edgeiq_canonical_historical_timing_warehouse_v1.csv` promoted from `public/data/edgeiq_recovered_timing_warehouse_v1.csv`.

## Reason
Recovered governed historical timing warehouse has 70,308 numeric-positive timed races; active benchmark observation contract is a 39-row current-window Racing.com speed feed and is incompatible as historical timing authority.

## Producers
- `scripts/build_edgeiq_timing_warehouse_recovery_v1.py`
- `scripts/promote_edgeiq_timing_warehouse_canonical_v1.py`
- `scripts/run_edgeiq_victoria_performance_intelligence_refresh_v1.py`

## Consumers
See `docs/performance-intelligence/restart-v1/timing-canonical-promotion-v1/edgeiq_timing_downstream_consumer_graph_v1.csv` and `docs/performance-intelligence/restart-v1/timing-canonical-promotion-v1/edgeiq_timing_downstream_builder_dependency_graph_v1.csv`.

## Rollback
Archive: `docs/performance-intelligence/restart-v1/timing-canonical-promotion-v1/archive/20260730T074411Z`. Restore archived files to reverse promotion.

## Schema Comparison
Old fields: `33`
New fields: `31`
Shared fields: `5`

## Contract Comparison
The old contract is current-window sectional speed evidence. The new authority is canonical historical timing evidence with explicit seconds, identity, unit semantics, surface/condition and recovery status.

## Migration Impact
Standard Time, Race Time Delta, Lengths v Standard and Performance Base now originate from the recovered governed historical timing warehouse; later stages rebuild through existing governance gates.
