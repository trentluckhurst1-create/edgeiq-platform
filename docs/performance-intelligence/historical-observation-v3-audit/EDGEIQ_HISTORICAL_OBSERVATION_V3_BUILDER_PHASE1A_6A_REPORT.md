# EDGEIQ Historical Observation V3 Builder — Phase 1A.6A Audit

**Status:** `EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_AUDIT_V1_FAIL`

**Decision:** `REPLACE`

## Scope

This was an inspection-only audit.

- No warehouse was rebuilt.
- No candidate was promoted.
- No existing V2 or V3 file was modified.
- No recursive repository scan was performed.
- The existing large CSV outputs were not processed.
- Only the candidate header was inspected.

## Decision rationale

The existing builder's source-admission architecture is broad and does not enforce the locked consolidated GraphQL authority. Because source authority defines the warehouse population, this is a foundational divergence rather than a cosmetic defect.

## Existing builder

- Builder: `scripts/rebuild_edgeiq_historical_observation_warehouse_v3.py`
- Source-summary rows inspected: 277
- Recursive source discovery detected: True
- Explicit consolidated authority allow-list detected: False

## Source classification

```json
{
  "REJECT_BACKUP": 2,
  "REJECT_SECTIONAL": 46,
  "REJECT_SPEED": 146,
  "UNAPPROVED_GRAPHQL_OR_UNKNOWN": 2,
  "UNAPPROVED_RACINGCOM_OR_UNKNOWN": 81
}
```

## Governance matrix

| Check | Requirement | Result | Severity |
|---|---|---:|---:|
| A01 | Builder must exist and remain inspectable without execution. | **PASS** | CRITICAL |
| A02 | Source admission must use the approved consolidated GraphQL authority only. | **FAIL** | CRITICAL |
| A03 | Monthly, legacy, speed, sectional, live and checkpoint sources must be explicitly excluded. | **FAIL** | CRITICAL |
| A04 | Previously admitted sources must conform to the approved source authority. | **FAIL** | CRITICAL |
| A05 | Every admitted observation must preserve row-level source and identity lineage. | **PASS** | HIGH |
| A06 | Identity resolution must remain deterministic and prohibit fuzzy matching. | **PASS** | HIGH |
| A07 | Observation identifiers must be generated deterministically. | **PASS** | HIGH |
| A08 | Physical population must equal 879,784 rows. | **NOT_VERIFIED** | CRITICAL |
| A09 | Unique raw observation identities must equal 879,695. | **NOT_VERIFIED** | CRITICAL |
| A10 | The governed duplicate excess must remain 89. | **NOT_VERIFIED** | CRITICAL |
| A11 | Observation construction must remain separate from downstream performance enrichment. | **PASS** | HIGH |
| A12 | The builder must verify byte-identical deterministic rebuilds. | **PARTIAL** | HIGH |

## Population contract

- Expected physical rows: **879,784**
- Expected unique raw identities: **879,695**
- Expected duplicate excess: **89**

The existing audit was inspected for these values. No large
warehouse file was recounted during this phase.

## Deliverables

- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.json`
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.md`
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_SOURCE_ADMISSION_MATRIX.csv`
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_GOVERNANCE_MATRIX.csv`
- `docs/performance-intelligence/historical-observation-v3-audit/EDGEIQ_HISTORICAL_OBSERVATION_V3_RECOMMENDATION.md`
