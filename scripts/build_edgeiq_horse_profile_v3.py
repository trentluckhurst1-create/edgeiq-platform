from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_governed_v1.csv"
WAREHOUSE = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"
RATING = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
STYLE = DATA / "edgeiq_runner_style_profile_v1.csv"
SECTIONAL = DATA / "edgeiq_sectional_strength_v2.csv"

OUT_PROFILE = DATA / "edgeiq_horse_profile_v3.csv"
OUT_LIVE = DATA / "edgeiq_live_horse_profile_v3.csv"
OUT_SUMMARY = DATA / "edgeiq_live_horse_profile_v3_summary.csv"

def key(x):
    s = str(x or "").strip().upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def num(x):
    return pd.to_numeric(x, errors="coerce")

def finish_num(x):
    s = str(x or "").strip().upper()
    m = re.search(r"\d+", s)
    if m:
        return float(m.group(0))
    return np.nan

def pct(n, d):
    if d and d > 0:
        return round((n / d) * 100, 2)
    return ""

def main():
    now = datetime.now(timezone.utc)

    live = pd.read_csv(LIVE, dtype=str, keep_default_na=False, low_memory=False)
    wh = pd.read_csv(WAREHOUSE, dtype=str, keep_default_na=False, low_memory=False)
    rating = pd.read_csv(RATING, dtype=str, keep_default_na=False, low_memory=False)

    live["horse_key_join"] = live["horse"].map(key)
    wh["horse_key_join"] = wh["horseName"].map(key)
    rating["horse_key_join"] = rating["horse"].map(key)

    wh["run_date_dt"] = pd.to_datetime(wh.get("meeting_date", ""), errors="coerce")
    wh["finish_num"] = num(wh.get("finishPosition", ""))
    wh["is_win"] = wh["finish_num"].eq(1)
    wh["is_place"] = wh["finish_num"].between(1, 3, inclusive="both")
    wh["distance_num"] = num(wh.get("distance", "").astype(str).str.replace("m", "", regex=False))
    wh["track_condition_upper"] = wh.get("trackCondition", "").astype(str).str.upper()
    wh["is_wet"] = wh["track_condition_upper"].str.contains("SOFT|HEAVY", regex=True)
    wh["sp_num"] = num(wh.get("sp", "").astype(str).str.replace("$", "", regex=False))

    rating["race_date_dt"] = pd.to_datetime(rating.get("race_date", ""), errors="coerce")
    rating["rating_num"] = num(rating.get("performance_rating_v6_1_research", ""))
    rating["is_backfilled"] = rating.get("rating_v5_1_status", "").astype(str).str.upper().eq("BACKFILLED_POWER_RATING")

    horse_keys = sorted(set(live["horse_key_join"].dropna()) | set(wh["horse_key_join"].dropna()) | set(rating["horse_key_join"].dropna()))

    rows = []

    for hk in horse_keys:
        if not hk:
            continue

        live_rows = live[live["horse_key_join"].eq(hk)]
        c = wh[wh["horse_key_join"].eq(hk)].sort_values("run_date_dt", ascending=False)
        r = rating[rating["horse_key_join"].eq(hk)].sort_values("race_date_dt", ascending=False)

        display_horse = ""
        if len(live_rows):
            display_horse = live_rows.iloc[0].get("horse", "")
        elif len(c):
            display_horse = c.iloc[0].get("horseName", "")
        elif len(r):
            display_horse = r.iloc[0].get("horse", "")

        career_starts = len(c)
        career_wins = int(c["is_win"].sum()) if len(c) else 0
        career_places = int(c["is_place"].sum()) if len(c) else 0

        last5 = c.head(5)
        last5_form = "-".join([
            str(int(x)) if pd.notna(x) else "?"
            for x in last5["finish_num"].tolist()
        ])

        last_start = c["run_date_dt"].dropna().max() if len(c) else pd.NaT
        days_since = ""
        if pd.notna(last_start):
            days_since = (pd.Timestamp(now.date()) - pd.Timestamp(last_start.date())).days

        genuine_r = r[(r["rating_num"].notna()) & (~r["is_backfilled"])]
        all_r = r[r["rating_num"].notna()]
        backfilled_rows = int(r["is_backfilled"].sum()) if len(r) else 0
        genuine_rows = len(genuine_r)

        latest_v6_rating = ""
        avg_v6_rating_last_5 = ""
        peak_v6_rating = ""

        if len(genuine_r):
            latest_v6_rating = round(float(genuine_r.iloc[0]["rating_num"]), 2)
            avg_v6_rating_last_5 = round(float(genuine_r.head(5)["rating_num"].mean()), 2)
            peak_v6_rating = round(float(genuine_r["rating_num"].max()), 2)

        wet = c[c["is_wet"]]
        wet_starts = len(wet)
        wet_wins = int(wet["is_win"].sum()) if len(wet) else 0
        wet_places = int(wet["is_place"].sum()) if len(wet) else 0

        if career_starts >= 8:
            profile_quality = "HIGH"
        elif career_starts >= 3:
            profile_quality = "MEDIUM"
        elif career_starts >= 1:
            profile_quality = "LOW"
        elif genuine_rows >= 1:
            profile_quality = "RATING_ONLY"
        elif backfilled_rows >= 1:
            profile_quality = "BACKFILLED_ONLY_LOW_CONFIDENCE"
        else:
            profile_quality = "NO_PROFILE"

        rows.append({
            "horse": display_horse,
            "horse_key": hk,
            "career_starts_profile": career_starts,
            "career_wins_profile": career_wins,
            "career_places_profile": career_places,
            "career_win_pct_profile": pct(career_wins, career_starts),
            "career_place_pct_profile": pct(career_places, career_starts),
            "last_5_form_profile": last5_form,
            "last_start_date_profile": last_start.date().isoformat() if pd.notna(last_start) else "",
            "days_since_last_start_profile": days_since,
            "genuine_rating_rows_profile": genuine_rows,
            "backfilled_rating_rows_profile": backfilled_rows,
            "all_rating_rows_profile": len(all_r),
            "latest_v6_rating_profile": latest_v6_rating,
            "avg_v6_rating_last_5_profile": avg_v6_rating_last_5,
            "peak_v6_rating_profile": peak_v6_rating,
            "wet_starts_profile": wet_starts,
            "wet_wins_profile": wet_wins,
            "wet_places_profile": wet_places,
            "wet_win_pct_profile": pct(wet_wins, wet_starts),
            "wet_place_pct_profile": pct(wet_places, wet_starts),
            "profile_quality": profile_quality,
            "profile_source": "edgeiq_racingcom_results_warehouse_full_v1.csv + edgeiq_historical_performance_rating_v6_1_research.csv",
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

    live_profile = live.merge(
        profile,
        left_on="horse_key_join",
        right_on="horse_key",
        how="left",
        suffixes=("", "_profile")
    )

    live_profile["profile_match_status"] = np.where(
        live_profile["horse_key"].notna(),
        "MATCHED_PROFILE",
        "NO_PROFILE_MATCH"
    )

    live_profile.to_csv(OUT_LIVE, index=False)

    summary_rows = [
        {"metric":"status","value":"HORSE_PROFILE_V3_BUILT"},
        {"metric":"profile_rows","value":len(profile)},
        {"metric":"live_rows","value":len(live_profile)},
        {"metric":"live_matched_profiles","value":int(live_profile["profile_match_status"].eq("MATCHED_PROFILE").sum())},
        {"metric":"live_unmatched_profiles","value":int(live_profile["profile_match_status"].eq("NO_PROFILE_MATCH").sum())},
    ]

    for k, v in live_profile["profile_quality"].fillna("NO_PROFILE").value_counts().items():
        summary_rows.append({"metric":f"profile_quality_{k}","value":int(v)})

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_SUMMARY, index=False)

    print("[HORSE_PROFILE_V3] COMPLETE")
    print(summary.to_string(index=False))
    print(f"profile={OUT_PROFILE}")
    print(f"live_profile={OUT_LIVE}")
    print(f"summary={OUT_SUMMARY}")

if __name__ == "__main__":
    main()
