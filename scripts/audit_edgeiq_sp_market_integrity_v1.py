from pathlib import Path
import pandas as pd
import numpy as np

DATA = Path("public/data")
SRC = DATA / "edgeiq_probability_research_v7_tab_candidate_t6.csv"

df = pd.read_csv(SRC, low_memory=False)

df["_sp"] = pd.to_numeric(df["sp_price"], errors="coerce")
df["_won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)
df["_race_group"] = df["_race_group_v4"].astype(str)

df["raw_market_prob"] = np.where(df["_sp"] > 1, 1 / df["_sp"], np.nan)

race = (
    df.groupby("_race_group")
    .agg(
        rows=("horse", "count"),
        winners=("_won", "sum"),
        sp_rows=("_sp", lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())),
        min_sp=("_sp", "min"),
        max_sp=("_sp", "max"),
        raw_prob_sum=("raw_market_prob", "sum")
    )
    .reset_index()
)

race["valid_market_race"] = (
    race["winners"].eq(1) &
    race["sp_rows"].eq(race["rows"]) &
    race["raw_prob_sum"].between(0.90, 1.80)
)

print("[SP_INTEGRITY_SUMMARY]")
print({
    "rows": len(df),
    "races": df["_race_group"].nunique(),
    "valid_market_races": int(race["valid_market_race"].sum()),
    "invalid_market_races": int((~race["valid_market_race"]).sum()),
    "raw_prob_sum_min": float(race["raw_prob_sum"].min()),
    "raw_prob_sum_max": float(race["raw_prob_sum"].max()),
    "raw_prob_sum_avg": float(race["raw_prob_sum"].mean())
})

print("")
print("[RAW_PROB_SUM_BUCKETS]")
print(pd.cut(
    race["raw_prob_sum"],
    bins=[0,0.5,0.9,1.1,1.3,1.8,3,10,100],
    include_lowest=True
).value_counts().sort_index().to_string())

print("")
print("[BAD_MARKET_RACE_EXAMPLES]")
print(
    race[~race["valid_market_race"]]
    .sort_values("raw_prob_sum")
    .head(30)
    .to_string(index=False)
)

race.to_csv(DATA / "edgeiq_sp_market_integrity_audit_v1.csv", index=False)
