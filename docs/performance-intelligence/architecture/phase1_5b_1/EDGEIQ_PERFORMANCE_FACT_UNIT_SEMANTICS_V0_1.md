# EDGEiQ Performance-Fact Unit Semantics V0.1

## Winning-time rule

A numeric source value must never be labelled as seconds until its source unit has been validated.

The historical GraphQL warehouse may encode winning time in integer centiseconds.

Example:

`12383` represents `123.83 seconds` when the unit is centiseconds.

## Required fields

The corrected performance-facts warehouse must retain both:

- `official_winning_time_raw`
- `official_winning_time_source_unit`
- `official_winning_time_seconds`

## Immutability

The existing Phase 1.5B snapshot is not overwritten.

A corrected snapshot supersedes it while preserving the original snapshot and audit lineage.

## Benchmark boundary

No race-time benchmark may consume an unresolved or mislabelled time field.
