param(
  [string]$Workspace = "BETA-005"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$ProgressPath = Join-Path $Root "public\data\edgeiq_remaining_beta_autonomous_completion_v1_progress.txt"
$JsonPath = Join-Path $Root "public\data\edgeiq_remaining_beta_autonomous_completion_v1_progress.json"

New-Item -ItemType Directory -Force -Path (Split-Path $ProgressPath) | Out-Null

$now = (Get-Date).ToString("o")
$payload = [ordered]@{
  program = "EDGEIQ_REMAINING_BETA_AUTONOMOUS_COMPLETION_V1"
  last_updated_at = $now
  current_workspace = $Workspace
  overall_status = "RUNNER_AVAILABLE"
  note = "Manual/autonomous execution record. Workspace-specific scripts own implementation and audits."
}

$payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
@(
  "EDGEIQ_REMAINING_BETA_AUTONOMOUS_COMPLETION_V1_RUNNER_AVAILABLE",
  "updated_at=$now",
  "current_workspace=$Workspace",
  "root=$Root"
) | Set-Content -LiteralPath $ProgressPath -Encoding UTF8

Write-Output "EDGEIQ_REMAINING_BETA_AUTONOMOUS_COMPLETION_V1_RUNNER_AVAILABLE"
