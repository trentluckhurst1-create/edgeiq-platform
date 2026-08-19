from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RATINGS = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
STYLE = DATA / "edgeiq_runner_style_profile_v1.csv"
SECTIONAL = DATA / "edgeiq_sectional_strength_v2.csv"
LIVE = DATA / "edgeiq_live_runner_board_governed_v1.csv"

OUT_PROFILE = DATA / "edgeiq_horse_profile_v1.csv"
OUT_LIVE = DATA / "edgeiq_live_horse_profile_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_live_horse_profile_v1_summary.csv"

def key(x):
    return re.sub(r"[^A-Z0-9]", "", re.sub(r"\([^)]*\)", "", str(x or "").upper()))

def num(s):
    return pd.to_numeric(s, errors="coerce")

def safe_rate(wins, starts):
    if starts and starts > 0:
        return round((wins / starts) * 100, 2)
    return ""

def main():
    ratings = pd.read_csv(RATINGS, dtype=str, keep_default_na=False, low_memory=False)
    ratings["horse_key"] = ratings["horse"].map(key)
    ratings["race_date_dt"] = pd.to_datetime(ratings["race_date"], errors="coerce")
    ratings["rating"] = num(ratings["performance_rating_v6_1_research"])
    ratings["finish_num"] = num(ratings["finish_position"])
    ratings["distance_num"] = num(ratings["distance"])
    ratings["is_win"] = ratings["finish_num"].eq(1)
    ratings["is_place"] = ratings["finish_num"].between(1, 3, inclusive="both")
    ratings["is_wet"] = ratings["condition_recovered"].astype(str).str.upper().str.contains("SOFT|HEAVY", regex=True)
    ratings["is_backfilled"] = ratings["rating_v5_1_status"].astype(str).str.upper().eq("BACKFILLED_POWER_RATING")
    ratings = ratings[ratings["horse_key"].ne("")].copy()

    rows = []
    now = datetime.now(timezone.utc)

    for hk, g in ratings.sort_values("race_date_dt", ascending=False).groupby("horse_key", dropna=False):
        g = g.copy()
        horse = g["horse"].dropna().astype(str).iloc[0]

        valid_rating_all = g[g["rating"].notna()].copy()
        valid_rating = valid_rating_all[~valid_rating_all["is_backfilled"]].copy()
        genuine = g[~g["is_backfilled"]].copy()
        last5 = valid_rating.head(5)
        last10 = valid_rating.head(10)

        starts = len(g)
        wins = int(g["is_win"].sum())
        places = int(g["is_place"].sum())
        backfilled_rows = int(g["is_backfilled"].sum())
        genuine_rows = int((~g["is_backfilled"]).sum())

        last_start = g["race_date_dt"].dropna().max()
        days_since = ""
        if pd.notna(last_start):
            days_since = (pd.Timestamp(now.date()) - pd.Timestamp(last_start.date())).days

        last_12_cutoff = pd.Timestamp(now.date()) - pd.Timedelta(days=365)
        starts_12m = int(g["race_date_dt"].ge(last_12_cutoff).sum())

        latest_rating = ""
        if len(valid_rating):
            latest_rating = round(float(valid_rating.iloc[0]["rating"]), 2)

        avg5 = round(float(last5["rating"].mean()), 2) if len(last5) else ""
        avg10 = round(float(last10["rating"].mean()), 2) if len(last10) else ""
        peak = round(float(valid_rating["rating"].max()), 2) if len(valid_rating) else ""

        wet = g[g["is_wet"]]
        wet_starts = len(wet)
        wet_wins = int(wet["is_win"].sum())
        wet_places = int(wet["is_place"].sum())

        data_quality = "LOW"
        if genuine_rows >= 5:
            data_quality = "HIGH"
        elif genuine_rows >= 2:
            data_quality = "MEDIUM"
        elif starts > 0:
            data_quality = "LOW_BACKFILL_AWARE"

        profile_quality = data_quality
        if starts == 0:
            profile_quality = "NO_PROFILE"
        elif backfilled_rows > 0 and genuine_rows == 0:
            profile_quality = "BACKFILLED_ONLY_LOW_CONFIDENCE"

        rows.append({
            "horse": horse,
            "horse_key": hk,
            "career_starts_profile": starts,
            "career_wins_profile": wins,
            "career_places_profile": places,
            "career_win_pct_profile": safe_rate(wins, starts),
            "career_place_pct_profile": safe_rate(places, starts),
            "genuine_rating_rows_profile": genuine_rows,
            "backfilled_rating_rows_profile": backfilled_rows,
            "last_start_date_profile": last_start.date().isoformat() if pd.notna(last_start) else "",
            "days_since_last_start_profile": days_since,
            "starts_last_12_months_profile": starts_12m,
            "latest_rating_profile": latest_rating,
            "avg_rating_last_5_profile": avg5,
            "avg_rating_last_10_profile": avg10,
            "peak_rating_profile": peak,
            "wet_starts_profile": wet_starts,
            "wet_wins_profile": wet_wins,
            "wet_places_profile": wet_places,
            "wet_win_pct_profile": safe_rate(wet_wins, wet_starts),
            "wet_place_pct_profile": safe_rate(wet_places, wet_starts),
            "profile_data_quality": data_quality,
            "profile_quality": profile_quality,
            "profile_rating_source": "GENUINE_ONLY" if len(valid_rating) else "NO_GENUINE_RATING_BACKFILLED_ONLY",
            "profile_source": "edgeiq_historical_performance_rating_v6_1_research.csv",
            "built_at_profile": now.isoformat(timespec="seconds"),
        })

    profile = pd.DataFrame(rows)

    if STYLE.exists():
        style = pd.read_csv(STYLE, dtype=str, keep_default_na=False, low_memory=False)
        style["horse_key"] = style["horse_key"].map(key)
        keep = [
            "horse_key","dominant_run_style","movement_profile","style_confidence",
            "leader_pct","onpace_pct","midfield_pct","backmarker_pct",
            "avg_pos800","avg_pos400","improver_pct","fader_pct"
        ]
        profile = profile.merge(style[[c for c in keep if c in style.columns]], on="horse_key", how="left")

    if SECTIONAL.exists():
        sec = pd.read_csv(SECTIONAL, dtype=str, keep_default_na=False, low_memory=False)
        sec["horse_key"] = sec["horse_key"].map(key)
        keep = [
            "horse_key","sectional_strength_rating","sectional_strength_band",
            "sectional_strength_confidence","sectional_archetype",
            "avg_early_speed","avg_mid_speed","avg_late_speed","avg_peak_speed",
            "strength_adjusted_late_speed","runs_with_sectionals"
        ]
        profile = profile.merge(sec[[c for c in keep if c in sec.columns]], on="horse_key", how="left")

    profile.to_csv(OUT_PROFILE, index=False)

    live = pd.read_csv(LIVE, dtype=str, keep_default_na=False, low_memory=False)
    live["horse_key_profile_join"] = live["horse"].map(key)

    live_profile = live.merge(
        profile,
        left_on="horse_key_profile_join",
        right_on="horse_key",
        how="left",
        suffixes=("", "_profile_master")
    )

    live_profile["profile_match_status"] = np.where(
        live_profile["career_starts_profile"].notna(),
        "MATCHED_PROFILE",
        "NO_PROFILE_MATCH"
    )

    live_profile.to_csv(OUT_LIVE, index=False)

    summary = pd.DataFrame([
        {"metric": "status", "value": "HORSE_PROFILE_V1_BUILT"},
        {"metric": "profile_rows", "value": len(profile)},
        {"metric": "live_rows", "value": len(live_profile)},
        {"metric": "live_matched_profiles", "value": int(live_profile["profile_match_status"].eq("MATCHED_PROFILE").sum())},
        {"metric": "live_unmatched_profiles", "value": int(live_profile["profile_match_status"].eq("NO_PROFILE_MATCH").sum())},
        {"metric": "profile_high_quality_live", "value": int(live_profile["profile_quality"].astype(str).eq("HIGH").sum())},
        {"metric": "profile_medium_quality_live", "value": int(live_profile["profile_quality"].astype(str).eq("MEDIUM").sum())},
        {"metric": "profile_backfilled_only_live", "value": int(live_profile["profile_quality"].astype(str).eq("BACKFILLED_ONLY_LOW_CONFIDENCE").sum())},
    ])
    summary.to_csv(OUT_SUMMARY, index=False)

    print("[HORSE_PROFILE_V1] COMPLETE")
    print(summary.to_string(index=False))
    print(f"profile={OUT_PROFILE}")
    print(f"live_profile={OUT_LIVE}")
    print(f"summary={OUT_SUMMARY}")

if __name__ == "__main__":
    main()
