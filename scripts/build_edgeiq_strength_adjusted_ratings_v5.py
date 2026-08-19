import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V4 = DATA / "edgeiq_strength_adjusted_ratings_v4.csv"
PROFILES = DATA / "edgeiq_horse_results_strength_profile_v3.csv"
RACE_STRENGTH = DATA / "edgeiq_live_race_strength_v3.csv"

OUT = DATA / "edgeiq_strength_adjusted_ratings_v5.csv"
AUDIT = DATA / "edgeiq_strength_adjusted_ratings_v5_audit.csv"

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def norm_track(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = s.replace("BET365 ", "")
    s = s.replace("LADBROKES ", "")
    s = s.replace("SPORTSBET ", "")
    s = s.replace("SPORTSBET-", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def n(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index)

def band(score):
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 75:
        return "ELITE"
    if score >= 65:
        return "STRONG"
    if score >= 55:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 35:
        return "WEAK"
    return "POOR"

def main():
    for f in [V4, PROFILES, RACE_STRENGTH]:
        if not f.exists():
            raise FileNotFoundError(f"Missing required file: {f}")

    v4 = pd.read_csv(V4)
    profiles = pd.read_csv(PROFILES)
    races = pd.read_csv(RACE_STRENGTH)

    v4["horse_key_v5"] = v4["horse"].map(canon)
    profiles["horse_key_v5"] = profiles["horse_key"].astype(str)
    v4["track_norm_v5"] = v4["track"].map(norm_track)
    races["track_norm_v5"] = races["track"].map(norm_track)

    v4["race_no_int_v5"] = pd.to_numeric(v4["race_no"], errors="coerce").astype("Int64")
    races["race_no_int_v5"] = pd.to_numeric(races["race_no"], errors="coerce").astype("Int64")

    out = v4.merge(
        profiles[[
            "horse_key_v5",
            "starts",
            "wins",
            "places",
            "win_rate",
            "place_rate",
            "avg_finish_pct",
            "recent_avg_finish_pct",
            "horse_results_strength_v3",
            "results_reliability_v3",
        ]],
        on="horse_key_v5",
        how="left"
    )

    out = out.merge(
        races[[
            "track_norm_v5",
            "race_no_int_v5",
            "field_size_v3",
            "profiled_runners_v3",
            "profile_coverage_v3",
            "live_race_strength_score_v3",
            "live_race_strength_band_v3",
        ]],
        on=["track_norm_v5", "race_no_int_v5"],
        how="left"
    )

    out["strength_adjusted_rating_v4"] = n(out, "strength_adjusted_rating_v4")
    out["horse_results_strength_v3"] = n(out, "horse_results_strength_v3")
    out["live_race_strength_score_v3"] = n(out, "live_race_strength_score_v3")

    base = out["strength_adjusted_rating_v4"]
    horse_result = out["horse_results_strength_v3"]
    race_strength = out["live_race_strength_score_v3"]

    # V5: blend old rating with actual historical performance profile and race strength context.
    out["strength_adjusted_rating_v5"] = (
        0.56 * base.fillna(35) +
        0.34 * horse_result.fillna(28) +
        0.10 * race_strength.fillna(45)
    ).clip(0, 100).round(3)

    out["v5_minus_v4"] = (out["strength_adjusted_rating_v5"] - base).round(3)

    out["strength_rating_band_v5"] = out["strength_adjusted_rating_v5"].apply(band)

    out["strength_rating_reason_v5"] = (
        "v4=" + base.round(2).astype(str) +
        " | horse_results_v3=" + horse_result.round(2).astype(str) +
        " | race_strength_v3=" + race_strength.round(2).astype(str) +
        " | reliability=" + out["results_reliability_v3"].astype(str) +
        " | race_band=" + out["live_race_strength_band_v3"].astype(str)
    )

    out.to_csv(OUT, index=False)

    audit = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "rows", "value": len(out)},
        {"metric": "matched_horse_result_profiles", "value": int(out["horse_results_strength_v3"].notna().sum())},
        {"metric": "matched_race_strength_v3", "value": int(out["live_race_strength_score_v3"].notna().sum())},
        {"metric": "avg_v4", "value": round(base.mean(), 3)},
        {"metric": "avg_horse_results_strength_v3", "value": round(horse_result.mean(), 3)},
        {"metric": "avg_race_strength_v3", "value": round(race_strength.mean(), 3)},
        {"metric": "avg_v5", "value": round(out["strength_adjusted_rating_v5"].mean(), 3)},
        {"metric": "elite_v5", "value": int((out["strength_rating_band_v5"] == "ELITE").sum())},
        {"metric": "strong_v5", "value": int((out["strength_rating_band_v5"] == "STRONG").sum())},
        {"metric": "positive_v5", "value": int((out["strength_rating_band_v5"] == "POSITIVE").sum())},
        {"metric": "neutral_v5", "value": int((out["strength_rating_band_v5"] == "NEUTRAL").sum())},
        {"metric": "weak_v5", "value": int((out["strength_rating_band_v5"] == "WEAK").sum())},
        {"metric": "poor_v5", "value": int((out["strength_rating_band_v5"] == "POOR").sum())},
    ])
    audit.to_csv(AUDIT, index=False)

    print("[STRENGTH_ADJUSTED_RATINGS_V5] COMPLETE")
    print(f"rows={len(out)}")
    print(f"matched_horse_profiles={int(out['horse_results_strength_v3'].notna().sum())}")
    print(f"matched_race_strength={int(out['live_race_strength_score_v3'].notna().sum())}")
    print(f"avg_v5={round(out['strength_adjusted_rating_v5'].mean(), 3)}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
