import pandas as pd

df = pd.read_csv(
    ".\public\data\edgeiq_projection_v6_research_prior_rating_backtest.csv",
    low_memory=False
)

elite = df[
    (df["model"] == "V5_1_PRODUCTION_PRIOR") &
    (df["projection_band"] == "ELITE")
].copy()

elite["won"] = pd.to_numeric(elite["won"], errors="coerce").fillna(0)

elite["rating_gap"] = pd.to_numeric(
    elite["rating_gap"],
    errors="coerce"
)

elite["gap_bucket"] = pd.cut(
    elite["rating_gap"],
    bins=[10,15,20,25,30,999],
    labels=[
        "10_15",
        "15_20",
        "20_25",
        "25_30",
        "30_PLUS"
    ]
)

summary = (
    elite.groupby("gap_bucket")
    .agg(
        runners=("horse","count"),
        wins=("won","sum"),
        win_pct=("won","mean")
    )
    .reset_index()
)

summary["win_pct"] = (
    summary["win_pct"] * 100
).round(2)

summary.to_csv(
    ".\public\data\edgeiq_v5_elite_gap_strength_audit.csv",
    index=False
)

print(summary)
