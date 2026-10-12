param(
    [string]$RepoRoot = "C:\EDGEIQ_PROFITABILITY_RESEARCH",
    [string]$Out = "outputs/research/issue18_eight_race_sensitivity"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location $RepoRoot
try {
    python .\scripts\research\run_issue18_eight_race_sensitivity.py --out $Out
}
finally {
    Pop-Location
}
