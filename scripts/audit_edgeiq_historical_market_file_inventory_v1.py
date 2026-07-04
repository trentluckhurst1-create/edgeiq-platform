from pathlib import Path
import pandas as pd

root = Path(r".\public\data")

keywords = [
    "market",
    "price",
    "odds",
    "fixed",
    "sportsbet",
    "tab",
    "tote"
]

rows = []

for f in root.rglob("*.csv"):
    try:
        cols = pd.read_csv(f, nrows=0).columns.tolist()
    except:
        continue

    matches = [
        c for c in cols
        if any(k in c.lower() for k in keywords)
    ]

    if matches:
        rows.append({
            "file": str(f),
            "column_count": len(cols),
            "market_columns": " | ".join(matches)
        })

out = pd.DataFrame(rows)

out = out.sort_values(
    ["file"]
).reset_index(drop=True)

out.to_csv(
    r".\public\data\edgeiq_historical_market_file_inventory_v1.csv",
    index=False
)

print(out.to_string(index=False))
