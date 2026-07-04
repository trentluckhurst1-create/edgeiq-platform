from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

files = list((ROOT / "public/data").glob("*reliability*.csv"))

print("\n=== REL FILES FOUND ===")
for f in files:
    try:
        df = pd.read_csv(f)
        print(f.name, "-> rows:", len(df))
    except Exception as e:
        print(f.name, "-> ERROR:", e)

print("\n=== EXPECTED FILE CHECK ===")
target = ROOT / "public/data/edgeiq_live_race_reliability_v1_feed.csv"
print("Target exists:", target.exists())
if target.exists():
    df = pd.read_csv(target)
    print("Target rows:", len(df))
