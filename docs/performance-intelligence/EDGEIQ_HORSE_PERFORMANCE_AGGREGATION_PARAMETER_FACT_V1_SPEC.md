# EDGEIQ Horse Performance Aggregation Parameter Fact V1

## Status

Governed canonical horse-performance aggregation policy registry.

## Purpose

Horse Performance Aggregation Parameter Fact V1 stores explicitly approved
parameters for future horse-level performance aggregation.

It defines the policy governing:

- aggregation method
- maximum observations
- lookback period
- minimum observations
- recency-weighting method
- optional recency half-life
- effective-date range
- model version
- evidence lineage

The registry does not aggregate horse performances.

## Architecture

Approved Aggregation Policy Evidence  
→ Horse Performance Aggregation Parameter Fact V1  
→ Future Horse Performance Aggregate Fact V1  
→ Future EPI Engine

## Optional governed source

`config/performance-intelligence/edgeiq_horse_performance_aggregation_parameter_source_v1.csv`

When the source does not exist, the canonical parameter fact must contain its
governed header and zero rows.

This is a valid governed result and must audit as PASS.

## Supported V1 aggregation methods

- `ARITHMETIC_MEAN`
- `WEIGHTED_ARITHMETIC_MEAN`

## Supported V1 recency methods

- `NONE`
- `EXPONENTIAL_HALF_LIFE`

## Publication rules

A parameter may be published only when:

- source status is `APPROVED`
- aggregation method is supported
- maximum observations is a positive integer
- lookback days is a positive integer
- minimum observations is a positive integer
- minimum observations does not exceed maximum observations
- recency method is supported
- `NONE` has no half-life value
- `EXPONENTIAL_HALF_LIFE` has a positive half-life value
- model version is populated
- effective dates are valid
- effective ranges do not overlap
- evidence reference is populated
- evidence SHA-256 is valid

Published status is:

`AVAILABLE`

## Current population behaviour

Until an aggregation policy has been approved and evidenced, the canonical
output must contain zero data rows.

The engine must not select conventional values merely to populate the registry.

## Prohibited behaviour

The builder must not:

- select a lookback period
- select a maximum number of runs
- select a minimum number of runs
- select a recency-decay rate
- infer parameters from industry convention
- infer parameters from the current warehouse
- aggregate horse performances
- calculate EPI
- calculate ERI
- calculate a predictive rating
- publish draft parameters
- permit overlapping effective-date ranges
