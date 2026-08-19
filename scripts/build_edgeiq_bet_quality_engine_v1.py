from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

REPLAY_FILE = DATA / "edgeiq_fair_price_v8_interaction_filter_replay_v1.csv"

OUT_CSV = DATA / "edgeiq_bet_quality_engine_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_bet_quality_engine_v1_summary.csv"
OUT_GRADE = DATA / "edgeiq_bet_quality_engine_v1_by_grade.csv"
OUT_SCORE = DATA / "edgeiq_bet_quality_engine_v1_by_score_band.csv"
OUT_JSON = DATA / "edgeiq_bet_quality_engine_v1.json"


def overlay_score(v):
    try:
        v = float(v)
    except:
        return 0

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


def interaction_score(v):
    try:
        v = int(float(v))
    except:
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
    try:
        v = float(v)
    except:
        return 0

    if v >= 20:
        return 10

    if v >= 10:
        return 5

    return 0


def grade(score):
    if score >= 85:
        return "A+"
    if score >= 75:
        return "A"
    if score >= 65:
        return "B"
    if score >= 55:
        return "C"
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


def main():

    df = pd.read_csv(REPLAY_FILE)

    df["overlay_score_v1"] = df["v8_adjusted_overlay_pct_v1"].apply(
        overlay_score
    )

    df["interaction_score_component_v1"] = df[
        "interaction_score_v1"
    ].apply(interaction_score)

    df["market_score_component_v1"] = df[
        "v8_adjusted_overlay_pct_v1"
    ].apply(market_score)

    df["bet_quality_score_v1"] = (
        df["overlay_score_v1"]
        + df["interaction_score_component_v1"]
        + df["market_score_component_v1"]
    )

    df["bet_quality_grade_v1"] = (
        df["bet_quality_score_v1"]
        .apply(grade)
    )

    df["bet_quality_score_band_v1"] = (
        df["bet_quality_score_v1"]
        .apply(score_band)
    )

    df.to_csv(OUT_CSV, index=False)

    grade_summary = (
        df.groupby("bet_quality_grade_v1", dropna=False)
        .agg(
            rows=("horse","size"),
            wins=("won","sum"),
            real_overlays=(
                "v8_adjusted_overlay_truth_v1",
                lambda s: (s=="REAL_OVERLAY").sum()
            )
        )
        .reset_index()
    )

    grade_summary["win_rate"] = (
        grade_summary["wins"]
        / grade_summary["rows"]
    )

    grade_summary["real_overlay_rate"] = (
        grade_summary["real_overlays"]
        / grade_summary["rows"]
    )

    grade_summary.to_csv(
        OUT_GRADE,
        index=False
    )

    score_summary = (
        df.groupby("bet_quality_score_band_v1", dropna=False)
        .agg(
            rows=("horse","size"),
            wins=("won","sum"),
            real_overlays=(
                "v8_adjusted_overlay_truth_v1",
                lambda s: (s=="REAL_OVERLAY").sum()
            )
        )
        .reset_index()
    )

    score_summary["win_rate"] = (
        score_summary["wins"]
        / score_summary["rows"]
    )

    score_summary["real_overlay_rate"] = (
        score_summary["real_overlays"]
        / score_summary["rows"]
    )

    score_summary.to_csv(
        OUT_SCORE,
        index=False
    )

    summary = pd.DataFrame([
        {
            "metric":"rows",
            "value":len(df)
        },
        {
            "metric":"avg_bet_quality_score",
            "value":round(
                df["bet_quality_score_v1"].mean(),
                4
            )
        },
        {
            "metric":"max_bet_quality_score",
            "value":int(
                df["bet_quality_score_v1"].max()
            )
        },
        {
            "metric":"verdict",
            "value":"BET_QUALITY_ENGINE_V1_BUILT"
        }
    ])

    summary.to_csv(
        OUT_SUMMARY,
        index=False
    )

    payload = {
        "rows": int(len(df)),
        "avg_score": float(
            df["bet_quality_score_v1"].mean()
        ),
        "max_score": int(
            df["bet_quality_score_v1"].max()
        ),
        "verdict":"BET_QUALITY_ENGINE_V1_BUILT"
    }

    with open(OUT_JSON,"w") as f:
        json.dump(payload,f,indent=2)

    print("[BET_QUALITY_ENGINE_V1] COMPLETE")
    print(f"rows={len(df)}")
    print(f"avg_score={df['bet_quality_score_v1'].mean():.4f}")
    print(f"max_score={int(df['bet_quality_score_v1'].max())}")
    print("verdict=BET_QUALITY_ENGINE_V1_BUILT")


if __name__ == "__main__":
    main()

