# EDGEIQ Horse Performance Rating Fact V1

## Status

Governed canonical historical horse-performance rating layer.

## Purpose

Horse Performance Rating Fact V1 converts each governed Horse Performance
Aggregate Fact row into a stable canonical horse-performance rating record.

V1 applies no additional transformation.

The canonical calculation is:

`horse_performance_rating_value = aggregate_rating_value`

This layer establishes a stable rating contract before any future EPI,
race-context, suitability or prediction engine is introduced.

## Architecture

Horse Performance Observation Fact V1  
→ Horse Performance Aggregation Parameter Fact V1  
→ Horse Performance Aggregate Fact V1  
→ Horse Performance Rating Fact V1  
→ Future Race Context Rating Layer  
→ Future EPI Engine

## Canonical input

`public/data/edgeiq_horse_performance_aggregate_fact_v1.csv`

## Output grain

One row per governed Horse Performance Aggregate Fact row.

## V1 calculation

`horse_performance_rating_value = aggregate_rating_value`

No transformation, scaling, ranking, adjustment, clipping or prediction is
permitted.

## Rating status

Published rows use:

`horse_performance_rating_status = HISTORICAL_HORSE_RATING_GOVERNED`

This status means:

- the rating is derived from governed historical performances
- the rating uses a governed aggregation policy
- the rating is attached to a durable canonical horse identity
- the rating is valid only as at its historical aggregate date
- the rating is not a future-performance forecast
- the rating is not EPI
- the rating is not ERI
- the rating is not today's race rating

## Current population behaviour

When Horse Performance Aggregate Fact V1 contains zero rows:

- the output must contain its governed header
- the output must contain zero data rows
- the audit must PASS

This is a valid governed result.

## Deterministic identity

`horse_performance_rating_id` is derived from:

- contract version
- horse performance aggregate ID
- canonical horse ID
- rating method

## Evidence identity

`horse_performance_rating_evidence_sha256` is derived from:

- horse performance rating ID
- source aggregate evidence SHA-256
- horse-performance rating value
- rating status

## Prohibited behaviour

The builder must not:

- calculate EPI
- calculate ERI
- calculate today's rating
- forecast future performance
- rank horses
- rank races
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
- infer missing aggregate rows
- publish rows without governed aggregate lineage
