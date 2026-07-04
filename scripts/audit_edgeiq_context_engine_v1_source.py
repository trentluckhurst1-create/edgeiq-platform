import csv
import re
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv"
OUT = DATA / "edgeiq_context_engine_v1_source_audit.csv"
SUMMARY = DATA / "edgeiq_context_engine_v1_source_audit_summary.csv"

def clean(v):
    return (v or "").strip()

def to_float(v):
    s = clean(v).replace("$", "").replace(",", "").replace("kg", "").strip()
    try:
        return float(s)
    except Exception:
        return None

def distance_bucket(v):
    n = to_float(clean(v).lower().replace("m",""))
    if n is None:
        return "UNKNOWN"
    if n < 1200:
        return "SPRINT_SHORT"
    if n < 1400:
        return "SPRINT"
    if n < 1600:
        return "SPRINT_MILE"
    if n < 2000:
        return "MILE_MIDDLE"
    if n < 2400:
        return "STAYING"
    return "LONG_STAYING"

def condition_bucket(v):
    s = clean(v).upper()
    if "HEAVY" in s:
        return "HEAVY"
    if "SOFT" in s:
        return "SOFT"
    if "GOOD" in s:
        return "GOOD"
    if "SYNTH" in s:
        return "SYNTHETIC"
    if "FAST" in s:
        return "FAST"
    return "UNKNOWN"

def barrier_bucket(v):
    n = to_float(v)
    if n is None or n <= 0:
        return "UNKNOWN"
    if n <= 4:
        return "INSIDE"
    if n <= 8:
        return "MIDDLE"
    return "WIDE"

def sp_bucket(v):
    n = to_float(v)
    if n is None or n <= 0:
        return "UNKNOWN"
    if n < 2:
        return "ODDS_ON"
    if n < 4:
        return "FAVOURITE_RANGE"
    if n < 8:
        return "MARKET_CHANCE"
    if n < 15:
        return "ROUGH_CHANCE"
    return "OUTSIDER"

def class_bucket(v):
    s = clean(v).upper()
    if not s:
        return "UNKNOWN"
    m = re.search(r"BM\s*([0-9]+)", s)
    if m:
        n = int(m.group(1))
        if n < 58:
            return "BM_LOW"
        if n < 70:
            return "BM_58_69"
        if n < 84:
            return "BM_70_83"
        return "BM_84_PLUS"
    if "MAIDEN" in s or s == "MDN":
        return "MAIDEN"
    if "GROUP" in s or "LISTED" in s or "LR" in s:
        return "BLACK_TYPE"
    if "HANDICAP" in s:
        return "HANDICAP"
    return "OTHER"

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

fields = list(rows[0].keys()) if rows else []

total = len(rows)
nonblank = {}
for f in fields:
    nonblank[f] = sum(1 for r in rows if clean(r.get(f)))

track_counter = Counter(clean(r.get("track")) for r in rows if clean(r.get("track")))
trainer_counter = Counter(clean(r.get("trainer_canonical")) for r in rows if clean(r.get("trainer_canonical")))
jockey_counter = Counter(clean(r.get("jockey_canonical")) for r in rows if clean(r.get("jockey_canonical")))
combo_counter = Counter(clean(r.get("trainer_jockey_canonical")) for r in rows if clean(r.get("trainer_jockey_canonical")))

context_counts = Counter()
for r in rows:
    context_counts[("TRACK", clean(r.get("track")))] += 1
    context_counts[("DISTANCE_BUCKET", distance_bucket(r.get("distance")))] += 1
    context_counts[("CONDITION_BUCKET", condition_bucket(r.get("track_condition")))] += 1
    context_counts[("BARRIER_BUCKET", barrier_bucket(r.get("barrier")))] += 1
    context_counts[("SP_BUCKET", sp_bucket(r.get("sp")))] += 1
    context_counts[("CLASS_BUCKET", class_bucket(r.get("race_class")))] += 1

audit_rows = []
for field, count in sorted(nonblank.items()):
    audit_rows.append({
        "audit_type": "FIELD_COMPLETENESS",
        "name": field,
        "value": "",
        "rows": count,
        "pct": round((count / total * 100), 2) if total else 0,
    })

for label, counter in [
    ("TRACK", track_counter),
    ("TRAINER", trainer_counter),
    ("JOCKEY", jockey_counter),
    ("TRAINER_JOCKEY", combo_counter),
]:
    audit_rows.append({
        "audit_type": "ENTITY_COUNT",
        "name": label,
        "value": "unique",
        "rows": len(counter),
        "pct": "",
    })

for (ctype, cval), count in sorted(context_counts.items(), key=lambda x: (x[0][0], x[0][1])):
    audit_rows.append({
        "audit_type": "CONTEXT_BUCKET",
        "name": ctype,
        "value": cval,
        "rows": count,
        "pct": round((count / total * 100), 2) if total else 0,
    })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["audit_type","name","value","rows","pct"])
    writer.writeheader()
    writer.writerows(audit_rows)

summary_rows = [
    {"metric": "status", "value": "COMPLETE"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "rows", "value": total},
    {"metric": "columns", "value": len(fields)},
    {"metric": "unique_tracks", "value": len(track_counter)},
    {"metric": "unique_trainers", "value": len(trainer_counter)},
    {"metric": "unique_jockeys", "value": len(jockey_counter)},
    {"metric": "unique_trainer_jockey_combos", "value": len(combo_counter)},
    {"metric": "built_at", "value": datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary_rows)

print("[EDGEIQ_CONTEXT_ENGINE_V1_SOURCE_AUDIT] COMPLETE")
print(f"audit={OUT}")
print(f"summary={SUMMARY}")
