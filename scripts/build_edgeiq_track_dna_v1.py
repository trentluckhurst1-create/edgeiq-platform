from __future__ import annotations

import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "public" / "data"

SOURCE = DATA / "edgeiq_graphql_master_v2.csv"

OUT = DATA / "edgeiq_track_dna_v1.csv"
SUMMARY = DATA / "edgeiq_track_dna_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return clean(v).upper()

def score_band(score, starts):
    if starts < 10:
        return "LOW_SAMPLE"
    if score >= 85:
        return "ELITE"
    if score >= 72:
        return "STRONG"
    if score >= 60:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 32:
        return "NEGATIVE"
    return "POOR"

profiles = {}

with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:

    reader = csv.DictReader(f)

    for row in reader:

        track = clean(row.get("track"))

        horse = clean(row.get("horse"))
        trainer = clean(row.get("trainer"))
        jockey = clean(row.get("jockey"))

        finish = clean(row.get("finish"))

        win = 1 if finish == "1" else 0
        place = 1 if finish in ("1","2","3") else 0

        entities = []

        if horse and track:
            entities.append(("HORSE", horse, track))

        if trainer and track:
            entities.append(("TRAINER", trainer, track))

        if jockey and track:
            entities.append(("JOCKEY", jockey, track))

        if trainer and jockey and track:
            entities.append(("CONNECTION", f"{trainer} | {jockey}", track))

        for entity_type, entity_name, entity_track in entities:

            key = (
                entity_type,
                norm(entity_name),
                norm(entity_track)
            )

            if key not in profiles:
                profiles[key] = {
                    "entity_type": entity_type,
                    "entity_name": entity_name,
                    "track": entity_track,
                    "starts": 0,
                    "wins": 0,
                    "places": 0,
                    "years": set()
                }

            p = profiles[key]

            p["starts"] += 1
            p["wins"] += win
            p["places"] += place

            race_date = clean(row.get("race_date"))

            if len(race_date) >= 4:
                p["years"].add(race_date[:4])

rows = []

built_at = datetime.now(timezone.utc).isoformat()

for p in profiles.values():

    starts = p["starts"]
    wins = p["wins"]
    places = p["places"]

    win_pct = (wins / starts) * 100 if starts else 0
    place_pct = (places / starts) * 100 if starts else 0

    score = (
        50
        + min(win_pct,40) * 0.8
        + min(place_pct,60) * 0.3
        + min(starts,200) / 20
    )

    score = round(min(score,100),1)

    rows.append({
        "built_at": built_at,
        "entity_type": p["entity_type"],
        "entity_name": p["entity_name"],
        "track": p["track"],
        "starts": starts,
        "wins": wins,
        "places": places,
        "win_pct": round(win_pct,2),
        "place_pct": round(place_pct,2),
        "years_seen": len(p["years"]),
        "track_dna_score": score,
        "track_dna_band": score_band(score, starts)
    })

rows.sort(
    key=lambda r: (
        r["entity_type"],
        -float(r["track_dna_score"]),
        -int(r["starts"])
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(rows[0].keys())
    )

    writer.writeheader()
    writer.writerows(rows)

summary_rows = [
    {
        "metric":"status",
        "value":"EDGEIQ_TRACK_DNA_V1_BUILT"
    },
    {
        "metric":"rows",
        "value":len(rows)
    },
    {
        "metric":"horse_rows",
        "value":sum(1 for r in rows if r["entity_type"]=="HORSE")
    },
    {
        "metric":"trainer_rows",
        "value":sum(1 for r in rows if r["entity_type"]=="TRAINER")
    },
    {
        "metric":"jockey_rows",
        "value":sum(1 for r in rows if r["entity_type"]=="JOCKEY")
    },
    {
        "metric":"connection_rows",
        "value":sum(1 for r in rows if r["entity_type"]=="CONNECTION")
    },
    {
        "metric":"output",
        "value":str(OUT)
    }
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=["metric","value"]
    )

    writer.writeheader()
    writer.writerows(summary_rows)

print("[TRACK_DNA_V1] COMPLETE")
print(f"rows={len(rows)}")
print(f"output={OUT}")
