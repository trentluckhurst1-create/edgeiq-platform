from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

MASTER = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_horse_universe_audit_v1.csv"
SUMMARY = DATA / "edgeiq_horse_universe_audit_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def is_win(v):
    return clean(v) in {"1", "1st", "1ST"}

def is_place(v):
    return clean(v) in {"1", "2", "3", "1st", "2nd", "3rd", "1ST", "2ND", "3RD"}

horses = {}

with MASTER.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        horse = clean(r.get("horse"))
        if not horse:
            continue

        key = horse.upper()
        h = horses.setdefault(key, {
            "horse": horse,
            "starts": 0,
            "wins": 0,
            "places": 0,
            "years": set(),
            "tracks": set(),
            "trainers": set(),
            "jockeys": set(),
            "first_start": "",
            "last_start": "",
            "sp_rows": 0,
            "rail_rows": 0,
        })

        h["starts"] += 1

        if is_win(r.get("finish")):
            h["wins"] += 1

        if is_place(r.get("finish")):
            h["places"] += 1

        d = clean(r.get("race_date"))
        if d:
            h["years"].add(d[:4])
            if not h["first_start"] or d < h["first_start"]:
                h["first_start"] = d
            if not h["last_start"] or d > h["last_start"]:
                h["last_start"] = d

        for col, bucket in [
            ("track", "tracks"),
            ("trainer", "trainers"),
            ("jockey", "jockeys"),
        ]:
            v = clean(r.get(col))
            if v:
                h[bucket].add(v.upper())

        if clean(r.get("starting_price_decimal")):
            h["sp_rows"] += 1

        if clean(r.get("rail_position")):
            h["rail_rows"] += 1

rows = []
for h in horses.values():
    starts = h["starts"]
    rows.append({
        "horse": h["horse"],
        "starts": starts,
        "wins": h["wins"],
        "places": h["places"],
        "win_pct": round((h["wins"] / starts) * 100, 2) if starts else 0,
        "place_pct": round((h["places"] / starts) * 100, 2) if starts else 0,
        "years_seen": len(h["years"]),
        "first_start": h["first_start"],
        "last_start": h["last_start"],
        "tracks_seen": len(h["tracks"]),
        "trainers_seen": len(h["trainers"]),
        "jockeys_seen": len(h["jockeys"]),
        "sp_rows": h["sp_rows"],
        "rail_rows": h["rail_rows"],
    })

rows.sort(key=lambda x: x["starts"], reverse=True)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["horse"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

built_at = datetime.now(timezone.utc).isoformat()

summary_rows = [
    {"metric": "status", "value": "EDGEIQ_HORSE_UNIVERSE_AUDIT_V1_BUILT"},
    {"metric": "unique_horses", "value": len(rows)},
    {"metric": "total_starts", "value": sum(int(r["starts"]) for r in rows)},
    {"metric": "horses_1_start", "value": sum(1 for r in rows if int(r["starts"]) == 1)},
    {"metric": "horses_5_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 5)},
    {"metric": "horses_10_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 10)},
    {"metric": "horses_20_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 20)},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[HORSE_UNIVERSE_AUDIT_V1] COMPLETE")
print(f"horses={len(rows)}")
print(f"output={OUT}")
