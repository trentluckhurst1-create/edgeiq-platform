# EDGEiQ Context Parameter Methodology Policy V1

- policy_id: EPI-CONTEXT-PARAM-A-v1
- target_definition: rating_base_value
- unit: HPR-NORM-A normalised rating units
- baseline_construction: mean of the horse's latest 5 governed prior performances before the target race
- residual_definition: observed canonical performance minus strictly pre-race horse baseline
- positive_residual_direction: better than pre-race baseline
- permitted_context_dimensions: ['track', 'track_configuration', 'distance_band', 'race_class_family', 'track_condition_group', 'surface', 'rail_group', 'barrier_band', 'weight_band', 'field_size_band']
- estimation_method: additive residualised context model
- regularisation: RIDGE_REGULARISED_GROUP_MEAN_RESIDUAL
- regularisation_selection: time-ordered validation over fixed lambda grid
- evidence_floors: {'main_effect': {'observations': 100, 'races': 25, 'horses': 40, 'date_span_days': 365}, 'two_dimensional_interaction': {'observations': 150, 'races': 40, 'horses': 60, 'date_span_days': 365}, 'three_or_more_dimensional_interaction': {'observations': 250, 'races': 60, 'horses': 100, 'date_span_days': 730}}
- temporal_validation: expanding-window yearly folds, no race appears in both training and validation within a fold
- approval_rules: must meet evidence floors, improve out-of-sample MAE, not worsen bias, and maintain fold coefficient direction
- overlap_handling: highest validated interaction supersedes lower-order component effects; unvalidated overlaps fail closed
- effective_date: 2026-07-30
- rebuild_frequency: manual governed rebuild until an operations cadence is separately approved
- fail_closed_behaviour: CONTEXT_PARAMETER_UNAVAILABLE where no approved parameter exists
