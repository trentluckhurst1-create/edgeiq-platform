# EDGEiQ Live Entry Historical Rating Coverage V1

Live entries: `204`
Active live entries: `188`
Horse performance rating rows: `0`
Live horses with historical ratings: `0`
Live horses without historical ratings: `188`

## Status Counts
- `EMERGENCY`: 10
- `INSUFFICIENT_HISTORY`: 188
- `SCRATCHED`: 6

## Finding
No live race-entry runner currently matches a governed horse-performance rating because `edgeiq_horse_performance_rating_fact_v1.csv` has zero data rows. Scratched and emergency statuses are preserved separately; active entries are marked `INSUFFICIENT_HISTORY` rather than assigned synthetic ratings.
