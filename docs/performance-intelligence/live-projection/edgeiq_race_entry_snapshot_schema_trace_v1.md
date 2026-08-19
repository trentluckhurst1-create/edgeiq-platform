# EDGEIQ Race-Entry Snapshot Schema Trace V1

Status: `EDGEIQ_RACE_ENTRY_SNAPSHOT_SCHEMA_TRACE_COMPLETE`

## Current Race-Entry Fact

- File: `public\data\edgeiq_race_entry_fact_v1.csv`
- Exists: `True`
- Rows: `204`

## Current Columns

- `canonical_race_id`
- `canonical_runner_id`
- `race_date`
- `meeting_date`
- `canonical_track`
- `course_identity`
- `state`
- `country`
- `race_number`
- `race_name`
- `race_distance_metres`
- `surface_group`
- `track_condition_number`
- `scheduled_start_time`
- `saddlecloth_number`
- `runner_name`
- `barrier`
- `weight_kg`
- `jockey_name`
- `trainer_name`
- `declaration_status`
- `scratching_status`
- `source_updated_at`
- `source_system`
- `source_record_id`
- `source_hash`
- `audit_status`

## Likely Active Builders

### `scripts\add_edgeiq_command_context_strip_2l.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `raceContextStrip`

### `scripts\add_edgeiq_command_race_context_contract_2g.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `race`

### `scripts\add_edgeiq_toolbar_jump_context_2k.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- No likely column literals detected.

### `scripts\apply_edgeiq_australian_synthetic_performance_v2.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `BLOCKED_AMBIGUOUS_SURFACE`
- `BLOCKED_UNSUPPORTED_SURFACE`
- `CANONICAL_SURFACE_REGISTRY_BUILT`
- `DISTANCE_EXACT`
- `EDGEIQ_CANONICAL_SURFACE_REGISTRY_V1`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_GENUINE_EPI_INPUT`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_FAIL`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_FULL_LIVE_PASS`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_LIVE_PARTIAL_SOURCE_COVERAGE`
- `EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2`
- `EPI_INPUTS_PARTIAL_PROJECTED_PERFORMANCE_MISSING`
- `INVALID_TRACK_CONDITION_NUMBER`
- `LENGTHS_V_STANDARD_V2_CANDIDATE_BUILT`
- `MISSING_SURFACE`
- `MISSING_TRACK_CONDITION_NUMBER`
- `NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH`
- `PERFORMANCE_BASE_ROWS_BUILT`
- `PERFORMANCE_INTELLIGENCE_ONLY`
- `PERFORMANCE_INTELLIGENCE_PRODUCTION_V2_REVIEW_REQUIRED`
- `PERFORMANCE_INTELLIGENCE_PRODUCTION_V2_SYNTHETIC_CHAIN_PASS`
- `PERFORMANCE_INTELLIGENCE_PROGRAM_SMOKE_PASS`
- `RUNNER_SECTIONAL_PERFORMANCE_V2_BUILT`
- `STANDARD_TIME_ELIGIBLE`
- `Surface`
- `TRACK`
- `UNSUPPORTED_SURFACE`
- `audit_status`
- `candidate_exists`
- `candidate_hash`
- `candidate_hash_comparison`
- `candidate_paths_active`
- `canonical_race_id`
- `canonical_runner_id`
- `canonical_surface_group`
- `canonical_surface_groups`
- `canonical_track`
- `conversion_status`
- `coverage_status`
- `elapsed_time_observations`
- `elapsed_time_seconds`
- `eligibility_status`
- `final_status`
- `method_status`
- `official_distance_metres`
- `performance_fact_rows`
- `performance_intelligence_base`
- `performance_intelligence_base_rows`
- `production_orchestration_status`
- `production_runner_warehouse_hash`
- `projected_performance_rows`
- `race_date`
- `race_distance_metres`
- `race_entry_projected_performance`
- `race_entry_projected_performance_rows`
- `race_key`
- `race_number`
- `race_time_delta_id`
- `races`
- `runner_input_rows`
- `runner_rows`
- `runner_sectional_v2`
- `runners`
- `sectional_performance_rows`
- `segment_distance_metres`
- `source_race_time_delta_evidence_sha256`
- `source_surface`
- `source_track_name`
- `standard_time_eligibility_status`
- `standard_time_facts`
- `standard_time_groups_available`
- `standard_time_id`
- `standard_time_rows`
- `standard_time_seconds`
- `standard_times`
- `status`
- `surface_group`
- `surface_registry`
- `surface_registry_audit`
- `time_delta_seconds`
- `time_difference_seconds`
- `track`
- `track_condition`
- `track_condition_group`
- `track_condition_number`
- `track_name`
- `track_rating_number`
- `winner_horse_name`
- `winner_race_time_seconds`

### `scripts\audit_edgeiq_context_engine_v1_source.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `BARRIER_BUCKET`
- `CLASS_BUCKET`
- `CONTEXT_BUCKET`
- `DISTANCE_BUCKET`
- `JOCKEY`
- `TRACK`
- `TRAINER`
- `TRAINER_JOCKEY`
- `barrier`
- `distance`
- `jockey_canonical`
- `race_class`
- `status`
- `track`
- `track_condition`
- `trainer_canonical`
- `trainer_jockey_canonical`
- `unique_jockeys`
- `unique_tracks`
- `unique_trainer_jockey_combos`
- `unique_trainers`

### `scripts\audit_edgeiq_context_warehouse_v1_quality.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CONTEXT_EDGE`
- `CONTEXT_RISK`
- `MILD_CONTEXT_EDGE`
- `blank_context_type`
- `context_type`
- `status`

### `scripts\audit_edgeiq_epi_context_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `BARRIER`
- `CLASS`
- `DATE`
- `DISTANCE`
- `EDGEIQ_EPI_CONTEXT_V1_AUDIT_FAIL`
- `EDGEIQ_EPI_CONTEXT_V1_AUDIT_PASS`
- `JOCKEY`
- `TRACK`
- `TRAINER`
- `WEIGHT`
- `all_populated_tiles_have_valid_context`
- `contexts_checked`
- `horse`
- `populated_contexts_present`
- `status`

### `scripts\audit_edgeiq_epi_performance_dependency_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `EPI_INPUTS_PARTIAL_PROJECTED_PERFORMANCE_MISSING`
- `audit_status`
- `coverage_status`
- `performance_intelligence_base`
- `performance_intelligence_base_rows`
- `projected_performance_rows`
- `race_entry_projected_performance`
- `status`

### `scripts\audit_edgeiq_horse_performance_rating_builder_trace_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `ACTIVE_RATING_AUDIT`
- `ACTIVE_RATING_BUILDER`
- `ARCHIVED_HISTORICAL_RATING_BUILDER`
- `CANDIDATE`
- `CANDIDATE_DEFINED`
- `DOWNSTREAM_PROJECTED_PERFORMANCE_AUDIT`
- `DOWNSTREAM_PROJECTED_PERFORMANCE_BUILDER`
- `PROJECTED_PERFORMANCE_REFERENCE`
- `RATING_METHOD`
- `STATUS`
- `UPSTREAM_HORSE_PERFORMANCE_AUDIT`
- `UPSTREAM_HORSE_PERFORMANCE_BUILDER`
- `audit_edgeiq_horse_performance_`
- `audit_edgeiq_race_entry_projected_performance`
- `build_edgeiq_historical_performance_rating`
- `build_edgeiq_horse_performance_`
- `build_edgeiq_race_entry_projected_performance`
- `candidate_path`
- `classification`
- `consumes_projected_performance`
- `consumes_rating_fact`
- `edgeiq_horse_performance_rating_fact_v1`
- `entry_function`
- `horse_performance`
- `horse_performance_rating`
- `projected_performance`
- `race_entry_projected_performance`
- `rating_method`
- `trace_rows`

### `scripts\audit_edgeiq_nexus_contextual_intelligence_v2.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `barrier`
- `context_band`
- `context_type`
- `context_value`
- `contextual_score`
- `horse_run_style`
- `jockey`
- `jockey_best_context`
- `jockey_best_style`
- `jockey_context`
- `jockey_context_score`
- `jockey_recent_100_win_pct`
- `jockey_recent_25_win_pct`
- `jockey_recent_50_win_pct`
- `live_contextual_feed`
- `live_contextual_feed_rows_gt_0_if_live_exists`
- `nexus_context_band`
- `nexus_context_score`
- `nexus_context_score_populated_for_live_rows`
- `no_forbidden_barrier_specialist_outputs_or_columns`
- `partnership_context`
- `race_date`
- `race_no`
- `runner_key`
- `runner_name`
- `status`
- `track`
- `trainer`
- `trainer_best_context`
- `trainer_best_style`
- `trainer_context`
- `trainer_context_score`
- `trainer_recent_100_win_pct`
- `trainer_recent_25_win_pct`
- `trainer_recent_50_win_pct`

### `scripts\audit_edgeiq_official_source_race_context_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `barrier`
- `carried_weight`
- `class`
- `class_columns`
- `class_name`
- `context_categories`
- `context_fields`
- `date`
- `distance`
- `has_class`
- `has_race_grade`
- `has_race_id`
- `has_race_name`
- `has_race_no`
- `has_source_race_key`
- `horse`
- `horse_all_form_url`
- `horse_code`
- `horse_key`
- `horse_name`
- `horse_url`
- `is_race_context_field`
- `official_time`
- `race_class`
- `race_class_band`
- `race_class_clean`
- `race_class_raw`
- `race_date`
- `race_entry`
- `race_grade`
- `race_grade_columns`
- `race_id`
- `race_id_columns`
- `race_name`
- `race_name_columns`
- `race_no`
- `race_no_columns`
- `race_no_missing_count`
- `race_time`
- `raw_context`
- `run_date`
- `runner`
- `runner_key`
- `source_race_key`
- `source_race_key_columns`
- `source_race_no`
- `track`
- `track_code`
- `track_condition`
- `weight`
- `weight_carried`

### `scripts\audit_edgeiq_performance_intelligence_deterministic_rerun_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `status`

### `scripts\audit_edgeiq_performance_intelligence_final_live_v2.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_GENUINE_EPI_INPUT`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_PROJECTED_FACT_INPUT`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_FAIL`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_FULL_LIVE_PASS`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_LIVE_PARTIAL_SOURCE_COVERAGE`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_NO_ACTIVE_RACE_ENTRIES`
- `EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2`
- `NO_ACTIVE_RACE_ENTRIES_AVAILABLE`
- `PARTIAL_PROJECTED_PERFORMANCE_MISSING`
- `PERFORMANCE_BASE_ROWS_BUILT`
- `PERFORMANCE_INTELLIGENCE_PRODUCTION_V2_SYNTHETIC_CHAIN_PASS`
- `PERFORMANCE_INTELLIGENCE_PROGRAM_SMOKE_PASS`
- `STANDARD_TIME_ELIGIBLE`
- `Surface`
- `audit_status`
- `canonical_surface_group`
- `canonical_surface_groups`
- `eligibility_status`
- `final_status`
- `method_status`
- `overall_status`
- `performance_fact_rows`
- `production_orchestration_status`
- `production_runner_warehouse_hash`
- `race_entry_projected_performance_rows`
- `sectional_performance_rows`
- `standard_time_eligibility_status`
- `standard_time_rows`
- `standard_times`
- `status`

### `scripts\audit_edgeiq_price_truth_snapshot_dedupe_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `blank_timestamp_flag_v1`
- `blank_timestamp_rows`
- `dedupe_status`
- `dedupe_status_counts`
- `dedupe_status_v1`
- `duplicate_same_horse_race_timestamp_count_v1`
- `duplicate_same_horse_same_race_timestamp_flag_v1`
- `duplicate_same_horse_same_race_timestamp_groups`
- `duplicate_same_horse_same_race_timestamp_rows`
- `duplicated_full_row_same_timestamp_count_v1`
- `duplicated_full_row_same_timestamp_flag_v1`
- `duplicated_full_row_same_timestamp_groups`
- `duplicated_full_row_same_timestamp_rows`
- `exact_snapshot_runner_key_v1`
- `horse`
- `horse_key`
- `horse_key_clean_v1`
- `horse_name_key_v1`
- `malformed_timestamp_flag_v1`
- `malformed_timestamp_rows`
- `race_context_key_v1`
- `race_date`
- `race_no`
- `race_no_key_v1`
- `races_in_snapshot_v1`
- `races_per_snapshot`
- `runners_in_snapshot_v1`
- `runners_per_snapshot`
- `same_horse_race_timestamp_key_v1`
- `snapshot_fewer_than_87_runners_flag_v1`
- `snapshot_fewer_than_8_races_flag_v1`
- `snapshot_timestamp`
- `snapshot_timestamp_clean`
- `snapshots_with_fewer_than_87_runners`
- `snapshots_with_fewer_than_8_races`
- `status`
- `track`
- `track_key_v1`

### `scripts\audit_edgeiq_projected_performance_epi_activation_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `True`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `HISTORICAL_RATING_AVAILABLE`
- `PROJECTED_PERFORMANCE_UNAVAILABLE`
- `RACE_ENTRY_SNAPSHOT_BUILDER_SCHEMA_MISMATCH`
- `SUITABILITY_CONTEXT_INPUTS_UNAVAILABLE`
- `active_runners_with_epi`
- `active_runners_without_epi`
- `epi_status`
- `historical_rating_matches`
- `match_status`
- `projected_performance`
- `projected_performance_rows`
- `projected_status`
- `race_entry_input_rows`
- `status`
- `temporally_eligible_ratings`

### `scripts\audit_edgeiq_race_entry_context_adjusted_performance_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CONTEXT_INELIGIBLE`
- `CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTED_PERFORMANCE`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_AUDIT_PASS`
- `GOVERNED_CONTEXT_ADJUSTED_PERFORMANCE`
- `GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `PERFORMANCE_ADJUSTED`
- `adjusted_performance_arithmetic_exact`
- `adjusted_performance_ids_unique`
- `adjusted_performance_population_exact`
- `canonical_horse_id`
- `canonical_horse_name`
- `context_adjusted_performance_decision`
- `context_adjusted_performance_rows`
- `context_adjusted_performance_value`
- `context_adjustment_rows`
- `context_ineligible_rows`
- `context_parameter_id`
- `decisions_and_statuses_governed`
- `edgeiq_race_entry_context_adjusted_performance_fact_v1`
- `historical_rating_value`
- `one_output_per_context_adjustment`
- `performance_adjusted_rows`
- `race_date`
- `race_entry_context_adjusted_performance_evidence_sha256`
- `race_entry_context_adjusted_performance_id`
- `race_entry_context_adjusted_performance_status`
- `race_entry_context_adjustment_id`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_id`
- `race_entry_id`
- `race_entry_performance_context_id`
- `race_id`
- `runner_id`
- `status`
- `total_context_adjustment`

### `scripts\audit_edgeiq_race_entry_context_adjustment_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CONTEXT_INELIGIBLE`
- `CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTMENT`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_AUDIT_PASS`
- `GOVERNED_CONTEXT_ADJUSTMENT_APPLIED`
- `GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `barrier_adjustment`
- `canonical_horse_id`
- `canonical_horse_name`
- `class_adjustment`
- `context_adjustment_application_decision`
- `context_adjustment_rows`
- `context_ineligible_rows`
- `context_parameter_id`
- `context_parameter_selection_rows`
- `distance_adjustment`
- `edgeiq_race_entry_context_adjustment_fact_v1`
- `historical_rating_value`
- `race_date`
- `race_entry_context_adjustment_evidence_sha256`
- `race_entry_context_adjustment_id`
- `race_entry_context_adjustment_status`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_id`
- `race_entry_id`
- `race_entry_performance_context_id`
- `race_id`
- `runner_id`
- `source_context_builder_version`
- `source_context_evidence_sha256`
- `status`
- `surface_adjustment`
- `total_context_adjustment`
- `track_adjustment`
- `track_condition_adjustment`
- `track_configuration_adjustment`
- `weight_adjustment`

### `scripts\audit_edgeiq_race_entry_context_eligibility_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `ALL_REQUIRED_CONTEXT_ELIGIBLE`
- `COMPLETE_CONTEXT_ELIGIBLE`
- `COMPLETE_CONTEXT_INELIGIBLE`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ELIGIBILITY_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ELIGIBILITY_FACT_V1_AUDIT_PASS`
- `INELIGIBLE_INVALID_CONTEXT`
- `INELIGIBLE_MISSING_CONTEXT`
- `INELIGIBLE_UNSUPPORTED_CONTEXT`
- `allocated_weight_eligibility`
- `barrier_context_eligibility`
- `canonical_horse_id`
- `canonical_horse_name`
- `class_context_eligibility`
- `complete_context_eligibility`
- `complete_context_eligible_rows`
- `complete_context_ineligible_rows`
- `distance_context_eligibility`
- `edgeiq_race_entry_context_eligibility_fact_v1`
- `historical_rating_eligibility`
- `one_eligibility_row_per_context`
- `primary_context_eligibility_reason_code`
- `race_date`
- `race_entry_context_eligibility_evidence_sha256`
- `race_entry_context_eligibility_id`
- `race_entry_context_eligibility_rows`
- `race_entry_context_eligibility_status`
- `race_entry_horse_performance_snapshot_id`
- `race_entry_id`
- `race_entry_performance_context_evidence_sha256`
- `race_entry_performance_context_id`
- `race_entry_performance_context_rows`
- `race_id`
- `rail_context_eligibility`
- `runner_id`
- `source_context_builder_version`
- `source_context_evidence_sha256`
- `source_context_lineage`
- `source_context_rows`
- `status`
- `surface_context_eligibility`
- `track_condition_eligibility`
- `track_configuration_eligibility`
- `track_context_eligibility`

### `scripts\audit_edgeiq_race_entry_context_parameter_selection_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CONTEXT_INELIGIBLE`
- `CONTEXT_NOT_ELIGIBLE_FOR_PARAMETER_SELECTION`
- `EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_AUDIT_PASS`
- `EXACT_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `EXACT_CONTEXT_PARAMETER_SELECTED`
- `canonical_horse_id`
- `canonical_horse_name`
- `complete_context_eligibility`
- `context_eligibility_rows`
- `context_exists`
- `context_ineligible_rows`
- `context_parameter_id`
- `context_parameter_registry_rows`
- `context_parameter_selection_decision`
- `context_parameter_selection_rows`
- `context_required_when_eligibility_rows_exist`
- `context_signature_sha256`
- `edgeiq_race_entry_context_parameter_selection_fact_v1`
- `performance_context_rows`
- `race_date`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_evidence_sha256`
- `race_entry_context_parameter_selection_id`
- `race_entry_context_parameter_selection_status`
- `race_entry_id`
- `race_entry_performance_context_id`
- `race_id`
- `runner_id`
- `source_context_builder_version`
- `source_context_evidence_sha256`
- `status`

### `scripts\audit_edgeiq_race_entry_epi_component_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_EPI_COMPONENT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_EPI_COMPONENT_FACT_V1_AUDIT_PASS`
- `GOVERNED_RACE_ENTRY_EPI_COMPONENT`
- `HISTORICAL_PERFORMANCE`
- `RACE_CONTEXT`
- `SUITABILITY`
- `authorised_component_weight`
- `edgeiq_race_entry_epi_component_fact_v1`
- `epi_component_status`
- `race_component_population_count`
- `race_date`
- `race_entry_count`
- `race_entry_epi_component_evidence_sha256`
- `race_entry_epi_component_id`
- `race_entry_id`
- `race_id`
- `status`
- `three_components_per_entry`
- `weighted_component_value`

### `scripts\audit_edgeiq_race_entry_epi_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_EPI_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_EPI_FACT_V1_AUDIT_PASS`
- `GOVERNED_RACE_ENTRY_EPI`
- `HISTORICAL_PERFORMANCE`
- `NORMALISED_WEIGHTED_ADDITIVE_EPI_V1`
- `RACE_CONTEXT`
- `SUITABILITY`
- `authorised_component_weight`
- `edgeiq_race_entry_epi_fact_v1`
- `eligible_race_entry_count`
- `epi_status`
- `historical_performance_component_evidence_sha256`
- `historical_performance_component_id`
- `historical_performance_normalised_value`
- `historical_performance_weight`
- `historical_performance_weighted_value`
- `race_context_component_evidence_sha256`
- `race_context_component_id`
- `race_context_normalised_value`
- `race_context_weight`
- `race_context_weighted_value`
- `race_date`
- `race_entry_epi_component_evidence_sha256`
- `race_entry_epi_component_id`
- `race_entry_epi_evidence_sha256`
- `race_entry_epi_id`
- `race_entry_epi_rows`
- `race_entry_id`
- `race_id`
- `status`
- `suitability_component_evidence_sha256`
- `suitability_component_id`
- `suitability_normalised_value`
- `suitability_weight`
- `suitability_weighted_value`
- `total_component_weight`
- `weight`
- `weighted`
- `weighted_component_total`
- `weighted_component_value`

### `scripts\audit_edgeiq_race_entry_epi_ordering_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_AUDIT_PASS`
- `GOVERNED_RACE_ENTRY_EPI_ORDERING`
- `edgeiq_race_entry_epi_ordering_fact_v1`
- `epi_ordering_status`
- `epi_tie_status`
- `fact_races`
- `race_date`
- `race_entry_epi_ordering_evidence_sha256`
- `race_entry_epi_ordering_id`
- `race_entry_epi_relative_context_evidence_sha256`
- `race_entry_epi_relative_context_id`
- `race_entry_id`
- `race_id`
- `race_population_keys_exact`
- `relative_context_rows`
- `runner_epi_value`
- `source_race_count`
- `source_races`
- `status`

### `scripts\audit_edgeiq_race_entry_epi_publication_snapshot_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_PASS`
- `GOVERNED_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT`
- `RACE_ENTRY_EPI_SNAPSHOT_PUBLISHED`
- `RACE_ENTRY_EPI_SNAPSHOT_RECONCILED`
- `edgeiq_race_entry_epi_publication_snapshot_fact_v1`
- `epi_tie_status`
- `race_count`
- `race_date`
- `race_entry_epi_ordering_evidence_sha256`
- `race_entry_epi_ordering_id`
- `race_entry_epi_publication_snapshot_evidence_sha256`
- `race_entry_epi_publication_snapshot_id`
- `race_entry_epi_relative_context_evidence_sha256`
- `race_entry_epi_snapshot_publication_decision`
- `race_entry_epi_snapshot_reconciliation_decision`
- `race_entry_epi_snapshot_status`
- `race_entry_id`
- `race_id`
- `race_ordering_reconciled`
- `runner_epi_value`
- `source_relative_context_evidence_sha256`
- `status`

### `scripts\audit_edgeiq_race_entry_epi_relative_context_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_AUDIT_PASS`
- `EPI_RELATIVE_CONTEXT_PUBLISHED`
- `EPI_RELATIVE_CONTEXT_RECONCILED`
- `GOVERNED_RACE_ENTRY_EPI_RELATIVE_CONTEXT`
- `deterministic_relative_context_evidence`
- `deterministic_relative_context_identity`
- `distance_above_minimum_epi`
- `distance_below_maximum_epi`
- `edgeiq_race_entry_epi_relative_context_fact_v1`
- `epi_relative_context_publication_decision`
- `epi_relative_context_reconciliation_decision`
- `epi_relative_context_status`
- `race_date`
- `race_entry_epi_evidence_sha256`
- `race_entry_epi_id`
- `race_entry_epi_relative_context_evidence_sha256`
- `race_entry_epi_relative_context_id`
- `race_entry_epi_rows`
- `race_entry_id`
- `race_epi_distribution_evidence_sha256`
- `race_epi_distribution_id`
- `race_epi_distribution_rows`
- `race_id`
- `relative_context_arithmetic_reconciled`
- `relative_context_governance_exact`
- `relative_context_lineage_complete`
- `relative_context_rows`
- `relative_context_sources_reconciled`
- `runner_epi_value`
- `status`

### `scripts\audit_edgeiq_race_entry_eri_context_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_ERI_CONTEXT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_ERI_CONTEXT_FACT_V1_AUDIT_PASS`
- `ERI_CONTEXT_PUBLISHED`
- `ERI_CONTEXT_RECONCILED`
- `GOVERNED_RACE_ENTRY_ERI_CONTEXT`
- `context_arithmetic_exact`
- `context_governance_complete`
- `context_ids_unique`
- `context_lineage_complete`
- `context_natural_keys_unique`
- `context_output_decimal_places`
- `context_rounding_mode`
- `deterministic_context_evidence`
- `deterministic_context_identity`
- `edgeiq_race_entry_eri_context_fact_v1`
- `eri_context_publication_decision`
- `eri_context_reconciliation_decision`
- `projected_performance_rows`
- `projected_performance_value`
- `projected_performance_vs_eri`
- `race_date`
- `race_entry_eri_context_evidence_sha256`
- `race_entry_eri_context_id`
- `race_entry_eri_context_rows`
- `race_entry_eri_context_status`
- `race_entry_id`
- `race_entry_projected_performance_evidence_sha256`
- `race_entry_projected_performance_id`
- `race_eri_evidence_sha256`
- `race_eri_id`
- `race_eri_parameter_id`
- `race_eri_rows`
- `race_id`
- `source_projected_performance_builder_version`
- `source_projected_performance_evidence_sha256`
- `source_race_eri_builder_version`
- `source_race_eri_evidence_sha256`
- `status`

### `scripts\audit_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py`

- Race-entry reference: `True`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_AUDIT_PASS`
- `POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE`
- `average_eligible_historical_rating_value`
- `canonical_horse_id`
- `canonical_horse_name`
- `edgeiq_race_entry_horse_performance_snapshot_fact_v1`
- `eligible_historical_rating_count`
- `first_eligible_rating_date`
- `highest_eligible_historical_rating_value`
- `horse_performance_rating_method`
- `horse_performance_rating_rows`
- `latest_eligible_rating_date`
- `lowest_eligible_historical_rating_value`
- `one_snapshot_per_race_entry`
- `point_in_time_boundary`
- `race_date`
- `race_entry_fact_exists`
- `race_entry_fact_not_required_for_empty_ratings`
- `race_entry_fact_required_when_ratings_exist`
- `race_entry_horse_performance_snapshot_evidence_sha256`
- `race_entry_horse_performance_snapshot_id`
- `race_entry_horse_performance_snapshot_rows`
- `race_entry_horse_performance_snapshot_status`
- `race_entry_id`
- `race_entry_rows`
- `race_id`
- `rating_age_days`
- `runner_id`
- `selected_horse_performance_rating_id`
- `selected_horse_performance_rating_value`
- `selected_rating_as_of_date`
- `source_eligible_rating_evidence_sha256`
- `source_eligible_rating_ids_sha256`
- `source_race_entry_evidence_sha256`
- `source_selected_rating_evidence_sha256`
- `status`

### `scripts\audit_edgeiq_race_entry_performance_context_fact_v1.py`

- Race-entry reference: `True`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_AUDIT_PASS`
- `FACTUAL_DECLARED_RACE_CONTEXT_GOVERNED`
- `allocated_weight_kg`
- `barrier`
- `canonical_horse_id`
- `canonical_horse_name`
- `context_governance`
- `context_historical_rating_value`
- `context_ids_unique`
- `context_numeric_governance`
- `context_population_exact`
- `context_rows`
- `deterministic_context_identity`
- `edgeiq_race_entry_performance_context_fact_v1`
- `historical_rating_preserved`
- `missing_context_rows`
- `one_context_per_snapshot`
- `race_class_code`
- `race_date`
- `race_distance_m`
- `race_entry_fact_exists`
- `race_entry_fact_not_required_for_empty_snapshots`
- `race_entry_fact_required_when_snapshots_exist`
- `race_entry_horse_performance_snapshot_id`
- `race_entry_horse_performance_snapshot_rows`
- `race_entry_id`
- `race_entry_performance_context_evidence_sha256`
- `race_entry_performance_context_id`
- `race_entry_performance_context_rows`
- `race_entry_performance_context_status`
- `race_entry_rows`
- `race_id`
- `racing_surface`
- `rating_age_days`
- `runner_id`
- `selected_horse_performance_rating_id`
- `selected_horse_performance_rating_value`
- `selected_rating_as_of_date`
- `source_race_entry_builder_version`
- `source_race_entry_evidence_sha256`
- `status`
- `track_condition`
- `track_configuration`
- `track_id`
- `track_name`
- `unexpected_context_rows`

### `scripts\audit_edgeiq_race_entry_projected_performance_builder_trace_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `False`

Likely referenced columns:

- `BUILDER_TRACE_WRITTEN`
- `EXPECTED_ADJUSTED_STATUS`
- `EXPECTED_AGGREGATE_STATUS`
- `PROJECTED_STATUS`
- `entry_function`
- `status`

### `scripts\audit_edgeiq_race_entry_projected_performance_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_AUDIT_PASS`
- `GOVERNED_PROJECTED_PERFORMANCE`
- `PROJECTED_PERFORMANCE_PUBLISHED`
- `PROJECTED_PERFORMANCE_RECONCILED`
- `adjusted_performance_ids_unique`
- `aggregate_suitability_value`
- `canonical_horse_id`
- `canonical_horse_name`
- `context_adjusted_performance_rows`
- `context_adjusted_performance_value`
- `context_parameter_id`
- `edgeiq_race_entry_projected_performance_fact_v1`
- `historical_rating_value`
- `projected_performance_delta_from_historical`
- `projected_performance_publication_decision`
- `projected_performance_reconciliation_decision`
- `projected_performance_rows`
- `projected_performance_value`
- `race_date`
- `race_entry_context_adjusted_performance_id`
- `race_entry_context_adjustment_id`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_id`
- `race_entry_id`
- `race_entry_performance_context_id`
- `race_entry_projected_performance_evidence_sha256`
- `race_entry_projected_performance_id`
- `race_entry_projected_performance_status`
- `race_entry_suitability_aggregate_id`
- `race_id`
- `runner_id`
- `source_adjusted_performance_builder_version`
- `source_adjusted_performance_evidence_sha256`
- `source_suitability_aggregate_builder_version`
- `source_suitability_aggregate_evidence_sha256`
- `status`
- `suitability_aggregate_ids_unique`
- `suitability_aggregate_rows`
- `total_context_adjustment`

### `scripts\audit_edgeiq_race_entry_projection_forensics_v1.py`

- Race-entry reference: `True`
- Projected-performance reference: `True`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `DUPLICATE_HISTORICAL_RATING_IDENTITY`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_PROJECTED_FACT_INPUT`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_NO_ACTIVE_RACE_ENTRIES`
- `FUTURE_OR_SAME_RACE_OBSERVATION`
- `NO_ACTIVE_RACE_ENTRIES_AVAILABLE`
- `PRIOR_RATING_ELIGIBLE`
- `active_projected_performance_builder`
- `canonical_horse_id`
- `canonical_horse_name`
- `collision_status`
- `current_or_future_race_entries`
- `current_race_entry_rows`
- `current_race_entry_source`
- `date_status_sample`
- `exact_runner_id_matches`
- `gate_status`
- `historical_performance_rows`
- `historical_performance_source`
- `historical_rating_available`
- `horse_code_matches`
- `horse_performance_rating_id`
- `likely_race_entry_source`
- `match_status`
- `overall_status`
- `prior_rating_matches`
- `projected_performance_candidate_rows`
- `projected_performance_hash`
- `projected_performance_production_rows`
- `race_date`
- `race_entry_id`
- `race_id`
- `rating_as_of_date`
- `rating_id`
- `runner_count`
- `runner_id`
- `runners_below_minimum`
- `runners_meeting_minimum`
- `temporal_status`

### `scripts\audit_edgeiq_race_entry_projection_row_funnel_v1.py`

- Race-entry reference: `True`
- Projected-performance reference: `True`
- Snapshot reference: `True`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `FUTURE_OR_SAME_RACE_OBSERVATION`
- `NO_CURRENT_RACE_ENTRY`
- `NO_HISTORICAL_PERFORMANCE`
- `canonical_horse_id`
- `canonical_horse_name`
- `canonical_race_id`
- `canonical_runner_id`
- `context_adjusted`
- `context_adjustment`
- `context_eligibility`
- `horse_performance_rating`
- `horse_snapshot`
- `join_status`
- `performance_context`
- `prior_rating_count`
- `projected_performance`
- `race_date`
- `race_entry_fact`
- `race_entry_id`
- `race_entry_rows`
- `race_id`
- `race_key`
- `rating_as_of_date`
- `rating_rows`
- `runner_id`
- `status`
- `suitability_aggregate`
- `suitability_component`
- `unique_races`
- `unique_runners`

### `scripts\audit_edgeiq_race_entry_snapshot_schema_trace_v1.py`

- Race-entry reference: `True`
- Projected-performance reference: `True`
- Snapshot reference: `True`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_SNAPSHOT_SCHEMA_TRACE_COMPLETE`
- `all_candidate_files`
- `barrier`
- `candidate_file_count`
- `class`
- `context`
- `date`
- `distance`
- `edgeiq_race_entry_fact_v1`
- `entry`
- `horse`
- `jockey`
- `performance`
- `projected_performance`
- `race`
- `race_entry`
- `race_entry_exists`
- `race_entry_fact`
- `race_entry_file`
- `race_entry_projected`
- `race_entry_projected_performance`
- `race_entry_rows`
- `rating`
- `references_context`
- `references_projected_performance`
- `references_race_entry`
- `references_suitability`
- `runner`
- `status`
- `suitability`
- `surface`
- `time`
- `track`
- `trainer`
- `weight`

### `scripts\audit_edgeiq_race_entry_suitability_aggregate_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `BARRIER`
- `CLASS`
- `CONTEXT_INELIGIBLE`
- `DISTANCE`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_AUDIT_PASS`
- `GOVERNED_SUITABILITY_AGGREGATE`
- `PERFORMANCE_ADJUSTED`
- `SUITABILITY_AGGREGATED`
- `SURFACE`
- `TRACK`
- `TRACK_CONDITION`
- `TRACK_CONFIGURATION`
- `WEIGHT`
- `actual_suitability_aggregate_rows`
- `adjusted_performance_ids_unique`
- `aggregate_suitability_value`
- `barrier_suitability_value`
- `canonical_horse_id`
- `canonical_horse_name`
- `class_suitability_value`
- `context_adjusted_performance_decision`
- `context_adjusted_performance_rows`
- `context_adjusted_performance_value`
- `context_ineligible_rows`
- `context_parameter_id`
- `distance_suitability_value`
- `edgeiq_race_entry_suitability_aggregate_fact_v1`
- `eligible_adjusted_performance_rows`
- `field_size_suitability_value`
- `historical_rating_value`
- `one_aggregate_per_eligible_entry`
- `race_date`
- `race_entry_context_adjusted_performance_id`
- `race_entry_context_adjustment_id`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_id`
- `race_entry_id`
- `race_entry_performance_context_id`
- `race_entry_suitability_aggregate_evidence_sha256`
- `race_entry_suitability_aggregate_id`
- `race_entry_suitability_aggregate_status`
- `race_entry_suitability_component_evidence_sha256`
- `race_id`
- `runner_id`
- `source_adjusted_performance_builder_version`
- `source_adjusted_performance_evidence_sha256`
- `status`
- `suitability_aggregate_decision`
- `suitability_aggregate_rows`
- `suitability_component_count`
- `suitability_component_rows`
- `suitability_component_type`
- `suitability_component_value`
- `surface_suitability_value`
- `total_context_adjustment`
- `track_condition_suitability_value`
- `track_configuration_suitability_value`
- `track_suitability_value`
- `weight_suitability_value`

### `scripts\audit_edgeiq_race_entry_suitability_component_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `BARRIER`
- `CLASS`
- `CONTEXT_INELIGIBLE`
- `DISTANCE`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_AUDIT_PASS`
- `GOVERNED_SUITABILITY_COMPONENT`
- `PERFORMANCE_ADJUSTED`
- `SURFACE`
- `TRACK`
- `TRACK_CONDITION`
- `TRACK_CONFIGURATION`
- `WEIGHT`
- `barrier_adjustment`
- `canonical_horse_id`
- `canonical_horse_name`
- `class_adjustment`
- `context_adjusted_performance_decision`
- `context_adjusted_performance_rows`
- `context_adjusted_performance_value`
- `context_adjustment_rows`
- `context_ineligible_rows`
- `context_parameter_id`
- `distance_adjustment`
- `edgeiq_race_entry_suitability_component_fact_v1`
- `eligible_adjusted_performance_rows`
- `historical_rating_value`
- `nine_components_per_eligible_entry`
- `race_date`
- `race_entry_context_adjusted_performance_id`
- `race_entry_context_adjustment_id`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_id`
- `race_entry_id`
- `race_entry_performance_context_id`
- `race_entry_suitability_component_evidence_sha256`
- `race_entry_suitability_component_id`
- `race_entry_suitability_component_status`
- `race_id`
- `runner_id`
- `source_adjusted_performance_builder_version`
- `source_adjusted_performance_evidence_sha256`
- `source_context_adjustment_builder_version`
- `source_context_adjustment_evidence_sha256`
- `status`
- `suitability_component_decision`
- `suitability_component_rows`
- `suitability_component_type`
- `suitability_component_value`
- `surface_adjustment`
- `total_context_adjustment`
- `track_adjustment`
- `track_condition_adjustment`
- `track_configuration_adjustment`
- `weight_adjustment`

### `scripts\audit_edgeiq_race_epi_publication_snapshot_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_PASS`
- `GOVERNED_RACE_EPI_PUBLICATION_SNAPSHOT`
- `RACE_EPI_SNAPSHOT_PUBLISHED`
- `RACE_EPI_SNAPSHOT_RECONCILED`
- `distribution_population_reconciliation_status`
- `edgeiq_race_epi_publication_snapshot_fact_v1`
- `race_date`
- `race_epi_distribution_evidence_sha256`
- `race_epi_distribution_fact_evidence_sha256`
- `race_epi_distribution_fact_id`
- `race_epi_distribution_id`
- `race_epi_ordering_summary_evidence_sha256`
- `race_epi_ordering_summary_id`
- `race_epi_publication_snapshot_evidence_sha256`
- `race_epi_publication_snapshot_id`
- `race_epi_snapshot_publication_decision`
- `race_epi_snapshot_reconciliation_decision`
- `race_epi_snapshot_status`
- `race_id`
- `source_race_populations_exact`
- `status`
- `tied_epi_entry_count`
- `top_epi_tie_status`
- `unique_epi_entry_count`

### `scripts\audit_edgeiq_race_eri_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `BLANK_RACE_ID`
- `EDGEIQ_RACE_ERI_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ERI_FACT_V1_AUDIT_PASS`
- `FIELD_MEAN_PROJECTED_PERFORMANCE`
- `GOVERNED_PROJECTED_PERFORMANCE`
- `GOVERNED_RACE_ERI`
- `PROJECTED_PERFORMANCE_PUBLISHED`
- `PROJECTED_PERFORMANCE_RECONCILED`
- `below_minimum_field_size_races`
- `edgeiq_race_eri_fact_v1`
- `effective_from_date`
- `effective_to_date`
- `eligible_runner_count`
- `minimum_eligible_runner_count`
- `projected_performance_maximum`
- `projected_performance_mean`
- `projected_performance_mean_unrounded`
- `projected_performance_median`
- `projected_performance_minimum`
- `projected_performance_publication_decision`
- `projected_performance_range`
- `projected_performance_reconciliation_decision`
- `projected_performance_rows`
- `projected_performance_sum`
- `projected_performance_value`
- `projected_race_count`
- `race_date`
- `race_entry_id`
- `race_entry_projected_performance_evidence_sha256`
- `race_entry_projected_performance_id`
- `race_entry_projected_performance_status`
- `race_eri_evidence_sha256`
- `race_eri_id`
- `race_eri_ids_unique`
- `race_eri_natural_keys_unique`
- `race_eri_parameter_evidence_sha256`
- `race_eri_parameter_id`
- `race_eri_parameter_status`
- `race_eri_rows`
- `race_eri_status`
- `race_id`
- `source_projected_performance_builder_version_set`
- `source_projected_performance_evidence_set_sha256`
- `source_projected_performance_id_set_sha256`
- `status`

### `scripts\build_edgeiq_connection_context_research_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `combo_vs_jockey_place_lift_pct`
- `combo_vs_jockey_win_lift_pct`
- `combo_vs_trainer_place_lift_pct`
- `combo_vs_trainer_win_lift_pct`
- `context_rows`
- `jockey`
- `jockey_base_place_pct`
- `jockey_base_starts`
- `jockey_base_win_pct`
- `jockey_canonical`
- `status`
- `trainer`
- `trainer_base_place_pct`
- `trainer_base_starts`
- `trainer_base_win_pct`
- `trainer_canonical`
- `trainer_jockey_canonical`
- `unique_jockeys`
- `unique_trainers`

### `scripts\build_edgeiq_connection_context_research_v2_stability.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `combo_vs_jockey_place_lift_pct`
- `combo_vs_jockey_win_lift_pct`
- `combo_vs_trainer_place_lift_pct`
- `combo_vs_trainer_win_lift_pct`
- `context_rows`
- `dates`
- `first_date`
- `horse`
- `horse_key`
- `horses`
- `jockey`
- `jockey_base_place_pct`
- `jockey_base_starts`
- `jockey_base_win_pct`
- `jockey_canonical`
- `last_date`
- `meeting_date`
- `race_key_v1`
- `races`
- `status`
- `trainer`
- `trainer_base_place_pct`
- `trainer_base_starts`
- `trainer_base_win_pct`
- `trainer_canonical`
- `trainer_jockey_canonical`
- `unique_horses`
- `unique_races`

### `scripts\build_edgeiq_context_translation_engine_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `horse`
- `jockey`
- `race_date`
- `race_no`
- `status`
- `track`
- `trainer`

### `scripts\build_edgeiq_context_warehouse_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `HORSE`
- `JOCKEY`
- `TRAINER`
- `context_type`
- `context_value`
- `horse_key`
- `horse_rows`
- `jockey`
- `jockey_rows`
- `status`
- `trainer`
- `trainer_rows`

### `scripts\build_edgeiq_context_warehouse_v2_graphql.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CONTEXT_WAREHOUSE_V2_GRAPHQL_BUILT`
- `DISTANCE`
- `HORSE`
- `JOCKEY`
- `TRACK`
- `TRAINER`
- `context_type`
- `context_value`
- `distance`
- `distance_bucket`
- `horse`
- `horse_rows`
- `jockey`
- `jockey_rows`
- `status`
- `track`
- `track_condition`
- `trainer`
- `trainer_rows`

### `scripts\build_edgeiq_context_warehouse_v2_graphql_signal_view.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CONTEXT_WAREHOUSE_V2_GRAPHQL_SIGNAL_VIEW_BUILT`
- `HORSE`
- `JOCKEY`
- `TRAINER`
- `horse_rows`
- `jockey_rows`
- `status`
- `trainer_rows`

### `scripts\build_edgeiq_contextual_learning_engine_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `horse`
- `overlay_runners`
- `projected_race_shape`
- `race_date`
- `race_no`
- `runners`
- `track`
- `v5_contextual_overlay_pct`
- `v5_contextual_probability`

### `scripts\build_edgeiq_contextual_probability_engine_v5.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `PROXY_CONTEXTUAL_WATCH`
- `contextual_probability`
- `horse`
- `proxy_contextual_watch`
- `race_no`
- `track`
- `v5_contextual_action`
- `v5_contextual_fair_price`
- `v5_contextual_overlay_pct`
- `v5_contextual_probability`
- `v5_contextual_reason`

### `scripts\build_edgeiq_contextual_result_link_engine_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `elite_overlay_runners`
- `horse`
- `overlay_runners`
- `projected_race_shape`
- `race_no`
- `track`
- `universal_runner_key`
- `v5_contextual_overlay_pct`

### `scripts\build_edgeiq_current_suitability_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `CURRENT_SUITABILITY_V1`
- `RUNNER_NAME_STRICT_CURRENT_RACE_PLUS_ASOF_HISTORY`
- `asOfDate`
- `barrier`
- `class`
- `classFamily`
- `crossRaceJoins`
- `crossRunnerJoins`
- `distance`
- `distanceBand`
- `edgeiq_current_suitability_v1`
- `horse`
- `normalizedRunner`
- `projected_rating_v5_2`
- `raceDate`
- `raceIdentity`
- `raceNumber`
- `raceShape`
- `runnerId`
- `runnerName`
- `runnerNumber`
- `runners`
- `selectedRaceOutcomeRowsUsed`
- `suitability`
- `suitabilityBand`
- `track`
- `trackDistance`
- `trackKey`

### `scripts\build_edgeiq_ecology_snapshot_archive_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `archive_status`
- `audit_status`
- `evidence_class`
- `governance_status`
- `health_status`
- `orchestrator_status`
- `overall_status`
- `timestamp_utc`
- `track`

### `scripts\build_edgeiq_ecology_snapshot_comparison_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `change_classification`
- `governance_status`
- `latest_governance_status`
- `previous_governance_status`
- `timestamp_utc`
- `track`

### `scripts\build_edgeiq_horse_context_engine_v2.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CLASS`
- `DISTANCE`
- `HORSE`
- `TRACK`
- `class_profile_1`
- `class_profile_count`
- `context_type`
- `context_value`
- `distance_profile_1`
- `distance_profile_2`
- `distance_profile_count`
- `horse`
- `horse_context_rows`
- `horse_context_view`
- `horses_with_cautions`
- `horses_with_condition_profiles`
- `horses_with_distance_profiles`
- `horses_with_track_profiles`
- `status`
- `track_profile_1`
- `track_profile_2`
- `track_profile_count`

### `scripts\build_edgeiq_horse_context_research_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CLASS`
- `DISTANCE`
- `TRACK`
- `context_rows`
- `context_type`
- `context_value`
- `distance`
- `horse_base_place_pct`
- `horse_base_win_pct`
- `horse_key`
- `horse_starts`
- `race_class`
- `status`
- `track`
- `track_condition`
- `unique_horses`

### `scripts\build_edgeiq_jockey_context_research_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `BARRIER`
- `CLASS`
- `DISTANCE`
- `TRACK`
- `barrier`
- `context_rows`
- `context_type`
- `context_value`
- `distance`
- `jockey`
- `jockey_canonical`
- `race_class`
- `status`
- `track`
- `track_condition`

### `scripts\build_edgeiq_jockey_context_research_v2.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `BARRIER`
- `CLASS`
- `CONTEXT_EDGE`
- `CONTEXT_RISK`
- `DISTANCE`
- `MILD_CONTEXT_EDGE`
- `TRACK`
- `barrier`
- `context_edge`
- `context_risk`
- `context_rows`
- `context_type`
- `context_value`
- `distance`
- `jockey`
- `jockey_base_place_pct`
- `jockey_base_starts`
- `jockey_base_win_pct`
- `jockey_canonical`
- `mild_context_edge`
- `race_class`
- `status`
- `track`
- `track_condition`
- `unique_jockeys`
- `within_jockey_place_lift_pct`
- `within_jockey_win_lift_pct`

### `scripts\build_edgeiq_live_context_signal_feed_v2_graphql.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `DISTANCE`
- `HORSE`
- `JOCKEY`
- `LIVE_CONTEXT_SIGNAL_FEED_V2_GRAPHQL_BUILT`
- `TRACK`
- `TRAINER`
- `context_signal_1_context`
- `context_signal_1_entity_type`
- `context_signal_1_importance`
- `context_signal_1_insight`
- `context_signal_1_signal`
- `context_signal_1_starts`
- `context_signal_2_context`
- `context_signal_2_entity_type`
- `context_signal_2_insight`
- `context_signal_2_signal`
- `context_signal_3_context`
- `context_signal_3_entity_type`
- `context_signal_3_insight`
- `context_signal_3_signal`
- `context_signal_count`
- `context_type`
- `context_value`
- `distance`
- `distance_bucket`
- `horse`
- `horse_key`
- `jockey`
- `jockey_graphql`
- `match_status`
- `race_date`
- `race_no`
- `rows_with_context_signals`
- `status`
- `total_top_context_signals`
- `track`
- `track_condition`
- `trainer`
- `trainer_graphql`

### `scripts\build_edgeiq_live_form_context_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `LIGHTLY_RACED`
- `horse`
- `horse_key`
- `is_official_race`
- `lightly_raced_profiles`
- `live_form_context_grade`
- `live_form_context_reason`
- `live_peak_rating`
- `race_no`
- `run_rating`
- `track`

### `scripts\build_edgeiq_live_on_track_weather_snapshot_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `EDGEIQ_LIVE_RAW_ON_TRACK_WEATHER_SNAPSHOT_V1_BUILT`
- `edgeiq_live_raw_on_track_weather_v1`
- `http_status`
- `schema_status`
- `source_status`
- `timestamp`
- `track_group`

### `scripts\build_edgeiq_nexus_contextual_intelligence_v2.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `Context`
- `FRONTRUNNER`
- `FRONT_RUNNER`
- `Jockey`
- `Trainer`
- `barrier_specialist_logic_built`
- `class_band`
- `class_combo`
- `context_band`
- `context_type`
- `context_value`
- `contextual_score_rows`
- `current_class_bucket`
- `current_distance_bucket`
- `current_track`
- `distance`
- `distance_band`
- `distance_combo`
- `horse`
- `horse_code`
- `horse_key`
- `horse_run_style`
- `jockey`
- `jockey_best_context`
- `jockey_best_style`
- `jockey_best_style_ae`
- `jockey_best_style_roi`
- `jockey_best_style_win_pct`
- `jockey_canonical`
- `jockey_context_rows`
- `jockey_context_score`
- `jockey_key`
- `jockey_name`
- `jockey_recent_100_win_pct`
- `jockey_recent_25_win_pct`
- `jockey_recent_50_win_pct`
- `lifetime`
- `live_contextual_feed_rows`
- `live_rows_with_nexus_context_score`
- `nexus_context_band`
- `nexus_context_score`
- `partnership_context_rows`
- `pricing_probability_rating_model_math_changed`
- `race_class`
- `race_date`
- `race_date_dt`
- `race_id`
- `race_no`
- `race_no_num`
- `race_shape_label`
- `race_shape_story`
- `runner_key`
- `runner_name`
- `track`
- `track_combo`
- `track_condition`
- `trainer`
- `trainer_best_context`
- `trainer_best_style`
- `trainer_best_style_ae`
- `trainer_best_style_roi`
- `trainer_best_style_win_pct`
- `trainer_canonical`
- `trainer_context_rows`
- `trainer_context_score`
- `trainer_key`
- `trainer_name`
- `trainer_recent_100_win_pct`
- `trainer_recent_25_win_pct`
- `trainer_recent_50_win_pct`

### `scripts\build_edgeiq_official_run_context_bridge_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `RACE`
- `candidate_rows`
- `class_name`
- `date`
- `distance`
- `duplicate_candidate_rows`
- `horse`
- `horse_all_form_url`
- `horse_code`
- `horse_key`
- `horse_name`
- `horse_url`
- `is_official_race`
- `race_class`
- `race_class_clean`
- `race_class_raw`
- `race_date`
- `race_entry`
- `race_id`
- `race_key`
- `race_name`
- `race_no`
- `race_number`
- `run_date`
- `runner`
- `runner_key`
- `source_race_no`
- `track`
- `track_code`
- `track_condition`

### `scripts\build_edgeiq_performance_intelligence_trust_manifest_v1.py`

- Race-entry reference: `True`
- Projected-performance reference: `True`
- Snapshot reference: `True`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `AGG_B_WEIGHTED_ARITHMETIC_MEAN_EXPONENTIAL_HALF_LIFE_V1`
- `DATA_COVERAGE_PARTIAL_PROJECTED_PERFORMANCE_AND_EPI_UNAVAILABLE`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_HORSE_RATINGS_READY_NO_LIVE_MATCH`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_LIVE_PARTIAL_HISTORICAL_COVERAGE`
- `HISTORICAL_RATING_AVAILABLE`
- `PASS_FOR_PARAMETER_SOURCES_AND_HORSE_RATING_CANDIDATE`
- `active_horses_with_ratings`
- `active_horses_without_ratings`
- `candidate_promotion_result`
- `canonical_horse_id`
- `horse_rating`
- `horse_rating_hash`
- `live_rating_match`
- `match_status`
- `overall_status`
- `program_status`
- `projected_performance`
- `projected_performance_rows`
- `rating_base`
- `run_timestamp_utc`
- `status`

### `scripts\build_edgeiq_race_context_grouping_audit_v5_1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `A_CURRENT_FULL_CONTEXT`
- `B_DATE_TRACK_DISTANCE_SOURCE`
- `C_DATE_TRACK_DISTANCE_ROUND_25_SOURCE`
- `D_DATE_TRACK_DISTANCE_ROUND_50_SOURCE`
- `E_DATE_TRACK_RACE_NAME_SOURCE`
- `F_DATE_TRACK_DISTANCE_BAND_SOURCE`
- `UNAVAILABLE_MISSING_RACE_NAME`
- `average_runner_count`
- `candidate_E_unavailable`
- `context_key`
- `context_key_A_CURRENT_FULL_CONTEXT`
- `contexts_17_plus`
- `contexts_2_4`
- `contexts_5_8`
- `contexts_9_16`
- `distance`
- `distance_band_key`
- `distance_band_v5_1`
- `distance_key`
- `distance_min`
- `distance_num`
- `distance_round_25_key`
- `distance_round_50_key`
- `distance_span`
- `exact_distance_count`
- `grouping_candidate`
- `horse`
- `max_distance`
- `max_runner_count`
- `median_runner_count`
- `min_distance`
- `multi_runner_contexts`
- `nearby_distance_split`
- `performance_rating_v5_1`
- `projection_status_v5_1`
- `race_class`
- `race_class_clean_v5_1`
- `race_class_key`
- `race_contexts`
- `race_date`
- `race_date_key`
- `race_name`
- `race_name_available_for_candidate_E`
- `race_name_key`
- `race_target_rating_v5_1`
- `runner_count`
- `runner_rows`
- `sample_distances`
- `sample_horses`
- `single_runner_contexts`
- `single_runner_current_contexts`
- `top_100_largest_contexts`
- `top_100_single_runner_contexts_current_grouping`
- `total_current_contexts`
- `track`
- `track_key`

### `scripts\build_edgeiq_race_entry_context_adjusted_performance_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CONTEXT_INELIGIBLE`
- `CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTED_PERFORMANCE`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_BUILD_PASS`
- `GOVERNED_CONTEXT_ADJUSTED_PERFORMANCE`
- `GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `PERFORMANCE_ADJUSTED`
- `canonical_horse_id`
- `canonical_horse_name`
- `context_adjusted_performance_decision`
- `context_adjusted_performance_value`
- `context_adjustment_application_decision`
- `context_parameter_id`
- `historical_rating_value`
- `race_date`
- `race_entry_context_adjusted_performance_evidence_sha256`
- `race_entry_context_adjusted_performance_id`
- `race_entry_context_adjusted_performance_status`
- `race_entry_context_adjustment_evidence_sha256`
- `race_entry_context_adjustment_id`
- `race_entry_context_adjustment_status`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_id`
- `race_entry_id`
- `race_entry_performance_context_id`
- `race_id`
- `runner_id`
- `total_context_adjustment`

### `scripts\build_edgeiq_race_entry_context_adjustment_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CONTEXT_INELIGIBLE`
- `CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTMENT`
- `CONTEXT_PARAMETER_GOVERNED`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_BUILD_PASS`
- `GOVERNED_CONTEXT_ADJUSTMENT_APPLIED`
- `GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `barrier_adjustment`
- `canonical_horse_id`
- `canonical_horse_name`
- `class_adjustment`
- `context_adjustment_application_decision`
- `context_historical_rating_value`
- `context_parameter_evidence_sha256`
- `context_parameter_id`
- `context_parameter_selection_decision`
- `distance_adjustment`
- `historical_rating_value`
- `parameter_status`
- `race_date`
- `race_entry_context_adjustment_evidence_sha256`
- `race_entry_context_adjustment_id`
- `race_entry_context_adjustment_status`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_evidence_sha256`
- `race_entry_context_parameter_selection_id`
- `race_entry_id`
- `race_entry_performance_context_evidence_sha256`
- `race_entry_performance_context_id`
- `race_id`
- `runner_id`
- `source_context_builder_version`
- `source_context_evidence_sha256`
- `surface_adjustment`
- `total_context_adjustment`
- `track_adjustment`
- `track_condition_adjustment`
- `track_configuration_adjustment`
- `weight_adjustment`

### `scripts\build_edgeiq_race_entry_context_eligibility_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `ALLOCATED_WEIGHT`
- `ALL_REQUIRED_CONTEXT_ELIGIBLE`
- `BARRIER_CONTEXT`
- `CLASS_CONTEXT`
- `COMPLETE_CONTEXT_ELIGIBLE`
- `COMPLETE_CONTEXT_INELIGIBLE`
- `DISTANCE_CONTEXT`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ELIGIBILITY_FACT_V1_BUILD_PASS`
- `FACTUAL_DECLARED_RACE_CONTEXT_GOVERNED`
- `HISTORICAL_RATING`
- `INELIGIBLE_INVALID_CONTEXT`
- `INELIGIBLE_MISSING_CONTEXT`
- `INELIGIBLE_UNSUPPORTED_CONTEXT`
- `RAIL_CONTEXT`
- `SURFACE_CONTEXT`
- `TRACK_CONDITION`
- `TRACK_CONFIGURATION`
- `TRACK_CONTEXT`
- `allocated_weight_eligibility`
- `allocated_weight_kg`
- `barrier`
- `barrier_context_eligibility`
- `canonical_horse_id`
- `canonical_horse_name`
- `class_context_eligibility`
- `complete_context_eligibility`
- `context_historical_rating_value`
- `distance_context_eligibility`
- `historical_rating_eligibility`
- `primary_context_eligibility_reason_code`
- `race_class_code`
- `race_date`
- `race_distance_m`
- `race_entry_context_eligibility_evidence_sha256`
- `race_entry_context_eligibility_id`
- `race_entry_context_eligibility_status`
- `race_entry_horse_performance_snapshot_id`
- `race_entry_id`
- `race_entry_performance_context_evidence_sha256`
- `race_entry_performance_context_id`
- `race_entry_performance_context_status`
- `race_id`
- `racing_surface`
- `rail_context_eligibility`
- `runner_id`
- `source_context_builder_version`
- `source_context_evidence_sha256`
- `surface_context_eligibility`
- `track_condition`
- `track_condition_eligibility`
- `track_configuration`
- `track_configuration_eligibility`
- `track_context_eligibility`
- `track_id`
- `track_name`

### `scripts\build_edgeiq_race_entry_context_parameter_selection_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `COMPLETE_CONTEXT_ELIGIBLE`
- `COMPLETE_CONTEXT_INELIGIBLE`
- `CONTEXT_INELIGIBLE`
- `CONTEXT_NOT_ELIGIBLE_FOR_PARAMETER_SELECTION`
- `CONTEXT_PARAMETER_GOVERNED`
- `EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_BUILD_PASS`
- `EXACT_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `EXACT_CONTEXT_PARAMETER_SELECTED`
- `WEIGHT_35_TO_49_999999`
- `WEIGHT_50_TO_54_999999`
- `WEIGHT_55_TO_59_999999`
- `WEIGHT_60_TO_64_999999`
- `WEIGHT_65_TO_80`
- `allocated_weight_kg`
- `barrier`
- `barrier_band`
- `canonical_horse_id`
- `canonical_horse_name`
- `complete_context_eligibility`
- `context_parameter_evidence_sha256`
- `context_parameter_id`
- `context_parameter_selection_decision`
- `context_signature_sha256`
- `parameter_status`
- `primary_context_eligibility_reason_code`
- `race_class_code`
- `race_date`
- `race_distance_m`
- `race_entry_context_eligibility_evidence_sha256`
- `race_entry_context_eligibility_id`
- `race_entry_context_eligibility_status`
- `race_entry_context_parameter_selection_evidence_sha256`
- `race_entry_context_parameter_selection_id`
- `race_entry_context_parameter_selection_status`
- `race_entry_horse_performance_snapshot_id`
- `race_entry_id`
- `race_entry_performance_context_evidence_sha256`
- `race_entry_performance_context_id`
- `race_id`
- `racing_surface`
- `runner_id`
- `source_context_builder_version`
- `source_context_eligibility_reason_code`
- `source_context_evidence_sha256`
- `track_condition`
- `track_configuration`
- `track_id`
- `weight_band`

### `scripts\build_edgeiq_race_entry_epi_component_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_EPI_COMPONENT_FACT_V1_BUILD_PASS`
- `GOVERNED_RACE_ENTRY_EPI_COMPONENT`
- `HISTORICAL_PERFORMANCE`
- `RACE_CONTEXT`
- `SUITABILITY`
- `aggregate_suitability_value`
- `authorised_component_weight`
- `edgeiq_race_entry_eri_context_fact_v1`
- `edgeiq_race_entry_projected_performance_fact_v1`
- `edgeiq_race_entry_suitability_aggregate_fact_v1`
- `effective_from_date`
- `effective_to_date`
- `epi_component_status`
- `epi_parameter_status`
- `eri_context_evidence_sha256`
- `evidence_candidates`
- `historical_performance_weight`
- `id_candidates`
- `normalisation_parameter_status`
- `projected_performance_evidence_sha256`
- `projected_performance_value`
- `projected_performance_vs_eri`
- `race_context_weight`
- `race_date`
- `race_entry_epi_component_evidence_sha256`
- `race_entry_epi_component_id`
- `race_entry_eri_context_evidence_sha256`
- `race_entry_eri_context_id`
- `race_entry_id`
- `race_entry_projected_performance_evidence_sha256`
- `race_entry_projected_performance_id`
- `race_entry_suitability_aggregate_evidence_sha256`
- `race_entry_suitability_aggregate_id`
- `race_entry_suitability_aggregate_value`
- `race_entry_suitability_evidence_sha256`
- `race_entry_suitability_id`
- `race_id`
- `suitability_aggregate_evidence_sha256`
- `suitability_aggregate_value`
- `suitability_value`
- `suitability_weight`
- `value_candidates`
- `weight_field`
- `weighted_component_value`

### `scripts\build_edgeiq_race_entry_epi_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_EPI_FACT_V1_BUILD_PASS`
- `GOVERNED_RACE_ENTRY_EPI`
- `GOVERNED_RACE_ENTRY_EPI_COMPONENT`
- `HISTORICAL_PERFORMANCE`
- `NORMALISED_WEIGHTED_ADDITIVE_EPI_V1`
- `RACE_CONTEXT`
- `SUITABILITY`
- `authorised_component_weight`
- `effective_from_date`
- `effective_to_date`
- `epi_component_status`
- `epi_parameter_status`
- `epi_status`
- `historical_performance_component_evidence_sha256`
- `historical_performance_component_id`
- `historical_performance_normalised_value`
- `historical_performance_weight`
- `historical_performance_weighted_value`
- `race_context_component_evidence_sha256`
- `race_context_component_id`
- `race_context_normalised_value`
- `race_context_weight`
- `race_context_weighted_value`
- `race_date`
- `race_entry_epi_component_evidence_sha256`
- `race_entry_epi_component_id`
- `race_entry_epi_evidence_sha256`
- `race_entry_epi_id`
- `race_entry_id`
- `race_id`
- `suitability_component_evidence_sha256`
- `suitability_component_id`
- `suitability_normalised_value`
- `suitability_weight`
- `suitability_weighted_value`
- `total_component_weight`
- `weighted_component_total`
- `weighted_component_value`

### `scripts\build_edgeiq_race_entry_epi_ordering_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_BUILD_PASS`
- `EPI_RELATIVE_CONTEXT_PUBLISHED`
- `EPI_RELATIVE_CONTEXT_RECONCILED`
- `GOVERNED_RACE_ENTRY_EPI_ORDERING`
- `GOVERNED_RACE_ENTRY_EPI_RELATIVE_CONTEXT`
- `context_id`
- `epi_ordering_status`
- `epi_relative_context_publication_decision`
- `epi_relative_context_reconciliation_decision`
- `epi_relative_context_status`
- `epi_tie_status`
- `race_date`
- `race_entry_epi_ordering_evidence_sha256`
- `race_entry_epi_ordering_id`
- `race_entry_epi_relative_context_evidence_sha256`
- `race_entry_epi_relative_context_id`
- `race_entry_id`
- `race_id`
- `runner_epi`
- `runner_epi_text`
- `runner_epi_value`

### `scripts\build_edgeiq_race_entry_epi_publication_snapshot_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_BUILD_PASS`
- `GOVERNED_RACE_ENTRY_EPI_ORDERING`
- `GOVERNED_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT`
- `RACE_ENTRY_EPI_SNAPSHOT_PUBLISHED`
- `RACE_ENTRY_EPI_SNAPSHOT_RECONCILED`
- `epi_ordering_status`
- `epi_tie_status`
- `race_date`
- `race_entry_epi_ordering_evidence_sha256`
- `race_entry_epi_ordering_id`
- `race_entry_epi_publication_snapshot_evidence_sha256`
- `race_entry_epi_publication_snapshot_id`
- `race_entry_epi_relative_context_evidence_sha256`
- `race_entry_epi_snapshot_publication_decision`
- `race_entry_epi_snapshot_reconciliation_decision`
- `race_entry_epi_snapshot_status`
- `race_entry_id`
- `race_id`
- `runner_epi_value`
- `source_relative_context_evidence_sha256`
- `tie_status`

### `scripts\build_edgeiq_race_entry_epi_relative_context_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_BUILD_PASS`
- `EPI_RELATIVE_CONTEXT_PUBLISHED`
- `EPI_RELATIVE_CONTEXT_RECONCILED`
- `GOVERNED_RACE_ENTRY_EPI`
- `GOVERNED_RACE_ENTRY_EPI_RELATIVE_CONTEXT`
- `GOVERNED_RACE_EPI_DISTRIBUTION`
- `RACE_EPI_DISTRIBUTION_PUBLISHED`
- `RACE_EPI_DISTRIBUTION_RECONCILED`
- `distance_above_minimum_epi`
- `distance_below_maximum_epi`
- `epi_relative_context_publication_decision`
- `epi_relative_context_reconciliation_decision`
- `epi_relative_context_status`
- `epi_status`
- `race_date`
- `race_entry_epi_evidence_sha256`
- `race_entry_epi_id`
- `race_entry_epi_relative_context_evidence_sha256`
- `race_entry_epi_relative_context_id`
- `race_entry_id`
- `race_epi_distribution_evidence_sha256`
- `race_epi_distribution_id`
- `race_epi_distribution_publication_decision`
- `race_epi_distribution_reconciliation_decision`
- `race_epi_distribution_status`
- `race_id`
- `runner_epi_value`

### `scripts\build_edgeiq_race_entry_eri_context_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_ERI_CONTEXT_FACT_V1_BUILD_PASS`
- `ERI_CONTEXT_PUBLISHED`
- `ERI_CONTEXT_RECONCILED`
- `GOVERNED_PROJECTED_PERFORMANCE`
- `GOVERNED_RACE_ENTRY_ERI_CONTEXT`
- `GOVERNED_RACE_ERI`
- `PROJECTED_PERFORMANCE_PUBLISHED`
- `PROJECTED_PERFORMANCE_RECONCILED`
- `context_output_decimal_places`
- `context_rounding_mode`
- `eri_context_publication_decision`
- `eri_context_reconciliation_decision`
- `projected_performance_publication_decision`
- `projected_performance_reconciliation_decision`
- `projected_performance_value`
- `projected_performance_vs_eri`
- `race_date`
- `race_entry_eri_context_evidence_sha256`
- `race_entry_eri_context_id`
- `race_entry_eri_context_status`
- `race_entry_id`
- `race_entry_projected_performance_evidence_sha256`
- `race_entry_projected_performance_id`
- `race_entry_projected_performance_status`
- `race_eri_evidence_sha256`
- `race_eri_id`
- `race_eri_parameter_id`
- `race_eri_status`
- `race_id`
- `source_projected_performance_builder_version`
- `source_projected_performance_evidence_sha256`
- `source_race_eri_builder_version`
- `source_race_eri_evidence_sha256`

### `scripts\build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py`

- Race-entry reference: `True`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_BUILD_PASS`
- `HISTORICAL_HORSE_RATING_GOVERNED`
- `POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE`
- `average_eligible_historical_rating_value`
- `canonical_horse_id`
- `canonical_horse_name`
- `eligible_historical_rating_count`
- `first_eligible_rating_date`
- `highest_eligible_historical_rating_value`
- `horse_performance_rating_evidence_sha256`
- `horse_performance_rating_id`
- `horse_performance_rating_method`
- `horse_performance_rating_status`
- `horse_performance_rating_value`
- `latest_eligible_rating_date`
- `lowest_eligible_historical_rating_value`
- `race_date`
- `race_entry_evidence_sha256`
- `race_entry_horse_performance_snapshot_evidence_sha256`
- `race_entry_horse_performance_snapshot_id`
- `race_entry_horse_performance_snapshot_status`
- `race_entry_id`
- `race_entry_status`
- `race_id`
- `rating_age_days`
- `rating_as_of_date`
- `runner_id`
- `selected_horse_performance_rating_id`
- `selected_horse_performance_rating_value`
- `selected_rating_as_of_date`
- `source_eligible_rating_evidence_sha256`
- `source_eligible_rating_ids_sha256`
- `source_race_entry_builder_version`
- `source_race_entry_evidence_sha256`
- `source_rating_builder_version`
- `source_selected_rating_evidence_sha256`

### `scripts\build_edgeiq_race_entry_performance_context_fact_v1.py`

- Race-entry reference: `True`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_BUILD_PASS`
- `FACTUAL_DECLARED_RACE_CONTEXT_GOVERNED`
- `POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE`
- `allocated_weight_kg`
- `barrier`
- `canonical_horse_id`
- `canonical_horse_name`
- `context_historical_rating_value`
- `race_class_code`
- `race_date`
- `race_distance_m`
- `race_entry_evidence_sha256`
- `race_entry_horse_performance_snapshot_evidence_sha256`
- `race_entry_horse_performance_snapshot_id`
- `race_entry_horse_performance_snapshot_status`
- `race_entry_id`
- `race_entry_performance_context_evidence_sha256`
- `race_entry_performance_context_id`
- `race_entry_performance_context_status`
- `race_entry_status`
- `race_id`
- `racing_surface`
- `rating_age_days`
- `runner_id`
- `selected_horse_performance_rating_id`
- `selected_horse_performance_rating_value`
- `selected_rating_as_of_date`
- `source_race_entry_builder_version`
- `source_race_entry_evidence_sha256`
- `track_condition`
- `track_configuration`
- `track_id`
- `track_name`

### `scripts\build_edgeiq_race_entry_projected_performance_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_BUILD_PASS`
- `GOVERNED_CONTEXT_ADJUSTED_PERFORMANCE`
- `GOVERNED_PROJECTED_PERFORMANCE`
- `GOVERNED_SUITABILITY_AGGREGATE`
- `PERFORMANCE_ADJUSTED`
- `PROJECTED_PERFORMANCE_PUBLISHED`
- `PROJECTED_PERFORMANCE_RECONCILED`
- `SUITABILITY_AGGREGATED`
- `aggregate_suitability_value`
- `canonical_horse_id`
- `canonical_horse_name`
- `context_adjusted_performance_decision`
- `context_adjusted_performance_value`
- `context_parameter_id`
- `historical_rating_value`
- `projected_performance_delta_from_historical`
- `projected_performance_publication_decision`
- `projected_performance_reconciliation_decision`
- `projected_performance_value`
- `race_date`
- `race_entry_context_adjusted_performance_evidence_sha256`
- `race_entry_context_adjusted_performance_id`
- `race_entry_context_adjusted_performance_status`
- `race_entry_context_adjustment_id`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_id`
- `race_entry_id`
- `race_entry_performance_context_id`
- `race_entry_projected_performance_evidence_sha256`
- `race_entry_projected_performance_id`
- `race_entry_projected_performance_status`
- `race_entry_suitability_aggregate_evidence_sha256`
- `race_entry_suitability_aggregate_id`
- `race_entry_suitability_aggregate_status`
- `race_id`
- `runner_id`
- `source_adjusted_performance_builder_version`
- `source_adjusted_performance_evidence_sha256`
- `source_suitability_aggregate_builder_version`
- `source_suitability_aggregate_evidence_sha256`
- `suitability_aggregate_decision`
- `total_context_adjustment`

### `scripts\build_edgeiq_race_entry_suitability_aggregate_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `BARRIER`
- `CLASS`
- `CONTEXT_INELIGIBLE`
- `DISTANCE`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_BUILD_PASS`
- `GOVERNED_SUITABILITY_AGGREGATE`
- `GOVERNED_SUITABILITY_COMPONENT`
- `PERFORMANCE_ADJUSTED`
- `SUITABILITY_AGGREGATED`
- `SURFACE`
- `TRACK`
- `TRACK_CONDITION`
- `TRACK_CONFIGURATION`
- `WEIGHT`
- `aggregate_suitability_value`
- `barrier_suitability_value`
- `canonical_horse_id`
- `canonical_horse_name`
- `class_suitability_value`
- `context_adjusted_performance_decision`
- `context_adjusted_performance_value`
- `context_parameter_id`
- `distance_suitability_value`
- `field_size_suitability_value`
- `historical_rating_value`
- `race_date`
- `race_entry_context_adjusted_performance_evidence_sha256`
- `race_entry_context_adjusted_performance_id`
- `race_entry_context_adjustment_id`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_id`
- `race_entry_id`
- `race_entry_performance_context_id`
- `race_entry_suitability_aggregate_evidence_sha256`
- `race_entry_suitability_aggregate_id`
- `race_entry_suitability_aggregate_status`
- `race_entry_suitability_component_evidence_sha256`
- `race_entry_suitability_component_id`
- `race_entry_suitability_component_status`
- `race_id`
- `runner_id`
- `source_adjusted_performance_builder_version`
- `source_adjusted_performance_evidence_sha256`
- `suitability_aggregate_decision`
- `suitability_component_count`
- `suitability_component_decision`
- `suitability_component_type`
- `suitability_component_value`
- `surface_suitability_value`
- `total_context_adjustment`
- `track_condition_suitability_value`
- `track_configuration_suitability_value`
- `track_suitability_value`
- `weight_suitability_value`

### `scripts\build_edgeiq_race_entry_suitability_component_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `True`
- Context reference: `True`

Likely referenced columns:

- `BARRIER`
- `CLASS`
- `CONTEXT_INELIGIBLE`
- `DISTANCE`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_BUILD_PASS`
- `GOVERNED_SUITABILITY_COMPONENT`
- `PERFORMANCE_ADJUSTED`
- `SURFACE`
- `TRACK`
- `TRACK_CONDITION`
- `TRACK_CONFIGURATION`
- `WEIGHT`
- `barrier_adjustment`
- `canonical_horse_id`
- `canonical_horse_name`
- `class_adjustment`
- `context_adjusted_performance_decision`
- `context_adjusted_performance_value`
- `context_adjustment_application_decision`
- `context_parameter_id`
- `distance_adjustment`
- `historical_rating_value`
- `race_date`
- `race_entry_context_adjusted_performance_evidence_sha256`
- `race_entry_context_adjusted_performance_id`
- `race_entry_context_adjustment_evidence_sha256`
- `race_entry_context_adjustment_id`
- `race_entry_context_eligibility_id`
- `race_entry_context_parameter_selection_id`
- `race_entry_id`
- `race_entry_performance_context_id`
- `race_entry_suitability_component_evidence_sha256`
- `race_entry_suitability_component_id`
- `race_entry_suitability_component_status`
- `race_id`
- `runner_id`
- `source_adjusted_performance_builder_version`
- `source_adjusted_performance_evidence_sha256`
- `source_context_adjustment_builder_version`
- `source_context_adjustment_evidence_sha256`
- `suitability_component_decision`
- `suitability_component_type`
- `suitability_component_value`
- `surface_adjustment`
- `total_context_adjustment`
- `track_adjustment`
- `track_condition_adjustment`
- `track_configuration_adjustment`
- `weight_adjustment`

### `scripts\build_edgeiq_race_epi_publication_snapshot_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_BUILD_PASS`
- `GOVERNED_RACE_EPI_ORDERING_SUMMARY`
- `GOVERNED_RACE_EPI_PUBLICATION_SNAPSHOT`
- `RACE_EPI_ORDERING_SUMMARY_PUBLISHED`
- `RACE_EPI_ORDERING_SUMMARY_RECONCILED`
- `RACE_EPI_SNAPSHOT_PUBLISHED`
- `RACE_EPI_SNAPSHOT_RECONCILED`
- `distribution_population_reconciliation_status`
- `entry_count`
- `race_date`
- `race_epi_distribution_evidence_sha256`
- `race_epi_distribution_fact_evidence_sha256`
- `race_epi_distribution_fact_id`
- `race_epi_distribution_id`
- `race_epi_ordering_summary_evidence_sha256`
- `race_epi_ordering_summary_id`
- `race_epi_ordering_summary_publication_decision`
- `race_epi_ordering_summary_reconciliation_decision`
- `race_epi_ordering_summary_status`
- `race_epi_population_count`
- `race_epi_publication_snapshot_evidence_sha256`
- `race_epi_publication_snapshot_id`
- `race_epi_snapshot_publication_decision`
- `race_epi_snapshot_reconciliation_decision`
- `race_epi_snapshot_status`
- `race_id`
- `runner_count`
- `tied_epi_entry_count`
- `top_epi_tie_status`
- `unique_epi_entry_count`

### `scripts\build_edgeiq_race_eri_fact_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `True`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `EDGEIQ_RACE_ERI_FACT_V1_BUILD_PASS`
- `FIELD_MEAN_PROJECTED_PERFORMANCE`
- `GOVERNED_PROJECTED_PERFORMANCE`
- `GOVERNED_RACE_ERI`
- `PROJECTED_PERFORMANCE_PUBLISHED`
- `PROJECTED_PERFORMANCE_RECONCILED`
- `effective_from_date`
- `effective_to_date`
- `eligible_runner_count`
- `minimum_eligible_runner_count`
- `projected_performance_maximum`
- `projected_performance_mean`
- `projected_performance_mean_unrounded`
- `projected_performance_median`
- `projected_performance_minimum`
- `projected_performance_publication_decision`
- `projected_performance_range`
- `projected_performance_reconciliation_decision`
- `projected_performance_sum`
- `projected_performance_value`
- `race_date`
- `race_entry_id`
- `race_entry_projected_performance_evidence_sha256`
- `race_entry_projected_performance_id`
- `race_entry_projected_performance_status`
- `race_eri_evidence_sha256`
- `race_eri_id`
- `race_eri_parameter_evidence_sha256`
- `race_eri_parameter_id`
- `race_eri_parameter_status`
- `race_eri_status`
- `race_id`
- `source_projected_performance_builder_version_set`
- `source_projected_performance_evidence_set_sha256`
- `source_projected_performance_id_set_sha256`

### `scripts\build_edgeiq_runner_profile_engine_v1_1_CHECKPOINT_CONTEXT_PROFILE_WORKING_20260624.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `CLASS`
- `DISTANCE`
- `HORSE`
- `RUNNER`
- `RUNNER_PROFILE_ENGINE_V1_1_BUILT`
- `TRACK`
- `class_profile`
- `context_type`
- `context_value`
- `distance_profile`
- `horse`
- `horse_archetype`
- `profile_context_rows`
- `race_no`
- `race_number`
- `runner`
- `runner_dna_band`
- `runner_dna_score`
- `runner_key`
- `runner_name`
- `status`
- `track`
- `track_profile`
- `unique_tracks`
- `with_context_profile`
- `without_context_profile`

### `scripts\build_edgeiq_timestamp_safe_market_snapshot_spine_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `EDGEIQ_TIMESTAMP_SAFE_MARKET_SNAPSHOT_SPINE_V1`
- `HAS_TIMESTAMP_SAFE_ROWS`
- `HIGH_LATE_PRE_RACE`
- `LATE_PRE_RACE_SAFE`
- `MEDIUM_PRE_RACE`
- `NO_TIMESTAMP_SAFE_MARKET_FOUND`
- `QUARANTINED_CANDIDATE_SOURCE`
- `ROW_CANDIDATE`
- `UNSAFE_NO_TIMESTAMP`
- `candidate_files`
- `candidate_rows`
- `cannot_compare_timestamp_to_race_time`
- `capture_timestamp_utc`
- `capture_timestamp_v1`
- `classification`
- `date`
- `fixed_odds_update_time`
- `has_horse`
- `has_race_date`
- `has_race_no`
- `has_race_time`
- `has_timestamp`
- `has_track`
- `horse`
- `horse_key`
- `horse_key_clean_v1`
- `horse_name`
- `inventory_classification`
- `jump_time`
- `latest_safe_timestamp`
- `live_runner_board`
- `market_update_time`
- `meeting_date`
- `missing_or_unparseable_market_timestamp`
- `missing_or_unparseable_race_time_or_jump_time`
- `odds_update_time`
- `quarantine_classification`
- `race`
- `race_date`
- `race_id`
- `race_key`
- `race_key_v1`
- `race_no`
- `race_number`
- `race_time`
- `race_time_columns`
- `race_time_utc`
- `race_time_value`
- `races_covered`
- `runner`
- `runner_key`
- `runner_name`
- `runners_covered`
- `safe_row_classification`
- `scheduled_race_time`
- `scheduled_time`
- `snapshot_status`
- `snapshot_timestamp`
- `timestamp`
- `timestamp_before_race_time`
- `timestamp_columns`
- `timestamp_dt`
- `timestamp_value`
- `track`
- `updated_at`

### `scripts\build_edgeiq_trainer_context_research_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `BARRIER`
- `CLASS`
- `CONTEXT_EDGE`
- `CONTEXT_RISK`
- `DISTANCE`
- `MILD_CONTEXT_EDGE`
- `TRACK`
- `barrier`
- `context_edge`
- `context_risk`
- `context_rows`
- `context_type`
- `context_value`
- `distance`
- `mild_context_edge`
- `race_class`
- `status`
- `track`
- `track_condition`
- `trainer`
- `trainer_base_place_pct`
- `trainer_base_starts`
- `trainer_base_win_pct`
- `trainer_canonical`
- `unique_trainers`
- `within_trainer_place_lift_pct`
- `within_trainer_win_lift_pct`

### `scripts\build_edgeiq_trainer_context_research_v2.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `BARRIER`
- `CLASS`
- `CONTEXT_EDGE`
- `CONTEXT_RISK`
- `DISTANCE`
- `MILD_CONTEXT_EDGE`
- `TRACK`
- `TRACK_FAMILY`
- `TRAINER`
- `barrier`
- `context_edge`
- `context_risk`
- `context_rows`
- `context_type`
- `context_value`
- `distance`
- `mild_context_edge`
- `race_class`
- `status`
- `track`
- `track_condition`
- `trainer`
- `trainer_base_place_pct`
- `trainer_base_starts`
- `trainer_base_win_pct`
- `trainer_canonical`
- `unique_trainers`
- `within_trainer_place_lift_pct`
- `within_trainer_win_lift_pct`

### `scripts\build_edgeiq_weight_context_join_expansion_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_WEIGHT_CONTEXT_JOIN_EXPANSION_V1`
- `EDGEIQ_WEIGHT_CONTEXT_JOIN_EXPANSION_V1_BUILT`
- `JOIN_EXPANSION_WEIGHT_CONTEXT_ONLY_NO_AGE_SEX_NO_WFA_CLAIM`
- `MISSING_WEIGHT`
- `NO_CANDIDATE`
- `STAGE_1_EXACT_HORSE_DATE_TRACK_RACE_NO`
- `STAGE_2_HORSE_DATE_DISTANCE`
- `STAGE_3_HORSE_DATE_RACE_CLASS`
- `STAGE_4_HORSE_TRACK_DISTANCE_FINISH_MARGIN`
- `STAGE_5_NORMALISED_HORSE_DATE_TOLERANCE`
- `TOPWEIGHT_61_PLUS`
- `allocated_weight`
- `candidate_count`
- `carried_weight_kg`
- `class_name`
- `date`
- `distance`
- `distance_m`
- `horse`
- `horse_key`
- `horse_name`
- `jockey`
- `join_candidate_count`
- `join_status`
- `meeting_date`
- `performance_rating`
- `performance_rating_v5_1`
- `performance_rating_v6`
- `performance_rating_v6_1_research`
- `race`
- `race_class`
- `race_class_clean`
- `race_class_clean_v3_3`
- `race_class_raw`
- `race_class_recovered`
- `race_date`
- `race_no`
- `race_number`
- `runner_name`
- `safe_candidate_count`
- `status`
- `track`
- `track_condition`
- `trainer`
- `v6_distance`
- `v6_horse`
- `v6_race_date`
- `v6_track`
- `weight`
- `weight_band_research_v1`
- `weight_carried`
- `weight_source_class`
- `weight_source_distance`
- `weight_source_finish`
- `weight_source_jockey`
- `weight_source_margin`
- `weight_source_race_date`
- `weight_source_race_no`
- `weight_source_rows`
- `weight_source_sp`
- `weight_source_track`
- `weight_source_trainer`

### `scripts\build_edgeiq_weight_context_join_quality_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `DATE_MISMATCH`
- `DATE_TOLERANCE`
- `DISTANCE_MISMATCH`
- `EDGEIQ_WEIGHT_CONTEXT_JOIN_QUALITY_V1`
- `EXACT_DATE`
- `EXACT_DISTANCE`
- `IMPOSSIBLE_WEIGHT`
- `MISSING_DATE`
- `MISSING_DISTANCE`
- `MISSING_WEIGHT`
- `NEAR_DISTANCE`
- `PLAUSIBLE_WEIGHT`
- `STAGE_1_EXACT_HORSE_DATE_TRACK_RACE_NO`
- `STAGE_2_HORSE_DATE_DISTANCE`
- `STAGE_3_HORSE_DATE_RACE_CLASS`
- `STAGE_4_HORSE_TRACK_DISTANCE_FINISH_MARGIN`
- `STAGE_5_DATE_TOLERANCE_RISK_AUDIT`
- `STAGE_5_NORMALISED_HORSE_DATE_TOLERANCE`
- `SUSPICIOUS_WEIGHT_RANGE`
- `WEIGHT_CONTEXT_JOIN_QUALITY_ONLY_NO_AGE_SEX_NO_WFA_CLAIM`
- `carried_weight_kg`
- `date_delta_days`
- `date_quality`
- `distance`
- `distance_agreement`
- `distance_delta_m`
- `exact_date_rate_pct`
- `exact_distance_rate_pct`
- `horse`
- `impossible_weight_count`
- `join_candidate_count`
- `join_status`
- `performance_rating_v6_1_research`
- `race_class_clean`
- `race_date`
- `rating_coverage_pct`
- `same_horse_multiple_matches_same_day`
- `same_horse_multiple_matches_same_day_count`
- `suspicious_weight_jump`
- `suspicious_weight_jump_count`
- `tolerance_date_rate_pct`
- `track`
- `weight_coverage_pct`
- `weight_quality`
- `weight_source_class`
- `weight_source_distance`
- `weight_source_finish`
- `weight_source_margin`
- `weight_source_race_date`
- `weight_source_race_no`
- `weight_source_track`

### `scripts\build_edgeiq_weight_context_prior_rating_replay_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_WEIGHT_CONTEXT_PRIOR_RATING_REPLAY_V1`
- `EXCLUDED_RACE_GROUPS`
- `INSUFFICIENT_PRIOR_RATED_RUNNERS`
- `INSUFFICIENT_WEIGHT_ROWS`
- `PRIOR_RATING_WEIGHT_CONTEXT_REPLAY_ONLY_NO_AGE_SEX_NO_WFA_CLAIM`
- `absolute_weight_boost_used`
- `adjusted_top_pick_adjusted_prior_rating`
- `adjusted_top_pick_prior_rating`
- `adjusted_top_pick_prior_rating_date`
- `adjusted_top_pick_weight`
- `adjusted_top_pick_weight_delta_vs_avg_kg`
- `allocated_weight`
- `carried_weight_kg`
- `class_name`
- `date`
- `days_since_prior_rating`
- `distance`
- `distance_m`
- `eligible_runner_count`
- `excluded_race_groups`
- `horse`
- `horse_key`
- `horse_name`
- `kg_to_rating_points`
- `meeting_date`
- `original_prior_rating`
- `original_top_pick_prior_rating`
- `original_top_pick_prior_rating_date`
- `original_top_pick_weight`
- `performance_rating`
- `performance_rating_v5_1`
- `performance_rating_v6`
- `performance_rating_v6_1_research`
- `prior_rating`
- `prior_rating_date`
- `race`
- `race_avg_weight_kg`
- `race_class`
- `race_class_clean`
- `race_date`
- `race_key`
- `race_no`
- `race_number`
- `race_relative_only`
- `races_tested`
- `runner_name`
- `runners_tested`
- `suspicious_lightweight_boost_flag`
- `suspicious_lightweight_boosts`
- `target_rows_with_prior_rating`
- `target_rows_with_weight`
- `track`
- `weight`
- `weight_carried`
- `weight_delta_vs_avg_kg`

### `scripts\build_edgeiq_weight_context_research_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `ABOVE_RACE_AVG`
- `BELOW_RACE_AVG`
- `DATE_TRACK_HORSE`
- `EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1`
- `EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1_BUILT`
- `EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1_NO_WEIGHT_MATCHES`
- `EXACT_DATE_TRACK_HORSE_DISTANCE`
- `MISSING_WEIGHT`
- `NEAR_RACE_AVG`
- `NO_WEIGHT_MATCH`
- `TOPWEIGHT_61_PLUS`
- `WEIGHT_CONTEXT_ONLY_NO_AGE_SEX_NO_WFA_CLAIM`
- `WELL_ABOVE_RACE_AVG`
- `WELL_BELOW_RACE_AVG`
- `allocated_weight`
- `avg_carried_weight_kg`
- `avg_v6_1_rating`
- `barrier`
- `carried_weight_kg`
- `date`
- `distance`
- `distance_m`
- `horse`
- `horse_key`
- `horse_name`
- `jockey`
- `join_candidate_count`
- `joined_weight_rows`
- `max_carried_weight_kg`
- `median_carried_weight_kg`
- `median_v6_1_rating`
- `meeting_date`
- `min_carried_weight_kg`
- `performance_rating_v3`
- `performance_rating_v5_1`
- `performance_rating_v6`
- `performance_rating_v6_1_research`
- `performance_rating_v6_1_research_reason`
- `race_avg_weight_kg`
- `race_class`
- `race_class_clean`
- `race_class_raw`
- `race_class_recovered`
- `race_date`
- `race_max_weight_kg`
- `race_min_weight_kg`
- `race_relative_weight_rows`
- `runner_name`
- `status`
- `track`
- `track_condition`
- `trainer`
- `v6_1_rating_rows`
- `weight`
- `weight_and_rating_rows`
- `weight_band_research_v1`
- `weight_carried`
- `weight_delta_to_race_avg_kg`
- `weight_join_coverage_pct`
- `weight_rank_in_joined_race`
- `weight_relative_band_research_v1`
- `weight_source`
- `weight_source_barrier`
- `weight_source_file`
- `weight_source_jockey`
- `weight_source_rows`
- `weight_source_sp`
- `weight_source_trainer`
- `weight_source_weight_raw`

### `scripts\build_edgeiq_weight_context_stage2_replay_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `EDGEIQ_WEIGHT_CONTEXT_STAGE2_REPLAY_V1`
- `IMPOSSIBLE_WEIGHT`
- `MISSING_RATING_OR_WEIGHT`
- `NO_POST_RACE_RATING_LEAKAGE`
- `STAGE_2_HORSE_DATE_DISTANCE`
- `STAGE_2_HORSE_DATE_DISTANCE_ONLY`
- `absolute_weight_boost_used`
- `adjusted_top_pick_adjusted_rating`
- `adjusted_top_pick_original_rating`
- `adjusted_top_pick_weight`
- `cap_hit_runner_count`
- `carried_weight_kg`
- `distance`
- `excluded_race_groups`
- `horse`
- `kg_to_rating_points`
- `original_top_pick_rating`
- `original_top_pick_weight`
- `performance_rating_v6_1_research`
- `race_avg_weight_kg`
- `race_class_clean`
- `race_date`
- `race_key`
- `race_relative_only`
- `replay_races`
- `stage2_runner_count`
- `stage2_runner_rows`
- `suspicious_overadjustment_races`
- `track`
- `weight_context_top_pick_better`
- `weight_context_top_pick_better_count`
- `weight_quality`

### `scripts\build_feed_context_service_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `normalised_track`
- `race_date`
- `race_no`
- `track`

### `scripts\build_intelligence_snapshot_layer_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- No likely column literals detected.

### `scripts\build_strict_live_race_snapshot_v2.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `barrier`
- `edgeRating`
- `edge_rating`
- `edgerating`
- `horse`
- `horseFormUrl`
- `horseName`
- `horseProfileUrl`
- `horse_name`
- `horseform`
- `horsename`
- `jockey`
- `jockeyName`
- `jockey_name`
- `rating`
- `runner`
- `runnerDNA`
- `runnerName`
- `runner_dna`
- `runner_name`
- `runnerdna`
- `runnername`
- `trainer`
- `trainerName`
- `trainer_name`
- `weight`

### `scripts\diagnose_edgeiq_snapshot_count_mismatch_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `DEDUPE_SUMMARY_STALE_MISSING_LATEST_TIMESTAMP`
- `PIPELINE_STATUS_STALE_OR_COUNT_LOGIC_DIFFERS`
- `RERUN_DEDUPE_AUDIT_THEN_PIPELINE_STATUS`
- `SNAPSHOT_TIMESTAMPS_DUPLICATED_IN_HISTORY`
- `dedupe_summary_races`
- `dedupe_summary_runners`
- `distinct_timestamps`
- `history_races`
- `history_runners`
- `horse_key`
- `missing_history_timestamps`
- `pipeline_status`
- `pipeline_status_summary_found`
- `race_date`
- `race_no`
- `races`
- `races_per_snapshot`
- `runners`
- `runners_per_snapshot`
- `snapshot_timestamp`
- `snapshot_timestamps`
- `timestamp_duplicate_in_history`
- `timestamp_duplicate_issue_count`
- `timestamp_present_in_dedupe_summary`
- `timestamps`
- `timestamps_with_non_87_row_count`
- `track`

### `scripts\embed_production_csv_snapshots_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- No likely column literals detected.

### `scripts\fix_edgeiq_command_context_strip_type_2l.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- No likely column literals detected.

### `scripts\move_edgeiq_race_context_to_store_2i.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- No likely column literals detected.

### `scripts\prepare_edgeiq_command_summary_context_2f.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- No likely column literals detected.

### `scripts\refactor_core_adapters_to_snapshot_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `RUNNER_DNA`
- `horse`
- `pace_advantage_runner`
- `pressure_risk_runner`
- `race_shape_label`
- `race_shape_story`
- `runner_dna_v6_1_narrative`
- `runner_dna_v6_2_narrative`
- `runner_profile_summary`

### `scripts\refactor_remaining_adapters_to_snapshot_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `TRACK`
- `TRACKADAPTER_SOURCE`
- `TrackAdapter`
- `track`
- `track_intelligence_comment_v2_1`

### `scripts\run_edgeiq_price_truth_daily_snapshot_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `True`
- Suitability reference: `False`
- Context reference: `False`

Likely referenced columns:

- `RESULTS_TRUTH_LOOP_UPDATE_DIAGNOSTIC_V1`
- `SAFE_TO_UPDATE_RESULTS_LOOP`
- `SPORTSBET_FULL_DAY_RACECARD_CAPTURE_V5_2`
- `final_status`
- `health_status`
- `health_status_counts`
- `racecards`
- `results_loop_update_diagnostic_rows`
- `results_truth_loop_update_ready`
- `results_truth_loop_update_status`
- `runner_script`
- `safest_update_source_recommendation`
- `settlement_status`
- `settlement_write_status`
- `status`

### `scripts\test_tab_api_browser_context_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `status`
- `statusText`

### `scripts\test_tab_api_context_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `status`

### `scripts\wire_active_context_remaining_adapters_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- `TRACK`
- `track`
- `track_intelligence_comment_v2_1`

### `scripts\wire_active_race_context_into_adapters_v1.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- No likely column literals detected.

### `scripts\wire_edgeiq_command_temp_race_context_2h.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- No likely column literals detected.

### `scripts\wire_edgeiq_toolbar_race_context_2j.py`

- Race-entry reference: `False`
- Projected-performance reference: `False`
- Snapshot reference: `False`
- Suitability reference: `False`
- Context reference: `True`

Likely referenced columns:

- No likely column literals detected.

## Referenced Tokens Missing From Current Schema

- `ABOVE_RACE_AVG`
- `ACTIVE_ENTRY`
- `ACTIVE_RATING_AUDIT`
- `ACTIVE_RATING_BUILDER`
- `AGG_B_WEIGHTED_ARITHMETIC_MEAN_EXPONENTIAL_HALF_LIFE_V1`
- `ALLOCATED_WEIGHT`
- `ALL_REQUIRED_CONTEXT_ELIGIBLE`
- `ARCHIVED_HISTORICAL_RATING_BUILDER`
- `A_CURRENT_FULL_CONTEXT`
- `BARRIER_BUCKET`
- `BARRIER_CONTEXT`
- `BELOW_RACE_AVG`
- `BLANK_RACE_ID`
- `BLOCKED_AMBIGUOUS_SURFACE`
- `BLOCKED_UNSUPPORTED_SURFACE`
- `BUILDER_TRACE_WRITTEN`
- `B_DATE_TRACK_DISTANCE_SOURCE`
- `CANDIDATE`
- `CANDIDATE_DEFINED`
- `CANONICAL_RACE_ENTRIES_AVAILABLE`
- `CANONICAL_SURFACE_REGISTRY_BUILT`
- `CLASS`
- `CLASS_BUCKET`
- `CLASS_CONTEXT`
- `COMPLETE_CONTEXT_ELIGIBLE`
- `COMPLETE_CONTEXT_INELIGIBLE`
- `CONTEXT_BUCKET`
- `CONTEXT_EDGE`
- `CONTEXT_INELIGIBLE`
- `CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTED_PERFORMANCE`
- `CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTMENT`
- `CONTEXT_NOT_ELIGIBLE_FOR_PARAMETER_SELECTION`
- `CONTEXT_PARAMETER_GOVERNED`
- `CONTEXT_RISK`
- `CONTEXT_WAREHOUSE_V2_GRAPHQL_BUILT`
- `CONTEXT_WAREHOUSE_V2_GRAPHQL_SIGNAL_VIEW_BUILT`
- `CURRENT_RACE_ENTRY_SOURCE_AUDIT_WRITTEN`
- `CURRENT_SUITABILITY_V1`
- `C_DATE_TRACK_DISTANCE_ROUND_25_SOURCE`
- `Context`
- `DATA_COVERAGE_PARTIAL_PROJECTED_PERFORMANCE_AND_EPI_UNAVAILABLE`
- `DATE`
- `DATE_MISMATCH`
- `DATE_TOLERANCE`
- `DATE_TRACK_HORSE`
- `DEDUPE_SUMMARY_STALE_MISSING_LATEST_TIMESTAMP`
- `DISTANCE`
- `DISTANCE_BUCKET`
- `DISTANCE_CONTEXT`
- `DISTANCE_EXACT`
- `DISTANCE_MISMATCH`
- `DOWNSTREAM_PROJECTED_PERFORMANCE_AUDIT`
- `DOWNSTREAM_PROJECTED_PERFORMANCE_BUILDER`
- `DUPLICATE_HISTORICAL_RATING_IDENTITY`
- `D_DATE_TRACK_DISTANCE_ROUND_50_SOURCE`
- `EDGEIQ_CANONICAL_SURFACE_REGISTRY_V1`
- `EDGEIQ_EPI_CONTEXT_V1_AUDIT_FAIL`
- `EDGEIQ_EPI_CONTEXT_V1_AUDIT_PASS`
- `EDGEIQ_LIVE_RAW_ON_TRACK_WEATHER_SNAPSHOT_V1_BUILT`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_GENUINE_EPI_INPUT`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_PROJECTED_FACT_INPUT`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_FAIL`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_FULL_LIVE_PASS`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_HORSE_RATINGS_READY_NO_LIVE_MATCH`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_LIVE_PARTIAL_HISTORICAL_COVERAGE`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_LIVE_PARTIAL_SOURCE_COVERAGE`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_NO_ACTIVE_RACE_ENTRIES`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ELIGIBILITY_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ELIGIBILITY_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_CONTEXT_ELIGIBILITY_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_EPI_COMPONENT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_EPI_COMPONENT_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_EPI_COMPONENT_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_EPI_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_EPI_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_EPI_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_ERI_CONTEXT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_ERI_CONTEXT_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_ERI_CONTEXT_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_FACT_V1_AUDIT`
- `EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_SNAPSHOT_SCHEMA_TRACE_COMPLETE`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_BUILD_PASS`
- `EDGEIQ_RACE_ERI_FACT_V1_AUDIT_FAIL`
- `EDGEIQ_RACE_ERI_FACT_V1_AUDIT_PASS`
- `EDGEIQ_RACE_ERI_FACT_V1_BUILD_PASS`
- `EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2`
- `EDGEIQ_TIMESTAMP_SAFE_MARKET_SNAPSHOT_SPINE_V1`
- `EDGEIQ_WEIGHT_CONTEXT_JOIN_EXPANSION_V1`
- `EDGEIQ_WEIGHT_CONTEXT_JOIN_EXPANSION_V1_BUILT`
- `EDGEIQ_WEIGHT_CONTEXT_JOIN_QUALITY_V1`
- `EDGEIQ_WEIGHT_CONTEXT_PRIOR_RATING_REPLAY_V1`
- `EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1`
- `EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1_BUILT`
- `EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1_NO_WEIGHT_MATCHES`
- `EDGEIQ_WEIGHT_CONTEXT_STAGE2_REPLAY_V1`
- `EMERGENCY_ENTRY`
- `EPI_INPUTS_PARTIAL_PROJECTED_PERFORMANCE_MISSING`
- `EPI_RELATIVE_CONTEXT_PUBLISHED`
- `EPI_RELATIVE_CONTEXT_RECONCILED`
- `ERI_CONTEXT_PUBLISHED`
- `ERI_CONTEXT_RECONCILED`
- `EXACT_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `EXACT_CONTEXT_PARAMETER_SELECTED`
- `EXACT_DATE`
- `EXACT_DATE_TRACK_HORSE_DISTANCE`
- `EXACT_DISTANCE`
- `EXCLUDED_RACE_GROUPS`
- `EXPECTED_ADJUSTED_STATUS`
- `EXPECTED_AGGREGATE_STATUS`
- `E_DATE_TRACK_RACE_NAME_SOURCE`
- `FACTUAL_DECLARED_RACE_CONTEXT_GOVERNED`
- `FIELD_MEAN_PROJECTED_PERFORMANCE`
- `FRONTRUNNER`
- `FRONT_RUNNER`
- `FUTURE_OR_SAME_RACE_OBSERVATION`
- `F_DATE_TRACK_DISTANCE_BAND_SOURCE`
- `GOVERNED_CONTEXT_ADJUSTED_PERFORMANCE`
- `GOVERNED_CONTEXT_ADJUSTMENT_APPLIED`
- `GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `GOVERNED_PROJECTED_PERFORMANCE`
- `GOVERNED_RACE_ENTRY_EPI`
- `GOVERNED_RACE_ENTRY_EPI_COMPONENT`
- `GOVERNED_RACE_ENTRY_EPI_ORDERING`
- `GOVERNED_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT`
- `GOVERNED_RACE_ENTRY_EPI_RELATIVE_CONTEXT`
- `GOVERNED_RACE_ENTRY_ERI_CONTEXT`
- `GOVERNED_RACE_EPI_DISTRIBUTION`
- `GOVERNED_RACE_EPI_ORDERING_SUMMARY`
- `GOVERNED_RACE_EPI_PUBLICATION_SNAPSHOT`
- `GOVERNED_RACE_ERI`
- `GOVERNED_SUITABILITY_AGGREGATE`
- `GOVERNED_SUITABILITY_COMPONENT`
- `HAS_TIMESTAMP_SAFE_ROWS`
- `HIGH_LATE_PRE_RACE`
- `HISTORICAL_HORSE_RATING_GOVERNED`
- `HISTORICAL_PERFORMANCE`
- `HISTORICAL_RATING`
- `HISTORICAL_RATING_AVAILABLE`
- `HORSE`
- `IMPOSSIBLE_WEIGHT`
- `INELIGIBLE_INVALID_CONTEXT`
- `INELIGIBLE_MISSING_CONTEXT`
- `INELIGIBLE_UNSUPPORTED_CONTEXT`
- `INSUFFICIENT_PRIOR_RATED_RUNNERS`
- `INSUFFICIENT_WEIGHT_ROWS`
- `INVALID_TRACK_CONDITION_NUMBER`
- `JOCKEY`
- `JOIN_EXPANSION_WEIGHT_CONTEXT_ONLY_NO_AGE_SEX_NO_WFA_CLAIM`
- `Jockey`
- `LATE_PRE_RACE_SAFE`
- `LENGTHS_V_STANDARD_V2_CANDIDATE_BUILT`
- `LIGHTLY_RACED`
- `LIVE_CONTEXT_SIGNAL_FEED_V2_GRAPHQL_BUILT`
- `LIVE_RUNNER_BOARD`
- `MEDIUM_PRE_RACE`
- `MILD_CONTEXT_EDGE`
- `MISSING_DATE`
- `MISSING_DISTANCE`
- `MISSING_RATING_OR_WEIGHT`
- `MISSING_SURFACE`
- `MISSING_TRACK_CONDITION_NUMBER`
- `MISSING_WEIGHT`
- `NEAR_DISTANCE`
- `NEAR_RACE_AVG`
- `NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH`
- `NORMALISED_WEIGHTED_ADDITIVE_EPI_V1`
- `NO_ACTIVE_RACE_ENTRIES_AVAILABLE`
- `NO_CANDIDATE`
- `NO_CURRENT_RACE_ENTRY`
- `NO_DATE_EVIDENCE`
- `NO_HISTORICAL_PERFORMANCE`
- `NO_POST_RACE_RATING_LEAKAGE`
- `NO_TEMPORALLY_ELIGIBLE_RATING`
- `NO_TIMESTAMP_SAFE_MARKET_FOUND`
- `NO_WEIGHT_MATCH`
- `PARTIAL_PROJECTED_PERFORMANCE_MISSING`
- `PASS_FOR_PARAMETER_SOURCES_AND_HORSE_RATING_CANDIDATE`
- `PERFORMANCE_ADJUSTED`
- `PERFORMANCE_BASE_ROWS_BUILT`
- `PERFORMANCE_INTELLIGENCE_ONLY`
- `PERFORMANCE_INTELLIGENCE_PRODUCTION_V2_REVIEW_REQUIRED`
- `PERFORMANCE_INTELLIGENCE_PRODUCTION_V2_SYNTHETIC_CHAIN_PASS`
- `PERFORMANCE_INTELLIGENCE_PROGRAM_SMOKE_PASS`
- `PIPELINE_STATUS_STALE_OR_COUNT_LOGIC_DIFFERS`
- `PLAUSIBLE_WEIGHT`
- `POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE`
- `PRIOR_RATING_ELIGIBLE`
- `PRIOR_RATING_WEIGHT_CONTEXT_REPLAY_ONLY_NO_AGE_SEX_NO_WFA_CLAIM`
- `PROJECTED_PERFORMANCE_PUBLISHED`
- `PROJECTED_PERFORMANCE_RECONCILED`
- `PROJECTED_PERFORMANCE_REFERENCE`
- `PROJECTED_PERFORMANCE_UNAVAILABLE`
- `PROJECTED_STATUS`
- `PROXY_CONTEXTUAL_WATCH`
- `QUARANTINED_CANDIDATE_SOURCE`
- `RACE`
- `RACE_CATALOGUE`
- `RACE_CONTEXT`
- `RACE_ENTRY_EPI_SNAPSHOT_PUBLISHED`
- `RACE_ENTRY_EPI_SNAPSHOT_RECONCILED`
- `RACE_ENTRY_FACT_BUILDER_OR_PATH_MISSING`
- `RACE_ENTRY_SNAPSHOT_BUILDER_SCHEMA_MISMATCH`
- `RACE_EPI_DISTRIBUTION_PUBLISHED`
- `RACE_EPI_DISTRIBUTION_RECONCILED`
- `RACE_EPI_ORDERING_SUMMARY_PUBLISHED`
- `RACE_EPI_ORDERING_SUMMARY_RECONCILED`
- `RACE_EPI_SNAPSHOT_PUBLISHED`
- `RACE_EPI_SNAPSHOT_RECONCILED`
- `RACING_COM_GETRACEFORM`
- `RAIL_CONTEXT`
- `RATING_METHOD`
- `RERUN_DEDUPE_AUDIT_THEN_PIPELINE_STATUS`
- `RESULTS_TRUTH_LOOP_UPDATE_DIAGNOSTIC_V1`
- `ROW_CANDIDATE`
- `RUNNER`
- `RUNNER_DNA`
- `RUNNER_FIELD_CANDIDATE`
- `RUNNER_NAME_STRICT_CURRENT_RACE_PLUS_ASOF_HISTORY`
- `RUNNER_PROFILE_ENGINE_V1_1_BUILT`
- `RUNNER_SECTIONAL_PERFORMANCE_V2_BUILT`
- `SAFE_TO_UPDATE_RESULTS_LOOP`
- `SCRATCHED_ENTRY`
- `SNAPSHOT_TIMESTAMPS_DUPLICATED_IN_HISTORY`
- `SPORTSBET_FULL_DAY_RACECARD_CAPTURE_V5_2`
- `STAGE_1_EXACT_HORSE_DATE_TRACK_RACE_NO`
- `STAGE_2_HORSE_DATE_DISTANCE`
- `STAGE_2_HORSE_DATE_DISTANCE_ONLY`
- `STAGE_3_HORSE_DATE_RACE_CLASS`
- `STAGE_4_HORSE_TRACK_DISTANCE_FINISH_MARGIN`
- `STAGE_5_DATE_TOLERANCE_RISK_AUDIT`
- `STAGE_5_NORMALISED_HORSE_DATE_TOLERANCE`
- `STALE_RACE_DATE`
- `STANDARD_TIME_ELIGIBLE`
- `STATUS`
- `SUITABILITY`
- `SUITABILITY_AGGREGATED`
- `SUITABILITY_CONTEXT_INPUTS_UNAVAILABLE`
- `SURFACE`
- `SURFACE_CONTEXT`
- `SUSPICIOUS_WEIGHT_RANGE`
- `Surface`
- `THREE_DAY_RACE_CATALOG`
- `TOPWEIGHT_61_PLUS`
- `TRACK`
- `TRACKADAPTER_SOURCE`
- `TRACK_CONDITION`
- `TRACK_CONFIGURATION`
- `TRACK_CONTEXT`
- `TRACK_FAMILY`
- `TRAINER`
- `TRAINER_JOCKEY`
- `TrackAdapter`
- `Trainer`
- `UNAVAILABLE_MISSING_RACE_NAME`
- `UNCLASSIFIED_CANDIDATE`
- `UNKNOWN_DATE`
- `UNKNOWN_DECLARATION_STATUS`
- `UNSAFE_NO_TIMESTAMP`
- `UNSUPPORTED_CANDIDATE`
- `UNSUPPORTED_SURFACE`
- `UPSTREAM_HORSE_PERFORMANCE_AUDIT`
- `UPSTREAM_HORSE_PERFORMANCE_BUILDER`
- `WEIGHT`
- `WEIGHT_35_TO_49_999999`
- `WEIGHT_50_TO_54_999999`
- `WEIGHT_55_TO_59_999999`
- `WEIGHT_60_TO_64_999999`
- `WEIGHT_65_TO_80`
- `WEIGHT_CONTEXT_JOIN_QUALITY_ONLY_NO_AGE_SEX_NO_WFA_CLAIM`
- `WEIGHT_CONTEXT_ONLY_NO_AGE_SEX_NO_WFA_CLAIM`
- `WELL_ABOVE_RACE_AVG`
- `WELL_BELOW_RACE_AVG`
- `absolute_weight_boost_used`
- `active_horses_with_ratings`
- `active_horses_without_ratings`
- `active_projected_performance_builder`
- `active_runners_with_epi`
- `active_runners_without_epi`
- `actual_suitability_aggregate_rows`
- `adjusted_performance_arithmetic_exact`
- `adjusted_performance_ids_unique`
- `adjusted_performance_population_exact`
- `adjusted_top_pick_adjusted_prior_rating`
- `adjusted_top_pick_adjusted_rating`
- `adjusted_top_pick_original_rating`
- `adjusted_top_pick_prior_rating`
- `adjusted_top_pick_prior_rating_date`
- `adjusted_top_pick_weight`
- `adjusted_top_pick_weight_delta_vs_avg_kg`
- `aggregate_suitability`
- `aggregate_suitability_value`
- `all_candidate_files`
- `all_populated_tiles_have_valid_context`
- `allocated_weight`
- `allocated_weight_eligibility`
- `allocated_weight_kg`
- `allowedRowStatuses`
- `archive_status`
- `asOfDate`
- `audit_edgeiq_horse_performance_`
- `audit_edgeiq_race_entry_projected_performance`
- `authorised_component_weight`
- `average_eligible_historical_rating_value`
- `average_runner_count`
- `avg_carried_weight_kg`
- `avg_v6_1_rating`
- `bad_or_stale_dates`
- `barrierNumber`
- `barrier_adjustment`
- `barrier_band`
- `barrier_context_eligibility`
- `barrier_number`
- `barrier_specialist_logic_built`
- `barrier_suitability_value`
- `below_minimum_field_size_races`
- `blank_context_type`
- `blank_timestamp_flag_v1`
- `blank_timestamp_rows`
- `build_edgeiq_historical_performance_rating`
- `build_edgeiq_horse_performance_`
- `build_edgeiq_race_entry_projected_performance`
- `candidate_E_unavailable`
- `candidate_count`
- `candidate_exists`
- `candidate_file_count`
- `candidate_files`
- `candidate_hash`
- `candidate_hash_comparison`
- `candidate_path`
- `candidate_paths_active`
- `candidate_promotion_result`
- `candidate_races`
- `candidate_rows`
- `cannot_compare_timestamp_to_race_time`
- `canonical_horse_id`
- `canonical_horse_name`
- `canonical_race_id_coverage_sample`
- `canonical_runner_id_coverage_sample`
- `canonical_surface_group`
- `canonical_surface_groups`
- `cap_hit_runner_count`
- `capture_timestamp_utc`
- `capture_timestamp_v1`
- `carried_weight`
- `carried_weight_kg`
- `change_classification`
- `class`
- `classFamily`
- `class_adjustment`
- `class_band`
- `class_columns`
- `class_combo`
- `class_context_eligibility`
- `class_name`
- `class_profile`
- `class_profile_1`
- `class_profile_count`
- `class_suitability_value`
- `classification`
- `collision_status`
- `combo_vs_jockey_place_lift_pct`
- `combo_vs_jockey_win_lift_pct`
- `combo_vs_trainer_place_lift_pct`
- `combo_vs_trainer_win_lift_pct`
- `complete_context_eligibility`
- `complete_context_eligible_rows`
- `complete_context_ineligible_rows`
- `consumer_status`
- `consumes_projected_performance`
- `consumes_rating_fact`
- `context`
- `context_adjusted`
- `context_adjusted_performance_decision`
- `context_adjusted_performance_rows`
- `context_adjusted_performance_value`
- `context_adjusted_rating`
- `context_adjustment`
- `context_adjustment_application_decision`
- `context_adjustment_rows`
- `context_arithmetic_exact`
- `context_band`
- `context_categories`
- `context_edge`
- `context_eligibility`
- `context_eligibility_rows`
- `context_exists`
- `context_fields`
- `context_governance`
- `context_governance_complete`
- `context_historical_rating_value`
- `context_id`
- `context_ids_unique`
- `context_ineligible_rows`
- `context_key`
- `context_key_A_CURRENT_FULL_CONTEXT`
- `context_lineage_complete`
- `context_natural_keys_unique`
- `context_numeric_governance`
- `context_output_decimal_places`
- `context_parameter_evidence_sha256`
- `context_parameter_id`
- `context_parameter_registry_rows`
- `context_parameter_selection_decision`
- `context_parameter_selection_rows`
- `context_population_exact`
- `context_required_when_eligibility_rows_exist`
- `context_risk`
- `context_rounding_mode`
- `context_rows`
- `context_signal_1_context`
- `context_signal_1_entity_type`
- `context_signal_1_importance`
- `context_signal_1_insight`
- `context_signal_1_signal`
- `context_signal_1_starts`
- `context_signal_2_context`
- `context_signal_2_entity_type`
- `context_signal_2_insight`
- `context_signal_2_signal`
- `context_signal_3_context`
- `context_signal_3_entity_type`
- `context_signal_3_insight`
- `context_signal_3_signal`
- `context_signal_count`
- `context_signature_sha256`
- `context_type`
- `context_value`
- `contexts_17_plus`
- `contexts_2_4`
- `contexts_5_8`
- `contexts_9_16`
- `contexts_checked`
- `contextual_probability`
- `contextual_score`
- `contextual_score_rows`
- `conversion_status`
- `coverage_status`
- `crossRaceJoins`
- `crossRunnerJoins`
- `current_class_bucket`
- `current_distance_bucket`
- `current_or_future_race_entries`
- `current_race_entry_rows`
- `current_race_entry_source`
- `current_track`
- `date`
- `date_delta_days`
- `date_max_sample`
- `date_min_sample`
- `date_quality`
- `date_status_sample`
- `dates`
- `days_since_prior_rating`
- `decisions_and_statuses_governed`
- `declared_runner_count`
- `dedupe_status`
- `dedupe_status_counts`
- `dedupe_status_v1`
- `dedupe_summary_races`
- `dedupe_summary_runners`
- `deterministic_context_evidence`
- `deterministic_context_identity`
- `deterministic_relative_context_evidence`
- `deterministic_relative_context_identity`
- `distance`
- `distanceBand`
- `distance_above_minimum_epi`
- `distance_adjustment`
- `distance_agreement`
- `distance_band`
- `distance_band_key`
- `distance_band_v5_1`
- `distance_below_maximum_epi`
- `distance_bucket`
- `distance_combo`
- `distance_context_eligibility`
- `distance_delta_m`
- `distance_key`
- `distance_m`
- `distance_metres`
- `distance_min`
- `distance_num`
- `distance_profile`
- `distance_profile_1`
- `distance_profile_2`
- `distance_profile_count`
- `distance_round_25_key`
- `distance_round_50_key`
- `distance_span`
- `distance_suitability_value`
- `distinct_timestamps`
- `distribution_population_reconciliation_status`
- `duplicate_candidate_rows`
- `duplicate_race_runner_keys`
- `duplicate_same_horse_race_timestamp_count_v1`
- `duplicate_same_horse_same_race_timestamp_flag_v1`
- `duplicate_same_horse_same_race_timestamp_groups`
- `duplicate_same_horse_same_race_timestamp_rows`
- `duplicated_full_row_same_timestamp_count_v1`
- `duplicated_full_row_same_timestamp_flag_v1`
- `duplicated_full_row_same_timestamp_groups`
- `duplicated_full_row_same_timestamp_rows`
- `earliest_date`
- `edgeRating`
- `edge_rating`
- `edgeiq_current_suitability_v1`
- `edgeiq_horse_performance_rating_fact_v1`
- `edgeiq_live_raw_on_track_weather_v1`
- `edgeiq_race_entry_context_adjusted_performance_fact_v1`
- `edgeiq_race_entry_context_adjustment_fact_v1`
- `edgeiq_race_entry_context_eligibility_fact_v1`
- `edgeiq_race_entry_context_parameter_selection_fact_v1`
- `edgeiq_race_entry_epi_component_fact_v1`
- `edgeiq_race_entry_epi_fact_v1`
- `edgeiq_race_entry_epi_ordering_fact_v1`
- `edgeiq_race_entry_epi_publication_snapshot_fact_v1`
- `edgeiq_race_entry_epi_relative_context_fact_v1`
- `edgeiq_race_entry_eri_context_fact_v1`
- `edgeiq_race_entry_fact_v1`
- `edgeiq_race_entry_fact_v1_contract`
- `edgeiq_race_entry_horse_performance_snapshot_fact_v1`
- `edgeiq_race_entry_performance_context_fact_v1`
- `edgeiq_race_entry_projected_performance_fact_v1`
- `edgeiq_race_entry_suitability_aggregate_fact_v1`
- `edgeiq_race_entry_suitability_component_fact_v1`
- `edgeiq_race_epi_publication_snapshot_fact_v1`
- `edgeiq_race_eri_fact_v1`
- `edgeiq_vic_three_day_race_fields`
- `edgerating`
- `effective_from_date`
- `effective_to_date`
- `elapsed_time_observations`
- `elapsed_time_seconds`
- `eligibility_status`
- `eligible_adjusted_performance_rows`
- `eligible_historical_rating_count`
- `eligible_race_entry_count`
- `eligible_runner_count`
- `elite_overlay_runners`
- `entry`
- `entry_count`
- `entry_function`
- `epi_component_status`
- `epi_ordering_status`
- `epi_parameter_status`
- `epi_relative_context_publication_decision`
- `epi_relative_context_reconciliation_decision`
- `epi_relative_context_status`
- `epi_status`
- `epi_tie_status`
- `eri_context_evidence_sha256`
- `eri_context_publication_decision`
- `eri_context_reconciliation_decision`
- `evidence_candidates`
- `evidence_class`
- `exact_date_rate_pct`
- `exact_distance_count`
- `exact_distance_rate_pct`
- `exact_runner_id_matches`
- `exact_snapshot_runner_key_v1`
- `excluded_race_groups`
- `fact_races`
- `field_size_suitability_value`
- `final_status`
- `first_date`
- `first_eligible_rating_date`
- `fixed_odds_update_time`
- `forecast_rating`
- `gate_status`
- `governance_status`
- `grouping_candidate`
- `has_class`
- `has_horse`
- `has_race_date`
- `has_race_grade`
- `has_race_id`
- `has_race_name`
- `has_race_no`
- `has_race_time`
- `has_source_race_key`
- `has_timestamp`
- `has_track`
- `health_status`
- `health_status_counts`
- `highest_eligible_historical_rating_value`
- `historical_performance_component_evidence_sha256`
- `historical_performance_component_id`
- `historical_performance_normalised_value`
- `historical_performance_rows`
- `historical_performance_source`
- `historical_performance_weight`
- `historical_performance_weighted_value`
- `historical_rating_available`
- `historical_rating_eligibility`
- `historical_rating_match_count`
- `historical_rating_matches`
- `historical_rating_preserved`
- `historical_rating_value`
- `history_races`
- `history_runners`
- `horse`
- `horseCode`
- `horseFormUrl`
- `horseName`
- `horseProfileUrl`
- `horse_all_form_url`
- `horse_archetype`
- `horse_base_place_pct`
- `horse_base_win_pct`
- `horse_code`
- `horse_code_matches`
- `horse_context_rows`
- `horse_context_view`
- `horse_field`
- `horse_key`
- `horse_key_clean_v1`
- `horse_name`
- `horse_name_key_v1`
- `horse_no`
- `horse_performance`
- `horse_performance_profile_id`
- `horse_performance_rating`
- `horse_performance_rating_evidence_sha256`
- `horse_performance_rating_id`
- `horse_performance_rating_method`
- `horse_performance_rating_rows`
- `horse_performance_rating_status`
- `horse_performance_rating_value`
- `horse_rating`
- `horse_rating_hash`
- `horse_rows`
- `horse_run_style`
- `horse_snapshot`
- `horse_starts`
- `horse_url`
- `horseform`
- `horsename`
- `horses`
- `horses_with_cautions`
- `horses_with_condition_profiles`
- `horses_with_distance_profiles`
- `horses_with_track_profiles`
- `http_status`
- `id_candidates`
- `impossible_weight_count`
- `insufficient_history_runners`
- `inventory_classification`
- `is_official_race`
- `is_race_context_field`
- `jockey`
- `jockeyName`
- `jockey_adjustment`
- `jockey_base_place_pct`
- `jockey_base_starts`
- `jockey_base_win_pct`
- `jockey_best_context`
- `jockey_best_style`
- `jockey_best_style_ae`
- `jockey_best_style_roi`
- `jockey_best_style_win_pct`
- `jockey_canonical`
- `jockey_context`
- `jockey_context_rows`
- `jockey_context_score`
- `jockey_graphql`
- `jockey_key`
- `jockey_recent_100_win_pct`
- `jockey_recent_25_win_pct`
- `jockey_recent_50_win_pct`
- `jockey_rows`
- `join_candidate_count`
- `join_status`
- `joined_weight_rows`
- `jump_time`
- `kg_to_rating_points`
- `last_date`
- `latest_date`
- `latest_eligible_rating_date`
- `latest_governance_status`
- `latest_safe_timestamp`
- `latest_strictly_prior_rating_selected`
- `lifetime`
- `lightly_raced_profiles`
- `likely_race_entry_source`
- `live_contextual_feed`
- `live_contextual_feed_rows`
- `live_contextual_feed_rows_gt_0_if_live_exists`
- `live_form_context_grade`
- `live_form_context_reason`
- `live_peak_rating`
- `live_rating_match`
- `live_rows_with_nexus_context_score`
- `live_runner_board`
- `lowest_eligible_historical_rating_value`
- `malformed_timestamp_flag_v1`
- `malformed_timestamp_rows`
- `market_update_time`
- `match_status`
- `max_carried_weight_kg`
- `max_distance`
- `max_runner_count`
- `maximum_date`
- `median_carried_weight_kg`
- `median_runner_count`
- `median_v6_1_rating`
- `meetingDate`
- `meeting_track`
- `mentions_race_entry_fact`
- `mentions_race_fields`
- `method_status`
- `mild_context_edge`
- `min_carried_weight_kg`
- `min_distance`
- `minimum_date`
- `minimum_eligible_runner_count`
- `missing_context_rows`
- `missing_history_timestamps`
- `missing_or_unparseable_market_timestamp`
- `missing_or_unparseable_race_time_or_jump_time`
- `multi_runner_contexts`
- `nearby_distance_split`
- `nexus_context_band`
- `nexus_context_score`
- `nexus_context_score_populated_for_live_rows`
- `nine_components_per_eligible_entry`
- `no_forbidden_barrier_specialist_outputs_or_columns`
- `no_governed_horse_rating_for_canonical_runner_id`
- `no_temporally_eligible_rating`
- `normalisation_parameter_status`
- `normalised_track`
- `normalizedRunner`
- `odds_update_time`
- `official_distance_metres`
- `official_time`
- `one_aggregate_per_eligible_entry`
- `one_context_per_snapshot`
- `one_eligibility_row_per_context`
- `one_governed_context_adjusted_performance_decision_per_context_adjustment`
- `one_governed_context_adjustment_application_decision_per_parameter_selection`
- `one_governed_descriptive_epi_relative_context_row_per_race_entry`
- `one_governed_epi_ordering_row_per_race_entry`
- `one_governed_epi_publication_snapshot_row_per_race`
- `one_governed_epi_publication_snapshot_row_per_race_entry`
- `one_governed_epi_row_per_fully_reconciled_race_entry`
- `one_governed_eri_context_row_per_projected_performance_entry`
- `one_governed_projected_performance_per_suitability_aggregate`
- `one_governed_row_per_race_entry_and_epi_component`
- `one_governed_suitability_aggregate_per_eligible_context_adjusted_performance`
- `one_output_per_context_adjustment`
- `one_snapshot_per_race_entry`
- `orchestrator_status`
- `original_prior_rating`
- `original_top_pick_prior_rating`
- `original_top_pick_prior_rating_date`
- `original_top_pick_rating`
- `original_top_pick_weight`
- `overall_status`
- `overlay_runners`
- `pace_advantage_runner`
- `parameter_status`
- `partnership_context`
- `partnership_context_rows`
- `performance`
- `performance_adjusted_rows`
- `performance_context`
- `performance_context_rows`
- `performance_fact_rows`
- `performance_intelligence_base`
- `performance_intelligence_base_rows`
- `performance_rating`
- `performance_rating_v3`
- `performance_rating_v5_1`
- `performance_rating_v6`
- `performance_rating_v6_1_research`
- `performance_rating_v6_1_research_reason`
- `pipeline_status`
- `pipeline_status_summary_found`
- `point_in_time_boundary`
- `populated_contexts_present`
- `predictive_rating`
- `pressure_risk_runner`
- `previous_governance_status`
- `pricing_probability_rating_model_math_changed`
- `primary_context_eligibility_reason_code`
- `prior_rating`
- `prior_rating_count`
- `prior_rating_date`
- `prior_rating_matches`
- `production_orchestration_status`
- `production_runner_warehouse_hash`
- `profile_context_rows`
- `program_status`
- `projected_performance`
- `projected_performance_candidate_rows`
- `projected_performance_delta_from_historical`
- `projected_performance_evidence_sha256`
- `projected_performance_hash`
- `projected_performance_maximum`
- `projected_performance_mean`
- `projected_performance_mean_unrounded`
- `projected_performance_median`
- `projected_performance_minimum`
- `projected_performance_production_rows`
- `projected_performance_publication_decision`
- `projected_performance_range`
- `projected_performance_reconciliation_decision`
- `projected_performance_rows`
- `projected_performance_sum`
- `projected_performance_value`
- `projected_performance_vs_eri`
- `projected_race_count`
- `projected_race_shape`
- `projected_rating_v5_2`
- `projected_status`
- `projection_status_v5_1`
- `proxy_contextual_watch`
- `quarantine_classification`
- `race`
- `raceContextStrip`
- `raceDate`
- `raceDistance`
- `raceEntryNumber`
- `raceId`
- `raceIdentity`
- `raceKey`
- `raceName`
- `raceNo`
- `raceNumber`
- `raceShape`
- `raceStatus`
- `raceTime`
- `race_avg_weight_kg`
- `race_class`
- `race_class_band`
- `race_class_clean`
- `race_class_clean_v3_3`
- `race_class_clean_v5_1`
- `race_class_code`
- `race_class_key`
- `race_class_raw`
- `race_class_recovered`
- `race_component_population_count`
- `race_context_component_evidence_sha256`
- `race_context_component_id`
- `race_context_key_v1`
- `race_context_normalised_value`
- `race_context_weight`
- `race_context_weighted_value`
- `race_contexts`
- `race_count`
- `race_count_declared`
- `race_count_sample`
- `race_date_dt`
- `race_date_field`
- `race_date_key`
- `race_distance`
- `race_distance_invalid`
- `race_distance_m`
- `race_entry`
- `race_entry_context_adjusted_performance_evidence_sha256`
- `race_entry_context_adjusted_performance_id`
- `race_entry_context_adjusted_performance_status`
- `race_entry_context_adjustment_evidence_sha256`
- `race_entry_context_adjustment_id`
- `race_entry_context_adjustment_status`
- `race_entry_context_eligibility_evidence_sha256`
- `race_entry_context_eligibility_id`
- `race_entry_context_eligibility_rows`
- `race_entry_context_eligibility_status`
- `race_entry_context_parameter_selection_evidence_sha256`
- `race_entry_context_parameter_selection_id`
- `race_entry_context_parameter_selection_status`
- `race_entry_count`
- `race_entry_emergency`
- `race_entry_epi_component_evidence_sha256`
- `race_entry_epi_component_id`
- `race_entry_epi_evidence_sha256`
- `race_entry_epi_id`
- `race_entry_epi_ordering_evidence_sha256`
- `race_entry_epi_ordering_id`
- `race_entry_epi_publication_snapshot_evidence_sha256`
- `race_entry_epi_publication_snapshot_id`
- `race_entry_epi_relative_context_evidence_sha256`
- `race_entry_epi_relative_context_id`
- `race_entry_epi_rows`
- `race_entry_epi_snapshot_publication_decision`
- `race_entry_epi_snapshot_reconciliation_decision`
- `race_entry_epi_snapshot_status`
- `race_entry_eri_context_evidence_sha256`
- `race_entry_eri_context_id`
- `race_entry_eri_context_rows`
- `race_entry_eri_context_status`
- `race_entry_evidence_sha256`
- `race_entry_exists`
- `race_entry_fact`
- `race_entry_fact_exists`
- `race_entry_fact_hash`
- `race_entry_fact_not_required_for_empty_ratings`
- `race_entry_fact_not_required_for_empty_snapshots`
- `race_entry_fact_required_when_ratings_exist`
- `race_entry_fact_required_when_snapshots_exist`
- `race_entry_file`
- `race_entry_horse_performance_snapshot_evidence_sha256`
- `race_entry_horse_performance_snapshot_id`
- `race_entry_horse_performance_snapshot_rows`
- `race_entry_horse_performance_snapshot_status`
- `race_entry_id`
- `race_entry_input_rows`
- `race_entry_performance_context_evidence_sha256`
- `race_entry_performance_context_id`
- `race_entry_performance_context_rows`
- `race_entry_performance_context_status`
- `race_entry_projected`
- `race_entry_projected_performance`
- `race_entry_projected_performance_evidence_sha256`
- `race_entry_projected_performance_id`
- `race_entry_projected_performance_rows`
- `race_entry_projected_performance_status`
- `race_entry_rows`
- `race_entry_scratched`
- `race_entry_status`
- `race_entry_suitability_aggregate_evidence_sha256`
- `race_entry_suitability_aggregate_id`
- `race_entry_suitability_aggregate_status`
- `race_entry_suitability_aggregate_value`
- `race_entry_suitability_component_evidence_sha256`
- `race_entry_suitability_component_id`
- `race_entry_suitability_component_status`
- `race_entry_suitability_evidence_sha256`
- `race_entry_suitability_id`
- `race_epi_distribution_evidence_sha256`
- `race_epi_distribution_fact_evidence_sha256`
- `race_epi_distribution_fact_id`
- `race_epi_distribution_id`
- `race_epi_distribution_publication_decision`
- `race_epi_distribution_reconciliation_decision`
- `race_epi_distribution_rows`
- `race_epi_distribution_status`
- `race_epi_ordering_summary_evidence_sha256`
- `race_epi_ordering_summary_id`
- `race_epi_ordering_summary_publication_decision`
- `race_epi_ordering_summary_reconciliation_decision`
- `race_epi_ordering_summary_status`
- `race_epi_population_count`
- `race_epi_publication_snapshot_evidence_sha256`
- `race_epi_publication_snapshot_id`
- `race_epi_snapshot_publication_decision`
- `race_epi_snapshot_reconciliation_decision`
- `race_epi_snapshot_status`
- `race_eri_evidence_sha256`
- `race_eri_id`
- `race_eri_ids_unique`
- `race_eri_natural_keys_unique`
- `race_eri_parameter_evidence_sha256`
- `race_eri_parameter_id`
- `race_eri_parameter_status`
- `race_eri_rows`
- `race_eri_status`
- `race_fields`
- `race_grade`
- `race_grade_columns`
- `race_id`
- `race_id_columns`
- `race_key`
- `race_key_v1`
- `race_list`
- `race_max_weight_kg`
- `race_min_weight_kg`
- `race_name_available_for_candidate_E`
- `race_name_columns`
- `race_name_key`
- `race_no`
- `race_no_columns`
- `race_no_field`
- `race_no_key_v1`
- `race_no_missing_count`
- `race_no_num`
- `race_ordering_reconciled`
- `race_population_keys_exact`
- `race_rank`
- `race_relative_only`
- `race_relative_weight_rows`
- `race_shape_adjustment`
- `race_shape_label`
- `race_shape_story`
- `race_start_time`
- `race_status`
- `race_strength`
- `race_target_rating_v5_1`
- `race_time`
- `race_time_columns`
- `race_time_delta_id`
- `race_time_utc`
- `race_time_value`
- `racecards`
- `races`
- `races_covered`
- `races_in_snapshot_v1`
- `races_per_snapshot`
- `races_tested`
- `racing_surface`
- `rail_context_eligibility`
- `rating`
- `rating_adjustment`
- `rating_age_days`
- `rating_as_of_date`
- `rating_base`
- `rating_coverage_pct`
- `rating_id`
- `rating_method`
- `rating_rows`
- `ratings_exist_but_not_strictly_prior`
- `raw_context`
- `references_context`
- `references_projected_performance`
- `references_race_entry`
- `references_suitability`
- `relative_context_arithmetic_reconciled`
- `relative_context_governance_exact`
- `relative_context_lineage_complete`
- `relative_context_rows`
- `relative_context_sources_reconciled`
- `replay_races`
- `results_loop_update_diagnostic_rows`
- `results_truth_loop_update_ready`
- `results_truth_loop_update_status`
- `rows_with_context_signals`
- `run_date`
- `run_rating`
- `run_timestamp_utc`
- `runner`
- `runnerDNA`
- `runnerId`
- `runnerKey`
- `runnerName`
- `runnerNumber`
- `runnerStatus`
- `runner_count`
- `runner_count_declared`
- `runner_count_sample`
- `runner_dna`
- `runner_dna_band`
- `runner_dna_score`
- `runner_dna_v6_1_narrative`
- `runner_dna_v6_2_narrative`
- `runner_epi`
- `runner_epi_text`
- `runner_epi_value`
- `runner_id`
- `runner_input_rows`
- `runner_key`
- `runner_number`
- `runner_profile_summary`
- `runner_rank`
- `runner_rows`
- `runner_script`
- `runner_sectional_v2`
- `runner_status`
- `runnerdna`
- `runnername`
- `runners`
- `runners_below_minimum`
- `runners_covered`
- `runners_in_snapshot_v1`
- `runners_meeting_minimum`
- `runners_per_snapshot`
- `runners_tested`
- `safe_candidate_count`
- `safe_row_classification`
- `safest_update_source_recommendation`
- `same_horse_multiple_matches_same_day`
- `same_horse_multiple_matches_same_day_count`
- `same_horse_race_timestamp_key_v1`
- `sample_distances`
- `sample_horses`
- `scheduled_date`
- `scheduled_race_time`
- `scheduled_time`
- `schema_status`
- `scratch_status`
- `scratchingStatus`
- `sectional_performance_rows`
- `segment_distance_metres`
- `selectedRaceOutcomeRowsUsed`
- `selected_candidate_reason`
- `selected_horse_performance_rating_id`
- `selected_horse_performance_rating_value`
- `selected_rating_as_of_date`
- `settlement_status`
- `settlement_write_status`
- `single_runner_contexts`
- `single_runner_current_contexts`
- `snapshot_fewer_than_87_runners_flag_v1`
- `snapshot_fewer_than_8_races_flag_v1`
- `snapshot_status`
- `snapshot_timestamp`
- `snapshot_timestamp_clean`
- `snapshot_timestamps`
- `snapshots_with_fewer_than_87_runners`
- `snapshots_with_fewer_than_8_races`
- `source_adjusted_performance_builder_version`
- `source_adjusted_performance_evidence_sha256`
- `source_context_adjustment_builder_version`
- `source_context_adjustment_evidence_sha256`
- `source_context_builder_version`
- `source_context_eligibility_reason_code`
- `source_context_evidence_sha256`
- `source_context_lineage`
- `source_context_rows`
- `source_eligible_rating_evidence_sha256`
- `source_eligible_rating_ids_sha256`
- `source_projected_performance_builder_version`
- `source_projected_performance_builder_version_set`
- `source_projected_performance_evidence_set_sha256`
- `source_projected_performance_evidence_sha256`
- `source_projected_performance_id_set_sha256`
- `source_race_count`
- `source_race_entry_builder_version`
- `source_race_entry_evidence_sha256`
- `source_race_eri_builder_version`
- `source_race_eri_evidence_sha256`
- `source_race_key`
- `source_race_key_columns`
- `source_race_no`
- `source_race_populations_exact`
- `source_race_time_delta_evidence_sha256`
- `source_races`
- `source_rating_builder_version`
- `source_relative_context_evidence_sha256`
- `source_selected_rating_evidence_sha256`
- `source_status`
- `source_suitability_aggregate_builder_version`
- `source_suitability_aggregate_evidence_sha256`
- `source_surface`
- `source_track_name`
- `stage2_runner_count`
- `stage2_runner_rows`
- `standard_time_eligibility_status`
- `standard_time_facts`
- `standard_time_groups_available`
- `standard_time_id`
- `standard_time_rows`
- `standard_time_seconds`
- `standard_times`
- `startTime`
- `status`
- `statusText`
- `status_counts`
- `suitability`
- `suitabilityBand`
- `suitability_aggregate`
- `suitability_aggregate_decision`
- `suitability_aggregate_evidence_sha256`
- `suitability_aggregate_ids_unique`
- `suitability_aggregate_rows`
- `suitability_aggregate_value`
- `suitability_component`
- `suitability_component_count`
- `suitability_component_decision`
- `suitability_component_evidence_sha256`
- `suitability_component_id`
- `suitability_component_rows`
- `suitability_component_type`
- `suitability_component_value`
- `suitability_normalised_value`
- `suitability_score`
- `suitability_value`
- `suitability_weight`
- `suitability_weighted_value`
- `surface`
- `surface_adjustment`
- `surface_context_eligibility`
- `surface_identity_invalid`
- `surface_registry`
- `surface_registry_audit`
- `surface_suitability_value`
- `suspicious_lightweight_boost_flag`
- `suspicious_lightweight_boosts`
- `suspicious_overadjustment_races`
- `suspicious_weight_jump`
- `suspicious_weight_jump_count`
- `target_rows_with_prior_rating`
- `target_rows_with_weight`
- `temporal_status`
- `temporally_eligible_ratings`
- `three_components_per_entry`
- `three_day_race_fields`
- `three_day_race_list`
- `tie_status`
- `tied_epi_entry_count`
- `time`
- `time_delta_seconds`
- `time_difference_seconds`
- `timestamp`
- `timestamp_before_race_time`
- `timestamp_columns`
- `timestamp_dt`
- `timestamp_duplicate_in_history`
- `timestamp_duplicate_issue_count`
- `timestamp_present_in_dedupe_summary`
- `timestamp_utc`
- `timestamp_value`
- `timestamps`
- `timestamps_with_non_87_row_count`
- `today_rating`
- `tolerance_date_rate_pct`
- `top_100_largest_contexts`
- `top_100_single_runner_contexts_current_grouping`
- `top_epi_tie_status`
- `total_component_weight`
- `total_context_adjustment`
- `total_current_contexts`
- `total_top_context_signals`
- `trace_rows`
- `track`
- `trackCondition`
- `trackDistance`
- `trackKey`
- `trackName`
- `trackRating`
- `track_adjustment`
- `track_code`
- `track_combo`
- `track_condition`
- `track_condition_adjustment`
- `track_condition_eligibility`
- `track_condition_group`
- `track_condition_suitability_value`
- `track_configuration`
- `track_configuration_adjustment`
- `track_configuration_eligibility`
- `track_configuration_suitability_value`
- `track_context_eligibility`
- `track_field`
- `track_group`
- `track_id`
- `track_intelligence_comment_v2_1`
- `track_key`
- `track_key_v1`
- `track_name`
- `track_profile`
- `track_profile_1`
- `track_profile_2`
- `track_profile_count`
- `track_rating`
- `track_rating_number`
- `track_suitability_value`
- `tracks`
- `trainer`
- `trainerName`
- `trainer_adjustment`
- `trainer_base_place_pct`
- `trainer_base_starts`
- `trainer_base_win_pct`
- `trainer_best_context`
- `trainer_best_style`
- `trainer_best_style_ae`
- `trainer_best_style_roi`
- `trainer_best_style_win_pct`
- `trainer_canonical`
- `trainer_context`
- `trainer_context_rows`
- `trainer_context_score`
- `trainer_graphql`
- `trainer_jockey_canonical`
- `trainer_key`
- `trainer_recent_100_win_pct`
- `trainer_recent_25_win_pct`
- `trainer_recent_50_win_pct`
- `trainer_rows`
- `unexpected_context_rows`
- `unique_epi_entry_count`
- `unique_horses`
- `unique_jockeys`
- `unique_races`
- `unique_runners`
- `unique_tracks`
- `unique_trainer_jockey_combos`
- `unique_trainers`
- `universal_runner_key`
- `updated_at`
- `v5_contextual_action`
- `v5_contextual_fair_price`
- `v5_contextual_overlay_pct`
- `v5_contextual_probability`
- `v5_contextual_reason`
- `v6_1_rating_rows`
- `v6_distance`
- `v6_horse`
- `v6_race_date`
- `v6_track`
- `value_candidates`
- `value_classification`
- `weight`
- `weightKg`
- `weight_adjustment`
- `weight_and_rating_rows`
- `weight_band`
- `weight_band_research_v1`
- `weight_carried`
- `weight_carried_adjustment`
- `weight_context_top_pick_better`
- `weight_context_top_pick_better_count`
- `weight_coverage_pct`
- `weight_delta_to_race_avg_kg`
- `weight_delta_vs_avg_kg`
- `weight_field`
- `weight_join_coverage_pct`
- `weight_quality`
- `weight_rank_in_joined_race`
- `weight_relative_band_research_v1`
- `weight_source`
- `weight_source_barrier`
- `weight_source_class`
- `weight_source_distance`
- `weight_source_file`
- `weight_source_finish`
- `weight_source_jockey`
- `weight_source_margin`
- `weight_source_race_date`
- `weight_source_race_no`
- `weight_source_rows`
- `weight_source_sp`
- `weight_source_track`
- `weight_source_trainer`
- `weight_source_weight_raw`
- `weight_suitability_value`
- `weighted`
- `weighted_component_total`
- `weighted_component_value`
- `winner_horse_name`
- `winner_race_time_seconds`
- `with_context_profile`
- `within_jockey_place_lift_pct`
- `within_jockey_win_lift_pct`
- `within_trainer_place_lift_pct`
- `within_trainer_win_lift_pct`
- `without_context_profile`

## Required Decision

Use this evidence to patch the active snapshot/context builder to consume the current governed race-entry schema.

Do not add fake columns to the canonical race-entry fact.

Do not weaken horse-history or EPI eligibility rules.
