from __future__ import annotations

import os
from datetime import datetime

import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_SPEED_MAP = os.path.join(DATA, "edgeiq_sectional_speed_map_positions_v3.csv")

OUT_RACE = os.path.join(DATA, "edgeiq_pace_pressure_engine_v2.csv")
OUT_RUNNERS = os.path.join(DATA, "edgeiq_pace_pressure_engine_v2_runners.csv")
OUT_AUDIT = os.path.join(DATA, "edgeiq_pace_pressure_engine_v2_audit.csv")


def safe_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def clean_band(x):
    s = safe_str(x).upper()

    if "LEADER" in s:
        return "LEADER"

    if "ON" in s and "PACE" in s:
        return "ON_PACE"

    if "PACE" in s and "LEADER" not in s:
        return "ON_PACE"

    if "MID" in s:
        return "MIDFIELD"

    if "BACK" in s:
        return "BACKMARKER"

    if "SETTLE" in s:
        return "MIDFIELD"

    return "UNKNOWN"


def pressure_band(score):
    try:
        s = float(score)
    except Exception:
        return "UNKNOWN"

    if s >= 27:
        return "EXTREME"
    if s >= 19:
        return "FAST"
    if s >= 11:
        return "MODERATE"
    return "SLOW"


def pressure_shape(score, leaders, on_pace, backmarkers):
    try:
        s = float(score)
    except Exception:
        return "UNKNOWN"

    if leaders >= 4 or s >= 27:
        return "PRESSURE_COLLAPSE_RISK"

    if leaders >= 2 and on_pace >= 4:
        return "FAST_CONTESTED"

    if leaders <= 1 and on_pace <= 2:
        return "LOW_PRESSURE"

    if backmarkers >= leaders + on_pace:
        return "BACKMARKER_HEAVY"

    return "BALANCED"


def main():
    if not os.path.exists(IN_SPEED_MAP):
        raise FileNotFoundError(IN_SPEED_MAP)

    sm = pd.read_csv(IN_SPEED_MAP, low_memory=False)

    required = ["race_date", "track", "race_no", "race_key", "horse", "horse_key"]
    missing = [c for c in required if c not in sm.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    sm["pace_input_band_v2"] = ""

    for col in [
        "projected_settling_band",
        "tactical_position_group",
        "run_style",
        "sectional_speed_bucket",
        "tactical_speed_bucket",
        "pace_profile",
    ]:
        if col in sm.columns:
            sm["pace_input_band_v2"] = sm["pace_input_band_v2"].where(
                sm["pace_input_band_v2"].astype(str).str.len() > 0,
                sm[col].astype(str),
            )

    sm["pace_role_v2"] = sm["pace_input_band_v2"].map(clean_band)

    sm["leader_flag_v2"] = (sm["pace_role_v2"] == "LEADER").astype(int)
    sm["on_pace_flag_v2"] = (sm["pace_role_v2"] == "ON_PACE").astype(int)
    sm["midfield_flag_v2"] = (sm["pace_role_v2"] == "MIDFIELD").astype(int)
    sm["backmarker_flag_v2"] = (sm["pace_role_v2"] == "BACKMARKER").astype(int)
    sm["unknown_pace_flag_v2"] = (sm["pace_role_v2"] == "UNKNOWN").astype(int)

    sm["runner_pressure_points_v2"] = (
        sm["leader_flag_v2"] * 4
        + sm["on_pace_flag_v2"] * 2
        + sm["midfield_flag_v2"] * 1
    )

    grouped = []

    for race_key, g in sm.groupby("race_key", dropna=False):
        leaders = int(g["leader_flag_v2"].sum())
        on_pace = int(g["on_pace_flag_v2"].sum())
        midfield = int(g["midfield_flag_v2"].sum())
        backmarkers = int(g["backmarker_flag_v2"].sum())
        unknown = int(g["unknown_pace_flag_v2"].sum())
        runners = int(len(g))

        pressure_score = int(g["runner_pressure_points_v2"].sum())
        pressure_per_runner = round(pressure_score / runners, 3) if runners else 0
        early_speed_count = leaders + on_pace
        early_speed_ratio = round(early_speed_count / runners, 4) if runners else 0
        known_pace_ratio = round((runners - unknown) / runners, 4) if runners else 0

        first = g.iloc[0]

        grouped.append({
            "built_at": datetime.now().isoformat(timespec="seconds"),
            "race_date": safe_str(first.get("race_date")),
            "track": safe_str(first.get("track")),
            "race_no": safe_str(first.get("race_no")),
            "race_key": safe_str(race_key),
            "field_size": runners,
            "leaders": leaders,
            "on_pace": on_pace,
            "midfield": midfield,
            "backmarkers": backmarkers,
            "unknown_pace": unknown,
            "early_speed_count": early_speed_count,
            "early_speed_ratio": early_speed_ratio,
            "known_pace_ratio": known_pace_ratio,
            "pressure_score_v2": pressure_score,
            "pressure_per_runner_v2": pressure_per_runner,
            "pressure_band_v2": pressure_band(pressure_score),
            "pressure_shape_v2": pressure_shape(pressure_score, leaders, on_pace, backmarkers),
        })

    race = pd.DataFrame(grouped)

    sm = sm.merge(
        race[
            [
                "race_key",
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
                "pressure_per_runner_v2",
                "pressure_band_v2",
                "pressure_shape_v2",
            ]
        ],
        on="race_key",
        how="left",
    )

    runner_cols = [
        "race_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "barrier",
        "runner_no",
        "pace_input_band_v2",
        "pace_role_v2",
        "runner_pressure_points_v2",
        "field_size",
        "leaders",
        "on_pace",
        "midfield",
        "backmarkers",
        "unknown_pace",
        "pressure_score_v2",
        "pressure_per_runner_v2",
        "pressure_band_v2",
        "pressure_shape_v2",
        "speed_map_source",
        "dna_confidence",
        "bucket_confidence",
    ]

    runner_cols = [c for c in runner_cols if c in sm.columns]

    race.to_csv(OUT_RACE, index=False)
    sm[runner_cols].to_csv(OUT_RUNNERS, index=False)

    audit = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_SPEED_MAP},
        {"metric": "runner_rows", "value": len(sm)},
        {"metric": "races", "value": race["race_key"].nunique()},
        {"metric": "slow_races", "value": int((race["pressure_band_v2"] == "SLOW").sum())},
        {"metric": "moderate_races", "value": int((race["pressure_band_v2"] == "MODERATE").sum())},
        {"metric": "fast_races", "value": int((race["pressure_band_v2"] == "FAST").sum())},
        {"metric": "extreme_races", "value": int((race["pressure_band_v2"] == "EXTREME").sum())},
        {"metric": "avg_pressure_score", "value": round(float(race["pressure_score_v2"].mean()), 3) if len(race) else 0},
        {"metric": "avg_known_pace_ratio", "value": round(float(race["known_pace_ratio"].mean()), 4) if len(race) else 0},
    ])

    audit.to_csv(OUT_AUDIT, index=False)

    print("[PACE_PRESSURE_ENGINE_V2] COMPLETE")
    print(f"wrote={OUT_RACE}")
    print(f"wrote={OUT_RUNNERS}")
    print(f"wrote={OUT_AUDIT}")


if __name__ == "__main__":
    main()
