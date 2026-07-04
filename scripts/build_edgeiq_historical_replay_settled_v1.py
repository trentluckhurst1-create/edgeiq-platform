from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

REPLAY = DATA / "edgeiq_historical_replay_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUT = DATA / "edgeiq_historical_replay_settled_v1.csv"
SUMMARY = DATA / "edgeiq_historical_replay_settled_v1_summary.csv"
ROI_BY_RANK = DATA / "edgeiq_historical_replay_settled_v1_roi_by_rank.csv"
ROI_BY_SCORE_BAND = DATA / "edgeiq_historical_replay_settled_v1_roi_by_score_band.csv"
ROI_BY_GOVERNANCE = DATA / "edgeiq_historical_replay_settled_v1_roi_by_governance.csv"


RANK_ORDER = {
    "RANK_1": 1,
    "RANK_2": 2,
    "RANK_3": 3,
    "RANK_4_5": 4,
    "RANK_6_10": 5,
    "RANK_11_PLUS": 6,
}

SCORE_BAND_ORDER = {
    "LT_40": 1,
    "40_44": 2,
    "45_49": 3,
    "50_54": 4,
    "55_59": 5,
    "60_64": 6,
    "65_69": 7,
    "70_74": 8,
    "75_79": 9,
    "80_PLUS": 10,
}

GOVERNANCE_ORDER = {
    "PROVEN": 1,
    "PROVEN_UNCLEAR_HISTORY": 2,
    "LIMITED_DATA_3_4_STARTS": 3,
    "LIMITED_DATA_2_STARTS": 4,
    "LIMITED_DATA_1_START": 5,
    "IMPORT_UNKNOWN": 6,
    "FIRST_STARTER_OR_UNKNOWN": 7,
    "UNKNOWN": 99,
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


def parse_float(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).replace("$", "").replace(",", "").replace("kg", "").strip()
    text = text.replace("-", "-")
    if text == "":
        return np.nan
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return np.nan
    try:
        return float(match.group(0))
    except ValueError:
        return np.nan


def rank_bucket(value: object) -> str:
    rank_value = pd.to_numeric(value, errors="coerce")
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


def score_band(value: object) -> str:
    score_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(score_value):
        return "UNKNOWN"
    if score_value < 40:
        return "LT_40"
    if score_value < 45:
        return "40_44"
    if score_value < 50:
        return "45_49"
    if score_value < 55:
        return "50_54"
    if score_value < 60:
        return "55_59"
    if score_value < 65:
        return "60_64"
    if score_value < 70:
        return "65_69"
    if score_value < 75:
        return "70_74"
    if score_value < 80:
        return "75_79"
    return "80_PLUS"


def add_sort_key(df: pd.DataFrame, col: str, mapping: dict[str, int], sort_col: str) -> pd.DataFrame:
    out = df.copy()
    out[sort_col] = out[col].map(mapping).fillna(999).astype(int)
    return out


def compute_roi_table(df: pd.DataFrame, group_col: str, output_col: str) -> pd.DataFrame:
    work = df.copy()
    work["sp_num"] = work["sp_settled"].map(parse_float)
    work = work[work["sp_num"].gt(1)].copy()
    if work.empty:
        return pd.DataFrame(columns=[output_col, "bets", "winners", "strike_rate", "avg_sp", "profit_1u", "roi"])

    work["profit_1u"] = np.where(work["won"] == 1, work["sp_num"] - 1.0, -1.0)

    table = (
        work.groupby(group_col, dropna=False)
        .agg(
            bets=(group_col, "count"),
            winners=("won", "sum"),
            strike_rate=("won", "mean"),
            avg_sp=("sp_num", "mean"),
            profit_1u=("profit_1u", "sum"),
        )
        .reset_index()
        .rename(columns={group_col: output_col})
    )
    table["roi"] = np.where(table["bets"] > 0, table["profit_1u"] / table["bets"], np.nan)
    for col in ["strike_rate", "avg_sp", "profit_1u", "roi"]:
        table[col] = pd.to_numeric(table[col], errors="coerce").round(4)
    return table


def main() -> None:
    if not REPLAY.exists():
        raise FileNotFoundError(f"Missing replay file: {REPLAY}")
    if not RESULTS.exists():
        raise FileNotFoundError(f"Missing results warehouse: {RESULTS}")

    replay = pd.read_csv(REPLAY, low_memory=False)
    results = pd.read_csv(RESULTS, low_memory=False)

    replay_required = {"meeting_date", "track", "race_no", "horse", "runner_score", "runner_rank", "won"}
    results_required = {"meeting_date", "track", "race_no", "horseName", "sp"}

    replay_missing = sorted(replay_required.difference(replay.columns))
    results_missing = sorted(results_required.difference(results.columns))
    if replay_missing:
        raise ValueError(f"Replay missing columns: {replay_missing}")
    if results_missing:
        raise ValueError(f"Results missing columns: {results_missing}")

    replay["meeting_date"] = replay["meeting_date"].astype(str).str.slice(0, 10)
    replay["track_norm_join"] = replay["track"].map(norm_track)
    replay["race_no_join"] = pd.to_numeric(replay["race_no"], errors="coerce").astype("Int64")
    replay["horse_join"] = replay["horse"].map(canon_horse)
    replay["rank_bucket"] = replay["runner_rank"].map(rank_bucket)
    replay["score_band"] = replay["runner_score"].map(score_band)
    replay["governance"] = replay.get("projection_status_v6", "UNKNOWN").fillna("UNKNOWN").astype(str).str.strip().replace("", "UNKNOWN")

    results["meeting_date"] = results["meeting_date"].astype(str).str.slice(0, 10)
    results["track_norm_join"] = results["track"].map(norm_track)
    results["race_no_join"] = pd.to_numeric(results["race_no"], errors="coerce").astype("Int64")
    results["horse_join"] = results["horseName"].map(canon_horse)
    results["sp_num"] = results["sp"].map(parse_float)

    results_keep = (
        results[["meeting_date", "track_norm_join", "race_no_join", "horse_join", "sp", "sp_num"]]
        .sort_values(["meeting_date", "track_norm_join", "race_no_join", "horse_join", "sp_num"], ascending=[True, True, True, True, False])
        .drop_duplicates(["meeting_date", "track_norm_join", "race_no_join", "horse_join"], keep="first")
    )

    settled = replay.merge(
        results_keep,
        on=["meeting_date", "track_norm_join", "race_no_join", "horse_join"],
        how="left",
        suffixes=("", "_warehouse"),
    )

    settled["sp_replay_original"] = settled["sp"] if "sp" in settled.columns else ""
    settled["sp_settled"] = settled["sp_warehouse"].where(
        settled["sp_warehouse"].fillna("").astype(str).str.strip().ne(""),
        settled["sp_replay_original"],
    )
    settled["sp_num_settled"] = settled["sp_settled"].map(parse_float)
    settled["sp_valid"] = settled["sp_num_settled"].gt(1)
    settled["profit_1u"] = np.where(settled["sp_valid"], np.where(settled["won"] == 1, settled["sp_num_settled"] - 1.0, -1.0), np.nan)

    replay_rows = int(len(settled))
    sp_rows = int(settled["sp_valid"].sum())
    sp_coverage = round(sp_rows / replay_rows, 4) if replay_rows else 0.0
    winner_mask = settled["won"] == 1
    winner_rows = int(winner_mask.sum())
    winner_sp_rows = int((winner_mask & settled["sp_valid"]).sum())
    winner_sp_coverage = round(winner_sp_rows / winner_rows, 4) if winner_rows else 0.0
    all_priced_profit_1u = round(float(settled.loc[settled["sp_valid"], "profit_1u"].sum()), 4) if sp_rows else 0.0
    all_priced_roi = round(float(all_priced_profit_1u / sp_rows), 4) if sp_rows else 0.0

    summary = pd.DataFrame(
        [
            {"metric": "replay_rows", "value": replay_rows},
            {"metric": "sp_rows", "value": sp_rows},
            {"metric": "sp_coverage", "value": sp_coverage},
            {"metric": "winner_sp_rows", "value": winner_sp_rows},
            {"metric": "winner_sp_coverage", "value": winner_sp_coverage},
            {"metric": "all_priced_profit_1u", "value": all_priced_profit_1u},
            {"metric": "all_priced_roi", "value": all_priced_roi},
        ]
    )

    roi_by_rank = compute_roi_table(settled, "rank_bucket", "rank_bucket")
    roi_by_rank = add_sort_key(roi_by_rank, "rank_bucket", RANK_ORDER, "_sort")
    roi_by_rank = roi_by_rank.sort_values(["_sort", "rank_bucket"]).drop(columns=["_sort"])

    roi_by_score_band = compute_roi_table(settled, "score_band", "score_band")
    roi_by_score_band = add_sort_key(roi_by_score_band, "score_band", SCORE_BAND_ORDER, "_sort")
    roi_by_score_band = roi_by_score_band.sort_values(["_sort", "score_band"]).drop(columns=["_sort"])

    roi_by_governance = compute_roi_table(settled, "governance", "governance")
    roi_by_governance = add_sort_key(roi_by_governance, "governance", GOVERNANCE_ORDER, "_sort")
    roi_by_governance = roi_by_governance.sort_values(["_sort", "governance"]).drop(columns=["_sort"])

    out_cols = list(replay.columns)
    for extra in [
        "rank_bucket",
        "score_band",
        "governance",
        "sp_replay_original",
        "sp_settled",
        "sp_num_settled",
        "sp_valid",
        "profit_1u",
        "track_norm_join",
        "race_no_join",
        "horse_join",
    ]:
        if extra not in out_cols:
            out_cols.append(extra)

    settled[out_cols].to_csv(OUT, index=False)
    summary.to_csv(SUMMARY, index=False)
    roi_by_rank.to_csv(ROI_BY_RANK, index=False)
    roi_by_score_band.to_csv(ROI_BY_SCORE_BAND, index=False)
    roi_by_governance.to_csv(ROI_BY_GOVERNANCE, index=False)

    print("[EDGEIQ_HISTORICAL_REPLAY_SETTLED_V1] COMPLETE")
    print(f"replay_rows={replay_rows}")
    print(f"sp_rows={sp_rows}")
    print(f"sp_coverage={sp_coverage}")
    print(f"winner_sp_rows={winner_sp_rows}")
    print(f"winner_sp_coverage={winner_sp_coverage}")
    print(f"all_priced_profit_1u={all_priced_profit_1u}")
    print(f"all_priced_roi={all_priced_roi}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")
    print(f"roi_by_rank={ROI_BY_RANK}")
    print(f"roi_by_score_band={ROI_BY_SCORE_BAND}")
    print(f"roi_by_governance={ROI_BY_GOVERNANCE}")


if __name__ == "__main__":
    main()
