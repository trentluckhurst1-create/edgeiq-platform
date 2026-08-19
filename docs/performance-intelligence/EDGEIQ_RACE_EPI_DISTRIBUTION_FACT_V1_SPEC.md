# EDGEIQ Race EPI Distribution Fact V1

## Status

Governed deterministic race-level descriptive distribution fact.

## Purpose

Race EPI Distribution Fact V1 calculates descriptive population statistics
for the governed EPI values published for each race.

It provides race-level context without ranking runners or introducing any
pricing, probability, market, confidence or recommendation logic.

## Canonical input

`edgeiq_race_entry_epi_fact_v1.csv`

Only rows with all of the following may enter the distribution:

- `epi_publication_decision = EPI_PUBLISHED`
- `epi_reconciliation_decision = EPI_RECONCILED`
- `epi_status = GOVERNED_RACE_ENTRY_EPI`
- finite governed `epi_value`
- complete race identity
- complete race-entry identity
- complete EPI evidence

## Output grain

One row per:

`race_id + race_date`

## Population definition

The distribution population is the complete set of governed Race Entry EPI
Fact rows for the race.

No governed race-entry EPI row may be excluded because of:

- EPI value
- runner identity
- market position
- price
- trainer
- jockey
- barrier
- subjective opinion
- manual selection

## V1 calculations

Population count:

`N`

EPI total:

`sum(EPI)`

Field mean:

`sum(EPI) / N`

Population variance:

`sum((EPI - field mean)^2) / N`

Population standard deviation:

`square root(population variance)`

Minimum EPI:

`minimum(EPI)`

Maximum EPI:

`maximum(EPI)`

EPI range:

`maximum EPI - minimum EPI`

## Population standard deviation

Population standard deviation is mandatory.

The divisor is:

`N`

not:

`N - 1`

Sample standard deviation is prohibited.

## Single-entry populations

A governed one-entry race population may be published descriptively.

For a one-entry population:

- variance is `0.000000`
- population standard deviation is `0.000000`
- minimum equals maximum
- range is `0.000000`

No additional runner may be invented.

## Decimal policy

All published numeric distribution values use:

- six decimal places
- `ROUND_HALF_EVEN`

High-precision decimal arithmetic must be used before publication rounding.

## Reconciliation

A race distribution may publish only where:

- every source row is governed
- race identity is complete
- race date is complete
- race-entry identities are unique within the race
- Race Entry EPI Fact identities are unique
- all EPI values are finite
- all source evidence hashes are present
- population arithmetic can be independently reproduced

## Governance

Published rows use:

- `RACE_EPI_DISTRIBUTION_PUBLISHED`
- `RACE_EPI_DISTRIBUTION_RECONCILED`
- `GOVERNED_RACE_EPI_DISTRIBUTION`

## Deterministic identity

`race_epi_distribution_id` is derived from:

- contract version
- race ID
- race date
- governed EPI population count
- deterministic source-population SHA256
- publication decision

## Source-population evidence

The deterministic source-population SHA256 is derived from sorted source rows
using:

- race-entry ID
- Race Entry EPI Fact ID
- EPI value
- Race Entry EPI evidence SHA256

## Distribution evidence

The deterministic distribution evidence SHA256 includes:

- distribution identity
- race identity
- race date
- population count
- EPI total
- field mean
- population variance
- population standard deviation
- minimum EPI
- maximum EPI
- EPI range
- source-population SHA256
- governance decisions
- source lineage

## Prohibited behaviour

This fact must not calculate or publish:

- runner rank
- EPI rank
- race rank
- percentile
- probability
- fair price
- market price
- market edge
- confidence
- prediction
- forecast
- recommendation
- bet classification
- selection
- tip

## Empty-source handling

Where Race Entry EPI Fact V1 contains zero rows, the builder publishes an
empty governed distribution fact with its header.

The independent audit may pass with zero distribution rows.

No synthetic race or runner rows may be created.
