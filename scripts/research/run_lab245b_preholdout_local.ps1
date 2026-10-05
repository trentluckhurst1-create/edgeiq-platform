$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ResearchRoot = "C:\EDGEIQ_PROFITABILITY_RESEARCH"
$ProductionRoot = "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
$ExpectedBranch = "local/profitability-program-20261004"

if (-not (Test-Path -LiteralPath $ResearchRoot)) { throw "Research worktree missing: $ResearchRoot" }
if (-not (Test-Path -LiteralPath $ProductionRoot)) { throw "Production data root missing: $ProductionRoot" }

Set-Location -LiteralPath $ResearchRoot

$branch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) { throw "Unable to determine research branch." }
if ($branch -notin @($ExpectedBranch, "research/profitability-program-20261004")) {
    throw "Refusing to run from unexpected branch: $branch"
}

$warehouse = Join-Path $ProductionRoot "docs\performance-intelligence\warehouse\edgeiq_performance_fact_warehouse_v1.csv"
$authority = Join-Path $ProductionRoot "docs\performance-intelligence\lengths-v-standard\edgeiq_runner_lengths_v_standard_fact_v1.csv"
if (-not (Test-Path -LiteralPath $warehouse)) { throw "Frozen warehouse missing: $warehouse" }
if (-not (Test-Path -LiteralPath $authority)) { throw "Historical runner-LVS parity authority missing: $authority" }

$env:EDGEIQ_DATA_ROOT = $ProductionRoot
Write-Host "EDGEIQ_DATA_ROOT=$env:EDGEIQ_DATA_ROOT"
Write-Host "RESEARCH_ROOT=$ResearchRoot"
Write-Host "PRODUCTION_WRITE_POLICY=READ_ONLY_DATA_SOURCE"
Write-Host "HOLDOUT_2025_2026=SEALED"

python scripts/research/run_lab245b_preholdout_chain.py
if ($LASTEXITCODE -ne 0) { throw "LAB245B preholdout chain failed with exit code $LASTEXITCODE" }

Write-Host "LAB245B_PREHOLDOUT_CHAIN_COMPLETE"
Write-Host "HOLDOUT_2025_2026_REMAINS_SEALED=YES"
