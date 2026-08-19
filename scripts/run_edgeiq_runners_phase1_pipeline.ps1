$ErrorActionPreference = "Stop"

Write-Host "[EDGEIQ_RUNNERS_PHASE1_PIPELINE_V1_3] START"

$Root = "C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard"
Set-Location $Root

function Run-Step($label, $command) {
  Write-Host "`n[$label]"
  Invoke-Expression $command
}

Run-Step "BUILD PROFILE" 'python ".\scripts\build_edgeiq_runner_profile_engine_current.py"'

Run-Step "PROMOTE PROFILE OUTPUTS" '
Copy-Item ".\public\data\edgeiq_runner_profile_engine_v1_2.csv" ".\public\data\edgeiq_runner_profile_engine_current.csv" -Force
Copy-Item ".\public\data\edgeiq_runner_profile_engine_v1_2_summary.csv" ".\public\data\edgeiq_runner_profile_engine_current_summary.csv" -Force
'

Run-Step "BUILD FORM" 'python ".\scripts\build_edgeiq_runner_form_engine_current.py"'

Run-Step "PROMOTE FORM OUTPUTS" '
Copy-Item ".\public\data\edgeiq_runner_form_engine_v1_1.csv" ".\public\data\edgeiq_runner_form_engine_current.csv" -Force
Copy-Item ".\public\data\edgeiq_runner_form_engine_v1_1_summary.csv" ".\public\data\edgeiq_runner_form_engine_current_summary.csv" -Force
'

Run-Step "AUDIT FORM" 'python ".\scripts\audit_edgeiq_runner_form_engine_current.py"'
Run-Step "BUILD BASE HISTORY DETAIL SEED" 'python ".\scripts\build_edgeiq_runner_history_detail_v1_CHECKPOINT_BEFORE_FIGURE_RECOVERY_20260625.py"'
Run-Step "BUILD HISTORICAL FIGURE RECOVERY" 'python ".\scripts\build_edgeiq_historical_figure_recovery_v1.py"'
Run-Step "AUDIT HISTORICAL FIGURE RECOVERY" 'python ".\scripts\audit_edgeiq_historical_figure_recovery_v1.py"'
Run-Step "BUILD RACE STRENGTH HISTORY" 'python ".\scripts\build_edgeiq_race_strength_history_v1.py"'
Run-Step "BUILD RICH HISTORY DETAIL" 'python ".\scripts\build_edgeiq_runner_history_detail_v1.py"'
Run-Step "AUDIT RICH HISTORY DETAIL" 'python ".\scripts\audit_edgeiq_runner_history_detail_v1.py"'

$Required = @(
  ".\public\data\edgeiq_runner_profile_engine_current.csv",
  ".\public\data\edgeiq_runner_profile_engine_current_summary.csv",
  ".\public\data\edgeiq_runner_profile_engine_current_audit.csv",
  ".\public\data\edgeiq_runner_form_engine_current.csv",
  ".\public\data\edgeiq_runner_form_engine_current_summary.csv",
  ".\public\data\edgeiq_runner_form_engine_current_audit.csv",
  ".\public\data\edgeiq_runner_form_engine_current_audit_summary.csv",
  ".\public\data\edgeiq_historical_figure_recovery_v1.csv",
  ".\public\data\edgeiq_historical_figure_recovery_v1_summary.csv",
  ".\public\data\edgeiq_historical_figure_recovery_v1_audit.csv",
  ".\public\data\edgeiq_historical_figure_recovery_v1_audit_summary.csv",
  ".\public\data\edgeiq_race_strength_history_v1.csv",
  ".\public\data\edgeiq_runner_history_detail_v1.csv",
  ".\public\data\edgeiq_runner_history_detail_v1_summary.csv",
  ".\public\data\edgeiq_runner_history_detail_v1_audit.csv",
  ".\public\data\edgeiq_runner_history_detail_v1_audit_summary.csv"
)

Write-Host "`n[VERIFY OUTPUTS]"

$Inventory = foreach ($file in $Required) {
  if (Test-Path $file) {
    $item = Get-Item $file
    [PSCustomObject]@{
      file = $file
      exists = $true
      length = $item.Length
      last_write_time = $item.LastWriteTime
      status = "OK"
    }
  } else {
    [PSCustomObject]@{
      file = $file
      exists = $false
      length = 0
      last_write_time = ""
      status = "MISSING"
    }
  }
}

$Inventory | Export-Csv ".\public\data\edgeiq_runners_phase1_pipeline_inventory.csv" -NoTypeInformation
$Inventory | Format-Table -AutoSize

$Missing = $Inventory | Where-Object { $_.status -ne "OK" }
if ($Missing.Count -gt 0) {
  throw "[PIPELINE FAILED] Missing outputs detected."
}

Write-Host "`n[SUMMARY SNAPSHOT]"
Import-Csv ".\public\data\edgeiq_runner_profile_engine_current_summary.csv" | Format-List
Import-Csv ".\public\data\edgeiq_runner_form_engine_current_summary.csv" | Format-List
Import-Csv ".\public\data\edgeiq_runner_form_engine_current_audit_summary.csv" | Format-List
Import-Csv ".\public\data\edgeiq_historical_figure_recovery_v1_summary.csv" | Format-List
Import-Csv ".\public\data\edgeiq_historical_figure_recovery_v1_audit_summary.csv" | Format-List
Import-Csv ".\public\data\edgeiq_runner_history_detail_v1_summary.csv" | Format-List
Import-Csv ".\public\data\edgeiq_runner_history_detail_v1_audit_summary.csv" | Format-List

Write-Host "`n[BUILD CHECK]"
npm run build

Write-Host "`n[EDGEIQ_RUNNERS_PHASE1_PIPELINE_V1_3] COMPLETE"
