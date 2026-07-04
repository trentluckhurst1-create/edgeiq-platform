from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_pricing_replay_spine_v3_2_reconstructed_normalised.csv"

OUT = DATA / "edgeiq_pricing_replay_v3_2_evaluation.csv"
SUMMARY = DATA / "edgeiq_pricing_replay_v3_2_evaluation_summary.csv"

print("[PRICING_REPLAY_V3_2_EVALUATION] START")

df = pd.read_csv(SRC, low_memory=False)

df["_prob"] = pd.to_numeric(df["reconstructed_replay_probability_v3_2"], errors="coerce")
df["_fair"] = pd.to_numeric(df["reconstructed_replay_fair_price_v3_2"], errors="coerce")
df["_won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)

eps = 1e-12
df["_log_loss"] = -(df["_won"] * np.log(df["_prob"].clip(eps, 1 - eps)) + (1 - df["_won"]) * np.log((1 - df["_prob"]).clip(eps, 1 - eps)))
df["_brier"] = (df["_prob"] - df["_won"]) ** 2

df["_race_group"] = (
    pd.to_datetime(df["race_date"], errors="coerce").dt.date.astype("string").fillna("") + "|" +
    df["track"].astype(str).str.upper().str.strip() + "|" +
    pd.to_numeric(df["race_no"], errors="coerce").astype("Int64").astype("string").fillna("")
)

df["_rank"] = df.groupby("_race_group")["_prob"].rank(method="first", ascending=False)

race_eval = (
    df.groupby("_race_group")
    .agg(
        runners=("horse", "count"),
        winners=("_won", "sum"),
        prob_sum=("_prob", "sum"),
        fav_prob=("_prob", "max"),
        fav_fair=("_fair", "min"),
        top_pick_won=("_won", lambda s: int(s.loc[df.loc[s.index, "_rank"] == 1].sum()) if any(df.loc[s.index, "_rank"] == 1) else 0),
        avg_log_loss=("_log_loss", "mean"),
        avg_brier=("_brier", "mean")
    )
    .reset_index()
)

race_eval.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": len(df),
    "races": df["_race_group"].nunique(),
    "winners": int(df["_won"].sum()),
    "probability_coverage_pct": round(float(df["_prob"].notna().mean() * 100), 2),
    "avg_log_loss": float(df["_log_loss"].mean()),
    "avg_brier": float(df["_brier"].mean()),
    "top_pick_wins": int(race_eval["top_pick_won"].sum()),
    "top_pick_win_pct": round(float(race_eval["top_pick_won"].mean() * 100), 2),
    "avg_fav_prob": float(race_eval["fav_prob"].mean()),
    "avg_fav_fair": float(race_eval["fav_fair"].mean()),
    "prob_sum_bad_races": int((~race_eval["prob_sum"].between(0.995, 1.005)).sum()),
    "status": "PRICING_REPLAY_V3_2_EVALUATED_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

print("[PRICING_REPLAY_V3_2_EVALUATION] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
