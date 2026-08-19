# EDGEiQ Racing.com CSV Acquisition V2

Built UTC: `2026-07-22T08:38:13+00:00`
Status: `RACINGCOM_CSV_ACQUISITION_V2_PASS`
CSV queue rows: `8`
Valid CSV files: `8`
Rejected files: `0`

## Download Results
- `ACQUIRED_VALID_CSV`: `8`

## Audit
- `csv_queue_rows_only`: `PASS` (8) - Attempted all CSV_ACQUISITION rows from queue; total queue rows=12.
- `valid_csv_or_rejected`: `PASS` (0) - Every response accepted as plausible CSV or rejected with reason.
- `no_html_accepted`: `PASS` (0) - HTML bodies/content-types are rejected, not accepted.
- `cache_repository_local`: `PASS` (0) - All accepted CSV cache paths are repository-relative.
- `no_first_n_silent_truncation`: `PASS` (8) - All admitted CSV rows attempted; no MAX_FETCHES cap.
- `no_constructed_urls`: `PASS` (8) - All CSV URLs came from admitted historical proof.
- `production_unchanged`: `PASS` (0) - No production warehouse, UI, pricing, probability, or rating files modified.
