from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDITS = ROOT / "outputs" / "audits"
AUDITS.mkdir(parents=True, exist_ok=True)

SRC = DATA / "full_career_form.csv"
OUT = DATA / "edgeiq_historical_run_rating_v2.csv"
AUDIT = AUDITS / "edgeiq_historical_run_rating_v2_audit.csv"

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def to_float(v):
    s = clean(v).replace("$", "").replace(",", "").replace("kg", "").replace("KG", "")
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

def compact(v):
    return re.sub(r"[^A-Z0-9]", "", upper(v))

def margin_lengths(v):
    s = upper(v)
    if not s:
        return None
    if s in {"HD", "HEAD"}:
        return 0.2
    if s in {"NK", "NECK"}:
        return 0.3
    if s in {"NOSE", "NS"}:
        return 0.1
    return to_float(s)

def finish_num(v):
    return to_int(v)

def field_size_num(v):
    s = clean(v)
    if s:
        f = to_int(s)
        if f:
            return f
    m = re.search(r"OF\s+(\d+)", upper(v))
    return int(m.group(1)) if m else None

def dist_num(v):
    return to_float(v)

def condition_group(v):
    u = upper(v)
    if "HEAVY" in u or re.search(r"\bH\d", u):
        return "HEAVY"
    if "SOFT" in u or re.search(r"\bS\d", u):
        return "SOFT"
    if "SYN" in u or "POLY" in u or "TAPETA" in u:
        return "SYNTH"
    if "FIRM" in u:
        return "FIRM"
    return "GOOD"

def dist_bucket(d):
    if d is None:
        return "UNKNOWN"
    if d <= 1400:
        return "SPRINT"
    if d <= 1800:
        return "MILE"
    if d <= 2400:
        return "MIDDLE"
    return "STAYING"

def margin_penalty_per_len(bucket):
    return {
        "SPRINT": 2.65,
        "MILE": 2.35,
        "MIDDLE": 2.05,
        "STAYING": 1.55,
    }.get(bucket, 2.2)

def class_key(v):
    u = upper(v)
    if not u:
        return "UNKNOWN"
    if "GROUP 1" in u or re.search(r"\bG1\b", u):
        return "G1"
    if "GROUP 2" in u or re.search(r"\bG2\b", u):
        return "G2"
    if "GROUP 3" in u or re.search(r"\bG3\b", u):
        return "G3"
    if "LISTED" in u or re.search(r"\bLR\b", u):
        return "LISTED"
    m = re.search(r"BM\s?(\d+)", u)
    if m:
        return f"BM{m.group(1)}"
    m = re.search(r"0\s*-\s*(\d+)", u)
    if m:
        return f"BM{m.group(1)}"
    if "MAIDEN" in u or "MDN" in u:
        return "MDN"
    if "OPEN" in u or "HCP" in u:
        return "OPEN"
    if re.search(r"\bCL(\d+)\b", u):
        return re.search(r"\bCL(\d+)\b", u).group(0)
    return u[:18]

def class_base(k):
    if k == "G1": return 100
    if k == "G2": return 96
    if k == "G3": return 93
    if k == "LISTED": return 90
    if k == "OPEN": return 86
    if k.startswith("BM"):
        n = to_int(k)
        return max(60, min(88, float(n or 68)))
    if k.startswith("CL"):
        n = to_int(k) or 1
        return 66 + min(12, n * 3)
    if k == "MDN": return 64
    return 70

def official_race(row):
    return upper(row.get("run_type")) == "RACE"

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    raw_rows = [r for r in csv.DictReader(f)]

parsed = []
for r in raw_rows:
    if not official_race(r):
        continue

    d = dist_num(r.get("distance"))
    fpos = finish_num(r.get("finish_pos"))
    margin = margin_lengths(r.get("margin"))
    field_size = field_size_num(r.get("field_size")) or field_size_num(r.get("finish_pos"))
    old_rating = to_float(r.get("run_rating") or r.get("rating_display"))

    if d is None or fpos is None or margin is None:
        continue

    ckey = class_key(r.get("race_class"))
    cond = condition_group(r.get("track_condition"))
    bucket = dist_bucket(d)

    parsed.append({
        **r,
        "_distance": d,
        "_finish": fpos,
        "_margin": margin,
        "_field_size": field_size or max(8, fpos),
        "_class_key": ckey,
        "_condition": cond,
        "_bucket": bucket,
        "_old_rating": old_rating,
    })

groups = defaultdict(list)
winners = defaultdict(list)

for r in parsed:
    key = (r["_class_key"], r["_bucket"], r["_condition"])
    groups[key].append(r)
    if r["_finish"] == 1:
        winners[key].append(r)

class_strength = {}
for key, group in groups.items():
    win_group = winners.get(key, [])
    base = class_base(key[0])
    if len(win_group) >= 5:
        old_winner_ratings = [x["_old_rating"] for x in win_group if x["_old_rating"] is not None]
        if old_winner_ratings:
            class_strength[key] = 0.65 * base + 0.35 * median(old_winner_ratings)
        else:
            class_strength[key] = base
    else:
        class_strength[key] = base

out_rows = []
for r in parsed:
    key = (r["_class_key"], r["_bucket"], r["_condition"])
    strength = class_strength.get(key, class_base(r["_class_key"]))

    finish = r["_finish"]
    margin = r["_margin"]
    field_size = max(2, r["_field_size"])

    finish_pct = 1 - ((finish - 1) / max(1, field_size - 1))
    result_score = 55 + (finish_pct * 35)
    margin_penalty = min(26, margin * margin_penalty_per_len(r["_bucket"]))

    winner_bonus = 3.5 if finish == 1 else 0
    close_bonus = 1.5 if margin <= 1.0 and finish <= 3 else 0

    rating = (
        0.58 * strength +
        0.42 * result_score +
        winner_bonus +
        close_bonus -
        margin_penalty
    )

    cond_adj = {
        "HEAVY": 0.8,
        "SOFT": 0.3,
        "GOOD": 0.0,
        "FIRM": -0.2,
        "SYNTH": 0.0,
    }.get(r["_condition"], 0)

    rating = max(35, min(105, rating + cond_adj))

    out_rows.append({
        "horse_key": clean(r.get("horse_key")) or compact(r.get("horse")),
        "horse": clean(r.get("horse")),
        "race_date": clean(r.get("run_date")),
        "track": clean(r.get("track")),
        "distance": clean(r.get("distance")),
        "distance_bucket": r["_bucket"],
        "race_class": clean(r.get("race_class")),
        "class_key": r["_class_key"],
        "track_condition": clean(r.get("track_condition")),
        "condition_group": r["_condition"],
        "finish_pos": clean(r.get("finish_pos")),
        "field_size": clean(r.get("field_size")),
        "margin": clean(r.get("margin")),
        "barrier": clean(r.get("barrier")),
        "weight": clean(r.get("weight_carried")),
        "jockey": clean(r.get("jockey")),
        "trainer": clean(r.get("trainer")),
        "sp": clean(r.get("starting_price") or r.get("sp_text")),
        "old_run_rating": "" if r["_old_rating"] is None else round(r["_old_rating"], 2),
        "class_strength": round(strength, 2),
        "result_score": round(result_score, 2),
        "margin_penalty": round(margin_penalty, 2),
        "historical_run_rating_v2": round(rating, 2),
        "rating_version": "historical_run_rating_v2_stage2a_full_career",
        "rating_notes": "performance-only: excludes SP, barrier, weight, jockey, trainer, prior ratings, trend and consistency",
    })

fields = list(out_rows[0].keys()) if out_rows else []

with OUT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out_rows)

with AUDIT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out_rows[:5000])

ratings = [float(r["historical_run_rating_v2"]) for r in out_rows]
print("=" * 90)
print("EDGEIQ HISTORICAL RUN RATING V2 - FULL CAREER SOURCE")
print("=" * 90)
print(f"source_rows: {len(raw_rows)}")
print(f"official_race_rows_parsed: {len(parsed)}")
print(f"rated_rows: {len(out_rows)}")
print(f"rating_min: {min(ratings) if ratings else '-'}")
print(f"rating_median: {median(ratings) if ratings else '-'}")
print(f"rating_max: {max(ratings) if ratings else '-'}")
print(f"out: {OUT}")
print(f"audit: {AUDIT}")
