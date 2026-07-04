from __future__ import annotations

import os
from datetime import datetime

import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_FILE = os.path.join(DATA, "edgeiq_race_reliability_independence_audit_v1.csv")

OUT = os.path.join(DATA, "edgeiq_environment_score_v1.csv")
OUT_AUDIT = os.path.join(DATA, "edgeiq_environment_score_v1_audit.csv")


def to_bool(x):
    if pd.isna(x):
        return False
    return str(x).strip().lower() in {"true", "1", "yes", "y"}


def band(score):
    if score >= 8:
        return "ELITE"
    if score >= 6:
        return "POSITIVE"
    if score >= 4:
        return "NEUTRAL"
    if score >= 2:
        return "NEGATIVE"
    return "POOR"


def main():
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(IN_FILE)

    df = pd.read_csv(IN_FILE, low_memory=False)

    if "lone_leader_bool" in df.columns:
        df["lone_leader_bool"] = df["lone_leader_bool"].map(to_bool)
    else:
        df["lone_leader_bool"] = False

    reliability = df.get("race_reliability_band_v1", "").astype(str).str.upper()
    pace = df.get("pace_advantage_band_v1", "").astype(str).str.upper()
    strength = df.get("race_strength_band", "").astype(str).str.upper()

    score = pd.Series(0, index=df.index, dtype="int64")
    reasons = [[] for _ in range(len(df))]

    def add_points(mask, points, label):
        score.loc[mask] += points
        for idx in df.index[mask].tolist():
            reasons[idx].append(label)

    add_points(reliability.eq("ELITE"), 3, "Elite Race Reliability")
    add_points(reliability.eq("POSITIVE"), 1, "Positive Race Reliability")
    add_points(df["lone_leader_bool"], 4, "Lone Leader")
    add_points(pace.eq("ELITE"), 2, "Elite Pace")
    add_points(pace.eq("POSITIVE"), 1, "Positive Pace")
    add_points(strength.eq("VERY_WEAK"), 2, "Very Weak Competition")
    add_points(strength.eq("WEAK"), 1, "Weak Competition")

    df["environment_score_v1"] = score
    df["environment_band_v1"] = df["environment_score_v1"].map(band)
    df["environment_reason_v1"] = [
        " + ".join(r) if r else "No positive environment edge"
        for r in reasons
    ]

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
        "score_share_of_race",
        "score_share_band_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "field_size",
        "field_size_bucket_v1",
        "edge_proxy_pct",
        "accepted_signal_v4",
        "won",
        "rank1_won",
        "placed",
        "rank1_placed",
        "finish_position",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "pace_advantage_band_v1",
        "pace_advantage_score_v1",
        "pace_role_v1",
        "race_shape_density_v1",
        "lone_leader_bool",
        "race_strength_band",
        "field_strength_score",
        "field_strength_percentile",
        "environment_score_v1",
        "environment_band_v1",
        "environment_reason_v1",
    ]

    wanted = [c for c in wanted if c in df.columns]
    df[wanted].to_csv(OUT, index=False)

    audit = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_FILE},
        {"metric": "rows", "value": len(df)},
        {"metric": "columns_written", "value": len(wanted)},
        {"metric": "has_won", "value": "won" in df.columns},
        {"metric": "has_rank1_won", "value": "rank1_won" in df.columns},
        {"metric": "has_finish_position", "value": "finish_position" in df.columns},
        {"metric": "poor", "value": int((df["environment_band_v1"] == "POOR").sum())},
        {"metric": "negative", "value": int((df["environment_band_v1"] == "NEGATIVE").sum())},
        {"metric": "neutral", "value": int((df["environment_band_v1"] == "NEUTRAL").sum())},
        {"metric": "positive", "value": int((df["environment_band_v1"] == "POSITIVE").sum())},
        {"metric": "elite", "value": int((df["environment_band_v1"] == "ELITE").sum())},
        {"metric": "avg_environment_score", "value": round(float(df["environment_score_v1"].mean()), 3)},
    ])

    audit.to_csv(OUT_AUDIT, index=False)

    print("[ENVIRONMENT_SCORE_V1] COMPLETE")
    print(f"wrote={OUT}")
    print(f"wrote={OUT_AUDIT}")


if __name__ == "__main__":
    main()
