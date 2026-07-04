from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'loadCsv("/data/speed_map_report.csv"),',
'loadCsvOptional("/data/live_speed_map_v2.csv"),'
)

path.write_text(text, encoding="utf-8")

print("APP NOW USES live_speed_map_v2.csv")
