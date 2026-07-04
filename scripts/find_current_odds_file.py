import os
import pandas as pd

print("="*80)
print("FIND CURRENT ODDS FILE")
print("="*80)

paths = [
    r"public\data",
    r"..\..\outputs\markets",
]

for folder in paths:
    print("\nFOLDER:", folder)

    if not os.path.exists(folder):
        print("MISSING")
        continue

    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith(".csv"):
            continue

        if not any(k in f.lower() for k in ["odds", "market", "ladbrokes", "bet"]):
            continue

        path = os.path.join(folder, f)

        try:
            df = pd.read_csv(path, low_memory=False)
            print("\nFILE:", path)
            print("ROWS:", len(df))
            print("COLS:", list(df.columns)[:25])

            if "race_date" in df.columns:
                print("DATES:")
                print(pd.to_datetime(df["race_date"], errors="coerce").dt.date.value_counts().head(10).to_string())

            if "track" in df.columns:
                print("TRACKS:")
                print(sorted(df["track"].astype(str).str.upper().str.strip().dropna().unique())[:30])

        except Exception as e:
            print("\nFILE:", path)
            print("ERROR:", e)
