import pandas as pd

df = pd.read_csv(
    r".\public\data\edgeiq_projection_v6_research_prior_rating_backtest.csv",
    low_memory=False
)

for c in ["rank","won","placed","rating_gap","rating","fair_price"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

v5 = df[df["model"] == "V5_1_PRODUCTION_PRIOR"].copy()
v6 = df[df["model"] == "V6_RESEARCH_PRIOR"].copy()

keys = ["race_key", "horse"]

v5w = v5[
    (v5["projection_band"] == "ELITE") &
    (v5["won"] == 1)
].copy()

v5w = v5w[[
    "race_key","race_date","track","distance","race_name","horse",
    "rating","rating_gap","projection_band","rank","fair_price","won","placed"
]].rename(columns={
    "rating":"v5_rating",
    "rating_gap":"v5_rating_gap",
    "projection_band":"v5_projection_band",
    "rank":"v5_rank",
    "fair_price":"v5_fair_price",
    "won":"v5_won",
    "placed":"v5_placed"
})

v6s = v6[[
    "race_key","horse",
    "rating","rating_gap","projection_band","rank","fair_price","won","placed"
]].rename(columns={
    "rating":"v6_rating",
    "rating_gap":"v6_rating_gap",
    "projection_band":"v6_projection_band",
    "rank":"v6_rank",
    "fair_price":"v6_fair_price",
    "won":"v6_won",
    "placed":"v6_placed"
})

m = v5w.merge(v6s, on=["race_key","horse"], how="left")

m["v6_rank_change"] = m["v6_rank"] - m["v5_rank"]
m["rating_drop"] = m["v6_rating"] - m["v5_rating"]
m["gap_drop"] = m["v6_rating_gap"] - m["v5_rating_gap"]
m["fair_price_change"] = m["v6_fair_price"] - m["v5_fair_price"]

m.to_csv(
    r".\public\data\edgeiq_v6_elite_winner_damage_audit_v1.csv",
    index=False
)

summary = (
    m.groupby("v6_projection_band")
    .agg(
        winners=("horse","count"),
        avg_v5_gap=("v5_rating_gap","mean"),
        avg_v6_gap=("v6_rating_gap","mean"),
        avg_gap_drop=("gap_drop","mean"),
        avg_v5_rank=("v5_rank","mean"),
        avg_v6_rank=("v6_rank","mean"),
        avg_rank_change=("v6_rank_change","mean"),
        avg_v5_fair_price=("v5_fair_price","mean"),
        avg_v6_fair_price=("v6_fair_price","mean")
    )
    .reset_index()
)

for c in summary.columns:
    if c != "v6_projection_band":
        summary[c] = pd.to_numeric(summary[c], errors="coerce").round(4)

summary.to_csv(
    r".\public\data\edgeiq_v6_elite_winner_damage_audit_v1_summary.csv",
    index=False
)

print("[V6_ELITE_WINNER_DAMAGE_AUDIT] COMPLETE")
print(summary.to_string(index=False))
