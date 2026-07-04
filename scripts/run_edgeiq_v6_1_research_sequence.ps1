Write-Host "[EDGEIQ_V6_1_RESEARCH_SEQUENCE] START"

python ".\scripts\build_edgeiq_historical_performance_rating_v6_1_research.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python ".\scripts\build_edgeiq_current_field_projection_v6_1_research_replay.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python ".\scripts\build_edgeiq_current_fair_prices_v6_1_research_replay.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python ".\scripts\build_edgeiq_live_v6_1_research_vs_production_comparison_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[EDGEIQ_V6_1_RESEARCH_SEQUENCE] COMPLETE"
Import-Csv ".\public\data\edgeiq_live_v6_1_research_action_summary_v1.csv" | Format-Table -AutoSize
