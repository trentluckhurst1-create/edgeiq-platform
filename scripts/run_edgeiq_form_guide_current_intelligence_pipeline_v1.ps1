$ErrorActionPreference = "Stop"

function Invoke-Stage {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Command,
    [Parameter(Mandatory = $true)][string[]]$Arguments
  )

  Write-Host ""
  Write-Host "================================================================================"
  Write-Host "EDGEIQ CURRENT INTELLIGENCE PIPELINE STAGE: $Name"
  Write-Host "================================================================================"
  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Stage failed: $Name (exit code $LASTEXITCODE)"
  }
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Invoke-Stage "catalog bridge" "python" @(".\scripts\build_edgeiq_current_intelligence_catalog_bridge_v1.py")
Invoke-Stage "checkpoint derived outputs" "python" @(".\scripts\checkpoint_edgeiq_current_intelligence_pipeline_outputs_v1.py")
Invoke-Stage "current race class correction v5.1" "python" @(".\scripts\build_edgeiq_current_race_class_correction_v5_1.py")
Invoke-Stage "current field projection v5.2" "python" @(".\scripts\build_edgeiq_current_field_projection_v5_2.py")
Invoke-Stage "current field rated price audit v5.2" "python" @(".\scripts\build_edgeiq_current_field_rated_price_audit_v5_2.py")
Invoke-Stage "current fair prices review v5.2" "python" @(".\scripts\build_edgeiq_current_fair_prices_review_v5_2.py")
Invoke-Stage "live runner board pre-probability pass" "python" @(".\scripts\build_edgeiq_live_runner_board_v1.py")
Invoke-Stage "probability engine v3" "python" @(".\scripts\build_edgeiq_probability_engine_v3.py")
Invoke-Stage "live runner board governed-price pass" "python" @(".\scripts\build_edgeiq_live_runner_board_v1.py")
Invoke-Stage "governed live runner board" "python" @(".\scripts\build_edgeiq_live_runner_board_governed_v1.py")
Invoke-Stage "edgeiq epi distribution v1" "python" @(".\scripts\build_edgeiq_epi_distribution_v1.py")
Invoke-Stage "speed map v3" "python" @(".\scripts\build_live_speed_map_engine_v3.py")
Invoke-Stage "current early speed v1" "python" @(".\scripts\build_edgeiq_current_early_speed_v1.py")
Invoke-Stage "current late speed v1" "python" @(".\scripts\build_edgeiq_current_late_speed_v1.py")
Invoke-Stage "current race shape v2" "python" @(".\scripts\build_edgeiq_current_race_shape_v2.py")
Invoke-Stage "current suitability v1" "python" @(".\scripts\build_edgeiq_current_suitability_v1.py")
Invoke-Stage "current form momentum v1" "python" @(".\scripts\build_edgeiq_current_form_momentum_v1.py")
Invoke-Stage "weather beta v1" "python" @(".\scripts\build_edgeiq_weather_beta_v1.py")
Invoke-Stage "current map v1" "python" @(".\scripts\build_edgeiq_current_map_v1.py")
Invoke-Stage "form guide enriched v2" "python" @(".\scripts\build_edgeiq_form_guide_enriched_v2.py")
Invoke-Stage "current race intelligence v1" "python" @(".\scripts\build_edgeiq_current_race_intelligence_v1.py")
Invoke-Stage "current intelligence audit" "python" @(".\scripts\audit_edgeiq_current_intelligence_pipeline_v1.py")
Invoke-Stage "current speed projection audit v1" "python" @(".\scripts\audit_edgeiq_current_speed_projection_v1.py")
Invoke-Stage "current intelligence v1.1 audit" "python" @(".\scripts\audit_edgeiq_current_intelligence_v1_1.py")
Invoke-Stage "beta intelligence completion audit v1" "python" @(".\scripts\audit_edgeiq_beta_intelligence_completion_v1.py")
Invoke-Stage "npm build" "npm" @("run", "build")

Write-Host ""
Write-Host "EDGEIQ CURRENT INTELLIGENCE PIPELINE COMPLETE"
