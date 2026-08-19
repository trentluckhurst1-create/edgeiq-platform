from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
RUNNER_SCORES_PATH = DATA / "edgeiq_historical_runner_scores_v1.csv"
TRUST_REPLAY_PATH = DATA / "edgeiq_trust_band_replay_v1.csv"

ENGINE_OUT = DATA / "edgeiq_rank_gap_engine_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_rank_gap_engine_v1_summary.csv"
BY_GAP_BAND_OUT = DATA / "edgeiq_rank_gap_engine_v1_by_gap_band.csv"
BY_TRUST_AND_GAP_OUT = DATA / "edgeiq_rank_gap_engine_v1_by_trust_and_gap.csv"

TRUST_BANDS = ["A_PLUS", "A", "B", "C", "D"]
GAP12_ORDER = ["ZERO_TO_2", "TWO_TO_5", "FIVE_TO_10", "TEN_PLUS"]
GAP13_ORDER = ["ZERO_TO_5", "FIVE_TO_10", "TEN_TO_15", "FIFTEEN_PLUS"]
SHARE_ORDER = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
MIN_COMBINED_RACES = 300


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def normalize_horse(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def build_join_key(df: pd.DataFrame) -> pd.Series:
    race_no = pd.to_numeric(df["race_no"], errors="coerce").fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df["track"].map(normalize_track) + "|" + race_no


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def first_valid_numeric(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return math.nan
    return float(clean.iloc[0])


def first_valid_text(values: pd.Series, default: str = "") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def gap_1_2_band(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number < 2:
        return "ZERO_TO_2"
    if number < 5:
        return "TWO_TO_5"
    if number < 10:
        return "FIVE_TO_10"
    return "TEN_PLUS"


def gap_1_3_band(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number < 5:
        return "ZERO_TO_5"
    if number < 10:
        return "FIVE_TO_10"
    if number < 15:
        return "TEN_TO_15"
    return "FIFTEEN_PLUS"


def score_share_band(value: object, q25: float, q50: float, q75: float) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number <= q25:
        return "LOW"
    if number <= q50:
        return "MEDIUM"
    if number <= q75:
        return "HIGH"
    return "VERY_HIGH"


def load_replay() -> pd.DataFrame:
    if not REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing replay file: {REPLAY_PATH}")
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "runner_rank",
        "finish_position",
        "won",
    ]
    df = pd.read_csv(REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "race_key", "horse", "horse_key"]:
        df[col] = df[col].fillna("").astype(str)
    for col in ["race_no", "runner_rank", "finish_position", "won"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["join_key_v1"] = build_join_key(df)
    df["horse_join_key_v1"] = df["horse_key"].replace("", pd.NA).fillna(df["horse"].map(normalize_horse)).astype(str)
    return df.copy()


def load_runner_scores() -> pd.DataFrame:
    if not RUNNER_SCORES_PATH.exists():
        raise FileNotFoundError(f"Missing runner scores file: {RUNNER_SCORES_PATH}")
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "field_size",
        "governance_band_hist_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
    ]
    df = pd.read_csv(RUNNER_SCORES_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "race_key", "horse", "horse_key", "governance_band_hist_v1"]:
        df[col] = df[col].fillna("").astype(str)
    for col in ["race_no", "field_size", "runner_score_hist_v1", "runner_rank_hist_v1"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["join_key_v1"] = build_join_key(df)
    df["horse_join_key_v1"] = df["horse_key"].replace("", pd.NA).fillna(df["horse"].map(normalize_horse)).astype(str)
    return df.copy()


def load_trust_races() -> pd.DataFrame:
    if not TRUST_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing trust replay file: {TRUST_REPLAY_PATH}")
    usecols = ["meeting_date", "track", "race_no", "trust_band_v1", "trust_index_v1"]
    df = pd.read_csv(TRUST_REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "trust_band_v1"]:
        df[col] = df[col].fillna("").astype(str)
    for col in ["race_no", "trust_index_v1"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["join_key_v1"] = build_join_key(df)
    race_level = (
        df.groupby("join_key_v1", dropna=False)
        .agg(
            trust_band_v1=("trust_band_v1", "first"),
            trust_index_v1=("trust_index_v1", "first"),
        )
        .reset_index()
    )
    return race_level


def build_runner_level_base() -> pd.DataFrame:
    replay_df = load_replay()
    scores_df = load_runner_scores()
    trust_races_df = load_trust_races()

    merged = scores_df.merge(
        replay_df,
        on=["join_key_v1", "horse_join_key_v1"],
        how="inner",
        suffixes=("_scores", "_replay"),
    )
    merged = merged.merge(trust_races_df, on="join_key_v1", how="left")

    merged["meeting_date"] = merged["meeting_date_scores"].where(merged["meeting_date_scores"].ne(""), merged["meeting_date_replay"])
    merged["track"] = merged["track_scores"].where(merged["track_scores"].ne(""), merged["track_replay"])
    merged["race_no"] = merged["race_no_scores"].fillna(merged["race_no_replay"])
    merged["race_key"] = merged["race_key_scores"].where(merged["race_key_scores"].ne(""), merged["race_key_replay"])
    merged["horse"] = merged["horse_scores"].where(merged["horse_scores"].ne(""), merged["horse_replay"])

    merged["runner_rank"] = merged["runner_rank"].fillna(merged["runner_rank_hist_v1"])
    merged["runner_score"] = merged["runner_score_hist_v1"]
    merged["field_size"] = merged["field_size"].fillna(merged.groupby("join_key_v1")["horse"].transform("size"))
    merged["governance_band_hist_v1"] = merged["governance_band_hist_v1"].replace("", "UNKNOWN")
    merged["trust_band_v1"] = merged["trust_band_v1"].fillna("UNMATCHED")

    out_cols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "join_key_v1",
        "horse",
        "governance_band_hist_v1",
        "field_size",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
        "trust_band_v1",
        "trust_index_v1",
    ]
    return merged[out_cols].copy()


def build_race_level_engine(base_df: pd.DataFrame) -> tuple[pd.DataFrame, tuple[float, float, float]]:
    race_rows: list[dict[str, object]] = []
    for join_key, group in base_df.groupby("join_key_v1", sort=False):
        group = group.copy().sort_values(["runner_rank", "runner_score", "horse"], ascending=[True, False, True])
        top_row = group.iloc[0]
        top_three = group.head(3)
        scores = pd.to_numeric(top_three["runner_score"], errors="coerce").tolist()
        top_score = float(scores[0]) if len(scores) >= 1 and pd.notna(scores[0]) else math.nan
        second_score = float(scores[1]) if len(scores) >= 2 and pd.notna(scores[1]) else math.nan
        third_score = float(scores[2]) if len(scores) >= 3 and pd.notna(scores[2]) else math.nan
        total_race_score = float(pd.to_numeric(group["runner_score"], errors="coerce").fillna(0).sum())
        gap12 = top_score - second_score if pd.notna(top_score) and pd.notna(second_score) else math.nan
        gap13 = top_score - third_score if pd.notna(top_score) and pd.notna(third_score) else math.nan
        score_share_total = safe_div(top_score, total_race_score)

        winner_ranks = pd.to_numeric(group.loc[group["won"].eq(1), "runner_rank"], errors="coerce").dropna().tolist()
        winner_rank = min(winner_ranks) if winner_ranks else math.nan

        race_rows.append(
            {
                "meeting_date": first_valid_text(group["meeting_date"], ""),
                "track": first_valid_text(group["track"], ""),
                "race_no": first_valid_numeric(group["race_no"]),
                "race_key": first_valid_text(group["race_key"], ""),
                "join_key_v1": join_key,
                "field_size": int(round(first_valid_numeric(group["field_size"]))) if pd.notna(first_valid_numeric(group["field_size"])) else int(len(group)),
                "top_horse": first_valid_text(pd.Series([top_row["horse"]]), ""),
                "top_score": top_score,
                "second_score": second_score,
                "third_score": third_score,
                "gap_1_2": gap12,
                "gap_1_3": gap13,
                "total_race_score": total_race_score,
                "score_share_total": score_share_total,
                "top_pick_finish": pd.to_numeric(top_row["finish_position"], errors="coerce"),
                "top_pick_won": int(pd.to_numeric(top_row["won"], errors="coerce") == 1),
                "winner_rank": winner_rank,
                "trust_band_v1": first_valid_text(group["trust_band_v1"], "UNMATCHED"),
            }
        )

    race_df = pd.DataFrame(race_rows)
    q25 = float(race_df["score_share_total"].quantile(0.25))
    q50 = float(race_df["score_share_total"].quantile(0.50))
    q75 = float(race_df["score_share_total"].quantile(0.75))

    race_df["gap_1_2_band"] = race_df["gap_1_2"].apply(gap_1_2_band)
    race_df["gap_1_3_band"] = race_df["gap_1_3"].apply(gap_1_3_band)
    race_df["score_share_band"] = race_df["score_share_total"].apply(lambda value: score_share_band(value, q25, q50, q75))
    race_df["winner_top3_flag_v1"] = race_df["winner_rank"].le(3).astype(int)
    race_df["winner_top5_flag_v1"] = race_df["winner_rank"].le(5).astype(int)

    return race_df, (q25, q50, q75)


def summarize_races(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(
            races=("join_key_v1", "size"),
            top_pick_wins=("top_pick_won", "sum"),
            top_pick_win_rate=("top_pick_won", "mean"),
            winner_top3_rate=("winner_top3_flag_v1", "mean"),
            winner_top5_rate=("winner_top5_flag_v1", "mean"),
            avg_winner_rank=("winner_rank", "mean"),
        )
        .reset_index()
    )
    return grouped


def build_by_gap_band(race_df: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    config = [
        ("gap_1_2_band", GAP12_ORDER),
        ("gap_1_3_band", GAP13_ORDER),
        ("score_share_band", SHARE_ORDER),
    ]
    for gap_dimension, order in config:
        grouped = summarize_races(race_df, [gap_dimension]).rename(columns={gap_dimension: "gap_band"})
        grouped.insert(0, "gap_dimension", gap_dimension)
        grouped["band_order"] = grouped["gap_band"].map({name: idx for idx, name in enumerate(order, start=1)}).fillna(999)
        grouped = grouped.sort_values(["band_order", "gap_band"]).drop(columns=["band_order"])
        frames.append(grouped)
    return pd.concat(frames, ignore_index=True)


def build_by_trust_and_gap(race_df: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    config = [
        ("gap_1_2_band", GAP12_ORDER),
        ("gap_1_3_band", GAP13_ORDER),
        ("score_share_band", SHARE_ORDER),
    ]
    for gap_dimension, order in config:
        grouped = summarize_races(race_df, ["trust_band_v1", gap_dimension]).rename(columns={gap_dimension: "gap_band"})
        grouped.insert(1, "gap_dimension", gap_dimension)
        grouped["trust_order"] = grouped["trust_band_v1"].map({name: idx for idx, name in enumerate(TRUST_BANDS, start=1)}).fillna(999)
        grouped["band_order"] = grouped["gap_band"].map({name: idx for idx, name in enumerate(order, start=1)}).fillna(999)
        grouped = grouped.sort_values(["trust_order", "band_order", "gap_band"]).drop(columns=["trust_order", "band_order"])
        frames.append(grouped)
    return pd.concat(frames, ignore_index=True)


def build_summary(race_df: pd.DataFrame, by_gap_df: pd.DataFrame, by_trust_gap_df: pd.DataFrame, quantiles: tuple[float, float, float]) -> pd.DataFrame:
    q25, q50, q75 = quantiles
    summary_rows: list[dict[str, object]] = [
        {"metric": "total_races", "value": int(len(race_df))},
        {"metric": "overall_top_pick_win_rate", "value": float(race_df["top_pick_won"].mean())},
        {"metric": "overall_winner_top3_rate", "value": float(race_df["winner_top3_flag_v1"].mean())},
        {"metric": "overall_winner_top5_rate", "value": float(race_df["winner_top5_flag_v1"].mean())},
        {"metric": "overall_avg_winner_rank", "value": float(race_df["winner_rank"].mean())},
        {"metric": "score_share_q25", "value": q25},
        {"metric": "score_share_q50", "value": q50},
        {"metric": "score_share_q75", "value": q75},
    ]

    best_overall_gap = by_gap_df.sort_values(["top_pick_win_rate", "races"], ascending=[False, False]).iloc[0]
    summary_rows.extend(
        [
            {"metric": "best_gap_band_dimension", "value": best_overall_gap["gap_dimension"]},
            {"metric": "best_gap_band", "value": best_overall_gap["gap_band"]},
            {"metric": "best_gap_band_top_pick_win_rate", "value": float(best_overall_gap["top_pick_win_rate"])},
            {"metric": "best_gap_band_races", "value": int(best_overall_gap["races"])},
        ]
    )

    for gap_dimension in ["gap_1_2_band", "gap_1_3_band", "score_share_band"]:
        subset = by_gap_df[by_gap_df["gap_dimension"] == gap_dimension].copy()
        best = subset.sort_values(["top_pick_win_rate", "races"], ascending=[False, False]).iloc[0]
        summary_rows.extend(
            [
                {"metric": f"best::{gap_dimension}::band", "value": best["gap_band"]},
                {"metric": f"best::{gap_dimension}::top_pick_win_rate", "value": float(best["top_pick_win_rate"])},
                {"metric": f"best::{gap_dimension}::races", "value": int(best["races"])},
            ]
        )

    eligible_combined = by_trust_gap_df[by_trust_gap_df["races"].ge(MIN_COMBINED_RACES)].copy()
    if not eligible_combined.empty:
        best_combined = eligible_combined.sort_values(["top_pick_win_rate", "races"], ascending=[False, False]).iloc[0]
        summary_rows.extend(
            [
                {"metric": "best_combined_min300_trust_band", "value": best_combined["trust_band_v1"]},
                {"metric": "best_combined_min300_gap_dimension", "value": best_combined["gap_dimension"]},
                {"metric": "best_combined_min300_gap_band", "value": best_combined["gap_band"]},
                {"metric": "best_combined_min300_top_pick_win_rate", "value": float(best_combined["top_pick_win_rate"])},
                {"metric": "best_combined_min300_races", "value": int(best_combined["races"])},
                {"metric": "best_combined_min300_winner_top3_rate", "value": float(best_combined["winner_top3_rate"])},
                {"metric": "best_combined_min300_winner_top5_rate", "value": float(best_combined["winner_top5_rate"])},
                {"metric": "best_combined_min300_avg_winner_rank", "value": float(best_combined["avg_winner_rank"])},
            ]
        )

    return pd.DataFrame(summary_rows)


def main() -> None:
    base_df = build_runner_level_base()
    race_df, quantiles = build_race_level_engine(base_df)
    by_gap_df = build_by_gap_band(race_df)
    by_trust_gap_df = build_by_trust_and_gap(race_df)
    summary_df = build_summary(race_df, by_gap_df, by_trust_gap_df, quantiles)

    race_df.to_csv(ENGINE_OUT, index=False)
    by_gap_df.to_csv(BY_GAP_BAND_OUT, index=False)
    by_trust_gap_df.to_csv(BY_TRUST_AND_GAP_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)

    best_gap = by_gap_df.sort_values(["top_pick_win_rate", "races"], ascending=[False, False]).iloc[0]
    eligible = by_trust_gap_df[by_trust_gap_df["races"].ge(MIN_COMBINED_RACES)].copy()
    print("[EDGEIQ_RANK_GAP_ENGINE_V1] COMPLETE")
    print(f"races={len(race_df)}")
    print(f"best_gap_dimension={best_gap['gap_dimension']}")
    print(f"best_gap_band={best_gap['gap_band']}")
    print(f"best_gap_top_pick_win_rate={float(best_gap['top_pick_win_rate']):.6f}")
    if not eligible.empty:
        best_combined = eligible.sort_values(["top_pick_win_rate", "races"], ascending=[False, False]).iloc[0]
        print(f"best_combined_trust_band={best_combined['trust_band_v1']}")
        print(f"best_combined_gap_dimension={best_combined['gap_dimension']}")
        print(f"best_combined_gap_band={best_combined['gap_band']}")
        print(f"best_combined_top_pick_win_rate={float(best_combined['top_pick_win_rate']):.6f}")
        print(f"best_combined_races={int(best_combined['races'])}")
    print(f"engine_out={ENGINE_OUT}")
    print(f"summary_out={SUMMARY_OUT}")
    print(f"by_gap_band_out={BY_GAP_BAND_OUT}")
    print(f"by_trust_and_gap_out={BY_TRUST_AND_GAP_OUT}")


if __name__ == "__main__":
    main()
