from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
RUNS = DATA / "form_card_runs.csv"

def clean_key(x):
    s = str(x or "").upper()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s.strip()

live = pd.read_csv(LIVE, low_memory=False)
runs = pd.read_csv(RUNS, low_memory=False)

print("=" * 100)
print("LIVE HORSES")
print("=" * 100)

for h in live["horse"].astype(str).tolist():
    print(h)

print()
print("=" * 100)
print("SEARCHING form_card_runs")
print("=" * 100)

for h in live["horse"].astype(str).tolist():

    key = clean_key(h)

    exact = runs[runs["horse_key"].astype(str).map(clean_key).eq(key)]

    contains = runs[
        runs["horse"].astype(str).str.upper().str.contains(
            h.upper().replace("'", ""),
            na=False,
            regex=False
        )
    ]

    print()
    print("-" * 100)
    print("HORSE:", h)
    print("KEY:", key)
    print("EXACT horse_key MATCHES:", len(exact))
    print("NAME CONTAINS MATCHES:", len(contains))

    if len(exact):
        print()
        print("EXACT SAMPLE:")
        print(exact[["horse", "horse_key", "run_date", "track", "run_rating"]].head(5).to_string(index=False))

    if len(contains):
        print()
        print("CONTAINS SAMPLE:")
        print(contains[["horse", "horse_key", "run_date", "track", "run_rating"]].head(5).to_string(index=False))
