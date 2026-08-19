# EDGEIQ Race Entry Horse Performance Snapshot Fact V1

## Status

Governed point-in-time historical horse-performance snapshot layer.

## Purpose

Race Entry Horse Performance Snapshot Fact V1 attaches the latest eligible
governed historical horse-performance rating to a declared race entry.

It establishes the point-in-time boundary required before any future
race-context, suitability or EPI engine is introduced.

## Architecture

Horse Performance Rating Fact V1  
+ Race Entry Fact V1  
→ Race Entry Horse Performance Snapshot Fact V1  
→ Future Race Context Intelligence  
→ Future EPI Engine

## Canonical inputs

### Horse performance ratings

`public/data/edgeiq_horse_performance_rating_fact_v1.csv`

### Race entries

`public/data/edgeiq_race_entry_fact_v1.csv`

Race Entry Fact V1 is required only when governed Horse Performance Rating Fact
rows exist.

When the horse-rating source contains zero rows, the snapshot builder publishes
a governed header-only output without requiring Race Entry Fact V1.

## Point-in-time rule

For a race entry with race date `D`, an eligible historical rating must satisfy:

`rating_as_of_date < D`

Ratings dated on the race date are excluded because the warehouse does not yet
have governed race-start timestamps capable of proving that the rating existed
before the target race began.

This strict date boundary prevents:

- future leakage
- same-day leakage
- target-race self-inclusion

## Output grain

At most one row per governed race entry.

A row is published only when:

- the race entry has a durable canonical horse ID
- at least one eligible governed historical rating exists
- the latest eligible rating can be selected deterministically

Race entries with no eligible historical rating do not receive an invented
rating row.

## Latest eligible rating selection

For each race entry:

1. match on durable `canonical_horse_id`
2. retain ratings where `rating_as_of_date < race_date`
3. order by `rating_as_of_date` descending
4. use `horse_performance_rating_id` descending as deterministic tie-break
5. select the first row

## Point-in-time historical metrics

The snapshot publishes:

- latest eligible historical rating
- selected rating date
- rating age in calendar days
- eligible historical rating count
- first eligible rating date
- highest eligible historical rating
- lowest eligible historical rating
- arithmetic mean eligible historical rating
- selected rating observation count

All metrics are derived only from ratings eligible before the target race date.

## Profile Fact exclusion

Horse Performance Profile Fact V1 is deliberately not an input.

The profile is a current full-history consolidation and may include ratings
dated after a historical target race.

Using it in a historical race-entry snapshot could introduce future leakage.

## Snapshot status

Published rows use:

`race_entry_horse_performance_snapshot_status =
POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE`

## Current population behaviour

When Horse Performance Rating Fact V1 contains zero rows:

- Race Entry Fact V1 is not required
- the output contains its governed header
- the output contains zero data rows
- the audit must PASS

## Deterministic identity

`race_entry_horse_performance_snapshot_id` is derived from:

- contract version
- race entry ID
- selected horse-performance rating ID
- race date

## Evidence identity

`race_entry_horse_performance_snapshot_evidence_sha256` is derived from:

- deterministic snapshot ID
- source race-entry evidence SHA-256
- selected rating evidence SHA-256
- ordered eligible rating evidence SHA-256
- selected rating value
- eligible rating count
- rating age in days
- snapshot status

## Prohibited behaviour

The builder must not:

- calculate EPI
- calculate ERI
- calculate suitability
- calculate a forecast rating
- calculate today's adjusted rating
- use ratings dated on or after the race date
- use Horse Performance Profile Fact V1
- rank runners
- rank races
- calculate fair price
- use market price
- apply class adjustment
- apply distance adjustment
- apply track adjustment
- apply track-condition adjustment
- apply race-shape adjustment
- apply pace adjustment
- apply map adjustment
- apply jockey adjustment
- apply trainer adjustment
- apply barrier adjustment
- apply weight-carried adjustment
- apply preparation-stage adjustment
- apply fitness adjustment
- infer a rating where none exists
- match horses by name
