# EDGEIQ Race Entry Context-Adjusted Performance Fact V1

## Status

Governed deterministic warehouse fact.

## Purpose

Race Entry Context-Adjusted Performance Fact V1 publishes the historical
performance rating after application of the exact governed context adjustment.

It performs one calculation only:

`historical_rating_value + total_context_adjustment`

The calculation is permitted only when the source context-adjustment decision
is `ADJUSTMENT_APPLIED`.

## Architecture

Race Entry Context Adjustment Fact V1  
→ Race Entry Context-Adjusted Performance Fact V1  
→ Future Suitability Facts  
→ Future Projected Performance Fact  
→ Future ERI and EPI Facts

## Canonical input

`public/data/edgeiq_race_entry_context_adjustment_fact_v1.csv`

No profile table, market source, race ranking, price source, or prediction
source is permitted.

## Output grain

Exactly one row per governed:

`race_entry_context_adjustment_id`

Natural key:

`race_entry_context_adjustment_id`

## Historical rating

`historical_rating_value` must be copied unchanged from the source context
adjustment fact.

It must not be recalculated, rounded, normalised, smoothed, weighted, or
replaced.

## Context adjustment

`total_context_adjustment` must be copied unchanged from the source context
adjustment fact.

The component adjustments are not recalculated by this layer.

## Context-adjusted performance calculation

When:

`source_adjustment_decision = ADJUSTMENT_APPLIED`

calculate:

`context_adjusted_performance_value =
 historical_rating_value + total_context_adjustment`

The calculation uses exact finite decimal arithmetic.

## Parameter unavailable

When the source decision is:

`PARAMETER_NOT_AVAILABLE`

then:

- `total_context_adjustment` must be blank
- `context_adjusted_performance_value` must be blank
- decision must remain `PARAMETER_NOT_AVAILABLE`
- status must be `GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE`

## Context ineligible

When the source decision is:

`CONTEXT_INELIGIBLE`

then:

- `total_context_adjustment` must be blank
- `context_adjusted_performance_value` must be blank
- decision must remain `CONTEXT_INELIGIBLE`
- status must be `CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTED_PERFORMANCE`

## Decisions

- `PERFORMANCE_ADJUSTED`
- `PARAMETER_NOT_AVAILABLE`
- `CONTEXT_INELIGIBLE`

## Statuses

- `GOVERNED_CONTEXT_ADJUSTED_PERFORMANCE`
- `GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTED_PERFORMANCE`

## Deterministic identity

`race_entry_context_adjusted_performance_id` is derived from:

- contract version
- race-entry context-adjustment ID
- context-adjusted performance decision

## Evidence identity

The evidence SHA-256 is derived from:

- deterministic output ID
- source adjustment evidence SHA-256
- historical rating value
- total context adjustment
- context-adjusted performance value
- output decision
- output status

## Fail-closed rules

The builder must fail when:

- a context-adjustment ID is blank
- a context-adjustment ID is duplicated
- historical rating is blank
- historical rating is non-numeric
- historical rating is non-finite
- an applied adjustment has no total adjustment
- an applied total adjustment is non-numeric
- an applied total adjustment is non-finite
- an unavailable or ineligible row contains an adjustment
- source lineage is incomplete
- an unsupported source decision is encountered
- deterministic output identities collide

## Prohibited behaviour

This layer must not:

- calculate suitability
- calculate EPI
- calculate ERI
- calculate race strength
- calculate runner rank
- calculate race rank
- calculate probability
- calculate fair price
- read market prices
- calculate market edge
- calculate confidence
- generate predictions
- generate forecasts
- train or invoke machine-learning models
- alter the historical rating
- invent or interpolate an adjustment
