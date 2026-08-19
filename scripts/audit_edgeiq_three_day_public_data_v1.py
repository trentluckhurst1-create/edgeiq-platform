from __future__ import annotations

import csv
import json
import re
from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
data_dir = root / "public" / "data"

date_pattern = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
meeting_pattern = re.compile(
    r"\b(FLEMINGTON|CAULFIELD(?: HEATH)?|SPORTSBET CAULFIELD|"
    r"SANDOWN|LADBROKES PARK|MORNINGTON|MOONEE VALLEY)\b",
    re.IGNORECASE,
)

for path in sorted(
    data_dir.glob("*"),
    key=lambda item: item.stat().st_mtime,
    reverse=True,
)[:120]:
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

    print()
    print(f"FILE: {path.name}")
    print(f"DATES: {', '.join(dates[:20])}")
    print(f"MEETINGS: {', '.join(meetings[:20])}")
