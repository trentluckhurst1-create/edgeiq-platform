$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host ""
Write-Host "================================================"
Write-Host " EDGEIQ VICTORIAN LIVE WEATHER REGISTRY"
Write-Host " VRC + TurfTrax + Racing Australia + BOM"
Write-Host " Refresh interval: 5 minutes"
Write-Host " Press Ctrl+C to stop"
Write-Host "================================================"
Write-Host ""

while ($true) {
    Write-Host ""
    Write-Host (
        "[EDGEIQ] Victorian weather refresh: " +
        (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    )

    python ".\scripts\build_edgeiq_victorian_weather_registry_v1.py"

    if ($LASTEXITCODE -eq 0) {
        Write-Host (
            "[EDGEIQ] Victorian weather registry " +
            "updated successfully"
        )
    }
    else {
        Write-Warning (
            "[EDGEIQ] Victorian weather refresh failed; " +
            "the previous registry remains available"
        )
    }

    Write-Host "[EDGEIQ] Next refresh in 5 minutes"

    Start-Sleep -Seconds 300
}
