# EDGEiQ Racing.com Performance Warehouse V2

Built UTC: `2026-07-22T08:49:38+00:00`
Status: `RACINGCOM_PERFORMANCE_WAREHOUSE_V2_PASS`
Warehouse rows: `80`
Distinct races: `8`

## Audit
- `parser_rows_consumed`: `PASS` (80) - Parser V2 output consumed.
- `runner_rows_retained`: `PASS` (80) - Historical valid 80 runner rows retained.
- `distinct_races`: `PASS` (8) - Eight historical successful races represented.
- `no_duplicate_records`: `PASS` (0) - Unique warehouse_record_id.
- `no_duplicate_runners`: `PASS` (0) - Unique race_id/horse_key.
- `identity_complete`: `PASS` (0) - Race and runner identity complete.
- `provenance_complete`: `PASS` (0) - Source CSV URL/cache/SHA/acquisition timestamp retained.
- `speed_units_plausible`: `PASS` (0) - Speed fields in plausible m/s range when present.
- `split_units_plausible`: `PASS` (0) - Split fields in plausible seconds range when present.
- `no_future_race_records`: `PASS` (0) - No future races in warehouse.
- `production_warehouse_not_overwritten`: `PASS` (0) - Wrote versioned V2 warehouse only.
