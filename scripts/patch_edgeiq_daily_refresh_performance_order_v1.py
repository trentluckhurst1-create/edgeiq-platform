from pathlib import Path
p=Path('scripts/run_edgeiq_daily_product_refresh_v1.py')
s=p.read_text(encoding='utf-8')
old="'scripts/build_edgeiq_current_map_v1.py', 'scripts/build_edgeiq_performance_recovery_current_lineage_v1.py', 'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_map_terminal_feed_v1.py'"
new="'scripts/build_edgeiq_current_map_v1.py', 'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_performance_recovery_current_lineage_v1.py', 'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_map_terminal_feed_v1.py'"
if old not in s and new not in s:
    raise SystemExit('daily refresh target order not found')
if old in s:
    s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('PATCHED daily refresh: seed form enrichment before performance recovery, final enrichment after recovery')
