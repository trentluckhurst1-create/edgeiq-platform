param(
    [string]$RepoRoot = "C:\EDGEIQ_PROFITABILITY_RESEARCH",
    [string]$SourceDir = "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data",
    [string]$Out = "outputs/research/issue10_pre2022_partition"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location $RepoRoot
try {
    python .\scripts\research\build_issue10_pre2022_pit_partition.py `
        --source-dir $SourceDir `
        --out $Out `
        --cutoff-date 2022-01-01 `
        --allow-local-pre2022-monthly-export
}
finally {
    Pop-Location
}
