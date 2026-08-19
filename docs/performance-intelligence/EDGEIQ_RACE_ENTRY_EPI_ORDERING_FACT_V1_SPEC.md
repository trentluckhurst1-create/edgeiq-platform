# EDGEIQ Race Entry EPI Ordering Fact V1

## Status

Governed deterministic race-entry EPI ordering fact.

## Purpose

Race Entry EPI Ordering Fact V1 introduces deterministic within-race ordering
for governed Race Entry EPI values.

It publishes explicit rank and tie metadata for analytical and display use.

It does not calculate probability, pricing, market edge, confidence,
recommendations, betting classifications or selections.

## Canonical input

`edgeiq_race_entry_epi_relative_context_fact_v1.csv`

Only rows with all of the following may enter the ordering population:

- `epi_relative_context_publication_decision = EPI_RELATIVE_CONTEXT_PUBLISHED`
- `epi_relative_context_reconciliation_decision = EPI_RELATIVE_CONTEXT_RECONCILED`
- `epi_relative_context_status = GOVERNED_RACE_ENTRY_EPI_RELATIVE_CONTEXT`
- complete race identity
- complete race-entry identity
- finite governed `runner_epi_value`
- complete source evidence

## Output grain

One row per:

`race_entry_id`

## Ordering direction

Higher EPI values sort before lower EPI values.

Primary ordering:

`runner_epi_value DESC`

Stable tie ordering:

`race_entry_id ASC`

The stable tie ordering exists only to provide deterministic display order.

It must not be interpreted as a performance distinction between tied entries.

## Published positions

### Display order position

A unique sequential position within the race:

`1, 2, 3, ... N`

Display order uses:

1. EPI descending
2. race-entry ID ascending for exact EPI ties

### Competition rank

Competition ranking uses:

`1, 2, 2, 4`

All entries sharing the same governed EPI receive the same competition rank.

The next rank advances by the full tie-group size.

### Dense rank

Dense ranking uses:

`1, 2, 2, 3`

All entries sharing the same governed EPI receive the same dense rank.

The next distinct EPI receives the immediately following dense rank.

### Tie-group position

Within an exact EPI tie, deterministic tie-group position is:

`1, 2, 3, ... tie-group size`

Tie-group position is assigned by race-entry ID ascending.

It is display metadata only.

### Tie-group size

The number of governed race entries sharing the same six-decimal EPI value.

### Tie status

Allowed values:

- `UNIQUE_EPI`
- `TIED_EPI`

## Tie equality

V1 tie equality uses the published governed six-decimal `runner_epi_value`.

No hidden unrounded value may break a published EPI tie.

## Population reconciliation

For each race:

- output count equals governed source count
- display positions are exactly `1..N`
- competition rank starts at 1
- dense rank starts at 1
- identical EPI values share competition rank
- identical EPI values share dense rank
- tie-group size equals actual exact-EPI frequency
- tie-group positions are exactly `1..tie-group size`
- unique EPI values have tie-group size 1
- unique EPI values have tie-group position 1
- lower EPI values cannot receive a better rank than higher EPI values

## Deterministic identity

`race_entry_epi_ordering_id` is derived from:

- contract version
- race-entry ID
- race ID
- race date
- source relative-context ID
- runner EPI
- display order position
- competition rank
- dense rank
- publication decision

## Deterministic evidence

Evidence includes:

- ordering identity
- race-entry identity
- race identity
- source relative-context identity
- runner EPI
- population count
- display order
- competition rank
- dense rank
- tie-group size
- tie-group position
- tie status
- source evidence hash
- governance decisions
- source lineage

## Governance

Published rows use:

- `EPI_ORDERING_PUBLISHED`
- `EPI_ORDERING_RECONCILED`
- `GOVERNED_RACE_ENTRY_EPI_ORDERING`

## Prohibited behaviour

This fact must not calculate or publish:

- probability
- implied probability
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
- staking
- expected value
- value classification
- bookmaker comparison

## Empty-source handling

If the canonical input contains zero governed rows, the builder publishes an
empty governed fact with its header.

No synthetic race entries may be created.
