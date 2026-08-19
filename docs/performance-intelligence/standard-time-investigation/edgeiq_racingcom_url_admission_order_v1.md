# EDGEIQ Racing.com URL Admission Order V1

Generated UTC: `2026-07-22T07:37:03.684851+00:00`

## Governance boundary

- Read-only diagnostic.
- No network access.
- Production builder not executed.
- No cache or governed output modified.
- Current candidate ordering reconstructed through the existing discovery function.

## Historical run evidence

- Run timestamp: **2026-05-15T04:09:05+00:00**
- Historical unique CSV URLs: **1368**
- Fetch attempts: **50**
- CSVs fetched or cached: **8**
- Fetch failures: **42**
- CSVs parsed: **8**
- Runner rows parsed: **80**

## Current candidate population

- Unique CSV URLs: **1296**
- Default admission cap: **50**
- URLs in current first cohort: **50**
- Distinct dates: **31**
- Distinct tracks: **44**
- URLs matching the expected `raceid_suffix.csv` pattern: **1296**

## Candidate-population drift

- Historical unique URLs: **1368**
- Current unique URLs: **1296**
- Current minus historical: **-72**

## Historical successful sources

- Historical distinct source URLs: **8**
- Still present in current candidates: **8**
- Missing from current candidates: **0**
- Currently positioned inside first 50: **8**
- Minimum current admission position: **1**
- Maximum current admission position: **11**

| CSV | Ingestion date | Ingestion track | Race | Runners | Current candidate | Current position | Current first 50 |
|---|---:|---|---:|---:|---|---:|---|
| 5191125_01.csv | 2026-05-01 | Ladbrokes Geelong | 1 | 9 | YES | 1 | YES |
| 5191125_02.csv | 2026-05-01 | Ladbrokes Geelong | 2 | 8 | YES | 5 | YES |
| 5191125_03.csv | 2026-05-01 | Ladbrokes Geelong | 3 | 13 | YES | 6 | YES |
| 5191125_04.csv | 2026-05-01 | Ladbrokes Geelong | 4 | 10 | YES | 7 | YES |
| 5191125_05.csv | 2026-05-01 | Ladbrokes Geelong | 5 | 7 | YES | 8 | YES |
| 5191125_06.csv | 2026-05-01 | Ladbrokes Geelong | 6 | 11 | YES | 9 | YES |
| 5191125_07.csv | 2026-05-01 | Ladbrokes Geelong | 7 | 11 | YES | 10 | YES |
| 5191125_08.csv | 2026-05-01 | Ladbrokes Geelong | 8 | 11 | YES | 11 | YES |

## Interpretation boundary

This diagnostic does not assume that current HTTP status matches the May 2026 run.

It establishes only:

1. the deterministic candidate ordering currently produced by the builder;
2. whether the eight historically successful source URLs remain discoverable;
3. whether those historical successes are concentrated within the builder's first 50 admission positions;
4. whether the candidate population has drifted since the historical run.

## Decision

**HISTORICAL_SUCCESS_URLS_RECONSTRUCTED**

## Artifacts

- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_url_admission_order_ledger_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_first_50_url_cohort_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_historical_success_sources_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_url_admission_order_v1.json`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_url_admission_order_v1.md`
