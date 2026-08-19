import pandas as pd

df = pd.read_csv(
    r".\public\data\edgeiq_v6_vs_v5_prior_rank1_head_to_head.csv",
    low_memory=False
)

diff = df[df["same_rank1"] == False].copy()

cols = [
    "v5_race_date",
    "v5_track",
    "v5_distance",
    "v5_race_name",

    "v5_horse",
    "v5_rating",
    "v5_rating_gap",
    "v5_projection_band",
    "v5_won",
    "v5_placed",

    "v6_horse",
    "v6_rating",
    "v6_rating_gap",
    "v6_projection_band",
    "v6_won",
    "v6_placed"
]

diff[cols].to_csv(
    r".\public\data\edgeiq_v6_rank_switch_races_v1.csv",
    index=False
)

summary = []

summary.append({
    "metric":"rank_switch_races",
    "value":len(diff)
})

for track, g in (
    diff.groupby("v5_track")
    .size()
    .sort_values(ascending=False)
    .head(30)
    .items()
):
    summary.append({
        "metric":f"track_{track}",
        "value":int(g)
    })

pd.DataFrame(summary).to_csv(
    r".\public\data\edgeiq_v6_rank_switch_summary_v1.csv",
    index=False
)

print(diff[cols].head(50).to_string())
print()
print(pd.DataFrame(summary).to_string(index=False))
