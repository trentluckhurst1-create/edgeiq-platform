# EDGEiQ Daily Operations Engine V1 - Architecture

This governed document describes the Daily Operations Engine V1. It is Windows-native, PowerShell-operated, Python-processed, deterministic, idempotent, source-aware and protected from pricing/probability/model/UI changes.

## Core Commands

```powershell
cd C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM
python .\scripts\run_edgeiq_daily_operations_engine_v1.py --mode DRY_RUN --no-publish
python .\scripts\run_edgeiq_daily_operations_engine_v1.py --mode DAILY
python .\scripts\run_edgeiq_daily_operations_engine_v1.py --mode SPEED_ONLY --lookback-days 14
python .\scripts\run_edgeiq_daily_operations_engine_v1.py --mode BACKFILL --lookback-days 14
python .\scripts\run_edgeiq_daily_operations_engine_v1.py --mode HEALTH_CHECK
python .\scripts\run_edgeiq_daily_operations_engine_v1.py --mode FULL_REBUILD
python .\scripts\run_edgeiq_daily_operations_engine_v1.py --resume-run-id <RUN_ID>
python .\scripts\audit_edgeiq_daily_operations_engine_v1.py
.\scripts\install_edgeiq_daily_operations_tasks_v1.ps1
.\scripts\show_edgeiq_daily_operations_tasks_v1.ps1
.\scripts\uninstall_edgeiq_daily_operations_tasks_v1.ps1
```

Scheduled tasks are not installed automatically. Raw evidence should live under `data/evidence/daily-operations` and large payloads should remain outside Git unless repository policy changes.
