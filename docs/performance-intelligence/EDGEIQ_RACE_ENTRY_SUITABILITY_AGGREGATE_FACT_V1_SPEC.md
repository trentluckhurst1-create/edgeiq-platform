# EDGEIQ Race Entry Suitability Aggregate Fact V1

## Status

Governed deterministic warehouse fact.

## Purpose

Race Entry Suitability Aggregate Fact V1 publishes the exact aggregate of the
nine governed race-entry suitability components.

It answers one factual question only:

What is the total governed suitability adjustment represented by the complete
set of published suitability components?

It does not calculate projected performance, EPI, ERI, ranking, probability,
price, confidence, or prediction.

## Architecture

Race Entry Context-Adjusted Performance Fact V1  
+ Race Entry Suitability Component Fact V1  
→ Race Entry Suitability Aggregate Fact V1  
→ Future Race Entry Projected Performance Fact  
→ Future ERI and EPI Facts

## Canonical inputs

### Context-adjusted performance fact

`public/data/edgeiq_race_entry_context_adjusted_performance_fact_v1.csv`

### Suitability component fact

`public/data/edgeiq_race_entry_suitability_component_fact_v1.csv`

## Output grain

Exactly one row per governed:

`race_entry_context_adjusted_performance_id`

Only rows with:

`context_adjusted_performance_decision = PERFORMANCE_ADJUSTED`

are eligible for aggregate publication.

## Required component set

Every published aggregate must be supported by exactly one row for each of:

- `DISTANCE`
- `CLASS`
- `TRACK`
- `TRACK_CONFIGURATION`
- `TRACK_CONDITION`
- `SURFACE`
- `BARRIER`
- `WEIGHT`
- `FIELD_SIZE`

No duplicate component type is permitted.

No partial component set is permitted.

## Aggregate calculation

The canonical calculation is:

`aggregate_suitability_value =`

`distance_suitability_value`  
`+ class_suitability_value`  
`+ track_suitability_value`  
`+ track_configuration_suitability_value`  
`+ track_condition_suitability_value`  
`+ surface_suitability_value`  
`+ barrier_suitability_value`  
`+ weight_suitability_value`  
`+ field_size_suitability_value`

The calculation uses exact finite decimal arithmetic.

No weighting, smoothing, scaling, normalisation, interpolation, estimation, or
fallback is permitted.

## Source total reconciliation

For every published aggregate:

`aggregate_suitability_value`

must exactly equal the source:

`total_context_adjustment`

from Race Entry Context-Adjusted Performance Fact V1.

A mismatch is a fatal governance failure.

## Decisions

Published rows must use:

`SUITABILITY_AGGREGATED`

## Status

Published rows must use:

`GOVERNED_SUITABILITY_AGGREGATE`

## Deterministic identity

`race_entry_suitability_aggregate_id` is derived from:

- contract version
- race-entry context-adjusted performance ID
- aggregate decision

## Evidence identity

The evidence SHA-256 is derived from:

- deterministic aggregate ID
- source adjusted-performance evidence SHA-256
- ordered component evidence SHA-256 values
- ordered component values
- aggregate suitability value
- source total context adjustment
- aggregate decision
- aggregate status

## Fail-closed rules

The builder must fail when:

- a required source file is missing
- an eligible adjusted-performance ID is blank
- an eligible adjusted-performance ID is duplicated
- a component ID is blank
- a component ID is duplicated
- a component natural key is duplicated
- a required component is absent
- an unsupported component type is encountered
- an eligible component is blank
- an eligible component is non-numeric
- an eligible component is non-finite
- a component belongs to a non-eligible adjusted-performance row
- component lineage is incomplete
- component identity does not match the adjusted-performance source
- aggregate does not reconcile to total context adjustment
- deterministic identities collide

## Parameter unavailable and context ineligible

Rows with:

- `PARAMETER_NOT_AVAILABLE`
- `CONTEXT_INELIGIBLE`

do not produce suitability aggregate rows.

Their absence is governed and independently audited.

## Prohibited behaviour

This fact must not:

- calculate projected performance
- add the aggregate to historical performance
- add the aggregate to context-adjusted performance
- calculate EPI
- calculate ERI
- calculate race strength
- calculate rankings
- calculate probabilities
- calculate fair prices
- read market prices
- calculate market edge
- calculate confidence
- generate predictions
- generate forecasts
- train or invoke machine-learning models
- invent missing component values
- use partial component sets
