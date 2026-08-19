import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

VALIDATION = DATA / "edgeiq_rank_validation_v1_runner_rows.csv"

OUT = DATA / "edgeiq_winner_governance_audit_v1.csv"
SUMMARY = DATA / "edgeiq_winner_governance_audit_v1_summary.csv"

def n(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index)

def safe_band(x):
    s = "" if pd.isna(x) else str(x).strip()
    return s if s else "UNKNOWN"

def main():
    if not VALIDATION.exists():
        raise FileNotFoundError(f"Missing validation rows: {VALIDATION}")

    df = pd.read_csv(VALIDATION).copy()
    df = df[df["result_match_status_v1"].astype(str).str.upper().eq("MATCHED")].copy()

    df["finish_position"] = n(df, "finish_position")
    df["runner_score_v3_1"] = n(df, "runner_score_v3_1")
    df["strength_adjusted_rating_v4"] = n(df, "strength_adjusted_rating_v4")

    if "strength_adjusted_rating_v5" in df.columns:
        df["strength_adjusted_rating_v5"] = n(df, "strength_adjusted_rating_v5")
    else:
        df["strength_adjusted_rating_v5"] = np.nan

    df["governance_band_v7_2"] = df["governance_band_v7_2"].apply(safe_band)

    df["won"] = df["finish_position"].eq(1).astype(int)
    df["placed"] = df["finish_position"].le(3).astype(int)
    df["top4"] = df["finish_position"].le(4).astype(int)

    total_runners = len(df)
    total_winners = int(df["won"].sum())
    total_places = int(df["placed"].sum())

    g = df.groupby("governance_band_v7_2").agg(
        runners=("horse", "count"),
        races=("race_key", "nunique"),
        winners=("won", "sum"),
        places=("placed", "sum"),
        top4=("top4", "sum"),
        avg_finish=("finish_position", "mean"),
        median_finish=("finish_position", "median"),
        avg_rank=("runner_rank_v7_2", "mean"),
        avg_runner_score_v3_1=("runner_score_v3_1", "mean"),
        avg_strength_v4=("strength_adjusted_rating_v4", "mean"),
        avg_strength_v5=("strength_adjusted_rating_v5", "mean"),
    ).reset_index()

    g["runner_share"] = g["runners"] / total_runners if total_runners else 0
    g["winner_share"] = g["winners"] / total_winners if total_winners else 0
    g["place_share"] = g["places"] / total_places if total_places else 0

    g["win_rate"] = g["winners"] / g["runners"]
    g["place_rate"] = g["places"] / g["runners"]
    g["top4_rate"] = g["top4"] / g["runners"]

    # If this is >1.0, the governance band wins more often than its runner population share.
    g["winner_share_vs_runner_share"] = np.where(
        g["runner_share"] > 0,
        g["winner_share"] / g["runner_share"],
        np.nan
    )

    for c in [
        "runner_share",
        "winner_share",
        "place_share",
        "win_rate",
        "place_rate",
        "top4_rate",
        "winner_share_vs_runner_share",
        "avg_finish",
        "median_finish",
        "avg_rank",
        "avg_runner_score_v3_1",
        "avg_strength_v4",
        "avg_strength_v5",
    ]:
        g[c] = pd.to_numeric(g[c], errors="coerce").round(4)

    order = {
        "PROVEN": 1,
        "LIMITED_DATA_3_4_STARTS": 2,
        "LIMITED_DATA_2_STARTS": 3,
        "LIMITED_DATA_1_START": 4,
        "FIRST_STARTER_OR_UNKNOWN": 5,
        "IMPORT_UNKNOWN": 6,
        "UNKNOWN": 99,
    }
    g["_order"] = g["governance_band_v7_2"].map(order).fillna(50)
    g = g.sort_values("_order").drop(columns=["_order"])

    g.to_csv(OUT, index=False)

    summary = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "matched_runner_rows", "value": total_runners},
        {"metric": "races", "value": df["race_key"].nunique()},
        {"metric": "winners", "value": total_winners},
        {"metric": "places", "value": total_places},
        {"metric": "highest_overperforming_band", "value": g.sort_values("winner_share_vs_runner_share", ascending=False).iloc[0]["governance_band_v7_2"] if len(g) else ""},
        {"metric": "highest_overperforming_ratio", "value": g.sort_values("winner_share_vs_runner_share", ascending=False).iloc[0]["winner_share_vs_runner_share"] if len(g) else ""},
        {"metric": "lowest_underperforming_band", "value": g.sort_values("winner_share_vs_runner_share", ascending=True).iloc[0]["governance_band_v7_2"] if len(g) else ""},
        {"metric": "lowest_underperforming_ratio", "value": g.sort_values("winner_share_vs_runner_share", ascending=True).iloc[0]["winner_share_vs_runner_share"] if len(g) else ""},
    ])

    summary.to_csv(SUMMARY, index=False)

    print("[WINNER_GOVERNANCE_AUDIT_V1] COMPLETE")
    print(f"matched_runner_rows={total_runners}")
    print(f"races={df['race_key'].nunique()}")
    print(f"winners={total_winners}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
