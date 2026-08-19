# EDGEIQ Historical Observation V3 Raw Authority Semantic Lock

**Status:** `EDGEIQ_HISTORICAL_OBSERVATION_V3_RAW_AUTHORITY_SEMANTIC_LOCK_PHASE1A_6B_1B_V1_PASS`

**Decision:** `LOCK_CANONICAL_PERFORMANCE_EVIDENCE_AS_PHYSICAL_AUTHORITY`

**Selected physical authority:** `docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/canonical_performance_evidence.csv`

**Selected raw identity:** `race_id + provider_runner_id`

## Decision rationale

The canonical performance evidence dataset is the registered and materialised raw warehouse asset. Its provider-side identity expression `race_id + provider_runner_id` exactly reproduces the governed 879,695 unique raw identities and duplicate excess of 89. `horse_id` is retained as EDGEIQ's canonical resolved horse identity and is not substituted for the provider raw key.

## Identity semantics

- `provider_runner_id`: upstream provider runner identity.
- `horse_id`: EDGEIQ canonical resolved horse identity.
- The provider raw key and canonical key are numerically population-equivalent in this snapshot, but they are not semantically interchangeable.

## Governed population

- Physical rows: **879,784**
- Unique raw identities: **879,695**
- Duplicate excess: **89**

## Governance checks

| Check | Result | Detail |
|---|---:|---|
| `RAW_SOURCE_EXISTS` | **PASS** | docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/canonical_performance_evidence.csv |
| `RAW_SCHEMA_COMPLETE` | **PASS** | required=11; present=11 |
| `RAW_PHYSICAL_POPULATION` | **PASS** | actual=879784; expected=879784 |
| `PROVIDER_RAW_KEY_CONTRACT` | **PASS** | race_id + provider_runner_id; unique=879695; duplicates=89 |
| `PROVIDER_IDENTITY_COMPLETE` | **PASS** | blank_provider_runner_id=0 |
| `CANONICAL_HORSE_ID_COMPLETE` | **PASS** | blank_horse_id=0 |
| `CANONICAL_KEY_NUMERIC_EQUIVALENCE` | **PASS** | race_id + horse_id reproduces population but is classified as canonical rather than raw |
| `PROVIDER_CANONICAL_FIELD_DISTINCTION` | **PASS** | provider_runner_id and horse_id are stored as separate governed fields |
| `IDENTITY_PROCESSING_METADATA` | **PASS** | identity_method, identity_version and performance_natural_key_version populated |
| `RAW_ASSET_REGISTRATION` | **PASS** | docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/asset_catalog.csv |
| `RAW_MATERIALISATION` | **PASS** | docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/materialisation_checks.csv |
| `CORRECTED_FACTS_DOWNSTREAM_SCHEMA` | **PASS** | benchmark_eligible, performance_fact_id, quality_state |

## Safety

- No warehouse was written.
- Existing V2 was not modified.
- The rejected untracked V3 implementation was not modified.

## Build authority

Phase 1A.6B replacement warehouse construction is **authorised**.

## Deliverables

- `docs/performance-intelligence/historical-observation-v3-raw-authority-lock/EDGEIQ_HISTORICAL_OBSERVATION_V3_RAW_AUTHORITY_SEMANTIC_LOCK_REPORT.json`
- `docs/performance-intelligence/historical-observation-v3-raw-authority-lock/EDGEIQ_HISTORICAL_OBSERVATION_V3_RAW_AUTHORITY_SEMANTIC_LOCK_REPORT.md`
- `docs/performance-intelligence/historical-observation-v3-raw-authority-lock/EDGEIQ_HISTORICAL_OBSERVATION_V3_RAW_AUTHORITY_SEMANTIC_EVIDENCE.csv`
- `docs/performance-intelligence/historical-observation-v3-raw-authority-lock/edgeiq_historical_observation_v3_physical_authority_contract_v1.json`
