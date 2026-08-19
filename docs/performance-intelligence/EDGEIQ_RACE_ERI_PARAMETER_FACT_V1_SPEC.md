# EDGEIQ Race ERI Parameter Fact V1

## Status

Governed deterministic warehouse parameter fact.

## Purpose

Race ERI Parameter Fact V1 defines the authorised methodology used by the
future Race ERI Fact V1.

It does not calculate ERI values.

It publishes the governed rules that an ERI engine must follow.

## ERI meaning

ERI is the EDGEiQ Race Index.

ERI represents the governed projected strength of the complete eligible field
for a race.

ERI is a race-level measure.

It is not a horse rating.

It must never modify any runner's projected-performance value.

## Architecture

Race Entry Projected Performance Fact V1  
→ Race ERI Parameter Fact V1  
→ Race ERI Fact V1  
→ Future EPI Component Fact V1  
→ Future Final EPI Fact V1

## V1 methodology

The authorised V1 methodology is:

`FIELD_MEAN_PROJECTED_PERFORMANCE`

The canonical calculation is:

`eri_value = projected_performance_sum / eligible_runner_count`

where the input population contains every governed projected-performance row
for the race.

## Input population

Only rows with:

- `projected_performance_publication_decision =
  PROJECTED_PERFORMANCE_PUBLISHED`
- `projected_performance_reconciliation_decision =
  PROJECTED_PERFORMANCE_RECONCILED`
- `race_entry_projected_performance_status =
  GOVERNED_PROJECTED_PERFORMANCE`

may enter the ERI calculation.

## Complete-field requirement

V1 requires the complete governed eligible field.

The future ERI builder must fail closed when:

- a race has duplicate race-entry IDs
- a race has duplicate projected-performance IDs
- a projected-performance value is blank
- a projected-performance value is non-numeric
- a projected-performance value is non-finite
- source lineage is incomplete
- the eligible field population cannot be established
- the eligible runner count is below the governed minimum
- a race contains conflicting race dates
- a race contains conflicting parameter selection

## Minimum eligible field size

The governed V1 minimum is:

`2`

A race with fewer than two governed eligible runners must not publish ERI.

## Arithmetic

The ERI calculation must use exact finite decimal arithmetic.

The arithmetic mean must be calculated as:

`sum(projected_performance_value) / eligible_runner_count`

The published ERI value must use the governed decimal scale and rounding mode.

## Decimal policy

- output decimal places: `6`
- rounding mode: `ROUND_HALF_EVEN`

The unrounded sum and runner count must also be published by the future ERI
fact to preserve auditability.

## Descriptive field statistics

The future Race ERI Fact V1 must also publish:

- eligible runner count
- projected-performance sum
- projected-performance mean
- projected-performance median
- projected-performance minimum
- projected-performance maximum
- projected-performance range

Only the governed mean becomes `eri_value` in V1.

Median, minimum, maximum, and range are descriptive fields and must not alter
the ERI calculation.

## Parameter scope

The V1 parameter is globally applicable to all eligible races.

Scope:

`GLOBAL`

No track-specific, class-specific, distance-specific, jurisdiction-specific,
surface-specific, or race-type-specific ERI methodology is permitted in V1.

## Parameter selection

The future ERI builder must select exactly one active parameter row.

There must never be:

- no active parameter
- multiple active parameters
- overlapping active parameter periods
- an unsupported method
- an unsupported rounding mode

## Versioning

Any future change to:

- calculation method
- minimum eligible field size
- decimal scale
- rounding mode
- population rule
- field-completeness rule

requires a new governed parameter version.

Historical parameter records must remain immutable.

## Decision

Published parameter rows use:

`ERI_PARAMETER_AUTHORISED`

## Status

Published parameter rows use:

`GOVERNED_ERI_PARAMETER`

## Deterministic identity

`race_eri_parameter_id` is derived from:

- contract version
- parameter version
- methodology code
- effective-from date
- scope

## Evidence identity

The evidence SHA-256 is derived from:

- deterministic parameter ID
- methodology
- population rule
- minimum eligible runner count
- decimal places
- rounding mode
- effective dates
- scope
- decision
- status

## Prohibited behaviour

This parameter fact must not:

- calculate ERI
- calculate projected performance
- calculate EPI
- calculate runner rankings
- calculate race rankings
- calculate probabilities
- calculate fair prices
- read market prices
- calculate market edge
- calculate confidence
- generate predictions
- generate forecasts
- apply hidden weights
- apply class-specific adjustments
- apply track-specific adjustments
- apply market-derived adjustments
