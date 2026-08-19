# EDGEIQ Horse Performance Profile Fact V1

## Status

Governed canonical historical horse-performance profile layer.

## Purpose

Horse Performance Profile Fact V1 consolidates governed historical Horse
Performance Rating Fact records into one durable profile per canonical horse.

The profile describes the governed rating history available for each horse.

It does not predict future performance and does not calculate EPI.

## Architecture

Horse Performance Aggregate Fact V1  
→ Horse Performance Rating Fact V1  
→ Horse Performance Profile Fact V1  
→ Future Race Context Layer  
→ Future EPI Engine

## Canonical input

`public/data/edgeiq_horse_performance_rating_fact_v1.csv`

## Output grain

One row per durable `canonical_horse_id`.

Horse name is descriptive only.

The durable warehouse key is:

`canonical_horse_id`

## V1 historical profile metrics

For every canonical horse:

- historical rating count
- first governed rating date
- latest governed rating date
- latest historical horse-performance rating
- highest historical horse-performance rating
- lowest historical horse-performance rating
- arithmetic mean historical horse-performance rating
- latest included observation count
- maximum included observation count
- minimum included observation count
- total included observation count

## Latest rating selection

The latest historical rating is selected by:

1. latest `rating_as_of_date`
2. deterministic `horse_performance_rating_id` ascending as tie-break

Multiple rating rows for the same horse and date are permitted only when their
source aggregate lineage is distinct.

## Average rating

`average_historical_rating_value =
sum(horse_performance_rating_value) / historical_rating_count`

The profile average is descriptive only.

It is not a predictive rating.

## Profile status

Published rows use:

`horse_performance_profile_status =
HISTORICAL_HORSE_PROFILE_GOVERNED`

## Current population behaviour

When Horse Performance Rating Fact V1 contains zero rows:

- the output must contain its governed header
- the output must contain zero data rows
- the audit must PASS

This is a valid governed result.

## Deterministic identity

`horse_performance_profile_id` is derived from:

- contract version
- canonical horse ID
- ordered Horse Performance Rating Fact IDs

## Evidence identity

`horse_performance_profile_evidence_sha256` is derived from:

- deterministic profile ID
- ordered source rating evidence SHA-256 values
- historical rating count
- first governed rating date
- latest governed rating date
- latest rating value
- highest rating value
- lowest rating value
- average rating value
- profile status

## Prohibited behaviour

The builder must not:

- calculate EPI
- calculate ERI
- predict future performance
- calculate today's race rating
- rank horses
- rank races
- infer missing rating history
- use horse name as a durable key
- merge horses by fuzzy name
- apply class adjustment
- apply distance adjustment
- apply track adjustment
- apply track-condition adjustment
- apply race-shape adjustment
- apply pace adjustment
- apply jockey adjustment
- apply trainer adjustment
- apply barrier adjustment
- apply weight-carried adjustment
- apply preparation-stage adjustment
- apply fitness adjustment
- apply suitability adjustment
- infer confidence
- infer reliability
