import pandas as pd

print("[SP_VALID_ROI_REPLAY_V1] START")

df = pd.read_csv("public/data/edgeiq_historical_replay_settled_v1.csv")

df = df[df["sp_valid"] == "True"].copy()

df["sp_num"] = pd.to_numeric(df["sp_num_settled"], errors="coerce")

results = []

for version in ["BASE","LIGHT","MEDIUM","AGGRESSIVE"]:

    sub = df.copy()

    # proxy score alignment (use your current system signals)
    sub["score_proxy"] = (
        pd.to_numeric(sub["projected_rating_v5_2"], errors="coerce") * 0.4 +
        pd.to_numeric(sub["sectional_strength_rating"], errors="coerce") * 0.3 +
        pd.to_numeric(sub["jockey_score"], errors="coerce") * 0.15 +
        pd.to_numeric(sub["connection_score"], errors="coerce") * 0.15
    )

    sub["rank"] = sub.groupby("race_key")["score_proxy"].rank(ascending=False)

    wins = sub[sub["rank"] == 1]["won"].sum()
    runners = len(sub[sub["rank"] == 1])

    win_pct = wins / max(runners,1)

    # simple SP ROI
    winners = sub[(sub["rank"] == 1) & (sub["won"] == 1)]
    losers = sub[(sub["rank"] == 1) & (sub["won"] == 0)]

    profit = winners["sp_num"].sum() - len(sub[sub["rank"] == 1])
    roi = profit / len(sub[sub["rank"] == 1])

    results.append({
        "version": version,
        "win_pct": win_pct,
        "roi": roi,
        "bets": len(sub[sub["rank"] == 1]),
        "profit": profit
    })

out = pd.DataFrame(results)

print(out)

out.to_csv("public/data/edgeiq_runner_dna_v6_3_sp_valid_roi_replay_v1.csv", index=False)
