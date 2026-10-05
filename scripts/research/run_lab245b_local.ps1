param(
  [string]$ResearchRoot = "C:\EDGEIQ_PROFITABILITY_RESEARCH",
  [string]$DataRoot = "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Warehouse = Join-Path $DataRoot "docs\performance-intelligence\warehouse\edgeiq_performance_fact_warehouse_v1.csv"
$Authority = Join-Path $DataRoot "docs\performance-intelligence\lengths-v-standard\edgeiq_runner_lengths_v_standard_fact_v1.csv"
$Launcher = Join-Path $ResearchRoot "scripts\research\run_lab245b_preholdout_chain.py"
$LogDir = Join-Path $ResearchRoot "outputs\research\profitability_program\lab245b"
$Log = Join-Path $LogDir ("LAB245B_LOCAL_RUN_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")

if (-not (Test-Path $ResearchRoot)) { throw "Research worktree missing: $ResearchRoot" }
if (-not (Test-Path $Warehouse)) { throw "Immutable warehouse missing: $Warehouse" }
if (-not (Test-Path $Launcher)) { throw "LAB245B launcher missing: $Launcher" }
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$env:EDGEIQ_DATA_ROOT = $DataRoot
Set-Location $ResearchRoot

Write-Host "LAB245B LOCAL GOVERNED EXECUTION"
Write-Host "RESEARCH_ROOT=$ResearchRoot"
Write-Host "DATA_ROOT=$DataRoot"
Write-Host "WAREHOUSE_READ_ONLY_SOURCE=$Warehouse"
Write-Host "PARITY_AUTHORITY_PRESENT=$([bool](Test-Path $Authority))"
Write-Host "OUTPUT_ROOT=$LogDir"
Write-Host "HOLDOUT_2025_2026=SEALED"

Start-Transcript -Path $Log -Force
try {
  python -m py_compile $Launcher
  if ($LASTEXITCODE -ne 0) { throw "Launcher compile failed." }
  python $Launcher
  if ($LASTEXITCODE -ne 0) { throw "LAB245B governed chain failed with exit code $LASTEXITCODE." }
}
finally {
  Stop-Transcript
}
Write-Host "LAB245B_RUN_COMPLETE"
Write-Host "LOG=$Log"
