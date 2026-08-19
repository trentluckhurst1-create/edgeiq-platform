# EDGEiQ Timing Canonical Promotion Downstream Acceptance V1

Generated: 2026-07-28T22:42:49Z

## Canonical Promotion
Status: PASS

## Row Counts
- timing_warehouse: 70308
- standard_times: 695
- race_time_deltas: 54978
- lengths_versus_standard: 52414
- lengths_versus_standard_rejections: 2564
- performance_base: 52414
- performance_normalisation: 0
- performance_normalisation_rejections: 52414
- performance_rating_base: 0
- horse_observations: 0
- horse_aggregates: 0
- horse_ratings: 0
- race_entry_snapshots: 0
- race_entry_context: 0
- race_entry_context_adjusted: 0
- projected_performance: 0
- epi: 0

## Performance Base Date Partition
- cutoff: 2026-07-20
- before_2026_07_20: 52414
- on_or_after_2026_07_20: 0
- bad_dates: 0
- min_date: 2000-08-02
- max_date: 2026-06-21
- hpr_norm_a_v1_satisfied_rows: 0
- legitimate_normalisation_action: NO_POST_CUTOFF_ROWS_AVAILABLE
- normalisation_rejection_reasons: {'NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE': 52414}

## Current Victoria Coverage
- meetings: 1
- races: 7
- runners: 108
- historical_runners: 0
- horse_ratings: 0
- snapshots: 0
- performance_metrics: 52414
- epi_coverage: 0
- runtime_coverage: 0
- missing_coverage: NORMALISATION_BLOCKED_BY_HPR_NORM_A_V1_CUTOFF_NO_POST_2026_07_20_PERFORMANCE_BASE_ROWS

## Three-Race Reconciliation
- EIQ_RACE_477B30F765AAC875: 2023-05-04 WARRNAMBOOL R7.0 5500m, cause=None
- EIQ_RACE_B5B4A24EC160FD5B: 2007-05-03 WARRNAMBOOL R7.0 5500m, cause=None
- EIQ_RACE_C407130DC4B7DC56: 2024-10-14 BET365 SEYMOUR R5.0 1000m, cause=None

## Blocker
No performance-base rows are on or after 2026-07-20, so HPR-NORM-A-v1 cannot legitimately normalise any recovered historical rows without backdating the parameter. This is a governed data-window blocker, not repository architecture.
