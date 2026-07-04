from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_graphql_harvest_progress_monitor_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_harvest_progress_monitor_v1_summary.csv"

MONTH_RE = re.compile(r"edgeiq_graphql_([a-z]+)_(\d{4})_results_v1\.csv$", re.I)

MONTHS = [
    "january","february","march","april","may","june",
    "july","august","september","october","november","december"
]

def clean(v):
    return "" if v is None else str(v).strip()

def read_summary(path: Path):
    out = {}
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            out[clean(r.get("metric"))] = clean(r.get("value"))
    return out

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for year in range(2000, 2027):
    for month in MONTHS:
        result = DATA / f"edgeiq_graphql_{month}_{year}_results_v1.csv"
        summary = DATA / f"edgeiq_graphql_{month}_{year}_results_v1_summary.csv"
        audit = DATA / f"edgeiq_graphql_{month}_{year}_results_v1_audit.csv"

        s = read_summary(summary)

        rows.append({
            "built_at": built_at,
            "year": year,
            "month": month,
            "result_exists": "TRUE" if result.exists() else "FALSE",
            "summary_exists": "TRUE" if summary.exists() else "FALSE",
            "audit_exists": "TRUE" if audit.exists() else "FALSE",
            "output_rows": s.get("output_rows", ""),
            "meetings_attempted": s.get("meetings_attempted", ""),
            "meetings_ok": s.get("meetings_ok", ""),
            "meetings_failed": s.get("meetings_failed", ""),
            "unique_races": s.get("unique_races", ""),
            "rows_with_trainer": s.get("rows_with_trainer", ""),
            "rows_with_jockey": s.get("rows_with_jockey", ""),
            "rows_with_sp": s.get("rows_with_sp", ""),
            "rows_with_rail": s.get("rows_with_rail", ""),
            "last_write": result.stat().st_mtime if result.exists() else "",
            "result_file": result.name,
        })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys())
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

completed = [r for r in rows if r["result_exists"] == "TRUE"]
total_rows = sum(int(r["output_rows"]) for r in completed if str(r["output_rows"]).isdigit())

summary_rows = [
    {"metric": "status", "value": "EDGEIQ_GRAPHQL_HARVEST_PROGRESS_MONITOR_V1_BUILT"},
    {"metric": "months_checked", "value": len(rows)},
    {"metric": "months_completed", "value": len(completed)},
    {"metric": "completed_output_rows", "value": total_rows},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[HARVEST_PROGRESS_MONITOR_V1] COMPLETE")
print(f"completed_months={len(completed)}")
print(f"rows={total_rows}")
print(f"output={OUT}")
