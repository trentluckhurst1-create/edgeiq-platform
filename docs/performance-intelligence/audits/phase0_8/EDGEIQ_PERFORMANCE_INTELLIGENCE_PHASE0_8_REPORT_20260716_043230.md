# EDGEiQ Performance Intelligence
## Phase 0.8 Sectional Link Validation and Residual Diagnosis

Generated UTC: `2026-07-15T18:33:22.413157+00:00`

## Link validation

- Linked rows checked: **126,640**
- Validated rows: **122,959**
- Validation rate: **97.0933%**
- Validation mismatches: **3,681**

## Canonical migration eligibility

- Strong deterministic rows eligible for migration review: **100,143**

## Residual unlinked evidence

- Unlinked or ambiguous rows diagnosed: **3,844**

| Reason | Rows |
|---|---:|
| DUPLICATE_OR_AMBIGUOUS_RESULT_EVIDENCE | 1 |
| HORSE_NOT_PRESENT_ON_DATE | 2246 |
| RESULT_DATE_NOT_PRESENT | 1596 |
| TRACK_ALIAS_OR_RESULT_VENUE_MISMATCH | 1 |

## Permanent rule

No horse alias, track alias, race-number correction or fuzzy match is automatically promoted from this diagnosis.

All residual rows remain preserved with their diagnostic reason.
