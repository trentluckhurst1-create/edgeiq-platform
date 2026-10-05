param(
  [string]$ResearchRoot = "C:\EDGEIQ_PROFITABILITY_RESEARCH",
  [string]$DataRoot = "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
)

$ErrorActionPreference = "Stop"
$researchResolved = [System.IO.Path]::GetFullPath($ResearchRoot).TrimEnd([char]92)
$dataResolved = [System.IO.Path]::GetFullPath($DataRoot).TrimEnd([char]92)

if ($researchResolved -ieq $dataResolved) { throw "Refusing to run: research worktree and production data root are identical." }
if ($researchResolved -notlike "*EDGEIQ_PROFITABILITY_RESEARCH*") { throw "Refusing to run outside isolated EDGEIQ_PROFITABILITY_RESEARCH worktree: $researchResolved" }

Set-Location $ResearchRoot
$env:EDGEIQ_DATA_ROOT = $DataRoot

function Invoke-PythonChecked {
  param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PythonArgs)
  & python @PythonArgs
  if ($LASTEXITCODE -ne 0) { throw "Python stage failed with exit code $LASTEXITCODE" }
}

Write-Host "EDGEiQ LAB245B PREHOLDOUT"
Write-Host "ResearchRoot=$ResearchRoot"
Write-Host "DataRoot=$DataRoot"
Write-Host "Production checkout is read-only data authority; outputs remain in research worktree."
Write-Host "2025-2026 holdout cannot be opened by this launcher."

Invoke-PythonChecked -m py_compile scripts/research/run_lab245b_preflight.py
Invoke-PythonChecked -m py_compile scripts/research/build_lab245b_warehouse_runner_lvs.py
Invoke-PythonChecked -m py_compile scripts/research/build_lab245b_compact_performance_bridge.py
Invoke-PythonChecked -m py_compile scripts/research/run_lab245b1_next_performance_forecast.py
Invoke-PythonChecked -m py_compile scripts/research/run_lab245b2_probability_challenger.py
Invoke-PythonChecked -m py_compile scripts/research/run_lab245b3_selective_betting_forensics.py
Invoke-PythonChecked -m py_compile scripts/research/run_lab245b_preholdout_chain.py

Invoke-PythonChecked scripts/research/run_lab245b_vector_pit_equivalence_smoke.py
Invoke-PythonChecked scripts/research/run_lab245b_contract_smoke.py
Invoke-PythonChecked scripts/research/run_lab245b_preholdout_chain.py

Write-Host "LAB245B preholdout chain completed."
Write-Host "Status: outputs\research\profitability_program\lab245b\LAB245B_CHAIN_STATUS.json"
