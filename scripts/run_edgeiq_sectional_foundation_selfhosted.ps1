param(
  [string]$ProjectRoot = 'C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM'
)

$ErrorActionPreference = 'Stop'
Set-Location $ProjectRoot

Write-Host '=== EDGEIQ SECTIONAL SELF-HOSTED PIPELINE ==='
Write-Host "ROOT=$ProjectRoot"

# Keep GitHub as canonical source for scripts/manifest only; do not hard-reset local data.
git fetch origin

git restore --source=origin/main --worktree --staged -- `
  scripts/edgeiq_sectional_pipeline_manifest.txt `
  scripts/run_edgeiq_sectional_foundation_selfhosted.ps1

$manifest = Join-Path $ProjectRoot 'scripts\edgeiq_sectional_pipeline_manifest.txt'
if (-not (Test-Path $manifest)) { throw "Missing manifest: $manifest" }

$scripts = Get-Content $manifest |
  ForEach-Object { $_.Trim() } |
  Where-Object { $_ -and -not $_.StartsWith('#') }

foreach ($script in $scripts) {
  Write-Host "`n=== SYNC $script ==="
  git restore --source=origin/main --worktree --staged -- $script
  $full = Join-Path $ProjectRoot ($script -replace '/', '\')
  if (-not (Test-Path $full)) { throw "Missing pipeline script after sync: $full" }
  Write-Host "=== RUN $script ==="
  python $full
  if ($LASTEXITCODE -ne 0) { throw "Pipeline failed: $script ($LASTEXITCODE)" }
}

Write-Host "`n=== SECTIONAL SUMMARY FILES ==="
Get-ChildItem (Join-Path $ProjectRoot 'public\data') -Filter 'edgeiq_sectional_*summary*.csv' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 30 FullName,Length,LastWriteTime |
  Format-Table -AutoSize

Write-Host '=== EDGEIQ SECTIONAL SELF-HOSTED PIPELINE COMPLETE ==='
