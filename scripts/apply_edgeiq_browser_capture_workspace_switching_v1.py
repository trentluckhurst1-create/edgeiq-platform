from pathlib import Path
path = Path('scripts/capture_edgeiq_final_live_data_population_v1.cjs')
text = path.read_text(encoding='utf-8')
old = """  await page.addInitScript(({ key, state }) => {\n    window.localStorage.setItem(key, JSON.stringify(state));\n  }, { key: STORAGE_KEY, state: selectedContext });\n\n  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 });\n  await page.waitForTimeout(2500);\n"""
new = """  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 });\n  await page.waitForTimeout(1200);\n"""
if old not in text:
    raise SystemExit('Capture init block not found')
path.write_text(text.replace(old, new), encoding='utf-8')
print('EDGEIQ_BROWSER_CAPTURE_WORKSPACE_SWITCHING_PATCHED')
