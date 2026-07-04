import pandas as pd

print("[PROMOTION_READINESS] START")

exec_df = pd.read_csv("public/data/edgeiq_runner_dna_weight_ladder_v1_summary.csv")

base = exec_df[exec_df["version"]=="BASE"]
med = exec_df[exec_df["version"]=="MEDIUM"]

result = pd.DataFrame([{
    "base_win": base["rank1_win_pct"].values[0],
    "med_win": med["rank1_win_pct"].values[0],
    "base_place": base["rank1_place_pct"].values[0],
    "med_place": med["rank1_place_pct"].values[0],
    "decision": "CANDIDATE" if med["rank1_win_pct"].values[0] > base["rank1_win_pct"].values[0] else "HOLD"
}])

print(result)

result.to_csv("public/data/edgeiq_runner_dna_v6_3_promotion_readiness_v1.csv", index=False)
