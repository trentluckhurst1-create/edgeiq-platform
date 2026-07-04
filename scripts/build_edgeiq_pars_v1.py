from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDITS = ROOT / "outputs" / "audits"
AUDITS.mkdir(parents=True, exist_ok=True)

HIST = DATA / "edgeiq_historical_run_rating_v3.csv"
RACE_CODE = DATA / "edgeiq_race_code_v1.csv"

CLASS_OUT = DATA / "edgeiq_class_pars_v1.csv"
DIST_OUT = DATA / "edgeiq_distance_pars_v1.csv"
COND_OUT = DATA / "edgeiq_condition_pars_v1.csv"
AUDIT = AUDITS / "edgeiq_pars_v1_audit.csv"

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def to_float(v):
    s = clean(v).replace(",", "")
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

def race_no(v):
    return str(to_int(v) or "").strip()

def track_norm(v):
    return re.sub(r"[^A-Z0-9]", "", upper(v))

def race_key(r):
    return (
        clean(r.get("race_date")),
        track_norm(r.get("track")),
        race_no(r.get("race_no")),
        clean(r.get("distance")),
    )

def distance_bucket(d):
    if d is None:
        return "UNKNOWN"
    if d <= 1200:
        return "1000-1200"
    if d <= 1400:
        return "1201-1400"
    if d <= 1600:
        return "1401-1600"
    if d <= 1800:
        return "1601-1800"
    if d <= 2200:
        return "1801-2200"
    if d <= 2600:
        return "2201-2600"
    return "2600+"

def percentile(vals, p):
    if not vals:
        return None
    xs = sorted(vals)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return xs[int(k)]
    return xs[f] + (xs[c] - xs[f]) * (k - f)

def stats(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return {
            "sample_size": 0,
            "avg_winner_rating": "",
            "median_winner_rating": "",
            "std_winner_rating": "",
            "p25": "",
            "p50": "",
            "p75": "",
            "p90": "",
            "p95": "",
        }
    return {
        "sample_size": len(vals),
        "avg_winner_rating": round(mean(vals), 2),
        "median_winner_rating": round(median(vals), 2),
        "std_winner_rating": round(pstdev(vals), 2) if len(vals) > 1 else 0,
        "p25": round(percentile(vals, 25), 2),
        "p50": round(percentile(vals, 50), 2),
        "p75": round(percentile(vals, 75), 2),
        "p90": round(percentile(vals, 90), 2),
        "p95": round(percentile(vals, 95), 2),
    }

def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

hist = load_csv(HIST)
race_codes = load_csv(RACE_CODE)

code_by_race = {race_key(r): clean(r.get("race_code")) for r in race_codes}

winner_rows = []
for r in hist:
    if finish_num(r.get("finish_pos")) != 1:
        continue
    rk = race_key(r)
    if code_by_race.get(rk, "FLAT") != "FLAT":
        continue
    rating = to_float(r.get("historical_run_rating_v3"))
    if rating is None:
        continue
    cls = clean(r.get("race_class_clean")) or "UNKNOWN"
    band = clean(r.get("race_class_band")) or "UNKNOWN"
    if cls == "UNKNOWN":
        continue

    d = to_float(r.get("distance"))
    cond = upper(r.get("condition_group") or r.get("condition_recovered")) or "UNKNOWN"

    winner_rows.append({
        **r,
        "_rating": rating,
        "_distance_bucket": distance_bucket(d),
        "_condition_group": cond,
        "_class_key": cls,
        "_class_band": band,
    })

class_groups = defaultdict(list)
distance_groups = defaultdict(list)
condition_groups = defaultdict(list)
class_distance_groups = defaultdict(list)
class_condition_groups = defaultdict(list)

for r in winner_rows:
    class_groups[(r["_class_key"], r["_class_band"])].append(r["_rating"])
    distance_groups[r["_distance_bucket"]].append(r["_rating"])
    condition_groups[r["_condition_group"]].append(r["_rating"])
    class_distance_groups[(r["_class_key"], r["_class_band"], r["_distance_bucket"])].append(r["_rating"])
    class_condition_groups[(r["_class_key"], r["_class_band"], r["_condition_group"])].append(r["_rating"])

class_rows = []
for (cls, band), vals in sorted(class_groups.items()):
    s = stats(vals)
    class_rows.append({
        "race_class_clean": cls,
        "race_class_band": band,
        **s,
    })

distance_rows = []
for bucket, vals in sorted(distance_groups.items()):
    s = stats(vals)
    distance_rows.append({
        "distance_bucket": bucket,
        **s,
    })

condition_rows = []
for cond, vals in sorted(condition_groups.items()):
    s = stats(vals)
    condition_rows.append({
        "condition_group": cond,
        **s,
    })

audit_rows = []
for (cls, band, bucket), vals in sorted(class_distance_groups.items()):
    s = stats(vals)
    audit_rows.append({
        "audit_type": "class_distance",
        "race_class_clean": cls,
        "race_class_band": band,
        "bucket": bucket,
        **s,
    })

for (cls, band, cond), vals in sorted(class_condition_groups.items()):
    s = stats(vals)
    audit_rows.append({
        "audit_type": "class_condition",
        "race_class_clean": cls,
        "race_class_band": band,
        "bucket": cond,
        **s,
    })

for path, rows in [
    (CLASS_OUT, class_rows),
    (DIST_OUT, distance_rows),
    (COND_OUT, condition_rows),
    (AUDIT, audit_rows),
]:
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

print("=" * 90)
print("EDGEIQ PARS V1")
print("=" * 90)
print(f"flat_winner_rows_used: {len(winner_rows)}")
print(f"class_par_rows: {len(class_rows)}")
print(f"distance_par_rows: {len(distance_rows)}")
print(f"condition_par_rows: {len(condition_rows)}")
print(f"class_out: {CLASS_OUT}")
print(f"distance_out: {DIST_OUT}")
print(f"condition_out: {COND_OUT}")
print(f"audit: {AUDIT}")
