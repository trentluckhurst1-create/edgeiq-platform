import pandas as pd

print("[SINGLE_FACTOR_REPLAY] START")

df = pd.read_csv("public/data/edgeiq_historical_replay_settled_v1.csv")

factors = [
    "projected_rating_v5_2",
    "sectional_strength_rating",
    "jockey_score",
    "trainer_score",
    "connection_score"
]

results = []

for f in factors:
    corr = df[[f, "won"]].corr().iloc[0,1]
    results.append({"factor": f, "corr_to_win": corr})

out = pd.DataFrame(results)
print(out)

out.to_csv("public/data/edgeiq_runner_dna_single_factor_replay_v1.csv", index=False)
