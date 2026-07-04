import pandas as pd
import numpy as np
from pathlib import Path

DATA = Path("public/data")
SRC = DATA / "edgeiq_probability_research_v7_tab_candidate_t6.csv"

df = pd.read_csv(SRC, low_memory=False)

df["_sp"] = pd.to_numeric(df["sp_price"], errors="coerce")
df["_won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)
df["_race_group"] = df["_race_group_v4"].astype(str)

winner_sp = df[df["_won"] == 1].copy()
loser_sp = df[df["_won"] == 0].copy()

print("[SP_WINNER_LOSER_DISTRIBUTION]")
print("")
print("winner rows:", len(winner_sp))
print("loser rows:", len(loser_sp))
print("")
print("winner SP describe")
print(winner_sp["_sp"].describe().to_string())
print("")
print("loser SP describe")
print(loser_sp["_sp"].describe().to_string())

print("")
print("[SP VALUE COUNTS TOP 30]")
print(df["_sp"].value_counts().head(30).to_string())

race = (
    df.groupby("_race_group")
    .agg(
        rows=("horse", "count"),
        winners=("_won", "sum"),
        unique_sp=("_sp", "nunique"),
        min_sp=("_sp", "min"),
        max_sp=("_sp", "max"),
        winner_sp=("_sp", lambda s: float(s[df.loc[s.index, "_won"] == 1].iloc[0]) if any(df.loc[s.index, "_won"] == 1) else np.nan),
    )
    .reset_index()
)

print("")
print("[RACES_WITH_ALL_SAME_SP]")
print((race["unique_sp"] == 1).sum())

print("")
print("[RACE SP AUDIT SAMPLE]")
print(race.head(40).to_string(index=False))

race.to_csv(DATA / "edgeiq_sp_winner_loser_integrity_v1.csv", index=False)
