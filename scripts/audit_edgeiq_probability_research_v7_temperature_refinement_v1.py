from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_pricing_replay_spine_v3_3_temperature6.csv"

OUT = DATA / "edgeiq_probability_research_v7_temperature_refinement_v1.csv"
SUMMARY = DATA / "edgeiq_probability_research_v7_temperature_refinement_v1_summary.csv"

print("[PROBABILITY_RESEARCH_V7_TEMPERATURE_REFINEMENT_V1] START")

df = pd.read_csv(SRC, low_memory=False)

df["_rating"] = pd.to_numeric(df["reconstructed_rating_v3_1"], errors="coerce")
df["_won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)

df["_race_group"] = (
    pd.to_datetime(df["race_date"], errors="coerce").dt.date.astype("string").fillna("") + "|" +
    df["track"].astype(str).str.upper().str.strip() + "|" +
    pd.to_numeric(df["race_no"], errors="coerce").astype("Int64").astype("string").fillna("")
)

temps = [5.25, 5.5, 5.75, 6.0, 6.25, 6.5, 6.75, 7.0]

records = []

for temp in temps:
    frames = []

    for race_key, g in df.groupby("_race_group", dropna=False):
        g = g.copy()
        r = pd.to_numeric(g["_rating"], errors="coerce")

        if r.notna().sum() < 2:
            g["_p"] = 1 / len(g)
        else:
            sd = r.std()
            z = (r - r.mean()) / sd if pd.notna(sd) and sd != 0 else r - r.mean()
            exp_z = np.exp(z / temp)
            g["_p"] = exp_z / exp_z.sum()

        frames.append(g)

    x = pd.concat(frames, ignore_index=True)
    x["_fair"] = 1 / x["_p"]
    x["_rank"] = x.groupby("_race_group")["_p"].rank(method="first", ascending=False)

    eps = 1e-12
    x["_log_loss"] = -(
        x["_won"] * np.log(x["_p"].clip(eps, 1 - eps)) +
        (1 - x["_won"]) * np.log((1 - x["_p"]).clip(eps, 1 - eps))
    )
    x["_brier"] = (x["_p"] - x["_won"]) ** 2

    race_eval = (
        x.groupby("_race_group")
        .agg(
            fav_prob=("_p", "max"),
            fav_fair=("_fair", "min"),
            top_pick_won=("_won", lambda s: int(s.loc[x.loc[s.index, "_rank"] == 1].sum()) if any(x.loc[s.index, "_rank"] == 1) else 0),
            prob_sum=("_p", "sum")
        )
        .reset_index()
    )

    records.append({
        "temperature": temp,
        "rows": len(x),
        "races": x["_race_group"].nunique(),
        "avg_log_loss": float(x["_log_loss"].mean()),
        "avg_brier": float(x["_brier"].mean()),
        "top_pick_wins": int(race_eval["top_pick_won"].sum()),
        "top_pick_win_pct": round(float(race_eval["top_pick_won"].mean() * 100), 2),
        "avg_fav_prob": float(race_eval["fav_prob"].mean()),
        "avg_fav_fair": float(race_eval["fav_fair"].mean()),
        "prob_sum_bad_races": int((~race_eval["prob_sum"].between(0.995, 1.005)).sum())
    })

out = pd.DataFrame(records)
out.to_csv(OUT, index=False)

best_log = out.sort_values("avg_log_loss").head(1).iloc[0]
best_brier = out.sort_values("avg_brier").head(1).iloc[0]

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": int(best_log["rows"]),
    "races": int(best_log["races"]),
    "temps_tested": len(out),
    "best_log_loss_temperature": best_log["temperature"],
    "best_log_loss": best_log["avg_log_loss"],
    "best_brier_temperature": best_brier["temperature"],
    "best_brier": best_brier["avg_brier"],
    "status": "V7_TEMPERATURE_REFINEMENT_COMPLETE_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

print("[PROBABILITY_RESEARCH_V7_TEMPERATURE_REFINEMENT_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print("")
print(out.to_string(index=False))
print("")
print(summary.to_string(index=False))
