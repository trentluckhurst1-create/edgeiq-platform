from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDITS = ROOT / "outputs" / "audits"
AUDITS.mkdir(parents=True, exist_ok=True)

HIST = DATA / "edgeiq_historical_run_rating_v2.csv"
LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
TARGETS = DATA / "edgeiq_race_rating_targets_v1.csv"

OUT = DATA / "edgeiq_projection_rating_v1.csv"
AUDIT = AUDITS / "edgeiq_projection_rating_v1_audit.csv"

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def key(v):
    return re.sub(r"[^A-Z0-9]", "", upper(v))

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

def date_parse(v):
    s = clean(v)
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s[:10]).date()
    except Exception:
        return None

def track_norm(v):
    return key(v)

def race_no(v):
    return str(to_int(v) or "").strip()

def distance_num(v):
    return to_float(v)

def recent_weight(days):
    if days is None:
        return 0.85
    if days <= 7:
        return 0.85
    if days <= 45:
        return 1.00
    if days <= 90:
        return 0.96
    if days <= 180:
        return 0.88
    return 0.74

def distance_weight(run_dist, today_dist):
    if run_dist is None or today_dist is None:
        return 0.85
    diff = abs(run_dist - today_dist)
    if diff <= 100:
        return 1.10
    if diff <= 200:
        return 1.00
    if diff <= 400:
        return 0.86
    if diff <= 800:
        return 0.68
    return 0.48

def load_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

hist_rows = load_csv(HIST)
live_rows = load_csv(LIVE)
target_rows = load_csv(TARGETS)

hist_by_horse = defaultdict(list)
for r in hist_rows:
    hk = key(r.get("horse_key") or r.get("horse"))
    rating = to_float(r.get("historical_run_rating_v2"))
    d = date_parse(r.get("race_date"))
    if not hk or rating is None or d is None:
        continue
    r["_rating"] = rating
    r["_date"] = d
    r["_distance_num"] = distance_num(r.get("distance"))
    hist_by_horse[hk].append(r)

for hk in hist_by_horse:
    hist_by_horse[hk].sort(key=lambda r: r["_date"], reverse=True)

target_by_race = {}
for r in target_rows:
    rk = (
        clean(r.get("race_date")),
        track_norm(r.get("track")),
        race_no(r.get("race_no")),
    )
    target_by_race[rk] = r

out = []

for row in live_rows:
    horse = clean(row.get("horse"))
    hk = key(row.get("horse_key") or horse)
    race_date = clean(row.get("race_date") or row.get("date"))
    track = clean(row.get("track"))
    rn = race_no(row.get("race_no") or row.get("raceNo"))
    today_dist = distance_num(row.get("distance"))

    target = target_by_race.get((race_date, track_norm(track), rn), {})
    target_rating = to_float(target.get("target_rating"))

    race_dt = date_parse(race_date)
    runs = hist_by_horse.get(hk, [])[:8]

    weighted = []
    used = []
    for rr in runs:
        days = None
        if race_dt and rr["_date"]:
            days = (race_dt - rr["_date"]).days
        w = recent_weight(days) * distance_weight(rr.get("_distance_num"), today_dist)
        weighted.append((rr["_rating"], w))
        used.append(rr)

    if weighted:
        numerator = sum(r * w for r, w in weighted)
        denominator = sum(w for _, w in weighted) or 1
        base_projection = numerator / denominator
        last_rating = used[0]["_rating"]
        peak_rating = max(r["_rating"] for r in used)
        avg_last3 = mean([r["_rating"] for r in used[:3]]) if used[:3] else base_projection
        projected = (base_projection * 0.62) + (last_rating * 0.18) + (avg_last3 * 0.12) + (peak_rating * 0.08)
        confidence = "HIGH" if len(used) >= 5 else "MEDIUM" if len(used) >= 3 else "LOW"
    else:
        base_projection = None
        last_rating = None
        peak_rating = None
        avg_last3 = None
        projected = None
        confidence = "NONE"

    rating_vs_target = None
    if projected is not None and target_rating is not None:
        rating_vs_target = projected - target_rating

    out.append({
        "race_date": race_date,
        "track": track,
        "race_no": rn,
        "horse_no": clean(row.get("horse_no") or row.get("number") or row.get("saddlecloth")),
        "horse_key": hk,
        "horse": horse,
        "distance": clean(row.get("distance")),
        "race_class": clean(row.get("race_class") or row.get("race_class_rated")),
        "track_condition": clean(row.get("track_condition")),
        "runs_used": len(used),
        "base_projection_rating": "" if base_projection is None else round(base_projection, 2),
        "last_rating_v2": "" if last_rating is None else round(last_rating, 2),
        "avg_last3_rating_v2": "" if avg_last3 is None else round(avg_last3, 2),
        "peak_rating_v2": "" if peak_rating is None else round(peak_rating, 2),
        "projected_rating_v1": "" if projected is None else round(projected, 2),
        "projection_confidence": confidence,
        "target_rating": "" if target_rating is None else round(target_rating, 2),
        "target_confidence": clean(target.get("target_confidence")),
        "target_method": clean(target.get("target_method")),
        "target_sample_size": clean(target.get("sample_size")),
        "rating_vs_target": "" if rating_vs_target is None else round(rating_vs_target, 2),
        "projection_notes": "side-by-side only; no market, no probability, no fair price",
    })

fields = list(out[0].keys()) if out else []
with OUT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out)

with AUDIT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out)

matched = sum(1 for r in out if clean(r["projected_rating_v1"]))
targeted = sum(1 for r in out if clean(r["target_rating"]))
above = sum(1 for r in out if clean(r["rating_vs_target"]) and float(r["rating_vs_target"]) >= 0)

print("=" * 90)
print("EDGEIQ PROJECTION RATING V1")
print("=" * 90)
print(f"live_rows: {len(live_rows)}")
print(f"projection_rows: {len(out)}")
print(f"with_projection: {matched}")
print(f"with_target: {targeted}")
print(f"projected_above_target: {above}")
print(f"out: {OUT}")
print(f"audit: {AUDIT}")
