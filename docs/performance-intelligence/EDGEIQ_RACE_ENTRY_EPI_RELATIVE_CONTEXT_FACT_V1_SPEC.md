# EDGEIQ Race Entry EPI Relative Context Fact V1

## Status

Governed deterministic race-entry descriptive EPI context fact.

## Purpose

Race Entry EPI Relative Context Fact V1 joins each governed Race Entry EPI
Fact row to its governed Race EPI Distribution Fact row.

It publishes descriptive relative context only.

It does not rank runners and does not introduce pricing, probability, market,
confidence, prediction, recommendation or selection logic.

## Canonical inputs

### Race Entry EPI Fact V1

`edgeiq_race_entry_epi_fact_v1.csv`

### Race EPI Distribution Fact V1

`edgeiq_race_epi_distribution_fact_v1.csv`

## Output grain

One row per:

`race_entry_id`

## Required join

The race-entry EPI row must join to exactly one race distribution using:

`race_id + race_date`

No partial, inferred or fallback join is permitted.

## V1 calculations

### EPI minus field mean

`runner EPI - field EPI mean`

### Population z-score

Where population standard deviation is greater than zero:

`(runner EPI - field EPI mean) / field population standard deviation`

Where population standard deviation is exactly zero:

`0.000000`

A zero standard deviation is valid only where every EPI value in the governed
race population is identical.

### Distance above minimum

`runner EPI - field minimum EPI`

### Distance below maximum

`field maximum EPI - runner EPI`

## Range reconciliation

For every published row:

`distance above minimum + distance below maximum = race EPI range`

subject to the governed six-decimal publication policy.

## Population boundaries

Every runner EPI must satisfy:

`minimum EPI <= runner EPI <= maximum EPI`

## Decimal policy

All numeric values use:

- six decimal places
- high-precision decimal arithmetic
- `ROUND_HALF_EVEN`

## Required reconciliation

A row may publish only where:

- the source Race Entry EPI row is governed
- the source race distribution row is governed
- race identity agrees
- race date agrees
- source identities are unique
- the runner belongs to the distribution population
- population count is at least one
- all numeric inputs are finite
- the runner EPI lies within the published distribution boundaries
- relative arithmetic can be independently reproduced
- source evidence hashes are present
- source lineage is complete

## Governance

Published rows use:

- `EPI_RELATIVE_CONTEXT_PUBLISHED`
- `EPI_RELATIVE_CONTEXT_RECONCILED`
- `GOVERNED_RACE_ENTRY_EPI_RELATIVE_CONTEXT`

## Deterministic identity

`race_entry_epi_relative_context_id` is derived from:

- contract version
- race-entry ID
- Race Entry EPI Fact ID
- race ID
- race date
- Race EPI Distribution Fact ID
- publication decision

## Deterministic evidence

The evidence SHA256 includes:

- relative-context identity
- race-entry identity
- race identity
- race date
- source EPI fact identity
- source distribution identity
- runner EPI
- field EPI mean
- EPI minus field mean
- field population standard deviation
- population z-score
- field minimum
- field maximum
- EPI range
- distance above minimum
- distance below maximum
- population count
- source evidence hashes
- governance decisions
- source lineage

## Prohibited behaviour

This fact must not calculate or publish:

- runner rank
- EPI rank
- race rank
- ordinal position
- percentile
- quantile
- probability
- fair price
- market price
- market edge
- confidence
- prediction
- forecast
- recommendation
- selection
- bet
- tip

## Empty-source handling

Where both canonical inputs contain zero governed rows, the builder publishes
an empty governed fact with its header.

Where one source is populated and the other source is empty, the builder must
fail closed.

No synthetic rows may be created.
