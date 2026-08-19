from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = '''          loadCsvOptional("/data/pace_pressure_report.csv"),
          loadCsvOptional("/data/edgeiq_sectional_tempo_engine_v1.csv"),'''

new = '''          loadCsvOptional("/data/pace_pressure_report.csv"),
          loadCsvOptional("/data/edgeiq_race_shape_engine_v1.csv"),
          loadCsvOptional("/data/edgeiq_sectional_tempo_engine_v1.csv"),'''

if old not in text:
    raise SystemExit("CSV LOAD ANCHOR NOT FOUND")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("INSERTED race shape CSV INTO Promise.all")
