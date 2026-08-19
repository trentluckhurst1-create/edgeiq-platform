from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "EDGEIQ_FINAL_MEETING_WIRING_SOURCE_20260710_121543.txt"

source_files = [
    ROOT / "src/edgeiq-os/race/components/MeetingsWorkspace.tsx",
    ROOT / "src/edgeiq-os/services/weather/EdgeiqWeatherService.ts",
    ROOT / "src/edgeiq-os/services/race-file-v2.ts",
    ROOT / "src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts",
    ROOT / "src/edgeiq-os/race/RaceFileV3.tsx",
]

lines: list[str] = [
    "EDGEIQ FINAL MEETING WIRING SOURCE",
    "=" * 80,
    "",
]

for path in source_files:
    lines.extend([
        "",
        "=" * 80,
        f"FILE: {path.relative_to(ROOT)}",
        "=" * 80,
    ])

    if not path.exists():
        lines.append("MISSING")
        continue

    lines.append(path.read_text(encoding="utf-8", errors="ignore"))

lines.extend([
    "",
    "=" * 80,
    "CANDIDATE PUBLIC DATA FILES",
    "=" * 80,
])

tokens = (
    "meeting",
    "race",
    "field",
    "snapshot",
    "universe",
    "racebook",
    "three_day",
    "three-day",
    "current",
    "live",
)

candidates = []

for path in (ROOT / "public/data").glob("*"):
    if not path.is_file():
        continue

    lower = path.name.lower()

    if not any(token in lower for token in tokens):
        continue

    candidates.append(path)

for path in sorted(
    candidates,
    key=lambda item: item.stat().st_mtime,
    reverse=True,
):
    stat = path.stat()

    lines.append(
        f"{path.name} | {stat.st_size:,} bytes | "
        f"{stat.st_mtime_ns}"
    )

lines.extend([
    "",
    "=" * 80,
    "CANDIDATE DATA CONTENT SUMMARY",
    "=" * 80,
])

date_pattern = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
meeting_pattern = re.compile(
    r"\b("
    r"FLEMINGTON|"
    r"CAULFIELD(?:\s+HEATH)?|"
    r"SPORTSBET\s+CAULFIELD(?:\s+HEATH)?|"
    r"SANDOWN(?:\s+HILLSIDE|\s+LAKESIDE)?|"
    r"LADBROKES\s+PARK|"
    r"MORNINGTON|"
    r"MOONEE\s+VALLEY|"
    r"PAKENHAM|"
    r"CRANBOURNE|"
    r"BALLARAT|"
    r"BENDIGO|"
    r"GEELONG"
    r")\b",
    re.IGNORECASE,
)

for path in sorted(
    candidates,
    key=lambda item: item.stat().st_mtime,
    reverse=True,
)[:80]:
    if path.suffix.lower() not in {".json", ".csv", ".txt"}:
        continue

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    dates = sorted(set(date_pattern.findall(text)))
    meetings = sorted(
        {
            match.group(0).upper()
            for match in meeting_pattern.finditer(text)
        }
    )

    if not dates and not meetings:
        continue

    lines.extend([
        "",
        f"FILE: {path.name}",
        f"DATES: {', '.join(dates[:15])}",
        f"MEETINGS: {', '.join(meetings[:30])}",
    ])

OUT.write_text("\n".join(lines), encoding="utf-8")

print(f"[EDGEIQ] Final wiring source written: {OUT}")
