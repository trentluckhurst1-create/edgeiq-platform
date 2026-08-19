# EDGEiQ Victoria Live Recovery V5 Investigation

Status: `BLOCKED_GOVERNED_HISTORY_DEPTH`

Start commit: `8df332e`
Current head: `8df332e`
Built at: `DETERMINISTIC_NO_WALL_CLOCK_FOR_IDEMPOTENCY`

## Governance Determination

Historical HPR-NORM-A-v1 application permitted: `NO`

Policy effective date interpretation: `INTERPRETATION_A_PERFORMANCE_DATE_ELIGIBILITY_RULE`

Exact exclusion point: `scripts/build_edgeiq_performance_normalisation_fact_v1.py` rejects rows where the performance `race_date` is before the parameter `effective_from_date` with `NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE`.

The later temporal-authority decision explicitly records `Historical application authorised: NO`. The owner approval allows aggregation from eligible governed observations, but it does not authorise backdating the July-20-derived HPR-NORM-A-v1 parameter to earlier performance dates.

## Stage Counts

| stage | rows | min_date | max_date | before_2026_07_20_rows | on_or_after_2026_07_20_rows | distinct_horses_or_winners | distinct_races |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Performance Base | 52422 | 2000-08-02 | 2026-07-26 | 52414 | 8 | 8 | 52422 |
| Normalisation | 8 | 2026-07-26 | 2026-07-26 | 0 | 8 | 8 | 8 |
| Performance Rating Base | 8 | 2026-07-26 | 2026-07-26 | 0 | 8 | 8 | 8 |
| Horse Observations | 8 | 2026-07-26 | 2026-07-26 | 0 | 8 | 8 | 8 |
| Horse Aggregates | 0 |  |  | 0 | 0 | 0 | 0 |
| Horse Ratings | 0 |  |  | 0 | 0 | 0 | 0 |
| Snapshots | 0 |  |  | 0 | 0 | 0 | 0 |
| EPI | 0 |  |  | 0 | 0 | 0 | 0 |

## Current Sale Coverage

- Current runners: 80
- Governed identities: 80
- Runners with historical observations: 0
- Runners with 5+ observations: 0
- Horse Aggregates: 0
- Horse Ratings: 0
- Snapshots: 0
- EPI: 0

## CHIGURH

```json
{
  "aggregate_available": "NO",
  "blocking_reason": "MINIMUM_OBSERVATIONS_NOT_MET",
  "canonical_horse_id": "RA_HORSE_34054013730",
  "current_observation_count": 1,
  "epi_available": "NO",
  "historical_observation_count": 0,
  "raceentry_id": "99566658900",
  "rating_available": "NO",
  "snapshot_available": "NO",
  "source_horse_id": "34054013730",
  "source_horse_name": "CHIGURH",
  "total_governed_observations": 1
}
```

## Decision

No historical rebuild was performed. With the current governed evidence, pre-2026-07-20 historical Performance Base rows cannot be normalised under HPR-NORM-A-v1 without silent backdating/future leakage. The zero aggregate output is expected until horses accumulate five eligible governed observations or a separately approved earlier/backfill authority is created.
