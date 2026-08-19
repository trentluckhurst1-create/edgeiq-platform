# EDGEiQ Historical Horse Observation Eligibility V1

Status: `BLOCKED`

Historical HPR-NORM-A-v1 application permitted: `NO`

## Evidence

- HPR-NORM-A-v1 effective_from_date is `2026-07-20` in the parameter source and parameter fact.
- The canonical normalisation builder selects parameters by performance `race_date` effective window.
- Pre-cutoff rows are rejected with `NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE`.
- The temporal authority document explicitly states historical application authorised: `NO`.

## Conclusion

The restriction is an explicit governed temporal rule, not an accidental orchestration omission.
