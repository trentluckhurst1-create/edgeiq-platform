param(
    [string]$DataRoot = "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
)
$ErrorActionPreference = "Stop"
$ResearchRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$env:EDGEIQ_DATA_ROOT = (Resolve-Path $DataRoot).Path

$Warehouse = Join-Path $env:EDGEIQ_DATA_ROOT "docs\performance-intelligence\warehouse\edgeiq_performance_fact_warehouse_v1.csv"
$Lcp = Join-Path $env:EDGEIQ_DATA_ROOT "public\data\edgeiq_length_conversion_parameter_fact_v2.csv"
if (-not (Test-Path $Warehouse)) { throw "Missing warehouse: $Warehouse" }
if (-not (Test-Path $Lcp)) { throw "Missing length conversion authority: $Lcp" }

Write-Host "LAB245B_RESEARCH_ROOT=$ResearchRoot"
Write-Host "LAB245B_DATA_ROOT=$env:EDGEIQ_DATA_ROOT"
Write-Host "PRODUCTION_WRITE_POLICY=READ_ONLY_INPUTS"

Set-Location $ResearchRoot
$Scripts = @(
  "scripts/research/build_lab245b_warehouse_runner_lvs.py",
  "scripts/research/run_lab245b_target_parity_audit.py",
  "scripts/research/build_lab245b_compact_performance_bridge.py",
  "scripts/research/run_lab245b1_next_performance_forecast.py",
  "scripts/research/run_lab245b2_probability_challenger.py",
  "scripts/research/run_lab245b3_selective_betting_forensics.py",
  "scripts/research/run_lab245b4_sealed_holdout.py"
)
foreach ($s in $Scripts) {
  Write-Host ("=" * 100)
  Write-Host "RUN=$s"
  python $s
  if ($LASTEXITCODE -ne 0) { throw "LAB245B failed at $s with exit code $LASTEXITCODE" }
}
Write-Host ("=" * 100)
Write-Host "LAB245B_CHAIN_COMPLETE"
