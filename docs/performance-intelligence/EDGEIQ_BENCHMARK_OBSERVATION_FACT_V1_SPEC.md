# EDGEiQ Benchmark Observation Fact V1

## Status

GOVERNED SPECIFICATION

## Component

Benchmark Observation Fact V1

## Purpose

Create one immutable benchmark observation row per canonical race from the
EDGEiQ Racing.com Canonical Speed Warehouse V2.1.

This component records evidence only.

It must not calculate:

- standard times
- benchmark averages
- ratings
- lengths versus standard
- pace scores
- performance scores
- EPI
- ERI
- subjective confidence values

## Architectural Position

Canonical Speed Warehouse V2.1
→ Benchmark Observation Fact V1
→ future Standard Time Engine
→ future Lengths versus Standard Engine
→ future Performance Intelligence Engine

## Authoritative Inputs

- public/data/edgeiq_racingcom_canonical_race_speed_fact_v2_1.csv
- public/data/edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv
- public/data/edgeiq_racingcom_canonical_runner_sectional_fact_v2_1.csv
- public/data/edgeiq_racingcom_canonical_runner_split_fact_v2_1.csv
- public/data/edgeiq_racingcom_canonical_speed_warehouse_v2_1_audit.json

No provider payload may be consumed directly.

## Grain

One row per race_key.

## Required Governance Rules

1. Every race in the canonical race fact must produce exactly one observation.
2. Every observation must have a unique benchmark_observation_id.
3. No unresolved split coverage is allowed.
4. Runner counts must reconcile to the canonical runner fact.
5. Winner identity must be supported by canonical runner facts.
6. Winner timing fields must be copied without mathematical transformation.
7. Missing facts must remain null or blank.
8. No race distance may be invented.
9. No course, surface, rail, class, or track condition may be invented.
10. Output ordering must be deterministic.
11. Input and output file hashes must be recorded.
12. The builder must fail closed if the canonical V2.1 audit is not PASS.

## Coverage Semantics

Allowed split coverage classifications:

- FULL_RACE
- PARTIAL_TIMING_WINDOW

UNRESOLVED is prohibited.

Race-level coverage is classified as:

- FULL_RACE
- PARTIAL_TIMING_WINDOW
- MIXED
- UNRESOLVED

MIXED is allowed only when canonical runners within the same race legitimately
contain more than one resolved coverage type.

## Winner Determination

The winner is identified from canonical runner fields where an explicit finish
position equal to 1 is available.

The builder may inspect known canonical aliases, but it must not infer the
winner from the fastest recorded time when an explicit winner field is absent.

If no explicit winner can be identified:

- winner fields remain blank
- observation_status becomes INCOMPLETE_WINNER_IDENTITY
- the audit records the incomplete observation

## Closing Sectionals

Winner closing sectionals may be populated only from exact canonical markers:

- 600 metres
- 400 metres
- 200 metres

No interpolation is permitted.

## Observation Status

Allowed values:

- COMPLETE
- INCOMPLETE_WINNER_IDENTITY
- INCOMPLETE_WINNER_TIME
- INCOMPLETE_RACE_IDENTITY
- UNRESOLVED_COVERAGE

A row may remain governed evidence even when optional provider facts are absent,
but unresolved timing semantics are prohibited.

## Outputs

- public/data/edgeiq_benchmark_observation_fact_v1.csv
- public/data/edgeiq_benchmark_observation_fact_v1_audit.json

## PASS Marker

EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1_AUDIT_PASS
