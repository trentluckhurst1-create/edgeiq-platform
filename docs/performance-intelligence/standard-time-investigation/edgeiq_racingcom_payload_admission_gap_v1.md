# EDGEIQ Racing.com Payload Admission Gap V1

Generated UTC: `2026-07-22T07:08:49.941958+00:00`

## Investigation boundary

- Read-only forensic diagnostic.
- No governed builder or governed output was modified.
- No threshold was changed.
- No benchmark or standard-time data was fabricated.

## Population summary

- Probable raw Racing.com payloads: **1175**
- Source reference rows: **14826**
- Raw payloads matched to governed references: **39**
- Raw payloads with no governed reference: **1136**
- Reference values not matched to discovered raw files: **8275**

## V1 source datasets

- `edgeiq_racingcom_runner_speed_fact_v1.csv` ? FOUND ? rows=39 ? references=140 ? path=`outputs/sectionals/checkpoints/racingcom_speed_5_race_baseline_20260722_051140/edgeiq_racingcom_runner_speed_fact_v1.csv`
- `edgeiq_racingcom_runner_speed_fact_v1.csv` ? FOUND ? rows=392 ? references=977 ? path=`public/data/edgeiq_racingcom_runner_speed_fact_v1.csv`
- `edgeiq_racingcom_runner_sectional_fact_v1.csv` ? FOUND ? rows=270 ? references=10 ? path=`outputs/sectionals/checkpoints/racingcom_speed_5_race_baseline_20260722_051140/edgeiq_racingcom_runner_sectional_fact_v1.csv`
- `edgeiq_racingcom_runner_sectional_fact_v1.csv` ? FOUND ? rows=2854 ? references=78 ? path=`public/data/edgeiq_racingcom_runner_sectional_fact_v1.csv`
- `edgeiq_racingcom_runner_split_fact_v1.csv` ? FOUND ? rows=270 ? references=10 ? path=`outputs/sectionals/checkpoints/racingcom_speed_5_race_baseline_20260722_051140/edgeiq_racingcom_runner_split_fact_v1.csv`
- `edgeiq_racingcom_runner_split_fact_v1.csv` ? FOUND ? rows=2682 ? references=78 ? path=`public/data/edgeiq_racingcom_runner_split_fact_v1.csv`
- `edgeiq_racingcom_race_speed_summary_v1.csv` ? FOUND ? rows=5 ? references=10 ? path=`outputs/sectionals/checkpoints/racingcom_speed_5_race_baseline_20260722_051140/edgeiq_racingcom_race_speed_summary_v1.csv`
- `edgeiq_racingcom_race_speed_summary_v1.csv` ? FOUND ? rows=39 ? references=78 ? path=`public/data/edgeiq_racingcom_race_speed_summary_v1.csv`

## Admission by payload date

| Date | Raw | Admitted | Unreferenced |
|---|---:|---:|---:|
| 2026-05-30 | 18 | 0 | 18 |
| 2026-05-31 | 22 | 0 | 22 |
| 2026-06-13 | 1 | 0 | 1 |
| 2026-07-20 | 249 | 0 | 249 |
| 2026-07-22 | 13 | 0 | 13 |
| DATE_UNKNOWN | 872 | 39 | 833 |

## Candidate selector scripts

- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_dom_sectional_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=24
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_historical_sectional_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=24
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_racingcom_browser_csv_downloader_v1.py` ? syntax=PASS ? selector evidence lines=60
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_racingcom_speed_data_ingestion_v1.py` ? syntax=PASS ? selector evidence lines=58
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_real_chrome_csv_capture_v1.py` ? syntax=PASS ? selector evidence lines=23
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_real_chrome_csv_capture_v2.py` ? syntax=PASS ? selector evidence lines=44
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/build_edgeiq_vic_dom_sectional_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=24
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/build_edgeiq_vic_historical_sectional_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=24
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/build_edgeiq_vic_racingcom_browser_csv_downloader_v1.py` ? syntax=PASS ? selector evidence lines=60
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/build_edgeiq_vic_racingcom_speed_data_ingestion_v1.py` ? syntax=PASS ? selector evidence lines=58
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/build_edgeiq_vic_real_chrome_csv_capture_v1.py` ? syntax=PASS ? selector evidence lines=23
- `checkpoints/EDGEIQ_BEFORE_FINAL_LIVE_DATA_POPULATION_20260720_101414/scripts/build_edgeiq_vic_real_chrome_csv_capture_v2.py` ? syntax=PASS ? selector evidence lines=44
- `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_dom_sectional_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=24
- `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_historical_sectional_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=24
- `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_racingcom_browser_csv_downloader_v1.py` ? syntax=PASS ? selector evidence lines=60
- `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_racingcom_speed_data_ingestion_v1.py` ? syntax=PASS ? selector evidence lines=58
- `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_real_chrome_csv_capture_v1.py` ? syntax=PASS ? selector evidence lines=23
- `docs/full-product-implementation/checkpoints/CHECKPOINT_BEFORE_FULL_APPROVED_UI_REBUILD_20260719_121910/scripts/build_edgeiq_vic_real_chrome_csv_capture_v2.py` ? syntax=PASS ? selector evidence lines=44
- `scripts/audit_edgeiq_benchmark_sectional_display_v1.py` ? syntax=PASS ? selector evidence lines=5
- `scripts/audit_edgeiq_racingcom_history_horizon_v1.py` ? syntax=PASS ? selector evidence lines=78
- `scripts/audit_edgeiq_racingcom_runner_speed_reproducibility_v1.py` ? syntax=PASS ? selector evidence lines=15
- `scripts/audit_edgeiq_racingcom_speed_semantics_v1.py` ? syntax=PASS ? selector evidence lines=34
- `scripts/audit_edgeiq_racingcom_speed_semantics_v1_1.py` ? syntax=PASS ? selector evidence lines=42
- `scripts/audit_edgeiq_results_sectionals_v1.py` ? syntax=PASS ? selector evidence lines=11
- `scripts/audit_edgeiq_sectional_coverage_strategy_v1.py` ? syntax=PASS ? selector evidence lines=27
- `scripts/audit_edgeiq_sectional_pipeline.py` ? syntax=PASS ? selector evidence lines=22
- `scripts/audit_racingcom_batch_persistence_v1.py` ? syntax=PASS ? selector evidence lines=39
- `scripts/audit_racingcom_batch_recovery_v1.py` ? syntax=PASS ? selector evidence lines=24
- `scripts/audit_racingcom_rendered_speed_data_meeting_types_v1.py` ? syntax=PASS ? selector evidence lines=17
- `scripts/audit_racingcom_rendered_speed_data_non_harvested_v1.py` ? syntax=PASS ? selector evidence lines=83
- `scripts/audit_racingcom_sectional_warehouse_readiness_v1.py` ? syntax=PASS ? selector evidence lines=13
- `scripts/audit_racingcom_sectionals_coverage_v1.py` ? syntax=PASS ? selector evidence lines=68
- `scripts/audit_racingcom_speed_data_layout_variants_v1.py` ? syntax=PASS ? selector evidence lines=57
- `scripts/build_edgeiq_execution_board_sectional_layer_v1.py` ? syntax=PASS ? selector evidence lines=34
- `scripts/build_edgeiq_field_linked_sectional_escalation_v1.py` ? syntax=PASS ? selector evidence lines=8
- `scripts/build_edgeiq_form_sectional_profile_feed_v1.py` ? syntax=PASS ? selector evidence lines=9
- `scripts/build_edgeiq_form_sectional_terminal_feed_v1.py` ? syntax=PASS ? selector evidence lines=5
- `scripts/build_edgeiq_live_sectional_intelligence_v1.py` ? syntax=PASS ? selector evidence lines=47
- `scripts/build_edgeiq_race_sectional_rankings_v1.py` ? syntax=PASS ? selector evidence lines=47
- `scripts/build_edgeiq_race_sectional_rankings_v2.py` ? syntax=PASS ? selector evidence lines=74
- `scripts/build_edgeiq_race_sectional_read_v1.py` ? syntax=PASS ? selector evidence lines=46
- `scripts/build_edgeiq_racingcom_calendar_discovery_v1.py` ? syntax=PASS ? selector evidence lines=39
- `scripts/build_edgeiq_racingcom_canonical_speed_warehouse_v2.py` ? syntax=PASS ? selector evidence lines=117
- `scripts/build_edgeiq_racingcom_canonical_speed_warehouse_v2_1.py` ? syntax=PASS ? selector evidence lines=86
- `scripts/build_edgeiq_racingcom_csv_ingestion_v1.py` ? syntax=PASS ? selector evidence lines=89
- `scripts/build_edgeiq_racingcom_graphql_parser_v1.py` ? syntax=PASS ? selector evidence lines=78
- `scripts/build_edgeiq_racingcom_historical_calendar_backfill_v1.py` ? syntax=PASS ? selector evidence lines=29
- `scripts/build_edgeiq_racingcom_historical_calendar_backfill_v1_CHECKPOINT_BEFORE_DEPTH_INVESTIGATION_READ_20260621.py` ? syntax=PASS ? selector evidence lines=29
- `scripts/build_edgeiq_racingcom_rendered_results_harvester_v1.py` ? syntax=PASS ? selector evidence lines=31
- `scripts/build_edgeiq_racingcom_rendered_results_harvester_v2.py` ? syntax=PASS ? selector evidence lines=30
- `scripts/build_edgeiq_racingcom_results_warehouse_all_v1.py` ? syntax=PASS ? selector evidence lines=16
- `scripts/build_edgeiq_racingcom_runner_speed_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=160
- `scripts/build_edgeiq_racingcom_sectional_catalogue.py` ? syntax=PASS ? selector evidence lines=24
- `scripts/build_edgeiq_racingcom_three_day_race_list_v1.py` ? syntax=PASS ? selector evidence lines=22
- `scripts/build_edgeiq_racingcom_three_day_race_list_v1_CHECKPOINT_BEFORE_THREE_DAY_ROUTING_FINAL_20260710_132659.py` ? syntax=PASS ? selector evidence lines=22
- `scripts/build_edgeiq_raw_sectional_payload_discovery_v1.py` ? syntax=PASS ? selector evidence lines=108
- `scripts/build_edgeiq_raw_sectional_payload_schema_parser_v1.py` ? syntax=PASS ? selector evidence lines=73
- `scripts/build_edgeiq_real_sectional_data_readiness_audit_v1.py` ? syntax=PASS ? selector evidence lines=18
- `scripts/build_edgeiq_real_sectional_physics_features_v1.py` ? syntax=PASS ? selector evidence lines=17
- `scripts/build_edgeiq_sectional_ability_engine_v1.py` ? syntax=PASS ? selector evidence lines=42
- `scripts/build_edgeiq_sectional_ability_engine_v2.py` ? syntax=PASS ? selector evidence lines=23
- `scripts/build_edgeiq_sectional_ability_engine_v3.py` ? syntax=PASS ? selector evidence lines=38
- `scripts/build_edgeiq_sectional_ability_ui_feed_v1.py` ? syntax=PASS ? selector evidence lines=63
- `scripts/build_edgeiq_sectional_ambiguity_diagnostics_v1.py` ? syntax=PASS ? selector evidence lines=22
- `scripts/build_edgeiq_sectional_archetype_cluster_v1.py` ? syntax=PASS ? selector evidence lines=7
- `scripts/build_edgeiq_sectional_edge_detection_v1.py` ? syntax=PASS ? selector evidence lines=19
- `scripts/build_edgeiq_sectional_failure_diagnostics_v1.py` ? syntax=PASS ? selector evidence lines=18
- `scripts/build_edgeiq_sectional_feature_engine_v1.py` ? syntax=PASS ? selector evidence lines=9
- `scripts/build_edgeiq_sectional_feature_engine_v2.py` ? syntax=PASS ? selector evidence lines=25
- `scripts/build_edgeiq_sectional_field_composition_match_v1.py` ? syntax=PASS ? selector evidence lines=53
- `scripts/build_edgeiq_sectional_health_engine.py` ? syntax=PASS ? selector evidence lines=26
- `scripts/build_edgeiq_sectional_identity_engine_v1.py` ? syntax=PASS ? selector evidence lines=35
- `scripts/build_edgeiq_sectional_identity_engine_v2.py` ? syntax=PASS ? selector evidence lines=23
- `scripts/build_edgeiq_sectional_identity_engine_v3.py` ? syntax=PASS ? selector evidence lines=17
- `scripts/build_edgeiq_sectional_intelligence_engine_v1.py` ? syntax=PASS ? selector evidence lines=24
- `scripts/build_edgeiq_sectional_intelligence_engine_v2.py` ? syntax=PASS ? selector evidence lines=37
- `scripts/build_edgeiq_sectional_intelligence_ui_feed_v1.py` ? syntax=PASS ? selector evidence lines=58
- `scripts/build_edgeiq_sectional_intelligence_v1.py` ? syntax=PASS ? selector evidence lines=20
- `scripts/build_edgeiq_sectional_market_comparison_v1.py` ? syntax=PASS ? selector evidence lines=21
- `scripts/build_edgeiq_sectional_market_comparison_v2.py` ? syntax=PASS ? selector evidence lines=24
- `scripts/build_edgeiq_sectional_master_reconciliation_v1.py` ? syntax=PASS ? selector evidence lines=85
- `scripts/build_edgeiq_sectional_master_v1.py` ? syntax=PASS ? selector evidence lines=33
- `scripts/build_edgeiq_sectional_match_quality_audit_v1.py` ? syntax=PASS ? selector evidence lines=215
- `scripts/build_edgeiq_sectional_normalisation_v1.py` ? syntax=PASS ? selector evidence lines=21
- `scripts/build_edgeiq_sectional_outcome_tracking_v1.py` ? syntax=PASS ? selector evidence lines=8
- `scripts/build_edgeiq_sectional_payload_quality_engine_v1.py` ? syntax=PASS ? selector evidence lines=28
- `scripts/build_edgeiq_sectional_payload_reconstruction_v1.py` ? syntax=PASS ? selector evidence lines=74
- `scripts/build_edgeiq_sectional_physics_validation_v1.py` ? syntax=PASS ? selector evidence lines=23
- `scripts/build_edgeiq_sectional_position_audit_v1.py` ? syntax=PASS ? selector evidence lines=29
- `scripts/build_edgeiq_sectional_probability_realism_v1.py` ? syntax=PASS ? selector evidence lines=18
- `scripts/build_edgeiq_sectional_profiles_v1.py` ? syntax=PASS ? selector evidence lines=55
- `scripts/build_edgeiq_sectional_profiles_v2.py` ? syntax=PASS ? selector evidence lines=47
- `scripts/build_edgeiq_sectional_promotion_audit_v1.py` ? syntax=PASS ? selector evidence lines=22
- `scripts/build_edgeiq_sectional_resolution_backlog_v1.py` ? syntax=PASS ? selector evidence lines=15
- `scripts/build_edgeiq_sectional_sandbox_lab_v1.py` ? syntax=PASS ? selector evidence lines=12
- `scripts/build_edgeiq_sectional_schema_v2.py` ? syntax=PASS ? selector evidence lines=38
- `scripts/build_edgeiq_sectional_scraper_inventory.py` ? syntax=PASS ? selector evidence lines=17
- `scripts/build_edgeiq_sectional_signal_calibration_v1.py` ? syntax=PASS ? selector evidence lines=24
- `scripts/build_edgeiq_sectional_source_coverage_audit_v1.py` ? syntax=PASS ? selector evidence lines=16
- `scripts/build_edgeiq_sectional_source_ingestion_v1.py` ? syntax=PASS ? selector evidence lines=54
- `scripts/build_edgeiq_sectional_speed_map_positions_v2.py` ? syntax=PASS ? selector evidence lines=81
- `scripts/build_edgeiq_sectional_speed_map_positions_v3.py` ? syntax=PASS ? selector evidence lines=39
- `scripts/build_edgeiq_sectional_strength_engine_v1.py` ? syntax=PASS ? selector evidence lines=97
- `scripts/build_edgeiq_sectional_strength_v2.py` ? syntax=PASS ? selector evidence lines=59
- `scripts/build_edgeiq_sectional_tempo_engine_v1.py` ? syntax=PASS ? selector evidence lines=18
- `scripts/build_edgeiq_sectional_validation_engine.py` ? syntax=PASS ? selector evidence lines=38
- `scripts/build_edgeiq_sectional_value_plays_v1.py` ? syntax=PASS ? selector evidence lines=42
- `scripts/build_edgeiq_sectionals_retry_queue_v1.py` ? syntax=PASS ? selector evidence lines=17
- `scripts/build_edgeiq_standardised_sectionals_v1.py` ? syntax=PASS ? selector evidence lines=21
- `scripts/build_edgeiq_targeted_sectional_harvest_pipeline_v1.py` ? syntax=PASS ? selector evidence lines=26
- `scripts/build_edgeiq_trusted_sectional_universe.py` ? syntax=PASS ? selector evidence lines=29
- `scripts/build_edgeiq_trusted_sectional_universe_v2.py` ? syntax=PASS ? selector evidence lines=13
- `scripts/build_edgeiq_vic_dom_sectional_parser_v1.py` ? syntax=PASS ? selector evidence lines=24
- `scripts/build_edgeiq_vic_dom_sectional_parser_v2.py` ? syntax=PASS ? selector evidence lines=9
- `scripts/build_edgeiq_vic_dom_sectional_parser_v3.py` ? syntax=PASS ? selector evidence lines=8
- `scripts/build_edgeiq_vic_dom_sectional_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=24
- `scripts/build_edgeiq_vic_historical_sectional_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=24
- `scripts/build_edgeiq_vic_racingcom_browser_csv_downloader_v1.py` ? syntax=PASS ? selector evidence lines=60
- `scripts/build_edgeiq_vic_racingcom_speed_data_ingestion_v1.py` ? syntax=PASS ? selector evidence lines=58
- `scripts/build_edgeiq_vic_real_chrome_csv_capture_v1.py` ? syntax=PASS ? selector evidence lines=23
- `scripts/build_edgeiq_vic_real_chrome_csv_capture_v2.py` ? syntax=PASS ? selector evidence lines=44
- `scripts/build_edgeiq_vic_sectional_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=25
- `scripts/build_racingcom_form_speed_data_url_audit_v1.py` ? syntax=PASS ? selector evidence lines=48
- `scripts/build_racingcom_historical_meeting_discovery_v1.py` ? syntax=PASS ? selector evidence lines=104
- `scripts/build_racingcom_layout_b_derived_metrics_v1.py` ? syntax=PASS ? selector evidence lines=8
- `scripts/build_racingcom_rendered_speed_data_harvester_v1.py` ? syntax=PASS ? selector evidence lines=137
- `scripts/build_racingcom_sectional_history_harvest_v1.py` ? syntax=PASS ? selector evidence lines=82
- `scripts/build_racingcom_sectional_history_master_v1.py` ? syntax=PASS ? selector evidence lines=119
- `scripts/build_racingcom_sectional_warehouse_v1.py` ? syntax=PASS ? selector evidence lines=70
- `scripts/build_racingcom_sectional_warehouse_v2.py` ? syntax=PASS ? selector evidence lines=68
- `scripts/build_racingcom_sectionals_from_downloads_v1.py` ? syntax=PASS ? selector evidence lines=95
- `scripts/build_universal_sectional_memory_v1.py` ? syntax=PASS ? selector evidence lines=27
- `scripts/capture_racingcom_public_sectionals_v1.py` ? syntax=PASS ? selector evidence lines=56
- `scripts/click_visible_racingcom_csv_now_v1.py` ? syntax=PASS ? selector evidence lines=14
- `scripts/create_edgeiq_racingcom_speed_semantics_v1_1.py` ? syntax=PASS ? selector evidence lines=23
- `scripts/diagnose_edgeiq_racingcom_payload_admission_gap_v1.py` ? syntax=PASS ? selector evidence lines=113
- `scripts/discover_racingcom_calendar_speed_data_csv_v1.py` ? syntax=PASS ? selector evidence lines=60
- `scripts/discover_racingcom_speed_data_client_assets_v1.py` ? syntax=PASS ? selector evidence lines=58
- `scripts/discover_racingcom_speed_data_csv_browser_v1.py` ? syntax=PASS ? selector evidence lines=58
- `scripts/discover_real_vic_racingcom_meetings_90day_v1.py` ? syntax=PASS ? selector evidence lines=14
- `scripts/fix_app_sectional_execution_feed.py` ? syntax=PASS ? selector evidence lines=10
- `scripts/fix_formtab_sectionals.py` ? syntax=PASS ? selector evidence lines=4
- `scripts/fix_speedmap_sectionals.py` ? syntax=PASS ? selector evidence lines=14
- `scripts/fix_speedmap_topsectional_type.py` ? syntax=PASS ? selector evidence lines=8
- `scripts/force_patch_speedmap_sectional_fields.py` ? syntax=PASS ? selector evidence lines=5
- `scripts/investigate_racingcom_historical_depth_v1.py` ? syntax=PASS ? selector evidence lines=86
- `scripts/patch_racingcom_network_probe_getraceform_v1.py` ? syntax=PASS ? selector evidence lines=3
- `scripts/patch_speedmap_maprunner_real_sectionals.py` ? syntax=PASS ? selector evidence lines=4
- `scripts/patch_speedmap_runner_sectional_fields.py` ? syntax=PASS ? selector evidence lines=5
- `scripts/probe_racingcom_completed_speed_payload_v1.py` ? syntax=PASS ? selector evidence lines=47
- `scripts/probe_racingcom_speed_data_network_v1.before_getraceform_patch_20260722_041926.py` ? syntax=PASS ? selector evidence lines=23
- `scripts/probe_racingcom_speed_data_network_v1.py` ? syntax=PASS ? selector evidence lines=23
- `scripts/recover_racingcom_historical_batches_v1.py` ? syntax=PASS ? selector evidence lines=25
- `scripts/research_edgeiq_sectional_data_access_feasibility_v1.py` ? syntax=PASS ? selector evidence lines=58
- `scripts/research_edgeiq_sectional_source_expansion_v1.py` ? syntax=PASS ? selector evidence lines=77
- `scripts/run_edgeiq_open_tabs_sectional_harvest_final_v1.py` ? syntax=PASS ? selector evidence lines=28
- `scripts/run_edgeiq_open_tabs_sectional_harvest_v1.py` ? syntax=PASS ? selector evidence lines=28
- `scripts/run_edgeiq_vic_90day_sectional_backfill_final_v1.py` ? syntax=PASS ? selector evidence lines=26
- `scripts/run_edgeiq_vic_90day_sectional_backfill_v1.py` ? syntax=PASS ? selector evidence lines=27
- `scripts/run_edgeiq_vic_90day_sectional_backfill_v2.py` ? syntax=PASS ? selector evidence lines=29
- `scripts/run_edgeiq_vic_90day_sectional_backfill_v4.py` ? syntax=PASS ? selector evidence lines=26
- `scripts/run_edgeiq_vic_real_90day_sectional_backfill_v1.py` ? syntax=PASS ? selector evidence lines=33

## Preliminary forensic decision

**RAW_PAYLOAD_TO_GOVERNED_REFERENCE_GAP_PRESENT**

Raw payload files exist that cannot be matched to provenance references in the governed V1 speed datasets.

## Required next interpretation

Use the script evidence CSV to identify the first builder that enumerates raw payloads and compare its discovery rules against the unreferenced raw inventory. Do not modify that builder until its exclusion mechanism is proven.

## Diagnostic artifacts

- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_payload_admission_gap_v1.json`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_raw_payload_inventory_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_payload_reference_inventory_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_payload_selector_script_evidence_v1.csv`
