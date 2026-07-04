import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V6 = DATA / "edgeiq_strength_adjusted_ratings_v6.csv"

OUT = DATA / "edgeiq_runner_score_v4.csv"
AUDIT = DATA / "edgeiq_runner_score_v4_audit.csv"

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
    if not V6.exists():
        raise FileNotFoundError(f"Missing {V6}")

    df = pd.read_csv(V6).copy()

    df["strength_adjusted_rating_v6"] = pd.to_numeric(df["strength_adjusted_rating_v6"], errors="coerce")
    df["confidence_adjusted_rating_v6"] = pd.to_numeric(df["confidence_adjusted_rating_v6"], errors="coerce")
    df["horse_results_strength_v3"] = pd.to_numeric(df["horse_results_strength_v3"], errors="coerce")
    df["live_race_strength_score_v3"] = pd.to_numeric(df["live_race_strength_score_v3"], errors="coerce")

    # V4 score: ability first. Confidence stays separate.
    df["runner_score_v4"] = (
        0.72 * df["strength_adjusted_rating_v6"].fillna(35) +
        0.18 * df["horse_results_strength_v3"].fillna(df["strength_adjusted_rating_v6"]).fillna(35) +
        0.10 * df["live_race_strength_score_v3"].fillna(50)
    ).clip(0, 100).round(3)

    df["runner_confidence_score_v4"] = (
        df["confidence_adjusted_rating_v6"].fillna(df["runner_score_v4"] * 0.8)
    ).clip(0, 100).round(3)

    df["runner_score_band_v4"] = df["runner_score_v4"].apply(band)

    df["race_key_v4"] = (
        df["track"].astype(str).str.upper().str.strip() + "|" +
        df["race_no"].astype(str).str.strip()
    )

    df = df.sort_values(["race_key_v4", "runner_score_v4"], ascending=[True, False])
    df["runner_rank_v4"] = df.groupby("race_key_v4").cumcount() + 1

    df["runner_score_reason_v4"] = (
        "V4 ability rank | v6=" + df["strength_adjusted_rating_v6"].round(2).astype(str) +
        " | horse_results=" + df["horse_results_strength_v3"].round(2).astype(str) +
        " | race_strength=" + df["live_race_strength_score_v3"].round(2).astype(str) +
        " | confidence_rating=" + df["confidence_adjusted_rating_v6"].round(2).astype(str) +
        " | gov=" + df["governance_band_v7_2"].astype(str)
    )

    df.to_csv(OUT, index=False)

    audit = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "rows", "value": len(df)},
        {"metric": "races", "value": df["race_key_v4"].nunique()},
        {"metric": "avg_runner_score_v4", "value": round(df["runner_score_v4"].mean(), 3)},
        {"metric": "max_runner_score_v4", "value": round(df["runner_score_v4"].max(), 3)},
        {"metric": "min_runner_score_v4", "value": round(df["runner_score_v4"].min(), 3)},
        {"metric": "elite", "value": int((df["runner_score_band_v4"] == "ELITE").sum())},
        {"metric": "strong", "value": int((df["runner_score_band_v4"] == "STRONG").sum())},
        {"metric": "positive", "value": int((df["runner_score_band_v4"] == "POSITIVE").sum())},
        {"metric": "neutral", "value": int((df["runner_score_band_v4"] == "NEUTRAL").sum())},
        {"metric": "weak", "value": int((df["runner_score_band_v4"] == "WEAK").sum())},
        {"metric": "poor", "value": int((df["runner_score_band_v4"] == "POOR").sum())},
    ])
    audit.to_csv(AUDIT, index=False)

    print("[RUNNER_SCORE_V4] COMPLETE")
    print(f"rows={len(df)}")
    print(f"races={df['race_key_v4'].nunique()}")
    print(f"avg_score={round(df['runner_score_v4'].mean(), 3)}")
    print(f"max_score={round(df['runner_score_v4'].max(), 3)}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
