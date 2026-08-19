from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
FORM_GUIDE = ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v2.json"
OUT = ROOT / "docs" / "full-product-implementation" / "FORM_GUIDE_DATE_COVERAGE_AUDIT.txt"

if not FORM_GUIDE.exists():
    raise SystemExit(f"FORM_GUIDE_NOT_FOUND: {FORM_GUIDE}")

with FORM_GUIDE.open("r", encoding="utf-8") as f:
    payload = json.load(f)

races = payload.get("races", []) if isinstance(payload, dict) else []

dates = []
meetings = Counter()
date_meeting = Counter()

for race in races:
    if not isinstance(race, dict):
        continue

    date = str(race.get("raceDate") or "")
    meeting = str(race.get("meeting") or "")

    dates.append(date)
    meetings[meeting] += 1
    date_meeting[(date, meeting)] += 1

unique_dates = sorted(set(d for d in dates if d))

report = []
report.append("EDGEIQ FORM GUIDE DATE COVERAGE AUDIT")
report.append("=" * 120)
report.append(f"FILE={FORM_GUIDE}")
report.append(f"TOTAL_RACES={len(races)}")
report.append(f"UNIQUE_DATES={len(unique_dates)}")
report.append("")

if unique_dates:
    report.append(f"EARLIEST_DATE={unique_dates[0]}")
    report.append(f"LATEST_DATE={unique_dates[-1]}")
else:
    report.append("NO_DATES_FOUND")

report.append("")
report.append("DATES")
report.append("-" * 120)

for d in unique_dates:
    count = sum(1 for x in dates if x == d)
    report.append(f"{d} : {count} races")

report.append("")
report.append("MEETINGS")
report.append("-" * 120)

for meeting, count in meetings.most_common():
    report.append(f"{meeting} : {count}")

report.append("")
report.append("DATE / MEETING COMBINATIONS")
report.append("-" * 120)

for (d, m), count in sorted(date_meeting.items()):
    report.append(f"{d} | {m} | {count} races")

today = "2026-07-20"

report.append("")
report.append("=" * 120)
report.append(f"HAS_{today}={'YES' if today in unique_dates else 'NO'}")

if today in unique_dates:
    report.append("")
    report.append("2026-07-20 MEETINGS")
    report.append("-" * 120)
    for (d, m), count in sorted(date_meeting.items()):
        if d == today:
            report.append(f"{m} : {count} races")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print(f"WROTE={OUT}")
print("FORM_GUIDE_DATE_COVERAGE_AUDIT_PASS")
