import pandas as pd

print("[FACTOR_WIN_DRIVER_V1] START")

df = pd.read_csv("public/data/edgeiq_historical_replay_settled_v1.csv")

factors = [
    "projected_rating_v5_2",
    "sectional_strength_rating",
    "jockey_score",
    "trainer_score",
    "connection_score",
    "confidence_adjusted_rating_v6"
]

results = []

for f in factors:

    vals = pd.to_numeric(df[f], errors="coerce")
    df["f_score"] = vals

    top = df.groupby("race_key").apply(lambda x: x.sort_values("f_score", ascending=False).head(1))

    win_rate = top["won"].mean()

    results.append({
        "factor": f,
        "top1_win_rate": win_rate
    })

out = pd.DataFrame(results)

print(out)

out.to_csv("public/data/edgeiq_runner_dna_v6_3_factor_win_driver_v1.csv", index=False)
