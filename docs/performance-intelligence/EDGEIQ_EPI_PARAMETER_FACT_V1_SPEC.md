# EDGEIQ EPI Parameter Fact V1

## Status

Governed deterministic methodology parameter fact.

## Purpose

EPI Parameter Fact V1 defines the authorised methodology that future governed
EPI component and EPI facts must use.

This fact does not calculate runner EPI values.

## Architecture

Race Entry ERI Context Fact V1  
+ Race Entry Suitability Aggregate Fact V1  
+ governed performance sources  
+ EPI Parameter Fact V1  
→ Future EPI Component Fact V1  
→ Future EPI Fact V1

## V1 methodology

Methodology:

`NORMALISED_WEIGHTED_ADDITIVE_EPI_V1`

The future EPI calculation will use independently governed and normalised
components.

Authorised component weights:

- historical performance: `0.500000`
- suitability: `0.300000`
- race context: `0.200000`

Total authorised component weight:

`1.000000`

## Base value

The governed EPI neutral base is:

`100.000000`

The base value is a presentation anchor only.

It must not replace or alter the underlying component evidence.

## Component responsibilities

### Historical performance component

Represents governed historical performance strength derived from the canonical
performance warehouse.

### Suitability component

Represents the governed race-entry suitability aggregate already calculated by
the suitability pipeline.

### Race-context component

Represents the runner's governed projected performance relative to the
governed race ERI.

## Important separation

The parameter fact:

- authorises methodology
- authorises weights
- authorises decimal handling
- authorises effective dates
- defines minimum component requirements

The parameter fact does not:

- calculate component values
- calculate EPI
- rank runners
- calculate probabilities
- calculate prices
- read market data
- generate predictions

## Decimal policy

All published numeric parameters use:

- decimal places: `6`
- rounding mode: `ROUND_HALF_EVEN`

## Required components

V1 requires all three governed components:

- historical performance
- suitability
- race context

No missing component may be silently replaced with:

- zero
- an average
- a market value
- an estimate
- an invented fallback

Future EPI publication must fail closed when any required governed component is
missing.

## Effective period

The initial parameter row is effective from:

`2026-01-01`

It has no end date.

Only one active governed parameter row may apply to a race date.

## Governance

The parameter row must publish:

- `EPI_PARAMETER_AUTHORISED`
- `EPI_PARAMETER_RECONCILED`
- `GOVERNED_EPI_PARAMETER`

## Deterministic identity

`epi_parameter_id` is derived from:

- contract version
- parameter version
- methodology
- effective-from date
- publication decision

## Evidence

`epi_parameter_evidence_sha256` includes:

- parameter identity
- parameter version
- methodology
- base value
- all component weights
- total weight
- component requirements
- decimal policy
- effective dates
- publication decision
- reconciliation decision
- governed status

## Prohibited behaviour

This fact must not contain or calculate:

- runner EPI
- race-entry EPI
- runner ranking
- race ranking
- probability
- fair price
- market price
- market edge
- confidence
- prediction
- forecast
