from pathlib import Path
path = Path('scripts/capture_edgeiq_final_live_data_population_v1.cjs')
text = path.read_text(encoding='utf-8')
text = text.replace("url.includes('/data/') || url.includes('/performance-intelligence/')", "url.includes('/data/') || url.includes('/performance-intelligence/edgeiq')")
text = text.replace("const dataNetwork = network.filter((row) => row.url.includes('/data/') || row.url.includes('/performance-intelligence/'));", "const dataNetwork = network.filter((row) => row.url.includes('/data/') || row.url.includes('/performance-intelligence/edgeiq'));")
path.write_text(text, encoding='utf-8')
print('EDGEIQ_BROWSER_CAPTURE_DATA_REQUEST_FILTER_PATCHED')
