# EDGEIQ Daily Operations Runbook V1

## Normal daily refresh
```powershell
Set-Location "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
python -u .\scriptsun_edgeiq_daily_product_refresh_v1.py
```

## Frontend startup
```powershell
Set-Location "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
npm run dev
```

## Frontend production build
```powershell
npm run build
```

## Audit-only run
```powershell
python -u .\scriptsun_edgeiq_daily_product_refresh_v1.py --audit-only
```

## Specific date refresh
```powershell
python -u .\scriptsun_edgeiq_daily_product_refresh_v1.py --date YYYY-MM-DD
```

## Specific meeting refresh
```powershell
python -u .\scriptsun_edgeiq_daily_product_refresh_v1.py --meeting "TRACK"
```

## Specific race refresh
```powershell
python -u .\scriptsun_edgeiq_daily_product_refresh_v1.py --meeting "TRACK" --race R1
```

## Public-feed republish
```powershell
python -u .\scriptsun_edgeiq_daily_product_refresh_v1.py --publish-only
```

## Full governed historical rebuild
Only run the governed performance-intelligence historical builders when source governance changes. Normal daily startup must not require the 879,784-row rebuild.

## Last-known-good verification / recovery check
```powershell
python -u .\scriptsun_edgeiq_daily_product_refresh_v1.py --audit-only
```

## Failed-run diagnosis
Read `docs\operations-readiness\daily-refresh\edgeiq_daily_product_refresh_v1_run_log.txt` and `docs\operations-readiness\daily-refresh\edgeiq_daily_product_refresh_v1_audit.json`.
