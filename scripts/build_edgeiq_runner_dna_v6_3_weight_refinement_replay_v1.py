import pandas as pd

print("[WEIGHT_REFINEMENT] START")

df = pd.read_csv("public/data/edgeiq_runner_dna_weight_ladder_v1_summary.csv")

print(df)

df.to_csv("public/data/edgeiq_runner_dna_v6_3_weight_refinement_replay_v1.csv", index=False)
