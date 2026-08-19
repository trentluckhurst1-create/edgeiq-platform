# EDGEiQ Performance Intelligence
## Phase 0.2 Domain Audit

Generated UTC: `2026-07-15T08:16:15.468020+00:00`

## Audit rule

No asset is declared canonical merely because it exists, is highly populated, or has a PASS audit.

## results_warehouse

- Status: **EXISTING_REQUIRES_LINEAGE_VALIDATION**
- Scripts found: **13**
- Data files found: **970**
- Populated data files: **924**

### Largest candidate data files

| Path | Rows | Min date | Max date | Race estimate | Horse estimate |
|---|---:|---|---|---:|---:|
| `public/data/edgeiq_results_master_v1.csv` | 931245 | 2000-08-02 | 2026-06-24 | 76304 | 0 |
| `public/data/edgeiq_historical_results_warehouse_v2_graphql.csv` | 879784 | 2000-08-02 | 2026-06-24 | 71019 | 879695 |
| `public/data/edgeiq_historical_results_warehouse_v2_graphql_CHECKPOINT_20260623_164849.csv` | 879784 | 2000-08-02 | 2026-06-24 | 71019 | 879695 |
| `public/data/edgeiq_racingcom_results_warehouse_all_v1.csv` | 165816 | 2026-04-12 | 2026-06-14 | 14623 | 1017 |
| `public/data/edgeiq_racingcom_results_warehouse_v1.csv` | 165816 | 2026-04-12 | 2026-06-14 | 14623 | 1017 |
| `public/data/edgeiq_racingcom_results_warehouse_full_v1.csv` | 164277 | 2023-02-11 | 2026-06-06 | 13720 | 0 |
| `public/data/edgeiq_canonical_results_truth_v1.csv` | 47887 | 2025-08-23 | 2026-05-24 | 4870 | 23111 |
| `public/data/results_enriched.csv` | 27951 | 2025-08-23 | 2026-03-15 | 2922 | 11792 |
| `public/data/results_report.csv` | 27917 | 2025-08-23 | 2026-03-15 | 2922 | 11792 |
| `public/data/edgeiq_graphql_november_2024_results_v1.csv` | 5424 | 2024-11-01 | 2024-11-30 | 456 | 5424 |

### Existing scripts

- `scripts/build_edgeiq_canonical_results_truth_v1.py` — FOUND
- `scripts/build_edgeiq_historical_results_warehouse_v2_graphql.py` — FOUND
- `scripts/build_edgeiq_racingcom_results_warehouse_all_v1.py` — FOUND
- `scripts/build_edgeiq_results_warehouse_full_consolidation_v1.py` — FOUND
- `scripts/build_edgeiq_results_master.py` — FOUND
- `scripts/build_edgeiq_results_master_v1.py` — FOUND
- `scripts/build_edgeiq_results_intelligence_history_v1.py` — FOUND
- `scripts/build_edgeiq_official_results_backfill_v1.py` — FOUND
- `scripts/build_edgeiq_graphql_results_warehouse_week1_2025_v1.py` — FOUND
- `scripts/build_edgeiq_graphql_results_warehouse_sample_v1.py` — FOUND
- `scripts/audit_edgeiq_results_warehouse_inventory_v1.py` — FOUND
- `scripts/audit_edgeiq_historical_results_warehouse_v2_graphql_quality.py` — FOUND
- `scripts/audit_edgeiq_results_data_contract_v1.py` — FOUND

## sectional_warehouse

- Status: **EXISTING_REQUIRES_LINEAGE_VALIDATION**
- Scripts found: **14**
- Data files found: **27**
- Populated data files: **26**

### Largest candidate data files

| Path | Rows | Min date | Max date | Race estimate | Horse estimate |
|---|---:|---|---|---:|---:|
| `public/data/edgeiq_standardised_sectionals_v1.csv` | 1355824 | 2000-08-02 | 2026-06-23 | 65804 | 0 |
| `public/data/racingcom_sectional_warehouse_v2.csv` | 130484 | 2023-01-01 | 2026-06-04 | 0 | 18201 |
| `public/data/edgeiq_vic_90day_sectional_warehouse_final_v1.csv` | 4605 | 2026-03-04 | 2026-05-02 | 539 | 2056 |
| `public/data/racingcom_sectional_warehouse_readiness_v1.csv` | 4330 |  |  | 0 | 4330 |
| `public/data/racingcom_sectional_warehouse_v1.csv` | 1864 | 2026-02-14 | 2026-05-31 | 0 | 1665 |
| `public/data/edgeiq_vic_90day_sectional_warehouse_final_diagnostics_v1.csv` | 1188 | 2026-03-01 | 2026-05-02 | 1188 | 0 |
| `public/data/edgeiq_trusted_sectional_universe_v2.csv` | 865 | 2026-05-19 | 2026-05-20 | 15 | 184 |
| `public/data/racingcom_sectionals_normalised_v1.csv` | 246 | 2026-05-30 | 2026-05-31 | 0 | 177 |
| `public/data/edgeiq_sectional_schema_v2.csv` | 184 | 2026-05-19 | 2026-05-20 | 15 | 184 |
| `public/data/racingcom_sectional_history_master_v1.csv` | 180 | 2026-05-30 | 2026-05-31 | 0 | 177 |

### Existing scripts

- `scripts/build_edgeiq_vic_sectional_warehouse_v1.py` — FOUND
- `scripts/build_edgeiq_vic_historical_sectional_warehouse_v1.py` — FOUND
- `scripts/build_edgeiq_vic_dom_sectional_warehouse_v1.py` — FOUND
- `scripts/build_racingcom_sectional_warehouse_v1.py` — FOUND
- `scripts/build_racingcom_sectional_warehouse_v2.py` — FOUND
- `scripts/build_racingcom_sectional_history_master_v1.py` — FOUND
- `scripts/build_edgeiq_standardised_sectionals_v1.py` — FOUND
- `scripts/build_edgeiq_trusted_sectional_universe.py` — FOUND
- `scripts/build_edgeiq_trusted_sectional_universe_v2.py` — FOUND
- `scripts/build_edgeiq_sectional_normalisation_v1.py` — FOUND
- `scripts/build_edgeiq_sectional_schema_v2.py` — FOUND
- `scripts/build_edgeiq_sectional_master_reconciliation_v1.py` — FOUND
- `scripts/audit_edgeiq_sectional_pipeline.py` — FOUND
- `scripts/audit_racingcom_sectional_warehouse_readiness_v1.py` — FOUND

## benchmark_engine

- Status: **EXISTING_REQUIRES_LINEAGE_VALIDATION**
- Scripts found: **7**
- Data files found: **33**
- Populated data files: **33**

### Largest candidate data files

| Path | Rows | Min date | Max date | Race estimate | Horse estimate |
|---|---:|---|---|---:|---:|
| `public/data/edgeiq_standardised_sectionals_v1.csv` | 1355824 | 2000-08-02 | 2026-06-23 | 65804 | 0 |
| `public/data/edgeiq_sectional_strength_runs_v1.csv` | 130484 | 2023-01-01 | 2026-06-04 | 13405 | 18201 |
| `public/data/edgeiq_race_strength_independence_audit_v1.csv` | 129002 | 2023-02-11 | 2026-06-06 | 13576 | 17912 |
| `public/data/edgeiq_sectional_strength_v2.csv` | 18210 |  |  | 0 | 18210 |
| `public/data/edgeiq_sectional_strength_engine_v1.csv` | 18210 |  |  | 0 | 18210 |
| `public/data/edgeiq_race_strength_conditional_audit_v1.csv` | 6554 | 2023-02-11 | 2026-06-06 | 0 | 3537 |
| `public/data/edgeiq_race_strength_v1.csv` | 6064 | 2025-01-01 | 2026-06-04 | 6064 | 0 |
| `public/data/edgeiq_standard_times_v1.csv` | 5065 |  |  | 0 | 0 |
| `public/data/edgeiq_predictive_engine_baseline_benchmark_v1.csv` | 4182 | 2026-01-01 | 2026-06-21 | 697 | 0 |
| `public/data/edgeiq_race_strength_history_v1.csv` | 3463 | 2025-05-01 | 2026-03-19 | 2922 | 0 |

### Existing scripts

- `scripts/build_edgeiq_standard_times_v1.py` — FOUND
- `scripts/build_edgeiq_standardised_sectionals_v1.py` — FOUND
- `scripts/build_edgeiq_race_strength_v1.py` — MISSING
- `scripts/build_edgeiq_race_strength_v2.py` — MISSING
- `scripts/build_edgeiq_race_strength_v3.py` — FOUND
- `scripts/build_edgeiq_race_strength_history_v1.py` — FOUND
- `scripts/build_edgeiq_sectional_strength_v2.py` — FOUND
- `scripts/build_edgeiq_performance_rating_engine_audit_v1.py` — FOUND
- `scripts/audit_edgeiq_benchmark_sectional_display_v1.py` — FOUND

## identity_engine

- Status: **EXISTING_REQUIRES_LINEAGE_VALIDATION**
- Scripts found: **8**
- Data files found: **11**
- Populated data files: **11**

### Largest candidate data files

| Path | Rows | Min date | Max date | Race estimate | Horse estimate |
|---|---:|---|---|---:|---:|
| `public/data/edgeiq_runner_entity_graph_v1.csv` | 73164 |  |  | 0 | 0 |
| `public/data/edgeiq_sectional_identity_engine_v2.csv` | 71404 | 01/04/2026 | 31/03/2026 | 2315 | 7321 |
| `public/data/edgeiq_sectional_identity_engine_v3.csv` | 71404 | 01/04/2026 | 31/03/2026 | 2315 | 4814 |
| `public/data/edgeiq_sectional_identity_engine_v1.csv` | 71404 | 01/04/2026 | 31/03/2026 | 2315 | 7321 |
| `public/data/edgeiq_temporal_identity_memory_v1.csv` | 241 |  |  | 0 | 241 |
| `public/data/edgeiq_canonical_market_entity_graph_v1.csv` | 192 | 2026-05-19 | 2026-05-20 | 15 | 184 |
| `public/data/edgeiq_temporal_identity_memory_summary_v1.csv` | 18 |  |  | 0 | 0 |
| `public/data/edgeiq_sectional_identity_summary_v3.csv` | 16 |  |  | 0 | 0 |
| `public/data/edgeiq_runner_entity_graph_summary_v1.csv` | 14 |  |  | 0 | 0 |
| `public/data/edgeiq_sectional_identity_summary_v2.csv` | 12 |  |  | 0 | 0 |

### Existing scripts

- `scripts/build_edgeiq_sectional_identity_engine_v1.py` — FOUND
- `scripts/build_edgeiq_sectional_identity_engine_v2.py` — FOUND
- `scripts/build_edgeiq_sectional_identity_engine_v3.py` — FOUND
- `scripts/build_edgeiq_canonical_results_truth_v1.py` — FOUND
- `scripts/build_edgeiq_temporal_identity_memory_v1.py` — FOUND
- `scripts/build_edgeiq_canonical_market_entity_graph_v1.py` — FOUND
- `scripts/build_edgeiq_results_master.py` — FOUND
- `scripts/build_racingcom_sectional_warehouse_v2.py` — FOUND

## performance_ratings

- Status: **EXISTING_REQUIRES_LINEAGE_VALIDATION**
- Scripts found: **9**
- Data files found: **164**
- Populated data files: **163**

### Largest candidate data files

| Path | Rows | Min date | Max date | Race estimate | Horse estimate |
|---|---:|---|---|---:|---:|
| `public/data/edgeiq_runner_dna_weight_ladder_v1_detail.csv` | 516008 | 2023-02-11 | 2026-06-06 | 13576 | 17905 |
| `public/data/edgeiq_runner_dna_predictive_value_v1.csv` | 129002 | 2023-02-11 | 2026-06-06 | 13576 | 17905 |
| `public/data/edgeiq_runner_dna_v6_3_probability_calibration_replay_v1.csv` | 129002 | 2023-02-11 | 2026-06-06 | 13576 | 17905 |
| `public/data/edgeiq_runner_dna_v6_3_historical_replay_v1.csv` | 129002 | 2023-02-11 | 2026-06-06 | 13576 | 17905 |
| `public/data/edgeiq_historical_performance_rating_v6_1_research.csv` | 71327 | 2017-01-28 | 2026-06-04 | 0 | 18663 |
| `public/data/edgeiq_historical_performance_rating_v6_1_research_CHECKPOINT_BACKFILLED_RISK_20260617.csv` | 71327 | 2017-01-28 | 2026-06-04 | 0 | 18663 |
| `public/data/edgeiq_historical_performance_rating_v6_1_research_WORKING_100_RESEARCH_10_FALLBACK_20260615.csv` | 71327 | 2017-01-28 | 2026-06-04 | 0 | 18663 |
| `public/data/edgeiq_historical_performance_rating_v5_1.csv` | 71327 | 2017-01-28 | 2026-06-04 | 0 | 18663 |
| `public/data/edgeiq_historical_performance_rating_v5_1_BACKFILLED_POWER_V1.csv` | 71327 | 2017-01-28 | 2026-06-04 | 0 | 18663 |
| `public/data/edgeiq_historical_performance_rating_v6_1_research_CHECKPOINT_20260614.csv` | 66867 | 2017-01-28 | 2026-06-03 | 0 | 14203 |

### Existing scripts

- `scripts/build_edgeiq_historical_performance_rating_v3_3.py` — FOUND
- `scripts/build_edgeiq_historical_performance_rating_v5_1.py` — FOUND
- `scripts/build_edgeiq_performance_rating_engine_audit_v1.py` — FOUND
- `scripts/build_edgeiq_race_strength_history_v1.py` — FOUND
- `scripts/build_edgeiq_results_intelligence_history_v1.py` — FOUND
- `scripts/build_edgeiq_runner_history_detail_v1.py` — FOUND
- `scripts/build_edgeiq_results_terminal_feed_v1.py` — FOUND
- `scripts/build_edgeiq_runner_dna_v1.py` — FOUND
- `scripts/build_edgeiq_runner_dna_v2.py` — FOUND

## length_conversion

- Status: **LEGACY_CONVERSION_PRESENT_REQUIRES_GOVERNANCE**
- Scripts found: **2**
- Data files found: **5**
- Populated data files: **5**

### Largest candidate data files

| Path | Rows | Min date | Max date | Race estimate | Horse estimate |
|---|---:|---|---|---:|---:|
| `public/data/edgeiq_standardised_sectionals_v1.csv` | 1355824 | 2000-08-02 | 2026-06-23 | 65804 | 0 |
| `public/data/edgeiq_lengths_per_point_engine_v1.csv` | 1301 |  |  | 0 | 0 |
| `public/data/edgeiq_standardised_sectionals_examples_v1.csv` | 80 | 2000-08-02 | 2000-08-02 | 8 | 0 |
| `public/data/edgeiq_standardised_sectionals_summary_v1.csv` | 1 |  |  | 0 | 0 |
| `public/data/edgeiq_lengths_per_point_engine_summary_v1.csv` | 1 |  |  | 0 | 0 |

### Existing scripts

- `scripts/build_edgeiq_standardised_sectionals_v1.py` — FOUND
- `scripts/audit_edgeiq_ui_column_data_v1.py` — FOUND

## Mandatory next step

Select one candidate per domain only after validating its source evidence, transformation logic, output contract, coverage, duplication, quality states and downstream consumers.
