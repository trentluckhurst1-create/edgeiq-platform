from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"
BY_RACE = DATA / "edgeiq_runner_dna_weight_ladder_v1_by_race.csv"

OUT = DATA / "edgeiq_jockey_score_bucket_flip_analysis_v1.csv"
SUMMARY = DATA / "edgeiq_jockey_score_bucket_flip_analysis_v1_summary.csv"

VERSION = "MEDIUM"

def num(x):
    try:
        return float(str(x).replace("$","").replace("%",""))
    except:
        return np.nan

def bucket(x):
    if pd.isna(x):
        return "UNKNOWN"
    if x < 20:
        return "00_20"
    if x < 40:
        return "20_40"
    if x < 60:
        return "40_60"
    if x < 80:
        return "60_80"
    return "80_PLUS"

hist = pd.read_csv(SRC,dtype=str).fillna("")
races = pd.read_csv(BY_RACE,dtype=str).fillna("")

improved = races[
    (races["version"] == VERSION) &
    (races["top_changed_vs_base"] == "True")
].copy()

rows = []

for _, r in improved.iterrows():

    race_key = r["race_key"]
    base_top = r["base_top"]
    new_top = r["version_top"]

    race_df = hist[hist["race_key"] == race_key]

    b = race_df[race_df["horse"] == base_top]
    n = race_df[race_df["horse"] == new_top]

    if b.empty or n.empty:
        continue

    b = b.iloc[0]
    n = n.iloc[0]

    base_score = num(b["jockey_score"])
    new_score = num(n["jockey_score"])

    rows.append({
        "race_key": race_key,
        "base_top": base_top,
        "new_top": new_top,
        "base_jockey_score": base_score,
        "new_jockey_score": new_score,
        "base_bucket": bucket(base_score),
        "new_bucket": bucket(new_score),
        "base_top_won": r["base_top_won"],
        "new_top_won": r["version_top_won"]
    })

out = pd.DataFrame(rows)

bucket_summary = (
    out.groupby(["base_bucket","new_bucket"])
    .agg(
        races=("race_key","count")
    )
    .reset_index()
    .sort_values("races",ascending=False)
)

out.to_csv(OUT,index=False)
bucket_summary.to_csv(SUMMARY,index=False)

print("[JOCKEY_SCORE_BUCKET_FLIP_ANALYSIS_V1] COMPLETE")
print(bucket_summary.head(25).to_string(index=False))
