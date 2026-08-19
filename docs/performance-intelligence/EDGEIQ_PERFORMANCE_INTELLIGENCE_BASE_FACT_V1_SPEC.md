# EDGEIQ Performance Intelligence Base Fact V1

## Status

Governed canonical performance warehouse foundation.

## Purpose

Performance Intelligence Base Fact V1 creates one canonical performance record
for each governed Lengths Versus Standard observation.

It preserves the raw performance result and complete upstream lineage.

It does not calculate EPI, ratings, class adjustments, track variants,
condition adjustments, pace adjustments or projections.

## Architecture

Benchmark Observation Fact V1  
→ Benchmark Eligibility Fact V1  
→ Benchmark Accumulation Fact V1  
→ Standard Time Fact V1  
→ Race Time Delta Versus Standard Fact V1  
→ Length Conversion Parameter Fact V1  
→ Lengths Versus Standard Fact V1  
→ Performance Intelligence Base Fact V1  
→ Future Performance Normalisation Engine  
→ Future EPI Engine

## Canonical input

`public/data/edgeiq_lengths_versus_standard_fact_v1.csv`

## Output grain

One row per governed Lengths Versus Standard row.

## Performance measure

The canonical raw performance measure is:

`raw_performance_lengths = lengths_versus_standard`

Interpretation:

- positive: faster than standard
- zero: equal to standard
- negative: slower than standard

No transformation is permitted in V1.

## Performance status

Every published row has:

`performance_status = OBSERVED_GOVERNED`

This means the result is an observed, auditable historical race performance.

It does not mean the value is a predictive rating.

## Current population behaviour

When Lengths Versus Standard Fact V1 contains zero rows, the canonical output
must be created with its governed header and zero data rows.

This is a valid governed result and must audit as PASS.

## Deterministic identity

`performance_intelligence_base_id` is derived from:

- contract version
- lengths-versus-standard ID
- calculation method

The evidence hash is derived from:

- performance intelligence base ID
- source lengths-versus-standard evidence hash
- raw performance lengths
- raw performance interpretation

## Prohibited behaviour

The builder must not:

- calculate EPI
- calculate ERI
- calculate a speed rating
- calculate a class rating
- calculate a predictive rating
- calculate a track variant
- calculate a condition adjustment
- calculate a pace adjustment
- calculate a weight adjustment
- calculate a barrier adjustment
- calculate a jockey adjustment
- calculate a trainer adjustment
- calculate a recency weighting
- calculate a form weighting
- infer missing upstream results
- publish rows without governed Lengths Versus Standard lineage
