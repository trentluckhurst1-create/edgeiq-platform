param(
    [string]$RepoRoot = "C:\EDGEIQ_PROFITABILITY_RESEARCH",
    [string]$Out = "outputs/research/issue8_pre2022_source_admission"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location $RepoRoot
try {
    python .\scripts\research\run_issue8_pre2022_source_admission.py --repo-root . --out $Out
}
finally {
    Pop-Location
}
