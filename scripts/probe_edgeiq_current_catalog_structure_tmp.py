import json
from pathlib import Path
from pprint import pprint

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "public" / "data" / "edgeiq_three_day_product_catalog_v1.json"

with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)

meetings = payload.get("meetings", [])
print(f"MEETINGS={len(meetings)}")

if not meetings:
    raise SystemExit("NO_MEETINGS_IN_CATALOG")

meeting = meetings[0]
print("\nFIRST_MEETING")
pprint(meeting, width=160, sort_dicts=False)

races = meeting.get("races", [])
print(f"\nFIRST_MEETING_RACES={len(races)}")

if races:
    print("\nFIRST_RACE")
    pprint(races[0], width=160, sort_dicts=False)

    runners = races[0].get("runners", [])
    print(f"\nFIRST_RACE_RUNNERS={len(runners)}")

    if runners:
        print("\nFIRST_RUNNER")
        pprint(runners[0], width=160, sort_dicts=False)

print("\nCATALOG_STRUCTURE_PROBE_PASS")
