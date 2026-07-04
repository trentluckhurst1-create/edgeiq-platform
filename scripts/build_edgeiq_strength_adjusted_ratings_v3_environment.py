from __future__ import annotations

import os
from datetime import datetime

import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_ENV = os.path.join(DATA, "edgeiq_environment_score_v1.csv")

OUT = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v3_environment.csv")
OUT_AUDIT = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v3_environment_audit.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v3_environment_summary.csv")


def num(x):
    return pd.to_numeric(x, errors="coerce")


def env_adjustment(score):
    try:
        s = float(score)
    except Exception:
        return 0.0

    if s >= 7:
        return 2.5
    if s >= 5:
        return 2.0
    if s >= 3:
        return 1.0
    return 0.0


def reason(score, band, adj):
    if adj >= 2.5:
        return f"Elite environment boost ({band}, score {score})"
    if adj >= 2.0:
        return f"Strong environment boost ({band}, score {score})"
    if adj >= 1.0:
        return f"Positive environment boost ({band}, score {score})"
    return f"No environment rating boost ({band}, score {score})"


def band_v3(rating):
    try:
        r = float(rating)
    except Exception:
        return "UNKNOWN"

    if r >= 80:
        return "ELITE"
    if r >= 70:
        return "STRONG"
    if r >= 60:
        return "POSITIVE"
    if r >= 50:
        return "NEUTRAL"
    if r >= 40:
        return "WEAK"
    return "POOR"


def main():
    if not os.path.exists(IN_ENV):
        raise FileNotFoundError(IN_ENV)

    df = pd.read_csv(IN_ENV, low_memory=False)

    # Prefer an existing rating if one has been carried through.
    rating_candidates = [
        "strength_adjusted_rating_v2",
        "strength_adjusted_rating_v6",
        "confidence_adjusted_rating_v6",
        "runner_score",
        "runner_score_v1",
    ]

    rating_col = None
    for c in rating_candidates:
        if c in df.columns:
            rating_col = c
            break

    if rating_col is None:
        raise ValueError("No usable base rating column found in environment score file.")

    df["base_rating_for_v3_environment"] = num(df[rating_col])
    df["environment_score_num"] = num(df["environment_score_v1"]).fillna(0)
    df["environment_adjustment_v3"] = df["environment_score_num"].map(env_adjustment)

    df["strength_adjusted_rating_v3_environment"] = (
        df["base_rating_for_v3_environment"].fillna(0)
        + df["environment_adjustment_v3"]
    ).round(3)

    df["strength_adjusted_band_v3_environment"] = df["strength_adjusted_rating_v3_environment"].map(band_v3)

    df["strength_adjusted_reason_v3_environment"] = df.apply(
        lambda r: reason(
            r.get("environment_score_v1", ""),
            r.get("environment_band_v1", ""),
            r.get("environment_adjustment_v3", 0),
        ),
        axis=1,
    )

    wanted = [
        "meeting_date",
        "race_date",
        "track",
        "race_no",
        "horse",
        "race_join_key_fixed",
        "runner_join_key_fixed",
        "runner_rank",
        "runner_score",
        "base_rating_for_v3_environment",
        "score_share_of_race",
        "score_share_band_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "field_size",
        "field_size_bucket_v1",
        "edge_proxy_pct",
        "won",
        "placed",
        "finish_position",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "pace_advantage_band_v1",
        "pace_advantage_score_v1",
        "pace_role_v1",
        "race_shape_density_v1",
        "lone_leader_bool",
        "race_strength_band",
        "environment_score_v1",
        "environment_band_v1",
        "environment_reason_v1",
        "environment_adjustment_v3",
        "strength_adjusted_rating_v3_environment",
        "strength_adjusted_band_v3_environment",
        "strength_adjusted_reason_v3_environment",
    ]

    wanted = [c for c in wanted if c in df.columns]
    out = df[wanted].copy()
    out.to_csv(OUT, index=False)

    summary = (
        out.groupby(["environment_band_v1", "strength_adjusted_band_v3_environment"], dropna=False)
        .size()
        .reset_index(name="runners")
        .sort_values(["environment_band_v1", "strength_adjusted_band_v3_environment"])
    )
    summary.to_csv(OUT_SUMMARY, index=False)

    audit = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_ENV},
        {"metric": "base_rating_column_used", "value": rating_col},
        {"metric": "rows", "value": len(out)},
        {"metric": "avg_base_rating", "value": round(float(df["base_rating_for_v3_environment"].mean()), 3)},
        {"metric": "avg_environment_adjustment", "value": round(float(df["environment_adjustment_v3"].mean()), 3)},
        {"metric": "avg_v3_environment_rating", "value": round(float(df["strength_adjusted_rating_v3_environment"].mean()), 3)},
        {"metric": "boosted_rows", "value": int((df["environment_adjustment_v3"] > 0).sum())},
        {"metric": "boost_1pt_rows", "value": int((df["environment_adjustment_v3"] == 1.0).sum())},
        {"metric": "boost_2pt_rows", "value": int((df["environment_adjustment_v3"] == 2.0).sum())},
        {"metric": "boost_2_5pt_rows", "value": int((df["environment_adjustment_v3"] == 2.5).sum())},
    ])
    audit.to_csv(OUT_AUDIT, index=False)

    print("[STRENGTH_ADJUSTED_RATINGS_V3_ENVIRONMENT] COMPLETE")
    print(f"base_rating_column_used={rating_col}")
    print(f"wrote={OUT}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_AUDIT}")


if __name__ == "__main__":
    main()
