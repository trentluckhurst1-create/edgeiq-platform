param([string]$Mode = "DAILY", [string]$RepoRoot = "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
$ErrorActionPreference = "Stop"
Push-Location $RepoRoot
try { python .\scripts\run_edgeiq_daily_operations_engine_v1.py --mode $Mode } finally { Pop-Location }
