# EDGEIQ Race Entry Context Parameter Selection Fact V1

## Status

Governed exact context-parameter selection layer.

## Purpose

Race Entry Context Parameter Selection Fact V1 selects the exact governed
context parameter record applicable to each eligible race-entry context.

This layer performs selection only.

It does not calculate:

- suitability
- rating adjustments
- context-adjusted ratings
- EPI
- ERI
- rankings
- fair prices
- predictions

## Architecture

Race Entry Context Eligibility Fact V1  
+ Race Entry Performance Context Fact V1  
+ Context Parameter Registry V1  
→ Race Entry Context Parameter Selection Fact V1  
→ Future Context Adjustment Fact  
→ Future Suitability Facts  
→ Future EPI Engine

## Canonical inputs

### Eligibility input

`public/data/edgeiq_race_entry_context_eligibility_fact_v1.csv`

### Factual context input

`public/data/edgeiq_race_entry_performance_context_fact_v1.csv`

### Governed parameter registry

`public/data/edgeiq_context_parameter_registry_v1.csv`

The context and registry inputs are required only when the eligibility input
contains rows.

When the eligibility input contains zero rows:

- context input is not required
- parameter registry input is not required
- a governed header-only output is published
- the audit must PASS

## Output grain

Exactly one selection-decision row per governed context-eligibility row.

The natural key is:

`race_entry_context_eligibility_id`

## Registry grain

One exact parameter record per supported context signature.

Required registry fields:

- context_parameter_id
- race_distance_m
- race_class_code
- track_id
- track_configuration
- track_condition
- racing_surface
- barrier_band
- weight_band
- field_size_band
- parameter_status
- context_parameter_evidence_sha256
- builder_version
- contract_version

## Exact context signature

A parameter match requires exact equality across:

- race distance
- race class code
- track ID
- track configuration
- normalised track condition
- normalised racing surface
- deterministic barrier band
- deterministic allocated-weight band
- deterministic field-size band

No partial match is permitted.

No generic fallback is permitted.

No nearest-distance match is permitted.

No class substitution is permitted.

No track substitution is permitted.

## Deterministic bands

### Barrier band

- `INNER`: barrier proportion greater than 0 and no greater than 0.333333
- `MIDDLE`: barrier proportion greater than 0.333333 and no greater than 0.666667
- `OUTER`: barrier proportion greater than 0.666667 and no greater than 1

Barrier proportion:

`barrier / declared_field_size`

### Weight band

- `WEIGHT_35_TO_49_999999`
- `WEIGHT_50_TO_54_999999`
- `WEIGHT_55_TO_59_999999`
- `WEIGHT_60_TO_64_999999`
- `WEIGHT_65_TO_80`

### Field-size band

- `FIELD_1_TO_8`
- `FIELD_9_TO_12`
- `FIELD_13_TO_16`
- `FIELD_17_TO_24`
- `FIELD_25_TO_40`

## Selection decisions

`context_parameter_selection_decision` uses:

- `PARAMETER_SELECTED`
- `PARAMETER_NOT_AVAILABLE`
- `CONTEXT_INELIGIBLE`

## Selection status

Published rows use:

- `EXACT_CONTEXT_PARAMETER_SELECTED`
- `EXACT_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `CONTEXT_NOT_ELIGIBLE_FOR_PARAMETER_SELECTION`

## Ineligible rows

When complete context eligibility is not `ELIGIBLE`:

- no parameter registry lookup is performed
- context_parameter_id is blank
- decision is `CONTEXT_INELIGIBLE`
- the eligibility reason code is preserved

## Eligible rows without a registry match

When context is eligible but no exact governed parameter exists:

- context_parameter_id is blank
- decision is `PARAMETER_NOT_AVAILABLE`
- the builder must not select a fallback

## Duplicate registry signatures

More than one governed parameter record for the same exact context signature is
a governance failure.

The builder must fail closed.

## Current population behaviour

When Race Entry Context Eligibility Fact V1 contains zero rows:

- output contains the governed header
- output contains zero data rows
- audit passes

## Deterministic identity

`race_entry_context_parameter_selection_id` is derived from:

- contract version
- race-entry context-eligibility ID
- selected context-parameter ID, or the explicit absence token
- selection decision

## Evidence identity

The evidence SHA-256 is derived from:

- deterministic selection ID
- source eligibility evidence SHA-256
- source context evidence SHA-256
- selected parameter evidence SHA-256 when available
- exact context signature SHA-256
- selection decision
- selection status
- source eligibility reason code

## Prohibited behaviour

The builder must not:

- calculate suitability
- calculate rating adjustments
- calculate adjusted ratings
- calculate EPI
- calculate ERI
- rank runners
- rank races
- calculate fair price
- use market price
- invent parameters
- estimate parameters
- interpolate parameters
- select nearest parameters
- use generic fallback parameters
- silently replace unsupported values
- match horses by name
