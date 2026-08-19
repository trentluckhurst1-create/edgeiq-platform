# EDGEIQ Race Entry EPI Publication Snapshot Fact V1

## Status

Governed canonical runner-level EPI publication snapshot.

## Purpose

Race Entry EPI Publication Snapshot Fact V1 publishes the final governed
runner-level EPI record suitable for downstream read-only presentation feeds.

It consolidates the governed EPI value, race-relative population context,
deterministic ordering, rank and tie structure from:

`edgeiq_race_entry_epi_ordering_fact_v1.csv`

The ordering fact is the terminal governed runner-level dependency because it
already carries the final EPI value, race population, relative-context
provenance and deterministic ordering outputs.

## Output grain

One row per governed race entry.

## Canonical source

`edgeiq_race_entry_epi_ordering_fact_v1.csv`

## Published fields

- race-entry publication snapshot identity
- race-entry identity
- race identity
- race date
- governed EPI value
- eligible EPI population count
- EPI display-order position
- EPI competition rank
- EPI dense rank
- EPI tie-group size
- EPI tie-group position
- EPI tie status
- relative-context evidence hash
- source ordering identity
- source ordering evidence hash
- publication decision
- reconciliation decision
- governed status
- deterministic publication evidence
- source lineage
- builder version
- contract version
- build timestamp

## Source eligibility

Every source row must have:

- complete race-entry identity
- complete race identity
- complete race date
- finite governed six-decimal EPI
- valid population count
- valid display-order position
- valid competition rank
- valid dense rank
- valid tie-group size
- valid tie-group position
- valid tie status
- relative-context evidence
- ordering identity
- ordering evidence
- `EPI_ORDERING_PUBLISHED`
- `EPI_ORDERING_RECONCILED`
- `GOVERNED_RACE_ENTRY_EPI_ORDERING`

## Ordering rules

Within every race:

- display-order positions must equal `1..N`
- EPI must be descending by display order
- equal-EPI entries may differ in display position only
- equal-EPI entries must share competition rank
- equal-EPI entries must share dense rank
- competition rank must follow `1,2,2,4`
- dense rank must follow `1,2,2,3`
- tie-group size must equal exact EPI frequency
- tie-group positions must equal `1..tie-group size`

## Decimal policy

`runner_epi_value` must retain its governed six-decimal source
representation exactly.

No EPI value is recalculated in this publication layer.

## Deterministic identity

`race_entry_epi_publication_snapshot_id` is derived from:

- contract version
- race-entry identity
- race identity
- race date
- governed EPI
- display-order position
- competition rank
- publication decision

## Deterministic evidence

Evidence includes:

- publication snapshot identity
- race-entry identity
- race identity
- race date
- governed EPI
- race population
- display order
- competition rank
- dense rank
- tie-group structure
- relative-context evidence
- source ordering identity
- source ordering evidence
- governance decisions
- source lineage

## Governance

Published rows use:

- `RACE_ENTRY_EPI_SNAPSHOT_PUBLISHED`
- `RACE_ENTRY_EPI_SNAPSHOT_RECONCILED`
- `GOVERNED_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT`

## Prohibited behaviour

This layer must not calculate or publish:

- probability
- implied probability
- fair price
- market price
- market edge
- expected value
- confidence
- prediction
- forecast
- recommendation
- selection
- bet
- tip
- staking
- bookmaker comparison
- value classification

## Empty-source handling

If the canonical source contains no governed rows, the builder publishes an
empty governed fact with its header.

No synthetic race entries may be created.
