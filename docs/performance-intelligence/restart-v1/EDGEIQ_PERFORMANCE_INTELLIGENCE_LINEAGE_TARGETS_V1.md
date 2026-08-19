# EDGEIQ Performance Intelligence Lineage Targets V1

## Verdict

**PASS**

This unit identifies the exact canonical zero-row outputs discovered by Restart Unit 001.

No builder, threshold, source dataset, warehouse,
runtime dataset or React file was changed.

## Identified Targets

| Target | Canonical output | Status | Rows | Columns | Size bytes |
|---:|---|---|---:|---:|---:|
| 1 | `public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv` | HEADER_ONLY | 0 | 30 | 876 |
| 2 | `public/data/edgeiq_standard_time_fact_v1.csv` | HEADER_ONLY | 0 | 25 | 523 |

## Governed Next Action

**TRACE_TARGET_001_PRODUCING_BUILDER**

The next unit must identify the exact producer, orchestrator and declared inputs for Target 001.

No repair is authorised until the first proven upstream collapse point is identified.
