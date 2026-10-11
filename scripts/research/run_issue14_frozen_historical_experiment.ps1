param(
    [string]$RepoRoot = "C:\EDGEIQ_PROFITABILITY_RESEARCH",
    [string]$PitMatrix = "outputs/research/issue10_pre2022_partition/ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv",
    [string]$Attestation = "",
    [string]$ExecutionApproval = "",
    [string]$Out = "outputs/research/issue14_final_experiment_gate",
    [switch]$Execute
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location $RepoRoot
try {
    $argsList = @(
        ".\scripts\research\run_issue14_frozen_historical_experiment.py",
        "--pit-matrix", $PitMatrix,
        "--out", $Out
    )
    if ($Attestation -ne "") {
        $argsList += @("--attestation", $Attestation)
    }
    if ($ExecutionApproval -ne "") {
        $argsList += @("--execution-approval", $ExecutionApproval)
    }
    if ($Execute) {
        $argsList += "--execute"
    }
    python @argsList
}
finally {
    Pop-Location
}
