from pathlib import Path
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
TARGET = ROOT / "scripts" / "build_edgeiq_vic_three_day_meeting_universe.py"
OUT = ROOT / "docs" / "meeting_universe_builder_field_trace_v1.txt"

KEYWORDS = [
    "read_csv",
    "DictReader",
    "edgeiq_live_runner_board",
    "edgeiq_live_runner_board_governed",
    "edgeiq_vic_live_fields_synced",
    "edgeiq_graphql_getRacesForMeet_meeting_warehouse_v1",
    "edgeiq_graphql_master_v2",
    "edgeiq_vic_three_day_meeting_universe.csv",
    "barrier",
    "jockey",
    "trainer",
    "weight",
    "silk",
    "market",
    "to_csv",
    "DictWriter",
]

src = TARGET.read_text(encoding="utf-8-sig", errors="ignore").splitlines()

lines = []
lines.append("EDGEIQ MEETING UNIVERSE BUILDER TRACE")
lines.append("=" * 120)
lines.append(f"FILE={TARGET}")

for keyword in KEYWORDS:
    lines.append("")
    lines.append("=" * 120)
    lines.append(f"KEYWORD={keyword}")

    found = False

    for i, line in enumerate(src, start=1):
        if keyword.lower() in line.lower():
            found = True
            start = max(1, i - 6)
            end = min(len(src), i + 8)

            lines.append(f"--- Around line {i} ---")

            for j in range(start, end + 1):
                lines.append(f"{j:05d}: {src[j-1]}")

    if not found:
        lines.append("NOT FOUND")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print("")
print(f"OUTPUT={OUT}")
print("EDGEIQ_MEETING_UNIVERSE_BUILDER_TRACE_COMPLETE")
