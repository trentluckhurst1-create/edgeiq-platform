import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_execution_confidence_v1.csv"
OUT = DATA / "edgeiq_execution_board_v2_clean.csv"
AUDIT = DATA / "edgeiq_execution_board_v2_clean_summary.csv"

def n(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index)

def clean_action(x):
    x = str(x).upper().strip()
    return {
        "EXECUTE_HIGH": "EXECUTE HIGH",
        "EXECUTE_MEDIUM": "EXECUTE MEDIUM",
        "STRONG_WATCH": "STRONG WATCH",
        "WATCH_LOW": "WATCH LOW",
        "WATCH": "WATCH",
    }.get(x, x)

def money(x):
    if pd.isna(x):
        return ""
    return f"${x:.2f}"

def pct(x):
    if pd.isna(x):
        return ""
    return f"{x:.1f}%"

def main():
    df = pd.read_csv(INFILE)

    df = df[df["final_execution_action_v2"].astype(str).str.upper().ne("NO_BET")].copy()

    for c in [
        "runner_score_v3_1",
        "strength_adjusted_rating_v4",
        "runner_rank_v7_2",
        "fair_price_v7_2",
        "tab_fixed_win",
        "overlay_pct_v1",
        "execution_confidence_score_v1",
        "horse_quality_score_v1",
        "data_quality_score_v1",
        "race_quality_score_v1",
        "market_opportunity_score_v1",
    ]:
        df[c] = n(df, c)

    df["action"] = df["final_execution_action_v2"].apply(clean_action)
    df["confidence"] = df["execution_confidence_band_v1"].astype(str).str.upper().str.strip()
    df["fair"] = df["fair_price_v7_2"].apply(money)
    df["market"] = df["tab_fixed_win"].apply(money)
    df["edge"] = df["overlay_pct_v1"].apply(pct)

    df["decision_reason"] = (
        df["action"] +
        " | CONF " + df["execution_confidence_score_v1"].round(0).astype(int).astype(str) +
        " " + df["confidence"] +
        " | FAIR " + df["fair"] +
        " vs TAB " + df["market"] +
        " | EDGE " + df["edge"] +
        " | RANK " + df["runner_rank_v7_2"].round(0).astype(int).astype(str) +
        " | GOV " + df["governance_band_v7_2"].astype(str)
    )

    keep = [
        "track",
        "race_no",
        "horse",
        "action",
        "confidence",
        "execution_confidence_score_v1",
        "fair",
        "market",
        "edge",
        "runner_score_v3_1",
        "strength_adjusted_rating_v4",
        "runner_rank_v7_2",
        "governance_band_v7_2",
        "projection_status_v6",
        "live_race_strength_band_v2",
        "horse_quality_score_v1",
        "data_quality_score_v1",
        "race_quality_score_v1",
        "market_opportunity_score_v1",
        "decision_reason",
    ]

    df = df[[c for c in keep if c in df.columns]].copy()

    priority = {
        "EXECUTE HIGH": 5,
        "EXECUTE MEDIUM": 4,
        "STRONG WATCH": 3,
        "WATCH LOW": 2,
        "WATCH": 1,
    }

    df["_priority"] = df["action"].map(priority).fillna(0)
    df = df.sort_values(
        ["_priority", "execution_confidence_score_v1", "runner_score_v3_1"],
        ascending=[False, False, False],
    ).drop(columns=["_priority"])

    df.to_csv(OUT, index=False)

    summary = pd.DataFrame([
        {"metric": "board_rows", "value": len(df)},
        {"metric": "execute_high", "value": int((df["action"] == "EXECUTE HIGH").sum())},
        {"metric": "execute_medium", "value": int((df["action"] == "EXECUTE MEDIUM").sum())},
        {"metric": "strong_watch", "value": int((df["action"] == "STRONG WATCH").sum())},
        {"metric": "watch", "value": int((df["action"] == "WATCH").sum())},
    ])
    summary.to_csv(AUDIT, index=False)

    print("[EXECUTION_BOARD_V2_CLEAN] COMPLETE")
    print(f"rows={len(df)}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
