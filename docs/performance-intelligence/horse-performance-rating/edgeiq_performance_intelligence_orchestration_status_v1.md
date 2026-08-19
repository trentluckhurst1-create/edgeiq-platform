# EDGEiQ Performance Intelligence Orchestration Status V1

Status: `NO_HISTORICAL_RATINGS`

## Governed Order
1. Historical Results ingestion
2. Standard Times
3. Lengths v Standard
4. Sectional performance
5. Early speed
6. Late speed
7. Performance normalisation parameters
8. Performance normalisation
9. Performance rating base
10. Horse identity map
11. Horse performance observations
12. Horse performance aggregation parameters
13. Horse performance aggregate fact
14. Horse performance rating fact
15. Live race-entry fact
16. Projected performance
17. EPI
18. Downstream feeds

## Gates
- `NO_HISTORICAL_RATINGS`: current active state; horse rating fact has zero rows.
- `PARTIAL_HISTORICAL_RATING_COVERAGE`: blocked until governed parameter and identity sources are restored.
- `PROJECTED_PERFORMANCE_READY`: blocked until horse ratings exist.
- `PARTIAL_EPI_COVERAGE`: blocked until projected performance exists.

## Deterministic Execution Status
- Two deterministic executions: `NOT_RUN_BLOCKED_BY_GOVERNED_SOURCE_GAPS`.
- Hash comparison: `NOT_RUN_BLOCKED_BY_ZERO_RATING_FACT`.
- Candidate promotion test: `NOT_RUN_NO_CANDIDATE_BUILT`.
- Rollback test: `NOT_RUN_NO_PROMOTION`.
- Consumer audit: `EPI_INPUTS_PARTIAL_PROJECTED_PERFORMANCE_MISSING`.
- Program smoke: `RESOURCE_TIMEOUT`.
