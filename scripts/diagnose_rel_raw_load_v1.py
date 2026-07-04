import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

path = ROOT / "public/data/edgeiq_live_race_reliability_v1_feed.csv"

print("\n=== FILE EXISTS CHECK ===")
print("Path:", path)
print("Exists:", path.exists())

df = pd.read_csv(path)

print("\n=== RAW REL LOAD ===")
print("Shape:", df.shape)
print("Columns:", list(df.columns))

print("\n=== TRACK VALUE COUNT ===")
if "track" in df.columns:
    print(df["track"].value_counts().head(10))
else:
    print("NO TRACK COLUMN FOUND")

print("\n=== SAMPLE ROWS ===")
print(df.head(3).to_string(index=False))
