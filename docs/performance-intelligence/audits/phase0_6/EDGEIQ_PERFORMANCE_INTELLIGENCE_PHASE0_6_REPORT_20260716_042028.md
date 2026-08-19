# EDGEiQ Performance Intelligence
## Phase 0.6 Sectional Linkage Diagnosis

Generated UTC: `2026-07-15T18:20:28.945057+00:00`

## Finding

Phase 0.5 produced zero sectional links because the assumed provider-ID and composite field names were not shared by both source files.

This is a schema-contract mismatch, not evidence that the records cannot be linked.

## Candidate linkage tests

| Candidate | Strength | Exact matches | Exact % | Ambiguous | Unmatched |
|---|---|---:|---:|---:|---:|
| DATE_TRACK_RACE_AND_HORSE | STRONG | 0 | 0.0 | 0 | 130484 |
| DATE_HORSE_ONLY | UNSAFE_WITHOUT_UNIQUENESS | 105580 | 80.9141 | 119 | 24785 |

## Governance rule

Only unique deterministic matches may be promoted automatically.

Ambiguous matches must remain unresolved until stronger identity evidence exists.

Name-only or date-and-horse matches must never be silently promoted without uniqueness and supporting race evidence.
