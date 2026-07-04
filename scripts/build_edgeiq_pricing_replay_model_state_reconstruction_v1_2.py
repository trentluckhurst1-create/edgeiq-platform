from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_pricing_replay_model_state_reconstruction_v1_1.csv"

OUT = DATA / "edgeiq_pricing_replay_model_state_reconstruction_v1_2.csv"
SUMMARY = DATA / "edgeiq_pricing_replay_model_state_reconstruction_v1_2_summary.csv"
AUDIT = DATA / "edgeiq_pricing_replay_model_state_reconstruction_v1_2_audit.csv"

print("[PRICING_REPLAY_MODEL_STATE_RECONSTRUCTION_V1_2] START")

df = pd.read_csv(SRC, low_memory=False)

df["replay_probability"] = pd.to_numeric(df["replay_probability"], errors="coerce")
df["replay_fair_price"] = pd.to_numeric(df["replay_fair_price"], errors="coerce")

df["probability_sum_before_v1_2"] = (
    df.groupby("race_key")["replay_probability"].transform("sum")
)

df["normalisation_factor_v1_2"] = np.where(
    df["probability_sum_before_v1_2"] > 0,
    1 / df["probability_sum_before_v1_2"],
    np.nan
)

df["replay_probability_v1_2"] = (
    df["replay_probability"] *
    df["normalisation_factor_v1_2"]
)

df["replay_fair_price_v1_2"] = np.where(
    df["replay_probability_v1_2"] > 0,
    1 / df["replay_probability_v1_2"],
    np.nan
)

df["probability_sum_after_v1_2"] = (
    df.groupby("race_key")["replay_probability_v1_2"].transform("sum")
)

df["normalisation_status_v1_2"] = np.where(
    df["probability_sum_before_v1_2"].between(0.995, 1.005),
    "UNCHANGED_SUM_OK",
    "RENORMALISED_TO_100"
)

df["replay_probability_final"] = df["replay_probability_v1_2"]
df["replay_fair_price_final"] = df["replay_fair_price_v1_2"]

df["built_at_v1_2"] = datetime.now(timezone.utc).isoformat()

df.to_csv(OUT, index=False)

race_audit = (
    df.groupby("race_key")
    .agg(
        runners=("horse", "count"),
        sum_before=("probability_sum_before_v1_2", "first"),
        sum_after=("probability_sum_after_v1_2", "first"),
        archived_rows=("has_archived_probability", lambda s: int(pd.Series(s).astype(str).str.lower().isin(["true", "1"]).sum())),
        reconstructed_rows=("replay_probability_source", lambda s: int((s == "RECONSTRUCTED_FROM_HISTORICAL_RATING").sum())),
        status=("normalisation_status_v1_2", "first")
    )
    .reset_index()
)

race_audit.to_csv(AUDIT, index=False)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": len(df),
    "races": df["race_key"].nunique(),
    "probability_rows": int((df["replay_probability_final"].notna() & (df["replay_probability_final"] > 0)).sum()),
    "probability_coverage_pct": round(float((df["replay_probability_final"].notna() & (df["replay_probability_final"] > 0)).mean() * 100), 2),
    "races_sum_ok_after": int(race_audit["sum_after"].between(0.995, 1.005).sum()),
    "races_sum_bad_after": int((~race_audit["sum_after"].between(0.995, 1.005)).sum()),
    "races_renormalised": int((race_audit["status"] == "RENORMALISED_TO_100").sum()),
    "status": "MODEL_STATE_RECONSTRUCTION_V1_2_NORMALISED_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

print("[PRICING_REPLAY_MODEL_STATE_RECONSTRUCTION_V1_2] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print(summary.to_string(index=False))
print("")
print(race_audit["status"].value_counts().to_string())
