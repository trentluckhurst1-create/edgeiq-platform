from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"
REPLAY = DATA / "edgeiq_historical_replay_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

SUMMARY = DATA / "edgeiq_sp_bias_audit_v1_summary.csv"
BY_FINISH_POSITION = DATA / "edgeiq_sp_bias_audit_v1_by_finish_position.csv"
BY_RANK = DATA / "edgeiq_sp_bias_audit_v1_by_rank.csv"
BY_SCORE_BAND = DATA / "edgeiq_sp_bias_audit_v1_by_score_band.csv"
BY_GOVERNANCE = DATA / "edgeiq_sp_bias_audit_v1_by_governance.csv"
BY_TRACK = DATA / "edgeiq_sp_bias_audit_v1_by_track.csv"
BY_YEAR = DATA / "edgeiq_sp_bias_audit_v1_by_year.csv"
BY_FINISH_BUCKET = DATA / "edgeiq_sp_bias_audit_v1_by_finish_bucket.csv"

RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]
SCORE_BAND_ORDER = ["LT_40", "40_44", "45_49", "50_54", "55_59", "60_64", "65_69", "70_74", "75_79", "80_PLUS"]
FINISH_BUCKET_ORDER = ["1_WINNER", "2_SECOND", "3_THIRD", "4_10", "11_PLUS"]
WARNING_TEXT = "Do not use Racing.com SP ROI as final profitability if biased."


def parse_float(value: object) -> float:
    if pd.isna(value):
        return math.nan
    text = str(value).replace("$", "").replace(",", "").replace("kg", "").strip()
    if text == "":
        return math.nan
    try:
        return float(text)
    except ValueError:
        return math.nan


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


def score_band(score_value: object) -> str:
    score = pd.to_numeric(score_value, errors="coerce")
    if pd.isna(score):
        return "UNKNOWN"
    if score < 40:
        return "LT_40"
    if score < 45:
        return "40_44"
    if score < 50:
        return "45_49"
    if score < 55:
        return "50_54"
    if score < 60:
        return "55_59"
    if score < 65:
        return "60_64"
    if score < 70:
        return "65_69"
    if score < 75:
        return "70_74"
    if score < 80:
        return "75_79"
    return "80_PLUS"


def finish_bucket(finish_position: object) -> str:
    pos = pd.to_numeric(finish_position, errors="coerce")
    if pd.isna(pos):
        return "UNKNOWN"
    if pos == 1:
        return "1_WINNER"
    if pos == 2:
        return "2_SECOND"
    if pos == 3:
        return "3_THIRD"
    if pos <= 10:
        return "4_10"
    return "11_PLUS"


def coverage(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def grouped_metrics(df: pd.DataFrame, group_col: str, sort_order: list[str] | None = None) -> pd.DataFrame:
    total_winners = int(df["won"].sum())
    grouped = (
        df.groupby(group_col, dropna=False)
        .agg(
            runners=(group_col, "size"),
            sp_rows=("has_sp", "sum"),
            winners=("won", "sum"),
            winner_sp_rows=("winner_has_sp", "sum"),
            placed=("placed", "sum"),
            placed_sp_rows=("placed_has_sp", "sum"),
            avg_sp=("sp_num", "mean"),
            median_sp=("sp_num", "median"),
        )
        .reset_index()
    )

    grouped["sp_coverage"] = grouped.apply(lambda row: coverage(row["sp_rows"], row["runners"]), axis=1)
    grouped["winner_share"] = grouped.apply(lambda row: coverage(row["winners"], total_winners), axis=1)
    grouped["winner_sp_coverage"] = grouped.apply(lambda row: coverage(row["winner_sp_rows"], row["winners"]), axis=1)
    grouped["placed_sp_coverage"] = grouped.apply(lambda row: coverage(row["placed_sp_rows"], row["placed"]), axis=1)

    for col in ["sp_coverage", "winner_share", "winner_sp_coverage", "placed_sp_coverage"]:
        grouped[col] = grouped[col].round(4)
    for col in ["avg_sp", "median_sp"]:
        grouped[col] = pd.to_numeric(grouped[col], errors="coerce").round(3)

    if sort_order is not None:
        grouped["sort_order"] = grouped[group_col].map({value: idx for idx, value in enumerate(sort_order, start=1)}).fillna(999999)
        grouped = grouped.sort_values(["sort_order", group_col]).reset_index(drop=True)
    else:
        grouped = grouped.sort_values(group_col).reset_index(drop=True)

    return grouped


def main() -> None:
    for path in [SETTLED, REPLAY, RESULTS]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input file: {path}")

    settled = pd.read_csv(SETTLED, low_memory=False)
    replay = pd.read_csv(REPLAY, low_memory=False)
    results = pd.read_csv(RESULTS, low_memory=False)

    settled["meeting_date"] = settled["meeting_date"].astype(str).str.slice(0, 10)
    settled["year"] = pd.to_datetime(settled["meeting_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    settled["runner_rank"] = pd.to_numeric(settled["runner_rank"], errors="coerce")
    settled["runner_score"] = pd.to_numeric(settled["runner_score"], errors="coerce")
    settled["finish_position"] = pd.to_numeric(settled["finish_position"], errors="coerce")
    settled["won"] = settled["finish_position"].eq(1).astype(int)
    settled["placed"] = settled["finish_position"].le(3).fillna(False).astype(int)

    if "sp_num_settled" in settled.columns:
        settled["sp_num"] = pd.to_numeric(settled["sp_num_settled"], errors="coerce")
    else:
        settled["sp_num"] = settled["sp"].apply(parse_float)

    settled["has_sp"] = settled["sp_num"].gt(1)
    settled["winner_has_sp"] = (settled["won"].eq(1) & settled["has_sp"]).astype(int)
    settled["placed_has_sp"] = (settled["placed"].eq(1) & settled["has_sp"]).astype(int)
    settled["rank_bucket_audit"] = settled["runner_rank"].apply(rank_bucket)
    settled["score_band_audit"] = settled["runner_score"].apply(score_band)
    settled["governance_audit"] = settled["projection_status_v6"].fillna("UNKNOWN").astype(str)
    settled["finish_bucket_audit"] = settled["finish_position"].apply(finish_bucket)
    settled["finish_position_label"] = settled["finish_position"].apply(lambda value: "UNKNOWN" if pd.isna(value) else str(int(value)))
    settled["track_audit"] = settled["track"].fillna("UNKNOWN").astype(str)

    replay_rows = len(replay)
    settled_rows = len(settled)
    if replay_rows != settled_rows:
        raise RuntimeError(f"Replay row mismatch: replay={replay_rows} settled={settled_rows}")

    total_rows = int(len(settled))
    total_races = int(settled["race_key"].nunique())
    total_sp_rows = int(settled["has_sp"].sum())
    winner_rows = int(settled["won"].sum())
    winner_sp_rows = int(settled["winner_has_sp"].sum())
    placed_rows = int(settled["placed"].sum())
    placed_sp_rows = int(settled["placed_has_sp"].sum())
    non_placed_rows = int(total_rows - placed_rows)
    non_placed_sp_rows = int(settled[settled["placed"].eq(0) & settled["has_sp"]].shape[0])

    total_sp_coverage = coverage(total_sp_rows, total_rows)
    winner_sp_coverage = coverage(winner_sp_rows, winner_rows)
    placed_sp_coverage = coverage(placed_sp_rows, placed_rows)
    non_placed_sp_coverage = coverage(non_placed_sp_rows, non_placed_rows)
    conclusion_flag = "SP_SAMPLE_BIASED" if (winner_sp_coverage - total_sp_coverage) > 0.20 else "SP_SAMPLE_ACCEPTABLE"

    summary_rows = [
        {"metric": "total_rows", "value": total_rows},
        {"metric": "total_races", "value": total_races},
        {"metric": "total_sp_rows", "value": total_sp_rows},
        {"metric": "total_sp_coverage", "value": round(total_sp_coverage, 4)},
        {"metric": "winner_rows", "value": winner_rows},
        {"metric": "winner_sp_rows", "value": winner_sp_rows},
        {"metric": "winner_sp_coverage", "value": round(winner_sp_coverage, 4)},
        {"metric": "placed_rows", "value": placed_rows},
        {"metric": "placed_sp_rows", "value": placed_sp_rows},
        {"metric": "placed_sp_coverage", "value": round(placed_sp_coverage, 4)},
        {"metric": "non_placed_rows", "value": non_placed_rows},
        {"metric": "non_placed_sp_rows", "value": non_placed_sp_rows},
        {"metric": "non_placed_sp_coverage", "value": round(non_placed_sp_coverage, 4)},
        {"metric": "conclusion_flag", "value": conclusion_flag},
        {"metric": "warning", "value": WARNING_TEXT},
        {"metric": "settled_rows", "value": settled_rows},
        {"metric": "baseline_replay_rows", "value": replay_rows},
        {"metric": "results_rows_source", "value": int(len(results))},
        {"metric": "results_sp_nonnull_source", "value": int(results["sp"].notna().sum()) if "sp" in results.columns else 0},
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    by_finish_position = grouped_metrics(settled, "finish_position_label")
    by_finish_position.to_csv(BY_FINISH_POSITION, index=False)

    by_rank = grouped_metrics(settled, "rank_bucket_audit", RANK_BUCKET_ORDER)
    by_rank.to_csv(BY_RANK, index=False)

    by_score_band = grouped_metrics(settled, "score_band_audit", SCORE_BAND_ORDER)
    by_score_band.to_csv(BY_SCORE_BAND, index=False)

    by_governance = grouped_metrics(settled, "governance_audit")
    by_governance.to_csv(BY_GOVERNANCE, index=False)

    by_track = grouped_metrics(settled, "track_audit")
    by_track.to_csv(BY_TRACK, index=False)

    by_year = grouped_metrics(settled, "year")
    by_year.to_csv(BY_YEAR, index=False)

    by_finish_bucket = grouped_metrics(settled, "finish_bucket_audit", FINISH_BUCKET_ORDER)
    by_finish_bucket.to_csv(BY_FINISH_BUCKET, index=False)

    print("[EDGEIQ_SP_BIAS_AUDIT_V1] COMPLETE")
    print(f"total_rows={total_rows}")
    print(f"total_races={total_races}")
    print(f"total_sp_rows={total_sp_rows}")
    print(f"total_sp_coverage={round(total_sp_coverage, 4)}")
    print(f"winner_sp_coverage={round(winner_sp_coverage, 4)}")
    print(f"conclusion_flag={conclusion_flag}")
    print(f"summary={SUMMARY}")
    print(f"by_finish_bucket={BY_FINISH_BUCKET}")
    print(f"by_rank={BY_RANK}")
    print(f"by_year={BY_YEAR}")


if __name__ == "__main__":
    main()
