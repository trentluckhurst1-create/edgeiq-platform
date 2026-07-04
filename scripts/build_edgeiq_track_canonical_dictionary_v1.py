from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_track_canonical_dictionary_v1.csv"

SPONSORS = [
    "SPORTSBET", "LADBROKES", "BET365", "APIAM", "PICKLEBET",
    "TAB", "MRC", "VRC", "MELBOURNE RACING CLUB"
]

def clean(v):
    return "" if v is None else str(v).strip()

def canonical(track):
    t = clean(track).upper()
    original = t
    for s in SPONSORS:
        t = t.replace(s, "")
    t = t.replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()

    if "SANDOWN" in t and "HILLSIDE" in t:
        return "SANDOWN HILLSIDE"
    if "SANDOWN" in t and "LAKESIDE" in t:
        return "SANDOWN LAKESIDE"
    if "PAKENHAM" in t:
        return "PAKENHAM"
    if "GEELONG" in t:
        return "GEELONG"
    if "BENDIGO" in t:
        return "BENDIGO"
    if "HAMILTON" in t:
        return "HAMILTON"
    if "KILMORE" in t:
        return "KILMORE"
    if "BALLARAT" in t and "SYNTHETIC" in t:
        return "BALLARAT SYNTHETIC"
    if "BALLARAT" in t:
        return "BALLARAT"
    if "CAULFIELD HEATH" in t:
        return "CAULFIELD HEATH"
    if "CAULFIELD" in t:
        return "CAULFIELD"
    if "FLEMINGTON" in t:
        return "FLEMINGTON"
    if "MOONEE VALLEY" in t:
        return "MOONEE VALLEY"

    return t or original

tracks = {}
for p in DATA.glob("edgeiq_graphql_*_*_results_v1.csv"):
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            tr = clean(r.get("track"))
            if not tr:
                continue
            tracks[tr] = tracks.get(tr, 0) + 1

built_at = datetime.now(timezone.utc).isoformat()
rows = []
for raw, n in sorted(tracks.items(), key=lambda x: (-x[1], x[0])):
    rows.append({
        "raw_track": raw,
        "canonical_track": canonical(raw),
        "rows_seen": n,
        "review_status": "AUTO_SEEDED",
        "built_at": built_at,
    })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = ["raw_track","canonical_track","rows_seen","review_status","built_at"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print("[TRACK_CANONICAL_DICTIONARY_V1] COMPLETE")
print(f"tracks={len(rows)}")
print(f"output={OUT}")
