from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

RUNS = DATA / "form_card_runs.csv"

runs = pd.read_csv(RUNS, low_memory=False)

print("=" * 100)
print("FORM CARD RUNS DIAGNOSIS")
print("=" * 100)

print("ROWS:", len(runs))
print()

print("COLUMNS:")
print(list(runs.columns))
print()

if "horse" in runs.columns:
    print("HORSE SAMPLE:")
    print(runs["horse"].dropna().astype(str).head(20).to_string(index=False))
    print()

if "horse_key" in runs.columns:
    print("HORSE_KEY SAMPLE:")
    print(runs["horse_key"].dropna().astype(str).head(20).to_string(index=False))
    print()

if "run_date" in runs.columns:
    print("RUN DATE RANGE:")
    print("MIN:", runs["run_date"].astype(str).min())
    print("MAX:", runs["run_date"].astype(str).max())
    print()

if "track" in runs.columns:
    print("TRACK SAMPLE:")
    print(runs["track"].dropna().astype(str).value_counts().head(20).to_string())
    print()

print("FIRST 10 ROWS:")
print(runs.head(10).to_string(index=False))
