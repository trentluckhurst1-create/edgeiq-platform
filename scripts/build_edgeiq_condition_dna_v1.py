from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_condition_dna_v1.csv"
SUMMARY = DATA / "edgeiq_condition_dna_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return clean(v).upper()

def is_win(v):
    return clean(v).upper() in {"1","1ST"}

def is_place(v):
    return clean(v).upper() in {"1","2","3","1ST","2ND","3RD"}

def condition_bucket(condition, rating):
    c = norm(condition)
    r = clean(rating)

    if "FAST" in c:
        return "FAST"

    if "GOOD" in c:
        return "GOOD"

    if "SOFT" in c:
        return "SOFT"

    if "HEAVY" in c:
        return "HEAVY"

    try:
        n = int(float(r))
        if n <= 1:
            return "FAST"
        if n <= 4:
            return "GOOD"
        if n <= 7:
            return "SOFT"
        return "HEAVY"
    except:
        return "UNKNOWN"

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def band(score, starts):
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
source_rows_with_condition = 0

def add(entity_type, entity_name, bucket, row):
    if not entity_name or bucket == "UNKNOWN":
        return

    key = (entity_type, norm(entity_name), bucket)

    p = profiles.setdefault(key,{
        "entity_type": entity_type,
        "entity_name": entity_name,
        "condition_bucket": bucket,
        "starts": 0,
        "wins": 0,
        "places": 0,
        "years": set(),
    })

    p["starts"] += 1

    if is_win(row.get("finish")):
        p["wins"] += 1

    if is_place(row.get("finish")):
        p["places"] += 1

    race_date = clean(row.get("race_date"))
    if len(race_date) >= 4:
        p["years"].add(race_date[:4])

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):

        bucket = condition_bucket(
            row.get("track_condition"),
            row.get("track_rating")
        )

        if bucket != "UNKNOWN":
            source_rows_with_condition += 1

        horse = clean(row.get("horse"))
        trainer = clean(row.get("trainer"))
        jockey = clean(row.get("jockey"))

        add("HORSE", horse, bucket, row)
        add("TRAINER", trainer, bucket, row)
        add("JOCKEY", jockey, bucket, row)

        if trainer and jockey:
            add("CONNECTION", f"{trainer} | {jockey}", bucket, row)

built_at = datetime.now(timezone.utc).isoformat()

rows = []

for p in profiles.values():

    starts = p["starts"]
    wins = p["wins"]
    places = p["places"]

    win_pct = wins / starts * 100 if starts else 0
    place_pct = places / starts * 100 if starts else 0

    score = round(
        clamp(
            35
            + clamp(starts / 3, 0, 18)
            + clamp(win_pct * 1.05, 0, 35)
            + clamp(place_pct * 0.35, 0, 22),
            0,
            100,
        ),
        1,
    )

    rows.append({
        "built_at": built_at,
        "entity_type": p["entity_type"],
        "entity_name": p["entity_name"],
        "condition_bucket": p["condition_bucket"],
        "starts": starts,
        "wins": wins,
        "places": places,
        "win_pct": round(win_pct,2),
        "place_pct": round(place_pct,2),
        "years_seen": len(p["years"]),
        "condition_dna_score": score,
        "condition_dna_band": band(score, starts),
    })

rows.sort(
    key=lambda r: (
        r["entity_type"],
        -float(r["condition_dna_score"]),
        -int(r["starts"])
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys())
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary_rows = [
    {"metric":"status","value":"EDGEIQ_CONDITION_DNA_V1_BUILT"},
    {"metric":"source_rows_with_condition","value":source_rows_with_condition},
    {"metric":"rows","value":len(rows)},
    {"metric":"horse_rows","value":sum(1 for r in rows if r["entity_type"]=="HORSE")},
    {"metric":"trainer_rows","value":sum(1 for r in rows if r["entity_type"]=="TRAINER")},
    {"metric":"jockey_rows","value":sum(1 for r in rows if r["entity_type"]=="JOCKEY")},
    {"metric":"connection_rows","value":sum(1 for r in rows if r["entity_type"]=="CONNECTION")},
    {"metric":"elite_rows","value":sum(1 for r in rows if r["condition_dna_band"]=="ELITE")},
    {"metric":"strong_rows","value":sum(1 for r in rows if r["condition_dna_band"]=="STRONG")},
    {"metric":"positive_rows","value":sum(1 for r in rows if r["condition_dna_band"]=="POSITIVE")},
    {"metric":"low_sample_rows","value":sum(1 for r in rows if r["condition_dna_band"]=="LOW_SAMPLE")},
    {"metric":"output","value":str(OUT)},
    {"metric":"built_at","value":built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[CONDITION_DNA_V1] COMPLETE")
print(f"source_rows_with_condition={source_rows_with_condition}")
print(f"rows={len(rows)}")
print(f"output={OUT}")
