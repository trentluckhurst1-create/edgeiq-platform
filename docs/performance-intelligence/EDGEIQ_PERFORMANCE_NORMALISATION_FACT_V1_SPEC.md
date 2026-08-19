# EDGEIQ Performance Normalisation Fact V1

## Status

Governed canonical normalisation layer.

## Purpose

Performance Normalisation Fact V1 prepares governed historical performance
observations for future rating calculation.

It consumes Performance Intelligence Base Fact V1 and publishes a normalised
performance value only when a governed normalisation parameter is available.

It must not invent a population mean, standard deviation, scale, centre,
weighting, or rating.

## Architecture

Performance Intelligence Base Fact V1  
→ Performance Normalisation Parameter Fact V1  
→ Performance Normalisation Fact V1  
→ Future EPI Engine

## Canonical inputs

Required:

- `public/data/edgeiq_performance_intelligence_base_fact_v1.csv`

Required when base rows exist:

- `public/data/edgeiq_performance_normalisation_parameter_fact_v1.csv`

## Output grain

One row per Performance Intelligence Base Fact row with exactly one matching
governed normalisation parameter.

## V1 method

Supported method:

`LINEAR_CENTRE_AND_SCALE`

Calculation:

`normalised_performance_value =
(raw_performance_lengths - centre_value) / scale_value`

Requirements:

- scale value must be positive
- one parameter must match the performance date
- parameter status must be AVAILABLE
- parameter method must be LINEAR_CENTRE_AND_SCALE

## Current population behaviour

When Performance Intelligence Base Fact V1 has zero rows, the canonical
normalisation fact must be written with its governed header and zero data rows.

The parameter fact is not required while there are no base rows.

This is a valid governed result and must audit as PASS.

## Prohibited behaviour

The engine must not:

- calculate EPI
- calculate ERI
- infer a mean
- infer a standard deviation
- use a hard-coded centre
- use a hard-coded scale
- normalise against the current incomplete population
- calculate class adjustments
- calculate track variants
- calculate condition adjustments
- calculate recency weights
- calculate predictive ratings
