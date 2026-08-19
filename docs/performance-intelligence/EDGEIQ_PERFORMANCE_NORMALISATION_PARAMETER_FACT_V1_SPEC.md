# EDGEIQ Performance Normalisation Parameter Fact V1

## Status

Governed canonical parameter registry.

## Purpose

Performance Normalisation Parameter Fact V1 stores approved parameters used by
Performance Normalisation Fact V1.

It supplies:

- centre value
- scale value
- effective-date range
- model version
- evidence lineage

It must not calculate, infer, estimate, backfill, or invent parameters.

## Architecture

Approved Normalisation Evidence  
→ Performance Normalisation Parameter Fact V1  
→ Performance Normalisation Fact V1  
→ Future EPI Engine

## Optional governed source

`config/performance-intelligence/edgeiq_performance_normalisation_parameter_source_v1.csv`

When the governed source does not exist, the canonical parameter fact must be
written with its governed header and zero rows.

This is a valid governed result.

## Source grain

One row per proposed effective normalisation parameter.

## Required source fields

- normalisation_method
- centre_value
- scale_value
- normalisation_model_version
- parameter_status
- effective_from_date
- effective_to_date
- evidence_reference
- evidence_sha256

## Supported V1 method

`LINEAR_CENTRE_AND_SCALE`

Calculation performed downstream:

`normalised_performance_value =
(raw_performance_lengths - centre_value) / scale_value`

## Publication requirements

A source row may be published only when:

- normalisation method is `LINEAR_CENTRE_AND_SCALE`
- centre value is finite
- scale value is finite and greater than zero
- model version is populated
- source parameter status is `APPROVED`
- effective-from date is valid
- effective-to date is blank or not before effective-from
- evidence reference is populated
- evidence SHA-256 is valid lowercase hexadecimal
- no published effective-date overlap exists
- deterministic identity is unique

Published parameter status is normalised to:

`AVAILABLE`

## Current population behaviour

Until approved evidence-backed parameters exist, the canonical output contains
its governed header and zero rows.

The zero-row registry must audit as PASS.

## Deterministic identity

`normalisation_parameter_id` is derived from:

- contract version
- normalisation method
- centre value
- scale value
- normalisation model version
- effective-from date
- effective-to date
- source evidence SHA-256

## Evidence hash

`parameter_evidence_sha256` is derived from:

- deterministic parameter ID
- evidence reference
- source evidence SHA-256

## Prohibited behaviour

The builder must not:

- calculate parameters from the current warehouse population
- calculate a mean
- calculate a median
- calculate a standard deviation
- calculate a robust scale
- use zero as an assumed centre
- use one as an assumed scale
- copy conventional rating parameters
- permit overlapping effective ranges
- publish draft parameters
- calculate normalised performance values
- calculate EPI
- calculate ERI
- calculate ratings
