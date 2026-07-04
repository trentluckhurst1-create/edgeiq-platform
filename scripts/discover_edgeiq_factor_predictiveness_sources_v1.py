from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

KEYWORDS = [
    "historical",
    "performance",
    "rating",
    "runner_dna",
    "factor",
    "sectional",
    "trainer",
    "jockey",
    "results",
    "warehouse",
]

files = sorted(DATA.glob("*.csv"))

rows = []

for path in files:
    name = path.name.lower()

    if not any(k in name for k in KEYWORDS):
        continue

    try:
        df = pd.read_csv(path, nrows=5, dtype=str)
        cols = list(df.columns)
    except Exception as e:
        rows.append({
            "file": path.name,
            "rows_sampled": "ERROR",
            "columns": str(e),
            "has_win": "",
            "has_place": "",
            "has_sp": "",
            "has_factor_cols": "",
        })
        continue

    col_text = "|".join(cols).lower()

    factor_hits = [
        c for c in cols
        if any(x in c.lower() for x in [
            "form", "rating", "distance", "condition", "class",
            "sectional", "profile", "trainer", "jockey", "combo",
            "pace", "score", "band"
        ])
    ]

    rows.append({
        "file": path.name,
        "columns_count": len(cols),
        "has_win": any(x in col_text for x in ["won", "win", "finish_position"]),
        "has_place": any(x in col_text for x in ["placed", "place", "finish_position"]),
        "has_sp": any(x in col_text for x in ["sp", "starting_price", "fixed_win"]),
        "factor_cols_count": len(factor_hits),
        "factor_cols_preview": ", ".join(factor_hits[:20]),
    })

out = pd.DataFrame(rows)
out_path = DATA / "edgeiq_factor_predictiveness_source_discovery_v1.csv"
out.to_csv(out_path, index=False)

print("[FACTOR_PREDICTIVENESS_SOURCE_DISCOVERY_V1] COMPLETE")
print(out.to_string(index=False))
print(f"wrote={out_path}")
