# EDGEIQ Lengths Versus Standard Engine V1

## Status

Governed canonical calculation engine.

## Purpose

Lengths Versus Standard Engine V1 converts an established Race Time Delta
Versus Standard value into lengths only when a governed length-conversion
parameter is available.

It must never invent or assume a seconds-per-length value.

## Architecture

Benchmark Observation Fact V1  
→ Benchmark Eligibility Fact V1  
→ Benchmark Accumulation Fact V1  
→ Standard Time Fact V1  
→ Race Time Delta Versus Standard Fact V1  
→ Length Conversion Parameter Fact V1  
→ Lengths Versus Standard Fact V1

## Canonical inputs

Required:

- `public/data/edgeiq_race_time_delta_versus_standard_fact_v1.csv`

Required when Race Time Delta contains data:

- `public/data/edgeiq_length_conversion_parameter_fact_v1.csv`

## Output grain

One row per Race Time Delta row with one matching governed conversion
parameter.

## V1 calculation

Race Time Delta uses:

`time_delta_seconds = winner_race_time_seconds - standard_time_seconds`

Lengths Versus Standard uses:

`lengths_versus_standard = -(time_delta_seconds / seconds_per_length)`

Interpretation:

- positive value: faster than standard
- zero: equal to standard
- negative value: slower than standard

The sign is intentionally inverted from the time delta so that positive
lengths indicate superior performance.

## Conversion matching

A conversion parameter must match the observation's:

- official distance
- conversion model status
- effective-date range

V1 permits the governed scope:

`DISTANCE_EXACT`

The engine must reject:

- multiple matching parameters
- expired parameters
- future parameters
- zero or negative seconds-per-length values
- unsupported scopes
- unavailable parameters
- inferred parameters

## Current population behaviour

When Race Time Delta Fact V1 contains zero rows, Lengths Versus Standard Fact
V1 must be written with the governed header and zero data rows.

The conversion parameter file is not required while there are no time-delta
rows.

This is a valid governed result and must audit as PASS.

## Future fail-closed behaviour

When one or more time-delta rows exist:

- the canonical conversion parameter fact must exist
- every delta row must resolve to exactly one governed parameter
- unresolved rows must stop the build
- ambiguous matches must stop the build

## Deterministic identity

`lengths_versus_standard_id` is derived from:

- contract version
- race time delta ID
- length conversion parameter ID
- calculation method

The evidence hash is derived from:

- lengths-versus-standard ID
- source time delta
- seconds per length
- calculated lengths-versus-standard value

## Prohibited behaviour

The engine must not:

- use a hard-coded seconds-per-length value
- use a commonly quoted racing conversion
- infer a conversion by distance
- interpolate between parameter distances
- extrapolate outside an effective range
- calculate track variants
- calculate condition adjustments
- alter standard time
- alter race time
- remove outliers
- calculate ratings
- calculate EPI
