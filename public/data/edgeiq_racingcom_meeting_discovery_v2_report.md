# EDGEiQ Racing.com Meeting Discovery V2

Built UTC: `2026-07-22T19:21:33+00:00`
Status: `RACINGCOM_MEETING_DISCOVERY_V2_PASS`

## Counts
- Meeting rows: `186`
- Canonical meetings: `186`
- Race-level rows generated: `0`
- Fixed race expansion used: `NO`

## Contract Guardrails
- No `race_no` column.
- No `race_url` column.
- No `speed_data_url` column.
- No CSV URL column.
- No meeting-to-race expansion.
- Payload caches are repository-local under `outputs/performance-intelligence/racingcom-v2/raw/meeting-discovery/`.

## Source Types
- `LOCAL_RACE_FIELDS_MEETING_EVIDENCE`: `5`
- `RACINGCOM_GET_MEETS_BY_MONTH`: `185`

## Audit
- `output_rows_gt_zero`: `PASS` (186) - Meeting rows emitted.
- `no_race_number_column`: `PASS` (0) - 
- `no_race_url_generation_column`: `PASS` (0) - race_url absent from V2 meeting contract.
- `no_speed_data_url_generation_column`: `PASS` (0) - speed_data_url absent from V2 meeting contract.
- `no_csv_url_column`: `PASS` (0) - csv_url absent from V2 meeting contract.
- `no_duplicate_canonical_meetings`: `PASS` (0) - Duplicate meeting_id count.
- `valid_dates`: `PASS` (0) - Rows with invalid race_date.
- `valid_meeting_urls`: `PASS` (0) - Meeting URLs must be Racing.com form URLs when present.
- `provenance_retained`: `PASS` (0) - Rows missing source_url/provenance.
- `repository_local_payload_paths`: `PASS` (0) - Payload paths are relative to repository root.
- `deterministic_ordering`: `PASS` (0) - Rows sorted by date/track/meeting_id.
