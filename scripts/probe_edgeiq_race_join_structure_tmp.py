from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
BUILDER = ROOT / "scripts" / "build_edgeiq_epi_workspace_terminal_feed_v1.py"

spec = importlib.util.spec_from_file_location(
    "edgeiq_epi_structure_probe",
    BUILDER,
)

if spec is None or spec.loader is None:
    raise SystemExit("BUILDER_IMPORT_FAILED")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

catalog = module.read_json(module.CATALOG)
form_payload = module.read_json(module.FORM_GUIDE)

catalog_pairs = module.catalog_races(catalog)
form_races = (
    form_payload.get("races", [])
    if isinstance(form_payload, dict)
    else []
)

print("EDGEIQ RACE JOIN STRUCTURE PROBE")
print("=" * 100)

if catalog_pairs:
    meeting, race = catalog_pairs[0]

    print(f"CATALOG_MEETING_KEYS={sorted(meeting.keys())}")
    print(f"CATALOG_RACE_KEYS={sorted(race.keys())}")

    print("CATALOG_MEETING_VALUES")
    for key in [
        "date",
        "raceDate",
        "meeting",
        "meetingName",
        "track",
        "venue",
        "meetingKey",
    ]:
        print(f"  {key}={meeting.get(key)!r}")

    print("CATALOG_RACE_VALUES")
    for key in [
        "date",
        "raceDate",
        "meeting",
        "meetingName",
        "track",
        "venue",
        "raceNumber",
        "raceNo",
        "number",
        "raceKey",
    ]:
        print(f"  {key}={race.get(key)!r}")
else:
    print("NO_CATALOG_RACES")

print("")

first_form_race = next(
    (
        race
        for race in form_races
        if isinstance(race, dict)
    ),
    None,
)

if first_form_race:
    print(f"FORM_RACE_KEYS={sorted(first_form_race.keys())}")

    print("FORM_RACE_VALUES")
    for key in [
        "date",
        "raceDate",
        "meeting",
        "meetingName",
        "track",
        "venue",
        "raceNumber",
        "raceNo",
        "number",
        "raceKey",
    ]:
        print(f"  {key}={first_form_race.get(key)!r}")
else:
    print("NO_FORM_RACES")

print("EDGEIQ_RACE_JOIN_STRUCTURE_PROBE_PASS")
