from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_class_dna_v1.csv"
SUMMARY = DATA / "edgeiq_class_dna_v1_summary.csv"

CLASS_FIELDS = [
    "race_class",
    "race_class_clean",
    "class",
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

def extract_class_text(row):
    vals = []
    for f in CLASS_FIELDS:
        v = clean(row.get(f))
        if v:
            vals.append(v)
    return " | ".join(vals).upper()

def class_bucket(row):
    t = extract_class_text(row)

    if not t:
        return "UNKNOWN"

    if re.search(r"\b(GROUP|GRP|G1|GROUP 1|GROUP1)\b", t):
        return "GROUP"
    if re.search(r"\b(G2|GROUP 2|GROUP2|G3|GROUP 3|GROUP3)\b", t):
        return "GROUP"
    if "LISTED" in t or re.search(r"\bLR\b", t):
        return "LISTED"
    if "OPEN" in t or "HANDICAP" in t and "BM" not in t and "BENCHMARK" not in t:
        return "OPEN"

    m = re.search(r"\bBM\s*([0-9]{2,3})\b", t)
    if not m:
        m = re.search(r"\bBENCHMARK\s*([0-9]{2,3})\b", t)

    if m:
        n = int(m.group(1))
        if n <= 58:
            return "BM58"
        if n <= 64:
            return "BM64"
        if n <= 70:
            return "BM70"
        if n <= 78:
            return "BM78"
        if n <= 84:
            return "BM84"
        return "BM85_PLUS"

    if "MAIDEN" in t or re.search(r"\bMDN\b", t):
        return "MAIDEN"

    if "CLASS 1" in t or re.search(r"\bCL1\b", t):
        return "CLASS1"
    if "CLASS 2" in t or re.search(r"\bCL2\b", t):
        return "CLASS2"
    if "CLASS 3" in t or re.search(r"\bCL3\b", t):
        return "CLASS3"
    if "CLASS 4" in t or re.search(r"\bCL4\b", t):
        return "CLASS4"

    if "TRIAL" in t:
        return "TRIAL"

    return "OTHER"

profiles = {}
source_rows_with_class = 0

def add(entity_type, entity_name, bucket, row):
    if not entity_name or bucket == "UNKNOWN":
        return

    key = (entity_type, norm(entity_name), bucket)

    p = profiles.setdefault(key, {
        "entity_type": entity_type,
        "entity_name": entity_name,
        "class_bucket": bucket,
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

if not SRC.exists():
    raise FileNotFoundError(f"Missing source: {SRC}")

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        cb = class_bucket(row)

        if cb != "UNKNOWN":
            source_rows_with_class += 1

        horse = clean(row.get("horse"))
        trainer = clean(row.get("trainer"))
        jockey = clean(row.get("jockey"))

        add("HORSE", horse, cb, row)
        add("TRAINER", trainer, cb, row)
        add("JOCKEY", jockey, cb, row)

        if trainer and jockey:
            add("CONNECTION", f"{trainer} | {jockey}", cb, row)

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
        "class_bucket": p["class_bucket"],
        "starts": starts,
        "wins": wins,
        "places": places,
        "win_pct": round(win_pct, 2),
        "place_pct": round(place_pct, 2),
        "years_seen": len(p["years"]),
        "tracks_seen": len(p["tracks"]),
        "class_dna_score": score,
        "class_dna_band": band(score, starts),
    })

rows.sort(key=lambda r: (r["entity_type"], -float(r["class_dna_score"]), -int(r["starts"])))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["built_at"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary = [
    {"metric": "status", "value": "EDGEIQ_CLASS_DNA_V1_BUILT"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "source_rows_with_class", "value": source_rows_with_class},
    {"metric": "rows", "value": len(rows)},
    {"metric": "horse_rows", "value": sum(1 for r in rows if r["entity_type"] == "HORSE")},
    {"metric": "trainer_rows", "value": sum(1 for r in rows if r["entity_type"] == "TRAINER")},
    {"metric": "jockey_rows", "value": sum(1 for r in rows if r["entity_type"] == "JOCKEY")},
    {"metric": "connection_rows", "value": sum(1 for r in rows if r["entity_type"] == "CONNECTION")},
    {"metric": "elite_rows", "value": sum(1 for r in rows if r["class_dna_band"] == "ELITE")},
    {"metric": "strong_rows", "value": sum(1 for r in rows if r["class_dna_band"] == "STRONG")},
    {"metric": "positive_rows", "value": sum(1 for r in rows if r["class_dna_band"] == "POSITIVE")},
    {"metric": "low_sample_rows", "value": sum(1 for r in rows if r["class_dna_band"] == "LOW_SAMPLE")},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary)

print("[CLASS_DNA_V1] COMPLETE")
print(f"source_rows_with_class={source_rows_with_class}")
print(f"rows={len(rows)}")
print(f"output={OUT}")
