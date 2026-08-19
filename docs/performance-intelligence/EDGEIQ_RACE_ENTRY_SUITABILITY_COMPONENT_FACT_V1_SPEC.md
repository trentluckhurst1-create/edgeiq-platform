# EDGEIQ Race Entry Suitability Component Fact V1

## Status

Governed deterministic warehouse fact.

## Purpose

Race Entry Suitability Component Fact V1 publishes each governed race-entry
context component separately.

This fact does not calculate an aggregate suitability score.

It preserves the component values already applied by Race Entry Context
Adjustment Fact V1 and exposes them at a normalized component grain for
downstream aggregation, projected performance, EPI, and ERI processes.

## Architecture

Race Entry Context Adjustment Fact V1  
+ Race Entry Context-Adjusted Performance Fact V1  
→ Race Entry Suitability Component Fact V1  
→ Future Race Entry Suitability Aggregate Fact  
→ Future Race Entry Projected Performance Fact  
→ Future ERI and EPI Facts

## Canonical inputs

### Context-adjustment fact

`public/data/edgeiq_race_entry_context_adjustment_fact_v1.csv`

### Context-adjusted performance fact

`public/data/edgeiq_race_entry_context_adjusted_performance_fact_v1.csv`

## Output grain

Exactly one row per:

- `race_entry_context_adjusted_performance_id`
- `suitability_component_type`

For an eligible adjusted-performance row, exactly nine component rows must be
published.

## Component types

The only permitted component types are:

- `DISTANCE`
- `CLASS`
- `TRACK`
- `TRACK_CONFIGURATION`
- `TRACK_CONDITION`
- `SURFACE`
- `BARRIER`
- `WEIGHT`
- `FIELD_SIZE`

## Component source mapping

| Component type | Source field |
|---|---|
| DISTANCE | distance_adjustment |
| CLASS | class_adjustment |
| TRACK | track_adjustment |
| TRACK_CONFIGURATION | track_configuration_adjustment |
| TRACK_CONDITION | track_condition_adjustment |
| SURFACE | surface_adjustment |
| BARRIER | barrier_adjustment |
| WEIGHT | weight_adjustment |
| FIELD_SIZE | field_size_adjustment |

## Component value

When the source adjusted-performance decision is:

`PERFORMANCE_ADJUSTED`

the component value must be copied exactly from the corresponding governed
context-adjustment component.

No recalculation, scaling, weighting, smoothing, interpolation, or
normalisation is permitted.

## Parameter unavailable

When the source adjusted-performance decision is:

`PARAMETER_NOT_AVAILABLE`

no component rows are published.

## Context ineligible

When the source adjusted-performance decision is:

`CONTEXT_INELIGIBLE`

no component rows are published.

## Publication decisions

- `COMPONENT_PUBLISHED`
- `COMPONENTS_NOT_PUBLISHED_PARAMETER_NOT_AVAILABLE`
- `COMPONENTS_NOT_PUBLISHED_CONTEXT_INELIGIBLE`

Only `COMPONENT_PUBLISHED` produces output rows.

The other decisions are represented by the absence of component rows and are
audited against the upstream adjusted-performance population.

## Component status

Published component rows must use:

`GOVERNED_SUITABILITY_COMPONENT`

## Deterministic identity

`race_entry_suitability_component_id` is derived from:

- contract version
- race-entry context-adjusted performance ID
- suitability component type

## Evidence identity

The component evidence SHA-256 is derived from:

- deterministic component ID
- source adjusted-performance evidence SHA-256
- source context-adjustment evidence SHA-256
- component type
- source component field
- component value
- component decision
- component status

## Required source consistency

The builder must prove:

- one context-adjustment source row per context-adjustment ID
- one adjusted-performance row per adjusted-performance ID
- adjusted-performance and context-adjustment identities agree
- historical rating values agree
- context parameter IDs agree
- total context adjustments agree
- source decisions agree
- source lineage is complete

## Fail-closed rules

The builder must fail when:

- a required source file is missing
- an adjusted-performance ID is blank
- an adjusted-performance ID is duplicated
- a required context-adjustment row is absent
- context-adjustment identities do not match
- an eligible component is blank
- an eligible component is non-numeric
- an eligible component is non-finite
- a component type is unsupported
- source lineage is incomplete
- deterministic identities collide

## Prohibited behaviour

This fact must not:

- calculate aggregate suitability
- calculate projected performance
- calculate EPI
- calculate ERI
- calculate race strength
- calculate ranking
- calculate probability
- calculate fair price
- use market prices
- calculate market edge
- calculate confidence
- generate predictions
- generate forecasts
- invent missing components
- interpolate components
- apply fallback components
- alter historical or context-adjusted performance
