# EDGEIQ Race Entry Performance Context Fact V1

## Status

Governed factual declared-race context attachment layer.

## Purpose

Race Entry Performance Context Fact V1 attaches factual declared-race context
to each governed Race Entry Horse Performance Snapshot Fact row.

This layer does not adjust, transform, score, rank or interpret the historical
horse-performance rating.

It establishes the factual context required by future governed suitability and
EPI engines.

## Architecture

Race Entry Horse Performance Snapshot Fact V1  
+ Race Entry Fact V1  
→ Race Entry Performance Context Fact V1  
→ Future Context Parameter Facts  
→ Future Suitability Engines  
→ Future EPI Engine

## Canonical inputs

### Snapshot input

`public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv`

### Race-entry input

`public/data/edgeiq_race_entry_fact_v1.csv`

Race Entry Fact V1 is required only when the snapshot input contains rows.

When the snapshot input contains zero rows:

- Race Entry Fact V1 is not required
- the output must publish its governed header
- the output must contain zero data rows
- the audit must PASS

## Output grain

Exactly one factual context row for every governed snapshot row.

The natural key is:

`race_entry_horse_performance_snapshot_id`

## Required factual context

V1 attaches:

- race entry ID
- race ID
- race date
- runner ID
- canonical horse ID
- canonical horse name
- race distance in metres
- race class code
- track ID
- track name
- track configuration
- track condition
- racing surface
- rail position
- barrier
- allocated weight in kilograms
- declared field size

## Missing context behaviour

When snapshot rows exist, all required V1 context fields must be present in the
governed Race Entry Fact.

The builder must fail closed when a required factual value is missing.

It must not infer, estimate, default or fabricate missing context.

## Historical rating preservation

The selected historical horse-performance rating value is copied unchanged from
the snapshot input.

The canonical relationship is:

`context_historical_rating_value =
selected_horse_performance_rating_value`

No adjustment is permitted.

## Context status

Published rows use:

`race_entry_performance_context_status =
FACTUAL_DECLARED_RACE_CONTEXT_GOVERNED`

## Deterministic identity

`race_entry_performance_context_id` is derived from:

- contract version
- source snapshot ID
- race entry ID
- race ID

## Evidence identity

`race_entry_performance_context_evidence_sha256` is derived from:

- deterministic context ID
- source snapshot evidence SHA-256
- source race-entry evidence SHA-256
- historical rating value
- complete ordered factual context values
- context status

## Prohibited behaviour

The builder must not:

- calculate EPI
- calculate ERI
- calculate suitability
- calculate a context-adjusted rating
- calculate today's rating
- forecast future performance
- rank runners
- rank races
- calculate fair price
- use market price
- interpret class
- interpret distance
- interpret track
- interpret track condition
- interpret surface
- interpret rail position
- interpret barrier
- interpret weight
- interpret field size
- apply class adjustment
- apply distance adjustment
- apply track adjustment
- apply track-condition adjustment
- apply surface adjustment
- apply rail adjustment
- apply race-shape adjustment
- apply pace adjustment
- apply map adjustment
- apply jockey adjustment
- apply trainer adjustment
- apply barrier adjustment
- apply weight adjustment
- apply field-size adjustment
- infer missing values
- use horse name as the join key
