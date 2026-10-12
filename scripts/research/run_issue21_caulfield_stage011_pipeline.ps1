param(
  [string]$LiveDir = "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1",
  [string]$Lab245bDir = "C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b",
  [string]$ModelDir = "C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage011_research_2024_fit",
  [string]$OutputDir = "outputs\research\issue21_caulfield_stage011_pipeline",
  [switch]$CaptureBrowser,
  [switch]$SkipScoring
)

$ErrorActionPreference = "Stop"
$argsList = @(
  "scripts\research\run_issue21_caulfield_stage011_pipeline.py",
  "--live-dir", $LiveDir,
  "--lab245b-dir", $Lab245bDir,
  "--model-dir", $ModelDir,
  "--output-dir", $OutputDir
)
if ($CaptureBrowser) { $argsList += "--capture-browser" }
if ($SkipScoring) { $argsList += "--skip-scoring" }
python @argsList
