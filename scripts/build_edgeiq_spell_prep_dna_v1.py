from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_spell_prep_dna_v1.csv"
SUMMARY = DATA / "edgeiq_spell_prep_dna_v1_summary.csv"

SPELL_BUCKETS = [
    "FIRST_UP_120_PLUS",
    "SECOND_UP",
    "THIRD_UP",
    "FOURTH_PLUS",
    "QUICK_BACKUP_0_21",
    "NORMAL_22_60",
    "FRESH_61_120",
]

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return clean(v).upper()

def is_win(v):
    return norm(v) in {"1", "1ST"}

def is_place(v):
    return norm(v) in {"1", "2", "3", "1ST", "2ND", "3RD"}

def parse_date(v):
    s = clean(v)
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except:
        return None

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

def prep_bucket(days_since_last, prep_run_no):
    if days_since_last is None:
        return "UNKNOWN"

    if days_since_last >= 120:
        return "FIRST_UP_120_PLUS"

    if prep_run_no == 2:
        return "SECOND_UP"

    if prep_run_no == 3:
        return "THIRD_UP"

    if prep_run_no >= 4:
        return "FOURTH_PLUS"

    if days_since_last <= 21:
        return "QUICK_BACKUP_0_21"

    if days_since_last <= 60:
        return "NORMAL_22_60"

    if days_since_last <= 120:
        return "FRESH_61_120"

    return "UNKNOWN"

if not SRC.exists():
    raise FileNotFoundError(f"Missing source: {SRC}")

raw_rows = []

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        horse = clean(row.get("horse"))
        race_date = parse_date(row.get("race_date"))

        if not horse or race_date is None:
            continue

        raw_rows.append(row)

raw_rows.sort(key=lambda r: (norm(r.get("horse")), parse_date(r.get("race_date")) or datetime.max.date()))

horse_last_date = {}
horse_prep_run_no = {}
annotated = []

for row in raw_rows:
    horse_key = norm(row.get("horse"))
    race_date = parse_date(row.get("race_date"))

    last_date = horse_last_date.get(horse_key)
    days_since_last = None

    if last_date:
        days_since_last = (race_date - last_date).days

    if days_since_last is None or days_since_last >= 120:
        prep_no = 1
    else:
        prep_no = horse_prep_run_no.get(horse_key, 0) + 1

    horse_last_date[horse_key] = race_date
    horse_prep_run_no[horse_key] = prep_no

    bucket = prep_bucket(days_since_last, prep_no)

    if bucket == "UNKNOWN":
        continue

    row["_prep_bucket"] = bucket
    row["_days_since_last"] = "" if days_since_last is None else str(days_since_last)
    row["_prep_run_no"] = str(prep_no)

    annotated.append(row)

profiles = {}

def add(entity_type, entity_name, bucket, row):
    if not entity_name or bucket == "UNKNOWN":
        return

    key = (entity_type, norm(entity_name), bucket)

    p = profiles.setdefault(key, {
        "entity_type": entity_type,
        "entity_name": entity_name,
        "prep_bucket": bucket,
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

for row in annotated:
    bucket = row["_prep_bucket"]

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
        "prep_bucket": p["prep_bucket"],
        "starts": starts,
        "wins": wins,
        "places": places,
        "win_pct": round(win_pct, 2),
        "place_pct": round(place_pct, 2),
        "years_seen": len(p["years"]),
        "tracks_seen": len(p["tracks"]),
        "spell_prep_dna_score": score,
        "spell_prep_dna_band": band(score, starts),
    })

rows.sort(
    key=lambda r: (
        r["entity_type"],
        -float(r["spell_prep_dna_score"]),
        -int(r["starts"]),
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["built_at"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary_rows = [
    {"metric": "status", "value": "EDGEIQ_SPELL_PREP_DNA_V1_BUILT"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "source_rows_loaded", "value": len(raw_rows)},
    {"metric": "source_rows_used", "value": len(annotated)},
    {"metric": "rows", "value": len(rows)},
    {"metric": "horse_rows", "value": sum(1 for r in rows if r["entity_type"] == "HORSE")},
    {"metric": "trainer_rows", "value": sum(1 for r in rows if r["entity_type"] == "TRAINER")},
    {"metric": "jockey_rows", "value": sum(1 for r in rows if r["entity_type"] == "JOCKEY")},
    {"metric": "connection_rows", "value": sum(1 for r in rows if r["entity_type"] == "CONNECTION")},
    {"metric": "elite_rows", "value": sum(1 for r in rows if r["spell_prep_dna_band"] == "ELITE")},
    {"metric": "strong_rows", "value": sum(1 for r in rows if r["spell_prep_dna_band"] == "STRONG")},
    {"metric": "positive_rows", "value": sum(1 for r in rows if r["spell_prep_dna_band"] == "POSITIVE")},
    {"metric": "low_sample_rows", "value": sum(1 for r in rows if r["spell_prep_dna_band"] == "LOW_SAMPLE")},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric", "value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[SPELL_PREP_DNA_V1] COMPLETE")
print(f"source_rows_loaded={len(raw_rows)}")
print(f"source_rows_used={len(annotated)}")
print(f"rows={len(rows)}")
print(f"output={OUT}")
