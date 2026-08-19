from __future__ import annotations

import os
from datetime import datetime

import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_RUNNERS = os.path.join(DATA, "edgeiq_pace_pressure_engine_v2_runners.csv")
IN_RATINGS = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v6.csv")

OUT = os.path.join(DATA, "edgeiq_pace_advantage_engine_v1.csv")
OUT_AUDIT = os.path.join(DATA, "edgeiq_pace_advantage_engine_v1_audit.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_pace_advantage_engine_v1_summary.csv")


def safe_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def norm_key(x):
    return safe_str(x).upper().replace(" ", "").replace("'", "").replace("’", "").replace("-", "").replace("_", "")


def race_key_no_r(x):
    s = safe_str(x)
    if s.endswith("|R1") or "|R" in s:
        return s.replace("|R", "|")
    return s


def density_shape(row):
    try:
        density = float(row.get("early_speed_ratio", 0))
    except Exception:
        density = 0

    try:
        leaders = int(float(row.get("leaders", 0)))
    except Exception:
        leaders = 0

    if density >= 0.80 or leaders >= 5:
        return "PRESSURE_COLLAPSE"
    if density >= 0.60 or leaders >= 4:
        return "HIGH_PRESSURE"
    if density >= 0.40:
        return "FAST"
    if density >= 0.20:
        return "MODERATE"
    return "CRAWL"


MATRIX = {
    "LEADER": {
        "CRAWL": 25,
        "MODERATE": 10,
        "FAST": -5,
        "HIGH_PRESSURE": -20,
        "PRESSURE_COLLAPSE": -40,
    },
    "ON_PACE": {
        "CRAWL": 15,
        "MODERATE": 10,
        "FAST": 0,
        "HIGH_PRESSURE": -10,
        "PRESSURE_COLLAPSE": -25,
    },
    "MIDFIELD": {
        "CRAWL": -5,
        "MODERATE": 0,
        "FAST": 10,
        "HIGH_PRESSURE": 15,
        "PRESSURE_COLLAPSE": 20,
    },
    "BACKMARKER": {
        "CRAWL": -20,
        "MODERATE": -10,
        "FAST": 15,
        "HIGH_PRESSURE": 25,
        "PRESSURE_COLLAPSE": 40,
    },
    "UNKNOWN": {
        "CRAWL": 0,
        "MODERATE": 0,
        "FAST": 0,
        "HIGH_PRESSURE": 0,
        "PRESSURE_COLLAPSE": 0,
    },
}


def band(score):
    try:
        s = float(score)
    except Exception:
        return "UNKNOWN"

    if s >= 20:
        return "ELITE"
    if s >= 10:
        return "POSITIVE"
    if s <= -20:
        return "POOR"
    if s <= -10:
        return "NEGATIVE"
    return "NEUTRAL"


def reason(role, shape, score):
    if role == "UNKNOWN":
        return "UNKNOWN_RUN_STYLE"

    if score >= 20:
        return f"{role}_FAVOURED_BY_{shape}"
    if score >= 10:
        return f"{role}_SUITED_BY_{shape}"
    if score <= -20:
        return f"{role}_HEAVILY_HURT_BY_{shape}"
    if score <= -10:
        return f"{role}_HURT_BY_{shape}"
    return f"{role}_NEUTRAL_IN_{shape}"


def main():
    if not os.path.exists(IN_RUNNERS):
        raise FileNotFoundError(IN_RUNNERS)

    runners = pd.read_csv(IN_RUNNERS, low_memory=False)

    runners["horse_key_join"] = runners["horse_key"].map(norm_key)
    runners["race_key_join_clean"] = runners["race_key"].map(race_key_no_r)

    runners["race_shape_density_v1"] = runners.apply(density_shape, axis=1)

    runners["pace_role_v1"] = runners["pace_role_v2"].astype(str).str.upper().str.strip()
    runners["pace_advantage_raw_v1"] = runners.apply(
        lambda r: MATRIX.get(r["pace_role_v1"], MATRIX["UNKNOWN"]).get(r["race_shape_density_v1"], 0),
        axis=1,
    )

    runners["pace_advantage_score_v1"] = runners["pace_advantage_raw_v1"]
    runners["pace_advantage_band_v1"] = runners["pace_advantage_score_v1"].map(band)
    runners["pace_advantage_reason_v1"] = runners.apply(
        lambda r: reason(r["pace_role_v1"], r["race_shape_density_v1"], r["pace_advantage_score_v1"]),
        axis=1,
    )

    out = runners.copy()

    if os.path.exists(IN_RATINGS):
        ratings = pd.read_csv(IN_RATINGS, low_memory=False)

        ratings["horse_key_join"] = ratings["horse_key"].map(norm_key)
        ratings["race_key_join_clean"] = ratings["race_key_join"].map(race_key_no_r)

        keep = [
            "race_key_join_clean",
            "horse_key_join",
            "strength_adjusted_rating_v6",
            "confidence_adjusted_rating_v6",
            "strength_rating_band_v6",
            "projection_status_v6",
            "governance_band_v7_2",
            "predictability_score_v1",
            "predictability_band_v1",
            "sectional_strength_rating",
            "sectional_strength_band",
            "live_race_strength_score_v3",
            "live_race_strength_band_v3",
        ]

        keep = [c for c in keep if c in ratings.columns]

        out = out.merge(
            ratings[keep].drop_duplicates(["race_key_join_clean", "horse_key_join"]),
            on=["race_key_join_clean", "horse_key_join"],
            how="left",
        )

    out["pace_adjustment_rating_points_v1"] = (out["pace_advantage_score_v1"] / 5.0).round(3)

    if "strength_adjusted_rating_v6" in out.columns:
        out["strength_adjusted_rating_v7_pace_preview"] = (
            pd.to_numeric(out["strength_adjusted_rating_v6"], errors="coerce")
            + out["pace_adjustment_rating_points_v1"]
        ).round(3)

    if "confidence_adjusted_rating_v6" in out.columns:
        out["confidence_adjusted_rating_v7_pace_preview"] = (
            pd.to_numeric(out["confidence_adjusted_rating_v6"], errors="coerce")
            + out["pace_adjustment_rating_points_v1"]
        ).round(3)

    wanted = [
        "race_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "barrier",
        "runner_no",
        "pace_role_v1",
        "race_shape_density_v1",
        "pace_advantage_score_v1",
        "pace_advantage_band_v1",
        "pace_advantage_reason_v1",
        "pace_adjustment_rating_points_v1",
        "strength_adjusted_rating_v6",
        "strength_adjusted_rating_v7_pace_preview",
        "confidence_adjusted_rating_v6",
        "confidence_adjusted_rating_v7_pace_preview",
        "strength_rating_band_v6",
        "projection_status_v6",
        "governance_band_v7_2",
        "predictability_score_v1",
        "predictability_band_v1",
        "sectional_strength_rating",
        "sectional_strength_band",
        "live_race_strength_score_v3",
        "live_race_strength_band_v3",
        "field_size",
        "leaders",
        "on_pace",
        "midfield",
        "backmarkers",
        "unknown_pace",
        "early_speed_count",
        "early_speed_ratio",
        "known_pace_ratio",
        "pressure_score_v2",
        "pressure_band_v2",
        "pressure_shape_v2",
        "speed_map_source",
        "dna_confidence",
        "bucket_confidence",
    ]

    wanted = [c for c in wanted if c in out.columns]
    out[wanted].to_csv(OUT, index=False)

    summary = (
        out.groupby(["race_shape_density_v1", "pace_role_v1", "pace_advantage_band_v1"], dropna=False)
        .size()
        .reset_index(name="runners")
        .sort_values(["race_shape_density_v1", "pace_role_v1", "pace_advantage_band_v1"])
    )
    summary.to_csv(OUT_SUMMARY, index=False)

    audit = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "runner_rows", "value": len(out)},
        {"metric": "races", "value": out["race_key"].nunique()},
        {"metric": "elite_advantage", "value": int((out["pace_advantage_band_v1"] == "ELITE").sum())},
        {"metric": "positive_advantage", "value": int((out["pace_advantage_band_v1"] == "POSITIVE").sum())},
        {"metric": "neutral_advantage", "value": int((out["pace_advantage_band_v1"] == "NEUTRAL").sum())},
        {"metric": "negative_advantage", "value": int((out["pace_advantage_band_v1"] == "NEGATIVE").sum())},
        {"metric": "poor_advantage", "value": int((out["pace_advantage_band_v1"] == "POOR").sum())},
        {"metric": "avg_pace_advantage_score", "value": round(float(out["pace_advantage_score_v1"].mean()), 3)},
    ])
    audit.to_csv(OUT_AUDIT, index=False)

    print("[PACE_ADVANTAGE_ENGINE_V1] COMPLETE")
    print(f"wrote={OUT}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_AUDIT}")


if __name__ == "__main__":
    main()
