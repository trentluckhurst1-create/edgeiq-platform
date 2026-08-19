# EDGEiQ Victoria Live Pipeline Forensics V1

Status: PIPELINE_FORENSICS_BLOCKER_FOUND
Stages audited: 14
Passing stages: 12
Blocked stages: 2
First zero stage: Projected Performance
First missing stage: NONE
First blocker: Projected Performance

## Stage Results

### 1. Results Warehouse
- Status: PASS
- Builder: scripts/build_edgeiq_daily_official_results_ingestion_v1.py (YES)
- Output: public/data/edgeiq_canonical_results_truth_v1.csv (YES)
- Rows: 47887
- Reason: primary output exists with non-zero rows

### 2. Timed Races
- Status: PASS
- Builder: scripts/promote_edgeiq_timing_warehouse_canonical_v1.py (YES)
- Output: public/data/edgeiq_canonical_historical_timing_warehouse_v1.csv (YES)
- Rows: 70319
- Reason: primary output exists with non-zero rows

### 3. Standard Times
- Status: PASS
- Builder: scripts/build_edgeiq_standard_time_engine_v1.py (YES)
- Output: public/data/edgeiq_standard_time_fact_v1.csv (YES)
- Rows: 695
- Reason: primary output exists with non-zero rows

### 4. Race Time Delta
- Status: PASS
- Builder: scripts/build_edgeiq_race_time_delta_versus_standard_v1.py (YES)
- Output: public/data/edgeiq_race_time_delta_versus_standard_fact_v1.csv (YES)
- Rows: 54989
- Reason: primary output exists with non-zero rows

### 5. Lengths v Standard
- Status: PASS
- Builder: scripts/build_edgeiq_lengths_versus_standard_v1.py (YES)
- Output: public/data/edgeiq_lengths_versus_standard_fact_v1.csv (YES)
- Rows: 52425
- Reason: primary output exists with non-zero rows

### 6. Performance Base
- Status: PASS
- Builder: scripts/build_edgeiq_performance_intelligence_base_fact_v1.py (YES)
- Output: public/data/edgeiq_performance_intelligence_base_fact_v1.csv (YES)
- Rows: 52425
- Reason: primary output exists with non-zero rows

### 7. Normalisation
- Status: PASS
- Builder: scripts/build_edgeiq_performance_normalisation_fact_v1.py (YES)
- Output: public/data/edgeiq_performance_normalisation_fact_v1.csv (YES)
- Rows: 52320
- Reason: primary output exists with non-zero rows

### 8. Horse Aggregates
- Status: PASS
- Builder: scripts/build_edgeiq_horse_performance_aggregate_fact_v1.py (YES)
- Output: public/data/edgeiq_horse_performance_aggregate_fact_v1.csv (YES)
- Rows: 1265
- Reason: primary output exists with non-zero rows

### 9. Horse Ratings
- Status: PASS
- Builder: scripts/build_edgeiq_horse_performance_rating_fact_v1.py (YES)
- Output: public/data/edgeiq_horse_performance_rating_fact_v1.csv (YES)
- Rows: 1265
- Reason: primary output exists with non-zero rows

### 10. Snapshots
- Status: PASS
- Builder: scripts/build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py (YES)
- Output: public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv (YES)
- Rows: 5
- Reason: primary output exists with non-zero rows

### 11. Projected Performance
- Status: ZERO_ROWS
- Builder: scripts/build_edgeiq_race_entry_projected_performance_fact_v1.py (YES)
- Output: public/data/edgeiq_race_entry_projected_performance_fact_v1.csv (YES)
- Rows: 0
- Reason: primary output exists but has zero data rows

### 12. EPI
- Status: ZERO_ROWS
- Builder: scripts/build_edgeiq_race_entry_epi_fact_v1.py (YES)
- Output: public/data/edgeiq_race_entry_epi_fact_v1.csv (YES)
- Rows: 0
- Reason: primary output exists but has zero data rows

### 13. Daily Operations
- Status: PASS
- Builder: scripts/run_edgeiq_daily_operations_engine_v1.py (YES)
- Output: public/data/edgeiq_daily_operations_checkpoint_fact_v1.csv (YES)
- Rows: 61
- Reason: primary output exists with non-zero rows

### 14. React Feeds
- Status: PASS
- Builder: scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py (YES)
- Output: public/data/edgeiq_epi_workspace_terminal_feed_v1.csv (YES)
- Rows: 246
- Reason: primary output exists with non-zero rows
