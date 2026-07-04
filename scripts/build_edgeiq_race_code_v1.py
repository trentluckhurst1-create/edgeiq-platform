from __future__ import annotations

import csv
import re
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDITS = ROOT / "outputs" / "audits"
AUDITS.mkdir(parents=True, exist_ok=True)

SRC = DATA / "edgeiq_class_normalised_master_v1.csv"
OUT = DATA / "edgeiq_race_code_v1.csv"
AUDIT = AUDITS / "edgeiq_race_code_v1_audit.csv"

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def boolish(v):
    return upper(v) in {"TRUE", "YES", "Y", "1"}

def to_float(v):
    s = clean(v).replace("kg", "").replace("KG", "").replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

def race_key(r):
    return (
        clean(r.get("race_date")),
        upper(r.get("track")),
        clean(r.get("race_no")),
        clean(r.get("distance")),
    )

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

official = [
    r for r in rows
    if boolish(r.get("official_run_flag"))
    and not boolish(r.get("trial_flag"))
    and not boolish(r.get("jumpout_flag"))
]

groups = defaultdict(list)
for r in official:
    groups[race_key(r)].append(r)

out_rows = []
for key, group in groups.items():
    race_date, track, race_no, distance = key
    dist = to_float(distance)
    weights = [to_float(r.get("weight")) for r in group]
    weights = [w for w in weights if w is not None and w > 0]
    min_weight = min(weights) if weights else None
    max_weight = max(weights) if weights else None

    race_code = "FLAT"
    reason = "default flat"

    if dist is not None and dist >= 3000 and min_weight is not None and min_weight >= 63:
        race_code = "HIGHWEIGHT"
        reason = "distance >= 3000 and race min weight >= 63"

    out_rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "distance": distance,
        "runner_count": len(group),
        "race_min_weight": "" if min_weight is None else round(min_weight, 2),
        "race_max_weight": "" if max_weight is None else round(max_weight, 2),
        "race_code": race_code,
        "race_code_reason": reason,
    })

fields = list(out_rows[0].keys()) if out_rows else []
with OUT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out_rows)

counts = Counter(r["race_code"] for r in out_rows)
audit_rows = [{"race_code": k, "count": v} for k, v in counts.items()]
with AUDIT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["race_code", "count"])
    w.writeheader()
    w.writerows(audit_rows)

print("=" * 90)
print("EDGEIQ RACE CODE V1")
print("=" * 90)
print(f"official_rows: {len(official)}")
print(f"race_rows: {len(out_rows)}")
for k, v in counts.items():
    print(f"{k}: {v}")
print(f"out: {OUT}")
print(f"audit: {AUDIT}")
