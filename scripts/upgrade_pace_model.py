from __future__ import annotations

import re
from pathlib import Path
import pandas as pd

DATA = ROOT / "public" / "data"
RATINGS = DATA / "ratings_audit_elite_v2.csv"
SPEED = DATA / "speed_map_report.csv"
OUT = DATA / "ratings_audit_elite_v3.csv"

def clean_key(x):
    if pd.isna(x):
        return ""
    s = str(x).upper().strip()
    s = re.sub(r"\([A-Z]{2,4}\)", "", s)
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def race_no_clean(x):
    try:
        return str(int(float(x)))
    except Exception:
        return str(x).strip()

def speed_score(style):
    s = str(style).upper().strip()
    if "LEADER" in s:
        return 100
    if "ON PACE" in s:
        return 80
    if "MIDFIELD" in s:
        return 50
    if "BACKMARKER" in s:
        return 20
    return 50

ratings = pd.read_csv(RATINGS, low_memory=False)
speed = pd.read_csv(SPEED, low_memory=False)

for c in ["speed_map_bucket", "map_style", "runner_style", "pressure_index", "leader_probability", "collapse_probability"]:
    if c in ratings.columns:
        ratings = ratings.drop(columns=[c])

ratings["horse_key_norm"] = ratings["horse"].apply(clean_key)
speed["horse_key_norm"] = speed["horse"].apply(clean_key)

ratings["race_key"] = (
    ratings["race_date"].astype(str).str.strip() + "|" +
    ratings["track"].astype(str).str.upper().str.strip() + "|" +
    ratings["race_no"].apply(race_no_clean)
)

speed["race_key"] = (
    speed["race_date"].astype(str).str.strip() + "|" +
    speed["track"].astype(str).str.upper().str.strip() + "|" +
    speed["race_no"].apply(race_no_clean)
)

speed_small = speed[[
    "race_key",
    "horse_key_norm",
    "speed_map_bucket",
    "map_style",
    "runs_used",
    "official_runs_found",
    "avg_800_pos",
    "avg_400_pos",
    "pace_pressure",
    "confidence",
]].copy()

df = ratings.merge(speed_small, on=["race_key", "horse_key_norm"], how="left")

df["runner_style"] = (
    df["speed_map_bucket"]
    .fillna(df["map_style"])
    .fillna("MIDFIELD")
    .astype(str)
    .str.upper()
    .str.strip()
)

df["early_speed_score"] = df["runner_style"].apply(speed_score)

df["pressure_index"] = 0
df["leader_probability"] = 0.0
df["collapse_probability"] = 0.1

for rk, g in df.groupby("race_key"):
    leaders = int((g["runner_style"] == "LEADER").sum())
    onpace = int((g["runner_style"] == "ON PACE").sum())
    pressure = leaders * 2 + onpace

    if leaders == 0:
        lp = 0.0
    elif leaders == 1:
        lp = 0.75
    elif leaders == 2:
        lp = 0.45
    else:
        lp = 0.20

    if pressure <= 2:
        cp = 0.10
    elif pressure <= 5:
        cp = 0.30
    elif pressure <= 8:
        cp = 0.55
    else:
        cp = 0.75

    df.loc[g.index, "pressure_index"] = pressure
    df.loc[g.index, "leader_probability"] = lp
    df.loc[g.index, "collapse_probability"] = cp

def pace_adjust(row):
    base = float(row.get("elite_today_rating", 0) or 0)
    style = str(row.get("runner_style", "")).upper()
    lp = float(row.get("leader_probability", 0) or 0)
    cp = float(row.get("collapse_probability", 0.1) or 0.1)

    adj = 1.0

    if style == "LEADER":
        adj += (lp - 0.50) * 0.20
    elif style == "ON PACE":
        adj += (lp - 0.50) * 0.10
    elif style == "BACKMARKER":
        adj += (cp - 0.30) * 0.25
    elif style == "MIDFIELD":
        adj += (cp - 0.30) * 0.10

    return round(base * adj, 5)

df["pace_adjusted_rating"] = df.apply(pace_adjust, axis=1)
df["elite_today_rating"] = df["pace_adjusted_rating"]

df["elite_prob"] = 0.0
df["elite_rated_price"] = None

for rk, g in df.groupby("race_key"):
    total = g["elite_today_rating"].sum()
    if total > 0:
        probs = g["elite_today_rating"] / total
        df.loc[g.index, "elite_prob"] = probs
        df.loc[g.index, "elite_rated_price"] = (1 / probs).round(3)

df.to_csv(OUT, index=False)

print("PACE MODEL FULL REWRITE COMPLETE")
print()
print("STYLE DISTRIBUTION:")
print(df["runner_style"].value_counts(dropna=False))
print()
print(df[[
    "horse",
    "runner_style",
    "runs_used",
    "official_runs_found",
    "pressure_index",
    "leader_probability",
    "collapse_probability",
    "pace_adjusted_rating",
    "elite_rated_price",
]].head(40).to_string(index=False))
