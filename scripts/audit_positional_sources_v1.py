from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard" / "racing-dashboard"
PUBLIC = DASH / "public" / "data"

OUT = PUBLIC / "edgeiq_positional_source_audit_v1.csv"
DIAG = PUBLIC / "edgeiq_positional_source_audit_v1_diagnostics.csv"

KEYWORDS = [
    "pos", "position", "settle", "settling", "in_run", "inrun",
    "turn", "800", "600", "400", "200", "lead", "leader",
    "margin", "sectional", "run_style", "speed", "pace"
]

search_roots = [
    ROOT,
    DASH,
    PUBLIC,
    ROOT / "outputs",
]

rows = []

for root in search_roots:
    if not root.exists():
        continue

    for path in root.rglob("*.csv"):
        try:
            df = pd.read_csv(path, nrows=5, dtype=str, low_memory=False)
            cols = list(df.columns)
            matched = [c for c in cols if any(k in c.lower() for k in KEYWORDS)]

            if matched:
                rows.append({
                    "file": str(path),
                    "name": path.name,
                    "rows_estimate": sum(1 for _ in open(path, "r", encoding="utf-8", errors="ignore")) - 1,
                    "matched_columns": " | ".join(matched),
                    "all_columns": " | ".join(cols),
                })

        except Exception as e:
            rows.append({
                "file": str(path),
                "name": path.name,
                "rows_estimate": "",
                "matched_columns": f"READ_FAILED: {e}",
                "all_columns": "",
            })

out = pd.DataFrame(rows).drop_duplicates(subset=["file"])
out = out.sort_values(["name"])

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "files_with_possible_positional_columns": len(out),
    "output": str(OUT),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ POSITIONAL SOURCE AUDIT V1")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(out[["name","rows_estimate","matched_columns"]].head(80).to_string(index=False))
