$ErrorActionPreference = "Stop"

Write-Host "[EDGEIQ_V6_RESEARCH_SEQUENCE] START"

python ".\scripts\build_edgeiq_historical_performance_rating_v6_research.py"
python ".\scripts\build_edgeiq_current_field_projection_v6_research_replay.py"
python ".\scripts\build_edgeiq_current_fair_prices_v6_research_replay.py"
python ".\scripts\build_edgeiq_live_v6_research_vs_production_comparison_v1.py"

Write-Host "[EDGEIQ_V6_RESEARCH_SEQUENCE] COMPLETE"
