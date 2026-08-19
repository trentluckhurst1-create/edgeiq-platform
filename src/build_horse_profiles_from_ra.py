from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model")

INPUT_RUNS = BASE_DIR / "outputs" / "ra_careers" / "ra_horse_runs.csv"
OUT_PROFILES = BASE_DIR / "outputs" / "ra_careers" / "ra_horse_profiles.csv"


def clean_text(x: Any) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip()


def to_float(x: Any):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def preferred_distance(distances: pd.Series) -> float:
    vals = pd.to_numeric(distances, errors="coerce").dropna()
    if vals.empty:
        return np.nan
    return float(vals.median())


def most_common_value(series: pd.Series) -> str:
    s = series.dropna().astype(str).str.strip()
    s = s[s != ""]
    if s.empty:
        return ""
    return s.value_counts().idxmax()


def calc_consistency_score(finishes: pd.Series) -> float:
    vals = pd.to_numeric(finishes, errors="coerce").dropna()
    if len(vals) < 2:
        return np.nan
    # lower std = more consistent
    return float(vals.std())


def calc_place_rate(finishes: pd.Series) -> float:
    vals = pd.to_numeric(finishes, errors="coerce").dropna()
    if vals.empty:
        return np.nan
    return float((vals <= 3).mean())


def calc_win_rate(finishes: pd.Series) -> float:
    vals = pd.to_numeric(finishes, errors="coerce").dropna()
    if vals.empty:
        return np.nan
    return float((vals == 1).mean())


def main():
    print("=== BUILD HORSE PROFILES FROM RA ===")
    print(f"Input:  {INPUT_RUNS}")

    if not INPUT_RUNS.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_RUNS}")

    df = pd.read_csv(INPUT_RUNS)

    if df.empty:
        raise ValueError("ra_horse_runs.csv is empty")

    # clean columns
    for col in ["horse", "run_type", "track", "race_class", "track_condition"]:
        if col in df.columns:
            df[col] = df[col].map(clean_text)

    for col in ["distance", "finish_pos", "field_size", "margin", "weight", "barrier", "sp"]:
        if col in df.columns:
            df[col] = df[col].map(to_float)

    # focus on actual races for main profile metrics
    race_df = df[df["run_type"].str.lower() == "race"].copy()
    trial_df = df[df["run_type"].str.lower() == "trial"].copy()
    jumpout_df = df[df["run_type"].str.lower() == "jumpout"].copy()

    profile_rows = []

    for horse, g_all in df.groupby("horse", dropna=False):
        g_race = race_df[race_df["horse"] == horse]
        g_trial = trial_df[trial_df["horse"] == horse]
        g_jump = jumpout_df[jumpout_df["horse"] == horse]

        finishes = g_race["finish_pos"] if "finish_pos" in g_race.columns else pd.Series(dtype=float)
        distances = g_race["distance"] if "distance" in g_race.columns else pd.Series(dtype=float)

        profile = {
            "horse": horse,

            # volume
            "total_runs_all": len(g_all),
            "total_races": len(g_race),
            "total_trials": len(g_trial),
            "total_jumpouts": len(g_jump),

            # result quality
            "wins": int((pd.to_numeric(finishes, errors="coerce") == 1).sum()) if not g_race.empty else 0,
            "seconds": int((pd.to_numeric(finishes, errors="coerce") == 2).sum()) if not g_race.empty else 0,
            "thirds": int((pd.to_numeric(finishes, errors="coerce") == 3).sum()) if not g_race.empty else 0,
            "places": int((pd.to_numeric(finishes, errors="coerce") <= 3).sum()) if not g_race.empty else 0,

            "win_rate": calc_win_rate(finishes),
            "place_rate": calc_place_rate(finishes),
            "avg_finish_pos": float(pd.to_numeric(finishes, errors="coerce").mean()) if not g_race.empty else np.nan,
            "consistency_score": calc_consistency_score(finishes),

            # distance profile
            "min_distance": float(pd.to_numeric(distances, errors="coerce").min()) if not g_race.empty else np.nan,
            "max_distance": float(pd.to_numeric(distances, errors="coerce").max()) if not g_race.empty else np.nan,
            "preferred_distance": preferred_distance(distances),

            # race conditions
            "preferred_track_condition": most_common_value(g_race["track_condition"]) if "track_condition" in g_race.columns else "",
            "preferred_track": most_common_value(g_race["track"]) if "track" in g_race.columns else "",
            "preferred_race_class": most_common_value(g_race["race_class"]) if "race_class" in g_race.columns else "",

            # market
            "avg_sp": float(pd.to_numeric(g_race["sp"], errors="coerce").dropna().mean()) if "sp" in g_race.columns and not g_race.empty else np.nan,
            "min_sp": float(pd.to_numeric(g_race["sp"], errors="coerce").dropna().min()) if "sp" in g_race.columns and not g_race.empty and pd.to_numeric(g_race["sp"], errors="coerce").dropna().size > 0 else np.nan,
            "max_sp": float(pd.to_numeric(g_race["sp"], errors="coerce").dropna().max()) if "sp" in g_race.columns and not g_race.empty and pd.to_numeric(g_race["sp"], errors="coerce").dropna().size > 0 else np.nan,

            # misc
            "avg_margin": float(pd.to_numeric(g_race["margin"], errors="coerce").mean()) if "margin" in g_race.columns and not g_race.empty else np.nan,
            "avg_barrier": float(pd.to_numeric(g_race["barrier"], errors="coerce").mean()) if "barrier" in g_race.columns and not g_race.empty else np.nan,
            "avg_weight": float(pd.to_numeric(g_race["weight"], errors="coerce").mean()) if "weight" in g_race.columns and not g_race.empty else np.nan,
        }

        profile_rows.append(profile)

    out = pd.DataFrame(profile_rows)

    OUT_PROFILES.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PROFILES, index=False)

    print(f"✅ Saved: {OUT_PROFILES}")
    print(f"Horses profiled: {len(out):,}")
    print("\nSample:")
    print(out.head(20).to_string(index=False))


if __name__ == "__main__":
    main()