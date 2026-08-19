# Racing.com Production Runner Contract Profile V1

Built UTC: `2026-07-22T18:54:46+00:00`
Status: `RACINGCOM_PRODUCTION_RUNNER_CONTRACT_PROFILE_PASS`

## Contract

- Row grain: `RUNNER_AGGREGATE`
- Exact production row key: `warehouse_record_id`
- Secondary semantic key: `race_id + horse_key`
- Column count: `35`
- Sorting: `race_date, track, numeric race_no, horse_key`

## Unit Rules

- Speed fields: source m/s.
- Split fields: source seconds.
- Race time: source time string.
- Rounding: preserve source string.
