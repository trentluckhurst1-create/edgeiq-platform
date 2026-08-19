from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_pricing_replay_spine_v3_1_reconstructed.csv"

OUT = DATA / "edgeiq_pricing_replay_spine_v3_2_reconstructed_normalised.csv"
SUMMARY = DATA / "edgeiq_pricing_replay_spine_v3_2_reconstructed_normalised_summary.csv"
AUDIT = DATA / "edgeiq_pricing_replay_spine_v3_2_reconstructed_normalised_audit.csv"

print("[PRICING_REPLAY_SPINE_V3_2_RECONSTRUCTED_NORMALISED] START")

df = pd.read_csv(SRC, low_memory=False)

df["_race_group_v3_2"] = (
    pd.to_datetime(df["race_date"], errors="coerce").dt.date.astype("string").fillna("") + "|" +
    df["track"].astype(str).str.upper().str.strip() + "|" +
    pd.to_numeric(df["race_no"], errors="coerce").astype("Int64").astype("string").fillna("")
)

df["reconstructed_replay_probability_v3_1"] = pd.to_numeric(
    df["reconstructed_replay_probability_v3_1"],
    errors="coerce"
)

df["probability_sum_before_v3_2"] = (
    df.groupby("_race_group_v3_2")["reconstructed_replay_probability_v3_1"]
    .transform("sum")
)

df["normalisation_factor_v3_2"] = np.where(
    df["probability_sum_before_v3_2"] > 0,
    1 / df["probability_sum_before_v3_2"],
    np.nan
)

df["reconstructed_replay_probability_v3_2"] = (
    df["reconstructed_replay_probability_v3_1"] *
    df["normalisation_factor_v3_2"]
)

df["reconstructed_replay_fair_price_v3_2"] = np.where(
    df["reconstructed_replay_probability_v3_2"] > 0,
    1 / df["reconstructed_replay_probability_v3_2"],
    np.nan
)

df["probability_sum_after_v3_2"] = (
    df.groupby("_race_group_v3_2")["reconstructed_replay_probability_v3_2"]
    .transform("sum")
)

df["normalisation_status_v3_2"] = np.where(
    df["probability_sum_before_v3_2"].between(0.995, 1.005),
    "UNCHANGED_SUM_OK",
    "RENORMALISED_REPLAY_SUBSET_TO_100"
)

df["built_at_v3_2"] = datetime.now(timezone.utc).isoformat()

df.to_csv(OUT, index=False)

race_audit = (
    df.groupby("_race_group_v3_2")
    .agg(
        runners=("horse", "count"),
        winners=("won", "sum"),
        sum_before=("probability_sum_before_v3_2", "first"),
        sum_after=("probability_sum_after_v3_2", "first"),
        min_prob=("reconstructed_replay_probability_v3_2", "min"),
        max_prob=("reconstructed_replay_probability_v3_2", "max"),
        min_price=("reconstructed_replay_fair_price_v3_2", "min"),
        max_price=("reconstructed_replay_fair_price_v3_2", "max"),
        status=("normalisation_status_v3_2", "first")
    )
    .reset_index()
)

race_audit.to_csv(AUDIT, index=False)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": len(df),
    "races": df["_race_group_v3_2"].nunique(),
    "probability_rows": int(df["reconstructed_replay_probability_v3_2"].notna().sum()),
    "probability_coverage_pct": round(float(df["reconstructed_replay_probability_v3_2"].notna().mean() * 100), 2),
    "races_prob_sum_ok": int(race_audit["sum_after"].between(0.995, 1.005).sum()),
    "races_prob_sum_bad": int((~race_audit["sum_after"].between(0.995, 1.005)).sum()),
    "races_renormalised": int((race_audit["status"] == "RENORMALISED_REPLAY_SUBSET_TO_100").sum()),
    "winner_rows": int(pd.to_numeric(df["won"], errors="coerce").fillna(0).sum()),
    "status": "PRICING_REPLAY_SPINE_V3_2_NORMALISED_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

print("[PRICING_REPLAY_SPINE_V3_2_RECONSTRUCTED_NORMALISED] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print(summary.to_string(index=False))
print("")
print(race_audit["status"].value_counts().to_string())
