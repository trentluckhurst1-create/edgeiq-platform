$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host ""
Write-Host "=========================================================================================="
Write-Host "EDGEIQ SECTIONAL RECOVERY V2"
Write-Host "=========================================================================================="

Write-Host ""
Write-Host "[1/2] Layout-aware sectional audit..."
python .\scripts\audit_edgeiq_sectional_pipeline_v2.py
if ($LASTEXITCODE -ne 0) { throw "Sectional audit V2 failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "=== V2 AUDIT SUMMARY ==="
Get-Content .\public\data\edgeiq_sectional_pipeline_v2_summary.csv

Write-Host ""
Write-Host "=== SPLIT FAILURE REASONS ==="
Get-Content .\public\data\edgeiq_sectional_split_failure_reasons_v2.csv | Select-Object -First 40

Write-Host ""
Write-Host "[2/2] Building conservative canonical warehouse..."
python .\scripts\build_edgeiq_sectional_warehouse_v2.py
if ($LASTEXITCODE -ne 0) { throw "Sectional warehouse V2 failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "=== WAREHOUSE SUMMARY ==="
Get-Content .\public\data\edgeiq_sectional_warehouse_v2_summary.csv

Write-Host ""
Write-Host "=== OUTPUTS ==="
Write-Host "AUDIT       public\data\edgeiq_sectional_pipeline_v2_audit.csv"
Write-Host "FAILURES    public\data\edgeiq_sectional_split_failure_reasons_v2.csv"
Write-Host "WAREHOUSE   public\data\edgeiq_sectional_warehouse_v2.csv"
Write-Host "QUARANTINE  public\data\edgeiq_sectional_quarantine_v2.csv"
Write-Host "SUMMARY     public\data\edgeiq_sectional_warehouse_v2_summary.csv"
Write-Host ""
Write-Host "STATUS: RECOVERY_V2_COMPLETE"
