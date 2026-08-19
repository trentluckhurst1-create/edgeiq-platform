# EDGEiQ Racing.com Parser V2

Built UTC: `2026-07-22T08:41:18+00:00`
Status: `RACINGCOM_PARSER_V2_PASS`
Files consumed: `8`
Runner rows: `80`
Reject rows: `0`

## Audit
- `valid_csv_files_available`: `PASS` (8) - Valid acquired CSV files consumed.
- `parser_no_network_access`: `PASS` (0) - Parser consumes cached CSV paths only.
- `parsed_files`: `PASS` (8) - All acquired CSV files parsed.
- `runner_rows_retained`: `PASS` (80) - Previously established 80 runner rows retained or exceeded.
- `duplicate_runner_rows_controlled`: `PASS` (0) - No duplicate race_id/horse_key parser rows.
- `missing_identity_controlled`: `PASS` (0) - Every parser row has race_id and horse_key.
- `source_provenance_retained`: `PASS` (80) - Rows retain source URL/cache/SHA provenance.
