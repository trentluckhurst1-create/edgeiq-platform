import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_historical_runner_scores_v1.csv"

SUMMARY = DATA / "edgeiq_historical_validation_summary_v1.csv"
RANK = DATA / "edgeiq_historical_roi_by_rank_v1.csv"
GOV = DATA / "edgeiq_historical_roi_by_governance_v1.csv"
SCORE = DATA / "edgeiq_historical_roi_by_score_band_v1.csv"
CAPTURE = DATA / "edgeiq_historical_contender_capture_v1.csv"

def roi_group(df):
    bets = len(df)
    wins = int(df["won"].sum())

    profit = ((df["sp_num"].fillna(0) - 1) * df["won"]).sum() - (bets - wins)

    return pd.Series({
        "bets": bets,
        "wins": wins,
        "strike_rate": round(wins / bets, 4) if bets else 0,
        "profit_1u": round(profit, 2),
        "roi": round(profit / bets, 4) if bets else 0,
        "avg_sp": round(df["sp_num"].mean(), 2) if bets else 0
    })

def main():

    df = pd.read_csv(INPUT)

    df["sp_num"] = pd.to_numeric(df["sp_num"], errors="coerce")

    df = df[
        df["sp_num"].notna() &
        df["finish_position"].notna()
    ].copy()

    rank_bucket = np.select(
        [
            df["runner_rank_hist_v1"] == 1,
            df["runner_rank_hist_v1"] == 2,
            df["runner_rank_hist_v1"] == 3,
            df["runner_rank_hist_v1"].between(4,5),
            df["runner_rank_hist_v1"].between(6,10)
        ],
        [
            "RANK_1",
            "RANK_2",
            "RANK_3",
            "RANK_4_5",
            "RANK_6_10"
        ],
        default="RANK_11_PLUS"
    )

    df["rank_bucket_v1"] = rank_bucket

    score_band = pd.cut(
        df["runner_score_hist_v1"],
        bins=[-999,40,45,50,55,60,65,70,75,80,999],
        labels=[
            "<40",
            "40-44",
            "45-49",
            "50-54",
            "55-59",
            "60-64",
            "65-69",
            "70-74",
            "75-79",
            "80+"
        ]
    )

    df["score_band_v1"] = score_band

    rank = (
        df.groupby("rank_bucket_v1")
        .apply(roi_group)
        .reset_index()
    )

    rank.to_csv(RANK,index=False)

    gov = (
        df.groupby("governance_band_hist_v1")
        .apply(roi_group)
        .reset_index()
    )

    gov.to_csv(GOV,index=False)

    score = (
        df.groupby("score_band_v1")
        .apply(roi_group)
        .reset_index()
    )

    score.to_csv(SCORE,index=False)

    races = []

    for race_key, r in df.groupby("race_key"):

        r = r.sort_values("runner_rank_hist_v1")

        winners = r[r["finish_position"] == 1]
        if len(winners) == 0:
            continue

        winner_rank = int(winners["runner_rank_hist_v1"].iloc[0])

        top3 = int(winner_rank <= 3)
        top5 = int(winner_rank <= 5)
        top10 = int(winner_rank <= 10)

        finishers = (
            r.sort_values("finish_position")
            .head(3)
        )

        top5_ranks = set(
            r.sort_values("runner_rank_hist_v1")
            .head(5)
            .index
        )

        top8_ranks = set(
            r.sort_values("runner_rank_hist_v1")
            .head(8)
            .index
        )

        trifecta_top5 = int(
            len(set(finishers.index) & top5_ranks) == 3
        )

        trifecta_top8 = int(
            len(set(finishers.index) & top8_ranks) == 3
        )

        races.append({
            "race_key": race_key,
            "winner_top3": top3,
            "winner_top5": top5,
            "winner_top10": top10,
            "trifecta_top5": trifecta_top5,
            "trifecta_top8": trifecta_top8
        })

    capture = pd.DataFrame(races)

    capture.to_csv(CAPTURE,index=False)

    summary = pd.DataFrame([
        {"metric":"built_at","value":datetime.now().isoformat(timespec="seconds")},
        {"metric":"runners","value":len(df)},
        {"metric":"races","value":df["race_key"].nunique()},
        {"metric":"winner_top3_rate","value":round(capture["winner_top3"].mean(),4)},
        {"metric":"winner_top5_rate","value":round(capture["winner_top5"].mean(),4)},
        {"metric":"winner_top10_rate","value":round(capture["winner_top10"].mean(),4)},
        {"metric":"trifecta_top5_rate","value":round(capture["trifecta_top5"].mean(),4)},
        {"metric":"trifecta_top8_rate","value":round(capture["trifecta_top8"].mean(),4)}
    ])

    summary.to_csv(SUMMARY,index=False)

    print("[HISTORICAL_VALIDATION_SUITE_V1] COMPLETE")
    print(f"runners={len(df)}")
    print(f"races={df['race_key'].nunique()}")

if __name__ == "__main__":
    main()
