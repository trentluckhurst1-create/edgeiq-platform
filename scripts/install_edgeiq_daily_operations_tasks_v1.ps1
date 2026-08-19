param([string]$RepoRoot = "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
$ErrorActionPreference = "Stop"
$Python = (Get-Command python).Source
$Script = Join-Path $RepoRoot "scripts\run_edgeiq_daily_operations_engine_v1.py"
$Tasks = @(
  @{Name="EDGEiQ Daily Previous-Day Ingestion V1"; Time="05:00"; Args="`"$Script`" --mode DAILY"},
  @{Name="EDGEiQ Delayed Speed Refresh V1"; Time="07:00"; Args="`"$Script`" --mode SPEED_ONLY --lookback-days 14"},
  @{Name="EDGEiQ Nightly Recent Backfill V1"; Time="23:00"; Args="`"$Script`" --mode BACKFILL --lookback-days 14"},
  @{Name="EDGEiQ Weekly Deep Health Check V1"; Time="02:00"; Args="`"$Script`" --mode HEALTH_CHECK --lookback-days 14"}
)
foreach ($Task in $Tasks) {
  $Action = New-ScheduledTaskAction -Execute $Python -Argument $Task.Args -WorkingDirectory $RepoRoot
  $Trigger = if ($Task.Name -like "*Weekly*") { New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $Task.Time } else { New-ScheduledTaskTrigger -Daily -At $Task.Time }
  Register-ScheduledTask -TaskName $Task.Name -Action $Action -Trigger $Trigger -Description "EDGEiQ governed daily operations engine" -Force | Out-Null
}
Write-Host "EDGEiQ daily operations scheduled tasks installed."
