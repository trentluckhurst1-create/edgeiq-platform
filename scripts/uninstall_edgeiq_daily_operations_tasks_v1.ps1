$Tasks = @("EDGEiQ Daily Previous-Day Ingestion V1","EDGEiQ Delayed Speed Refresh V1","EDGEiQ Nightly Recent Backfill V1","EDGEiQ Weekly Deep Health Check V1")
foreach ($Task in $Tasks) { if (Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue) { Unregister-ScheduledTask -TaskName $Task -Confirm:$false } }
Write-Host "EDGEiQ daily operations scheduled tasks removed."
