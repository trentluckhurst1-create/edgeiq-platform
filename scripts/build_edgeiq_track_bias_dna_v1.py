from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_master_v2.csv"
TRACK_DICT = DATA / "edgeiq_track_canonical_dictionary_v2.csv"

OUT = DATA / "edgeiq_track_bias_dna_v1.csv"
SUMMARY = DATA / "edgeiq_track_bias_dna_v1_summary.csv"

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

CONDITION_FIELDS = [
    "track_condition",
    "condition",
    "trackCondition",
    "track_rating",
    "track_rating_text",
    "surface",
    "race_name",
]

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return clean(v).upper()

def to_int(v):
    try:
        return int(float(clean(v)))
    except:
        return 0

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

def barrier_bucket(v):
    n = to_int(v)
    if n <= 0:
        return "UNKNOWN"
    if n <= 4:
        return "INSIDE_1_4"
    if n <= 8:
        return "MIDDLE_5_8"
    return "WIDE_9_PLUS"

def condition_bucket(row):
    text = " ".join(clean(row.get(f)) for f in CONDITION_FIELDS if clean(row.get(f))).upper()
    if not text:
        return "UNKNOWN"
    if "SYNTHETIC" in text:
        return "SYNTHETIC"
    if "HEAVY" in text or re.search(r"\bH[0-9]\b", text):
        return "HEAVY"
    if "SOFT" in text or re.search(r"\bS[0-9]\b", text):
        return "SOFT"
    if "GOOD" in text or re.search(r"\bG[0-9]\b", text):
        return "GOOD"
    if "FAST" in text or re.search(r"\bF[0-9]\b", text):
        return "FAST"
    if "DEAD" in text:
        return "GOOD"
    if "SLOW" in text:
        return "SOFT"
    return "OTHER"

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def band(score, starts):
    if starts < 50:
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
            if raw:
                track_map[raw] = {
                    "track": clean(r.get("canonical_track")),
                    "track_group": clean(r.get("track_group")),
                    "surface": clean(r.get("surface")),
                }

profiles = {}
track_base = {}
source_rows_used = 0

def add_counter(store, key, win, place):
    p = store.setdefault(key, {"starts": 0, "wins": 0, "places": 0, "years": set()})
    p["starts"] += 1
    p["wins"] += win
    p["places"] += place
    return p

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        raw_track = clean(row.get("track"))
        meta = track_map.get(norm(raw_track), {"track": raw_track, "track_group": "", "surface": ""})
        track = clean(meta["track"])
        track_group = clean(meta["track_group"])
        surface = clean(meta["surface"])

        db = distance_bucket(extract_distance(row))
        cb = condition_bucket(row)
        bb = barrier_bucket(row.get("barrier"))

        if not track or db == "UNKNOWN" or bb == "UNKNOWN":
            continue

        source_rows_used += 1
        win = 1 if is_win(row.get("finish")) else 0
        place = 1 if is_place(row.get("finish")) else 0

        year = clean(row.get("race_date"))[:4] if len(clean(row.get("race_date"))) >= 4 else ""

        base_key = (track, db)
        b = add_counter(track_base, base_key, win, place)
        if year:
            b["years"].add(year)

        profile_key = (track, track_group, surface, db, cb, bb)
        p = add_counter(profiles, profile_key, win, place)
        if year:
            p["years"].add(year)

built_at = datetime.now(timezone.utc).isoformat()
rows = []

for key, p in profiles.items():
    track, track_group, surface, db, cb, bb = key
    starts = p["starts"]
    wins = p["wins"]
    places = p["places"]

    win_pct = wins / starts * 100 if starts else 0
    place_pct = places / starts * 100 if starts else 0

    base = track_base.get((track, db), {"starts": 0, "wins": 0, "places": 0})
    base_win_pct = base["wins"] / base["starts"] * 100 if base["starts"] else 0
    base_place_pct = base["places"] / base["starts"] * 100 if base["starts"] else 0

    win_bias = win_pct - base_win_pct
    place_bias = place_pct - base_place_pct

    score = round(clamp(
        50
        + clamp(win_bias * 2.2, -28, 32)
        + clamp(place_bias * 0.9, -18, 22)
        + clamp(starts / 25, 0, 12),
        0,
        100
    ), 1)

    rows.append({
        "built_at": built_at,
        "track": track,
        "track_group": track_group,
        "surface": surface,
        "distance_bucket": db,
        "condition_bucket": cb,
        "barrier_bucket": bb,
        "starts": starts,
        "wins": wins,
        "places": places,
        "win_pct": round(win_pct, 2),
        "place_pct": round(place_pct, 2),
        "track_distance_base_starts": base["starts"],
        "track_distance_base_win_pct": round(base_win_pct, 2),
        "track_distance_base_place_pct": round(base_place_pct, 2),
        "win_bias_vs_track_distance": round(win_bias, 2),
        "place_bias_vs_track_distance": round(place_bias, 2),
        "years_seen": len(p["years"]),
        "track_bias_score": score,
        "track_bias_band": band(score, starts),
    })

rows.sort(key=lambda r: (-float(r["track_bias_score"]), -int(r["starts"]), r["track"], r["distance_bucket"]))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["built_at"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary = [
    {"metric": "status", "value": "EDGEIQ_TRACK_BIAS_DNA_V1_BUILT"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "source_rows_used", "value": source_rows_used},
    {"metric": "rows", "value": len(rows)},
    {"metric": "elite_rows", "value": sum(1 for r in rows if r["track_bias_band"] == "ELITE")},
    {"metric": "strong_rows", "value": sum(1 for r in rows if r["track_bias_band"] == "STRONG")},
    {"metric": "positive_rows", "value": sum(1 for r in rows if r["track_bias_band"] == "POSITIVE")},
    {"metric": "low_sample_rows", "value": sum(1 for r in rows if r["track_bias_band"] == "LOW_SAMPLE")},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary)

print("[TRACK_BIAS_DNA_V1] COMPLETE")
print(f"source_rows_used={source_rows_used}")
print(f"rows={len(rows)}")
print(f"output={OUT}")
