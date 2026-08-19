import csv
from pathlib import Path

path = Path(
    r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
    r"\public\data\edgeiq_epi_workspace_terminal_feed_v1.csv"
)

with path.open("r", encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))

race_keys = sorted({
    str(row.get("race_key") or "").strip()
    for row in rows
    if str(row.get("race_key") or "").strip()
})

meeting_keys = sorted({
    str(row.get("meeting_key") or "").strip()
    for row in rows
    if str(row.get("meeting_key") or "").strip()
})

print("RACE_KEYS")
for key in race_keys:
    print(repr(key))

print()
print("MEETING_KEYS")
for key in meeting_keys:
    print(repr(key))
