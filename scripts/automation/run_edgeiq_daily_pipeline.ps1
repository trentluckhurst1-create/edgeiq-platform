param([switch]$RunOnce, [string]$Date)
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Repo
$Python = (Get-Command python -ErrorAction Stop).Source
$Args = @("scripts\run_edgeiq_daily_rolling_product_pipeline_v1.py")
if ($Date) { $Args += @("--date", $Date) }
& $Python @Args
exit $LASTEXITCODE
