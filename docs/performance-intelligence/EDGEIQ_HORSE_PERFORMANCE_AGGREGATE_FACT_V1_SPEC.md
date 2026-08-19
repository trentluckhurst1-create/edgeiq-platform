# EDGEIQ Horse Performance Aggregate Fact V1

## Status

Governed canonical historical horse-performance aggregation layer.

## Purpose

Horse Performance Aggregate Fact V1 aggregates governed historical horse
performance observations using an effective, evidence-backed aggregation
parameter.

It creates a historical aggregate as at each governed horse-performance
observation date.

It does not calculate EPI and does not predict a future performance.

## Architecture

Horse Performance Observation Fact V1  
→ Horse Performance Aggregation Parameter Fact V1  
→ Horse Performance Aggregate Fact V1  
→ Future Horse Performance Rating Fact  
→ Future EPI Engine

## Canonical inputs

- `public/data/edgeiq_horse_performance_observation_fact_v1.csv`
- `public/data/edgeiq_horse_performance_aggregation_parameter_fact_v1.csv`

## Output grain

One row per:

- canonical horse
- aggregate as-of race date
- effective aggregation parameter

An aggregate row is published only when the governed minimum-observation
requirement is met.

## Observation eligibility

For each horse and aggregate as-of date:

1. use only observations for the same canonical horse
2. use observations dated on or before the aggregate as-of date
3. apply the governed lookback period
4. order observations by race date descending
5. use no more than the governed maximum observations
6. require at least the governed minimum observations

## Supported aggregation methods

### ARITHMETIC_MEAN

`aggregate_rating_value = sum(rating_base_value) / observation_count`

The required recency method is:

`NONE`

Every included observation has weight `1`.

### WEIGHTED_ARITHMETIC_MEAN

The required recency method is:

`EXPONENTIAL_HALF_LIFE`

For each included observation:

`age_days = aggregate_as_of_date - race_date`

`weight = 0.5 ** (age_days / recency_half_life_days)`

Then:

`aggregate_rating_value =
sum(rating_base_value * weight) / sum(weight)`

## Current population behaviour

When Horse Performance Observation Fact V1 contains zero rows:

- no aggregation parameter is required for population
- the output must contain its governed header
- the output must contain zero data rows
- the audit must PASS

When observations exist but no effective governed parameter exists, the builder
must fail closed.

## Aggregate status

Published rows use:

`aggregate_status = HISTORICAL_AGGREGATE_GOVERNED`

This status does not imply:

- prediction
- suitability for today's race
- EPI
- ERI
- form momentum
- current fitness
- expected performance

## Deterministic identity

`horse_performance_aggregate_id` is derived from:

- contract version
- canonical horse ID
- aggregate as-of date
- aggregation parameter ID
- ordered included observation IDs

## Evidence identity

`horse_performance_aggregate_evidence_sha256` is derived from:

- deterministic aggregate ID
- source parameter evidence SHA-256
- ordered observation evidence SHA-256 values
- aggregate rating value
- total weight
- observation count
- aggregate status

## Prohibited behaviour

The builder must not:

- calculate EPI
- calculate ERI
- forecast the next start
- use future observations
- use observations outside the governed lookback
- exceed maximum observations
- publish below the minimum-observation threshold
- infer an aggregation parameter
- use horse name as the aggregation key
- apply class adjustment
- apply distance adjustment
- apply track adjustment
- apply condition adjustment
- apply jockey adjustment
- apply trainer adjustment
- apply barrier adjustment
- apply weight-carried adjustment
- apply preparation-stage adjustment
