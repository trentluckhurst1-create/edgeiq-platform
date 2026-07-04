import pandas as pd

print("[V6_3_PROB_CALIBRATION] START")

df = pd.read_csv("public/data/edgeiq_historical_replay_settled_v1.csv")

df["error"] = abs(df["runner_rank"] - df["runner_score"].rank())

print("Mean rank error:", df["error"].mean())

df.to_csv("public/data/edgeiq_runner_dna_v6_3_probability_calibration_replay_v1.csv", index=False)
