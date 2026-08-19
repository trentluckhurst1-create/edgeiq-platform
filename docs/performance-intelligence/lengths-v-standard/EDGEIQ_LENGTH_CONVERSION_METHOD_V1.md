# EDGEiQ Length Conversion Method V1

## Method Identifier

`EDGEIQ_GOING_DEPENDENT_LENGTHS_PER_SECOND_V1`

## Method Type

`GOING_DEPENDENT_FLAT_RACING_RATING_LENGTH`

## Formula

`seconds_per_length = 1 / lengths_per_second`

`time_difference_seconds = standard_elapsed_seconds - actual_elapsed_seconds`

`lengths_vs_standard = time_difference_seconds * lengths_per_second`

## Sign Convention

Positive means faster than Standard Time. Zero means equal to Standard Time. Negative means slower than Standard Time.

## Scope

This method applies only to thoroughbred flat racing on Turf with known Australian track condition numbers from 1 to 10.

Unsupported surfaces, missing condition numbers, invalid condition numbers, jumps, synthetic, polytrack, tapeta, fibresand, dirt, and unmapped conditions must be blocked with `BLOCKED_UNSUPPORTED_LENGTH_CONVERSION_SCOPE`.

## Turf Condition Mapping

- Turf condition 1-2: FIRM, 6 lengths per second, 1/6 seconds per length.
- Turf condition 3-4: GOOD, 6 lengths per second, 1/6 seconds per length.
- Turf condition 5-7: SOFT, 5 lengths per second, 1/5 seconds per length.
- Turf condition 8-10: HEAVY, 5 lengths per second, 1/5 seconds per length.

## Precision

Calculations use deterministic decimal arithmetic. The configured decimal values are display and contract values; provider calculations use exact `1 / 6` and `1 / 5` precision.

## Rounding

Published numeric outputs use stable decimal formatting. Internal calculations must not depend on binary floating point rounding.

## Null Behaviour

Missing surface or track condition blocks conversion. No default value is applied.

## Unsupported Behaviour

Unsupported combinations return a blocked method status and a reason. Builders must not silently fall back.

## Provenance

This is an EDGEiQ governed analytical convention derived from authoritative flat-racing elapsed-time distance methodology. It must not be described as an official Australian stewarding, finishing-margin, or photo-finish rule.

## Distinctions

Official finishing margin: the official result margin reported by race authorities.

Physical horse length: a physical distance concept, not used directly in V1.

EDGEiQ rating length: a time-derived analytical rating unit used to express performance relative to Standard Time.

## Consumer Expectations

Consumers must treat `lengths_vs_standard` as a governed analytical performance unit. Positive is faster than standard, negative is slower than standard. React must display calculated values only; it must not calculate conversion.

## Versioning Policy

Any future support for synthetic, dirt, or surface-specific variants requires a new governed method version or explicit extension with audit evidence.

## Replaced Precondition

The previous unpopulated `DISTANCE_EXACT` parameter requirement is classified as `UNSUPPORTED_PRECONDITION_REPLACED_BY_APPROVED_METHOD_CONTRACT`.
