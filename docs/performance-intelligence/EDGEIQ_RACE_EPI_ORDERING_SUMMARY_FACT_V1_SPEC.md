# EDGEIQ Race EPI Ordering Summary Fact V1

## Status

Governed deterministic race-level EPI ordering summary.

## Purpose

Race EPI Ordering Summary Fact V1 summarises each governed race population
from Race Entry EPI Ordering Fact V1.

It publishes descriptive ordering and tie structure only.

It does not calculate or publish probability, pricing, market edge,
confidence, betting classifications, recommendations or selections.

## Canonical input

`edgeiq_race_entry_epi_ordering_fact_v1.csv`

## Output grain

One row per:

`race_id + race_date`

## Required source governance

Only rows with all of the following may enter the summary population:

- `epi_ordering_publication_decision = EPI_ORDERING_PUBLISHED`
- `epi_ordering_reconciliation_decision = EPI_ORDERING_RECONCILED`
- `epi_ordering_status = GOVERNED_RACE_ENTRY_EPI_ORDERING`
- complete race identity
- complete race-entry identity
- finite governed six-decimal EPI
- complete ordering identity
- complete ordering evidence

## Published metrics

- ordered population count
- distinct EPI count
- unique-EPI entry count
- tied-EPI entry count
- tie-group count
- largest tie-group size
- top EPI
- second distinct EPI
- top-to-second EPI gap
- top tie-group size
- top tie status

## Definitions

### Ordered population count

The number of governed Race Entry EPI Ordering rows in the race.

### Distinct EPI count

The number of distinct governed six-decimal EPI values.

### Unique-EPI entry count

The number of race entries whose EPI occurs exactly once in the race.

### Tied-EPI entry count

The number of race entries whose EPI occurs more than once.

### Tie-group count

The number of distinct EPI values shared by two or more entries.

### Largest tie-group size

The greatest exact-EPI frequency in the race.

### Top EPI

The highest governed EPI in the race.

### Second distinct EPI

The second-highest distinct governed EPI.

Where fewer than two distinct EPI values exist:

`second_distinct_epi_available = NO`

and:

`second_distinct_epi = ""`

### Top-to-second EPI gap

Where a second distinct EPI exists:

`top EPI - second distinct EPI`

Where no second distinct EPI exists:

`top_to_second_epi_gap_available = NO`

and:

`top_to_second_epi_gap = ""`

### Top tie status

Allowed values:

- `TOP_EPI_UNIQUE`
- `TOP_EPI_TIED`

## Reconciliation requirements

For each race:

- output population equals source population
- display order positions reconcile to `1..N`
- ordered population count is at least one
- distinct EPI count is between 1 and population count
- unique-EPI entry count plus tied-EPI entry count equals population count
- tie-group count equals the number of EPI frequencies greater than one
- largest tie-group size equals the maximum EPI frequency
- top EPI equals the maximum governed EPI
- top tie-group size equals the frequency of top EPI
- second distinct EPI is lower than top EPI when available
- top-to-second gap is positive when available

## Decimal policy

All published EPI values use the governed six-decimal representation.

All calculated EPI gaps use:

- Decimal arithmetic
- six decimal places
- ROUND_HALF_EVEN

## Deterministic identity

`race_epi_ordering_summary_id` is derived from:

- contract version
- race ID
- race date
- ordered population count
- distinct EPI count
- top EPI
- publication decision

## Deterministic evidence

Evidence includes:

- summary identity
- race identity
- all published counts
- top EPI
- second distinct EPI availability and value
- top-to-second gap availability and value
- top tie-group size
- top tie status
- ordered source identities
- ordered source evidence hashes
- governance decisions
- source lineage

## Governance

Published rows use:

- `RACE_EPI_ORDERING_SUMMARY_PUBLISHED`
- `RACE_EPI_ORDERING_SUMMARY_RECONCILED`
- `GOVERNED_RACE_EPI_ORDERING_SUMMARY`

## Prohibited behaviour

This fact must not calculate or publish:

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

Where the canonical input contains zero governed rows, the builder publishes
an empty governed fact with its header.

No synthetic races may be created.
