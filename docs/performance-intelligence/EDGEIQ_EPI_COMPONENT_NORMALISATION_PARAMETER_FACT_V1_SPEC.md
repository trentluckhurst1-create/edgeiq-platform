# EDGEIQ EPI Component Normalisation Parameter Fact V1

## Status

Governed deterministic methodology parameter fact.

## Purpose

EPI Component Normalisation Parameter Fact V1 defines the authorised
normalisation methodology for the three governed EPI inputs:

- historical performance
- suitability
- race context

This layer exists because the raw source values are not guaranteed to use the
same scale.

No weighted EPI component or final EPI value may be calculated until this
normalisation methodology has been authorised.

## Architecture

Governed EPI source facts  
+ EPI Component Normalisation Parameter Fact V1  
+ EPI Parameter Fact V1  
→ Future Race Entry EPI Component Fact V1  
→ Future Race Entry EPI Fact V1

## V1 methodology

Methodology:

`WITHIN_RACE_POPULATION_Z_SCORE_CAPPED_V1`

For each component and each race:

`unbounded_normalised_value = (raw_value - field_mean) / field_population_standard_deviation`

The value is then capped:

- lower bound: `-3.000000`
- upper bound: `3.000000`

The governed output is rounded to six decimal places using:

`ROUND_HALF_EVEN`

## Population definition

The normalisation population is the complete governed eligible field for the
race.

No runner may be omitted because of:

- rank
- market position
- price
- trainer
- jockey
- barrier
- subjective confidence
- manual selection

## Standard-deviation policy

Population standard deviation must be used.

Sample standard deviation is prohibited.

The population divisor is:

`N`

not:

`N - 1`

## Minimum population

At least two governed eligible runners are required.

## Zero-variance policy

If every eligible runner has the same raw component value, the population
standard deviation is zero.

The V1 policy is:

`FAIL_CLOSED`

No normalised component row may be published for that race and component.

The system must not silently substitute:

- zero
- the field mean
- a neutral score
- a previous race value
- an estimate
- a market-derived value

## Component rows

The fact publishes one parameter row for each component:

1. `HISTORICAL_PERFORMANCE`
2. `SUITABILITY`
3. `RACE_CONTEXT`

All three components use the same V1 normalisation methodology and bounds.

## Effective period

The initial parameter rows are effective from:

`2026-01-01`

They have no end date.

Exactly one active governed parameter row must apply to each component for a
race date.

## Governance

Published rows use:

- `EPI_NORMALISATION_PARAMETER_AUTHORISED`
- `EPI_NORMALISATION_PARAMETER_RECONCILED`
- `GOVERNED_EPI_NORMALISATION_PARAMETER`

## Deterministic identity

`epi_component_normalisation_parameter_id` is derived from:

- contract version
- parameter version
- component code
- methodology
- effective-from date
- publication decision

## Evidence

The parameter evidence SHA256 includes:

- deterministic identity
- parameter version
- component code
- methodology
- population scope
- standard-deviation basis
- minimum population
- lower cap
- upper cap
- zero-variance policy
- decimal policy
- effective dates
- governance decisions
- status

## Prohibited behaviour

This fact must not:

- calculate runner-level normalised values
- calculate weighted components
- calculate EPI
- rank runners
- calculate probabilities
- calculate prices
- read market data
- calculate market edge
- calculate confidence
- generate predictions
- generate forecasts
