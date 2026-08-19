# EDGEIQ Race Entry Projected Performance Fact V1

## Status

Governed deterministic warehouse fact.

## Purpose

Race Entry Projected Performance Fact V1 publishes the governed performance
value for a horse under the known race-entry context.

It is a publication and reconciliation layer.

It does not independently determine context adjustments and must not apply any
new adjustment, weighting, smoothing, scaling, interpolation, estimation, or
fallback.

## Architecture

Horse Performance Rating Fact V1  
→ Race Entry Horse Performance Snapshot Fact V1  
→ Race Entry Performance Context Fact V1  
→ Race Entry Context Eligibility Fact V1  
→ Race Entry Context Parameter Selection Fact V1  
→ Race Entry Context Adjustment Fact V1  
→ Race Entry Context-Adjusted Performance Fact V1  
→ Race Entry Suitability Component Fact V1  
→ Race Entry Suitability Aggregate Fact V1  
→ Race Entry Projected Performance Fact V1  
→ Future ERI Fact  
→ Future EPI Component Fact  
→ Future Final EPI Fact

## Canonical inputs

### Context-adjusted performance fact

`public/data/edgeiq_race_entry_context_adjusted_performance_fact_v1.csv`

### Suitability aggregate fact

`public/data/edgeiq_race_entry_suitability_aggregate_fact_v1.csv`

## Output grain

Exactly one row per governed:

`race_entry_suitability_aggregate_id`

Each output row represents one eligible race entry with a complete governed
suitability aggregate.

## Eligibility

An output row may only be published when:

- the suitability aggregate decision is `SUITABILITY_AGGREGATED`
- the suitability aggregate status is `GOVERNED_SUITABILITY_AGGREGATE`
- the source adjusted-performance decision is `PERFORMANCE_ADJUSTED`
- the source adjusted-performance status is
  `GOVERNED_CONTEXT_ADJUSTED_PERFORMANCE`

## Canonical calculation

`projected_performance_value =`

`historical_rating_value + aggregate_suitability_value`

The calculation must use exact finite decimal arithmetic.

## Mandatory reconciliation

The calculated:

`projected_performance_value`

must exactly equal:

`context_adjusted_performance_value`

The aggregate:

`aggregate_suitability_value`

must exactly equal:

`total_context_adjustment`

Any mismatch is a fatal governance failure.

## Historical rating preservation

`historical_rating_value` must be copied unchanged from the governed
context-adjusted performance source.

The historical rating must never be recalculated or modified.

## Decisions

Published rows must use:

`PROJECTED_PERFORMANCE_PUBLISHED`

## Status

Published rows must use:

`GOVERNED_PROJECTED_PERFORMANCE`

## Reconciliation decision

Published rows must use:

`PROJECTED_PERFORMANCE_RECONCILED`

## Deterministic identity

`race_entry_projected_performance_id` is derived from:

- contract version
- race-entry suitability aggregate ID
- projected-performance publication decision

## Evidence identity

The evidence SHA-256 is derived from:

- deterministic projected-performance ID
- source adjusted-performance evidence SHA-256
- source suitability-aggregate evidence SHA-256
- historical rating value
- aggregate suitability value
- total context adjustment
- context-adjusted performance value
- projected performance value
- publication decision
- reconciliation decision
- status

## Fail-closed rules

The builder must fail when:

- a canonical input file is missing
- a required source field is missing
- a suitability aggregate ID is blank
- a suitability aggregate ID is duplicated
- a context-adjusted performance ID is blank
- a context-adjusted performance ID is duplicated
- an adjusted-performance source row is missing
- source identities do not agree
- source lineage is incomplete
- any required numeric value is blank
- any required numeric value is non-numeric
- any required numeric value is non-finite
- aggregate suitability does not equal total context adjustment
- projected performance does not equal context-adjusted performance
- an unsupported source decision is encountered
- a deterministic identity collides

## Parameter unavailable and context ineligible

Race entries represented upstream as:

- `PARAMETER_NOT_AVAILABLE`
- `CONTEXT_INELIGIBLE`

do not produce suitability aggregates and therefore do not produce projected
performance rows.

Their absence is independently audited.

## Prohibited behaviour

This fact must not:

- derive new context adjustments
- change historical ratings
- weight suitability components
- calculate EPI
- calculate ERI
- calculate race strength
- calculate ranking
- calculate probability
- calculate fair price
- read market prices
- calculate market edge
- calculate confidence
- generate predictions
- generate forecasts
- train or invoke machine-learning models
