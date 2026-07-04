from pathlib import Path
import pandas as pd
import re

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

OUT = PUBLIC / "edgeiq_positional_expansion_source_inventory_v1.csv"
DIAG = PUBLIC / "edgeiq_positional_expansion_source_inventory_v1_diagnostics.csv"

KEY_COLS = [
    "in_run",
    "in_run_positions_raw",
    "pos_800",
    "pos_400",
    "finish_pos",
    "finish_pos_num",
    "sectional_600",
    "sectional_600_seconds",
    "margin",
    "margin_num",
    "horse",
    "horse_name",
]

rows = []

for path in ROOT.rglob("*.csv"):
    try:
        df = pd.read_csv(path, dtype=str, nrows=3, low_memory=False)
        cols = list(df.columns)
        lower = [c.lower() for c in cols]

        score = 0
        matched = []

        for key in KEY_COLS:
            for c in cols:
                if key.lower() == c.lower() or key.lower() in c.lower():
                    score += 1
                    matched.append(c)

        if score >= 3:
            try:
                line_count = sum(1 for _ in open(path, "r", encoding="utf-8", errors="ignore")) - 1
            except Exception:
                line_count = ""

            rows.append({
                "file": str(path),
                "name": path.name,
                "rows_estimate": line_count,
                "score": score,
                "matched_columns": " | ".join(sorted(set(matched))),
                "all_columns": " | ".join(cols),
            })

    except Exception:
        pass

out = pd.DataFrame(rows)

if out.empty:
    raise SystemExit("NO POSITIONAL EXPANSION SOURCES FOUND")

out = out.sort_values(["score", "rows_estimate"], ascending=[False, False])
out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "candidate_files": len(out),
    "total_estimated_rows": pd.to_numeric(out["rows_estimate"], errors="coerce").fillna(0).sum(),
    "output": str(OUT),
}])
diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ POSITIONAL EXPANSION SOURCE INVENTORY V1")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(out[["name", "rows_estimate", "score", "matched_columns"]].head(80).to_string(index=False))
