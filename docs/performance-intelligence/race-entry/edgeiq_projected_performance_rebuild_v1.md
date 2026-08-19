# EDGEiQ Projected Performance Rebuild V1

Rebuild date: 2026-07-23

## Row Accounting
- Race-entry rows: 204
- Historical horse performance rating rows: 0
- Projected-performance output rows: 0

## Temporal Rule
Historical observations must be dated before the target race date. No target-race Results rows were used.

## Outcome

```text
LIVE_ENTRIES_NO_HISTORICAL_MATCH
```

The race-entry blocker is resolved, but projected performance remains zero because the governed historical horse performance rating fact is empty. The projected-performance formula was not changed and minimum-history rules were not lowered.

## Rejection / Block Reason
- `public/data/edgeiq_horse_performance_rating_fact_v1.csv` rows: 0
- Identity matches: 0
- Temporally eligible observations: 0
- Runners meeting minimum history: 0

## Next Action
Recover or rebuild the governed historical horse performance rating fact from already-approved historical PI facts, then rerun the existing projected-performance builder.
