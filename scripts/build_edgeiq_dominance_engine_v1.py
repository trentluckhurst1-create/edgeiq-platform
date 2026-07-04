from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_SCORES = DATA / "edgeiq_historical_runner_scores_v1.csv"
CURRENT_V6 = DATA / "edgeiq_runner_score_v6.csv"
BASELINE_REPLAY = DATA / "edgeiq_historical_replay_v1.csv"
PACE_REPLAY = DATA / "edgeiq_historical_pace_advantage_replay_v1.csv"
RUNNER_SCORE_V6_REPLAY = DATA / "edgeiq_historical_pace_trust_replay_v1.csv"

CURRENT_OUT = DATA / "edgeiq_dominance_engine_v1.csv"
AUDIT_OUT = DATA / "edgeiq_dominance_engine_v1_audit.csv"
HISTORICAL_OUT = DATA / "edgeiq_historical_dominance_replay_v1.csv"
HISTORICAL_SUMMARY_OUT = DATA / "edgeiq_historical_dominance_replay_v1_summary.csv"

WEIGHTS = {
    "score_share_of_race": 0.35,
    "dominance_gap_rank2": 0.25,
    "dominance_gap_rank3": 0.20,
    "dominance_vs_avg": 0.20,
}

DOMINANCE_BAND_ORDER = ["ELITE", "STRONG", "POSITIVE", "NEUTRAL", "WEAK", "POOR", "UNKNOWN"]
RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS", "UNKNOWN"]


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


def to_float(value: object) -> float:
    if value is None or pd.isna(value):
        return math.nan
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else math.nan
    text = str(value).replace("$", "").replace(",", "").strip()
    if text == "":
        return math.nan
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return math.nan
    try:
        number = float(match.group(0))
    except ValueError:
        return math.nan
    return number if math.isfinite(number) else math.nan


def to_int(value: object) -> float:
    number = to_float(value)
    if pd.isna(number):
        return math.nan
    return int(number)


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator is None or pd.isna(denominator) or float(denominator) == 0.0:
        return math.nan
    return float(numerator) / float(denominator)


def rank_bucket(rank_value: object) -> str:
    rank_num = to_int(rank_value)
    if pd.isna(rank_num):
        return "UNKNOWN"
    if rank_num == 1:
        return "RANK_1"
    if rank_num == 2:
        return "RANK_2"
    if rank_num == 3:
        return "RANK_3"
    if rank_num <= 5:
        return "RANK_4_5"
    if rank_num <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def dominance_band(score: object) -> str:
    value = to_float(score)
    if pd.isna(value):
        return "UNKNOWN"
    if value >= 80:
        return "ELITE"
    if value >= 68:
        return "STRONG"
    if value >= 56:
        return "POSITIVE"
    if value >= 44:
        return "NEUTRAL"
    if value >= 32:
        return "WEAK"
    return "POOR"


def empirical_cdf_scaler(reference: pd.Series, values: pd.Series) -> pd.Series:
    ref = pd.to_numeric(reference, errors="coerce").dropna().to_numpy(dtype=float)
    vals = pd.to_numeric(values, errors="coerce")
    if ref.size == 0:
        return pd.Series(np.nan, index=values.index)
    ref = np.sort(ref.copy())
    arr = vals.to_numpy(dtype=float)
    out = np.full(arr.shape, np.nan, dtype=float)
    mask = np.isfinite(arr)
    if mask.any():
        out[mask] = np.searchsorted(ref, arr[mask], side="right") / ref.size
    return pd.Series(out, index=values.index)


def load_historical_scores() -> pd.DataFrame:
    if not HISTORICAL_SCORES.exists():
        raise FileNotFoundError(f"Missing historical scores file: {HISTORICAL_SCORES}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "finish_position",
        "won",
        "placed",
        "field_size",
        "governance_band_hist_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
    ]
    df = pd.read_csv(HISTORICAL_SCORES, low_memory=False, usecols=usecols)
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["track"] = df["track"].fillna("")
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["horse"] = df["horse"].fillna("")
    df["horse_key"] = df["horse_key"].fillna(df["horse"].map(canon_horse)).astype(str)
    df["runner_score_base_v1"] = pd.to_numeric(df["runner_score_hist_v1"], errors="coerce")
    df["runner_rank_base_v1"] = pd.to_numeric(df["runner_rank_hist_v1"], errors="coerce")
    df["field_size_v1"] = pd.to_numeric(df["field_size"], errors="coerce")
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0).astype(int)
    df["placed"] = pd.to_numeric(df["placed"], errors="coerce").fillna(0).astype(int)
    df["governance_band_v1"] = df["governance_band_hist_v1"].fillna("UNKNOWN").astype(str)
    df["dataset_v1"] = "HISTORICAL"
    return df


def load_current_v6() -> pd.DataFrame:
    if not CURRENT_V6.exists():
        raise FileNotFoundError(f"Missing current V6 file: {CURRENT_V6}")

    df = pd.read_csv(CURRENT_V6, low_memory=False)
    df = df.copy()
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["track"] = df["track"].fillna("")
    df["horse"] = df["horse"].fillna("")
    if "horse_key" in df.columns:
        df["horse_key"] = df["horse_key"].fillna(df["horse"].map(canon_horse)).astype(str)
    else:
        df["horse_key"] = df["horse"].map(canon_horse)
    if "race_key_v6" in df.columns:
        df["race_key"] = df["race_key_v6"].astype(str)
    else:
        df["race_key"] = df["meeting_date"].astype(str) + "|" + df["track"].astype(str) + "|R" + df["race_no"].astype(str)
    df["runner_score_base_v1"] = pd.to_numeric(df["runner_score_v6"], errors="coerce")
    df["runner_rank_base_v1"] = pd.to_numeric(df["runner_rank_v6"], errors="coerce")
    df["field_size_v1"] = df.groupby("race_key")["horse"].transform("size")
    df["governance_band_v1"] = df["governance_band_v7_2"].fillna("UNKNOWN").astype(str) if "governance_band_v7_2" in df.columns else "UNKNOWN"
    df["dataset_v1"] = "CURRENT_V6"
    return df


def add_race_dominance_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["runner_score_base_v1"] = pd.to_numeric(df["runner_score_base_v1"], errors="coerce")
    df["field_size_v1"] = pd.to_numeric(df["field_size_v1"], errors="coerce")

    top_scores = (
        df.sort_values(["race_key", "runner_score_base_v1", "horse"], ascending=[True, False, True])
        .groupby("race_key")["runner_score_base_v1"]
        .apply(lambda s: pd.Series({"score_rank_1": s.iloc[0] if len(s) >= 1 else math.nan, "score_rank_2": s.iloc[1] if len(s) >= 2 else math.nan, "score_rank_3": s.iloc[2] if len(s) >= 3 else math.nan}))
        .reset_index()
    )
    top_scores = top_scores.pivot(index="race_key", columns="level_1", values="runner_score_base_v1").reset_index()
    top_scores.columns.name = None

    race_stats = (
        df.groupby("race_key", dropna=False)
        .agg(
            race_avg_score_v1=("runner_score_base_v1", "mean"),
            race_total_score_v1=("runner_score_base_v1", "sum"),
            field_size_calc_v1=("horse", "size"),
        )
        .reset_index()
    )

    df = df.merge(top_scores, on="race_key", how="left")
    df = df.merge(race_stats, on="race_key", how="left")
    df["field_size_v1"] = df["field_size_v1"].fillna(df["field_size_calc_v1"])
    df["dominance_gap_rank2"] = df["runner_score_base_v1"] - df["score_rank_2"]
    df["dominance_gap_rank3"] = df["runner_score_base_v1"] - df["score_rank_3"]
    df["dominance_vs_avg"] = df["runner_score_base_v1"] - df["race_avg_score_v1"]
    df["score_share_of_race"] = np.where(
        df["race_total_score_v1"].ne(0) & df["race_total_score_v1"].notna(),
        df["runner_score_base_v1"] / df["race_total_score_v1"],
        np.nan,
    )
    return df


def apply_dominance_scoring(df: pd.DataFrame, reference_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["score_share_scaled_v1"] = empirical_cdf_scaler(reference_df["score_share_of_race"], df["score_share_of_race"])
    df["gap_rank2_scaled_v1"] = empirical_cdf_scaler(reference_df["dominance_gap_rank2"], df["dominance_gap_rank2"])
    df["gap_rank3_scaled_v1"] = empirical_cdf_scaler(reference_df["dominance_gap_rank3"], df["dominance_gap_rank3"])
    df["vs_avg_scaled_v1"] = empirical_cdf_scaler(reference_df["dominance_vs_avg"], df["dominance_vs_avg"])

    df["dominance_score_v1"] = (
        100.0
        * (
            WEIGHTS["score_share_of_race"] * df["score_share_scaled_v1"]
            + WEIGHTS["dominance_gap_rank2"] * df["gap_rank2_scaled_v1"]
            + WEIGHTS["dominance_gap_rank3"] * df["gap_rank3_scaled_v1"]
            + WEIGHTS["dominance_vs_avg"] * df["vs_avg_scaled_v1"]
        )
    ).round(3)
    df["dominance_band_v1"] = df["dominance_score_v1"].apply(dominance_band)

    df = df.sort_values(
        ["race_key", "dominance_score_v1", "runner_score_base_v1", "horse"],
        ascending=[True, False, False, True],
    ).reset_index(drop=True)
    df["dominance_order_v1"] = df.groupby("race_key").cumcount() + 1
    df["dominance_rank_v1"] = pd.Series(df["dominance_order_v1"], index=df.index, dtype="Int64")
    df["dominance_rank_bucket_v1"] = df["dominance_rank_v1"].apply(rank_bucket)
    df["dominance_percentile"] = np.where(
        df["field_size_v1"].fillna(0).le(1),
        1.0,
        1.0 - ((df["dominance_rank_v1"] - 1.0) / (df["field_size_v1"] - 1.0)),
    )
    return df


def extract_capture_metrics(df: pd.DataFrame, rank_col: str) -> dict[str, float]:
    winners = df[pd.to_numeric(df["won"], errors="coerce").fillna(0).eq(1)].copy()
    ranks = pd.to_numeric(winners[rank_col], errors="coerce")
    return {
        "Top1": float(ranks.le(1).mean()),
        "Top3": float(ranks.le(3).mean()),
        "Top5": float(ranks.le(5).mean()),
        "Top10": float(ranks.le(10).mean()),
        "avg_winner_rank": float(ranks.mean()),
        "winner_rows": int(len(winners)),
    }


def build_current_output(df: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "governance_band_v1",
        "field_size_v1",
        "runner_score_base_v1",
        "runner_rank_base_v1",
        "score_rank_1",
        "score_rank_2",
        "score_rank_3",
        "race_avg_score_v1",
        "race_total_score_v1",
        "dominance_gap_rank2",
        "dominance_gap_rank3",
        "dominance_vs_avg",
        "score_share_of_race",
        "score_share_scaled_v1",
        "gap_rank2_scaled_v1",
        "gap_rank3_scaled_v1",
        "vs_avg_scaled_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "dominance_rank_v1",
        "dominance_percentile",
    ]
    out = df[keep_cols].copy()
    out = out.rename(columns={
        "governance_band_v1": "governance_band_v1",
        "runner_score_base_v1": "runner_score_v6_base_v1",
        "runner_rank_base_v1": "runner_rank_v6_base_v1",
    })
    return out


def build_historical_output(df: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "governance_band_v1",
        "field_size_v1",
        "runner_score_base_v1",
        "runner_rank_base_v1",
        "score_rank_1",
        "score_rank_2",
        "score_rank_3",
        "race_avg_score_v1",
        "race_total_score_v1",
        "dominance_gap_rank2",
        "dominance_gap_rank3",
        "dominance_vs_avg",
        "score_share_of_race",
        "dominance_score_v1",
        "dominance_band_v1",
        "dominance_rank_v1",
        "dominance_rank_bucket_v1",
        "dominance_percentile",
        "finish_position",
        "won",
        "placed",
    ]
    out = df[keep_cols].copy()
    out = out.rename(columns={
        "governance_band_v1": "governance_band_hist_v1",
        "runner_score_base_v1": "runner_score_hist_v1",
        "runner_rank_base_v1": "runner_rank_hist_v1",
    })
    return out


def build_audit(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    top1 = df[df["dominance_rank_v1"].eq(1)].copy()
    top1_by_band = (
        top1.groupby("dominance_band_v1", dropna=False)
        .agg(
            top1_rows=("horse", "size"),
            wins=("won", "sum"),
            avg_dominance_score=("dominance_score_v1", "mean"),
        )
        .reset_index()
    )
    top1_by_band["top1_win_rate"] = top1_by_band["wins"] / top1_by_band["top1_rows"]
    top1_by_band["sort_order"] = top1_by_band["dominance_band_v1"].map({value: idx for idx, value in enumerate(DOMINANCE_BAND_ORDER, start=1)}).fillna(999)
    top1_by_band = top1_by_band.sort_values(["sort_order", "dominance_band_v1"]).drop(columns=["sort_order"])
    for row in top1_by_band.itertuples(index=False):
        rows.append(
            {
                "section": "TOP1_WIN_RATE_BY_DOMINANCE_BAND",
                "bucket": row.dominance_band_v1,
                "metric": "top1_win_rate",
                "value": row.top1_win_rate,
                "rows": row.top1_rows,
                "wins": row.wins,
                "avg_dominance_score": row.avg_dominance_score,
                "rate": row.top1_win_rate,
            }
        )

    winners = df[df["won"].eq(1)].copy()
    winner_dist = (
        winners.groupby("dominance_rank_bucket_v1", dropna=False)
        .agg(
            winner_rows=("horse", "size"),
            avg_winner_rank=("dominance_rank_v1", "mean"),
            avg_dominance_score=("dominance_score_v1", "mean"),
        )
        .reset_index()
    )
    winner_dist["winner_rate"] = winner_dist["winner_rows"] / max(len(winners), 1)
    winner_dist["sort_order"] = winner_dist["dominance_rank_bucket_v1"].map({value: idx for idx, value in enumerate(RANK_BUCKET_ORDER, start=1)}).fillna(999)
    winner_dist = winner_dist.sort_values(["sort_order", "dominance_rank_bucket_v1"]).drop(columns=["sort_order"])
    for row in winner_dist.itertuples(index=False):
        rows.append(
            {
                "section": "WINNER_RANK_DISTRIBUTION",
                "bucket": row.dominance_rank_bucket_v1,
                "metric": "winner_rate",
                "value": row.winner_rate,
                "rows": row.winner_rows,
                "wins": row.winner_rows,
                "avg_dominance_score": row.avg_dominance_score,
                "rate": row.winner_rate,
            }
        )

    capture = extract_capture_metrics(df, "dominance_rank_v1")
    for metric_name in ["Top1", "Top3", "Top5", "Top10", "avg_winner_rank"]:
        rows.append(
            {
                "section": "WINNER_CAPTURE_SUMMARY",
                "bucket": "",
                "metric": metric_name,
                "value": capture[metric_name],
                "rows": capture["winner_rows"],
                "wins": np.nan,
                "avg_dominance_score": np.nan,
                "rate": capture[metric_name],
            }
        )

    return pd.DataFrame(rows)


def build_comparison_summary(dominance_df: pd.DataFrame) -> pd.DataFrame:
    baseline_df = pd.read_csv(BASELINE_REPLAY, low_memory=False) if BASELINE_REPLAY.exists() else pd.DataFrame()
    pace_df = pd.read_csv(PACE_REPLAY, low_memory=False) if PACE_REPLAY.exists() else pd.DataFrame()
    v6_replay_df = pd.read_csv(RUNNER_SCORE_V6_REPLAY, low_memory=False) if RUNNER_SCORE_V6_REPLAY.exists() else pd.DataFrame()

    metrics = {
        "baseline_replay": extract_capture_metrics(baseline_df, "runner_rank") if not baseline_df.empty else {},
        "pace_replay": extract_capture_metrics(pace_df, "runner_rank_pace_v1") if not pace_df.empty else {},
        "runner_score_v6_replay": extract_capture_metrics(v6_replay_df, "runner_rank_pace_trust_v1") if not v6_replay_df.empty else {},
        "dominance_replay": extract_capture_metrics(dominance_df, "dominance_rank_v1"),
    }

    rows: list[dict[str, object]] = []
    for metric_name in ["Top1", "Top3", "Top5", "Top10", "avg_winner_rank"]:
        baseline_value = metrics["baseline_replay"].get(metric_name, math.nan)
        pace_value = metrics["pace_replay"].get(metric_name, math.nan)
        v6_value = metrics["runner_score_v6_replay"].get(metric_name, math.nan)
        dominance_value = metrics["dominance_replay"].get(metric_name, math.nan)
        lower_is_better = metric_name == "avg_winner_rank"
        rows.append(
            {
                "metric": metric_name,
                "baseline_replay": baseline_value,
                "pace_replay": pace_value,
                "runner_score_v6_replay": v6_value,
                "dominance_replay": dominance_value,
                "dominance_minus_baseline": dominance_value - baseline_value if not pd.isna(dominance_value) and not pd.isna(baseline_value) else math.nan,
                "dominance_minus_pace_replay": dominance_value - pace_value if not pd.isna(dominance_value) and not pd.isna(pace_value) else math.nan,
                "dominance_minus_runner_score_v6": dominance_value - v6_value if not pd.isna(dominance_value) and not pd.isna(v6_value) else math.nan,
                "improved_vs_baseline": (dominance_value < baseline_value) if lower_is_better else (dominance_value > baseline_value),
                "improved_vs_pace_replay": (dominance_value < pace_value) if lower_is_better else (dominance_value > pace_value),
                "improved_vs_runner_score_v6": (dominance_value < v6_value) if lower_is_better else (dominance_value > v6_value),
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    historical = load_historical_scores()
    historical = add_race_dominance_features(historical)
    historical = apply_dominance_scoring(historical, historical)

    current = load_current_v6()
    current = add_race_dominance_features(current)
    current = apply_dominance_scoring(current, historical)

    current_out = build_current_output(current)
    current_out.to_csv(CURRENT_OUT, index=False)

    historical_out = build_historical_output(historical)
    historical_out.to_csv(HISTORICAL_OUT, index=False)

    audit = build_audit(historical)
    audit.to_csv(AUDIT_OUT, index=False)

    comparison = build_comparison_summary(historical)
    comparison.to_csv(HISTORICAL_SUMMARY_OUT, index=False)

    dom_metrics = extract_capture_metrics(historical, "dominance_rank_v1")
    print("[EDGEIQ_DOMINANCE_ENGINE_V1] COMPLETE")
    print(f"current_rows={len(current_out)}")
    print(f"historical_rows={len(historical_out)}")
    print(f"historical_races={historical['race_key'].nunique()}")
    print(f"dominance_top1={dom_metrics['Top1']:.6f}")
    print(f"dominance_top3={dom_metrics['Top3']:.6f}")
    print(f"dominance_top5={dom_metrics['Top5']:.6f}")
    print(f"dominance_top10={dom_metrics['Top10']:.6f}")
    print(f"dominance_avg_winner_rank={dom_metrics['avg_winner_rank']:.6f}")
    print(f"current_out={CURRENT_OUT}")
    print(f"audit_out={AUDIT_OUT}")
    print(f"historical_out={HISTORICAL_OUT}")
    print(f"historical_summary_out={HISTORICAL_SUMMARY_OUT}")


if __name__ == "__main__":
    main()






