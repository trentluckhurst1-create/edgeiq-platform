# EDGEiQ Benchmark Eligibility Fact V1

## Status

GOVERNED SPECIFICATION

## Purpose

Classify every governed Benchmark Observation Fact V1 row according to its
permitted future benchmark use.

This component is an eligibility and governance layer only.

It must not calculate:

- standard times
- average times
- median times
- benchmark values
- ratings
- lengths versus standard
- pace scores
- EPI
- ERI

## Architectural Position

Canonical Speed Warehouse V2.1
→ Benchmark Observation Fact V1
→ Benchmark Eligibility Fact V1
→ future Standard Time Engine V1

## Authoritative Input

- public/data/edgeiq_benchmark_observation_fact_v1.csv
- public/data/edgeiq_benchmark_observation_fact_v1_audit.json

No provider data or earlier warehouse layer may be consumed directly.

## Grain

One row per benchmark_observation_id.

## Benchmark Use Classes

### STANDARD_TIME_ELIGIBLE

The observation may be consumed by a future whole-race Standard Time Engine.

Required:

- observation_status = COMPLETE
- evidence_complete = true
- race_split_coverage_type = FULL_RACE
- race identity present
- track present
- official distance greater than zero
- winner identity present
- winner race time greater than zero
- runner count at least 2
- unresolved runner coverage count = 0

### SECTIONAL_REFERENCE_ONLY

The observation cannot be used for whole-race standard-time calculation but may
remain available for governed sectional research.

Required:

- observation_status = COMPLETE
- evidence_complete = true
- race_split_coverage_type = PARTIAL_TIMING_WINDOW
- race identity present
- track present
- governed partial split-window identity is present
- winner identity present
- winner race time greater than zero
- runner count at least 2
- unresolved runner coverage count = 0
- at least one exact winner closing sectional is available

A complete official race distance is not required for
SECTIONAL_REFERENCE_ONLY classification. A partial timing window must never be
represented as the complete official race distance.

### INELIGIBLE

The observation fails one or more required eligibility rules.

Every failed rule must be recorded explicitly.

## Governance Rules

1. Every Benchmark Observation Fact V1 row produces exactly one eligibility row.
2. No observations may be silently dropped.
3. Eligibility must be deterministic.
4. Eligibility reasons must be explicit.
5. Partial timing-window observations must never become standard-time eligible.
6. Unresolved coverage must never become eligible.
7. Missing values must not be inferred.
8. No thresholds may be hidden in React.
9. Input and output hashes must be recorded.
10. Output ordering must be deterministic.

## Outputs

- public/data/edgeiq_benchmark_eligibility_fact_v1.csv
- public/data/edgeiq_benchmark_eligibility_fact_v1_audit.json

## PASS Marker

EDGEIQ_BENCHMARK_ELIGIBILITY_FACT_V1_AUDIT_PASS
