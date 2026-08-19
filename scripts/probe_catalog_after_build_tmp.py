import json
from pathlib import Path

p = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data\edgeiq_three_day_product_catalog_v1.json")

j = json.loads(p.read_text(encoding="utf-8"))

meetings = j.get("meetings", [])

print("MEETINGS", len(meetings))

for m in meetings:
    print(
        m.get("meeting"),
        "raceCount=", m.get("raceCount"),
        "actual=", len(m.get("races", []))
    )
