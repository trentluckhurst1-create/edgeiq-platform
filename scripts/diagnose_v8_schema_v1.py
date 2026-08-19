import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")

runner = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")

# TRY ALL POSSIBLE V8 FILES
v8_files = list((ROOT / "public/data").glob("*v8*.csv"))

print("FOUND V8 FILES:", len(v8_files))

for f in v8_files:
    try:
        df = pd.read_csv(f)
        print("\nFILE:", f.name)
        print("COLUMNS:", list(df.columns))
        print("SAMPLE KEYS:")
        if "race_key" in df.columns:
            print(df["race_key"].head(3).tolist())
        elif "track" in df.columns:
            print(df[["track","race_no"]].head(3))
    except Exception as e:
        print("FAILED:", f.name, e)
