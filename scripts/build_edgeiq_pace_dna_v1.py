from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_pace_dna_v1.csv"
SUMMARY = DATA / "edgeiq_pace_dna_v1_summary.csv"
FIELD_AUDIT = DATA / "edgeiq_pace_dna_v1_field_audit.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return clean(v).upper()

def first_number(v):
    s = clean(v)
    m = re.search(r"\d+", s)
    return int(m.group(0)) if m else 0

def is_win(v):
    return clean(v).upper() in {"1", "1ST"}

def is_place(v):
    return clean(v).upper() in {"1", "2", "3", "1ST", "2ND", "3RD"}

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

if not SRC.exists():
    raise FileNotFoundError(f"Missing source: {SRC}")

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames or []

field_l = {f: f.lower() for f in fields}

pos800_fields = [
    f for f in fields
    if (
        "800" in field_l[f]
        or "eight" in field_l[f]
        or "pos800" in field_l[f]
    )
]

pos400_fields = [
    f for f in fields
    if (
        "400" in field_l[f]
        or "four" in field_l[f]
        or "pos400" in field_l[f]
    )
]

running_position_fields = [
    f for f in fields
    if (
        "position" in field_l[f]
        or "settling" in field_l[f]
        or "running" in field_l[f]
        or "pace" in field_l[f]
        or "in_run" in field_l[f]
        or "inrun" in field_l[f]
    )
]

candidate_fields = []
for f in pos800_fields + pos400_fields + running_position_fields:
    if f not in candidate_fields:
        candidate_fields.append(f)

with FIELD_AUDIT.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["field"])
    w.writeheader()
    for c in candidate_fields:
        w.writerow({"field": c})

profiles = {}
source_rows_with_pace = 0

def row_position(row):
    preferred = pos800_fields + pos400_fields + running_position_fields
    for f in preferred:
        n = first_number(row.get(f))
        if n > 0:
            return n
    return 0

def run_style(pos):
    if pos <= 0:
        return "UNKNOWN"
    if pos == 1:
        return "LEADER"
    if pos <= 4:
        return "ON_PACE"
    if pos <= 8:
        return "MIDFIELD"
    return "BACKMARKER"

def add(entity_type, entity_name, style, row):
    if not entity_name or style == "UNKNOWN":
        return

    key = (entity_type, norm(entity_name), style)

    p = profiles.setdefault(key, {
        "entity_type": entity_type,
        "entity_name": entity_name,
        "run_style": style,
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

    d = clean(row.get("race_date"))
    if len(d) >= 4:
        p["years"].add(d[:4])

    track = clean(row.get("track"))
    if track:
        p["tracks"].add(track.upper())

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        pos = row_position(row)
        style = run_style(pos)

        if style != "UNKNOWN":
            source_rows_with_pace += 1

        horse = clean(row.get("horse"))
        trainer = clean(row.get("trainer"))
        jockey = clean(row.get("jockey"))

        add("HORSE", horse, style, row)
        add("TRAINER", trainer, style, row)
        add("JOCKEY", jockey, style, row)

        if trainer and jockey:
            add("CONNECTION", f"{trainer} | {jockey}", style, row)

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
        + clamp(starts / 3, 0, 18)
        + clamp(win_pct * 1.05, 0, 35)
        + clamp(place_pct * 0.35, 0, 22),
        0,
        100
    ), 1)

    rows.append({
        "built_at": built_at,
        "entity_type": p["entity_type"],
        "entity_name": p["entity_name"],
        "run_style": p["run_style"],
        "starts": starts,
        "wins": wins,
        "places": places,
        "win_pct": round(win_pct, 2),
        "place_pct": round(place_pct, 2),
        "years_seen": len(p["years"]),
        "tracks_seen": len(p["tracks"]),
        "pace_dna_score": score,
        "pace_dna_band": band(score, starts),
    })

rows.sort(key=lambda r: (r["entity_type"], -float(r["pace_dna_score"]), -int(r["starts"])))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["built_at"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary = [
    {"metric": "status", "value": "EDGEIQ_PACE_DNA_V1_BUILT"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "candidate_position_fields", "value": len(candidate_fields)},
    {"metric": "field_audit", "value": str(FIELD_AUDIT)},
    {"metric": "source_rows_with_pace", "value": source_rows_with_pace},
    {"metric": "rows", "value": len(rows)},
    {"metric": "horse_rows", "value": sum(1 for r in rows if r["entity_type"] == "HORSE")},
    {"metric": "trainer_rows", "value": sum(1 for r in rows if r["entity_type"] == "TRAINER")},
    {"metric": "jockey_rows", "value": sum(1 for r in rows if r["entity_type"] == "JOCKEY")},
    {"metric": "connection_rows", "value": sum(1 for r in rows if r["entity_type"] == "CONNECTION")},
    {"metric": "elite_rows", "value": sum(1 for r in rows if r["pace_dna_band"] == "ELITE")},
    {"metric": "strong_rows", "value": sum(1 for r in rows if r["pace_dna_band"] == "STRONG")},
    {"metric": "positive_rows", "value": sum(1 for r in rows if r["pace_dna_band"] == "POSITIVE")},
    {"metric": "low_sample_rows", "value": sum(1 for r in rows if r["pace_dna_band"] == "LOW_SAMPLE")},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary)

print("[PACE_DNA_V1_FIXED] COMPLETE")
print(f"candidate_position_fields={len(candidate_fields)}")
print(f"source_rows_with_pace={source_rows_with_pace}")
print(f"rows={len(rows)}")
print(f"field_audit={FIELD_AUDIT}")
print(f"output={OUT}")
