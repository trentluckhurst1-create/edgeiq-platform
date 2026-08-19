# EDGEIQ Race Entry EPI Component Fact V1

## Status

Governed deterministic race-entry component fact.

## Purpose

Race Entry EPI Component Fact V1 calculates the three separately governed,
normalised and weighted inputs required by a future EPI Fact.

The three components are:

1. `HISTORICAL_PERFORMANCE`
2. `SUITABILITY`
3. `RACE_CONTEXT`

This layer does not calculate final EPI.

## Canonical inputs

### Historical performance

Source:

`edgeiq_race_entry_projected_performance_fact_v1.csv`

Governed raw value:

`projected_performance_value`

### Suitability

Source:

`edgeiq_race_entry_suitability_aggregate_fact_v1.csv`

Governed raw value:

`suitability_aggregate_value`

The builder may recognise a governed equivalent column alias only where the
canonical column name differs in an already-built source contract.

### Race context

Source:

`edgeiq_race_entry_eri_context_fact_v1.csv`

Governed raw value:

`projected_performance_vs_eri`

## Parameter inputs

Weight methodology:

`edgeiq_epi_parameter_fact_v1.csv`

Normalisation methodology:

`edgeiq_epi_component_normalisation_parameter_fact_v1.csv`

## Population reconciliation

All three source facts must describe the same complete governed race-entry
population.

A race entry cannot be published unless it has all three governed component
inputs.

The builder must fail closed when non-empty source populations disagree.

No inner join may silently discard an unmatched race entry.

## Normalisation

For each race and component:

`field_mean = sum(raw values) / N`

Population variance:

`sum((raw value - field mean)^2) / N`

Population standard deviation:

`square root(population variance)`

Unbounded normalised value:

`(raw value - field mean) / field population standard deviation`

Capped normalised value:

`minimum(upper cap, maximum(lower cap, unbounded normalised value))`

## Weighting

`weighted_component_value = capped_normalised_value * authorised_component_weight`

Authorised V1 weights:

- historical performance: `0.500000`
- suitability: `0.300000`
- race context: `0.200000`

## Minimum population

At least two eligible race entries are required for a race.

## Zero variance

If a component has zero population variance within a race, the entire race
must fail closed.

No neutral value may be invented.

## Output grain

One row per:

`race_entry_id + epi_component_code`

A fully eligible race entry therefore publishes exactly three rows.

## Governance

Published rows use:

- `EPI_COMPONENT_PUBLISHED`
- `EPI_COMPONENT_RECONCILED`
- `GOVERNED_RACE_ENTRY_EPI_COMPONENT`

## Deterministic identity

`race_entry_epi_component_id` is derived from:

- contract version
- race entry ID
- race ID
- race date
- component code
- source fact ID
- EPI parameter ID
- normalisation parameter ID
- publication decision

## Evidence

Evidence includes:

- deterministic identity
- race-entry identity
- component identity
- source fact identity
- raw value
- field population count
- field mean
- field population standard deviation
- unbounded normalised value
- capped normalised value
- authorised weight
- weighted component value
- parameter identities
- governance decisions
- source evidence

## Prohibited behaviour

This fact must not calculate or publish:

- final EPI
- EPI rank
- runner rank
- probability
- fair price
- market price
- market edge
- confidence
- prediction
- forecast

## Empty source handling

Where all three canonical source facts are empty, the builder publishes an
empty governed fact with its header and the audit may pass with zero rows.

A mixed empty and non-empty source state must fail closed.
