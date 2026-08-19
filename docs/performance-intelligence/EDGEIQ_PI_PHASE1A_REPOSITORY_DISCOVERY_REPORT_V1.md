# EDGEIQ Performance Intelligence

## Phase 1A Repository Discovery V1

- Program ID: `EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1A_REPOSITORY_DISCOVERY_V1`
- Version: `1.0.0`
- Repository: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM`
- Generated UTC: `2026-07-27T03:06:36+00:00`
- Overall status: **PARTIAL**

## Purpose

This checkpoint performs a non-destructive discovery of existing datasets, Python builders, audits and Performance Intelligence assets.

It does not create ratings, modify production datasets, lower governed thresholds, or nominate a canonical source without evidence.

## Repository Summary

- Files inspected: 52,218
- Supported datasets: 16,656
- Python files: 10,945
- Dataset schema errors: 20
- Python syntax failures: 20
- Candidate performance sources: 10,172

## Candidate Performance Sources

| Coverage | Relevance | Rows | Path |
|---:|---:|---:|---|
| 11 | 9 | 879,784 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_historical_results_warehouse_v2_graphql.csv` |
| 11 | 9 | 879,784 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_historical_results_warehouse_v2_graphql_CHECKPOINT_20260623_164849.csv` |
| 11 | 9 | 503 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_live_runner_board_governed_v1.csv` |
| 11 | 9 | 503 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_live_runner_board_governed_v1_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_163748.csv` |
| 11 | 9 | 503 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_live_runner_board_governed_v1_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_193502.csv` |
| 11 | 9 | 503 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_live_runner_board_governed_v1_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_211017.csv` |
| 11 | 9 | 503 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_live_runner_board_governed_v1_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260712_065207.csv` |
| 11 | 9 | 879,784 | `public/data/edgeiq_historical_results_warehouse_v2_graphql.csv` |
| 11 | 9 | 879,784 | `public/data/edgeiq_historical_results_warehouse_v2_graphql_CHECKPOINT_20260623_164849.csv` |
| 11 | 9 | 503 | `public/data/edgeiq_live_runner_board_governed_v1_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_163748.csv` |
| 11 | 9 | 503 | `public/data/edgeiq_live_runner_board_governed_v1_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_193502.csv` |
| 11 | 9 | 503 | `public/data/edgeiq_live_runner_board_governed_v1_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_211017.csv` |
| 11 | 9 | 503 | `public/data/edgeiq_live_runner_board_governed_v1_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260712_065207.csv` |
| 11 | 8 | 3,083 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2001_results_v1.csv` |
| 11 | 8 | 2,735 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2002_results_v1.csv` |
| 11 | 8 | 3,312 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2003_results_v1.csv` |
| 11 | 8 | 2,846 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2004_results_v1.csv` |
| 11 | 8 | 3,392 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2005_results_v1.csv` |
| 11 | 8 | 4,097 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2006_results_v1.csv` |
| 11 | 8 | 3,976 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2007_results_v1.csv` |
| 11 | 8 | 3,750 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2008_results_v1.csv` |
| 11 | 8 | 2,039 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2009_results_v1.csv` |
| 11 | 8 | 3,244 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2010_results_v1.csv` |
| 11 | 8 | 3,496 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2012_results_v1.csv` |
| 11 | 8 | 3,177 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2013_results_v1.csv` |
| 11 | 8 | 2,834 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2014_results_v1.csv` |
| 11 | 8 | 2,117 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2015_results_v1.csv` |
| 11 | 8 | 3,185 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2018_results_v1.csv` |
| 11 | 8 | 3,117 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2019_results_v1.csv` |
| 11 | 8 | 3,259 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2020_results_v1.csv` |
| 11 | 8 | 3,458 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2021_results_v1.csv` |
| 11 | 8 | 2,620 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2022_results_v1.csv` |
| 11 | 8 | 4,498 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2023_results_v1.csv` |
| 11 | 8 | 4,405 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2024_results_v1.csv` |
| 11 | 8 | 3,543 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2025_results_v1.csv` |
| 11 | 8 | 4,688 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_april_2026_results_v1.csv` |
| 11 | 8 | 2,816 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_august_2000_results_v1.csv` |
| 11 | 8 | 1,512 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_august_2001_results_v1.csv` |
| 11 | 8 | 3,241 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_august_2002_results_v1.csv` |
| 11 | 8 | 3,159 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_graphql_august_2003_results_v1.csv` |

## Most Relevant Datasets

| Score | Fields | Rows | Path |
|---:|---:|---:|---|
| 12 | 223 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_rank_validation_v1_runner_rows.csv` |
| 12 | 223 | 623 | `public/data/edgeiq_rank_validation_v1_runner_rows.csv` |
| 11 | 200 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_execution_candidates_v1.csv` |
| 11 | 212 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_execution_confidence_v1.csv` |
| 11 | 175 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_fair_price_v7.csv` |
| 11 | 176 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_fair_price_v7_1.csv` |
| 11 | 175 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_fair_price_v7_2.csv` |
| 11 | 175 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_fair_price_v7_2_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_154418.csv` |
| 11 | 175 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_fair_price_v7_2_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_163748.csv` |
| 11 | 175 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_fair_price_v7_2_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_193502.csv` |
| 11 | 175 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_fair_price_v7_2_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_211017.csv` |
| 11 | 175 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_fair_price_v7_2_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260712_065207.csv` |
| 11 | 195 | 623 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_overlay_audit_v1.csv` |
| 11 | 200 | 623 | `public/data/edgeiq_execution_candidates_v1.csv` |
| 11 | 212 | 623 | `public/data/edgeiq_execution_confidence_v1.csv` |
| 11 | 175 | 623 | `public/data/edgeiq_fair_price_v7.csv` |
| 11 | 176 | 623 | `public/data/edgeiq_fair_price_v7_1.csv` |
| 11 | 175 | 623 | `public/data/edgeiq_fair_price_v7_2_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_154418.csv` |
| 11 | 175 | 623 | `public/data/edgeiq_fair_price_v7_2_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_163748.csv` |
| 11 | 175 | 623 | `public/data/edgeiq_fair_price_v7_2_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_193502.csv` |
| 11 | 175 | 623 | `public/data/edgeiq_fair_price_v7_2_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260711_211017.csv` |
| 11 | 175 | 623 | `public/data/edgeiq_fair_price_v7_2_CHECKPOINT_BEFORE_CURRENT_INTEL_REBUILD_20260712_065207.csv` |
| 11 | 195 | 623 | `public/data/edgeiq_overlay_audit_v1.csv` |
| 11 | 43 | 1 | `docs/performance-intelligence/lengths-v-standard/edgeiq_performance_intelligence_final_live_v2_summary.json` |
| 10 | 64 | 129,002 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_historical_pace_advantage_replay_v1.csv` |
| 10 | 68 | 129,002 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_historical_pace_trust_replay_v1.csv` |
| 10 | 64 | 129,002 | `public/data/edgeiq_historical_pace_advantage_replay_v1.csv` |
| 10 | 68 | 129,002 | `public/data/edgeiq_historical_pace_trust_replay_v1.csv` |
| 10 | 64 | 109,431 | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/public/data/edgeiq_historical_race_shape_archive_v1.csv` |
| 10 | 64 | 109,431 | `public/data/edgeiq_historical_race_shape_archive_v1.csv` |

## Most Relevant Python Assets

| Score | Kind | Syntax | Path |
|---:|---|---|---|
| 21 | CHECKPOINT | PASS | `scripts/checkpoint_edgeiq_performance_intelligence_phase1a_repository_discovery_v1.py` |
| 17 | BUILDER | PASS | `scripts/build_edgeiq_performance_recovery_current_lineage_v1.py` |
| 17 | ORCHESTRATOR | PASS | `scripts/run_edgeiq_performance_intelligence_completion_v1.py` |
| 15 | AUDIT | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/audit_edgeiq_final_forensic_conformance_v1.py` |
| 15 | BUILDER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_performance_rating_engine_audit_v1.py` |
| 15 | ORCHESTRATOR | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/run_edgeiq_beta_governed_data_completion_v1.py` |
| 15 | AUDIT | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/audit_edgeiq_final_forensic_conformance_v1.py` |
| 15 | BUILDER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/build_edgeiq_performance_rating_engine_audit_v1.py` |
| 15 | ORCHESTRATOR | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/run_edgeiq_beta_governed_data_completion_v1.py` |
| 15 | AUDIT | PASS | `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/audit_edgeiq_final_forensic_conformance_v1.py` |
| 15 | BUILDER | PASS | `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_performance_rating_engine_audit_v1.py` |
| 15 | ORCHESTRATOR | PASS | `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/run_edgeiq_beta_governed_data_completion_v1.py` |
| 15 | APPLY | PASS | `scripts/apply_edgeiq_australian_synthetic_performance_v2.py` |
| 15 | AUDIT | PASS | `scripts/audit_edgeiq_final_forensic_conformance_v1.py` |
| 15 | BUILDER | PASS | `scripts/build_edgeiq_live_product_readiness_v1.py` |
| 15 | BUILDER | PASS | `scripts/build_edgeiq_performance_rating_engine_audit_v1.py` |
| 15 | ORCHESTRATOR | PASS | `scripts/run_edgeiq_beta_governed_data_completion_v1.py` |
| 14 | BUILDER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_comprehensive_predictive_model_research_v1.py` |
| 14 | BUILDER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_form_guide_enriched_v2.py` |
| 14 | OTHER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/edgeiq_beta_readiness_common_v1.py` |
| 14 | OTHER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/edgeiq_results_common_v1.py` |
| 14 | BUILDER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase0_4.py` |
| 14 | BUILDER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/build_edgeiq_comprehensive_predictive_model_research_v1.py` |
| 14 | BUILDER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/build_edgeiq_form_guide_enriched_v2.py` |
| 14 | OTHER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/edgeiq_beta_readiness_common_v1.py` |
| 14 | OTHER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/edgeiq_results_common_v1.py` |
| 14 | BUILDER | PASS | `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase0_4.py` |
| 14 | OTHER | PASS | `checkpoints/edgeiq_beta_readiness_lock_20260715_145728/scripts/edgeiq_beta_readiness_common_v1.py` |
| 14 | OTHER | PASS | `checkpoints/edgeiq_beta_readiness_lock_20260715_151703/scripts/edgeiq_beta_readiness_common_v1.py` |
| 14 | BUILDER | PASS | `checkpoints/edgeiq_form_guide_engineering_build_v1_20260713_033414/scripts/build_edgeiq_form_guide_enriched_v2.py` |
| 14 | BUILDER | PASS | `checkpoints/edgeiq_light_design_epi_map_v1_20260711T224718Z/scripts/build_edgeiq_form_guide_enriched_v2.py` |
| 14 | BUILDER | PASS | `checkpoints/edgeiq_light_repair_v1_20260712T013207Z/scripts/build_edgeiq_form_guide_enriched_v2.py` |
| 14 | BUILDER | PASS | `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_comprehensive_predictive_model_research_v1.py` |
| 14 | BUILDER | PASS | `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_form_guide_enriched_v2.py` |
| 14 | OTHER | PASS | `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/edgeiq_beta_readiness_common_v1.py` |
| 14 | OTHER | PASS | `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/edgeiq_results_common_v1.py` |
| 14 | BUILDER | PASS | `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase0_4.py` |
| 14 | APPLY | PASS | `scripts/apply_edgeiq_form_guide_final_table_v2.py` |
| 14 | BUILDER | PASS | `scripts/build_edgeiq_comprehensive_predictive_model_research_v1.py` |
| 14 | BUILDER | PASS | `scripts/build_edgeiq_form_guide_enriched_v2.py` |

## Audit

- **PASS** — `repository_root_exists`: C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM
- **PASS** — `dataset_inventory_created`: datasets=16656
- **PASS** — `python_inventory_created`: python_files=10945
- **PARTIAL** — `dataset_schema_readability`: schema_errors=20
- **PARTIAL** — `python_syntax_scan`: syntax_failures=20
- **PASS** — `candidate_source_detection`: candidate_sources=10172
- **PASS** — `output_location_available`: C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\docs\performance-intelligence

## Generated Files

- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_DATASET_INVENTORY_V1.csv`
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_DATASET_INVENTORY_V1.json`
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_PYTHON_INVENTORY_V1.csv`
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_PYTHON_INVENTORY_V1.json`
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_FIELD_FREQUENCY_V1.csv`
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_CANDIDATE_SOURCE_REGISTER_V1.csv`
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_REPOSITORY_DISCOVERY_REPORT_V1.json`
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_REPOSITORY_DISCOVERY_REPORT_V1.md`
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_REPOSITORY_DISCOVERY_AUDIT_V1.json`
- `docs/performance-intelligence/EDGEIQ_PI_PHASE1A_REPOSITORY_DISCOVERY_AUDIT_V1.md`

## Governance

- Existing production files were not modified.
- No rating formula was created.
- No benchmark threshold was changed.
- No synthetic data was created.
- Candidate sources are discovery results only.
- Canonical source nomination requires the next forensic review.
