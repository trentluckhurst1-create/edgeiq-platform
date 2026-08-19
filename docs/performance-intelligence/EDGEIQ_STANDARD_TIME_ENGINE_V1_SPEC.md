# EDGEIQ Standard Time Engine V1

## Status

Governed canonical engine.

## Purpose

Standard Time Engine V1 calculates one canonical standard time for each
benchmark accumulation group that has reached governed readiness.

The engine must never publish a standard time from an insufficient sample.

## Architecture

Provider Evidence  
→ Benchmark Observation Fact V1  
→ Benchmark Eligibility Fact V1  
→ Benchmark Accumulation Fact V1  
→ Standard Time Engine V1  
→ Lengths Versus Standard Engine V1

## Canonical inputs

- `public/data/edgeiq_benchmark_observation_fact_v1.csv`
- `public/data/edgeiq_benchmark_accumulation_fact_v1.csv`
- `public/data/edgeiq_benchmark_accumulation_membership_fact_v1.csv`

## Eligible benchmark groups

A group may enter Standard Time Engine V1 only when all conditions hold:

- `benchmark_ready = true`
- `accumulation_status = READY`
- `eligible_observation_count >= minimum_required_sample`
- membership count equals `eligible_observation_count`
- every membership resolves to one canonical observation
- every included observation has a valid positive `winner_race_time_seconds`

Groups marked `INSUFFICIENT_SAMPLE` must produce no standard-time row.

## V1 methodology

Method:

`MEDIAN_WINNER_RACE_TIME_SECONDS`

For each ready benchmark group:

1. Resolve all governed membership rows.
2. Load the canonical winner race time from Benchmark Observation Fact V1.
3. Sort race times numerically.
4. Calculate the deterministic median.
5. Preserve the sample minimum, maximum and count as evidence boundaries.
6. Round published time fields to six decimal places.

For an odd population, the median is the middle value.

For an even population, the median is the arithmetic mean of the two middle
values.

No weighting, smoothing, interpolation, track variant, condition adjustment,
course inference, or surface inference is permitted.

## Output grain

One row per ready benchmark group.

## Current population behaviour

When no benchmark group is ready, the canonical CSV must still be created with
its governed header and zero data rows.

This is a valid governed result and must audit as PASS.

## Deterministic identity

`standard_time_id` is derived from:

- contract version
- benchmark group ID
- standard time method
- source membership hash

`standard_time_evidence_sha256` is derived from:

- standard time ID
- ordered benchmark observation IDs
- ordered canonical winner race times

## Canonical output

- `public/data/edgeiq_standard_time_fact_v1.csv`
- `public/data/edgeiq_standard_time_fact_v1_audit.json`

## Forbidden behaviour

The engine must not:

- calculate standards from unready groups
- lower the 20-observation threshold
- infer missing dimensions
- substitute sectional times for total race times
- use ineligible observations
- remove outliers
- trim observations
- weight recent races
- weight race class
- weight track condition
- calculate track variants
- calculate lengths versus standard
- calculate runner ratings
- calculate EPI
