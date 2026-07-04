from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

MASTER = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_jockey_universe_audit_v1.csv"
SUMMARY = DATA / "edgeiq_jockey_universe_audit_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def is_win(v):
    return clean(v).upper() in {"1", "1ST"}

def is_place(v):
    return clean(v).upper() in {"1", "2", "3", "1ST", "2ND", "3RD"}

jockeys = {}

with MASTER.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        jockey = clean(r.get("jockey"))
        if not jockey:
            continue

        key = jockey.upper()
        j = jockeys.setdefault(key, {
            "jockey": jockey,
            "rides": 0,
            "wins": 0,
            "places": 0,
            "years": set(),
            "tracks": set(),
            "horses": set(),
            "trainers": set(),
            "first_ride": "",
            "last_ride": "",
            "sp_rows": 0,
            "rail_rows": 0,
        })

        j["rides"] += 1

        if is_win(r.get("finish")):
            j["wins"] += 1

        if is_place(r.get("finish")):
            j["places"] += 1

        d = clean(r.get("race_date"))
        if d:
            j["years"].add(d[:4])
            if not j["first_ride"] or d < j["first_ride"]:
                j["first_ride"] = d
            if not j["last_ride"] or d > j["last_ride"]:
                j["last_ride"] = d

        track = clean(r.get("track"))
        horse = clean(r.get("horse"))
        trainer = clean(r.get("trainer"))

        if track:
            j["tracks"].add(track.upper())
        if horse:
            j["horses"].add(horse.upper())
        if trainer:
            j["trainers"].add(trainer.upper())

        if clean(r.get("starting_price_decimal")):
            j["sp_rows"] += 1

        if clean(r.get("rail_position")):
            j["rail_rows"] += 1

rows = []

for j in jockeys.values():
    rides = j["rides"]
    rows.append({
        "jockey": j["jockey"],
        "rides": rides,
        "wins": j["wins"],
        "places": j["places"],
        "win_pct": round((j["wins"] / rides) * 100, 2) if rides else 0,
        "place_pct": round((j["places"] / rides) * 100, 2) if rides else 0,
        "years_seen": len(j["years"]),
        "first_ride": j["first_ride"],
        "last_ride": j["last_ride"],
        "tracks_seen": len(j["tracks"]),
        "horses_ridden": len(j["horses"]),
        "trainers_ridden_for": len(j["trainers"]),
        "sp_rows": j["sp_rows"],
        "rail_rows": j["rail_rows"],
    })

rows.sort(key=lambda x: x["rides"], reverse=True)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["jockey"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

built_at = datetime.now(timezone.utc).isoformat()

summary_rows = [
    {"metric": "status", "value": "EDGEIQ_JOCKEY_UNIVERSE_AUDIT_V1_BUILT"},
    {"metric": "unique_jockeys", "value": len(rows)},
    {"metric": "total_rides", "value": sum(int(r["rides"]) for r in rows)},
    {"metric": "jockeys_1_ride", "value": sum(1 for r in rows if int(r["rides"]) == 1)},
    {"metric": "jockeys_10_plus_rides", "value": sum(1 for r in rows if int(r["rides"]) >= 10)},
    {"metric": "jockeys_50_plus_rides", "value": sum(1 for r in rows if int(r["rides"]) >= 50)},
    {"metric": "jockeys_100_plus_rides", "value": sum(1 for r in rows if int(r["rides"]) >= 100)},
    {"metric": "jockeys_500_plus_rides", "value": sum(1 for r in rows if int(r["rides"]) >= 500)},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[JOCKEY_UNIVERSE_AUDIT_V1] COMPLETE")
print(f"jockeys={len(rows)}")
print(f"output={OUT}")
