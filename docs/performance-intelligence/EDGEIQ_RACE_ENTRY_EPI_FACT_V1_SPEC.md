# EDGEIQ Race Entry EPI Fact V1

## Status

Governed deterministic race-entry EPI fact.

## Purpose

Race Entry EPI Fact V1 combines the three governed Race Entry EPI Component
Fact rows into one governed EPI value per fully reconciled race entry.

This is the first canonical publication of race-entry EPI from the Performance
Intelligence Warehouse.

## Canonical inputs

### Race Entry EPI Component Fact V1

`edgeiq_race_entry_epi_component_fact_v1.csv`

Each eligible race entry must have exactly three component rows:

1. `HISTORICAL_PERFORMANCE`
2. `SUITABILITY`
3. `RACE_CONTEXT`

### EPI Parameter Fact V1

`edgeiq_epi_parameter_fact_v1.csv`

The parameter fact authorises:

- EPI base value
- component weights
- required component count
- decimal policy
- effective dates
- methodology

## V1 calculation

Weighted component total:

`historical weighted component`
`+ suitability weighted component`
`+ race-context weighted component`

Final EPI:

`EPI = governed EPI base value + weighted component total`

The authorised V1 base value is:

`100.000000`

## Required reconciliation

A race entry may publish only where:

- exactly three component rows exist
- all three authorised component codes exist
- no duplicate component exists
- all rows reference the same race entry
- all rows reference the same race
- all rows reference the same race date
- all rows reference the same EPI parameter ID
- all rows are governed and reconciled
- published component weights match the EPI parameter
- component weights total exactly `1.000000`
- component evidence is present
- the EPI parameter is active on the race date

## Fail-closed rules

No EPI row may be published where:

- a required component is missing
- a component is duplicated
- component populations disagree
- the parameter is missing
- the parameter is inactive
- a component is ungoverned
- numeric values are missing
- numeric values are non-finite
- component weights do not reconcile
- arithmetic cannot be independently reproduced

No missing component may be replaced with:

- zero
- an average
- a neutral value
- a market value
- an estimate
- a prior value
- an invented fallback

## Output grain

One row per:

`race_entry_id`

## Published component trace

The fact preserves the separate component values:

- historical normalised value
- historical weighted value
- suitability normalised value
- suitability weighted value
- race-context normalised value
- race-context weighted value

This permits full independent reconstruction of EPI.

## Governance

Published rows use:

- `EPI_PUBLISHED`
- `EPI_RECONCILED`
- `GOVERNED_RACE_ENTRY_EPI`

## Deterministic identity

`race_entry_epi_id` is derived from:

- contract version
- race entry ID
- race ID
- race date
- EPI parameter ID
- three component fact IDs
- publication decision

## Evidence

The deterministic EPI evidence SHA256 includes:

- EPI fact identity
- race-entry identity
- race identity
- race date
- EPI methodology
- base value
- all component fact IDs
- all component evidence hashes
- all normalised component values
- all authorised component weights
- all weighted component values
- weighted component total
- EPI value
- parameter identity
- governance decisions
- source lineage

## Prohibited behaviour

This fact must not calculate or publish:

- EPI ranking
- runner ranking
- race ranking
- probability
- fair price
- market price
- market edge
- confidence
- prediction
- forecast
- recommendation
- bet classification

## Empty-source handling

Where the Race Entry EPI Component Fact contains zero rows, the builder
publishes an empty governed EPI fact with its header.

The independent audit may pass with zero rows.

No synthetic EPI rows may be created.
