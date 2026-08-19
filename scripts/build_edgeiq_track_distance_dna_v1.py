from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_master_v2.csv"
TRACK_DICT = DATA / "edgeiq_track_canonical_dictionary_v2.csv"

OUT = DATA / "edgeiq_track_distance_dna_v1.csv"
SUMMARY = DATA / "edgeiq_track_distance_dna_v1_summary.csv"

DISTANCE_FIELDS = [
    "distance",
    "distance_m",
    "race_distance",
    "race_distance_m",
    "distance_metres",
    "distanceMeters",
    "distance_text",
    "race_name",
]

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return clean(v).upper()

def is_win(v):
    return clean(v).upper() in {"1", "1ST"}

def is_place(v):
    return clean(v).upper() in {"1", "2", "3", "1ST", "2ND", "3RD"}

def extract_distance(row):
    for field in DISTANCE_FIELDS:
        v = clean(row.get(field))
        if not v:
            continue
        m = re.search(r"(\d{3,4})\s*m?", v, re.I)
        if m:
            return int(m.group(1))
    return 0

def distance_bucket(n):
    if n <= 0:
        return "UNKNOWN"
    if n <= 1200:
        return "SPRINT_1000_1200"
    if n <= 1400:
        return "SPRINT_1201_1400"
    if n <= 1600:
        return "MILE_1401_1600"
    if n <= 2000:
        return "MIDDLE_1601_2000"
    return "STAYING_2000_PLUS"

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

track_map = {}
if TRACK_DICT.exists():
    with TRACK_DICT.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            raw = norm(r.get("raw_track"))
            canon = clean(r.get("canonical_track"))
            group = clean(r.get("track_group"))
            surface = clean(r.get("surface"))
            if raw:
                track_map[raw] = {
                    "track": canon,
                    "track_group": group,
                    "surface": surface,
                }

profiles = {}
source_rows_with_track_distance = 0

def add(entity_type, entity_name, track, track_group, surface, db, distance_m, row):
    if not entity_name or not track or db == "UNKNOWN":
        return

    key = (entity_type, norm(entity_name), norm(track), db)

    p = profiles.setdefault(key, {
        "entity_type": entity_type,
        "entity_name": entity_name,
        "track": track,
        "track_group": track_group,
        "surface": surface,
        "distance_bucket": db,
        "starts": 0,
        "wins": 0,
        "places": 0,
        "years": set(),
        "min_distance": distance_m,
        "max_distance": distance_m,
    })

    p["starts"] += 1

    if is_win(row.get("finish")):
        p["wins"] += 1

    if is_place(row.get("finish")):
        p["places"] += 1

    d = clean(row.get("race_date"))
    if len(d) >= 4:
        p["years"].add(d[:4])

    if distance_m:
        p["min_distance"] = min(p["min_distance"] or distance_m, distance_m)
        p["max_distance"] = max(p["max_distance"] or distance_m, distance_m)

if not SRC.exists():
    raise FileNotFoundError(f"Missing source: {SRC}")

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        raw_track = clean(row.get("track"))
        meta = track_map.get(norm(raw_track), {
            "track": raw_track,
            "track_group": "",
            "surface": "",
        })

        track = clean(meta.get("track"))
        track_group = clean(meta.get("track_group"))
        surface = clean(meta.get("surface"))

        distance_m = extract_distance(row)
        db = distance_bucket(distance_m)

        if track and db != "UNKNOWN":
            source_rows_with_track_distance += 1

        horse = clean(row.get("horse"))
        trainer = clean(row.get("trainer"))
        jockey = clean(row.get("jockey"))

        add("HORSE", horse, track, track_group, surface, db, distance_m, row)
        add("TRAINER", trainer, track, track_group, surface, db, distance_m, row)
        add("JOCKEY", jockey, track, track_group, surface, db, distance_m, row)

        if trainer and jockey:
            add("CONNECTION", f"{trainer} | {jockey}", track, track_group, surface, db, distance_m, row)

built_at = datetime.now(timezone.utc).isoformat()
rows = []

for p in profiles.values():
    starts = p["starts"]
    wins = p["wins"]
    places = p["places"]

    win_pct = (wins / starts) * 100 if starts else 0
    place_pct = (places / starts) * 100 if starts else 0

    score = round(clamp(
        35
        + clamp(starts / 2, 0, 18)
        + clamp(win_pct * 1.05, 0, 35)
        + clamp(place_pct * 0.35, 0, 22),
        0,
        100
    ), 1)

    rows.append({
        "built_at": built_at,
        "entity_type": p["entity_type"],
        "entity_name": p["entity_name"],
        "track": p["track"],
        "track_group": p["track_group"],
        "surface": p["surface"],
        "distance_bucket": p["distance_bucket"],
        "starts": starts,
        "wins": wins,
        "places": places,
        "win_pct": round(win_pct, 2),
        "place_pct": round(place_pct, 2),
        "years_seen": len(p["years"]),
        "min_distance": p["min_distance"],
        "max_distance": p["max_distance"],
        "track_distance_dna_score": score,
        "track_distance_dna_band": band(score, starts),
    })

rows.sort(key=lambda r: (r["entity_type"], -float(r["track_distance_dna_score"]), -int(r["starts"])))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["built_at"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary = [
    {"metric": "status", "value": "EDGEIQ_TRACK_DISTANCE_DNA_V1_BUILT"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "source_rows_with_track_distance", "value": source_rows_with_track_distance},
    {"metric": "rows", "value": len(rows)},
    {"metric": "horse_rows", "value": sum(1 for r in rows if r["entity_type"] == "HORSE")},
    {"metric": "trainer_rows", "value": sum(1 for r in rows if r["entity_type"] == "TRAINER")},
    {"metric": "jockey_rows", "value": sum(1 for r in rows if r["entity_type"] == "JOCKEY")},
    {"metric": "connection_rows", "value": sum(1 for r in rows if r["entity_type"] == "CONNECTION")},
    {"metric": "elite_rows", "value": sum(1 for r in rows if r["track_distance_dna_band"] == "ELITE")},
    {"metric": "strong_rows", "value": sum(1 for r in rows if r["track_distance_dna_band"] == "STRONG")},
    {"metric": "positive_rows", "value": sum(1 for r in rows if r["track_distance_dna_band"] == "POSITIVE")},
    {"metric": "low_sample_rows", "value": sum(1 for r in rows if r["track_distance_dna_band"] == "LOW_SAMPLE")},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary)

print("[TRACK_DISTANCE_DNA_V1] COMPLETE")
print(f"source_rows_with_track_distance={source_rows_with_track_distance}")
print(f"rows={len(rows)}")
print(f"output={OUT}")
