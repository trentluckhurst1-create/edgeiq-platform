from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_graphql_data_quality_audit_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_data_quality_audit_v1_summary.csv"

MONTH_RE = re.compile(r"edgeiq_graphql_([a-z]+)_(\d{4})_results_v1\.csv$", re.I)

def clean(v):
    return "" if v is None else str(v).strip()

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def pct(a, b):
    return round((a / b) * 100, 2) if b else 0

files = sorted(DATA.glob("edgeiq_graphql_*_*_results_v1.csv"))

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for p in files:
    m = MONTH_RE.match(p.name)
    if not m:
        continue

    month_name, year = m.group(1).lower(), m.group(2)
    data = read_csv(p)
    total = len(data)

    def count(col):
        return sum(1 for r in data if clean(r.get(col)))

    out = {
        "built_at": built_at,
        "year": year,
        "month": month_name,
        "file": p.name,
        "rows": total,
        "unique_races": len(set(f"{clean(r.get('race_date'))}|{clean(r.get('track'))}|{clean(r.get('race_no'))}" for r in data)),
        "unique_tracks": len(set(clean(r.get("track")) for r in data if clean(r.get("track")))),
        "trainer_rows": count("trainer"),
        "trainer_pct": pct(count("trainer"), total),
        "jockey_rows": count("jockey"),
        "jockey_pct": pct(count("jockey"), total),
        "sp_rows": count("starting_price_decimal"),
        "sp_pct": pct(count("starting_price_decimal"), total),
        "rail_rows": count("rail_position"),
        "rail_pct": pct(count("rail_position"), total),
        "condition_rows": count("track_condition"),
        "condition_pct": pct(count("track_condition"), total),
        "track_rating_rows": count("track_rating"),
        "track_rating_pct": pct(count("track_rating"), total),
        "barrier_rows": count("barrier"),
        "barrier_pct": pct(count("barrier"), total),
        "finish_rows": count("finish"),
        "finish_pct": pct(count("finish"), total),
    }
    rows.append(out)

fields = list(rows[0].keys()) if rows else ["built_at","status"]

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary = [
    {"metric":"status","value":"EDGEIQ_GRAPHQL_DATA_QUALITY_AUDIT_V1_BUILT"},
    {"metric":"files_scanned","value":len(rows)},
    {"metric":"total_rows","value":sum(int(r["rows"]) for r in rows)},
    {"metric":"years_seen","value":",".join(sorted(set(r["year"] for r in rows)))},
    {"metric":"output","value":str(OUT)},
    {"metric":"built_at","value":built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary)

print("[GRAPHQL_DATA_QUALITY_AUDIT_V1] COMPLETE")
print(f"files={len(rows)}")
print(f"rows={sum(int(r['rows']) for r in rows)}")
print(f"output={OUT}")
