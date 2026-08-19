# EDGEiQ Performance Intelligence
## Phase 0.4 Migration Map

No production data is changed by this specification.

| Priority | Domain | Source | Classification | Target | Required actions |
|---:|---|---|---|---|---|
| 1 | benchmark_definitions | `public/data/edgeiq_standard_times_v1.csv` | LEGACY_BENCHMARK_SEED | benchmark_definition | Add benchmark_id, hierarchy level, eligibility counts, exclusions, confidence, version, validity window and warehouse snapshot. |
| 1 | length_conversion | `scripts/build_edgeiq_standardised_sectionals_v1.py` | LEGACY_FIXED_CONVERSION | length_conversion_definition | Preserve as conversion version LEGACY_FIXED_0_17_V1; do not silently reuse as permanent universal conversion; formally test contextual alternatives. |
| 1 | performance_ratings | `public/data/edgeiq_historical_performance_rating_v5_1.csv` | REUSABLE_RESEARCH_OUTPUT | performance_derivation | Create performance_id links; distinguish source evidence from rating outputs; preserve formula and engine version. |
| 1 | raw_results | `public/data/edgeiq_historical_results_warehouse_v2_graphql.csv` | REUSABLE_AFTER_IDENTITY_REPAIR | source_evidence + performance_evidence | Resolve 89 duplicate performance keys; preserve monthly GraphQL files as source evidence; add immutable evidence versions. |
| 1 | runner_identity | `public/data/edgeiq_runner_entity_graph_v1.csv` | REUSABLE_ENTITY_GRAPH | canonical_horse + horse_alias + provider_horse_identifier | Audit columns and graph semantics; define permanent horse_id; retain aliases and provider IDs separately. |
| 1 | sectional_identity | `public/data/edgeiq_sectional_identity_engine_v3.csv` | REUSABLE_IDENTITY_EVIDENCE | identity_resolution_event | Do not treat rows as unique performances; preserve multiple candidate rows and resolution evidence; remove duplicated-performance assumption. |
| 1 | sectional_source | `public/data/racingcom_sectional_warehouse_v2.csv` | STRONG_RAW_SECTIONAL_CANDIDATE | performance_sectional_evidence | Attach canonical race_id and horse_id; preserve timing provider; formalise sectional quality states. |
| 2 | lengths_per_point | `public/data/edgeiq_lengths_per_point_engine_v1.csv` | RESEARCH_CANDIDATE | length_conversion_definition | Trace creator logic and inputs; compare against fixed 0.17 methodology; validate units and sign convention. |
| 2 | race_strength | `public/data/edgeiq_race_strength_v1.csv` | LEGACY_DERIVED_BENCHMARK | race_derivation | Trace source inputs; add engine version and derivation run; separate retrospective and pre-race strength. |
| 2 | results_consolidation | `public/data/edgeiq_results_master_v1.csv` | REUSABLE_AFTER_SCHEMA_MIGRATION | performance_evidence | Identify missing horse field mapping; create horse_id and performance_id; separate source evidence from derived fields. |
| 2 | standardised_sectionals | `public/data/edgeiq_standardised_sectionals_v1.csv` | DERIVED_ASSET_REQUIRES_DECOMPOSITION | performance_sectional_derivation | Do not use as raw sectional warehouse; reconstruct performance identities; add engine and conversion versions; separate raw seconds from derived lengths. |
| 3 | canonical_truth_experiment | `public/data/edgeiq_canonical_results_truth_v1.csv` | REUSABLE_LOGIC_NOT_CANONICAL_DATA | identity resolution and conflict-resolution rules | Extract rules; do not treat limited 2025-2026 output as global canonical warehouse. |
| 3 | runner_history | `public/data/edgeiq_runner_history_detail_v1.csv` | REUSABLE_APPLICATION_VIEW | query view generated from canonical warehouse | Do not promote as warehouse; rebuild as a query product over canonical performance records. |

## Critical blockers

- No current global immutable `performance_id`.
- Results assets contain overlapping and differently structured truths.
- The largest consolidated result asset lacks a safely detected horse identity.
- The GraphQL historical warehouse contains 89 duplicate performance keys.
- Standardised sectionals mix derived benchmark output with incomplete identity.
- Existing benchmark definitions lack complete versioning and validity governance.
- Existing length conversion uses a fixed 0.17 seconds-per-length constant.
- No audited sign-convention implementation was located in the conversion scripts.
- Several historical scripts currently fail Python syntax parsing and must not be executed or promoted.
