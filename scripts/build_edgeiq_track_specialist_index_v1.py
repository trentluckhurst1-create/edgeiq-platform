from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_track_dna_v1_1_canonical.csv"
OUT = DATA / "edgeiq_track_specialist_index_v1.csv"
SUMMARY = DATA / "edgeiq_track_specialist_index_v1_summary.csv"

MIN_STARTS = {
    "HORSE": 5,
    "TRAINER": 25,
    "JOCKEY": 25,
    "CONNECTION": 10,
}

TOP_N = 25

def clean(v):
    return "" if v is None else str(v).strip()

def to_int(v):
    try:
        return int(float(clean(v)))
    except:
        return 0

def to_float(v):
    try:
        return float(clean(v))
    except:
        return 0.0

if not SRC.exists():
    raise FileNotFoundError(f"Missing source: {SRC}")

by_track_entity = defaultdict(list)

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        entity_type = clean(r.get("entity_type"))
        starts = to_int(r.get("starts"))
        if starts < MIN_STARTS.get(entity_type, 999999):
            continue

        by_track_entity[(clean(r.get("track")), entity_type)].append(r)

built_at = datetime.now(timezone.utc).isoformat()
rows = []

for (track, entity_type), items in by_track_entity.items():
    items.sort(
        key=lambda r: (
            -to_float(r.get("track_dna_score")),
            -to_int(r.get("starts")),
            -to_float(r.get("win_pct")),
            -to_float(r.get("place_pct")),
        )
    )

    for rank, r in enumerate(items[:TOP_N], start=1):
        rows.append({
            "built_at": built_at,
            "track": track,
            "track_group": clean(r.get("track_group")),
            "surface": clean(r.get("surface")),
            "entity_type": entity_type,
            "specialist_rank": rank,
            "entity_name": clean(r.get("entity_name")),
            "starts": clean(r.get("starts")),
            "wins": clean(r.get("wins")),
            "places": clean(r.get("places")),
            "win_pct": clean(r.get("win_pct")),
            "place_pct": clean(r.get("place_pct")),
            "years_seen": clean(r.get("years_seen")),
            "track_dna_score": clean(r.get("track_dna_score")),
            "track_dna_band": clean(r.get("track_dna_band")),
            "raw_track_variants_seen": clean(r.get("raw_track_variants_seen")),
            "specialist_label": f"{entity_type}_TRACK_SPECIALIST",
        })

rows.sort(key=lambda r: (r["track"], r["entity_type"], int(r["specialist_rank"])))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["built_at"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary = [
    {"metric": "status", "value": "EDGEIQ_TRACK_SPECIALIST_INDEX_V1_BUILT"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "rows", "value": len(rows)},
    {"metric": "tracks", "value": len(set(r["track"] for r in rows))},
    {"metric": "horse_rows", "value": sum(1 for r in rows if r["entity_type"] == "HORSE")},
    {"metric": "trainer_rows", "value": sum(1 for r in rows if r["entity_type"] == "TRAINER")},
    {"metric": "jockey_rows", "value": sum(1 for r in rows if r["entity_type"] == "JOCKEY")},
    {"metric": "connection_rows", "value": sum(1 for r in rows if r["entity_type"] == "CONNECTION")},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary)

print("[TRACK_SPECIALIST_INDEX_V1] COMPLETE")
print(f"rows={len(rows)}")
print(f"output={OUT}")
