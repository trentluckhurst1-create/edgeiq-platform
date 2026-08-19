import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_execution_candidates_v1.csv"

OUT = DATA / "edgeiq_execution_confidence_v1.csv"
AUDIT = DATA / "edgeiq_execution_confidence_v1_summary.csv"
BOARD = DATA / "edgeiq_execution_board_v2.csv"

def n(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index)

def s(df, col):
    if col in df.columns:
        return df[col].astype(str).str.upper().str.strip()
    return pd.Series("", index=df.index)

def horse_quality(row):
    score = row["runner_score_v3_1"]
    strength = row["strength_adjusted_rating_v4"]

    runner_component = 0
    if pd.notna(score):
        if score >= 70:
            runner_component = 15
        elif score >= 65:
            runner_component = 13
        elif score >= 60:
            runner_component = 10
        elif score >= 55:
            runner_component = 7
        elif score >= 50:
            runner_component = 5
        elif score >= 45:
            runner_component = 3

    strength_component = 0
    if pd.notna(strength):
        if strength >= 70:
            strength_component = 15
        elif strength >= 65:
            strength_component = 13
        elif strength >= 60:
            strength_component = 10
        elif strength >= 55:
            strength_component = 7
        elif strength >= 50:
            strength_component = 5
        elif strength >= 45:
            strength_component = 3

    return runner_component + strength_component

def data_quality(governance):
    g = str(governance).upper().strip()

    if g == "PROVEN":
        return 30
    if g == "LIMITED_DATA_3_4_STARTS":
        return 20
    if g == "LIMITED_DATA_2_STARTS":
        return 12
    if g == "LIMITED_DATA_1_START":
        return 6
    if g == "IMPORT_UNKNOWN":
        return 4
    if g == "FIRST_STARTER_OR_UNKNOWN":
        return 2
    if g in ["", "NAN", "NONE"]:
        return 8

    return 10

def race_quality(band):
    b = str(band).upper().strip()

    if b == "ELITE":
        return 20
    if b == "STRONG":
        return 16
    if b == "SOLID":
        return 12
    if b == "WEAK":
        return 8
    if b == "VERY_WEAK":
        return 4

    return 10

def market_opportunity(edge):
    if pd.isna(edge):
        return 0
    if edge >= 200:
        return 20
    if edge >= 100:
        return 18
    if edge >= 60:
        return 16
    if edge >= 35:
        return 13
    if edge >= 25:
        return 10
    if edge >= 15:
        return 6
    if edge >= 8:
        return 3
    return 0

def rank_bonus(rank):
    if pd.isna(rank):
        return 0
    if rank == 1:
        return 5
    if rank == 2:
        return 4
    if rank == 3:
        return 3
    if rank <= 5:
        return 1
    return 0

def extreme_overlay_penalty(row):
    edge = row["overlay_pct_v1"]
    gov = str(row["governance_band_v7_2"]).upper().strip()

    if pd.isna(edge):
        return 0

    if edge >= 200 and gov != "PROVEN":
        return -10
    if edge >= 300 and gov == "PROVEN":
        return -3
    return 0

def band(score):
    if score >= 85:
        return "HIGH"
    if score >= 70:
        return "MEDIUM"
    if score >= 55:
        return "LOW"
    return "AVOID"

def final_action(row):
    base = str(row["execution_action_v1"]).upper().strip()
    conf = str(row["execution_confidence_band_v1"]).upper().strip()

    if base == "NO_BET":
        return "NO_BET"
    if conf == "AVOID":
        return "NO_BET"
    if base == "EXECUTE" and conf == "HIGH":
        return "EXECUTE_HIGH"
    if base == "EXECUTE" and conf == "MEDIUM":
        return "EXECUTE_MEDIUM"
    if base == "EXECUTE" and conf == "LOW":
        return "WATCH_LOW"
    if base == "STRONG_WATCH" and conf in ["HIGH", "MEDIUM"]:
        return "STRONG_WATCH"
    if base == "WATCH" and conf in ["HIGH", "MEDIUM", "LOW"]:
        return "WATCH"
    return "NO_BET"

def main():
    if not INFILE.exists():
        raise FileNotFoundError(f"Missing input: {INFILE}")

    df = pd.read_csv(INFILE).copy()

    df["runner_score_v3_1"] = n(df, "runner_score_v3_1")
    df["strength_adjusted_rating_v4"] = n(df, "strength_adjusted_rating_v4")
    df["runner_rank_v7_2"] = n(df, "runner_rank_v7_2")
    df["overlay_pct_v1"] = n(df, "overlay_pct_v1")
    df["tab_fixed_win"] = n(df, "tab_fixed_win")
    df["fair_price_v7_2"] = n(df, "fair_price_v7_2")

    df["governance_band_v7_2"] = s(df, "governance_band_v7_2")
    df["projection_status_v6"] = s(df, "projection_status_v6")
    df["live_race_strength_band_v2"] = s(df, "live_race_strength_band_v2")
    df["execution_action_v1"] = s(df, "execution_action_v1")

    df["horse_quality_score_v1"] = df.apply(horse_quality, axis=1)
    df["data_quality_score_v1"] = df["governance_band_v7_2"].apply(data_quality)
    df["race_quality_score_v1"] = df["live_race_strength_band_v2"].apply(race_quality)
    df["market_opportunity_score_v1"] = df["overlay_pct_v1"].apply(market_opportunity)
    df["rank_bonus_v1"] = df["runner_rank_v7_2"].apply(rank_bonus)
    df["extreme_overlay_penalty_v1"] = df.apply(extreme_overlay_penalty, axis=1)

    df["execution_confidence_score_v1"] = (
        df["horse_quality_score_v1"] +
        df["data_quality_score_v1"] +
        df["race_quality_score_v1"] +
        df["market_opportunity_score_v1"] +
        df["rank_bonus_v1"] +
        df["extreme_overlay_penalty_v1"]
    )

    df["execution_confidence_score_v1"] = df["execution_confidence_score_v1"].clip(0, 100).round(1)
    df["execution_confidence_band_v1"] = df["execution_confidence_score_v1"].apply(band)
    df["final_execution_action_v2"] = df.apply(final_action, axis=1)

    df["confidence_reason_v1"] = (
        "horseQ " + df["horse_quality_score_v1"].astype(str) +
        " | dataQ " + df["data_quality_score_v1"].astype(str) +
        " | raceQ " + df["race_quality_score_v1"].astype(str) +
        " | marketQ " + df["market_opportunity_score_v1"].astype(str) +
        " | rankB " + df["rank_bonus_v1"].astype(str) +
        " | penalty " + df["extreme_overlay_penalty_v1"].astype(str)
    )

    priority = {
        "EXECUTE_HIGH": 5,
        "EXECUTE_MEDIUM": 4,
        "STRONG_WATCH": 3,
        "WATCH_LOW": 2,
        "WATCH": 1,
        "NO_BET": 0,
    }

    df["final_execution_priority_v2"] = df["final_execution_action_v2"].map(priority).fillna(0)

    df = df.sort_values(
        ["final_execution_priority_v2", "execution_confidence_score_v1", "overlay_pct_v1"],
        ascending=[False, False, False],
        na_position="last"
    )

    df.to_csv(OUT, index=False)

    board = df[df["final_execution_action_v2"] != "NO_BET"].copy()
    board_cols = [
        "track",
        "race_no",
        "horse",
        "final_execution_action_v2",
        "execution_action_v1",
        "execution_confidence_score_v1",
        "execution_confidence_band_v1",
        "runner_score_v3_1",
        "strength_adjusted_rating_v4",
        "runner_rank_v7_2",
        "fair_price_v7_2",
        "tab_fixed_win",
        "overlay_pct_v1",
        "governance_band_v7_2",
        "projection_status_v6",
        "live_race_strength_band_v2",
        "horse_quality_score_v1",
        "data_quality_score_v1",
        "race_quality_score_v1",
        "market_opportunity_score_v1",
        "confidence_reason_v1",
        "execution_reason_v1",
    ]
    board = board[[c for c in board_cols if c in board.columns]]
    board.to_csv(BOARD, index=False)

    summary = pd.DataFrame([
        {"metric": "rows", "value": len(df)},
        {"metric": "board_rows", "value": len(board)},
        {"metric": "execute_high", "value": int((df["final_execution_action_v2"] == "EXECUTE_HIGH").sum())},
        {"metric": "execute_medium", "value": int((df["final_execution_action_v2"] == "EXECUTE_MEDIUM").sum())},
        {"metric": "strong_watch", "value": int((df["final_execution_action_v2"] == "STRONG_WATCH").sum())},
        {"metric": "watch_low", "value": int((df["final_execution_action_v2"] == "WATCH_LOW").sum())},
        {"metric": "watch", "value": int((df["final_execution_action_v2"] == "WATCH").sum())},
        {"metric": "no_bet", "value": int((df["final_execution_action_v2"] == "NO_BET").sum())},
        {"metric": "high_confidence", "value": int((df["execution_confidence_band_v1"] == "HIGH").sum())},
        {"metric": "medium_confidence", "value": int((df["execution_confidence_band_v1"] == "MEDIUM").sum())},
        {"metric": "low_confidence", "value": int((df["execution_confidence_band_v1"] == "LOW").sum())},
        {"metric": "avoid_confidence", "value": int((df["execution_confidence_band_v1"] == "AVOID").sum())},
    ])
    summary.to_csv(AUDIT, index=False)

    print("[EXECUTION_CONFIDENCE_V1] COMPLETE")
    print(f"rows={len(df)}")
    print(f"board_rows={len(board)}")
    print(f"wrote={OUT}")
    print(f"board={BOARD}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
