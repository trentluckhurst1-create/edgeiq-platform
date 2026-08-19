# EDGEIQ Historical Observation V3 Raw Identity Semantics Audit

**Status:** `EDGEIQ_HISTORICAL_OBSERVATION_V3_RAW_IDENTITY_SEMANTICS_PHASE1A_6B_1A_V1_FAIL`

**Decision:** `MULTIPLE_IDENTITY_EXPRESSIONS_MATCH`

## Decision rationale

Multiple complete identity expressions reproduce the governed population. The canonical expression must be distinguished by upstream source semantics.

## Raw physical source

`docs/performance-intelligence/warehouse/raw/eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e/canonical_performance_evidence.csv`

## Raw schema

1. `performance_id`
2. `race_id`
3. `meeting_id`
4. `horse_id`
5. `source_evidence_id`
6. `source_row_number`
7. `provider_race_id`
8. `provider_runner_id`
9. `race_date`
10. `state`
11. `track`
12. `race_number`
13. `horse_name`
14. `identity_method`
15. `identity_quality_state`
16. `identity_version`
17. `evidence_version`
18. `generated_at`
19. `legacy_performance_id`
20. `performance_natural_key_version`
21. `rekeyed_at`

## Identity expression testing

| Identity expression | Complete | Unique | Duplicate excess | Match |
|---|---:|---:|---:|---:|
| `race_id + horse_id` | 879,784 | 879,695 | 89 | True |
| `race_id + provider_runner_id` | 879,784 | 879,695 | 89 | True |
| `race_id + race_number` | 879,784 | 71,025 | 808,759 | False |
| `race_id + horse_name` | 879,784 | 879,693 | 91 | False |
| `race_id + horse_id + race_number` | 879,784 | 879,784 | 0 | False |
| `race_id + horse_name + race_number` | 879,784 | 879,781 | 3 | False |

## Governance evidence

- Asset catalogue registration: **True**
- Materialisation evidence: **True**
- Raw lineage fields: `source_row_number`
- Corrected derived fields: `performance_fact_id | benchmark_eligible | quality_state`
- Non-circular raw references: **42**

## Safety

- No warehouse was written.
- Existing V2 was not modified.
- The rejected untracked V3 implementation was not modified.

## Deliverables

- `docs/performance-intelligence/historical-observation-v3-raw-identity-semantics/EDGEIQ_HISTORICAL_OBSERVATION_V3_RAW_IDENTITY_SEMANTICS_REPORT.json`
- `docs/performance-intelligence/historical-observation-v3-raw-identity-semantics/EDGEIQ_HISTORICAL_OBSERVATION_V3_RAW_IDENTITY_SEMANTICS_REPORT.md`
- `docs/performance-intelligence/historical-observation-v3-raw-identity-semantics/EDGEIQ_HISTORICAL_OBSERVATION_V3_RAW_IDENTITY_EXPRESSION_MATRIX.csv`
- `docs/performance-intelligence/historical-observation-v3-raw-identity-semantics/EDGEIQ_HISTORICAL_OBSERVATION_V3_NON_CIRCULAR_LINEAGE_MATRIX.csv`
- `docs/performance-intelligence/historical-observation-v3-raw-identity-semantics/edgeiq_historical_observation_v3_raw_identity_authority_contract.json`
