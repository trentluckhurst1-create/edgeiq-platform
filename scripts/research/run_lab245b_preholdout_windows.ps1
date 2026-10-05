param(
  [string]$DataRoot = "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
)
$ErrorActionPreference = "Stop"
$ResearchRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$env:EDGEIQ_DATA_ROOT = (Resolve-Path $DataRoot).Path
$OutDir = Join-Path $ResearchRoot "outputs\research\profitability_program\lab245b"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log = Join-Path $OutDir "LAB245B_PREHOLDOUT_$Stamp.log"
Set-Location $ResearchRoot
Write-Host "RESEARCH_ROOT=$ResearchRoot"
Write-Host "EDGEIQ_DATA_ROOT=$env:EDGEIQ_DATA_ROOT"
Write-Host "PRODUCTION_WRITE_POLICY=READ_ONLY_INPUTS; OUTPUTS_RESEARCH_WORKTREE_ONLY"
Write-Host "HOLDOUT_2025_2026=SEALED"
python -m py_compile scripts/research/run_lab245b_preflight.py scripts/research/build_lab245b_warehouse_runner_lvs.py scripts/research/build_lab245b_compact_performance_bridge.py scripts/research/run_lab245b1_next_performance_forecast.py scripts/research/run_lab245b2_probability_challenger.py scripts/research/run_lab245b3_selective_betting_forensics.py scripts/research/run_lab245b_preholdout_chain.py
if ($LASTEXITCODE -ne 0) { throw "LAB245B compile gate failed." }
python scripts/research/run_lab245b_preholdout_chain.py 2>&1 | Tee-Object -FilePath $Log
if ($LASTEXITCODE -ne 0) { throw "LAB245B preholdout chain failed. Log: $Log" }
Write-Host "LAB245B_PREHOLDOUT_CHAIN_COMPLETE"
Write-Host "LOG=$Log"
