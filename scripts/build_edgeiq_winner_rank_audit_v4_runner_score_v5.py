from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SCORE = DATA / "edgeiq_runner_score_v5.csv"
TAB = DATA / "edgeiq_tab_vic_racecards_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUT = DATA / "edgeiq_winner_rank_audit_v4_runner_score_v5.csv"
SUMMARY = DATA / "edgeiq_winner_rank_audit_v4_runner_score_v5_summary.csv"

BASELINE = {
    "winner_rank1_rate": 0.1176,
    "winner_top3_rate": 0.4706,
    "winner_top5_rate": 0.5882,
    "winner_top10_rate": 0.9412,
    "avg_winner_rank": 4.706,
}


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


def pos_num(value: object) -> float:
    text = upper_text(value)
    if text in {"", "NAN", "NONE", "SCR", "SCRATCHED"}:
        return np.nan
    match = re.search(r"\d+", text)
    return float(match.group(0)) if match else np.nan


def rank_bucket(rank_value: object) -> str:
    if pd.isna(rank_value):
        return "NO_RANK"
    rank_int = int(rank_value)
    if rank_int == 1:
        return "RANK_1"
    if rank_int == 2:
        return "RANK_2"
    if rank_int == 3:
        return "RANK_3"
    if rank_int <= 5:
        return "RANK_4_5"
    if rank_int <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def load_score() -> pd.DataFrame:
    if not SCORE.exists():
        raise FileNotFoundError(f"Missing runner score v5 file: {SCORE}")

    df = pd.read_csv(SCORE, low_memory=False)
    df["meeting_date"] = df["meeting_date"].astype(str).str.slice(0, 10)
    df["join_track"] = df["track"].map(norm_track)
    df["join_race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["join_horse"] = df["horse"].map(canon_horse)
    df["runner_score_v5"] = pd.to_numeric(df["runner_score_v5"], errors="coerce")
    df["runner_rank_v5"] = pd.to_numeric(df["runner_rank_v5"], errors="coerce")
    df["race_key_v5"] = (
        df["meeting_date"].astype(str) + "|" + df["join_track"].astype(str) + "|" + df["join_race_no"].astype(str)
    )
    return df


def load_tab() -> pd.DataFrame:
    if not TAB.exists():
        raise FileNotFoundError(f"Missing TAB racecards file: {TAB}")

    df = pd.read_csv(TAB, low_memory=False)
    df["meeting_date"] = df["meeting_date"].astype(str).str.slice(0, 10)
    df["join_track"] = df["meeting_name"].map(norm_track)
    df["join_race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["join_horse"] = df["horse"].map(canon_horse)
    keep = ["meeting_date", "join_track", "join_race_no", "join_horse"]
    return df[keep].drop_duplicates(keep, keep="last")


def load_results() -> pd.DataFrame:
    if not RESULTS.exists():
        raise FileNotFoundError(f"Missing results warehouse file: {RESULTS}")

    df = pd.read_csv(RESULTS, low_memory=False)
    horse_col = "horseName" if "horseName" in df.columns else "horse"
    finish_col = "finishPosition" if "finishPosition" in df.columns else "finish_position"

    df["meeting_date"] = df["meeting_date"].astype(str).str.slice(0, 10)
    df["join_track"] = df["track"].map(norm_track)
    df["join_race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["join_horse"] = df[horse_col].map(canon_horse)
    df["finish_position"] = df[finish_col].apply(pos_num)

    keep = ["meeting_date", "join_track", "join_race_no", "join_horse", "finish_position"]
    return df[keep].drop_duplicates(keep, keep="last")


def main() -> None:
    score = load_score()
    tab = load_tab()
    results = load_results()

    current = score.merge(
        tab,
        on=["meeting_date", "join_track", "join_race_no", "join_horse"],
        how="inner",
    )
    if current.empty:
        raise RuntimeError("No runner_score_v5 rows matched the current TAB racecards.")

    current_card_races = int(current["race_key_v5"].nunique())

    current = current.merge(
        results,
        on=["meeting_date", "join_track", "join_race_no", "join_horse"],
        how="left",
    )

    matched = current[current["finish_position"].notna()].copy()
    matched_result_races = int(matched["race_key_v5"].nunique())
    winners = matched[matched["finish_position"].eq(1)].copy()
    if winners.empty:
        raise RuntimeError("No winners matched between runner_score_v5 and Racing.com results.")

    winner_counts = winners.groupby("race_key_v5").size()
    unique_winner_races = int(winner_counts.shape[0])
    dead_heat_races = int((winner_counts > 1).sum())
    missing_result_races = int(current_card_races - matched_result_races)

    top_ranked = matched.sort_values(
        ["race_key_v5", "runner_rank_v5", "runner_score_v5", "horse"],
        ascending=[True, True, False, True],
    ).groupby("race_key_v5").head(1).copy()

    winners = winners.rename(columns={
        "horse": "winner",
        "runner_rank_v5": "winner_runner_rank_v5",
        "runner_score_v5": "winner_runner_score_v5",
        "runner_score_v4": "winner_runner_score_v4",
        "pace_pressure_band_v1": "winner_pace_pressure_band_v1",
        "tactical_style": "winner_tactical_style",
        "pace_advantage_score_v1": "winner_pace_advantage_score_v1",
        "pace_advantage_band_v1": "winner_pace_advantage_band_v1",
    })
    top_ranked = top_ranked[[
        "race_key_v5",
        "horse",
        "runner_rank_v5",
        "runner_score_v5",
        "runner_score_v4",
        "finish_position",
        "pace_pressure_band_v1",
        "tactical_style",
        "pace_advantage_score_v1",
        "pace_advantage_band_v1",
    ]].rename(columns={
        "horse": "top_ranked_horse_v5",
        "runner_rank_v5": "top_ranked_runner_rank_v5",
        "runner_score_v5": "top_ranked_runner_score_v5",
        "runner_score_v4": "top_ranked_runner_score_v4",
        "finish_position": "top_ranked_finish_position",
        "pace_pressure_band_v1": "top_ranked_pace_pressure_band_v1",
        "tactical_style": "top_ranked_tactical_style",
        "pace_advantage_score_v1": "top_ranked_pace_advantage_score_v1",
        "pace_advantage_band_v1": "top_ranked_pace_advantage_band_v1",
    })

    out = winners.merge(top_ranked, on="race_key_v5", how="left")
    out["winner_top1"] = out["winner_runner_rank_v5"].eq(1).astype(int)
    out["winner_top3"] = out["winner_runner_rank_v5"].le(3).astype(int)
    out["winner_top5"] = out["winner_runner_rank_v5"].le(5).astype(int)
    out["winner_top10"] = out["winner_runner_rank_v5"].le(10).astype(int)
    out["winner_rank_bucket_v5"] = out["winner_runner_rank_v5"].apply(rank_bucket)
    out["score_gap_top_minus_winner_v5"] = (
        out["top_ranked_runner_score_v5"] - out["winner_runner_score_v5"]
    ).round(3)

    keep = [
        "meeting_date",
        "track",
        "race_no",
        "race_key_v5",
        "winner",
        "winner_runner_rank_v5",
        "winner_runner_score_v5",
        "winner_runner_score_v4",
        "winner_pace_pressure_band_v1",
        "winner_tactical_style",
        "winner_pace_advantage_score_v1",
        "winner_pace_advantage_band_v1",
        "top_ranked_horse_v5",
        "top_ranked_runner_rank_v5",
        "top_ranked_runner_score_v5",
        "top_ranked_runner_score_v4",
        "top_ranked_finish_position",
        "top_ranked_pace_pressure_band_v1",
        "top_ranked_tactical_style",
        "top_ranked_pace_advantage_score_v1",
        "top_ranked_pace_advantage_band_v1",
        "score_gap_top_minus_winner_v5",
        "winner_rank_bucket_v5",
        "winner_top1",
        "winner_top3",
        "winner_top5",
        "winner_top10",
    ]
    out = out[[col for col in keep if col in out.columns]].sort_values(["meeting_date", "track", "race_no", "winner"]).reset_index(drop=True)
    out.to_csv(OUT, index=False)

    total_winner_rows = len(out)
    current_metrics = {
        "winner_rank1_rate": round(float(out["winner_top1"].mean()), 4) if total_winner_rows else 0.0,
        "winner_top3_rate": round(float(out["winner_top3"].mean()), 4) if total_winner_rows else 0.0,
        "winner_top5_rate": round(float(out["winner_top5"].mean()), 4) if total_winner_rows else 0.0,
        "winner_top10_rate": round(float(out["winner_top10"].mean()), 4) if total_winner_rows else 0.0,
        "avg_winner_rank": round(float(out["winner_runner_rank_v5"].mean()), 3) if total_winner_rows else 0.0,
    }

    comparison_rows = [
        {"metric": "races_audited", "value": total_winner_rows},
        {"metric": "winner_rows", "value": total_winner_rows},
        {"metric": "unique_races_audited", "value": unique_winner_races},
        {"metric": "current_card_races", "value": current_card_races},
        {"metric": "matched_result_races", "value": matched_result_races},
        {"metric": "missing_result_races", "value": missing_result_races},
        {"metric": "dead_heat_races", "value": dead_heat_races},
        {"metric": "winner_rank1_count", "value": int(out["winner_top1"].sum())},
        {"metric": "winner_top3_count", "value": int(out["winner_top3"].sum())},
        {"metric": "winner_top5_count", "value": int(out["winner_top5"].sum())},
        {"metric": "winner_top10_count", "value": int(out["winner_top10"].sum())},
        {"metric": "winner_rank1_rate", "value": current_metrics["winner_rank1_rate"]},
        {"metric": "winner_top3_rate", "value": current_metrics["winner_top3_rate"]},
        {"metric": "winner_top5_rate", "value": current_metrics["winner_top5_rate"]},
        {"metric": "winner_top10_rate", "value": current_metrics["winner_top10_rate"]},
        {"metric": "avg_winner_rank", "value": current_metrics["avg_winner_rank"]},
        {"metric": "avg_score_gap_top_minus_winner_v5", "value": round(float(out["score_gap_top_minus_winner_v5"].mean()), 3) if total_winner_rows else 0.0},
    ]

    improved_flags = []
    for metric, baseline_value in BASELINE.items():
        current_value = current_metrics[metric]
        delta = round(current_value - baseline_value, 4) if metric != "avg_winner_rank" else round(current_value - baseline_value, 3)
        improved = current_value > baseline_value if metric != "avg_winner_rank" else current_value < baseline_value
        improved_flags.append(bool(improved))
        comparison_rows.append({"metric": f"baseline::{metric}", "value": baseline_value})
        comparison_rows.append({"metric": f"delta_vs_baseline::{metric}", "value": delta})
        comparison_rows.append({"metric": f"improved_vs_baseline::{metric}", "value": improved})

    improved_metric_count = int(sum(improved_flags))
    comparison_rows.append({"metric": "improved_metric_count", "value": improved_metric_count})
    comparison_rows.append({"metric": "v5_improved_current_day_audit", "value": improved_metric_count >= 3})

    pd.DataFrame(comparison_rows).to_csv(SUMMARY, index=False)

    print("[EDGEIQ_WINNER_RANK_AUDIT_V4_RUNNER_SCORE_V5] COMPLETE")
    print(f"winner_rows={total_winner_rows}")
    print(f"unique_races_audited={unique_winner_races}")
    print(f"current_card_races={current_card_races}")
    print(f"matched_result_races={matched_result_races}")
    print(f"missing_result_races={missing_result_races}")
    print(f"dead_heat_races={dead_heat_races}")
    print(f"winner_rank1_rate={current_metrics['winner_rank1_rate']}")
    print(f"winner_top3_rate={current_metrics['winner_top3_rate']}")
    print(f"winner_top5_rate={current_metrics['winner_top5_rate']}")
    print(f"winner_top10_rate={current_metrics['winner_top10_rate']}")
    print(f"avg_winner_rank={current_metrics['avg_winner_rank']}")
    print(f"v5_improved_current_day_audit={improved_metric_count >= 3}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
