import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

VALIDATION = DATA / "edgeiq_rank_validation_v1_runner_rows.csv"

OUT = DATA / "edgeiq_winner_rank_audit_v1.csv"
SUMMARY = DATA / "edgeiq_winner_rank_audit_v1_summary.csv"
WINNER_BUCKETS = DATA / "edgeiq_winner_rank_audit_v1_winner_rank_buckets.csv"

def n(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index)

def rank_bucket(rank):
    if pd.isna(rank):
        return "NO_RANK"
    r = int(rank)
    if r == 1:
        return "RANK_1"
    if r == 2:
        return "RANK_2"
    if r == 3:
        return "RANK_3"
    if r <= 5:
        return "RANK_4_5"
    if r <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"

def main():
    if not VALIDATION.exists():
        raise FileNotFoundError(f"Missing validation rows: {VALIDATION}")

    df = pd.read_csv(VALIDATION).copy()

    df = df[df["result_match_status_v1"].astype(str).str.upper().eq("MATCHED")].copy()

    df["runner_rank_v7_2"] = n(df, "runner_rank_v7_2")
    df["runner_score_v3_1"] = n(df, "runner_score_v3_1")
    df["strength_adjusted_rating_v4"] = n(df, "strength_adjusted_rating_v4")
    df["finish_position"] = n(df, "finish_position")

    winners = df[df["finish_position"].eq(1)].copy()
    top_ranked = df.sort_values(["race_key", "runner_rank_v7_2"]).groupby("race_key").head(1).copy()

    w_keep = [
        "race_key",
        "event_date",
        "track",
        "race_no",
        "horse",
        "runner_rank_v7_2",
        "runner_score_v3_1",
        "strength_adjusted_rating_v4",
        "governance_band_v7_2",
        "execution_confidence_band_v1",
        "fair_price_v7_2",
        "tab_fixed_win",
        "finish_position",
    ]

    t_keep = [
        "race_key",
        "horse",
        "runner_rank_v7_2",
        "runner_score_v3_1",
        "strength_adjusted_rating_v4",
        "governance_band_v7_2",
        "execution_confidence_band_v1",
        "fair_price_v7_2",
        "tab_fixed_win",
        "finish_position",
    ]

    w = winners[[c for c in w_keep if c in winners.columns]].copy()
    t = top_ranked[[c for c in t_keep if c in top_ranked.columns]].copy()

    w = w.rename(columns={
        "horse": "winner",
        "runner_rank_v7_2": "winner_rank_v7_2",
        "runner_score_v3_1": "winner_score_v3_1",
        "strength_adjusted_rating_v4": "winner_strength_adjusted_rating_v4",
        "governance_band_v7_2": "winner_governance_band_v7_2",
        "execution_confidence_band_v1": "winner_confidence_band_v1",
        "fair_price_v7_2": "winner_fair_price_v7_2",
        "tab_fixed_win": "winner_market_price",
        "finish_position": "winner_finish_position",
    })

    t = t.rename(columns={
        "horse": "top_ranked_runner",
        "runner_rank_v7_2": "top_ranked_rank_v7_2",
        "runner_score_v3_1": "top_ranked_score_v3_1",
        "strength_adjusted_rating_v4": "top_ranked_strength_adjusted_rating_v4",
        "governance_band_v7_2": "top_ranked_governance_band_v7_2",
        "execution_confidence_band_v1": "top_ranked_confidence_band_v1",
        "fair_price_v7_2": "top_ranked_fair_price_v7_2",
        "tab_fixed_win": "top_ranked_market_price",
        "finish_position": "top_ranked_finish_position",
    })

    out = w.merge(t, on="race_key", how="left")

    out["winner_rank_bucket_v1"] = out["winner_rank_v7_2"].apply(rank_bucket)
    out["winner_was_rank1_v1"] = out["winner_rank_v7_2"].eq(1).astype(int)
    out["winner_was_top3_v1"] = out["winner_rank_v7_2"].le(3).astype(int)
    out["winner_was_top5_v1"] = out["winner_rank_v7_2"].le(5).astype(int)
    out["winner_was_top10_v1"] = out["winner_rank_v7_2"].le(10).astype(int)

    out["score_gap_top_minus_winner_v1"] = (
        out["top_ranked_score_v3_1"] - out["winner_score_v3_1"]
    ).round(3)

    out["strength_gap_top_minus_winner_v1"] = (
        out["top_ranked_strength_adjusted_rating_v4"] -
        out["winner_strength_adjusted_rating_v4"]
    ).round(3)

    out = out.sort_values(["event_date", "track", "race_no"])
    out.to_csv(OUT, index=False)

    buckets = out.groupby("winner_rank_bucket_v1").agg(
        races=("race_key", "count"),
        avg_winner_rank=("winner_rank_v7_2", "mean"),
        avg_winner_score=("winner_score_v3_1", "mean"),
        avg_top_score=("top_ranked_score_v3_1", "mean"),
        avg_score_gap=("score_gap_top_minus_winner_v1", "mean"),
    ).reset_index()

    order = {
        "RANK_1": 1,
        "RANK_2": 2,
        "RANK_3": 3,
        "RANK_4_5": 4,
        "RANK_6_10": 6,
        "RANK_11_PLUS": 11,
        "NO_RANK": 99,
    }
    buckets["_order"] = buckets["winner_rank_bucket_v1"].map(order).fillna(99)
    buckets = buckets.sort_values("_order").drop(columns=["_order"])
    for c in ["avg_winner_rank", "avg_winner_score", "avg_top_score", "avg_score_gap"]:
        buckets[c] = buckets[c].round(3)

    buckets.to_csv(WINNER_BUCKETS, index=False)

    total = len(out)

    summary = pd.DataFrame([
        {"metric": "races_audited", "value": total},
        {"metric": "winner_rank1_count", "value": int(out["winner_was_rank1_v1"].sum())},
        {"metric": "winner_top3_count", "value": int(out["winner_was_top3_v1"].sum())},
        {"metric": "winner_top5_count", "value": int(out["winner_was_top5_v1"].sum())},
        {"metric": "winner_top10_count", "value": int(out["winner_was_top10_v1"].sum())},
        {"metric": "winner_rank1_rate", "value": round(out["winner_was_rank1_v1"].mean(), 4) if total else 0},
        {"metric": "winner_top3_rate", "value": round(out["winner_was_top3_v1"].mean(), 4) if total else 0},
        {"metric": "winner_top5_rate", "value": round(out["winner_was_top5_v1"].mean(), 4) if total else 0},
        {"metric": "winner_top10_rate", "value": round(out["winner_was_top10_v1"].mean(), 4) if total else 0},
        {"metric": "avg_winner_rank", "value": round(out["winner_rank_v7_2"].mean(), 3) if total else 0},
        {"metric": "avg_score_gap_top_minus_winner", "value": round(out["score_gap_top_minus_winner_v1"].mean(), 3) if total else 0},
        {"metric": "avg_strength_gap_top_minus_winner", "value": round(out["strength_gap_top_minus_winner_v1"].mean(), 3) if total else 0},
    ])

    summary.to_csv(SUMMARY, index=False)

    print("[WINNER_RANK_AUDIT_V1] COMPLETE")
    print(f"races_audited={total}")
    print(f"winner_rank1_rate={summary.loc[summary['metric'].eq('winner_rank1_rate'), 'value'].iloc[0]}")
    print(f"winner_top3_rate={summary.loc[summary['metric'].eq('winner_top3_rate'), 'value'].iloc[0]}")
    print(f"winner_top5_rate={summary.loc[summary['metric'].eq('winner_top5_rate'), 'value'].iloc[0]}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
