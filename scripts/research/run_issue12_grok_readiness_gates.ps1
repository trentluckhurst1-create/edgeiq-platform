param(
    [string]$RepoRoot = "C:\EDGEIQ_PROFITABILITY_RESEARCH",
    [string]$Issue10Dir = "outputs/research/issue10_pre2022_partition",
    [string]$Out = "outputs/research/issue12_grok_readiness"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location $RepoRoot
try {
    python .\scripts\research\run_issue12_grok_readiness_gates.py `
        --issue10-dir $Issue10Dir `
        --out $Out
}
finally {
    Pop-Location
}
