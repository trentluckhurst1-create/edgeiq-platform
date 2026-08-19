# EDGEIQ Performance Intelligence

## Phase 1A.2 Warehouse Lineage and Equivalence V1

- Program ID: `EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1A_2_WAREHOUSE_LINEAGE_EQUIVALENCE_V1`
- Version: `1.0.0`
- Generated UTC: `2026-07-27T03:17:36+00:00`
- Overall status: **PASS**

## Target Inventory

| Target | Exists | Rows | Fields | SHA-256 | Role |
|---|---|---:|---:|---|---|
| `PERFORMANCE_WAREHOUSE_V1` | True | 879784 | 32 | `bcdcef1c7cb9144f` | EARLY_PERFORMANCE_WAREHOUSE |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | True | 879784 | 51 | `1845f561022e34bf` | IMMUTABLE_PERFORMANCE_FACT_SNAPSHOT |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | True | 879784 | 52 | `51c5c04ce04bdd28` | CORRECTED_PERFORMANCE_FACT_WAREHOUSE |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | True | 879784 | 53 | `13f17e2ae21802ae` | HISTORICAL_RESULTS_SOURCE |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | True | 1772640 | 37 | `428ac99ebf0e0eb4` | HISTORICAL_RUN_OBSERVATION |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2_CANDIDATE` | True | 1772640 | 37 | `428ac99ebf0e0eb4` | HISTORICAL_RUN_OBSERVATION_CANDIDATE |
| `RACE_LENGTHS_V_STANDARD_FACT_V1` | True | 51769 | 8 | `5881a2d2490ecfb6` | RACE_LEVEL_LENGTHS_V_STANDARD |
| `EPI_PERFORMANCE_FACT_V1` | True | 533387 | 26 | `ef4fad0f0a1b10d7` | EPI_RESEARCH_PERFORMANCE_FACT |
| `BENCHMARK_ELIGIBILITY_FACT_V1` | True | 39 | 20 | `79017ae2082e834d` | BENCHMARK_ELIGIBILITY |

## Runner-Key Audit

| Target | Key Type | Rows | Unique | Missing | Duplicate Rows |
|---|---|---:|---:|---:|---:|
| `PERFORMANCE_WAREHOUSE_V1` | RACE_ID_PLUS_HORSE_ID | 879784 | 879781 | 0 | 3 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | PARTIAL_COMPOSITE_KEY | 879784 | 70238 | 0 | 809546 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_ID_PLUS_HORSE_ID | 879784 | 879693 | 0 | 91 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_ID_PLUS_HORSE_ID | 879784 | 879693 | 0 | 91 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | RACE_ID_PLUS_HORSE_ID | 1772640 | 1772462 | 0 | 178 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2_CANDIDATE` | RACE_ID_PLUS_HORSE_ID | 1772640 | 1772462 | 0 | 178 |
| `RACE_LENGTHS_V_STANDARD_FACT_V1` | NO_DEFENSIBLE_RUNNER_KEY | 0 | 0 | 0 | 0 |
| `EPI_PERFORMANCE_FACT_V1` | RACE_ID_PLUS_HORSE_ID | 533387 | 533387 | 0 | 0 |
| `BENCHMARK_ELIGIBILITY_FACT_V1` | NO_DEFENSIBLE_RUNNER_KEY | 0 | 0 | 0 | 0 |

## Identical File Pairs

- `HISTORICAL_RUN_OBSERVATION_FACT_V2` is byte-identical to `HISTORICAL_RUN_OBSERVATION_FACT_V2_CANDIDATE`.

## Same-Row-Count Comparisons

| Left | Right | Same Rows | Same Header | Same Sample | Schema Jaccard |
|---|---|---|---|---|---:|
| `PERFORMANCE_WAREHOUSE_V1` | `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | True | False | False | 0.121622 |
| `PERFORMANCE_WAREHOUSE_V1` | `CANONICAL_PERFORMANCE_FACTS_V0_2` | True | False | False | 0.12 |
| `PERFORMANCE_WAREHOUSE_V1` | `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | True | False | False | 0.0625 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | `CANONICAL_PERFORMANCE_FACTS_V0_2` | True | False | False | 0.256098 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | True | False | False | 0.405405 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | True | False | False | 0.25 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | `HISTORICAL_RUN_OBSERVATION_FACT_V2_CANDIDATE` | True | True | True | 1.0 |

## Active Python Lineage References

- References detected: 98

- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/audit_edgeiq_benchmark_accumulation_fact_v1.py` (AUDIT)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/audit_edgeiq_benchmark_eligibility_fact_v1.py` (AUDIT)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/audit_edgeiq_performance_fact_dependency_trace_v1.py` (AUDIT)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/audit_edgeiq_performance_intelligence_live_e2e_v1.py` (AUDIT)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/audit_edgeiq_race_time_delta_versus_standard_v1.py` (AUDIT)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/audit_edgeiq_standard_time_recovery_result_v1.py` (AUDIT)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/build_edgeiq_benchmark_accumulation_fact_v1.py` (BUILDER)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/build_edgeiq_benchmark_eligibility_fact_v1.py` (BUILDER)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/build_edgeiq_race_time_delta_versus_standard_v1.py` (BUILDER)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/create_edgeiq_benchmark_eligibility_fact_v1.py` (OTHER)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/inspect_edgeiq_benchmark_accumulation_inputs_v1.py` (OTHER)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/inspect_edgeiq_benchmark_accumulation_inputs_v1_1.py` (OTHER)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/preflight_edgeiq_benchmark_accumulation_fact_v1.py` (OTHER)
- `BENCHMARK_ELIGIBILITY_FACT_V1` ← `scripts/run_edgeiq_performance_fact_rebuild_from_racingcom_v1.py` (ORCHESTRATOR)
- `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` ← `scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase1_5b.py` (BUILDER)
- `CANONICAL_PERFORMANCE_FACTS_V0_2` ← `scripts/audit_edgeiq_product_maturity_phase5_v1.py` (AUDIT)
- `CANONICAL_PERFORMANCE_FACTS_V0_2` ← `scripts/performance-intelligence/phase1_6_1/apply_phase1_6_1_recovery_patch.py` (APPLY)
- `CANONICAL_PERFORMANCE_FACTS_V0_2` ← `scripts/performance-intelligence/phase1_6_1/audit_edgeiq_corrected_performance_facts_phase1_6_1.py` (AUDIT)
- `CANONICAL_PERFORMANCE_FACTS_V0_2` ← `scripts/performance-intelligence/phase1_6_1/build_edgeiq_corrected_performance_facts_phase1_6_1.py` (BUILDER)
- `CANONICAL_PERFORMANCE_FACTS_V0_2` ← `scripts/performance-intelligence/phase1_6_1/patch_phase1_6_1_corrected_builder.py` (PATCH)
- `CANONICAL_PERFORMANCE_FACTS_V0_2` ← `scripts/performance-intelligence/product-integration/audit_edgeiq_performance_intelligence_product_integration_v1.py` (AUDIT)
- `CANONICAL_PERFORMANCE_FACTS_V0_2` ← `scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py` (BUILDER)
- `CANONICAL_PERFORMANCE_FACTS_V0_2` ← `scripts/performance-intelligence/run_edgeiq_performance_intelligence_full_pipeline_v1.py` (ORCHESTRATOR)
- `EPI_PERFORMANCE_FACT_V1` ← `scripts/build_edgeiq_performance_recovery_current_lineage_v1.py` (BUILDER)
- `EPI_PERFORMANCE_FACT_V1` ← `scripts/patch_edgeiq_performance_recovery_current_epi_shape_v1.py` (PATCH)
- `EPI_PERFORMANCE_FACT_V1` ← `scripts/run_edgeiq_performance_intelligence_completion_v1.py` (ORCHESTRATOR)
- `EPI_PERFORMANCE_FACT_V1` ← `scripts/test_edgeiq_performance_recovery_lineage_v1.py` (TEST)
- `EPI_PERFORMANCE_FACT_V1` ← `scripts/verify_edgeiq_weight_adjusted_epi_and_race_count_v1.py` (OTHER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/audit_edgeiq_connection_v2_coverage_gap_v1.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/audit_edgeiq_epf_v1_quality_guardrails.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/audit_edgeiq_form_full_history_trace_all_current_v1.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/audit_edgeiq_form_guide_v2_1.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/audit_edgeiq_historical_results_warehouse_v2_graphql_quality.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/audit_edgeiq_time_variant_data_sources_v1.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/audit_edgeiq_wfa_input_coverage_v1.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/audit_edgeiq_wfa_rating_source_inventory_v1.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_active_build_chain_manifest_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_comprehensive_predictive_model_research_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_connection_intelligence_v2.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_connection_intelligence_v2_1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_context_warehouse_v2_graphql.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_debutant_intelligence_engine_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_epf_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_epf_v1_1_guardrailed.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_form_display_clean_v2.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_form_enrichment_feed_v4.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_form_guide_enriched_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_form_guide_enriched_v2.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_form_guide_v3_3_reports.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_gear_pace_impact_research_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_gear_profile_engine_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_historical_results_warehouse_v2_graphql.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_historical_standard_times_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_live_graphql_entity_resolution_bridge_v3.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_live_stable_intent_feed_v2_1_graphql_resolved.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_live_stable_intent_feed_v2_graphql.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_nexus_contextual_intelligence_v2.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_nexus_feature_engine_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_predictive_engine_baseline_benchmark_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_predictive_engine_baseline_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_prior_asof_rating_spine_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_repository_safe_migration_plan_v2.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_stage_of_prep_engine_v2_graphql.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_timestamp_safe_market_snapshot_spine_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_track_variant_engine_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_trainer_jockey_prep_engine_v2_graphql.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/build_edgeiq_true_track_rating_v1.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/edgeiq_results_common_v1.py` (OTHER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase0_3.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase0_6.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase1_4_1.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase1_4_1a.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase1_4_1b.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase1_4_1c.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase1_5a.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase1_5b_1.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase1_5b_2.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase1_5b_3.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase1_5b_4.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/audit_edgeiq_performance_intelligence_phase1_5b_5.py` (AUDIT)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase0_4.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase0_5.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase0_7.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase0_8.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase1_5b.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/performance-intelligence/phase1_6/build_edgeiq_performance_fact_warehouse_phase1_6.py` (BUILDER)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/run_edgeiq_performance_intelligence_completion_v1.py` (ORCHESTRATOR)
- `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` ← `scripts/verify_edgeiq_post_race_lifecycle_v1.py` (OTHER)
- `HISTORICAL_RUN_OBSERVATION_FACT_V2` ← `scripts/build_edgeiq_historical_run_observation_fact_v2.py` (BUILDER)
- `HISTORICAL_RUN_OBSERVATION_FACT_V2_CANDIDATE` ← `scripts/build_edgeiq_historical_run_observation_fact_v2.py` (BUILDER)
- `PERFORMANCE_WAREHOUSE_V1` ← `scripts/audit_edgeiq_daily_betting_readiness_v1.py` (AUDIT)
- `PERFORMANCE_WAREHOUSE_V1` ← `scripts/build_edgeiq_performance_recovery_current_lineage_v1.py` (BUILDER)
- `PERFORMANCE_WAREHOUSE_V1` ← `scripts/run_edgeiq_performance_intelligence_completion_v1.py` (ORCHESTRATOR)
- `PERFORMANCE_WAREHOUSE_V1` ← `scripts/verify_edgeiq_weight_adjusted_epi_and_race_count_v1.py` (OTHER)
- `RACE_LENGTHS_V_STANDARD_FACT_V1` ← `scripts/build_edgeiq_performance_recovery_current_lineage_v1.py` (BUILDER)
- `RACE_LENGTHS_V_STANDARD_FACT_V1` ← `scripts/run_edgeiq_performance_intelligence_completion_v1.py` (ORCHESTRATOR)
- `RACE_LENGTHS_V_STANDARD_FACT_V1` ← `scripts/test_edgeiq_performance_recovery_lineage_v1.py` (TEST)
- `RACE_LENGTHS_V_STANDARD_FACT_V1` ← `scripts/verify_edgeiq_weight_adjusted_epi_and_race_count_v1.py` (OTHER)

## Audit

- **PASS** — `target_file_availability`: existing=9; missing=0
- **PASS** — `target_file_readability`: inspection_errors=0
- **PASS** — `runner_identity_key_detection`: exact_key_audits=7
- **PASS** — `pairwise_equivalence_completed`: pairwise_comparisons=36
- **PASS** — `active_lineage_reference_detection`: active_python_references=98
- **PASS** — `exact_duplicate_detection`: byte_identical_pairs=1

## Governance

- No production datasets were modified.
- No warehouse was declared canonical.
- No rating or benchmark was recalculated.
- File equivalence is assessed through byte hashes, schemas, row counts and governed key audits.
