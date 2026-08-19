# EDGEIQ Performance Rating Base Fact V1

## Status

Governed canonical rating foundation.

## Purpose

Performance Rating Base Fact V1 converts each governed Performance
Normalisation Fact observation into a canonical rating-base record.

V1 does not transform the normalised value.

The canonical rating-base value is:

`rating_base_value = normalised_performance_value`

This layer exists to establish:

- rating identity
- rating lineage
- observation status
- model-version lineage
- a stable contract for future rating engines

It does not calculate EPI.

## Architecture

Performance Intelligence Base Fact V1  
→ Performance Normalisation Parameter Fact V1  
→ Performance Normalisation Fact V1  
→ Performance Rating Base Fact V1  
→ Future Performance Rating Engine  
→ Future Horse Performance Aggregation  
→ Future EPI Engine

## Canonical input

`public/data/edgeiq_performance_normalisation_fact_v1.csv`

## Output grain

One row per governed Performance Normalisation Fact row.

## V1 calculation

`rating_base_value = normalised_performance_value`

No transformation, centring, scaling, clipping, ranking or weighting is
permitted in V1.

## Rating status

Every published row has:

`rating_status = OBSERVED_NORMALISED_GOVERNED`

This means:

- the row represents an observed historical performance
- the source performance was governed
- the source performance was normalised using a governed parameter
- the value is not a forecast
- the value is not a final EPI

## Current population behaviour

When Performance Normalisation Fact V1 contains zero rows, the canonical
Performance Rating Base Fact must contain its governed header and zero data
rows.

This is a valid governed result and must audit as PASS.

## Deterministic identity

`performance_rating_base_id` is derived from:

- contract version
- performance normalisation ID
- rating method

## Evidence identity

`performance_rating_base_evidence_sha256` is derived from:

- performance rating base ID
- source performance normalisation evidence SHA-256
- rating base value
- rating status

## Prohibited behaviour

The builder must not:

- calculate EPI
- calculate ERI
- aggregate multiple performances
- rank horses
- rank races
- apply recency weighting
- apply reliability weighting
- apply class weighting
- apply distance weighting
- apply track weighting
- apply condition weighting
- apply jockey adjustments
- apply trainer adjustments
- apply barrier adjustments
- apply weight-carried adjustments
- calculate predictive ratings
- calculate today ratings
- infer missing normalisation rows
- publish rows without governed lineage
