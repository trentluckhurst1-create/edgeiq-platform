from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

MASTER = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_trainer_universe_audit_v1.csv"
SUMMARY = DATA / "edgeiq_trainer_universe_audit_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def is_win(v):
    return clean(v).upper() in {"1", "1ST"}

def is_place(v):
    return clean(v).upper() in {"1", "2", "3", "1ST", "2ND", "3RD"}

trainers = {}

with MASTER.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        trainer = clean(r.get("trainer"))
        if not trainer:
            continue

        key = trainer.upper()
        t = trainers.setdefault(key, {
            "trainer": trainer,
            "starts": 0,
            "wins": 0,
            "places": 0,
            "years": set(),
            "tracks": set(),
            "horses": set(),
            "jockeys": set(),
            "first_start": "",
            "last_start": "",
            "sp_rows": 0,
            "rail_rows": 0,
        })

        t["starts"] += 1

        if is_win(r.get("finish")):
            t["wins"] += 1

        if is_place(r.get("finish")):
            t["places"] += 1

        d = clean(r.get("race_date"))
        if d:
            t["years"].add(d[:4])
            if not t["first_start"] or d < t["first_start"]:
                t["first_start"] = d
            if not t["last_start"] or d > t["last_start"]:
                t["last_start"] = d

        track = clean(r.get("track"))
        horse = clean(r.get("horse"))
        jockey = clean(r.get("jockey"))

        if track:
            t["tracks"].add(track.upper())
        if horse:
            t["horses"].add(horse.upper())
        if jockey:
            t["jockeys"].add(jockey.upper())

        if clean(r.get("starting_price_decimal")):
            t["sp_rows"] += 1

        if clean(r.get("rail_position")):
            t["rail_rows"] += 1

rows = []

for t in trainers.values():
    starts = t["starts"]
    rows.append({
        "trainer": t["trainer"],
        "starts": starts,
        "wins": t["wins"],
        "places": t["places"],
        "win_pct": round((t["wins"] / starts) * 100, 2) if starts else 0,
        "place_pct": round((t["places"] / starts) * 100, 2) if starts else 0,
        "years_seen": len(t["years"]),
        "first_start": t["first_start"],
        "last_start": t["last_start"],
        "tracks_seen": len(t["tracks"]),
        "horses_trained": len(t["horses"]),
        "jockeys_used": len(t["jockeys"]),
        "sp_rows": t["sp_rows"],
        "rail_rows": t["rail_rows"],
    })

rows.sort(key=lambda x: x["starts"], reverse=True)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["trainer"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

built_at = datetime.now(timezone.utc).isoformat()

summary_rows = [
    {"metric": "status", "value": "EDGEIQ_TRAINER_UNIVERSE_AUDIT_V1_BUILT"},
    {"metric": "unique_trainers", "value": len(rows)},
    {"metric": "total_starts", "value": sum(int(r["starts"]) for r in rows)},
    {"metric": "trainers_1_start", "value": sum(1 for r in rows if int(r["starts"]) == 1)},
    {"metric": "trainers_10_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 10)},
    {"metric": "trainers_50_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 50)},
    {"metric": "trainers_100_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 100)},
    {"metric": "trainers_500_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 500)},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[TRAINER_UNIVERSE_AUDIT_V1] COMPLETE")
print(f"trainers={len(rows)}")
print(f"output={OUT}")
