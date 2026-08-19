# EDGEiQ Seconds Per Length Method Decision V1

## Status

`NO_GOVERNED_METHOD_EXISTS`

## Selected Method

None. Lengths v Standard remains blocked.

## Formula

No formula selected. The active EDGEiQ convention expects `lengths_versus_standard = -time_delta_seconds / seconds_per_length`, but no governed `seconds_per_length` parameter is available.

## Units

Seconds per length. Length unit is not recoverable from current governed evidence.

## Parameter Source

`config/performance-intelligence/edgeiq_length_conversion_parameter_source_v1.csv` is expected by the active builder, but it is absent. `public/data/edgeiq_length_conversion_parameter_fact_v1.csv` has zero rows.

## Scope

The active builder expects `DISTANCE_EXACT` conversion parameters.

## Distance Treatment

Blocked. Distance-exact parameter rows are absent.

## Speed Treatment

Blocked. A speed-derived method would require a governed physical horse-length distance parameter, which is absent.

## Surface And Condition Treatment

No governed dependency found.

## Rounding And Null Handling

Null or missing parameters block calculation. No default constant is applied.

## Evidence Strength

`BLOCKED_BY_MISSING_METHODOLOGY_EVIDENCE`

## Known Limitations

Standard Times can be built, but Lengths v Standard, sectional performance and downstream EPI cannot be rebuilt without a governed conversion parameter or recoverable methodology.

## Affected Downstream Engines

Lengths v Standard, runner sectional performance, EPI, Performance Intelligence consumers.
