from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_probability_archive_v1_1.csv"

OUT = DATA / "edgeiq_pricing_replay_model_state_reconstruction_v1.csv"
SUMMARY = DATA / "edgeiq_pricing_replay_model_state_reconstruction_v1_summary.csv"
AUDIT = DATA / "edgeiq_pricing_replay_model_state_reconstruction_v1_audit.csv"

print("[PRICING_REPLAY_MODEL_STATE_RECONSTRUCTION_V1] START")

df = pd.read_csv(SRC, low_memory=False)

df["final_rating"] = pd.to_numeric(df["final_rating"], errors="coerce")
df["final_probability"] = pd.to_numeric(df["final_probability"], errors="coerce")
df["final_fair_price"] = pd.to_numeric(df["final_fair_price"], errors="coerce")

df["has_archived_probability"] = (
    df["final_probability"].notna() &
    (df["final_probability"] > 0)
)

def reconstruct_race(g):
    g = g.copy()

    ratings = pd.to_numeric(g["final_rating"], errors="coerce")

    if ratings.notna().sum() < 2:
        g["reconstructed_probability"] = np.nan
        g["reconstructed_fair_price"] = np.nan
        g["reconstruction_status"] = "INSUFFICIENT_RATING_FIELD"
        return g

    mean_rating = ratings.mean()
    std_rating = ratings.std()

    if pd.isna(std_rating) or std_rating == 0:
        score = ratings - mean_rating
    else:
        score = (ratings - mean_rating) / std_rating

    field_size = len(g)

    if field_size <= 7:
        temp = 0.95
    elif field_size <= 10:
        temp = 1.05
    elif field_size <= 13:
        temp = 1.15
    else:
        temp = 1.25

    exp_score = np.exp(score / temp)
    prob = exp_score / exp_score.sum()

    g["reconstructed_probability"] = prob
    g["reconstructed_fair_price"] = 1 / prob
    g["reconstruction_status"] = "RECONSTRUCTED_FROM_HISTORICAL_RATING"

    return g

recon = (
    df
    .groupby("race_key", group_keys=False)
    .apply(reconstruct_race)
)

recon["replay_probability"] = recon["final_probability"].where(
    recon["has_archived_probability"],
    recon["reconstructed_probability"]
)

recon["replay_fair_price"] = recon["final_fair_price"].where(
    recon["has_archived_probability"],
    recon["reconstructed_fair_price"]
)

recon["replay_probability_source"] = recon["has_archived_probability"].map(
    {
        True: "ARCHIVED_PROBABILITY",
        False: "RECONSTRUCTED_FROM_HISTORICAL_RATING"
    }
)

recon["replay_probability"] = pd.to_numeric(
    recon["replay_probability"],
    errors="coerce"
)

recon["replay_fair_price"] = pd.to_numeric(
    recon["replay_fair_price"],
    errors="coerce"
)

recon["has_replay_probability"] = (
    recon["replay_probability"].notna() &
    (recon["replay_probability"] > 0)
)

recon["probability_sum_by_race"] = (
    recon
    .groupby("race_key")["replay_probability"]
    .transform("sum")
)

recon["probability_sum_ok"] = (
    recon["probability_sum_by_race"]
    .between(0.995, 1.005)
)

recon["built_at"] = datetime.now(timezone.utc).isoformat()

recon.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": len(recon),
    "races": recon["race_key"].nunique(),
    "archived_probability_rows": int(recon["has_archived_probability"].sum()),
    "reconstructed_probability_rows": int((~recon["has_archived_probability"] & recon["has_replay_probability"]).sum()),
    "replay_probability_rows": int(recon["has_replay_probability"].sum()),
    "replay_probability_coverage_pct": round(float(recon["has_replay_probability"].mean() * 100), 2),
    "races_probability_sum_ok": int(
        recon.groupby("race_key")["probability_sum_ok"].max().sum()
    ),
    "status": "MODEL_STATE_RECONSTRUCTION_BUILT_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

audit = (
    recon
    .groupby("replay_probability_source")
    .agg(
        rows=("horse", "count"),
        races=("race_key", "nunique"),
        avg_probability=("replay_probability", "mean"),
        avg_fair_price=("replay_fair_price", "mean")
    )
    .reset_index()
)

audit.to_csv(AUDIT, index=False)

print("[PRICING_REPLAY_MODEL_STATE_RECONSTRUCTION_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print(summary.to_string(index=False))
print("")
print(audit.to_string(index=False))
