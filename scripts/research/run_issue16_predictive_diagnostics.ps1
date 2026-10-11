param(
    [string]$RepoRoot = "C:\EDGEIQ_PROFITABILITY_RESEARCH",
    [string]$Out = "outputs/research/issue14_predictive_diagnostics"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location $RepoRoot
try {
    python .\scripts\research\run_issue16_predictive_diagnostics.py --out $Out
}
finally {
    Pop-Location
}
