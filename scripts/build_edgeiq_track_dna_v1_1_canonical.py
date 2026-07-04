from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE = DATA / "edgeiq_graphql_master_v2.csv"
TRACK_DICT = DATA / "edgeiq_track_canonical_dictionary_v2.csv"

OUT = DATA / "edgeiq_track_dna_v1_1_canonical.csv"
SUMMARY = DATA / "edgeiq_track_dna_v1_1_canonical_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return clean(v).upper()

def is_win(v):
    return clean(v).upper() in {"1", "1ST"}

def is_place(v):
    return clean(v).upper() in {"1", "2", "3", "1ST", "2ND", "3RD"}

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

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

track_map = {}

with TRACK_DICT.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        raw = norm(r.get("raw_track"))
        if raw:
            track_map[raw] = {
                "canonical_track": clean(r.get("canonical_track")),
                "track_group": clean(r.get("track_group")),
                "surface": clean(r.get("surface")),
            }

profiles = {}

with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        raw_track = clean(row.get("track"))
        meta = track_map.get(norm(raw_track), {
            "canonical_track": raw_track,
            "track_group": "",
            "surface": "",
        })

        track = clean(meta["canonical_track"])
        track_group = clean(meta["track_group"])
        surface = clean(meta["surface"])

        horse = clean(row.get("horse"))
        trainer = clean(row.get("trainer"))
        jockey = clean(row.get("jockey"))

        win = 1 if is_win(row.get("finish")) else 0
        place = 1 if is_place(row.get("finish")) else 0

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
            key = (entity_type, norm(entity_name), norm(entity_track))

            if key not in profiles:
                profiles[key] = {
                    "entity_type": entity_type,
                    "entity_name": entity_name,
                    "track": entity_track,
                    "track_group": track_group,
                    "surface": surface,
                    "starts": 0,
                    "wins": 0,
                    "places": 0,
                    "years": set(),
                    "raw_tracks_seen": set(),
                }

            p = profiles[key]
            p["starts"] += 1
            p["wins"] += win
            p["places"] += place

            race_date = clean(row.get("race_date"))
            if len(race_date) >= 4:
                p["years"].add(race_date[:4])

            if raw_track:
                p["raw_tracks_seen"].add(raw_track.upper())

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for p in profiles.values():
    starts = p["starts"]
    wins = p["wins"]
    places = p["places"]

    win_pct = (wins / starts) * 100 if starts else 0
    place_pct = (places / starts) * 100 if starts else 0

    sample_component = clamp(starts / 2, 0, 15)
    win_component = clamp(win_pct * 0.9, 0, 36)
    place_component = clamp(place_pct * 0.35, 0, 24)

    score = round(clamp(35 + sample_component + win_component + place_component, 0, 100), 1)

    rows.append({
        "built_at": built_at,
        "entity_type": p["entity_type"],
        "entity_name": p["entity_name"],
        "track": p["track"],
        "track_group": p["track_group"],
        "surface": p["surface"],
        "starts": starts,
        "wins": wins,
        "places": places,
        "win_pct": round(win_pct, 2),
        "place_pct": round(place_pct, 2),
        "years_seen": len(p["years"]),
        "raw_track_variants_seen": len(p["raw_tracks_seen"]),
        "track_dna_score": score,
        "track_dna_band": score_band(score, starts),
    })

rows.sort(key=lambda r: (r["entity_type"], -float(r["track_dna_score"]), -int(r["starts"])))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

summary_rows = [
    {"metric":"status","value":"EDGEIQ_TRACK_DNA_V1_1_CANONICAL_BUILT"},
    {"metric":"rows","value":len(rows)},
    {"metric":"horse_rows","value":sum(1 for r in rows if r["entity_type"]=="HORSE")},
    {"metric":"trainer_rows","value":sum(1 for r in rows if r["entity_type"]=="TRAINER")},
    {"metric":"jockey_rows","value":sum(1 for r in rows if r["entity_type"]=="JOCKEY")},
    {"metric":"connection_rows","value":sum(1 for r in rows if r["entity_type"]=="CONNECTION")},
    {"metric":"elite_rows","value":sum(1 for r in rows if r["track_dna_band"]=="ELITE")},
    {"metric":"strong_rows","value":sum(1 for r in rows if r["track_dna_band"]=="STRONG")},
    {"metric":"positive_rows","value":sum(1 for r in rows if r["track_dna_band"]=="POSITIVE")},
    {"metric":"low_sample_rows","value":sum(1 for r in rows if r["track_dna_band"]=="LOW_SAMPLE")},
    {"metric":"output","value":str(OUT)},
    {"metric":"built_at","value":built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary_rows)

print("[TRACK_DNA_V1_1_CANONICAL] COMPLETE")
print(f"rows={len(rows)}")
print(f"output={OUT}")
