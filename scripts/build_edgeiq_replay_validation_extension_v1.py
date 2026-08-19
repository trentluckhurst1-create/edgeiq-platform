import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

REPLAY = DATA / "edgeiq_historical_replay_v1.csv"

SP_COVERAGE = DATA / "edgeiq_replay_sp_coverage_by_finish_v1.csv"
CONTENDER = DATA / "edgeiq_replay_contender_capture_detail_v1.csv"
FAIR = DATA / "edgeiq_fair_price_replay_v1.csv"
FAIR_SUMMARY = DATA / "edgeiq_fair_price_replay_v1_summary.csv"
FAIR_BY_BAND = DATA / "edgeiq_fair_price_replay_v1_by_overlay_band.csv"

def num(s):
    return pd.to_numeric(s, errors="coerce")

def overlay_band(x):
    if pd.isna(x):
        return "NO_SP"
    if x >= 100:
        return "100%+"
    if x >= 50:
        return "50-100%"
    if x >= 25:
        return "25-50%"
    if x >= 15:
        return "15-25%"
    if x >= 8:
        return "8-15%"
    if x >= 0:
        return "0-8%"
    return "UNDERLAY"

def main():
    df = pd.read_csv(REPLAY)

    df["finish_position"] = num(df["finish_position"])
    df["runner_rank"] = num(df["runner_rank"])
    df["runner_score"] = num(df["runner_score"])
    df["sp_num"] = num(df["sp_num"]) if "sp_num" in df.columns else np.nan

    df["has_sp"] = df["sp_num"].notna() & (df["sp_num"] > 1)
    df["won"] = df["finish_position"].eq(1).astype(int)
    df["placed"] = df["finish_position"].le(3).astype(int)

    # 1. SP coverage
    df["finish_bucket"] = np.select(
        [
            df["finish_position"].eq(1),
            df["finish_position"].eq(2),
            df["finish_position"].eq(3),
            df["finish_position"].between(4, 10),
        ],
        ["1_WINNER", "2_SECOND", "3_THIRD", "4_10"],
        default="11_PLUS"
    )

    sp_cov = df.groupby("finish_bucket").agg(
        runners=("horse", "count"),
        sp_rows=("has_sp", "sum"),
        avg_sp=("sp_num", "mean"),
        median_sp=("sp_num", "median"),
    ).reset_index()

    sp_cov["sp_coverage"] = (sp_cov["sp_rows"] / sp_cov["runners"]).round(4)
    sp_cov["avg_sp"] = sp_cov["avg_sp"].round(2)
    sp_cov["median_sp"] = sp_cov["median_sp"].round(2)
    sp_cov.to_csv(SP_COVERAGE, index=False)

    # 2. Contender capture detail
    race_rows = []
    for race_key, g in df.groupby("race_key"):
        g_rank = g.sort_values("runner_rank")
        g_fin = g.sort_values("finish_position")

        winner = g_fin[g_fin["finish_position"].eq(1)]
        if len(winner) == 0:
            continue

        winner_rank = int(winner["runner_rank"].iloc[0])
        winner_score = float(winner["runner_score"].iloc[0])

        top3_set = set(g_rank.head(3).index)
        top5_set = set(g_rank.head(5).index)
        top8_set = set(g_rank.head(8).index)
        top10_set = set(g_rank.head(10).index)

        first3_set = set(g_fin.head(3).index)
        first4_set = set(g_fin.head(4).index)

        race_rows.append({
            "race_key": race_key,
            "meeting_date": winner["meeting_date"].iloc[0],
            "track": winner["track"].iloc[0],
            "race_no": winner["race_no"].iloc[0],
            "winner": winner["horse"].iloc[0],
            "winner_rank": winner_rank,
            "winner_score": round(winner_score, 3),
            "winner_top1": int(winner_rank <= 1),
            "winner_top3": int(winner_rank <= 3),
            "winner_top5": int(winner_rank <= 5),
            "winner_top8": int(winner_rank <= 8),
            "winner_top10": int(winner_rank <= 10),
            "first3_in_top5_count": len(first3_set & top5_set),
            "first3_in_top8_count": len(first3_set & top8_set),
            "first4_in_top8_count": len(first4_set & top8_set),
            "trifecta_all_top5": int(len(first3_set & top5_set) == 3),
            "trifecta_all_top8": int(len(first3_set & top8_set) == 3),
            "first4_all_top8": int(len(first4_set & top8_set) == 4),
        })

    contender = pd.DataFrame(race_rows)
    contender.to_csv(CONTENDER, index=False)

    # 3. Fair price replay from rank probabilities
    # Empirical win probability by rank bucket using all replay rows.
    df["rank_bucket"] = np.select(
        [
            df["runner_rank"].eq(1),
            df["runner_rank"].eq(2),
            df["runner_rank"].eq(3),
            df["runner_rank"].between(4,5),
            df["runner_rank"].between(6,10),
        ],
        ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10"],
        default="RANK_11_PLUS"
    )

    rank_win = df.groupby("rank_bucket")["won"].mean().to_dict()
    fallback = df["won"].mean()

    df["empirical_win_prob"] = df["rank_bucket"].map(rank_win).fillna(fallback)

    # Blend empirical rank probability with within-race score softmax.
    df["score_weight"] = np.exp((df["runner_score"].fillna(0) - 45) / 18)
    df["score_prob"] = df["score_weight"] / df.groupby("race_key")["score_weight"].transform("sum")

    df["raw_prob"] = (0.55 * df["score_prob"]) + (0.45 * df["empirical_win_prob"])
    df["fair_prob_replay_v1"] = df["raw_prob"] / df.groupby("race_key")["raw_prob"].transform("sum")
    df["fair_price_replay_v1"] = (1 / df["fair_prob_replay_v1"]).round(2)

    df["overlay_pct_replay_v1"] = np.where(
        df["has_sp"],
        ((df["sp_num"] / df["fair_price_replay_v1"]) - 1) * 100,
        np.nan
    ).round(1)

    df["overlay_band_replay_v1"] = df["overlay_pct_replay_v1"].apply(overlay_band)

    priced = df[df["has_sp"]].copy()
    priced["profit_1u"] = np.where(priced["won"].eq(1), priced["sp_num"] - 1, -1)

    fair_cols = [
        "meeting_date","track","race_no","horse","race_key",
        "runner_rank","runner_score","rank_bucket",
        "finish_position","won","sp_num",
        "fair_prob_replay_v1","fair_price_replay_v1",
        "overlay_pct_replay_v1","overlay_band_replay_v1",
    ]
    df[[c for c in fair_cols if c in df.columns]].to_csv(FAIR, index=False)

    by_band = priced.groupby("overlay_band_replay_v1").agg(
        bets=("horse", "count"),
        wins=("won", "sum"),
        profit_1u=("profit_1u", "sum"),
        avg_sp=("sp_num", "mean"),
        avg_fair=("fair_price_replay_v1", "mean"),
        avg_overlay=("overlay_pct_replay_v1", "mean"),
    ).reset_index()

    by_band["strike_rate"] = (by_band["wins"] / by_band["bets"]).round(4)
    by_band["roi"] = (by_band["profit_1u"] / by_band["bets"]).round(4)
    for c in ["profit_1u","avg_sp","avg_fair","avg_overlay"]:
        by_band[c] = by_band[c].round(2)

    by_band.to_csv(FAIR_BY_BAND, index=False)

    summary = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "replay_rows", "value": len(df)},
        {"metric": "races", "value": df["race_key"].nunique()},
        {"metric": "sp_rows", "value": int(df["has_sp"].sum())},
        {"metric": "sp_coverage", "value": round(df["has_sp"].mean(), 4)},
        {"metric": "winner_top3", "value": round(contender["winner_top3"].mean(), 4)},
        {"metric": "winner_top5", "value": round(contender["winner_top5"].mean(), 4)},
        {"metric": "winner_top8", "value": round(contender["winner_top8"].mean(), 4)},
        {"metric": "winner_top10", "value": round(contender["winner_top10"].mean(), 4)},
        {"metric": "trifecta_all_top5", "value": round(contender["trifecta_all_top5"].mean(), 4)},
        {"metric": "trifecta_all_top8", "value": round(contender["trifecta_all_top8"].mean(), 4)},
        {"metric": "first4_all_top8", "value": round(contender["first4_all_top8"].mean(), 4)},
    ])

    summary.to_csv(FAIR_SUMMARY, index=False)

    print("[REPLAY_VALIDATION_EXTENSION_V1] COMPLETE")
    print(f"rows={len(df)}")
    print(f"races={df['race_key'].nunique()}")
    print(f"sp_rows={int(df['has_sp'].sum())}")
    print(f"wrote={SP_COVERAGE}")
    print(f"wrote={CONTENDER}")
    print(f"wrote={FAIR}")
    print(f"summary={FAIR_SUMMARY}")

if __name__ == "__main__":
    main()
