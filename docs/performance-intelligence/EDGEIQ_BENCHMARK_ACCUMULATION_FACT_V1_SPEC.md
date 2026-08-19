# EDGEIQ Benchmark Accumulation Fact V1

## Status

Governed canonical architecture.

## Purpose

Benchmark Accumulation Fact V1 accumulates observations classified as
`STANDARD_TIME_ELIGIBLE` into deterministic benchmark populations.

It performs no statistical calculations.

## Architecture

Provider Evidence  
→ Canonical Racing.com Speed Warehouse V2.1  
→ Benchmark Observation Fact V1  
→ Benchmark Eligibility Fact V1  
→ Benchmark Accumulation Fact V1  
→ Standard Time Engine V1

## Canonical inputs

- `public/data/edgeiq_benchmark_observation_fact_v1.csv`
- `public/data/edgeiq_benchmark_eligibility_fact_v1.csv`

The only permitted join key is:

`benchmark_observation_id`

## Eligibility

Only rows where:

`benchmark_use_class = STANDARD_TIME_ELIGIBLE`

may enter this warehouse.

`SECTIONAL_REFERENCE_ONLY` rows are excluded without modification.

## V1 benchmark grouping

Grouping basis:

`TRACK_DISTANCE`

Governed grouping dimensions:

- `track_name`
- `official_distance_metres`

The following dimensions are unavailable in current source evidence and must
remain blank:

- `course_name`
- `surface`
- `track_condition`

Their corresponding status is:

`NOT_AVAILABLE_IN_SOURCE`

No value may be inferred, defaulted, mapped, estimated, or substituted.

## Normalised warehouse model

### Benchmark Accumulation Fact

Grain:

One row per deterministic benchmark group.

### Benchmark Accumulation Membership Fact

Grain:

One row per eligible observation-to-benchmark-group relationship.

Every eligible observation must belong to exactly one group.

## Readiness governance

Minimum required sample:

`20`

Rules:

- count >= 20 → `benchmark_ready=true`, `accumulation_status=READY`
- count < 20 → `benchmark_ready=false`, `accumulation_status=INSUFFICIENT_SAMPLE`

This is a governance threshold only.

## Deterministic identity

Benchmark group identity is derived from the canonical payload:

- contract version
- benchmark group basis
- track name
- official distance metres

Membership identity is derived from:

- benchmark group ID
- benchmark observation ID

Group membership hash is derived from the complete, deterministically ordered
set of benchmark observation IDs.

## Forbidden calculations

This warehouse must not calculate or store:

- average
- mean
- median
- percentile
- variance
- regression
- weighting
- interpolation
- smoothing
- benchmark time
- standard time
- track variant
- lengths versus standard
- performance rating
- speed rating
- EPI

## Canonical outputs

- `public/data/edgeiq_benchmark_accumulation_fact_v1.csv`
- `public/data/edgeiq_benchmark_accumulation_membership_fact_v1.csv`
- `public/data/edgeiq_benchmark_accumulation_fact_v1_audit.json`

## Required integrity

The independent audit verifies:

- every eligible observation is represented exactly once
- no ineligible observation is represented
- no duplicate benchmark groups
- no duplicate memberships
- deterministic group IDs
- deterministic dimension hashes
- deterministic membership hashes
- correct readiness and status logic
- unavailable dimensions remain blank
- unavailable dimension statuses are explicit
- no statistical fields or calculations
