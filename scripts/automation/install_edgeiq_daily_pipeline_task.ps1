$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Script = Join-Path $Repo "scripts\automation\run_edgeiq_daily_pipeline.ps1"
$TaskName = "EDGEiQ Daily Rolling Product Pipeline"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""
$Trigger = New-ScheduledTaskTrigger -Daily -At 4:15am
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Runs the EDGEiQ rolling three-day product data pipeline every morning." -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State
