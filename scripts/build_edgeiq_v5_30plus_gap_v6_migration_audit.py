import pandas as pd

df = pd.read_csv(
    r".\public\data\edgeiq_v6_vs_v5_prior_rank1_head_to_head.csv",
    low_memory=False
)

for c in ["v5_rating_gap","v6_rating_gap","v5_won","v6_won","v5_placed","v6_placed"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

x = df[df["v5_rating_gap"] >= 30].copy()

def bucket(g):
    if pd.isna(g): return "NO_MODEL"
    if g >= 30: return "30_PLUS"
    if g >= 25: return "25_30"
    if g >= 20: return "20_25"
    if g >= 15: return "15_20"
    if g >= 10: return "10_15"
    if g >= 6: return "6_10"
    if g >= 3: return "3_6"
    if g >= -2: return "NEUTRAL"
    return "NEGATIVE"

x["v6_gap_bucket"] = x["v6_rating_gap"].apply(bucket)

summary = (
    x.groupby("v6_gap_bucket")
    .agg(
        races=("v5_race_key","count"),
        v5_wins=("v5_won","sum"),
        v6_wins=("v6_won","sum"),
        v5_places=("v5_placed","sum"),
        v6_places=("v6_placed","sum"),
        avg_v5_gap=("v5_rating_gap","mean"),
        avg_v6_gap=("v6_rating_gap","mean")
    )
    .reset_index()
)

summary["v5_win_pct"] = (summary["v5_wins"] / summary["races"] * 100).round(2)
summary["v6_win_pct"] = (summary["v6_wins"] / summary["races"] * 100).round(2)
summary["v5_place_pct"] = (summary["v5_places"] / summary["races"] * 100).round(2)
summary["v6_place_pct"] = (summary["v6_places"] / summary["races"] * 100).round(2)
summary["avg_v5_gap"] = summary["avg_v5_gap"].round(4)
summary["avg_v6_gap"] = summary["avg_v6_gap"].round(4)

summary = summary[
    [
        "v6_gap_bucket",
        "races",
        "v5_wins",
        "v6_wins",
        "v5_win_pct",
        "v6_win_pct",
        "v5_place_pct",
        "v6_place_pct",
        "avg_v5_gap",
        "avg_v6_gap"
    ]
]

summary.to_csv(
    r".\public\data\edgeiq_v5_30plus_gap_v6_migration_audit.csv",
    index=False
)

print(summary.to_string(index=False))
