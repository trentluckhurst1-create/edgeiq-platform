# EDGEiQ Benchmark Engine Readiness V0.1

## Purpose

Phase 1.5 audits whether the immutable warehouse contains sufficient evidence to begin benchmark-engine design.

No benchmark values are calculated in this phase.

## Benchmark hierarchy

The intended hierarchy remains:

1. Track
2. Track and course
3. Track, course and distance
4. Track, course, distance and class
5. Track, course, distance, class and going
6. Track, course, distance, class, going and rail

Each benchmark must retain:

- benchmark ID
- hierarchy level
- sample size
- confidence
- source snapshot
- eligibility rules
- exclusion counts
- benchmark version
- generated timestamp

## Timing convention

Raw official seconds are preserved.

Derived benchmark differences use:

- negative = faster than benchmark
- positive = slower than benchmark

This convention cannot change between engines.

## Evidence restrictions

No benchmark may be built from:

- invalid official times
- missing distance
- abandoned races
- timing inconsistencies
- sectional mismatches
- unresolved race identity
- manually fabricated values

## Next phase

Phase 1.5.1 defines the formal eligibility and hierarchy-fallback contract before benchmark calculation begins.
