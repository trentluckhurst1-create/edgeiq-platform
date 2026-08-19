from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
LIVE_TRUST_INDEX_PATH = DATA / "edgeiq_trust_index_v1.csv"
HIST_CERTAINTY_PATH = DATA / "edgeiq_certainty_engine_v1.csv"
HIST_PACE_TRUST_PATH = DATA / "edgeiq_historical_pace_trust_replay_v1.csv"

REPLAY_OUT = DATA / "edgeiq_trust_band_replay_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_trust_band_replay_v1_summary.csv"
BY_RANK_OUT = DATA / "edgeiq_trust_band_replay_v1_by_rank.csv"

PRIOR_RACES = 300.0
WEIGHTS = {
    "field_size_score": 0.24,
    "gap_1_2_score": 0.18,
    "gap_1_3_score": 0.18,
    "dominance_score": 0.22,
    "governance_score": 0.12,
    "pace_trust_score": 0.06,
}
TRUST_BAND_ORDER = ["A_PLUS", "A", "B", "C", "D"]
RANK_ORDER = [1, 2, 3]


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_race_key(value: object) -> str:
    text = clean_text(value).upper()
    if text == "":
        return ""
    text = re.sub(r"\|R(\d+)$", lambda m: f"|{m.group(1)}", text)
    return text


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def field_size_bucket(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number <= 7:
        return "LE_7"
    if number <= 10:
        return "8_10"
    if number <= 13:
        return "11_13"
    return "14_PLUS"


def gap_1_2_bucket(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number < 2:
        return "0_2"
    if number < 5:
        return "2_5"
    if number < 10:
        return "5_10"
    return "10_PLUS"


def gap_1_3_bucket(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number < 5:
        return "0_5"
    if number < 10:
        return "5_10"
    if number < 15:
        return "10_15"
    return "15_PLUS"


def dominance_band(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number >= 80:
        return "VERY_HIGH"
    if number >= 65:
        return "HIGH"
    if number >= 50:
        return "MEDIUM"
    return "LOW"


def trust_band(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "D"
    if number >= 80:
        return "A_PLUS"
    if number >= 65:
        return "A"
    if number >= 50:
        return "B"
    if number >= 35:
        return "C"
    return "D"


def first_valid_numeric(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return math.nan
    return float(clean.iloc[0])


def first_valid_text(values: pd.Series, default: str = "UNKNOWN") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def is_nonincreasing(values: list[float]) -> bool:
    clean = [float(v) for v in values if pd.notna(v)]
    return all(clean[i] >= clean[i + 1] for i in range(len(clean) - 1))


def is_nondecreasing(values: list[float]) -> bool:
    clean = [float(v) for v in values if pd.notna(v)]
    return all(clean[i] <= clean[i + 1] for i in range(len(clean) - 1))


def build_smoothed_score_map(df: pd.DataFrame, category_col: str, outcome_col: str = "top_pick_won") -> pd.DataFrame:
    grouped = (
        df.groupby(category_col, dropna=False)
        .agg(
            races=("join_key_v1", "size"),
            wins=(outcome_col, "sum"),
        )
        .reset_index()
    )
    overall_rate = float(df[outcome_col].mean())
    grouped["raw_win_rate"] = grouped["wins"] / grouped["races"]
    grouped["smoothed_win_rate"] = (grouped["wins"] + PRIOR_RACES * overall_rate) / (grouped["races"] + PRIOR_RACES)
    min_rate = float(grouped["smoothed_win_rate"].min())
    max_rate = float(grouped["smoothed_win_rate"].max())
    if math.isclose(min_rate, max_rate):
        grouped["score"] = 50.0
    else:
        grouped["score"] = 100.0 * (grouped["smoothed_win_rate"] - min_rate) / (max_rate - min_rate)
    grouped["score"] = grouped["score"].round(3)
    return grouped


def load_live_trust_reference() -> tuple[int, str]:
    if not LIVE_TRUST_INDEX_PATH.exists():
        return 0, ""
    df = pd.read_csv(LIVE_TRUST_INDEX_PATH, low_memory=False, usecols=["trust_band_v1"])
    bands = [band for band in TRUST_BAND_ORDER if band in set(df["trust_band_v1"].fillna("").astype(str))]
    return int(len(df)), "|".join(bands)


def load_historical_replay() -> pd.DataFrame:
    if not HISTORICAL_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing historical replay file: {HISTORICAL_REPLAY_PATH}")

    df = pd.read_csv(HISTORICAL_REPLAY_PATH, low_memory=False)
    for col in ["meeting_date", "track", "horse", "race_key"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    numeric_cols = ["race_no", "runner_score", "runner_rank", "finish_position", "won"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_num(df[col])
    df["race_key_norm_v1"] = df["race_key"].map(normalize_race_key)
    df["track_norm_v1"] = df["track"].map(normalize_track)
    df["race_no_num_v1"] = to_num(df["race_no"])
    df["join_key_v1"] = (
        df["meeting_date"].astype(str)
        + "|"
        + df["track_norm_v1"].astype(str)
        + "|"
        + df["race_no_num_v1"].fillna(-1).astype(int).astype(str)
    )
    return df.copy()


def load_historical_certainty() -> pd.DataFrame:
    if not HIST_CERTAINTY_PATH.exists():
        raise FileNotFoundError(f"Missing historical certainty file: {HIST_CERTAINTY_PATH}")

    df = pd.read_csv(HIST_CERTAINTY_PATH, low_memory=False)
    numeric_cols = [
        "race_no",
        "field_size",
        "dominance_certainty_score",
        "top_score",
        "second_score",
        "third_score",
        "score_gap_1_2",
        "score_gap_1_3",
        "winner_rank",
        "top_pick_won",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_num(df[col])
    text_cols = [
        "meeting_date",
        "track",
        "race_key",
        "top_pick_horse",
        "top_pick_governance_band",
        "dominance_certainty_band",
        "field_size_bucket",
        "gap_1_2_bucket",
        "gap_1_3_bucket",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    df["race_key_norm_v1"] = df["race_key"].map(normalize_race_key)
    df["track_norm_v1"] = df["track"].map(normalize_track)
    df["race_no_num_v1"] = to_num(df["race_no"])
    df["join_key_v1"] = (
        df["meeting_date"].astype(str)
        + "|"
        + df["track_norm_v1"].astype(str)
        + "|"
        + df["race_no_num_v1"].fillna(-1).astype(int).astype(str)
    )
    return df.copy()


def load_historical_pace_race_level() -> pd.DataFrame:
    if not HIST_PACE_TRUST_PATH.exists():
        return pd.DataFrame(columns=["join_key_v1", "pace_trust_band_v1", "pace_trust_score_raw_v1"])

    df = pd.read_csv(HIST_PACE_TRUST_PATH, low_memory=False)
    if "race_key" not in df.columns:
        return pd.DataFrame(columns=["join_key_v1", "pace_trust_band_v1", "pace_trust_score_raw_v1"])

    if "pace_trust_score_v1" in df.columns:
        df["pace_trust_score_v1"] = to_num(df["pace_trust_score_v1"])
    else:
        df["pace_trust_score_v1"] = math.nan
    if "pace_trust_band_v1" not in df.columns:
        df["pace_trust_band_v1"] = "UNKNOWN"

    if "meeting_date" in df.columns:
        df["meeting_date"] = df["meeting_date"].fillna("").astype(str)
    if "track" in df.columns:
        df["track"] = df["track"].fillna("").astype(str)
    if "race_no" in df.columns:
        df["race_no"] = to_num(df["race_no"])
    df["track_norm_v1"] = df["track"].map(normalize_track)
    df["race_no_num_v1"] = to_num(df["race_no"])
    df["join_key_v1"] = (
        df["meeting_date"].astype(str)
        + "|"
        + df["track_norm_v1"].astype(str)
        + "|"
        + df["race_no_num_v1"].fillna(-1).astype(int).astype(str)
    )

    grouped = (
        df.groupby("join_key_v1", dropna=False)
        .agg(
            pace_trust_band_v1=("pace_trust_band_v1", lambda s: first_valid_text(s, "UNKNOWN")),
            pace_trust_score_raw_v1=("pace_trust_score_v1", first_valid_numeric),
        )
        .reset_index()
    )
    grouped["pace_trust_band_v1"] = grouped["pace_trust_band_v1"].fillna("UNKNOWN").astype(str)
    grouped["pace_trust_score_raw_v1"] = to_num(grouped["pace_trust_score_raw_v1"])
    return grouped


def build_dominance_proxy_maps(hist_df: pd.DataFrame) -> dict[str, pd.DataFrame | float]:
    triple = (
        hist_df.groupby(["field_size_bucket", "gap_1_2_bucket", "gap_1_3_bucket"], dropna=False)
        .agg(dominance_score_mean=("dominance_certainty_score", "mean"))
        .reset_index()
    )
    pair_gap = (
        hist_df.groupby(["gap_1_2_bucket", "gap_1_3_bucket"], dropna=False)
        .agg(dominance_score_mean=("dominance_certainty_score", "mean"))
        .reset_index()
    )
    pair_field_gap12 = (
        hist_df.groupby(["field_size_bucket", "gap_1_2_bucket"], dropna=False)
        .agg(dominance_score_mean=("dominance_certainty_score", "mean"))
        .reset_index()
    )
    pair_field_gap13 = (
        hist_df.groupby(["field_size_bucket", "gap_1_3_bucket"], dropna=False)
        .agg(dominance_score_mean=("dominance_certainty_score", "mean"))
        .reset_index()
    )
    single_field = (
        hist_df.groupby("field_size_bucket", dropna=False)
        .agg(dominance_score_mean=("dominance_certainty_score", "mean"))
        .reset_index()
    )
    single_gap12 = (
        hist_df.groupby("gap_1_2_bucket", dropna=False)
        .agg(dominance_score_mean=("dominance_certainty_score", "mean"))
        .reset_index()
    )
    single_gap13 = (
        hist_df.groupby("gap_1_3_bucket", dropna=False)
        .agg(dominance_score_mean=("dominance_certainty_score", "mean"))
        .reset_index()
    )
    overall = float(hist_df["dominance_certainty_score"].mean())
    return {
        "triple": triple,
        "pair_gap": pair_gap,
        "pair_field_gap12": pair_field_gap12,
        "pair_field_gap13": pair_field_gap13,
        "single_field": single_field,
        "single_gap12": single_gap12,
        "single_gap13": single_gap13,
        "overall": overall,
    }


def lookup_mean(frame: pd.DataFrame, filters: dict[str, str], value_col: str) -> float:
    subset = frame.copy()
    for col, value in filters.items():
        subset = subset[subset[col].astype(str) == str(value)]
        if subset.empty:
            return math.nan
    values = to_num(subset[value_col]).dropna()
    if values.empty:
        return math.nan
    return float(values.iloc[0])


def predict_dominance_score(row: pd.Series, maps: dict[str, pd.DataFrame | float]) -> float:
    value = lookup_mean(
        maps["triple"],
        {
            "field_size_bucket": row["field_size_bucket"],
            "gap_1_2_bucket": row["gap_1_2_bucket"],
            "gap_1_3_bucket": row["gap_1_3_bucket"],
        },
        "dominance_score_mean",
    )
    if pd.notna(value):
        return float(value)

    value = lookup_mean(
        maps["pair_gap"],
        {"gap_1_2_bucket": row["gap_1_2_bucket"], "gap_1_3_bucket": row["gap_1_3_bucket"]},
        "dominance_score_mean",
    )
    if pd.notna(value):
        return float(value)

    value = lookup_mean(
        maps["pair_field_gap12"],
        {"field_size_bucket": row["field_size_bucket"], "gap_1_2_bucket": row["gap_1_2_bucket"]},
        "dominance_score_mean",
    )
    if pd.notna(value):
        return float(value)

    value = lookup_mean(
        maps["pair_field_gap13"],
        {"field_size_bucket": row["field_size_bucket"], "gap_1_3_bucket": row["gap_1_3_bucket"]},
        "dominance_score_mean",
    )
    if pd.notna(value):
        return float(value)

    for key, filter_key in [("single_gap13", "gap_1_3_bucket"), ("single_gap12", "gap_1_2_bucket"), ("single_field", "field_size_bucket")]:
        value = lookup_mean(maps[key], {filter_key: row[filter_key]}, "dominance_score_mean")
        if pd.notna(value):
            return float(value)

    return float(maps["overall"])


def build_historical_trust_races() -> pd.DataFrame:
    certainty_df = load_historical_certainty()
    pace_df = load_historical_pace_race_level()
    certainty_df = certainty_df.merge(pace_df, on="join_key_v1", how="left")
    certainty_df["pace_trust_band_v1"] = certainty_df["pace_trust_band_v1"].fillna("UNKNOWN").astype(str)
    certainty_df["pace_trust_score_raw_v1"] = to_num(certainty_df["pace_trust_score_raw_v1"]).fillna(0)

    field_map_df = build_smoothed_score_map(certainty_df, "field_size_bucket")
    gap12_map_df = build_smoothed_score_map(certainty_df, "gap_1_2_bucket")
    gap13_map_df = build_smoothed_score_map(certainty_df, "gap_1_3_bucket")
    gov_map_df = build_smoothed_score_map(certainty_df, "top_pick_governance_band")
    pace_map_df = build_smoothed_score_map(certainty_df, "pace_trust_band_v1")

    field_map = dict(zip(field_map_df["field_size_bucket"], field_map_df["score"]))
    gap12_map = dict(zip(gap12_map_df["gap_1_2_bucket"], gap12_map_df["score"]))
    gap13_map = dict(zip(gap13_map_df["gap_1_3_bucket"], gap13_map_df["score"]))
    gov_map = dict(zip(gov_map_df["top_pick_governance_band"], gov_map_df["score"]))
    pace_map = dict(zip(pace_map_df["pace_trust_band_v1"], pace_map_df["score"]))

    certainty_df["field_size_score"] = certainty_df["field_size_bucket"].map(field_map).fillna(50.0)
    certainty_df["gap_1_2_score"] = certainty_df["gap_1_2_bucket"].map(gap12_map).fillna(50.0)
    certainty_df["gap_1_3_score"] = certainty_df["gap_1_3_bucket"].map(gap13_map).fillna(50.0)
    certainty_df["governance_score"] = certainty_df["top_pick_governance_band"].map(gov_map).fillna(50.0)
    certainty_df["pace_trust_score"] = certainty_df["pace_trust_band_v1"].map(pace_map).fillna(50.0)
    certainty_df["dominance_score"] = to_num(certainty_df["dominance_certainty_score"]).fillna(to_num(certainty_df["dominance_certainty_score"]).mean()).clip(0, 100)

    dominance_maps = build_dominance_proxy_maps(certainty_df)
    certainty_df["dominance_score"] = certainty_df.apply(lambda row: predict_dominance_score(row, dominance_maps), axis=1).clip(0, 100).round(3)
    certainty_df["dominance_certainty_band"] = certainty_df["dominance_score"].apply(dominance_band)
    certainty_df["trust_index_v1"] = (
        WEIGHTS["field_size_score"] * certainty_df["field_size_score"]
        + WEIGHTS["gap_1_2_score"] * certainty_df["gap_1_2_score"]
        + WEIGHTS["gap_1_3_score"] * certainty_df["gap_1_3_score"]
        + WEIGHTS["dominance_score"] * certainty_df["dominance_score"]
        + WEIGHTS["governance_score"] * certainty_df["governance_score"]
        + WEIGHTS["pace_trust_score"] * certainty_df["pace_trust_score"]
    ).round(3)
    certainty_df["trust_band_v1"] = certainty_df["trust_index_v1"].apply(trust_band)

    return certainty_df[
        [
            "meeting_date",
            "track",
            "track_norm_v1",
            "race_no",
            "race_no_num_v1",
            "race_key",
            "race_key_norm_v1",
            "join_key_v1",
            "top_pick_horse",
            "top_pick_governance_band",
            "pace_trust_band_v1",
            "pace_trust_score_raw_v1",
            "field_size",
            "field_size_bucket",
            "top_score",
            "second_score",
            "third_score",
            "score_gap_1_2",
            "score_gap_1_3",
            "gap_1_2_bucket",
            "gap_1_3_bucket",
            "field_size_score",
            "gap_1_2_score",
            "gap_1_3_score",
            "dominance_score",
            "dominance_certainty_band",
            "governance_score",
            "pace_trust_score",
            "trust_index_v1",
            "trust_band_v1",
        ]
    ].copy()


def build_replay_with_trust() -> pd.DataFrame:
    replay_df = load_historical_replay()
    trust_races_df = build_historical_trust_races()
    merged = replay_df.merge(
        trust_races_df,
        on=["meeting_date", "track_norm_v1", "race_no_num_v1"],
        how="left",
        suffixes=("", "_trust"),
    )
    merged["trust_band_v1"] = merged["trust_band_v1"].fillna("UNMATCHED")
    merged["winner_top1_flag_v1"] = merged["runner_rank"].eq(1).astype(int) * merged["won"].fillna(0).astype(int)
    merged["winner_top3_flag_v1"] = merged["runner_rank"].le(3).fillna(False).astype(int) * merged["won"].fillna(0).astype(int)
    merged["winner_top5_flag_v1"] = merged["runner_rank"].le(5).fillna(False).astype(int) * merged["won"].fillna(0).astype(int)
    merged["winner_top10_flag_v1"] = merged["runner_rank"].le(10).fillna(False).astype(int) * merged["won"].fillna(0).astype(int)

    out_cols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "race_key_norm_v1",
        "join_key_v1",
        "horse",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
        "top_pick_horse",
        "top_pick_governance_band",
        "pace_trust_band_v1",
        "pace_trust_score_raw_v1",
        "field_size",
        "field_size_bucket",
        "top_score",
        "second_score",
        "third_score",
        "score_gap_1_2",
        "score_gap_1_3",
        "gap_1_2_bucket",
        "gap_1_3_bucket",
        "field_size_score",
        "gap_1_2_score",
        "gap_1_3_score",
        "dominance_score",
        "dominance_certainty_band",
        "governance_score",
        "pace_trust_score",
        "trust_index_v1",
        "trust_band_v1",
        "winner_top1_flag_v1",
        "winner_top3_flag_v1",
        "winner_top5_flag_v1",
        "winner_top10_flag_v1",
    ]
    return merged[out_cols].copy()


def build_race_level_summary(replay_with_trust_df: pd.DataFrame) -> pd.DataFrame:
    race_rows: list[dict[str, object]] = []
    for join_key, group in replay_with_trust_df.groupby("join_key_v1", sort=False):
        group = group.copy()
        winner_ranks = to_num(group.loc[group["won"].eq(1), "runner_rank"]).dropna().tolist()
        best_winner_rank = min(winner_ranks) if winner_ranks else math.nan
        race_rows.append(
            {
                "join_key_v1": join_key,
                "meeting_date": first_valid_text(group["meeting_date"], ""),
                "track": first_valid_text(group["track"], ""),
                "race_no": first_valid_numeric(group["race_no"]),
                "trust_index_v1": first_valid_numeric(group["trust_index_v1"]),
                "trust_band_v1": first_valid_text(group["trust_band_v1"], "UNMATCHED"),
                "winner_rank": best_winner_rank,
                "winner_count": int(group["won"].fillna(0).sum()),
                "winner_top1_rate_flag_v1": int(pd.notna(best_winner_rank) and best_winner_rank <= 1),
                "winner_top3_rate_flag_v1": int(pd.notna(best_winner_rank) and best_winner_rank <= 3),
                "winner_top5_rate_flag_v1": int(pd.notna(best_winner_rank) and best_winner_rank <= 5),
                "winner_top10_rate_flag_v1": int(pd.notna(best_winner_rank) and best_winner_rank <= 10),
            }
        )
    return pd.DataFrame(race_rows)


def build_by_rank(replay_with_trust_df: pd.DataFrame) -> pd.DataFrame:
    base = replay_with_trust_df[replay_with_trust_df["trust_band_v1"].isin(TRUST_BAND_ORDER)].copy()
    base = base[base["runner_rank"].isin(RANK_ORDER)].copy()
    grouped = (
        base.groupby(["trust_band_v1", "runner_rank"], dropna=False)
        .agg(
            runners=("horse", "size"),
            wins=("won", "sum"),
        )
        .reset_index()
    )
    grouped["win_rate"] = grouped["wins"] / grouped["runners"]

    rows: list[dict[str, object]] = []
    for band in TRUST_BAND_ORDER:
        for rank in RANK_ORDER:
            subset = grouped[(grouped["trust_band_v1"] == band) & (grouped["runner_rank"] == rank)]
            if subset.empty:
                rows.append(
                    {
                        "trust_band_v1": band,
                        "runner_rank": rank,
                        "rank_label": f"RANK_{rank}",
                        "runners": 0,
                        "wins": 0,
                        "win_rate": math.nan,
                    }
                )
            else:
                row = subset.iloc[0]
                rows.append(
                    {
                        "trust_band_v1": band,
                        "runner_rank": int(row["runner_rank"]),
                        "rank_label": f"RANK_{int(row['runner_rank'])}",
                        "runners": int(row["runners"]),
                        "wins": int(row["wins"]),
                        "win_rate": float(row["win_rate"]),
                    }
                )
    return pd.DataFrame(rows)


def build_summary(race_level_df: pd.DataFrame, by_rank_df: pd.DataFrame) -> pd.DataFrame:
    race_level_df = race_level_df[race_level_df["trust_band_v1"].isin(TRUST_BAND_ORDER)].copy()
    band_summary = (
        race_level_df.groupby("trust_band_v1", dropna=False)
        .agg(
            races=("join_key_v1", "size"),
            winner_top1_rate=("winner_top1_rate_flag_v1", "mean"),
            winner_top3_rate=("winner_top3_rate_flag_v1", "mean"),
            winner_top5_rate=("winner_top5_rate_flag_v1", "mean"),
            winner_top10_rate=("winner_top10_rate_flag_v1", "mean"),
            avg_winner_rank=("winner_rank", "mean"),
        )
        .reset_index()
    )

    rank_pivot = by_rank_df.pivot(index="trust_band_v1", columns="runner_rank", values="win_rate")
    rank_pivot = rank_pivot.rename(columns={1: "rank1_win_rate", 2: "rank2_win_rate", 3: "rank3_win_rate"}).reset_index()
    band_summary = band_summary.merge(rank_pivot, on="trust_band_v1", how="left")
    band_summary["rank1_minus_rank2_gap"] = band_summary["rank1_win_rate"] - band_summary["rank2_win_rate"]
    band_summary["rank1_minus_rank3_gap"] = band_summary["rank1_win_rate"] - band_summary["rank3_win_rate"]
    band_summary["sort_order"] = band_summary["trust_band_v1"].map({band: idx for idx, band in enumerate(TRUST_BAND_ORDER, start=1)}).fillna(999)
    band_summary = band_summary.sort_values("sort_order").drop(columns=["sort_order"])

    summary_rows: list[dict[str, object]] = []
    for row in band_summary.itertuples(index=False):
        summary_rows.append(
            {
                "section": "BAND_SUMMARY",
                "trust_band_v1": row.trust_band_v1,
                "races": int(row.races),
                "winner_top1_rate": row.winner_top1_rate,
                "winner_top3_rate": row.winner_top3_rate,
                "winner_top5_rate": row.winner_top5_rate,
                "winner_top10_rate": row.winner_top10_rate,
                "avg_winner_rank": row.avg_winner_rank,
                "rank1_win_rate": row.rank1_win_rate,
                "rank2_win_rate": row.rank2_win_rate,
                "rank3_win_rate": row.rank3_win_rate,
                "rank1_minus_rank2_gap": row.rank1_minus_rank2_gap,
                "rank1_minus_rank3_gap": row.rank1_minus_rank3_gap,
                "metric": "",
                "passed": np.nan,
                "sequence": "",
            }
        )

    top1_seq = band_summary["winner_top1_rate"].tolist()
    top3_seq = band_summary["winner_top3_rate"].tolist()
    top5_seq = band_summary["winner_top5_rate"].tolist()
    top10_seq = band_summary["winner_top10_rate"].tolist()
    avg_rank_seq = band_summary["avg_winner_rank"].tolist()
    rank1_seq = band_summary["rank1_win_rate"].tolist()
    gap12_seq = band_summary["rank1_minus_rank2_gap"].tolist()
    gap13_seq = band_summary["rank1_minus_rank3_gap"].tolist()

    checks = [
        ("winner_top1_rate_descending_v1", is_nonincreasing(top1_seq), top1_seq),
        ("winner_top3_rate_descending_v1", is_nonincreasing(top3_seq), top3_seq),
        ("winner_top5_rate_descending_v1", is_nonincreasing(top5_seq), top5_seq),
        ("winner_top10_rate_descending_v1", is_nonincreasing(top10_seq), top10_seq),
        ("avg_winner_rank_ascending_v1", is_nondecreasing(avg_rank_seq), avg_rank_seq),
        ("rank1_win_rate_descending_v1", is_nonincreasing(rank1_seq), rank1_seq),
        ("rank1_minus_rank2_gap_descending_v1", is_nonincreasing(gap12_seq), gap12_seq),
        ("rank1_minus_rank3_gap_descending_v1", is_nonincreasing(gap13_seq), gap13_seq),
    ]
    for metric_name, passed, seq in checks:
        summary_rows.append(
            {
                "section": "MONOTONICITY_CHECKS",
                "trust_band_v1": "",
                "races": np.nan,
                "winner_top1_rate": np.nan,
                "winner_top3_rate": np.nan,
                "winner_top5_rate": np.nan,
                "winner_top10_rate": np.nan,
                "avg_winner_rank": np.nan,
                "rank1_win_rate": np.nan,
                "rank2_win_rate": np.nan,
                "rank3_win_rate": np.nan,
                "rank1_minus_rank2_gap": np.nan,
                "rank1_minus_rank3_gap": np.nan,
                "metric": metric_name,
                "passed": bool(passed),
                "sequence": "|".join(f"{float(value):.6f}" for value in seq if pd.notna(value)),
            }
        )

    live_reference_rows, live_reference_bands = load_live_trust_reference()
    summary_rows.append(
        {
            "section": "OVERALL",
            "trust_band_v1": "",
            "races": int(race_level_df["join_key_v1"].nunique()),
            "winner_top1_rate": float(race_level_df["winner_top1_rate_flag_v1"].mean()) if not race_level_df.empty else math.nan,
            "winner_top3_rate": float(race_level_df["winner_top3_rate_flag_v1"].mean()) if not race_level_df.empty else math.nan,
            "winner_top5_rate": float(race_level_df["winner_top5_rate_flag_v1"].mean()) if not race_level_df.empty else math.nan,
            "winner_top10_rate": float(race_level_df["winner_top10_rate_flag_v1"].mean()) if not race_level_df.empty else math.nan,
            "avg_winner_rank": float(race_level_df["winner_rank"].mean()) if not race_level_df.empty else math.nan,
            "rank1_win_rate": np.nan,
            "rank2_win_rate": np.nan,
            "rank3_win_rate": np.nan,
            "rank1_minus_rank2_gap": np.nan,
            "rank1_minus_rank3_gap": np.nan,
            "metric": f"live_trust_reference_rows={live_reference_rows};live_trust_reference_bands={live_reference_bands}",
            "passed": np.nan,
            "sequence": "",
        }
    )

    return pd.DataFrame(summary_rows)


def main() -> None:
    replay_with_trust_df = build_replay_with_trust()
    race_level_df = build_race_level_summary(replay_with_trust_df)
    by_rank_df = build_by_rank(replay_with_trust_df)
    summary_df = build_summary(race_level_df, by_rank_df)

    replay_with_trust_df.to_csv(REPLAY_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    by_rank_df.to_csv(BY_RANK_OUT, index=False)

    band_rows = summary_df[summary_df["section"] == "BAND_SUMMARY"].copy()
    print("[EDGEIQ_TRUST_BAND_REPLAY_V1] COMPLETE")
    print(f"rows={len(replay_with_trust_df)}")
    print(f"races={race_level_df['join_key_v1'].nunique()}")
    for band in TRUST_BAND_ORDER:
        subset = band_rows[band_rows["trust_band_v1"] == band]
        if subset.empty:
            continue
        row = subset.iloc[0]
        print(
            f"{band}: races={int(row['races'])} top1={float(row['winner_top1_rate']):.6f} top3={float(row['winner_top3_rate']):.6f} top5={float(row['winner_top5_rate']):.6f} avg_rank={float(row['avg_winner_rank']):.6f}"
        )
    print(f"replay_out={REPLAY_OUT}")
    print(f"summary_out={SUMMARY_OUT}")
    print(f"by_rank_out={BY_RANK_OUT}")


if __name__ == "__main__":
    main()
