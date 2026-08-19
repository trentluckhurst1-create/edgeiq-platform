from pathlib import Path
p=Path('scripts/audit_edgeiq_full_product_population_v1.py')
s=p.read_text(encoding='utf-8')
s=s.replace('    epi_ws = load_csv_index(DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv")\n    fair = load_csv_index(DATA / "edgeiq_fair_price_v7_2.csv")', '    epi_ws = load_csv_index(DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv")\n    current_epi_feed = load_projection(DATA / "edgeiq_epi_current_rating_v1.json")\n    fair = load_csv_index(DATA / "edgeiq_fair_price_v7_2.csv")')
s=s.replace('        ep = epi_ws.get(k, {})\n        fp = fair.get(k, {})', '        ep = epi_ws.get(k, {})\n        cep = current_epi_feed.get(k, {})\n        fp = fair.get(k, {})')
s=s.replace('        epi_value = ep.get("current_epi") or get_value(f.get("epi"))\n        eri_value = ep.get("current_eri") or ep.get("eri")', '        epi_value = ep.get("current_epi") or get_value(f.get("epi")) or cep.get("value") or get_value(cep.get("epi"))\n        eri_value = ep.get("current_eri") or ep.get("eri") or cep.get("eriValue") or get_value(cep.get("eri"))')
s=s.replace('Current race fields and as-of form/speed/map joins were repaired; current EPI/fair-price upstream outputs remain absent for 2026-07-26.', 'Current race fields and as-of form/speed/map joins were repaired; EPI/ERI/fair-price are governed-limited by prior performance evidence rather than blank upstream publication.')
p.write_text(s,encoding='utf-8')
print('PATCHED full product audit current ERI reader')
