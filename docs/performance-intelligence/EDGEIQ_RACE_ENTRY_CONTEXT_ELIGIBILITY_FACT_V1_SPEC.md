# EDGEIQ Race Entry Context Eligibility Fact V1

## Status

Governed deterministic context-eligibility decision layer.

## Purpose

Race Entry Context Eligibility Fact V1 determines whether each governed Race
Entry Performance Context Fact row contains sufficient factual context to enter
future context parameter and suitability engines.

This layer does not calculate:

- suitability
- adjustments
- EPI
- ERI
- ranking
- prediction
- fair price

## Architecture

Race Entry Performance Context Fact V1  
→ Race Entry Context Eligibility Fact V1  
→ Future Context Parameter Facts  
→ Future Suitability Facts  
→ Future EPI Engine

## Canonical input

`public/data/edgeiq_race_entry_performance_context_fact_v1.csv`

## Output grain

Exactly one eligibility row per governed race-entry performance-context row.

The natural key is:

`race_entry_performance_context_id`

## Eligibility dimensions

V1 publishes deterministic decisions for:

- historical rating eligibility
- distance-context eligibility
- class-context eligibility
- track-context eligibility
- track-configuration eligibility
- track-condition eligibility
- surface eligibility
- rail-context eligibility
- barrier-context eligibility
- allocated-weight eligibility
- field-size eligibility
- complete context eligibility

## Decision values

Dimension decisions use:

- `ELIGIBLE`
- `INELIGIBLE_MISSING_CONTEXT`
- `INELIGIBLE_INVALID_CONTEXT`
- `INELIGIBLE_UNSUPPORTED_CONTEXT`

## Current V1 support rules

### Historical rating

Eligible when:

- the value is finite

### Distance

Eligible when:

- distance is a positive integer
- distance is between 400 and 5000 metres inclusive

Values outside the supported range are not rewritten or estimated.

### Class

Eligible when:

- race class code is present

V1 does not interpret class hierarchy.

### Track

Eligible when:

- track ID is present
- track name is present

### Track configuration

Eligible when:

- track configuration is present

### Track condition

Eligible when the normalised governed value is one of:

- FIRM
- GOOD
- SOFT
- HEAVY
- SYNTHETIC

Numeric condition variants are permitted when their condition family is
recognisable, including:

- FIRM 1
- FIRM 2
- GOOD 3
- GOOD 4
- SOFT 5
- SOFT 6
- SOFT 7
- HEAVY 8
- HEAVY 9
- HEAVY 10

The source value is preserved unchanged.

### Racing surface

Eligible when the normalised governed value is one of:

- TURF
- SYNTHETIC

### Rail position

Eligible when:

- a factual rail-position value is present

V1 does not interpret rail advantage or disadvantage.

### Barrier

Eligible when:

- barrier is a positive integer
- barrier does not exceed declared field size

### Allocated weight

Eligible when:

- allocated weight is finite
- allocated weight is greater than zero
- allocated weight is between 35 and 80 kilograms inclusive

### Field size

Eligible when:

- declared field size is a positive integer
- declared field size is no greater than 40

## Complete context eligibility

Complete context is `ELIGIBLE` only when every V1 dimension is eligible.

Otherwise complete context is ineligible.

## Primary reason code

The primary reason code is selected in this fixed order:

1. historical rating
2. distance
3. class
4. track
5. track configuration
6. track condition
7. surface
8. rail position
9. barrier
10. allocated weight
11. field size

If all dimensions are eligible:

`ALL_REQUIRED_CONTEXT_ELIGIBLE`

## Eligibility status

Published rows use:

- `COMPLETE_CONTEXT_ELIGIBLE`
- `COMPLETE_CONTEXT_INELIGIBLE`

## Missing-value behaviour

The builder must not:

- infer missing context
- default missing context
- estimate unsupported values
- rewrite source values
- map unknown conditions to known conditions
- map unknown surfaces to known surfaces

## Current population behaviour

When Race Entry Performance Context Fact V1 contains zero rows:

- the output contains its governed header
- the output contains zero data rows
- the audit must PASS

## Deterministic identity

`race_entry_context_eligibility_id` is derived from:

- contract version
- race-entry performance-context ID

## Evidence identity

The evidence SHA-256 is derived from:

- deterministic eligibility ID
- source context evidence SHA-256
- all dimension decisions
- complete-context decision
- primary reason code
- eligibility status

## Prohibited behaviour

The builder must not:

- calculate EPI
- calculate ERI
- calculate suitability
- calculate a rating adjustment
- calculate a context-adjusted rating
- rank runners
- rank races
- calculate fair price
- use market price
- infer missing values
- estimate unsupported values
- apply class adjustment
- apply distance adjustment
- apply track adjustment
- apply condition adjustment
- apply surface adjustment
- apply rail adjustment
- apply barrier adjustment
- apply weight adjustment
- apply field-size adjustment
- apply jockey adjustment
- apply trainer adjustment
- apply pace adjustment
- apply map adjustment
