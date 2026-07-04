from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

MASTER = DATA / "edgeiq_graphql_master_v2.csv"
TRACKS = DATA / "edgeiq_track_canonical_dictionary_v2.csv"

OUT = DATA / "edgeiq_track_universe_audit_v1.csv"
SUMMARY = DATA / "edgeiq_track_universe_audit_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

track_map = {}

with TRACKS.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        track_map[clean(r["raw_track"]).upper()] = {
            "canonical": clean(r["canonical_track"]),
            "group": clean(r["track_group"]),
            "surface": clean(r["surface"]),
        }

tracks = {}

with MASTER.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):

        raw_track = clean(r.get("track")).upper()

        if raw_track not in track_map:
            continue

        meta = track_map[raw_track]

        canon = meta["canonical"]

        t = tracks.setdefault(canon,{
            "track":canon,
            "group":meta["group"],
            "surface":meta["surface"],
            "years":set(),
            "meetings":set(),
            "races":set(),
            "horses":set(),
            "trainers":set(),
            "jockeys":set(),
            "runners":0,
            "sp_rows":0,
            "rail_rows":0,
        })

        year = clean(r.get("source_year"))
        if year:
            t["years"].add(year)

        race_key = (
            clean(r.get("race_date")) + "|" +
            canon + "|" +
            clean(r.get("race_no"))
        )

        meeting_key = (
            clean(r.get("race_date")) + "|" +
            canon
        )

        t["meetings"].add(meeting_key)
        t["races"].add(race_key)

        horse = clean(r.get("horse"))
        trainer = clean(r.get("trainer"))
        jockey = clean(r.get("jockey"))

        if horse:
            t["horses"].add(horse.upper())

        if trainer:
            t["trainers"].add(trainer.upper())

        if jockey:
            t["jockeys"].add(jockey.upper())

        t["runners"] += 1

        if clean(r.get("starting_price_decimal")):
            t["sp_rows"] += 1

        if clean(r.get("rail_position")):
            t["rail_rows"] += 1

rows = []

for track, t in tracks.items():

    races = len(t["races"])
    runners = t["runners"]

    rows.append({
        "track":track,
        "track_group":t["group"],
        "surface":t["surface"],
        "years_seen":len(t["years"]),
        "first_year":min(t["years"]) if t["years"] else "",
        "last_year":max(t["years"]) if t["years"] else "",
        "meetings":len(t["meetings"]),
        "races":races,
        "runners":runners,
        "unique_horses":len(t["horses"]),
        "unique_trainers":len(t["trainers"]),
        "unique_jockeys":len(t["jockeys"]),
        "sp_rows":t["sp_rows"],
        "rail_rows":t["rail_rows"],
        "avg_runners_per_race":round(runners/races,2) if races else 0,
    })

rows.sort(key=lambda x: x["runners"], reverse=True)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

built_at = datetime.now(timezone.utc).isoformat()

summary_rows = [
    {"metric":"status","value":"EDGEIQ_TRACK_UNIVERSE_AUDIT_V1_BUILT"},
    {"metric":"tracks","value":len(rows)},
    {"metric":"total_runners","value":sum(int(r["runners"]) for r in rows)},
    {"metric":"output","value":str(OUT)},
    {"metric":"built_at","value":built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[TRACK_UNIVERSE_AUDIT_V1] COMPLETE")
print(f"tracks={len(rows)}")
print(f"output={OUT}")
