$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $Root

Write-Host "EDGEIQ_ENGINEERING_SPECIFICATION_LIBRARY_V1_VALIDATION"

$auditScript = Join-Path $Root "scripts\audit_edgeiq_engineering_specification_library_v1.py"
python $auditScript

$inventory = Join-Path $Root "public\data\edgeiq_engineering_specification_library_v1_inventory.csv"
if (Test-Path $inventory) {
  Write-Host ""
  Write-Host "SPECIFICATION INVENTORY"
  Import-Csv $inventory | Format-Table spec_id,workspace,bytes,lines,headings,typescript_blocks,json_blocks,status -AutoSize
} else {
  throw "Inventory CSV was not created: $inventory"
}

$allowedMarkers = @(
  "docs/",
  "scripts/checkpoint_edgeiq_engineering_specification_library_v1.py",
  "scripts/audit_edgeiq_engineering_specification_library_v1.py",
  "scripts/validate_edgeiq_engineering_specification_library_v1.ps1",
  "public/data/edgeiq_engineering_specification_library_v1_"
)

$statusLines = git status --short
$outside = @()
foreach ($line in $statusLines) {
  $normalised = $line.Replace("\", "/")
  $allowed = $false
  foreach ($marker in $allowedMarkers) {
    if ($normalised.Contains($marker)) {
      $allowed = $true
      break
    }
  }
  if (-not $allowed -and $normalised.Trim().Length -gt 0) {
    $outside += $line
  }
}

Write-Host ""
Write-Host "WORKING TREE SAFETY"
if ($outside.Count -gt 0) {
  Write-Host "Pre-existing/unrelated dirty entries detected. Validation records them but does not reset, restore, clean, stage or delete them."
  $outside | ForEach-Object { Write-Host "  $_" }
} else {
  Write-Host "No dirty entries outside the engineering specification recovery paths."
}

Write-Host ""
Write-Host "EDGEIQ_ENGINEERING_SPECIFICATION_LIBRARY_V1_VALIDATION_COMPLETE"
