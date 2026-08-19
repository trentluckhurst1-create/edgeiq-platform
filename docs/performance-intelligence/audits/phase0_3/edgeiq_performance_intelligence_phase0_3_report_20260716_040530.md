# EDGEiQ Performance Intelligence
## Phase 0.3 Canonical Candidate Validation

Generated UTC: `2026-07-15T18:05:30.191093+00:00`

No candidate is declared canonical solely from file size, row count, naming, or a prior PASS audit.

## results_warehouse

| Score | Classification | Path | Rows | Performances | Duplicates | Blockers |
|---:|---|---|---:|---:|---:|---|
| 68.0 | REUSABLE_AFTER_MIGRATION | `public/data/edgeiq_results_master_v1.csv` | 931245 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | MISSING_PERFORMANCE_KEYS |
| 54.0 | REQUIRES_VALIDATION | `public/data/edgeiq_historical_results_warehouse_v2_graphql.csv` | 879784 | 879695 | 89 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | DUPLICATE_PERFORMANCE_KEYS |
| 31.5 | LEGACY_OR_PARTIAL | `public/data/edgeiq_canonical_results_truth_v1.csv` | 47887 | 47887 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING |
| 30.0 | LEGACY_OR_PARTIAL | `public/data/edgeiq_racingcom_results_warehouse_full_v1.csv` | 164277 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |

## sectional_warehouse

| Score | Classification | Path | Rows | Performances | Duplicates | Blockers |
|---:|---|---|---:|---:|---:|---|
| 54.5 | REQUIRES_VALIDATION | `public/data/edgeiq_standardised_sectionals_v1.csv` | 1355824 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |
| 42.0 | REQUIRES_VALIDATION | `public/data/racingcom_sectional_warehouse_v2.csv` | 130484 | 130484 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING |
| 35.5 | LEGACY_OR_PARTIAL | `public/data/edgeiq_sectional_schema_v2.csv` | 184 | 184 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING |
| 23.5 | LEGACY_OR_PARTIAL | `public/data/edgeiq_trusted_sectional_universe_v2.csv` | 865 | 184 | 681 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING | DUPLICATE_PERFORMANCE_KEYS |

## benchmark_engine

| Score | Classification | Path | Rows | Performances | Duplicates | Blockers |
|---:|---|---|---:|---:|---:|---|
| 54.5 | REQUIRES_VALIDATION | `public/data/edgeiq_standardised_sectionals_v1.csv` | 1355824 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |
| 47.0 | REQUIRES_VALIDATION | `public/data/edgeiq_race_strength_history_v1.csv` | 3463 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | MISSING_PERFORMANCE_KEYS |
| 19.5 | LEGACY_OR_PARTIAL | `public/data/edgeiq_standard_times_v1.csv` | 5065 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |
| 18.0 | LEGACY_OR_PARTIAL | `public/data/edgeiq_race_strength_v1.csv` | 6064 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |

## identity_engine

| Score | Classification | Path | Rows | Performances | Duplicates | Blockers |
|---:|---|---|---:|---:|---:|---|
| 33.0 | LEGACY_OR_PARTIAL | `public/data/edgeiq_sectional_identity_engine_v3.csv` | 71404 | 2980 | 16094 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_ENGINE_VERSIONING | DUPLICATE_PERFORMANCE_KEYS | MISSING_PERFORMANCE_KEYS |
| 23.5 | LEGACY_OR_PARTIAL | `public/data/edgeiq_canonical_market_entity_graph_v1.csv` | 192 | 184 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |
| 16.0 | LEGACY_OR_PARTIAL | `public/data/edgeiq_temporal_identity_memory_v1.csv` | 241 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |
| 13.5 | LEGACY_OR_PARTIAL | `public/data/edgeiq_runner_entity_graph_v1.csv` | 73164 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |

## performance_ratings

| Score | Classification | Path | Rows | Performances | Duplicates | Blockers |
|---:|---|---|---:|---:|---:|---|
| 69.5 | REUSABLE_AFTER_MIGRATION | `public/data/edgeiq_runner_history_detail_v1.csv` | 2280 | 1669 | 0 | NO_EXPLICIT_PERFORMANCE_ID | MISSING_PERFORMANCE_KEYS |
| 47.0 | REQUIRES_VALIDATION | `public/data/edgeiq_race_strength_history_v1.csv` | 3463 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | MISSING_PERFORMANCE_KEYS |
| 28.5 | LEGACY_OR_PARTIAL | `public/data/edgeiq_historical_performance_rating_v5_1.csv` | 71327 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |
| 28.5 | LEGACY_OR_PARTIAL | `public/data/edgeiq_historical_performance_rating_v6_1_research.csv` | 71327 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |

## length_conversion

| Score | Classification | Path | Rows | Performances | Duplicates | Blockers |
|---:|---|---|---:|---:|---:|---|
| 54.5 | REQUIRES_VALIDATION | `public/data/edgeiq_standardised_sectionals_v1.csv` | 1355824 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |
| 19.5 | LEGACY_OR_PARTIAL | `public/data/edgeiq_lengths_per_point_engine_v1.csv` | 1301 | 0 | 0 | NO_EXPLICIT_PERFORMANCE_ID | NO_EXPLICIT_QUALITY_GOVERNANCE | NO_EXPLICIT_ENGINE_VERSIONING | MISSING_PERFORMANCE_KEYS |

## Required architectural response

Preserve reusable evidence and transformations, but migrate all selected assets into an immutable, versioned canonical performance model with explicit performance IDs, source lineage, quality states, engine versions and reproducible derivation records.
