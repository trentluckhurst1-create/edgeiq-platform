# EDGEIQ Performance Intelligence

## Phase 1A.5 Historical Observation Correction Specification V1

**Overall status: PASS**

## Authoritative Result Source

`public/data/edgeiq_historical_results_warehouse_v2_graphql.csv`

- Physical rows: 879784
- Unique `race_id + runner_id` keys: 879695
- Duplicate raw-key groups: 89
- Duplicate excess rows: 89
- Missing raw identities: 0
- Source SHA256: `13f17e2ae21802aef5017a9a09cbb9ec572c9fda4c8fa8f85da27231e8828974`

## Governing Identity

```text
raw_natural_key = race_id + runner_id
row_identity = SHA256(authority_version | race_id | runner_id | collision_discriminator)
```

Every physical authoritative source row must be retained. Duplicate natural keys must receive deterministic collision discriminators and must never be silently discarded.

## Source Admission Policy

| Source class | Decision | Creates rows | Enrichment |
|---|---|---:|---:|
| `CONSOLIDATED_GRAPHQL_RESULTS` | `ADMIT_AS_RESULT_AUTHORITY` | True | True |
| `MONTHLY_GRAPHQL_RESULT_FILES` | `EXCLUDE_DUPLICATE_SOURCE` | False | False |
| `LEGACY_GRAPHQL_MASTER_FILES` | `EXCLUDE_DUPLICATE_SOURCE` | False | False |
| `SPEED_AND_SECTIONAL_FACTS` | `ENRICHMENT_ONLY` | False | True |
| `LIVE_AND_UPCOMING_PRODUCT_FEEDS` | `EXCLUDE_FROM_HISTORICAL_FACT` | False | False |
| `REJECTED_RECORDS` | `EXCLUDE_REJECTED` | False | False |
| `CHECKPOINT_AND_BACKUP_FILES` | `EXCLUDE_NONPRODUCTION_ARTEFACT` | False | False |

## Acceptance Criteria

- `AUTHORITY_SOURCE_EXCLUSIVE`: Only consolidated GraphQL creates historical observation rows.
- `PHYSICAL_ROW_PRESERVATION`: 879784
- `UNIQUE_RAW_IDENTITY_COUNT`: 879695
- `DUPLICATE_GROUP_COUNT`: 89
- `DUPLICATE_EXCESS_ROW_COUNT`: 89
- `MISSING_RAW_IDENTITY`: 0
- `LIVE_SOURCE_ROWS_ADMITTED`: 0
- `MONTHLY_SOURCE_ROWS_ADMITTED`: 0
- `REJECTED_SOURCE_ROWS_ADMITTED`: 0
- `UNRESOLVED_ENRICHMENT_CREATES_ROWS`: 0
- `DETERMINISTIC_REBUILD_SHA`: Two consecutive builds produce identical output SHA256.

## Prohibited Behaviour

- Recursive discovery of arbitrary CSV files as historical observations.
- Admission of live or upcoming runner feeds into completed-run facts.
- Creation of observations from unresolved speed or sectional records.
- Silent deletion of duplicate source rows.
- Population expansion from checkpoint, backup or rejected files.
- Threshold reduction or fabricated identity resolution.

## Governance

- This unit changes no production builder.
- This unit changes no production dataset.
- This unit lowers no governed threshold.
- This unit fabricates no observation.
