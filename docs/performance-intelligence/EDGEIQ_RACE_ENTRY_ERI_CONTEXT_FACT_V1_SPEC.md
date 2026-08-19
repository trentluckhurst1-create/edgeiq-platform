# EDGEIQ Race Entry ERI Context Fact V1

## Status

Governed deterministic warehouse fact.

## Purpose

Race Entry ERI Context Fact V1 attaches the governed race-level ERI value and
ERI lineage to each eligible race-entry projected-performance row.

It publishes the runner's projected performance in the context of the governed
projected strength of the complete eligible race field.

It does not calculate EPI.

## Architecture

Race Entry Projected Performance Fact V1  
+ Race ERI Fact V1  
→ Race Entry ERI Context Fact V1  
→ Future EPI Parameter Fact V1  
→ Future EPI Component Fact V1  
→ Future EPI Fact V1

## Canonical inputs

### Race-entry projected performance

`public/data/edgeiq_race_entry_projected_performance_fact_v1.csv`

### Race ERI

`public/data/edgeiq_race_eri_fact_v1.csv`

## Output grain

Exactly one governed row per eligible:

`race_entry_projected_performance_id`

## Join rule

Each projected-performance row joins to exactly one Race ERI row using:

- `race_id`
- `race_date`

Both fields must agree.

The joined ERI row must represent the same race.

## V1 context calculation

The only V1 calculation is:

`projected_performance_vs_eri = projected_performance_value - eri_value`

This is a signed contextual difference.

Interpretation:

- positive: projected performance is above the race ERI
- zero: projected performance equals the race ERI
- negative: projected performance is below the race ERI

This value is not:

- EPI
- a runner rank
- a probability
- a price
- a confidence measure
- a prediction

## Decimal policy

The contextual difference must use exact finite decimal arithmetic.

The output uses:

- decimal places: `6`
- rounding mode: `ROUND_HALF_EVEN`

The source projected-performance value and ERI value are also published at six
decimal places for consistent governed consumption.

## Input governance

Projected-performance rows must have:

- `PROJECTED_PERFORMANCE_PUBLISHED`
- `PROJECTED_PERFORMANCE_RECONCILED`
- `GOVERNED_PROJECTED_PERFORMANCE`

Race ERI rows must have:

- `ERI_PUBLISHED`
- `ERI_METHOD_RECONCILED`
- `GOVERNED_RACE_ERI`

## Population equality

Every projected-performance row must resolve exactly one ERI row.

Every ERI race must have at least one projected-performance source row.

The builder must fail closed when:

- a projected-performance row has no matching ERI
- a projected-performance row matches multiple ERI rows
- an ERI row has no projected-performance rows
- race dates conflict
- race IDs conflict
- source identities are duplicated
- required lineage is missing
- source states are unsupported

## Published decision

Published rows use:

`ERI_CONTEXT_PUBLISHED`

## Reconciliation decision

Published rows use:

`ERI_CONTEXT_RECONCILED`

## Status

Published rows use:

`GOVERNED_RACE_ENTRY_ERI_CONTEXT`

## Deterministic identity

`race_entry_eri_context_id` is derived from:

- contract version
- race-entry projected-performance ID
- race ERI ID
- publication decision

## Evidence

`race_entry_eri_context_evidence_sha256` is derived from:

- deterministic context ID
- projected-performance identity
- projected-performance evidence
- race ERI identity
- race ERI parameter identity
- race ERI evidence
- race-entry identity
- race identity
- race date
- projected-performance value
- ERI value
- projected-performance-versus-ERI value
- publication decision
- reconciliation decision
- status

## Prohibited behaviour

This fact must not:

- alter projected-performance values
- alter ERI values
- calculate EPI
- calculate rankings
- calculate probabilities
- calculate prices
- read market data
- calculate market edge
- calculate confidence
- generate predictions
- generate forecasts
- apply hidden weighting
- apply machine-learning models
