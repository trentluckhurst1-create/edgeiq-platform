# EDGEiQ Length Conversion Method V2

Method identifier: `EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2`

Method status: `GOVERNED_APPROVED`

## Approved Surface Groups

EDGEiQ recognises two governed analytical surface groups for Performance Intelligence:

- `TURF`
- `AUSTRALIAN_SYNTHETIC`

All Australian synthetic thoroughbred tracks are treated as one canonical EDGEiQ analytical surface: `AUSTRALIAN_SYNTHETIC`.

Technology-specific labels such as Polytrack, Tapeta, Pro-Ride, Fibresand, or other manufacturer names are not calculation dimensions in V2. They may be retained as source evidence, but they must not create separate conversion parameters.

V1 Turf methodology remains preserved as historical governance in `EDGEIQ_LENGTH_CONVERSION_METHOD_V1.md` and `edgeiq_length_conversion_parameter_source_v1.csv`.

## Turf Mapping

| Surface | Condition number | Condition group | Lengths per second | Seconds per length |
| --- | ---: | --- | ---: | ---: |
| TURF | 1-2 | FIRM | 6.0 | 0.166666667 |
| TURF | 3-4 | GOOD | 6.0 | 0.166666667 |
| TURF | 5-7 | SOFT | 5.0 | 0.200000000 |
| TURF | 8-10 | HEAVY | 5.0 | 0.200000000 |

## Australian Synthetic Mapping

| Surface | Condition number | Condition group | Lengths per second | Seconds per length |
| --- | --- | --- | ---: | ---: |
| AUSTRALIAN_SYNTHETIC | not required | STANDARD_SYNTHETIC | 6.0 | 0.166666667 |

Australian Synthetic does not require a Turf condition number.

## Formula

`seconds_per_length = 1 / lengths_per_second`

`time_difference_seconds = standard_elapsed_seconds - actual_elapsed_seconds`

`lengths_vs_standard = time_difference_seconds * lengths_per_second`

## Sign Convention

- Positive means faster than Standard Time.
- Zero means equal to Standard Time.
- Negative means slower than Standard Time.

Downstream consumers must not reverse this convention.

## Precision And Rounding

Calculations use deterministic Decimal arithmetic where practical. CSV outputs may store `seconds_per_length` to nine decimal places and performance values to six decimal places.

## Null Behaviour

`TURF` rows require a valid condition number from 1 to 10. Missing Turf condition rows are blocked with `BLOCKED_MISSING_TURF_CONDITION`.

`AUSTRALIAN_SYNTHETIC` rows do not require a condition number. Irrelevant source condition text is ignored for the conversion parameter selection.

## Unsupported Behaviour

Unknown, ambiguous, non-Australian synthetic, dirt, or blank surfaces are blocked rather than inferred. Supported blocked statuses are:

- `BLOCKED_MISSING_TURF_CONDITION`
- `BLOCKED_UNSUPPORTED_SURFACE`
- `BLOCKED_AMBIGUOUS_SURFACE`

## Versioning

V2 supersedes V1 as the active production contract for Performance Intelligence length conversion. V1 remains retained as the Turf-only historical governance baseline.

## Provenance Classification

This method is an `EDGEIQ_GOVERNED_ANALYTICAL_CONVENTION`.

The Australian Synthetic mapping is an `EDGEIQ_GOVERNED_AUSTRALIAN_ANALYTICAL_CONVENTION`. It is not represented as an official Racing Australia, Racing Victoria, or stewarding margin rule.

## Consumer Expectations

Engines calculate. React displays. Consumers must preserve:

- source surface evidence;
- canonical surface group;
- conversion method version;
- track condition group;
- lengths per second;
- seconds per length;
- sign convention;
- blocked reason where calculation is not governed.
