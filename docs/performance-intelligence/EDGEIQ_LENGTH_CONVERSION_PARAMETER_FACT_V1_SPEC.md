# EDGEIQ Length Conversion Parameter Fact V1

## Status

Governed canonical parameter registry.

## Purpose

Length Conversion Parameter Fact V1 stores evidence-backed parameters used to
convert time differences in seconds into racing lengths.

The registry must not manufacture, assume, interpolate or copy an unverified
seconds-per-length value.

## Architecture

Governed Conversion Evidence  
→ Length Conversion Parameter Fact V1  
→ Lengths Versus Standard Engine V1

## Source registry

Optional governed source:

`config/performance-intelligence/edgeiq_length_conversion_parameter_source_v1.csv`

When the source file is absent, the canonical parameter fact must be written
with its governed header and zero rows.

This is a valid governed result.

## Source grain

One row per proposed exact-distance conversion parameter.

## Required source fields

- conversion_scope
- official_distance_metres
- seconds_per_length
- conversion_model_version
- parameter_status
- effective_from_date
- effective_to_date
- evidence_reference
- evidence_sha256

## Supported V1 scope

`DISTANCE_EXACT`

V1 does not permit:

- distance bands
- interpolation
- extrapolation
- track-specific assumptions
- surface assumptions
- condition assumptions
- class assumptions
- pace assumptions
- sectional assumptions

## Publication requirements

A source row may be published only when:

- conversion scope is `DISTANCE_EXACT`
- official distance is a positive integer
- seconds per length is positive
- parameter status is `APPROVED`
- effective-from date is valid
- effective-to date is blank or not earlier than effective-from
- evidence reference is populated
- evidence SHA-256 is a valid lowercase hexadecimal SHA-256
- no effective-date overlap exists for the same exact distance
- the deterministic identity is unique

Published status is normalised to:

`AVAILABLE`

## Current population behaviour

Until approved evidence-backed parameters exist, the canonical output contains
its governed header and zero rows.

The zero-row registry must audit as PASS.

## Deterministic identity

`length_conversion_parameter_id` is derived from:

- contract version
- conversion scope
- official distance
- seconds per length
- conversion model version
- effective-from date
- effective-to date
- evidence SHA-256

## Prohibited behaviour

The builder must not:

- hard-code a conversion parameter
- use a conventional racing approximation
- infer seconds per length from horse speed
- derive parameters from the current 39-row benchmark population
- interpolate between distances
- reuse an expired parameter
- publish unapproved evidence
- overwrite source evidence
- calculate lengths versus standard
- calculate performance ratings
- calculate EPI
