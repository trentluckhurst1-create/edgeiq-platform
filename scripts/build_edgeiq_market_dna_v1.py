from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_sp_profile_universe_audit_v1.csv"
OUT = DATA / "edgeiq_market_dna_v1.csv"
SUMMARY = DATA / "edgeiq_market_dna_v1_summary.csv"

BUCKET_EXPECTED_WIN = {
    "FAVOURITE": 0.40,
    "2-4": 0.30,
    "4-8": 0.17,
    "8-15": 0.085,
    "15+": 0.035,
}

BUCKET_EXPECTED_PLACE = {
    "FAVOURITE": 0.72,
    "2-4": 0.58,
    "4-8": 0.42,
    "8-15": 0.27,
    "15+": 0.14,
}

BUCKET_ORDER = {
    "FAVOURITE": 1,
    "2-4": 2,
    "4-8": 3,
    "8-15": 4,
    "15+": 5,
}

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

profiles = {}

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        entity_type = clean(r.get("entity_type"))
        entity_name = clean(r.get("entity_name"))
        sp_bucket = clean(r.get("sp_bucket"))

        if not entity_type or not entity_name or sp_bucket not in BUCKET_EXPECTED_WIN:
            continue

        key = (entity_type, entity_name.upper())

        p = profiles.setdefault(key, {
            "entity_type": entity_type,
            "entity_name": entity_name,
            "starts": 0,
            "wins": 0,
            "places": 0,
            "expected_wins": 0.0,
            "expected_places": 0.0,
            "years": set(),
            "tracks": set(),
            "horses": set(),
            "bucket_starts": {b: 0 for b in BUCKET_ORDER},
            "bucket_wins": {b: 0 for b in BUCKET_ORDER},
            "bucket_places": {b: 0 for b in BUCKET_ORDER},
        })

        starts = to_int(r.get("starts"))
        wins = to_int(r.get("wins"))
        places = to_int(r.get("places"))

        p["starts"] += starts
        p["wins"] += wins
        p["places"] += places
        p["expected_wins"] += starts * BUCKET_EXPECTED_WIN[sp_bucket]
        p["expected_places"] += starts * BUCKET_EXPECTED_PLACE[sp_bucket]

        p["bucket_starts"][sp_bucket] += starts
        p["bucket_wins"][sp_bucket] += wins
        p["bucket_places"][sp_bucket] += places

        years_seen = to_int(r.get("years_seen"))
        tracks_seen = to_int(r.get("tracks_seen"))
        horses_seen = to_int(r.get("horses_seen"))

        if years_seen:
            p["years"].add(str(years_seen))
        if tracks_seen:
            p["tracks"].add(str(tracks_seen))
        if horses_seen:
            p["horses"].add(str(horses_seen))

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for p in profiles.values():
    starts = p["starts"]
    wins = p["wins"]
    places = p["places"]
    expected_wins = p["expected_wins"]
    expected_places = p["expected_places"]

    win_delta = wins - expected_wins
    place_delta = places - expected_places

    win_delta_pct = (win_delta / expected_wins * 100) if expected_wins else 0
    place_delta_pct = (place_delta / expected_places * 100) if expected_places else 0

    base = 50
    sample_bonus = clamp(starts / 50, 0, 15)
    win_component = clamp(win_delta_pct * 0.35, -25, 30)
    place_component = clamp(place_delta_pct * 0.20, -15, 20)

    score = round(clamp(base + sample_bonus + win_component + place_component, 0, 100), 1)

    out = {
        "built_at": built_at,
        "entity_type": p["entity_type"],
        "entity_name": p["entity_name"],
        "starts": starts,
        "wins": wins,
        "places": places,
        "expected_wins": round(expected_wins, 2),
        "expected_places": round(expected_places, 2),
        "win_outperformance": round(win_delta, 2),
        "place_outperformance": round(place_delta, 2),
        "win_outperformance_pct": round(win_delta_pct, 2),
        "place_outperformance_pct": round(place_delta_pct, 2),
        "market_dna_score": score,
        "market_dna_band": band(score, starts),
    }

    for b in BUCKET_ORDER:
        bs = p["bucket_starts"][b]
        bw = p["bucket_wins"][b]
        bp = p["bucket_places"][b]
        prefix = b.lower().replace("+", "plus").replace("-", "_")
        out[f"{prefix}_starts"] = bs
        out[f"{prefix}_win_pct"] = round((bw / bs) * 100, 2) if bs else 0
        out[f"{prefix}_place_pct"] = round((bp / bs) * 100, 2) if bs else 0

    rows.append(out)

rows.sort(key=lambda x: (x["entity_type"], -float(x["market_dna_score"]), -int(x["starts"])))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["entity_type","entity_name"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary_rows = [
    {"metric": "status", "value": "EDGEIQ_MARKET_DNA_V1_BUILT"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "rows", "value": len(rows)},
    {"metric": "horse_rows", "value": sum(1 for r in rows if r["entity_type"] == "HORSE")},
    {"metric": "trainer_rows", "value": sum(1 for r in rows if r["entity_type"] == "TRAINER")},
    {"metric": "jockey_rows", "value": sum(1 for r in rows if r["entity_type"] == "JOCKEY")},
    {"metric": "connection_rows", "value": sum(1 for r in rows if r["entity_type"] == "CONNECTION")},
    {"metric": "elite_rows", "value": sum(1 for r in rows if r["market_dna_band"] == "ELITE")},
    {"metric": "strong_rows", "value": sum(1 for r in rows if r["market_dna_band"] == "STRONG")},
    {"metric": "positive_rows", "value": sum(1 for r in rows if r["market_dna_band"] == "POSITIVE")},
    {"metric": "low_sample_rows", "value": sum(1 for r in rows if r["market_dna_band"] == "LOW_SAMPLE")},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[MARKET_DNA_V1] COMPLETE")
print(f"rows={len(rows)}")
print(f"output={OUT}")
print(f"summary={SUMMARY}")
