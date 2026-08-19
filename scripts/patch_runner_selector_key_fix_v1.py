from pathlib import Path

p = Path(".\\src\\components\\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

s = s.replace(
'''                const key = runnerKey(runner.row);''',
'''                const key = String(runner.row.race_key || "") + "_" + String(runner.row.horse || runner.row.runner || runner.row.runner_name || "").toUpperCase().replace(/[^A-Z0-9]/g, "");'''
)

p.write_text(s, encoding="utf-8")
print("[RUNNER_SELECTOR_KEY_FIX] COMPLETE")
