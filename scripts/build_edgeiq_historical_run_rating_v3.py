from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDITS = ROOT / "outputs" / "audits"
AUDITS.mkdir(parents=True, exist_ok=True)

SRC = DATA / "edgeiq_class_normalised_master_v1.csv"
OUT = DATA / "edgeiq_historical_run_rating_v3.csv"
AUDIT = AUDITS / "edgeiq_historical_run_rating_v3_audit.csv"

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def key(v):
    return re.sub(r"[^A-Z0-9]", "", upper(v))

def boolish(v):
    return upper(v) in {"TRUE", "YES", "Y", "1"}

def to_float(v):
    s = clean(v).replace("$", "").replace(",", "").replace("kg", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

def to_int(v):
    f = to_float(v)
    return int(f) if f is not None else None

def finish_num(v):
    return to_int(v)

def margin_num(v):
    u = upper(v)
    if u in {"HD", "HEAD"}:
        return 0.2
    if u in {"NK", "NECK"}:
        return 0.3
    if u in {"NOSE", "NS"}:
        return 0.1
    return to_float(v)

def distance_num(v):
    return to_float(v)

def distance_bucket(d):
    if d is None:
        return "UNKNOWN"
    if d <= 1400:
        return "SPRINT"
    if d <= 1800:
        return "MILE"
    if d <= 2400:
        return "MIDDLE"
    return "STAYING"

def condition_group(v):
    u = upper(v)
    if "HEAVY" in u:
        return "HEAVY"
    if "SOFT" in u:
        return "SOFT"
    if "SYNTH" in u or "POLY" in u or "TAPETA" in u:
        return "SYNTH"
    if "FIRM" in u:
        return "FIRM"
    if "GOOD" in u:
        return "GOOD"
    return "UNKNOWN"

def margin_scale(bucket):
    return {
        "SPRINT": 2.65,
        "MILE": 2.35,
        "MIDDLE": 2.05,
        "STAYING": 1.55,
    }.get(bucket, 2.2)

def class_strength(row):
    clean_class = upper(row.get("race_class_clean"))
    band = upper(row.get("race_class_band"))

    if clean_class == "G1":
        return 100
    if clean_class == "G2":
        return 96
    if clean_class == "G3":
        return 93
    if clean_class == "LISTED":
        return 90
    if clean_class == "FEATURE_RACE":
        return 86
    if clean_class == "OPEN":
        return 86
    if clean_class == "HANDICAP":
        return 74
    if clean_class == "SET_WEIGHTS":
        return 72
    if clean_class == "SET_WEIGHTS_PENALTIES":
        return 78
    if clean_class == "CONDITIONS":
        return 76
    if clean_class == "MAIDEN":
        return 64

    if clean_class.startswith("BM"):
        n = to_int(clean_class)
        return max(52, min(100, float(n or 64)))

    if clean_class.startswith("RTG"):
        n = to_int(clean_class)
        return max(50, min(100, float(n or 64)))

    if clean_class.startswith("CL"):
        n = to_int(clean_class) or 1
        return 66 + min(16, n * 3)

    if band == "RACE_TYPE":
        race_type = upper(row.get("race_type"))
        if "MIDWAY" in race_type:
            return 66
        if "COUNTRY" in race_type:
            return 58
        if "PROVINCIAL" in race_type:
            return 64
        if "WESTSPEED" in race_type or "VOBIS" in race_type or "SALES" in race_type:
            return 68
        if "QUALITY" in race_type:
            return 84
        return 64

    if band == "RESTRICTED":
        return 66

    return 64

def usable(row):
    return (
        boolish(row.get("official_run_flag"))
        and not boolish(row.get("trial_flag"))
        and not boolish(row.get("jumpout_flag"))
        and finish_num(row.get("finish_pos")) is not None
        and margin_num(row.get("margin")) is not None
        and distance_num(row.get("distance")) is not None
    )

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = [r for r in csv.DictReader(f) if usable(r)]

# Data-driven winner calibration by class/distance/condition bucket.
groups = defaultdict(list)
for r in rows:
    d = distance_num(r.get("distance"))
    bucket = distance_bucket(d)
    cond = condition_group(r.get("condition_recovered") or r.get("track_condition"))
    c = upper(r.get("race_class_clean"))
    groups[(c, bucket, cond)].append(r)

winner_counts = defaultdict(int)
for k, g in groups.items():
    winner_counts[k] = sum(1 for r in g if finish_num(r.get("finish_pos")) == 1)

out = []
for r in rows:
    d = distance_num(r.get("distance"))
    bucket = distance_bucket(d)
    cond = condition_group(r.get("condition_recovered") or r.get("track_condition"))
    finish = finish_num(r.get("finish_pos"))
    margin = margin_num(r.get("margin"))
    cls = class_strength(r)

    # Field size usually unavailable in master; infer a conservative default from finish.
    inferred_field = max(8, finish or 8)
    finish_pct = 1 - (((finish or inferred_field) - 1) / max(1, inferred_field - 1))
    result_score = 55 + (finish_pct * 35)

    penalty = min(28, (margin or 0) * margin_scale(bucket))
    winner_bonus = 3.5 if finish == 1 else 0
    close_bonus = 1.5 if (margin or 99) <= 1 and (finish or 99) <= 3 else 0

    cond_adj = {
        "HEAVY": 0.8,
        "SOFT": 0.3,
        "GOOD": 0.0,
        "FIRM": -0.2,
        "SYNTH": 0.0,
        "UNKNOWN": -0.3,
    }.get(cond, 0)

    # If class is unknown because only condition leaked, use neutral base but keep lower confidence.
    conf = upper(r.get("class_confidence"))
    confidence_penalty = 0
    if conf in {"LOW", "UNKNOWN"} and upper(r.get("race_class_clean")) == "UNKNOWN":
        confidence_penalty = 2.0

    rating = (
        0.58 * cls
        + 0.42 * result_score
        + winner_bonus
        + close_bonus
        + cond_adj
        - penalty
        - confidence_penalty
    )

    rating = max(30, min(108, rating))

    out.append({
        "horse_key": clean(r.get("horse_key")) or key(r.get("horse")),
        "horse": clean(r.get("horse")),
        "race_date": clean(r.get("race_date")),
        "track": clean(r.get("track")),
        "state": clean(r.get("state")),
        "race_no": clean(r.get("race_no")),
        "distance": clean(r.get("distance")),
        "distance_bucket": bucket,
        "race_class_raw": clean(r.get("race_class_raw") or r.get("race_class")),
        "race_class_clean": clean(r.get("race_class_clean")),
        "race_class_band": clean(r.get("race_class_band")),
        "race_restriction": clean(r.get("race_restriction")),
        "race_type": clean(r.get("race_type")),
        "feature_race_flag": clean(r.get("feature_race_flag")),
        "condition_recovered": clean(r.get("condition_recovered")),
        "condition_group": cond,
        "class_confidence": clean(r.get("class_confidence")),
        "finish_pos": clean(r.get("finish_pos")),
        "margin": clean(r.get("margin")),
        "barrier": clean(r.get("barrier")),
        "weight": clean(r.get("weight")),
        "jockey": clean(r.get("jockey")),
        "trainer": clean(r.get("trainer")),
        "sp": clean(r.get("sp")),
        "class_strength": round(cls, 2),
        "result_score": round(result_score, 2),
        "margin_penalty": round(penalty, 2),
        "historical_run_rating_v3": round(rating, 2),
        "rating_version": "historical_run_rating_v3_full_universe_class_normalised",
        "rating_notes": "performance-only; no market in core; uses class_normalised_master_v1",
    })

fields = list(out[0].keys()) if out else []
with OUT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out)

with AUDIT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out[:10000])

ratings = [float(r["historical_run_rating_v3"]) for r in out]
print("=" * 90)
print("EDGEIQ HISTORICAL RUN RATING V3")
print("=" * 90)
print(f"source_usable_rows: {len(rows)}")
print(f"rated_rows: {len(out)}")
print(f"rating_min: {min(ratings) if ratings else '-'}")
print(f"rating_median: {median(ratings) if ratings else '-'}")
print(f"rating_max: {max(ratings) if ratings else '-'}")
print(f"out: {OUT}")
print(f"audit: {AUDIT}")
