# EDGEiQ Current Race-Entry Source Inventory V1

Audit date: 2026-07-23
Files inventoried: 8214

## Governance Classification Counts
- ACTIVE_BUT_INCOMPLETE: 21
- HISTORICAL_ONLY: 162
- RESULTS_ONLY: 1091
- STALE_SOURCE: 6940

## Best Current/Future Candidate
- File: `docs\performance-intelligence\racingcom-ingestion-v2\edgeiq_racingcom_meeting_discovery_contract_v2.csv`
- Status: ACTIVE_BUT_INCOMPLETE
- Type: MEETING_CATALOGUE
- Rows: 186
- Races: 186
- Runners: 0
- Date range: 2026-06-01 to 2026-08-31
- Current/future rows: 51
- Reason: Has current/future evidence but runner_count=0, required_groups=2.

## Data-Governance Notes
- Results-only and historical sources are inventoried but blocked for target race-entry creation.
- Stale race-entry-shaped files remain classified as stale and are not eligible for canonical live race-entry fact promotion.
- Candidate selection requires current/future dates relative to the audit date and runner-level declaration fields.
