# EDGEiQ External Data Integration V1 Manual Import

Use only unmodified official files acquired through permitted access.

```powershell
cd C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM
python .\scripts\show_edgeiq_external_data_access_status_v1.py
python .\scripts\validate_edgeiq_external_data_credentials_v1.py
$env:RACINGCOM_PUBLIC_WIDGET_API_KEY="<APPROVED_VALUE>"
python .\scripts\run_edgeiq_external_source_acceptance_v1.py --mode RACINGCOM --dry-run --no-publish
python .\scripts\run_edgeiq_external_source_acceptance_v1.py --mode RACING_AUSTRALIA --dry-run --no-publish
python .\scripts\run_edgeiq_external_source_acceptance_v1.py --mode LOCAL_RECOVERY --dry-run --no-publish
python .\scripts\import_edgeiq_official_source_file_v1.py --source "OFFICIAL_EXPORT" --file "C:\path\to\official_export.csv" --date 2026-07-29 --data-type official_results --dry-run --no-publish
python .\scripts\run_edgeiq_daily_operations_engine_v1.py --mode BACKFILL --date-from 2026-07-20 --date-to 2026-07-29 --dry-run --no-publish
python .\scripts\audit_edgeiq_external_data_security_v1.py
```
