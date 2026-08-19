import pandas as pd
import numpy as np

INFILE = r".\public\data\edgeiq_projection_v6_research_prior_rating_backtest.csv"
OUT = r".\public\data\edgeiq_v6_power_sensitivity_replay_v1.csv"
SUMMARY = r".\public\data\edgeiq_v6_power_sensitivity_replay_v1_summary.csv"

df = pd.read_csv(INFILE, low_memory=False)

v6 = df[df["model"] == "V6_RESEARCH_PRIOR"].copy()

for c in ["rating","rating_gap","won","placed"]:
    v6[c] = pd.to_numeric(v6[c], errors="coerce")

powers = [0.45,0.50,0.55,0.60,0.65,0.70,0.75,0.80]
cap = 0.35

rows = []
detail_rows = []

for power in powers:
    x = v6.copy()

    def probs(g):
        gaps = (g["rating"] - g["rating"].median()).fillna(-99)
        raw = np.exp(np.clip(gaps * power / 10.0, -20, 20))
        p = raw / raw.sum()
        p = np.minimum(p, cap)
        p = p / p.sum()
        return pd.Series(p, index=g.index)

    x["model_prob_power"] = x.groupby("race_key", group_keys=False).apply(probs)
    x["fair_price_power"] = np.where(x["model_prob_power"] > 0, 1 / x["model_prob_power"], np.nan)

    rank1 = x[pd.to_numeric(x["rank"], errors="coerce") == 1].copy()

    rows.append({
        "power": power,
        "races": x["race_key"].nunique(),
        "rank1_win_pct": round(rank1["won"].mean() * 100, 2),
        "rank1_place_pct": round(rank1["placed"].mean() * 100, 2),
        "avg_rank1_fair_price": round(rank1["fair_price_power"].mean(), 4),
        "min_rank1_fair_price": round(rank1["fair_price_power"].min(), 4),
        "max_rank1_fair_price": round(rank1["fair_price_power"].max(), 4),
        "rank1_under_2_count": int((rank1["fair_price_power"] < 2).sum()),
        "rank1_under_3_count": int((rank1["fair_price_power"] < 3).sum()),
        "rank1_3_to_6_count": int(((rank1["fair_price_power"] >= 3) & (rank1["fair_price_power"] < 6)).sum()),
        "rank1_over_6_count": int((rank1["fair_price_power"] >= 6).sum()),
    })

    keep = rank1[[
        "race_key","race_date","track","distance","race_name","horse",
        "rating","rating_gap","projection_band","rank","won","placed"
    ]].copy()
    keep["power"] = power
    keep["fair_price_power"] = rank1["fair_price_power"]
    detail_rows.append(keep)

pd.DataFrame(rows).to_csv(SUMMARY, index=False)
pd.concat(detail_rows, ignore_index=True).to_csv(OUT, index=False)

print("[V6_POWER_SENSITIVITY] COMPLETE")
print(pd.DataFrame(rows).to_string(index=False))
