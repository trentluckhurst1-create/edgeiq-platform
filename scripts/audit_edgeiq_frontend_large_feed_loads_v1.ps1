$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Component = Join-Path $Root "src\components\RaceIntelligenceScreen.tsx"
$DataDir = Join-Path $Root "public\data"
$Out = Join-Path $DataDir "edgeiq_frontend_large_feed_loads_audit_v1.csv"

$MustCheck = @(
  "edgeiq_form_sectional_profile_feed_v1.csv",
  "edgeiq_results_master_v1.csv",
  "edgeiq_speed_master_v1.csv",
  "edgeiq_standardised_sectionals_v1.csv",
  "edgeiq_gear_profile_feed_v1.csv",
  "edgeiq_results_terminal_feed_v1.csv"
)

$Source = Get-Content -LiteralPath $Component -Raw
$Referenced = [regex]::Matches($Source, "/data/([^`"']+?\.csv)") | ForEach-Object { Split-Path $_.Groups[1].Value -Leaf }
$Targets = @($MustCheck + $Referenced) | Sort-Object -Unique
$Rows = New-Object System.Collections.Generic.List[object]

function Get-CsvRowCount {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  $count = 0
  $reader = [System.IO.File]::OpenText($Path)
  try {
    while ($null -ne $reader.ReadLine()) { $count++ }
  } finally {
    $reader.Dispose()
  }
  return [Math]::Max(0, $count - 1)
}

function Get-Risk {
  param([bool]$Fetched, [Nullable[int]]$Rows)
  if (-not $Fetched) { return "NONE_NOT_FETCHED" }
  if ($Rows -eq $null) { return "UNKNOWN_MISSING_FILE" }
  if ($Rows -gt 10000) { return "HIGH_BLOCK_FRONTEND" }
  if ($Rows -gt 5000) { return "MEDIUM_REVIEW" }
  return "LOW"
}

foreach ($File in $Targets) {
  $escaped = [regex]::Escape($File)
  $fetched = $Source -match $escaped
  $fileKey = ""
  $stateVariable = ""
  $componentUseEffect = ""

  if ($fetched) {
    $fileMatch = [regex]::Match($Source, "([A-Za-z0-9_]+)\s*:\s*`"?/data/$escaped`"?")
    if ($fileMatch.Success) {
      $fileKey = $fileMatch.Groups[1].Value
      $stateMatch = [regex]::Match($Source, "const\s+\[([A-Za-z0-9_]+),\s*set[A-Za-z0-9_]+\]\s*=\s*useState<Row\[\]>\(\[\]\);[\s\S]{0,2500}loadCsv\(FILES\.$fileKey\)")
      if ($stateMatch.Success) { $stateVariable = $stateMatch.Groups[1].Value }
      $loaderMatch = [regex]::Match($Source, "loadCsv\(FILES\.$fileKey\)")
      if ($loaderMatch.Success) { $componentUseEffect = "RaceIntelligenceScreen useEffect CSV loader" }
    }
  }

  $path = Join-Path $DataDir $File
  $rowCount = Get-CsvRowCount -Path $path
  $risk = Get-Risk -Fetched $fetched -Rows $rowCount
  $Rows.Add([pscustomobject]@{
    file = $File
    fetched_by_frontend = if ($fetched) { "YES" } else { "NO" }
    state_variable = $stateVariable
    estimated_csv_rows = if ($rowCount -eq $null) { "" } else { $rowCount }
    component_or_use_effect = $componentUseEffect
    risk_level = $risk
  })
}

$Rows | Export-Csv -LiteralPath $Out -NoTypeInformation
$Rows | Format-Table -AutoSize
Write-Host "Wrote $Out"

$Bad = $Rows | Where-Object { $_.fetched_by_frontend -eq "YES" -and $_.risk_level -eq "HIGH_BLOCK_FRONTEND" }
if ($Bad.Count -gt 0) {
  Write-Warning "Frontend is loading warehouse-scale CSV feeds. This must be fixed."
}
