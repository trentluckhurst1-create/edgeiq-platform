import pandas as pd

df = pd.read_csv(
    r".\public\data\edgeiq_projection_v6_research_prior_rating_backtest.csv",
    low_memory=False
)

rows = []

for model in ["V5_1_PRODUCTION_PRIOR", "V6_RESEARCH_PRIOR"]:
    x = df[
        (df["model"] == model) &
        (df["projection_band"] == "ELITE")
    ].copy()

    x["won"] = pd.to_numeric(x["won"], errors="coerce").fillna(0)
    x["rating_gap"] = pd.to_numeric(x["rating_gap"], errors="coerce")

    x["gap_bucket"] = pd.cut(
        x["rating_gap"],
        bins=[10,15,20,25,30,999],
        labels=["10_15","15_20","20_25","25_30","30_PLUS"]
    )

    s = (
        x.groupby("gap_bucket")
        .agg(
            runners=("horse","count"),
            wins=("won","sum"),
            win_pct=("won","mean"),
            avg_fair_price=("fair_price","mean")
        )
        .reset_index()
    )

    s["model"] = model
    s["win_pct"] = (s["win_pct"] * 100).round(2)
    s["avg_fair_price"] = s["avg_fair_price"].round(4)

    rows.append(s)

out = pd.concat(rows, ignore_index=True)

out = out[[
    "model",
    "gap_bucket",
    "runners",
    "wins",
    "win_pct",
    "avg_fair_price"
]]

out.to_csv(
    r".\public\data\edgeiq_v5_v6_elite_gap_strength_comparison.csv",
    index=False
)

print(out.to_string(index=False))
