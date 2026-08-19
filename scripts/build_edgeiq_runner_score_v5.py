from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_SCORE = DATA / "edgeiq_runner_score_v4.csv"
PACE_ADVANTAGE = DATA / "edgeiq_pace_advantage_v1.csv"

OUT = DATA / "edgeiq_runner_score_v5.csv"
AUDIT = DATA / "edgeiq_runner_score_v5_audit.csv"


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def upper_text(value: object) -> str:
    return clean_text(value).upper()


def canon_horse(value: object) -> str:
    text = upper_text(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def norm_track(value: object) -> str:
    text = upper_text(value)
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM "]:
        text = text.replace(prefix, "")
    return re.sub(r"\s+", " ", text).strip()


def score_band(score: float) -> str:
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 80:
        return "80_PLUS"
    if score >= 70:
        return "70_79"
    if score >= 60:
        return "60_69"
    if score >= 50:
        return "50_59"
    if score >= 40:
        return "40_49"
    return "LT_40"


def load_runner_score() -> pd.DataFrame:
    if not RUNNER_SCORE.exists():
        raise FileNotFoundError(f"Missing runner score file: {RUNNER_SCORE}")

    df = pd.read_csv(RUNNER_SCORE, low_memory=False)
    df["meeting_date"] = ""
    if "race_date" in df.columns:
        df["meeting_date"] = df["race_date"].astype(str).str.slice(0, 10)
    elif "meeting_date" in df.columns:
        df["meeting_date"] = df["meeting_date"].astype(str).str.slice(0, 10)

    df["join_track"] = df["track"].map(norm_track)
    df["join_race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["join_horse"] = df["horse"].map(canon_horse)
    df["runner_score_v4"] = pd.to_numeric(df["runner_score_v4"], errors="coerce")
    df["runner_rank_v4"] = pd.to_numeric(df.get("runner_rank_v4"), errors="coerce")
    df = df[
        df["meeting_date"].ne("")
        & df["join_track"].ne("")
        & df["join_race_no"].notna()
        & df["join_horse"].ne("")
    ].copy()
    return df


def load_pace_advantage() -> pd.DataFrame:
    if not PACE_ADVANTAGE.exists():
        raise FileNotFoundError(f"Missing pace advantage file: {PACE_ADVANTAGE}")

    df = pd.read_csv(PACE_ADVANTAGE, low_memory=False)
    df["meeting_date"] = df["meeting_date"].astype(str).str.slice(0, 10)
    df["join_track"] = df["track"].map(norm_track)
    df["join_race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["join_horse"] = df["horse"].map(canon_horse)
    df["runner_score_v4"] = pd.to_numeric(df["runner_score_v4"], errors="coerce")
    df["pace_advantage_score_v1"] = pd.to_numeric(df["pace_advantage_score_v1"], errors="coerce").fillna(0.0)
    return df


def main() -> None:
    runner = load_runner_score()
    pace = load_pace_advantage()

    merged = runner.merge(
        pace[[
            "meeting_date",
            "join_track",
            "join_race_no",
            "join_horse",
            "pace_pressure_score_v1",
            "pace_pressure_band_v1",
            "tactical_style",
            "dna_run_style",
            "style_source_v1",
            "pace_advantage_score_v1",
            "pace_advantage_band_v1",
            "pace_advantage_reason_v1",
        ]],
        on=["meeting_date", "join_track", "join_race_no", "join_horse"],
        how="inner",
    )
    if merged.empty:
        raise RuntimeError("No current runners matched between runner_score_v4 and pace_advantage_v1.")

    merged["runner_score_v5"] = np.clip(
        merged["runner_score_v4"].fillna(0.0) + merged["pace_advantage_score_v1"].fillna(0.0),
        0,
        100,
    )
    merged["runner_score_v5"] = merged["runner_score_v5"].round(3)

    merged["race_key_v5"] = (
        merged["meeting_date"].astype(str) + "|" + merged["track"].astype(str) + "|R" + merged["race_no"].astype(str)
    )

    merged = merged.sort_values(
        ["meeting_date", "track", "race_no", "runner_score_v5", "pace_advantage_score_v1", "runner_score_v4", "horse"],
        ascending=[True, True, True, False, False, False, True],
    ).reset_index(drop=True)

    merged["runner_order_v5"] = merged.groupby("race_key_v5").cumcount() + 1
    merged["runner_rank_v5"] = (
        merged.groupby("race_key_v5")["runner_score_v5"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    merged["runner_score_band_v5"] = merged["runner_score_v5"].apply(score_band)
    merged["v5_minus_v4"] = (merged["runner_score_v5"] - merged["runner_score_v4"]).round(3)
    merged["runner_score_reason_v5"] = (
        "v4=" + merged["runner_score_v4"].round(3).astype(str)
        + " | pace_adjustment=" + merged["pace_advantage_score_v1"].astype(int).astype(str)
        + " | pace_band=" + merged["pace_pressure_band_v1"].astype(str)
        + " | tactical_style=" + merged["tactical_style"].astype(str)
    )

    output_columns = list(runner.columns)
    extra_columns = [
        "pace_pressure_score_v1",
        "pace_pressure_band_v1",
        "tactical_style",
        "dna_run_style",
        "style_source_v1",
        "pace_advantage_score_v1",
        "pace_advantage_band_v1",
        "pace_advantage_reason_v1",
        "runner_score_v5",
        "v5_minus_v4",
        "runner_score_band_v5",
        "race_key_v5",
        "runner_order_v5",
        "runner_rank_v5",
        "runner_score_reason_v5",
    ]
    keep = [col for col in output_columns + extra_columns if col in merged.columns]
    out = merged[keep].copy()
    out.to_csv(OUT, index=False)

    top_scores = out.groupby("race_key_v5")["runner_score_v5"].max().reset_index(name="top_score")
    tied_top = out.merge(top_scores, on="race_key_v5", how="left")
    tied_top_races = tied_top[tied_top["runner_score_v5"].eq(tied_top["top_score"])].groupby("race_key_v5").size()

    audit_rows = [
        {"metric": "runner_score_v4_rows", "value": int(len(runner))},
        {"metric": "pace_advantage_rows", "value": int(len(pace))},
        {"metric": "runner_score_v5_rows", "value": int(len(out))},
        {"metric": "runner_score_v5_races", "value": int(out["race_key_v5"].nunique())},
        {"metric": "avg_runner_score_v4", "value": round(float(out["runner_score_v4"].mean()), 3)},
        {"metric": "avg_runner_score_v5", "value": round(float(out["runner_score_v5"].mean()), 3)},
        {"metric": "avg_pace_adjustment", "value": round(float(out["pace_advantage_score_v1"].mean()), 3)},
        {"metric": "positive_adjustment_rows", "value": int(out["pace_advantage_score_v1"].gt(0).sum())},
        {"metric": "negative_adjustment_rows", "value": int(out["pace_advantage_score_v1"].lt(0).sum())},
        {"metric": "neutral_adjustment_rows", "value": int(out["pace_advantage_score_v1"].eq(0).sum())},
        {"metric": "clipped_zero_rows", "value": int(out["runner_score_v5"].le(0).sum())},
        {"metric": "clipped_hundred_rows", "value": int(out["runner_score_v5"].ge(100).sum())},
        {"metric": "races_with_tied_top_score_v5", "value": int((tied_top_races > 1).sum())},
    ]

    pd.DataFrame(audit_rows).to_csv(AUDIT, index=False)

    print("[EDGEIQ_RUNNER_SCORE_V5] COMPLETE")
    print(f"runner_score_v5_rows={len(out)}")
    print(f"runner_score_v5_races={out['race_key_v5'].nunique()}")
    print(f"avg_pace_adjustment={round(float(out['pace_advantage_score_v1'].mean()), 3)}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")


if __name__ == "__main__":
    main()
