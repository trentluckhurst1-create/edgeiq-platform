# EDGEiQ Performance Intelligence Production Program V1

## Production Order

1. Historical source ingestion
2. Historical identity
3. Standard Times
4. Lengths v Standard
5. Runner sectional performance
6. Early speed
7. Late speed
8. Performance Intelligence base
9. Performance normalisation parameters
10. Performance normalisation
11. Horse performance identity map
12. Horse aggregation parameters
13. Performance rating base
14. Horse observations
15. Rolling horse aggregates
16. Horse performance ratings
17. Current/future race entries
18. Race-entry projected performance
19. EPI
20. Downstream production feeds
21. Consumer audits
22. Final certification

## Required Properties

- Candidate isolation
- Atomic promotion
- Last-valid-output preservation
- Fail-closed governance
- Stage-level row funnels
- Stage-level reason codes
- Effective-dated parameter versions
- Source hashes
- Parameter hashes
- Output hashes
- Deterministic reruns
- Partial-coverage support
- No deletion of valid upstream outputs after downstream failure

## Status Ladder

`HISTORICAL_SOURCE_UNAVAILABLE` -> `STANDARD_TIME_UNAVAILABLE` -> `LENGTHS_V_STANDARD_UNAVAILABLE` -> `NORMALISATION_PARAMETERS_UNAVAILABLE` -> `NORMALISATION_UNAVAILABLE` -> `IDENTITY_MAP_UNAVAILABLE` -> `AGGREGATION_PARAMETERS_UNAVAILABLE` -> `HORSE_RATINGS_UNAVAILABLE` -> `LIVE_ENTRIES_UNAVAILABLE` -> `PROJECTED_PERFORMANCE_UNAVAILABLE` -> `EPI_UNAVAILABLE` -> `PARTIAL_LIVE_COVERAGE` -> `FULL_LIVE_PASS`

## Current Status

`PARTIAL_LIVE_COVERAGE`: governed historical horse ratings are built and validated, but live projected performance and EPI are unavailable due limited current historical coverage and missing downstream context inputs.
