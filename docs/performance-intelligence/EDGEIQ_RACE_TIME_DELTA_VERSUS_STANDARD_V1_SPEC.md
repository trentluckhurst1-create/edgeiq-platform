# EDGEIQ Race Time Delta Versus Standard V1

## Status

Governed canonical calculation engine.

## Purpose

Race Time Delta Versus Standard V1 compares each eligible benchmark
observation with its canonical Standard Time Fact V1 record.

It calculates the exact time difference in seconds.

It does not convert seconds into lengths.

## Architecture

Benchmark Observation Fact V1  
→ Benchmark Eligibility Fact V1  
→ Benchmark Accumulation Fact V1  
→ Standard Time Fact V1  
→ Race Time Delta Versus Standard Fact V1  
→ Governed Length Conversion Engine  
→ Lengths Versus Standard Fact

## Canonical inputs

- `public/data/edgeiq_benchmark_observation_fact_v1.csv`
- `public/data/edgeiq_benchmark_eligibility_fact_v1.csv`
- `public/data/edgeiq_benchmark_accumulation_membership_fact_v1.csv`
- `public/data/edgeiq_standard_time_fact_v1.csv`

## Output grain

One row per standard-time-eligible observation with an available canonical
standard time.

## V1 calculation

`time_delta_seconds = winner_race_time_seconds - standard_time_seconds`

Interpretation:

- negative value: faster than standard
- zero: equal to standard
- positive value: slower than standard

The published value is rounded to six decimal places.

## Current population behaviour

When Standard Time Fact V1 contains zero available standards, the canonical
output must be written with its governed header and zero data rows.

This is a valid governed result and must audit as PASS.

## Deterministic identity

`race_time_delta_id` is derived from:

- contract version
- benchmark observation ID
- standard time ID
- calculation method

The evidence hash is derived from:

- race time delta ID
- source winner race time
- source standard time
- calculated time delta

## Prohibited behaviour

The engine must not:

- calculate against an unavailable standard
- calculate against an insufficient benchmark group
- infer a standard
- lower the benchmark sample threshold
- remove observations
- trim outliers
- calculate track variants
- calculate condition adjustments
- convert seconds to lengths
- use a fixed seconds-per-length constant
- calculate ratings
- calculate EPI
