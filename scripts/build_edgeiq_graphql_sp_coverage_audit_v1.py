from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_graphql_sp_coverage_audit_v1.csv"

MONTH_RE = re.compile(r"edgeiq_graphql_([a-z]+)_(\d{4})_results_v1\.csv$", re.I)

def clean(v):
    return "" if v is None else str(v).strip()

def pct(a,b):
    return round((a/b)*100,2) if b else 0

def bucket(sp):
    try:
        n = float(sp)
    except:
        return "UNKNOWN"
    if n <= 2: return "FAVOURITE"
    if n <= 4: return "2-4"
    if n <= 8: return "4-8"
    if n <= 15: return "8-15"
    return "15+"

built_at = datetime.now(timezone.utc).isoformat()
agg = {}

for p in DATA.glob("edgeiq_graphql_*_*_results_v1.csv"):
    m = MONTH_RE.match(p.name)
    if not m:
        continue
    year = m.group(2)
    key = year
    agg.setdefault(key, {"year":year, "rows":0, "sp_rows":0, "fav":0, "b2_4":0, "b4_8":0, "b8_15":0, "b15p":0})

    with p.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            agg[key]["rows"] += 1
            sp = clean(r.get("starting_price_decimal"))
            if sp:
                agg[key]["sp_rows"] += 1
                b = bucket(sp)
                if b == "FAVOURITE": agg[key]["fav"] += 1
                elif b == "2-4": agg[key]["b2_4"] += 1
                elif b == "4-8": agg[key]["b4_8"] += 1
                elif b == "8-15": agg[key]["b8_15"] += 1
                elif b == "15+": agg[key]["b15p"] += 1

rows = []
for year, r in sorted(agg.items()):
    total = r["rows"]
    rows.append({
        "built_at": built_at,
        "year": year,
        "rows": total,
        "sp_rows": r["sp_rows"],
        "sp_pct": pct(r["sp_rows"], total),
        "fav_rows": r["fav"],
        "bucket_2_4_rows": r["b2_4"],
        "bucket_4_8_rows": r["b4_8"],
        "bucket_8_15_rows": r["b8_15"],
        "bucket_15_plus_rows": r["b15p"],
    })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["built_at","year"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print("[SP_COVERAGE_AUDIT_V1] COMPLETE")
print(f"years={len(rows)}")
print(f"output={OUT}")
