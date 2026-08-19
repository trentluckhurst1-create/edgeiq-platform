$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host ""
Write-Host "[EDGEIQ] Refreshing Victorian weather registry"
Write-Host "[EDGEIQ] $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host ""

python ".\scripts\build_edgeiq_victorian_weather_registry_v1.py"

if ($LASTEXITCODE -ne 0) {
    throw "EDGEIQ Victorian weather refresh failed."
}

Write-Host ""
Write-Host "[EDGEIQ] Victorian weather refresh complete"
