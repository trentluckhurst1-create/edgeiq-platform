# EDGEiQ Horse Performance Rating Row Funnel V1

FIRST ZERO-ROW STAGE: `required formula fields validated`

## Stage Funnel
- 1. `historical runner performances loaded`: input=168, accepted=168, rejected=0, first_rejection=``
- 2. `race identities validated`: input=168, accepted=168, rejected=0, first_rejection=``
- 3. `runner identities validated`: input=168, accepted=168, rejected=0, first_rejection=``
- 4. `Lengths v Standard joined`: input=168, accepted=168, rejected=0, first_rejection=``
- 5. `sectional performance joined`: input=168, accepted=24, rejected=144, first_rejection=``
- 6. `early speed joined`: input=168, accepted=24, rejected=144, first_rejection=``
- 7. `late speed joined`: input=168, accepted=24, rejected=144, first_rejection=``
- 8. `required formula fields validated`: input=168, accepted=0, rejected=168, first_rejection=`MISSING_FORMULA_INPUT`
- 9. `performance normalisation calculated`: input=168, accepted=0, rejected=168, first_rejection=`MISSING_FORMULA_INPUT`
- 10. `performance rating base calculated`: input=0, accepted=0, rejected=0, first_rejection=``
- 11. `historical horse identities joined`: input=0, accepted=0, rejected=0, first_rejection=``
- 12. `horse performance observations built`: input=0, accepted=0, rejected=0, first_rejection=``
- 13. `eligibility gates applied`: input=0, accepted=0, rejected=0, first_rejection=``
- 14. `horse performance aggregate calculated`: input=0, accepted=0, rejected=0, first_rejection=``
- 15. `rating calculated`: input=0, accepted=0, rejected=0, first_rejection=``
- 16. `output validation`: input=0, accepted=0, rejected=0, first_rejection=``

## Rejection Counts
- `BELOW_MINIMUM_OBSERVATIONS`: 0
- `DISTANCE_UNSUPPORTED`: 0
- `DUPLICATE_KEY`: 0
- `FORMULA_ERROR`: 0
- `INVALID_RACE_ID`: 0
- `INVALID_RUNNER_ID`: 0
- `MISSING_FORMULA_INPUT`: 168
- `NO_EARLY_SPEED`: 0
- `NO_HISTORICAL_RUNNER_PERFORMANCE`: 0
- `NO_LATE_SPEED`: 0
- `NO_LENGTHS_V_STANDARD`: 0
- `NO_SECTIONAL_PERFORMANCE`: 0
- `SURFACE_UNSUPPORTED`: 0
- `UNKNOWN`: 0

## Critical Finding
The first zero-row stage is `required formula fields validated`: 168 governed performance-intelligence base rows exist, but `edgeiq_performance_normalisation_parameter_fact_v1.csv` has zero governed parameter rows.
Because the normalisation parameter table is header-only, `edgeiq_performance_normalisation_fact_v1.csv`, `edgeiq_performance_rating_base_fact_v1.csv`, horse observations, horse aggregates, horse ratings, and projected performance all remain header-only.
This is a formula-input dependency gap, not a projected-performance or EPI formula defect.
