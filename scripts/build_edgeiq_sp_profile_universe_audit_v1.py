from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

MASTER = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_sp_profile_universe_audit_v1.csv"
SUMMARY = DATA / "edgeiq_sp_profile_universe_audit_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def is_win(v):
    return clean(v).upper() in {"1", "1ST"}

def is_place(v):
    return clean(v).upper() in {"1", "2", "3", "1ST", "2ND", "3RD"}

def sp_bucket(v):
    try:
        n = float(clean(v))
    except:
        return "UNKNOWN"
    if n <= 2:
        return "FAVOURITE"
    if n <= 4:
        return "2-4"
    if n <= 8:
        return "4-8"
    if n <= 15:
        return "8-15"
    return "15+"

profiles = {}

def add(entity_type, entity_name, bucket, row):
    if not entity_name or bucket == "UNKNOWN":
        return

    key = (entity_type, entity_name.upper(), bucket)

    p = profiles.setdefault(key, {
        "entity_type": entity_type,
        "entity_name": entity_name,
        "sp_bucket": bucket,
        "starts": 0,
        "wins": 0,
        "places": 0,
        "years": set(),
        "tracks": set(),
        "horses": set(),
    })

    p["starts"] += 1

    if is_win(row.get("finish")):
        p["wins"] += 1

    if is_place(row.get("finish")):
        p["places"] += 1

    d = clean(row.get("race_date"))
    if d:
        p["years"].add(d[:4])

    track = clean(row.get("track"))
    horse = clean(row.get("horse"))

    if track:
        p["tracks"].add(track.upper())

    if horse:
        p["horses"].add(horse.upper())

with MASTER.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        bucket = sp_bucket(r.get("starting_price_decimal"))

        horse = clean(r.get("horse"))
        trainer = clean(r.get("trainer"))
        jockey = clean(r.get("jockey"))

        add("HORSE", horse, bucket, r)
        add("TRAINER", trainer, bucket, r)
        add("JOCKEY", jockey, bucket, r)

        if trainer and jockey:
            add("CONNECTION", f"{trainer} | {jockey}", bucket, r)

rows = []

for p in profiles.values():
    starts = p["starts"]
    rows.append({
        "entity_type": p["entity_type"],
        "entity_name": p["entity_name"],
        "sp_bucket": p["sp_bucket"],
        "starts": starts,
        "wins": p["wins"],
        "places": p["places"],
        "win_pct": round((p["wins"] / starts) * 100, 2) if starts else 0,
        "place_pct": round((p["places"] / starts) * 100, 2) if starts else 0,
        "years_seen": len(p["years"]),
        "tracks_seen": len(p["tracks"]),
        "horses_seen": len(p["horses"]),
    })

bucket_order = {"FAVOURITE": 1, "2-4": 2, "4-8": 3, "8-15": 4, "15+": 5}

rows.sort(key=lambda x: (x["entity_type"], -int(x["starts"]), bucket_order.get(x["sp_bucket"], 99)))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["entity_type","entity_name","sp_bucket"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

built_at = datetime.now(timezone.utc).isoformat()

summary_rows = [
    {"metric": "status", "value": "EDGEIQ_SP_PROFILE_UNIVERSE_AUDIT_V1_BUILT"},
    {"metric": "rows", "value": len(rows)},
    {"metric": "horse_profiles", "value": sum(1 for r in rows if r["entity_type"] == "HORSE")},
    {"metric": "trainer_profiles", "value": sum(1 for r in rows if r["entity_type"] == "TRAINER")},
    {"metric": "jockey_profiles", "value": sum(1 for r in rows if r["entity_type"] == "JOCKEY")},
    {"metric": "connection_profiles", "value": sum(1 for r in rows if r["entity_type"] == "CONNECTION")},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[SP_PROFILE_UNIVERSE_AUDIT_V1] COMPLETE")
print(f"rows={len(rows)}")
print(f"output={OUT}")
