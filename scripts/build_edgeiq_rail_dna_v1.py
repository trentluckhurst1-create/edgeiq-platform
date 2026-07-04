from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_rail_dna_v1.csv"
SUMMARY = DATA / "edgeiq_rail_dna_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return clean(v).upper()

def is_win(v):
    return norm(v) in {"1","1ST"}

def is_place(v):
    return norm(v) in {"1","2","3","1ST","2ND","3RD"}

def rail_bucket(v):
    t = norm(v)

    if not t:
        return "UNKNOWN"

    if "TRUE" in t:
        return "TRUE"

    nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*M", t)]

    if nums:
        mx = max(nums)

        if mx <= 1:
            return "TRUE"

        if mx <= 4:
            return "RAIL_OUT_1_4M"

        if mx <= 8:
            return "RAIL_OUT_4_8M"

        return "RAIL_OUT_8M_PLUS"

    if "INSIDE" in t:
        return "INSIDE_DETAIL"

    if "OUT" in t:
        return "RAIL_OUT_UNKNOWN"

    return "OTHER"

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
source_rows_with_rail = 0

def add(entity_type, entity_name, bucket, row):
    if not entity_name or bucket == "UNKNOWN":
        return

    key = (entity_type, norm(entity_name), bucket)

    p = profiles.setdefault(key, {
        "entity_type": entity_type,
        "entity_name": entity_name,
        "rail_bucket": bucket,
        "starts": 0,
        "wins": 0,
        "places": 0,
        "years": set(),
        "tracks": set(),
    })

    p["starts"] += 1

    if is_win(row.get("finish")):
        p["wins"] += 1

    if is_place(row.get("finish")):
        p["places"] += 1

    race_date = clean(row.get("race_date"))
    if len(race_date) >= 4:
        p["years"].add(race_date[:4])

    track = clean(row.get("track"))
    if track:
        p["tracks"].add(norm(track))

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        bucket = rail_bucket(row.get("rail_position"))

        if bucket != "UNKNOWN":
            source_rows_with_rail += 1

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
        "rail_bucket": p["rail_bucket"],
        "starts": starts,
        "wins": wins,
        "places": places,
        "win_pct": round(win_pct, 2),
        "place_pct": round(place_pct, 2),
        "years_seen": len(p["years"]),
        "tracks_seen": len(p["tracks"]),
        "rail_dna_score": score,
        "rail_dna_band": band(score, starts),
    })

rows.sort(
    key=lambda r: (
        r["entity_type"],
        -float(r["rail_dna_score"]),
        -int(r["starts"]),
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["built_at"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary_rows = [
    {"metric": "status", "value": "EDGEIQ_RAIL_DNA_V1_BUILT"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "source_rows_with_rail", "value": source_rows_with_rail},
    {"metric": "rows", "value": len(rows)},
    {"metric": "horse_rows", "value": sum(1 for r in rows if r["entity_type"] == "HORSE")},
    {"metric": "trainer_rows", "value": sum(1 for r in rows if r["entity_type"] == "TRAINER")},
    {"metric": "jockey_rows", "value": sum(1 for r in rows if r["entity_type"] == "JOCKEY")},
    {"metric": "connection_rows", "value": sum(1 for r in rows if r["entity_type"] == "CONNECTION")},
    {"metric": "elite_rows", "value": sum(1 for r in rows if r["rail_dna_band"] == "ELITE")},
    {"metric": "strong_rows", "value": sum(1 for r in rows if r["rail_dna_band"] == "STRONG")},
    {"metric": "positive_rows", "value": sum(1 for r in rows if r["rail_dna_band"] == "POSITIVE")},
    {"metric": "low_sample_rows", "value": sum(1 for r in rows if r["rail_dna_band"] == "LOW_SAMPLE")},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric", "value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[RAIL_DNA_V1] COMPLETE")
print(f"source_rows_with_rail={source_rows_with_rail}")
print(f"rows={len(rows)}")
print(f"output={OUT}")
