# EDGEiQ Victoria Live Recovery V2

Status: BLOCKED_CURRENT_RESULTS_NOT_INGESTED
Root cause: CURRENT_RESULTS_NOT_INGESTED

## Current Victorian Meetings

Meetings discovered from 2026-07-20 through 2026-07-30: 6

## Root Cause Evidence

- Canonical results warehouse max date is 2026-05-24.
- Current meetings discovered in window: 6.
- Latest daily operations window: 2026-07-15 to 2026-07-28.
- Official results ingestion status: PASS; raw_rows=80; facts=80.
- After 2026-07-20 result races: 0.

## Meeting Classification

- ORCHESTRATION_NOT_RUN: 2
- RESULT_NOT_IMPORTED: 4

## Orchestration

Latest run: DAILYOPS-2026-07-15-2026-07-28-7E34B128B4
Mode: BACKFILL
Status: PASS
Window: 2026-07-15 to 2026-07-28

Execution order:
1. race_discovery - rc=0 - python scripts/build_edgeiq_daily_race_discovery_v1.py --mode DEEP_BACKFILL --date-from 2026-07-15 --date-to 2026-07-28 --dry-run --no-publish
2. official_results - rc=0 - python scripts/build_edgeiq_daily_official_results_ingestion_v1.py --mode DEEP_BACKFILL --date-from 2026-07-15 --date-to 2026-07-28 --dry-run --no-publish
3. official_timing - rc=0 - python scripts/build_edgeiq_daily_official_timing_ingestion_v1.py --mode DEEP_BACKFILL --date-from 2026-07-15 --date-to 2026-07-28 --dry-run --no-publish
4. condition_evidence - rc=0 - python scripts/build_edgeiq_daily_condition_evidence_v1.py --mode DEEP_BACKFILL --date-from 2026-07-15 --date-to 2026-07-28 --dry-run --no-publish
5. delayed_speed - rc=0 - python scripts/build_edgeiq_delayed_speed_data_ingestion_v1.py --mode DEEP_BACKFILL --date-from 2026-07-15 --date-to 2026-07-28 --dry-run --no-publish
6. lifecycle - rc=0 - python scripts/build_edgeiq_race_data_lifecycle_fact_v1.py --mode DEEP_BACKFILL --date-from 2026-07-15 --date-to 2026-07-28 --dry-run --no-publish
7. canonical_timing_update - rc=0 - python scripts/update_edgeiq_canonical_historical_timing_warehouse_v1.py --mode DEEP_BACKFILL --date-from 2026-07-15 --date-to 2026-07-28 --dry-run --no-publish

## Decision

No implementation was performed. HPR-NORM-A-v1 remains unchanged. The next safe action is to restore current official results ingestion, not alter normalisation.
