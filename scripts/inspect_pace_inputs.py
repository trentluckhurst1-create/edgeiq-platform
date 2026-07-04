import pandas as pd
from pathlib import Path

paths = [
    "public/data/speed_map_report.csv",
    "public/data/ratings_audit_elite_v2.csv",
    "public/data/race_fields.csv",
]

for p in paths:
    print()
    print("FILE:", p)
    path = Path(p)
    if not path.exists():
        print("MISSING")
        continue

    df = pd.read_csv(path, low_memory=False)
    print("rows:", len(df))
    print("cols:", list(df.columns))
    print(df.head(12).to_string(index=False))
