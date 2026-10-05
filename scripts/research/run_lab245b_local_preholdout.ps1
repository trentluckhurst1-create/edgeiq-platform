param(
  [string]$ResearchRoot = "C:\EDGEIQ_PROFITABILITY_RESEARCH",
  [string]$DataRoot = "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
)
$ErrorActionPreference = "Stop"
Set-Location $ResearchRoot
$env:EDGEIQ_DATA_ROOT = $DataRoot
Write-Host "EDGEiQ LAB245B PREHOLDOUT"
Write-Host "ResearchRoot=$ResearchRoot"
Write-Host "DataRoot=$DataRoot"
Write-Host "Production checkout is read-only data authority; outputs remain in research worktree."
Write-Host "2025-2026 holdout cannot be opened by this launcher."
python -m py_compile scripts/research/run_lab245b_preflight.py
python -m py_compile scripts/research/build_lab245b_warehouse_runner_lvs.py
python -m py_compile scripts/research/build_lab245b_compact_performance_bridge.py
python -m py_compile scripts/research/run_lab245b1_next_performance_forecast.py
python -m py_compile scripts/research/run_lab245b2_probability_challenger.py
python -m py_compile scripts/research/run_lab245b3_selective_betting_forensics.py
python -m py_compile scripts/research/run_lab245b_preholdout_chain.py
python scripts/research/run_lab245b_vector_pit_equivalence_smoke.py
python scripts/research/run_lab245b_contract_smoke.py
python scripts/research/run_lab245b_preholdout_chain.py
if ($LASTEXITCODE -ne 0) { throw "LAB245B preholdout chain failed with exit code $LASTEXITCODE" }
Write-Host "LAB245B preholdout chain completed. Inspect outputs\research\profitability_program\lab245b\LAB245B_CHAIN_STATUS.json"
