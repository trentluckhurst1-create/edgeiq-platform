# EDGEIQ Horse Performance Observation Fact V1

## Status

Governed canonical horse-performance observation layer.

## Purpose

Horse Performance Observation Fact V1 assigns every governed Performance
Rating Base observation to a durable canonical horse identity.

This layer must exist before:

- horse-level performance aggregation
- recency modelling
- reliability modelling
- preparation profiling
- EPI calculation

Horse names must not be used as durable aggregation keys.

## Architecture

Performance Rating Base Fact V1  
→ Governed Horse Identity Map V1  
→ Horse Performance Observation Fact V1  
→ Future Horse Performance Aggregation  
→ Future EPI Engine

## Required rating input

`public/data/edgeiq_performance_rating_base_fact_v1.csv`

## Identity input required when rating rows exist

`config/performance-intelligence/edgeiq_horse_performance_identity_map_v1.csv`

## Identity-map grain

One row per governed source horse identity.

Required fields:

- source_horse_name
- canonical_horse_id
- canonical_horse_name
- identity_status
- evidence_reference
- evidence_sha256

Only rows with:

`identity_status = APPROVED`

may be used.

## Output grain

One row per governed Performance Rating Base observation with exactly one
approved canonical horse identity.

## Current population behaviour

When Performance Rating Base Fact V1 contains zero rows:

- the identity map is not required
- the output must contain its governed header
- the output must contain zero data rows
- the audit must PASS

## Identity matching

V1 permits exact normalized-name matching only.

Normalization is limited to:

- trim leading and trailing whitespace
- collapse repeated internal whitespace
- Unicode case folding

V1 must not use:

- fuzzy matching
- edit-distance matching
- phonetic matching
- partial matching
- alias inference
- punctuation removal
- country-code assumptions
- date-of-birth inference
- breeding inference

## Deterministic identity

`horse_performance_observation_id` is derived from:

- contract version
- performance rating base ID
- canonical horse ID
- identity method

## Prohibited behaviour

The builder must not:

- aggregate performances
- calculate EPI
- calculate ERI
- calculate a horse rating
- calculate a predictive value
- infer horse identity from similar names
- use horse name as the canonical key
- create synthetic horse IDs
- publish ambiguous identity matches
- publish unmatched rating observations
