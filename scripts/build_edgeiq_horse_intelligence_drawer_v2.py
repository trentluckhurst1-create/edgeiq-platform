from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"
PROFILE = DATA / "edgeiq_live_horse_profile_current.csv"
SECTIONAL = DATA / "edgeiq_live_sectional_intelligence_v1.csv"
RUNNER_INTEL = DATA / "edgeiq_runner_intelligence_v1.csv"
TRACK_INTEL = DATA / "edgeiq_live_track_intelligence_v1.csv"

OUT = DATA / "edgeiq_horse_intelligence_drawer_v2.csv"
SUMMARY = DATA / "edgeiq_horse_intelligence_drawer_v2_summary.csv"

def key(x):
    s = str(x or "").strip().upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def num(x):
    return pd.to_numeric(x, errors="coerce")

def pick_col(df, options):
    for c in options:
        if c in df.columns:
            return c
    return ""

def main():
    board = pd.read_csv(BOARD, dtype=str, keep_default_na=False, low_memory=False)
    profile = pd.read_csv(PROFILE, dtype=str, keep_default_na=False, low_memory=False)

    board["join_key_v2"] = board["horse"].map(key)
    profile["join_key_v2"] = profile["horse"].map(key)

    out = board.merge(
        profile,
        on="join_key_v2",
        how="left",
        suffixes=("", "_profilefeed")
    )

    if SECTIONAL.exists():
        sec = pd.read_csv(SECTIONAL, dtype=str, keep_default_na=False, low_memory=False)
        sec_horse_col = pick_col(sec, ["horse", "horse_name", "runner", "runner_name"])
        if sec_horse_col:
            sec["join_key_v2"] = sec[sec_horse_col].map(key)
            sec_keep = ["join_key_v2"] + [c for c in [
                "sectional_weapon_score",
                "late_power_index",
                "sectional_strength_rating",
                "sectional_strength_band",
                "sectional_archetype",
                "projected_spd",
                "speed_profile",
                "sectional_confidence",
            ] if c in sec.columns]
            out = out.merge(sec[sec_keep].drop_duplicates("join_key_v2"), on="join_key_v2", how="left", suffixes=("", "_sectional"))

    if RUNNER_INTEL.exists():
        ri = pd.read_csv(RUNNER_INTEL, dtype=str, keep_default_na=False, low_memory=False)
        ri_horse_col = pick_col(ri, ["horse", "horse_name", "runner", "runner_name"])
        if ri_horse_col:
            ri["join_key_v2"] = ri[ri_horse_col].map(key)
            ri_keep = ["join_key_v2"] + [c for c in [
                "run_style",
                "settling_band",
                "archetype",
                "runner_intelligence_score",
                "projected_spd",
                "late_power_index",
                "sectional_weapon_score",
            ] if c in ri.columns]
            out = out.merge(ri[ri_keep].drop_duplicates("join_key_v2"), on="join_key_v2", how="left", suffixes=("", "_runnerintel"))

    if TRACK_INTEL.exists():
        ti = pd.read_csv(TRACK_INTEL, dtype=str, keep_default_na=False, low_memory=False)
        ti_horse_col = pick_col(ti, ["horse", "horse_name", "runner", "runner_name"])
        if ti_horse_col:
            ti["join_key_v2"] = ti[ti_horse_col].map(key)
            ti_keep = ["join_key_v2"] + [c for c in [
                "track_fit_score",
                "track_fit_band",
                "condition_fit_score",
                "condition_fit_band",
                "distance_fit_score",
                "distance_fit_band",
                "track_intelligence_band",
                "track_intelligence_score",
            ] if c in ti.columns]
            out = out.merge(ti[ti_keep].drop_duplicates("join_key_v2"), on="join_key_v2", how="left", suffixes=("", "_trackintel"))

    out["drawer_profile_summary"] = (
        "Career "
        + out.get("career_starts_profile", "").astype(str)
        + ":"
        + out.get("career_wins_profile", "").astype(str)
        + "-"
        + out.get("career_places_profile", "").astype(str)
        + " | Last 5 "
        + out.get("last_5_form_profile", "").astype(str)
        + " | Quality "
        + out.get("profile_quality", "").astype(str)
    )

    out["drawer_rating_summary"] = (
        "Projection "
        + out.get("projected_rating_V6_1_RESEARCH", "").astype(str)
        + " / Gap "
        + out.get("projection_gap_V6_1_RESEARCH", "").astype(str)
        + " / Band "
        + out.get("projection_band_V6_1_RESEARCH", "").astype(str)
    )

    out["drawer_market_summary"] = (
        "Live "
        + out.get("live_price", "").astype(str)
        + " | Fair "
        + out.get("fair_price", "").astype(str)
        + " | Edge "
        + out.get("edge_pct", "").astype(str)
        + "% | Decision "
        + out.get("execution_action_governed", "").astype(str)
    )

    out["drawer_data_warning"] = ""
    out.loc[out.get("profile_quality", "").astype(str).eq("NO_PROFILE"), "drawer_data_warning"] = "NO_PROFILE_AVAILABLE"
    out.loc[out.get("profile_quality", "").astype(str).eq("BACKFILLED_ONLY_LOW_CONFIDENCE"), "drawer_data_warning"] = "BACKFILLED_ONLY_LOW_CONFIDENCE"

    out["built_at_drawer_v2"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    out.to_csv(OUT, index=False)

    summary = pd.DataFrame([
        {"metric": "status", "value": "HORSE_INTELLIGENCE_DRAWER_V2_BUILT"},
        {"metric": "rows", "value": len(out)},
        {"metric": "profile_matched_rows", "value": int(out.get("profile_match_status", "").astype(str).eq("MATCHED_PROFILE").sum())},
        {"metric": "high_quality_profiles", "value": int(out.get("profile_quality", "").astype(str).eq("HIGH").sum())},
        {"metric": "medium_quality_profiles", "value": int(out.get("profile_quality", "").astype(str).eq("MEDIUM").sum())},
        {"metric": "low_quality_profiles", "value": int(out.get("profile_quality", "").astype(str).eq("LOW").sum())},
        {"metric": "no_profile_rows", "value": int(out.get("profile_quality", "").astype(str).eq("NO_PROFILE").sum())},
    ])
    summary.to_csv(SUMMARY, index=False)

    print("[HORSE_INTELLIGENCE_DRAWER_V2] COMPLETE")
    print(summary.to_string(index=False))
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
