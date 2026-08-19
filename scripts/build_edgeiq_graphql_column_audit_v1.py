from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_graphql_column_audit_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_column_audit_v1_summary.csv"

KEYWORDS = {
    "distance": ["distance", "dist", "metre", "meter"],
    "barrier": ["barrier", "gate", "draw"],
    "condition": ["condition", "going", "track_rating", "rating"],
    "speed": ["speed", "sectional", "last600", "last_600", "600"],
    "pace": ["pace", "position", "pos", "settling", "running", "inrun", "in_run", "800", "400"],
    "sp": ["sp", "starting", "price", "odds"],
    "rail": ["rail"],
    "finish": ["finish", "position"],
    "weight": ["weight"],
}

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return clean(v).lower()

if not SRC.exists():
    raise FileNotFoundError(f"Missing source: {SRC}")

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames or []

    stats = {
        field: {
            "column": field,
            "nonblank": 0,
            "blank": 0,
            "sample_1": "",
            "sample_2": "",
            "sample_3": "",
            "possible_roles": set(),
        }
        for field in fields
    }

    total_rows = 0

    for row in reader:
        total_rows += 1

        for field in fields:
            v = clean(row.get(field))

            if v:
                stats[field]["nonblank"] += 1
                if not stats[field]["sample_1"]:
                    stats[field]["sample_1"] = v
                elif not stats[field]["sample_2"] and v != stats[field]["sample_1"]:
                    stats[field]["sample_2"] = v
                elif not stats[field]["sample_3"] and v not in {stats[field]["sample_1"], stats[field]["sample_2"]}:
                    stats[field]["sample_3"] = v
            else:
                stats[field]["blank"] += 1

for field in fields:
    f = norm(field)

    for role, words in KEYWORDS.items():
        if any(w in f for w in words):
            stats[field]["possible_roles"].add(role)

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for field in fields:
    s = stats[field]
    nonblank = s["nonblank"]
    blank = s["blank"]
    pct = round((nonblank / total_rows) * 100, 2) if total_rows else 0

    rows.append({
        "built_at": built_at,
        "column": field,
        "nonblank": nonblank,
        "blank": blank,
        "nonblank_pct": pct,
        "possible_roles": ",".join(sorted(s["possible_roles"])),
        "sample_1": s["sample_1"],
        "sample_2": s["sample_2"],
        "sample_3": s["sample_3"],
    })

rows.sort(key=lambda r: (-float(r["nonblank_pct"]), r["column"]))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(
        f,
        fieldnames=[
            "built_at",
            "column",
            "nonblank",
            "blank",
            "nonblank_pct",
            "possible_roles",
            "sample_1",
            "sample_2",
            "sample_3",
        ],
    )
    w.writeheader()
    w.writerows(rows)

summary = [
    {"metric": "status", "value": "EDGEIQ_GRAPHQL_COLUMN_AUDIT_V1_BUILT"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "rows_scanned", "value": total_rows},
    {"metric": "columns", "value": len(fields)},
    {"metric": "distance_candidates", "value": sum(1 for r in rows if "distance" in r["possible_roles"])},
    {"metric": "barrier_candidates", "value": sum(1 for r in rows if "barrier" in r["possible_roles"])},
    {"metric": "condition_candidates", "value": sum(1 for r in rows if "condition" in r["possible_roles"])},
    {"metric": "speed_candidates", "value": sum(1 for r in rows if "speed" in r["possible_roles"])},
    {"metric": "pace_candidates", "value": sum(1 for r in rows if "pace" in r["possible_roles"])},
    {"metric": "sp_candidates", "value": sum(1 for r in rows if "sp" in r["possible_roles"])},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary)

print("[GRAPHQL_COLUMN_AUDIT_V1] COMPLETE")
print(f"rows_scanned={total_rows}")
print(f"columns={len(fields)}")
print(f"output={OUT}")
