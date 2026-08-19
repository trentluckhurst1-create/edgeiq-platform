$Tasks = "EDGEiQ Daily Previous-Day Ingestion V1","EDGEiQ Delayed Speed Refresh V1","EDGEiQ Nightly Recent Backfill V1","EDGEiQ Weekly Deep Health Check V1"
Get-ScheduledTask | Where-Object { $Tasks -contains $_.TaskName } | Select-Object TaskName,State,Description
