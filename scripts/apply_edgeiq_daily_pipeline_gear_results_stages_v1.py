from pathlib import Path

path = Path('scripts/run_edgeiq_daily_rolling_product_pipeline_v1.py')
text = path.read_text(encoding='utf-8')
old = '''    "scripts/build_edgeiq_insights_terminal_feed_v1.py",
    "scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py",
    "scripts/build_edgeiq_on_track_weather_governed_v1_2.py",
]'''
new = '''    "scripts/build_edgeiq_insights_terminal_feed_v1.py",
    "scripts/build_edgeiq_gear_terminal_feed_v1.py",
    "scripts/build_edgeiq_meeting_results_terminal_feed_v1.py",
    "scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py",
    "scripts/build_edgeiq_on_track_weather_governed_v1_2.py",
]'''
if old not in text:
    raise SystemExit('Pipeline stage block not found or already patched')
path.write_text(text.replace(old, new), encoding='utf-8')
print('EDGEIQ_DAILY_PIPELINE_GEAR_RESULTS_STAGES_PATCHED')
