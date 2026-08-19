from pathlib import Path
import json
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

REPLAY_FILE = DATA / "edgeiq_fair_price_v8_interaction_filter_replay_v1.csv"
RELIABILITY_FILE = DATA / "edgeiq_race_reliability_v1.csv"
SECTIONAL_FILE = DATA / "edgeiq_sectional_profiles_v2.csv"

OUT_CSV = DATA / "edgeiq_bet_quality_engine_v1_1.csv"
OUT_SUMMARY = DATA / "edgeiq_bet_quality_engine_v1_1_summary.csv"
OUT_GRADE = DATA / "edgeiq_bet_quality_engine_v1_1_by_grade.csv"
OUT_SCORE = DATA / "edgeiq_bet_quality_engine_v1_1_by_score_band.csv"
OUT_JSON = DATA / "edgeiq_bet_quality_engine_v1_1.json"


def clean_track(x):
    if pd.isna(x):
        return ""
    s = str(x).upper().strip()
    s = s.replace("BET365 ", "")
    return re.sub(r"[^A-Z0-9]+", "", s)


def clean_horse(x):
    if pd.isna(x):
        return ""
    return re.sub(r"[^A-Z0-9]+", "", str(x).upper())


def to_num(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def overlay_score(v):
    v = to_num(v)
    if v >= 25:
        return 30
    if v >= 20:
        return 25
    if v >= 15:
        return 20
    if v >= 10:
        return 15
    if v >= 5:
        return 10
    return 0


def interaction_component(v):
    try:
        v = int(float(v))
    except Exception:
        return 0

    if v >= 3:
        return 25
    if v == 2:
        return 22
    if v == 1:
        return 18
    if v == 0:
        return 10
    if v == -1:
        return 5
    return 0


def market_score(v):
    v = to_num(v)
    if v >= 20:
        return 10
    if v >= 10:
        return 5
    return 0


def reliability_score(band, score):
    b = str(band or "").upper().strip()
    s = to_num(score, default=np.nan)

    if b in ["ELITE", "VERY_HIGH"]:
        return 20
    if b in ["POSITIVE", "HIGH", "STRONG"]:
        return 15
    if b in ["NEUTRAL", "MEDIUM", "SOLID"]:
        return 10
    if b in ["NEGATIVE", "LOW", "WEAK", "CHAOTIC"]:
        return 0

    if not np.isnan(s):
        if s >= 30:
            return 20
        if s >= 20:
            return 15
        if s >= 10:
            return 10
        return 0

    return 0


def sectional_score(depth, archetype, runs, peak, late, speed):
    d = str(depth or "").upper().strip()
    a = str(archetype or "").upper().strip()
    r = to_num(runs)
    p = to_num(peak)
    l = to_num(late)
    s = to_num(speed)

    score = 0

    if d == "DNA_READY":
        score += 6
    elif d:
        score += 3

    if r >= 10:
        score += 3
    elif r >= 3:
        score += 1

    if "STRONG_CLOSER" in a:
        score += 4
    elif "PEAK_SPEED" in a:
        score += 4
    elif a and a not in ["UNKNOWN", ""]:
        score += 2

    if p >= 65 or l >= 60 or s >= 58:
        score += 2

    return int(min(score, 15))


def grade(score):
    if score >= 85:
        return "A+"
    if score >= 75:
        return "A"
    if score >= 65:
        return "B"
    if score >= 55:
        return "C"
    if score >= 45:
        return "D"
    return "PASS"


def score_band(score):
    if score >= 90:
        return "90_PLUS"
    if score >= 80:
        return "80_89"
    if score >= 70:
        return "70_79"
    if score >= 60:
        return "60_69"
    if score >= 50:
        return "50_59"
    return "UNDER_50"


def summarise(df, group_col):
    out = (
        df.groupby(group_col, dropna=False)
        .agg(
            rows=("horse", "size"),
            bets=("v8_adjusted_positive_overlay_flag_v1", lambda s: (s.astype(str).str.upper() == "TRUE").sum()),
            wins=("won", "sum"),
            real_overlays=("v8_adjusted_overlay_truth_v1", lambda s: (s == "REAL_OVERLAY").sum()),
        )
        .reset_index()
    )

    out["win_rate"] = out["wins"] / out["rows"]
    out["real_overlay_rate"] = out["real_overlays"] / out["rows"]

    return out


def main():
    replay = pd.read_csv(REPLAY_FILE, low_memory=False)
    reliability = pd.read_csv(RELIABILITY_FILE, low_memory=False)
    sectionals = pd.read_csv(SECTIONAL_FILE, low_memory=False)

    replay["join_track"] = replay["track"].map(clean_track)
    replay["join_race_no"] = replay["race_no"].apply(lambda x: str(int(to_num(x))) if to_num(x) else "")
    replay["join_race"] = replay["meeting_date"].astype(str) + "|" + replay["join_track"] + "|" + replay["join_race_no"]
    replay["join_horse"] = replay["horse_key"].map(clean_horse)

    reliability["join_track"] = reliability["track"].map(clean_track)
    reliability["join_race_no"] = reliability["race_no"].apply(lambda x: str(int(to_num(x))) if to_num(x) else "")
    reliability["join_race"] = reliability["meeting_date"].astype(str) + "|" + reliability["join_track"] + "|" + reliability["join_race_no"]

    reliability_keep = reliability[
        [
            "join_race",
            "race_reliability_score_v1",
            "race_reliability_band_v1",
            "race_reliability_plain_english_v1",
        ]
    ].drop_duplicates("join_race")

    sectionals["join_horse"] = sectionals["horse_key"].map(clean_horse)
    sectional_keep = sectionals[
        [
            "join_horse",
            "runs_with_sectionals",
            "profile_depth_status",
            "sectional_archetype",
            "avg_peak_speed",
            "avg_late_speed",
            "avg_speed",
        ]
    ].drop_duplicates("join_horse")

    df = replay.merge(reliability_keep, on="join_race", how="left")
    df = df.merge(sectional_keep, on="join_horse", how="left")

    df["overlay_score_v1_1"] = df["v8_adjusted_overlay_pct_v1"].apply(overlay_score)
    df["interaction_score_component_v1_1"] = df["interaction_score_v1"].apply(interaction_component)
    df["market_score_component_v1_1"] = df["v8_adjusted_overlay_pct_v1"].apply(market_score)

    df["reliability_score_component_v1_1"] = df.apply(
        lambda r: reliability_score(
            r.get("race_reliability_band_v1"),
            r.get("race_reliability_score_v1"),
        ),
        axis=1,
    )

    df["sectional_score_component_v1_1"] = df.apply(
        lambda r: sectional_score(
            r.get("profile_depth_status"),
            r.get("sectional_archetype"),
            r.get("runs_with_sectionals"),
            r.get("avg_peak_speed"),
            r.get("avg_late_speed"),
            r.get("avg_speed"),
        ),
        axis=1,
    )

    df["bet_quality_score_v1_1"] = (
        df["overlay_score_v1_1"]
        + df["interaction_score_component_v1_1"]
        + df["market_score_component_v1_1"]
        + df["reliability_score_component_v1_1"]
        + df["sectional_score_component_v1_1"]
    )

    df["bet_quality_grade_v1_1"] = df["bet_quality_score_v1_1"].apply(grade)
    df["bet_quality_score_band_v1_1"] = df["bet_quality_score_v1_1"].apply(score_band)

    df["bet_quality_reason_v1_1"] = (
        "OVERLAY:" + df["overlay_score_v1_1"].astype(str)
        + "; INTERACTION:" + df["interaction_score_component_v1_1"].astype(str)
        + "; RELIABILITY:" + df["reliability_score_component_v1_1"].astype(str)
        + "; SECTIONAL:" + df["sectional_score_component_v1_1"].astype(str)
        + "; MARKET:" + df["market_score_component_v1_1"].astype(str)
    )

    df.to_csv(OUT_CSV, index=False)

    by_grade = summarise(df, "bet_quality_grade_v1_1")
    by_score = summarise(df, "bet_quality_score_band_v1_1")

    by_grade.to_csv(OUT_GRADE, index=False)
    by_score.to_csv(OUT_SCORE, index=False)

    summary_rows = [
        ["status", "COMPLETE"],
        ["rows", len(df)],
        ["reliability_matched_rows", int(df["race_reliability_band_v1"].notna().sum())],
        ["sectional_matched_rows", int(df["profile_depth_status"].notna().sum())],
        ["avg_bet_quality_score", round(df["bet_quality_score_v1_1"].mean(), 4)],
        ["max_bet_quality_score", int(df["bet_quality_score_v1_1"].max())],
        ["official_fair_price_replaced", "NO"],
        ["edge_execution_staking_changed", "NO"],
        ["verdict", "BET_QUALITY_ENGINE_V1_1_BUILT"],
    ]

    pd.DataFrame(summary_rows, columns=["metric", "value"]).to_csv(OUT_SUMMARY, index=False)

    OUT_JSON.write_text(
        json.dumps(
            {
                "status": "COMPLETE",
                "rows": int(len(df)),
                "reliability_matched_rows": int(df["race_reliability_band_v1"].notna().sum()),
                "sectional_matched_rows": int(df["profile_depth_status"].notna().sum()),
                "avg_score": float(df["bet_quality_score_v1_1"].mean()),
                "max_score": int(df["bet_quality_score_v1_1"].max()),
                "official_fair_price_replaced": False,
                "edge_execution_staking_changed": False,
                "verdict": "BET_QUALITY_ENGINE_V1_1_BUILT",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("[BET_QUALITY_ENGINE_V1_1] COMPLETE")
    print(f"rows={len(df)}")
    print(f"reliability_matched_rows={int(df['race_reliability_band_v1'].notna().sum())}")
    print(f"sectional_matched_rows={int(df['profile_depth_status'].notna().sum())}")
    print(f"avg_score={df['bet_quality_score_v1_1'].mean():.4f}")
    print(f"max_score={int(df['bet_quality_score_v1_1'].max())}")
    print("official_fair_price_replaced=NO")
    print("edge_execution_staking_changed=NO")
    print("verdict=BET_QUALITY_ENGINE_V1_1_BUILT")


if __name__ == "__main__":
    main()
