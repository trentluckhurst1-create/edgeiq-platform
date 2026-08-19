# Runbook

PowerShell commands:

```powershell
Set-Location 'C:\\Users\\trent\\OneDrive\\Documents\\EDGEIQ_PLATFORM'
python -u .\scripts\trace_edgeiq_racingcom_calendar_discovery_producer_v1.py
python -u .\scripts\build_edgeiq_racingcom_meeting_discovery_v2.py
python -u .\scripts\build_edgeiq_racingcom_race_discovery_v2.py
python -u .\scripts\build_edgeiq_racingcom_ingestion_v2_foundation.py
python -u .\scripts\build_edgeiq_racingcom_page_discovery_v2.py
python -u .\scripts\build_edgeiq_racingcom_csv_acquisition_v2.py
python -u .\scripts\build_edgeiq_racingcom_parser_v2.py
python -u .\scripts\test_edgeiq_racingcom_parser_v2.py
python -u .\scripts\build_edgeiq_racingcom_performance_warehouse_v2.py
python -u .\scripts\audit_edgeiq_racingcom_ingestion_v2_e2e_regression.py
```

Do not run Bash. Do not point production orchestration at V2 until the migration decision is `READY_FOR_CONTROLLED_MIGRATION`.
