import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

rel = pd.read_csv(ROOT / "public/data/edgeiq_live_race_reliability_v1_feed.csv")

print("\n=== REL COLUMNS ===")
print(rel.columns.tolist())

print("\n=== SAMPLE ROWS ===")
print(rel.head(5).to_string(index=False))

print("\n=== TRACK VALUE SAMPLE ===")
if "track" in rel.columns:
    print(rel["track"].dropna().head(10))
else:
    print("NO track COLUMN FOUND")
