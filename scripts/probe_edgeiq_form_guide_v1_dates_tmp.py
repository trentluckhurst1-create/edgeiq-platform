import json
from pathlib import Path

path = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data\edgeiq_form_guide_enriched_v1.json")

if not path.exists():
    raise SystemExit(f"FILE_NOT_FOUND: {path}")

with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)

races = payload.get("races", []) if isinstance(payload, dict) else []
dates = sorted({
    str(race.get("raceDate") or "")
    for race in races
    if isinstance(race, dict) and race.get("raceDate")
})

print(f"FILE={path}")
print(f"RACES={len(races)}")
print(f"DATES={dates}")
print("FORM_GUIDE_V1_DATE_PROBE_PASS")
