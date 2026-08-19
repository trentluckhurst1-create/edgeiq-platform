# EDGEIQ Performance Intelligence

## Phase 1A.3 Population, Duplicate and Builder Semantics V1

- Program ID: `EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1A_3_POPULATION_DUPLICATE_BUILDER_SEMANTICS_V1`
- Version: `1.0.0`
- Generated UTC: `2026-07-27T03:24:57+00:00`
- Overall status: **PARTIAL**

## Dataset Population Profiles

| Target | Rows | Fields | Key | Unique Keys | Duplicate Rows | Source Values |
|---|---:|---:|---|---:|---:|---:|
| `PERFORMANCE_WAREHOUSE_V1` | 879784 | 32 | RACE_ID_PLUS_HORSE_ID | 879781 | 3 | 0 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | 879784 | 51 | NO_DEFENSIBLE_RUNNER_KEY | None | None | 0 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | 879784 | 52 | RACE_ID_PLUS_HORSE_ID | 879693 | 91 | 0 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | 879784 | 53 | RACE_ID_PLUS_HORSE_ID | 879693 | 91 | 264 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | 1772640 | 37 | RACE_ID_PLUS_HORSE_ID | 1772462 | 178 | 2 |
| `EPI_PERFORMANCE_FACT_V1` | 533387 | 26 | RACE_ID_PLUS_HORSE_ID | 533387 | 0 | 0 |

## Comparable Population Overlap

| Left | Right | Intersection | Left Only | Right Only | Jaccard |
|---|---|---:|---:|---:|---:|
| `PERFORMANCE_WAREHOUSE_V1` | `CANONICAL_PERFORMANCE_FACTS_V0_2` | 0 | 879781 | 879693 | 0.0 |
| `PERFORMANCE_WAREHOUSE_V1` | `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | 0 | 879781 | 879693 | 0.0 |
| `PERFORMANCE_WAREHOUSE_V1` | `HISTORICAL_RUN_OBSERVATION_FACT_V2` | 0 | 879781 | 1772462 | 0.0 |
| `PERFORMANCE_WAREHOUSE_V1` | `EPI_PERFORMANCE_FACT_V1` | 533387 | 346394 | 0 | 0.60627247 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | 879693 | 0 | 0 | 1.0 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | `HISTORICAL_RUN_OBSERVATION_FACT_V2` | 0 | 879693 | 1772462 | 0.0 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | `EPI_PERFORMANCE_FACT_V1` | 0 | 879693 | 533387 | 0.0 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | `HISTORICAL_RUN_OBSERVATION_FACT_V2` | 0 | 879693 | 1772462 | 0.0 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | `EPI_PERFORMANCE_FACT_V1` | 0 | 879693 | 533387 | 0.0 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | `EPI_PERFORMANCE_FACT_V1` | 0 | 1772462 | 533387 | 0.0 |

## Duplicate Evidence

- Duplicate groups exported: 359

## Builder Semantics

| Target | Builder | Exists | Syntax | CSV References |
|---|---|---|---|---:|
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | `scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase1_5b.py` | True | PASS | 6 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | `scripts/performance-intelligence/phase1_6_1/build_edgeiq_corrected_performance_facts_phase1_6_1.py` | True | PASS | 4 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | `scripts/performance-intelligence/phase1_6_1/apply_phase1_6_1_recovery_patch.py` | True | PASS | 3 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | `scripts/performance-intelligence/phase1_6_1/patch_phase1_6_1_corrected_builder.py` | True | PASS | 4 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | `scripts/build_edgeiq_historical_results_warehouse_v2_graphql.py` | True | PASS | 3 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | `scripts/audit_edgeiq_historical_results_warehouse_v2_graphql_quality.py` | True | PASS | 3 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | `scripts/build_edgeiq_historical_run_observation_fact_v2.py` | True | PASS | 11 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | `scripts/create_edgeiq_historical_run_observation_fact_v2.py` | False | UNAVAILABLE | 0 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | `scripts/audit_edgeiq_historical_run_observation_fact_v2.py` | False | UNAVAILABLE | 0 |
| `PERFORMANCE_WAREHOUSE_V1` | `scripts/performance-intelligence/build_edgeiq_performance_fact_warehouse_phase1_6.py` | False | UNAVAILABLE | 0 |
| `PERFORMANCE_WAREHOUSE_V1` | `scripts/performance-intelligence/build_edgeiq_performance_intelligence_phase1_6.py` | False | UNAVAILABLE | 0 |

## Audit

- **PASS** — `target_dataset_availability`: all target datasets available
- **PARTIAL** — `defensible_runner_key_detection`: defensible_keys=5; targets=6
- **PASS** — `population_overlap_completed`: comparable_pairs=10
- **PASS** — `duplicate_evidence_exported`: duplicate_groups_exported=359
- **PARTIAL** — `builder_file_availability`: existing=7; missing=4
- **PASS** — `builder_syntax`: syntax_failures=0

## Governance

- Existing datasets were read only.
- No duplicate records were deleted.
- No source was declared canonical.
- No performance calculations were executed.
- Population overlap is based only on defensible, matching key types.
