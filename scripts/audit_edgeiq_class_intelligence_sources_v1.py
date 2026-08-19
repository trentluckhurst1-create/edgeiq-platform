from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDITS = ROOT / "outputs" / "audits"
AUDITS.mkdir(parents=True, exist_ok=True)

OUT = AUDITS / "edgeiq_class_intelligence_source_audit.csv"

TARGET_COLUMNS = [
    "race_class",
    "race_class_raw",
    "race_class_clean",
    "race_class_band",
    "class_confidence",
    "today_class_score",
    "class_adj",
    "class_adj_raw",
    "class_adj_confidence",
    "class_baseline",
    "class_strength",
    "class_strength_v5",
    "class_base_score",
]

def safe_rows(path: Path):
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []

def nonblank(v):
    return str(v or "").strip() != ""

audit = []

for path in sorted(DATA.glob("*.csv")):
    rows = safe_rows(path)
    if not rows:
        continue

    cols = rows[0].keys()
    relevant = [c for c in cols if c in TARGET_COLUMNS or re.search(r"class|baseline|strength", c, re.I)]
    if not relevant:
        continue

    total = len(rows)
    for col in relevant:
        filled = sum(1 for r in rows if nonblank(r.get(col)))
        examples = []
        for r in rows:
            v = str(r.get(col) or "").strip()
            if v and v not in examples:
                examples.append(v)
            if len(examples) >= 5:
                break

        audit.append({
            "file": path.name,
            "rows": total,
            "column": col,
            "filled": filled,
            "coverage_pct": round((filled / total) * 100, 2) if total else 0,
            "examples": " | ".join(examples),
        })

with OUT.open("w", encoding="utf-8", newline="") as f:
    fields = ["file", "rows", "column", "filled", "coverage_pct", "examples"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(audit)

print("=" * 90)
print("EDGEIQ CLASS INTELLIGENCE SOURCE AUDIT")
print("=" * 90)
print(f"rows_written: {len(audit)}")
print(f"out: {OUT}")
