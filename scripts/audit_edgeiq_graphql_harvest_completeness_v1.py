import csv
import os
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

OUT = DATA / "edgeiq_graphql_harvest_completeness_audit_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_harvest_completeness_audit_v1_summary.csv"

MONTHS = [
    ("january", 1), ("february", 2), ("march", 3), ("april", 4),
    ("may", 5), ("june", 6), ("july", 7), ("august", 8),
    ("september", 9), ("october", 10), ("november", 11), ("december", 12),
]

def count_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return max(sum(1 for _ in f) - 1, 0)
    except Exception:
        try:
            with path.open("r", encoding="utf-8", newline="") as f:
                return max(sum(1 for _ in f) - 1, 0)
        except Exception:
            return -1

rows = []

for year in range(2000, 2027):
    for month_name, month_no in MONTHS:
        name = f"edgeiq_graphql_{month_name}_{year}_results_v1.csv"
        path = DATA / name
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        row_count = count_rows(path) if exists else 0

        if not exists:
            status = "MISSING"
        elif row_count < 0:
            status = "READ_ERROR"
        elif row_count == 0:
            status = "ZERO_ROWS"
        elif size < 1000:
            status = "TINY_FILE"
        else:
            status = "OK"

        rows.append({
            "year": year,
            "month_no": month_no,
            "month": month_name.upper(),
            "expected_file": name,
            "exists": exists,
            "size_bytes": size,
            "row_count": row_count,
            "status": status,
            "file_path": str(path),
        })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

total = len(rows)
existing = sum(1 for r in rows if r["exists"])
ok = sum(1 for r in rows if r["status"] == "OK")
missing = sum(1 for r in rows if r["status"] == "MISSING")
zero = sum(1 for r in rows if r["status"] == "ZERO_ROWS")
tiny = sum(1 for r in rows if r["status"] == "TINY_FILE")
read_error = sum(1 for r in rows if r["status"] == "READ_ERROR")
total_rows = sum(int(r["row_count"]) for r in rows if int(r["row_count"]) > 0)

summary_rows = [
    {"metric": "status", "value": "COMPLETE"},
    {"metric": "expected_month_files_2000_2026", "value": total},
    {"metric": "existing_files", "value": existing},
    {"metric": "ok_files", "value": ok},
    {"metric": "missing_files", "value": missing},
    {"metric": "zero_row_files", "value": zero},
    {"metric": "tiny_files", "value": tiny},
    {"metric": "read_error_files", "value": read_error},
    {"metric": "total_rows_across_existing_files", "value": total_rows},
    {"metric": "built_at", "value": datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader()
    writer.writerows(summary_rows)

print("[GRAPHQL_HARVEST_COMPLETENESS_AUDIT_V1] COMPLETE")
print(f"audit={OUT}")
print(f"summary={SUMMARY}")
