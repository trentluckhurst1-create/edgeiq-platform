import pandas as pd

print("[V6_3_EXECUTION_REPLAY] START")

df = pd.read_csv("public/data/edgeiq_runner_dna_weight_ladder_v1_by_race.csv")

summary = df.groupby("version").agg({
    "version_top_won":"mean",
    "version_top_placed":"mean",
    "top_changed_vs_base":"mean"
}).reset_index()

summary["win_pct"] = summary["version_top_won"] * 100
summary["place_pct"] = summary["version_top_placed"] * 100
summary["flip_pct"] = summary["top_changed_vs_base"] * 100

print(summary)

summary.to_csv("public/data/edgeiq_runner_dna_v6_3_execution_replay_v1.csv", index=False)
