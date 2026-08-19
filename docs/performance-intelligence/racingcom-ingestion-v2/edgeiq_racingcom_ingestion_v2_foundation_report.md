# EDGEiQ Racing.com Ingestion V2 Foundation

Built UTC: `2026-07-22T08:31:59+00:00`
Status: `RACINGCOM_INGESTION_V2_FOUNDATION_PASS`

## Counts
- Meeting rows: `186`
- Race rows: `52`
- Admission rows: `52`
- Queue rows: `12`
- Rejection/deferred rows: `40`

## Admission Status Counts
- `ADMITTED_HISTORICAL_PROVEN_CSV`: `8`
- `REJECTED_NO_SPEED_DATA_EVIDENCE`: `40`
- `REQUIRES_PAGE_DISCOVERY`: `4`

## Queue Types
- `CSV_ACQUISITION`: `8`
- `PAGE_DISCOVERY`: `4`

## Guardrails
- No fixed race expansion.
- No future race enters the queue.
- No constructed CSV URLs are admitted.
- Production outputs unchanged.

## Audit
- `meeting_contract_rows`: `PASS` (186) - Meeting Discovery V2 rows consumed.
- `race_contract_rows`: `PASS` (52) - Race Discovery V2 rows consumed.
- `admission_rows_match_race_rows`: `PASS` (52) - One admission decision per race discovery row.
- `historical_proven_csv_admitted`: `PASS` (8) - Historically successful CSVs admitted.
- `page_discovery_queue_evidence_based`: `PASS` (4) - Only directly evidenced speed-data pages enter page discovery queue.
- `future_races_deferred_not_queued`: `PASS` (0) - Future races do not enter acquisition/page queues.
- `unsupported_races_rejected`: `PASS` (0) - No unsupported V2 race identities admitted.
- `no_constructed_csv_urls`: `PASS` (0) - CSV URLs only admitted from historical proof or explicit observed CSV evidence.
- `numeric_queue_ordering`: `PASS` (0) - Queue sorted by priority/date/track/race_no/race_id.
- `no_first_n_silent_truncation`: `PASS` (0) - Foundation builds the full V2 race discovery population; no fetch cap exists in this stage.
- `production_unchanged`: `PASS` (0) - No production warehouse, pricing, UI, or model outputs modified.
