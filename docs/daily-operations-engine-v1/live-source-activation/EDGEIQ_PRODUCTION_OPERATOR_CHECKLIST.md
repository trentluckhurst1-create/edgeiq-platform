# EDGEiQ Production Operator Checklist

## Daily Checks

```powershell
cd C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM
python .\scripts\run_edgeiq_daily_operations_engine_v1.py --mode DAILY --dry-run --no-publish
python .\scripts\run_edgeiq_daily_operations_engine_v1.py --mode BACKFILL --lookback-days 14 --dry-run --no-publish
python .\scripts\audit_edgeiq_daily_operations_engine_v1.py
```

## Inspect Pending Races

```powershell
Import-Csv .\public\data\edgeiq_race_data_lifecycle_fact_v1.csv | Group-Object result_status,timing_status,condition_status,speed_status
Import-Csv .\public\data\edgeiq_daily_operations_alert_fact_v1.csv | Format-Table
```

## Speed Pending

Races with `SPEED_PENDING` remain eligible for delayed refresh. Do not mark complete until authoritative speed rows arrive.

## Rollback

Use the rollback paths emitted by `update_edgeiq_canonical_historical_timing_warehouse_v1.py`; do not hand-edit canonical timing CSVs.

## Install Scheduled Tasks

Only after operator approval:

```powershell
.\scripts\install_edgeiq_daily_operations_tasks_v1.ps1
```

## Recovery

If a lock exists, inspect the process ID in `public/data/edgeiq_daily_operations_engine_v1.lock.json`; do not delete an active lock without proving the process is stale.
