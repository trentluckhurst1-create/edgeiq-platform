from pathlib import Path
import re

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = '''return speedRows
        .filter((row) => {
          return text(row.race_date) === currentRace.raceDate && cleanTrack(row.track) === cleanTrack(currentRace.track) && (num(row.race_no) ?? 0) === currentRace.raceNo;
        })'''

new = '''return speedRows
        .filter((row) => {
          const rowDate = text(row.race_date);
          const dateOk = !rowDate || rowDate === currentRace.raceDate;
          return dateOk && cleanTrack(row.track) === cleanTrack(currentRace.track) && (num(row.race_no) ?? 0) === currentRace.raceNo;
        })'''

if old not in text:
    raise SystemExit("CURRENT SPEED ROW FILTER BLOCK NOT FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("CURRENT SPEED ROW FILTER PATCHED")
print("V4 rows without race_date will now render")
print("=" * 80)
