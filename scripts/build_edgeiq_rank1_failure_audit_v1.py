from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
DOMINANCE_REFERENCE_PATH = DATA / "edgeiq_dominance_engine_v1.csv"
RANK_GAP_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
TRUST_PROFILE_REFERENCE_PATH = DATA / "edgeiq_trust_profile_engine_v1.csv"

AUDIT_OUT = DATA / "edgeiq_rank1_failure_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_rank1_failure_audit_v1_summary.csv"
FAILURE_REASONS_OUT = DATA / "edgeiq_rank1_failure_audit_v1_failure_reasons.csv"
BEST_WORST_OUT = DATA / "edgeiq_rank1_failure_audit_v1_best_vs_worst.csv"

WEIGHTS = {
    "score_share_of_race": 0.35,
    "dominance_gap_rank2": 0.25,
    "dominance_gap_rank3": 0.20,
    "dominance_vs_avg": 0.20,
}
FEATURE_WEIGHTS = {
    "trust_band_v1": 0.35,
    "gap_1_3_band": 0.25,
    "dominance_certainty_band": 0.20,
    "field_size_bucket_v1": 0.10,
    "gap_1_2_band": 0.10,
}
PRIOR_RACES = 300.0

DOMINANCE_BAND_ORDER = ["ELITE", "STRONG", "POSITIVE", "NEUTRAL", "WEAK", "POOR", "UNKNOWN"]
TRUST_PROFILE_ORDER_DEFAULT = ["ELITE", "STRONG", "STANDARD", "CHAOTIC"]
TRUST_BAND_ORDER = ["A_PLUS", "A", "B", "C", "D", "UNKNOWN"]
FIELD_SIZE_BUCKET_ORDER = ["LE_7", "8_10", "11_13", "14_PLUS", "UNKNOWN"]
FAILURE_REASON_ORDER = [
    "PASS_ALL",
    "DOMINANCE_FAIL",
    "SCORE_SHARE_FAIL",
    "TRUST_FAIL",
    "FIELD_SIZE_FAIL",
    "MULTI_FACTOR_FAIL",
]
WINNER_RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS", "UNKNOWN"]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def normalize_horse(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def build_join_key(df: pd.DataFrame) -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df["track"].map(normalize_track) + "|" + race_no


def build_runner_key(df: pd.DataFrame) -> pd.Series:
    return build_join_key(df) + "|" + df["horse"].map(normalize_horse)


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


def rank_bucket(rank_value: object) -> str:
    number = pd.to_numeric(rank_value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number == 1:
        return "RANK_1"
    if number == 2:
        return "RANK_2"
    if number == 3:
        return "RANK_3"
    if number <= 5:
        return "RANK_4_5"
    if number <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def dominance_band(score: object) -> str:
    value = pd.to_numeric(score, errors="coerce")
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


def dominance_certainty_band(value: object) -> str:
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


def trust_profile_from_score(value: object, q25: float, q50: float, q75: float) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number >= q75:
        return "ELITE"
    if number >= q50:
        return "STRONG"
    if number >= q25:
        return "STANDARD"
    return "CHAOTIC"


def first_valid_text(values: pd.Series, default: str = "UNKNOWN") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def load_profile_order() -> list[str]:
    ordered = TRUST_PROFILE_ORDER_DEFAULT.copy()
    if "UNKNOWN" not in ordered:
        ordered.append("UNKNOWN")
    return ordered


def load_dominance_reference_bands() -> list[str]:
    if not DOMINANCE_REFERENCE_PATH.exists():
        return DOMINANCE_BAND_ORDER.copy()
    try:
        ref = pd.read_csv(DOMINANCE_REFERENCE_PATH, low_memory=False, usecols=["dominance_band_v1"])
    except ValueError:
        return DOMINANCE_BAND_ORDER.copy()
    values = {
        clean_text(value).upper()
        for value in ref["dominance_band_v1"].dropna().tolist()
        if clean_text(value) != ""
    }
    ordered = [item for item in DOMINANCE_BAND_ORDER if item in values]
    return ordered or DOMINANCE_BAND_ORDER.copy()


def load_historical_replay() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
        "projection_status_v6",
    ]
    df = pd.read_csv(HIST_REPLAY_PATH, low_memory=False, usecols=usecols)

    for col in ["meeting_date", "track", "race_key", "horse", "horse_key", "projection_status_v6"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)

    for col in ["race_no", "runner_score", "runner_rank", "finish_position", "won"]:
        df[col] = to_num(df[col])

    df["placed"] = df["finish_position"].le(3).fillna(False).astype(int)
    df["join_key_v1"] = build_join_key(df)
    df["runner_key_v1"] = build_runner_key(df)
    df["horse_key"] = df["horse_key"].where(df["horse_key"].ne(""), df["horse"].map(normalize_horse))
    df["runner_rank"] = df["runner_rank"].fillna(999).astype(int)
    df["won"] = df["won"].fillna(0).astype(int)
    return df.copy()


def add_dominance_features(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["runner_score"] = to_num(work["runner_score"])

    sorted_scores = work.sort_values(["join_key_v1", "runner_score", "horse"], ascending=[True, False, True]).copy()
    top_scores = (
        sorted_scores.groupby("join_key_v1")["runner_score"]
        .apply(
            lambda s: pd.Series(
                {
                    "score_rank_1": s.iloc[0] if len(s) >= 1 else math.nan,
                    "score_rank_2": s.iloc[1] if len(s) >= 2 else math.nan,
                    "score_rank_3": s.iloc[2] if len(s) >= 3 else math.nan,
                }
            )
        )
        .reset_index()
    )
    top_scores = top_scores.pivot(index="join_key_v1", columns="level_1", values="runner_score").reset_index()
    top_scores.columns.name = None

    race_stats = (
        work.groupby("join_key_v1", dropna=False)
        .agg(
            field_size=("horse", "size"),
            race_avg_score_v1=("runner_score", "mean"),
            race_total_score_v1=("runner_score", "sum"),
        )
        .reset_index()
    )

    work = work.merge(top_scores, on="join_key_v1", how="left")
    work = work.merge(race_stats, on="join_key_v1", how="left")
    work["field_size_bucket_v1"] = work["field_size"].apply(field_size_bucket)
    work["dominance_gap_rank2"] = work["runner_score"] - work["score_rank_2"]
    work["dominance_gap_rank3"] = work["runner_score"] - work["score_rank_3"]
    work["dominance_vs_avg"] = work["runner_score"] - work["race_avg_score_v1"]
    work["score_share_of_race"] = np.where(
        work["race_total_score_v1"].ne(0) & work["race_total_score_v1"].notna(),
        work["runner_score"] / work["race_total_score_v1"],
        np.nan,
    )

    work["score_share_scaled_v1"] = empirical_cdf_scaler(work["score_share_of_race"], work["score_share_of_race"])
    work["gap_rank2_scaled_v1"] = empirical_cdf_scaler(work["dominance_gap_rank2"], work["dominance_gap_rank2"])
    work["gap_rank3_scaled_v1"] = empirical_cdf_scaler(work["dominance_gap_rank3"], work["dominance_gap_rank3"])
    work["vs_avg_scaled_v1"] = empirical_cdf_scaler(work["dominance_vs_avg"], work["dominance_vs_avg"])

    work["dominance_score_v1"] = (
        100.0
        * (
            WEIGHTS["score_share_of_race"] * work["score_share_scaled_v1"]
            + WEIGHTS["dominance_gap_rank2"] * work["gap_rank2_scaled_v1"]
            + WEIGHTS["dominance_gap_rank3"] * work["gap_rank3_scaled_v1"]
            + WEIGHTS["dominance_vs_avg"] * work["vs_avg_scaled_v1"]
        )
    ).round(3)
    work["dominance_band_v1"] = work["dominance_score_v1"].map(dominance_band)
    return work.copy()


def load_rank_gap() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "field_size",
        "top_pick_won",
        "winner_rank",
        "trust_band_v1",
        "gap_1_2",
        "gap_1_3",
        "gap_1_2_band",
        "gap_1_3_band",
        "score_share_total",
        "score_share_band",
    ]
    df = pd.read_csv(RANK_GAP_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "trust_band_v1", "gap_1_2_band", "gap_1_3_band", "score_share_band"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
        df[col] = df[col].replace("", "UNKNOWN")
    for col in ["race_no", "field_size", "top_pick_won", "winner_rank", "gap_1_2", "gap_1_3", "score_share_total"]:
        df[col] = to_num(df[col])
    df["join_key_v1"] = build_join_key(df)
    df["field_size_bucket_v1"] = df["field_size"].apply(field_size_bucket)
    df["top_pick_won"] = df["top_pick_won"].fillna(0).astype(int)
    return df.copy()


def build_historical_trust_profiles(rank1_df: pd.DataFrame, gap_df: pd.DataFrame, profile_order: list[str]) -> pd.DataFrame:
    race_df = gap_df.merge(
        rank1_df[["join_key_v1", "dominance_score_v1"]].rename(columns={"dominance_score_v1": "rank1_dominance_score_v1"}),
        on="join_key_v1",
        how="left",
    )
    race_df["dominance_certainty_band"] = race_df["rank1_dominance_score_v1"].map(dominance_certainty_band).fillna("UNKNOWN")

    feature_maps: dict[str, dict[str, float]] = {}
    overall_rate = float(race_df["top_pick_won"].mean())
    for feature_name in FEATURE_WEIGHTS:
        grouped = (
            race_df.groupby(feature_name, dropna=False)
            .agg(races=("join_key_v1", "size"), wins=("top_pick_won", "sum"))
            .reset_index()
        )
        grouped[feature_name] = grouped[feature_name].fillna("UNKNOWN").astype(str)
        grouped["smoothed_top1_rate_v1"] = (grouped["wins"] + PRIOR_RACES * overall_rate) / (grouped["races"] + PRIOR_RACES)
        min_rate = float(grouped["smoothed_top1_rate_v1"].min())
        max_rate = float(grouped["smoothed_top1_rate_v1"].max())
        if math.isclose(min_rate, max_rate):
            grouped["feature_score_v1"] = 50.0
        else:
            grouped["feature_score_v1"] = 100.0 * (grouped["smoothed_top1_rate_v1"] - min_rate) / (max_rate - min_rate)
        feature_maps[feature_name] = dict(zip(grouped[feature_name], grouped["feature_score_v1"]))

    for feature_name, weight in FEATURE_WEIGHTS.items():
        race_df[f"{feature_name}_score_v1"] = race_df[feature_name].map(feature_maps[feature_name]).fillna(50.0) * weight

    race_df["trust_profile_score_v1"] = sum(race_df[f"{feature}_score_v1"] for feature in FEATURE_WEIGHTS)
    q25 = float(race_df["trust_profile_score_v1"].quantile(0.25))
    q50 = float(race_df["trust_profile_score_v1"].quantile(0.50))
    q75 = float(race_df["trust_profile_score_v1"].quantile(0.75))
    race_df["trust_profile_v1"] = race_df["trust_profile_score_v1"].map(lambda value: trust_profile_from_score(value, q25, q50, q75))
    race_df["trust_profile_v1"] = pd.Categorical(race_df["trust_profile_v1"], categories=profile_order, ordered=True).astype(str)
    race_df["trust_profile_v1"] = race_df["trust_profile_v1"].replace("nan", "UNKNOWN")
    return race_df[
        [
            "join_key_v1",
            "field_size",
            "field_size_bucket_v1",
            "winner_rank",
            "trust_band_v1",
            "gap_1_2",
            "gap_1_3",
            "gap_1_2_band",
            "gap_1_3_band",
            "score_share_total",
            "score_share_band",
            "dominance_certainty_band",
            "trust_profile_v1",
        ]
    ].drop_duplicates(subset=["join_key_v1"]).copy()


def build_rank1_race_frame(runners_df: pd.DataFrame, race_context_df: pd.DataFrame) -> pd.DataFrame:
    rank1_rows = (
        runners_df.sort_values(["join_key_v1", "runner_rank", "runner_score", "horse"], ascending=[True, True, False, True])
        .groupby("join_key_v1", dropna=False)
        .head(1)
        .copy()
    )

    winner_rows = (
        runners_df[runners_df["won"].eq(1)]
        .sort_values(["join_key_v1", "runner_rank", "dominance_score_v1", "runner_score", "horse"], ascending=[True, True, False, False, True])
        .groupby("join_key_v1", dropna=False)
        .head(1)
        .copy()
    )

    rank1_rows = rank1_rows.rename(
        columns={
            "horse": "rank1_horse",
            "horse_key": "rank1_horse_key",
            "runner_score": "rank1_runner_score",
            "runner_rank": "rank1_runner_rank",
            "finish_position": "rank1_finish_position",
            "won": "rank1_won",
            "placed": "rank1_placed",
            "dominance_score_v1": "rank1_dominance_score_v1",
            "dominance_band_v1": "rank1_dominance_band_v1",
            "dominance_gap_rank2": "rank1_dominance_gap_rank2",
            "dominance_gap_rank3": "rank1_dominance_gap_rank3",
            "dominance_vs_avg": "rank1_dominance_vs_avg",
            "score_share_of_race": "rank1_score_share_of_race",
        }
    )
    winner_rows = winner_rows.rename(
        columns={
            "horse": "winner_horse",
            "horse_key": "winner_horse_key",
            "runner_score": "winner_runner_score",
            "runner_rank": "winner_rank",
            "finish_position": "winner_finish_position",
            "won": "winner_won",
            "placed": "winner_placed",
            "dominance_score_v1": "winner_dominance_score_v1",
            "dominance_band_v1": "winner_dominance_band_v1",
            "score_share_of_race": "winner_score_share_of_race",
        }
    )

    keep_rank1 = [
        "join_key_v1",
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "rank1_horse",
        "rank1_horse_key",
        "rank1_runner_score",
        "rank1_runner_rank",
        "rank1_finish_position",
        "rank1_won",
        "rank1_placed",
        "rank1_dominance_score_v1",
        "rank1_dominance_band_v1",
        "rank1_dominance_gap_rank2",
        "rank1_dominance_gap_rank3",
        "rank1_dominance_vs_avg",
        "rank1_score_share_of_race",
    ]
    keep_winner = [
        "join_key_v1",
        "winner_horse",
        "winner_horse_key",
        "winner_runner_score",
        "winner_rank",
        "winner_finish_position",
        "winner_won",
        "winner_placed",
        "winner_dominance_score_v1",
        "winner_dominance_band_v1",
        "winner_score_share_of_race",
    ]

    race_context_df = race_context_df.rename(columns={"winner_rank": "historical_winner_rank_v1"})

    race_df = rank1_rows[keep_rank1].merge(winner_rows[keep_winner], on="join_key_v1", how="left")
    race_df = race_df.merge(race_context_df, on="join_key_v1", how="left")
    race_df["rank1_is_winner_v1"] = race_df["rank1_won"].fillna(0).astype(int)
    race_df["winner_rank_bucket_v1"] = race_df["winner_rank"].map(rank_bucket)
    race_df["winner_field_size_v1"] = race_df["field_size"]
    race_df["winner_trust_profile_v1"] = race_df["trust_profile_v1"]
    return race_df.copy()


def feature_compare_rows(rank1_winners: pd.DataFrame, rank1_losers: pd.DataFrame) -> pd.DataFrame:
    feature_specs = [
        ("rank1_dominance_score_v1", "dominance_score"),
        ("rank1_score_share_of_race", "score_share"),
        ("rank1_dominance_gap_rank2", "dominance_gap_rank2"),
        ("rank1_dominance_gap_rank3", "dominance_gap_rank3"),
        ("gap_1_2", "score_gap_1_2"),
        ("gap_1_3", "score_gap_1_3"),
        ("field_size", "field_size"),
    ]

    rows = []
    for col_name, label in feature_specs:
        winner_mean = float(rank1_winners[col_name].mean()) if not rank1_winners.empty else math.nan
        loser_mean = float(rank1_losers[col_name].mean()) if not rank1_losers.empty else math.nan
        rows.append(
            {
                "section": "FEATURE_COMPARISON",
                "item": label,
                "winner_mean": winner_mean,
                "loser_mean": loser_mean,
                "difference": winner_mean - loser_mean if pd.notna(winner_mean) and pd.notna(loser_mean) else math.nan,
                "winner_mode": "",
                "loser_mode": "",
                "notes": "",
            }
        )

    for col_name, label in [("trust_profile_v1", "trust_profile"), ("trust_band_v1", "trust_band")]:
        winner_mode = first_valid_text(rank1_winners[col_name].mode(dropna=True), "UNKNOWN")
        loser_mode = first_valid_text(rank1_losers[col_name].mode(dropna=True), "UNKNOWN")
        rows.append(
            {
                "section": "FEATURE_COMPARISON",
                "item": label,
                "winner_mean": math.nan,
                "loser_mean": math.nan,
                "difference": math.nan,
                "winner_mode": winner_mode,
                "loser_mode": loser_mode,
                "notes": "",
            }
        )

    return pd.DataFrame(rows)


def assign_failure_reasons(race_df: pd.DataFrame) -> pd.DataFrame:
    work = race_df.copy()
    winner_rank1 = work[work["rank1_is_winner_v1"].eq(1)].copy()

    dom_score_q25 = float(winner_rank1["rank1_dominance_score_v1"].quantile(0.25))
    dom_gap2_q25 = float(winner_rank1["rank1_dominance_gap_rank2"].quantile(0.25))
    dom_gap3_q25 = float(winner_rank1["rank1_dominance_gap_rank3"].quantile(0.25))
    share_q25 = float(winner_rank1["rank1_score_share_of_race"].quantile(0.25))
    gap12_q25 = float(winner_rank1["gap_1_2"].quantile(0.25))
    gap13_q25 = float(winner_rank1["gap_1_3"].quantile(0.25))

    work["DOMINANCE_FAIL_FLAG"] = (
        work["rank1_dominance_score_v1"].lt(dom_score_q25)
        | work["rank1_dominance_gap_rank2"].lt(dom_gap2_q25)
        | work["rank1_dominance_gap_rank3"].lt(dom_gap3_q25)
    )
    work["SCORE_SHARE_FAIL_FLAG"] = (
        work["rank1_score_share_of_race"].lt(share_q25)
        | work["gap_1_2"].lt(gap12_q25)
        | work["gap_1_3"].lt(gap13_q25)
    )
    work["TRUST_FAIL_FLAG"] = work["trust_profile_v1"].isin(["STANDARD", "CHAOTIC"]) | work["trust_band_v1"].isin(["C", "D"])
    work["FIELD_SIZE_FAIL_FLAG"] = work["field_size_bucket_v1"].isin(["11_13", "14_PLUS"])
    work["failure_count_v1"] = (
        work["DOMINANCE_FAIL_FLAG"].astype(int)
        + work["SCORE_SHARE_FAIL_FLAG"].astype(int)
        + work["TRUST_FAIL_FLAG"].astype(int)
        + work["FIELD_SIZE_FAIL_FLAG"].astype(int)
    )

    def classify(row: pd.Series) -> str:
        if int(row["failure_count_v1"]) >= 2:
            return "MULTI_FACTOR_FAIL"
        if bool(row["DOMINANCE_FAIL_FLAG"]):
            return "DOMINANCE_FAIL"
        if bool(row["SCORE_SHARE_FAIL_FLAG"]):
            return "SCORE_SHARE_FAIL"
        if bool(row["TRUST_FAIL_FLAG"]):
            return "TRUST_FAIL"
        if bool(row["FIELD_SIZE_FAIL_FLAG"]):
            return "FIELD_SIZE_FAIL"
        return "PASS_ALL"

    work["failure_reason_v1"] = work.apply(classify, axis=1)
    return work.copy()


def build_failure_reason_table(race_df: pd.DataFrame) -> pd.DataFrame:
    table = (
        race_df.groupby("failure_reason_v1", dropna=False)
        .agg(
            races=("join_key_v1", "nunique"),
            rank1_wins=("rank1_is_winner_v1", "sum"),
            avg_winner_rank=("winner_rank", "mean"),
        )
        .reset_index()
    )
    total_races = int(race_df["join_key_v1"].nunique())
    table["pct"] = table["races"].map(lambda value: safe_div(value, total_races))
    table["rank1_win_rate"] = table.apply(lambda row: safe_div(row["rank1_wins"], row["races"]), axis=1)
    table["failure_reason_v1"] = pd.Categorical(table["failure_reason_v1"], categories=FAILURE_REASON_ORDER, ordered=True)
    table = table.sort_values("failure_reason_v1").reset_index(drop=True)
    return table.copy()


def build_best_worst_table(race_df: pd.DataFrame) -> pd.DataFrame:
    race_df = race_df.copy()
    race_df["pocket_id_v1"] = race_df["trust_profile_v1"].astype(str) + "|" + race_df["field_size_bucket_v1"].astype(str)

    table = (
        race_df.groupby(["trust_profile_v1", "field_size_bucket_v1", "pocket_id_v1"], dropna=False)
        .agg(
            races=("join_key_v1", "nunique"),
            rank1_wins=("rank1_is_winner_v1", "sum"),
            avg_winner_rank=("winner_rank", "mean"),
            avg_rank1_dominance_score=("rank1_dominance_score_v1", "mean"),
            avg_rank1_score_share=("rank1_score_share_of_race", "mean"),
            avg_field_size=("field_size", "mean"),
        )
        .reset_index()
    )
    table["rank1_win_rate"] = table.apply(lambda row: safe_div(row["rank1_wins"], row["races"]), axis=1)
    table["eligible_ge_500_v1"] = table["races"].ge(500)

    eligible = table[table["eligible_ge_500_v1"]].copy()
    best_key = None
    worst_key = None
    if not eligible.empty:
        best_key = eligible.sort_values(["rank1_win_rate", "avg_winner_rank", "races"], ascending=[False, True, False]).iloc[0]["pocket_id_v1"]
        worst_key = eligible.sort_values(["rank1_win_rate", "avg_winner_rank", "races"], ascending=[True, False, False]).iloc[0]["pocket_id_v1"]

    table["best_profile_flag_v1"] = table["pocket_id_v1"].eq(best_key) if best_key is not None else False
    table["danger_profile_flag_v1"] = table["pocket_id_v1"].eq(worst_key) if worst_key is not None else False
    table = table.sort_values(["rank1_win_rate", "races"], ascending=[False, False]).reset_index(drop=True)
    return table.copy()


def build_summary(race_df: pd.DataFrame, failure_table: pd.DataFrame, best_worst_df: pd.DataFrame) -> pd.DataFrame:
    rank1_winners = race_df[race_df["rank1_is_winner_v1"].eq(1)].copy()
    rank1_losers = race_df[race_df["rank1_is_winner_v1"].eq(0)].copy()

    winner_rank_distribution = (
        rank1_losers.groupby("winner_rank_bucket_v1", dropna=False)
        .agg(races=("join_key_v1", "nunique"))
        .reset_index()
    )
    winner_rank_distribution["pct"] = winner_rank_distribution["races"].map(lambda value: safe_div(value, len(rank1_losers)))
    winner_rank_distribution["winner_rank_bucket_v1"] = pd.Categorical(
        winner_rank_distribution["winner_rank_bucket_v1"],
        categories=WINNER_RANK_BUCKET_ORDER,
        ordered=True,
    )
    winner_rank_distribution = winner_rank_distribution.sort_values("winner_rank_bucket_v1").reset_index(drop=True)

    feature_compare_df = feature_compare_rows(rank1_winners, rank1_losers)

    largest_failure = (
        rank1_losers.groupby("failure_reason_v1", dropna=False)["join_key_v1"]
        .nunique()
        .sort_values(ascending=False)
    )
    largest_failure_reason = str(largest_failure.index[0]) if not largest_failure.empty else "UNKNOWN"

    best_row = best_worst_df[best_worst_df["best_profile_flag_v1"]].head(1)
    worst_row = best_worst_df[best_worst_df["danger_profile_flag_v1"]].head(1)

    summary_rows = [
        {
            "section": "OVERVIEW",
            "item": "total_races",
            "winner_mean": int(race_df["join_key_v1"].nunique()),
            "loser_mean": math.nan,
            "difference": math.nan,
            "winner_mode": "",
            "loser_mode": "",
            "notes": "Historical races with a rank1 horse and a canonical winner row",
        },
        {
            "section": "OVERVIEW",
            "item": "rank1_win_rate",
            "winner_mean": safe_div(rank1_winners["join_key_v1"].nunique(), race_df["join_key_v1"].nunique()),
            "loser_mean": math.nan,
            "difference": math.nan,
            "winner_mode": "",
            "loser_mode": "",
            "notes": "Overall rank1 strike rate",
        },
        {
            "section": "WHAT_BEATS_RANK1",
            "item": "winner_rank_mean_when_rank1_loses",
            "winner_mean": float(rank1_losers["winner_rank"].mean()) if not rank1_losers.empty else math.nan,
            "loser_mean": math.nan,
            "difference": math.nan,
            "winner_mode": "",
            "loser_mode": "",
            "notes": "",
        },
        {
            "section": "WHAT_BEATS_RANK1",
            "item": "winner_dominance_score_mean_when_rank1_loses",
            "winner_mean": float(rank1_losers["winner_dominance_score_v1"].mean()) if not rank1_losers.empty else math.nan,
            "loser_mean": math.nan,
            "difference": math.nan,
            "winner_mode": "",
            "loser_mode": "",
            "notes": "",
        },
        {
            "section": "WHAT_BEATS_RANK1",
            "item": "winner_score_share_mean_when_rank1_loses",
            "winner_mean": float(rank1_losers["winner_score_share_of_race"].mean()) if not rank1_losers.empty else math.nan,
            "loser_mean": math.nan,
            "difference": math.nan,
            "winner_mode": "",
            "loser_mode": "",
            "notes": "",
        },
        {
            "section": "WHAT_BEATS_RANK1",
            "item": "winner_trust_profile_mode_when_rank1_loses",
            "winner_mean": math.nan,
            "loser_mean": math.nan,
            "difference": math.nan,
            "winner_mode": first_valid_text(rank1_losers["winner_trust_profile_v1"].mode(dropna=True), "UNKNOWN"),
            "loser_mode": "",
            "notes": "",
        },
        {
            "section": "WHAT_BEATS_RANK1",
            "item": "winner_field_size_mean_when_rank1_loses",
            "winner_mean": float(rank1_losers["winner_field_size_v1"].mean()) if not rank1_losers.empty else math.nan,
            "loser_mean": math.nan,
            "difference": math.nan,
            "winner_mode": "",
            "loser_mode": "",
            "notes": "",
        },
    ]

    summary_rows.extend(feature_compare_df.to_dict(orient="records"))

    for _, row in winner_rank_distribution.iterrows():
        summary_rows.append(
            {
                "section": "WINNER_RANK_DISTRIBUTION_WHEN_RANK1_LOSES",
                "item": str(row["winner_rank_bucket_v1"]),
                "winner_mean": row["races"],
                "loser_mean": row["pct"],
                "difference": math.nan,
                "winner_mode": "",
                "loser_mode": "",
                "notes": "",
            }
        )

    summary_rows.append(
        {
            "section": "ANSWERS",
            "item": "WHY_RANK1_LOSES",
            "winner_mean": math.nan,
            "loser_mean": math.nan,
            "difference": math.nan,
            "winner_mode": largest_failure_reason,
            "loser_mode": "",
            "notes": "Largest primary failure bucket among rank1 losing races",
        }
    )
    summary_rows.append(
        {
            "section": "ANSWERS",
            "item": "MOST_IMPORTANT_FAILURE_FACTOR",
            "winner_mean": math.nan,
            "loser_mean": math.nan,
            "difference": math.nan,
            "winner_mode": largest_failure_reason,
            "loser_mode": "",
            "notes": "",
        }
    )

    if not best_row.empty:
        row = best_row.iloc[0]
        summary_rows.append(
            {
                "section": "ANSWERS",
                "item": "MOST_DEFENSIBLE_RANK1_PROFILE",
                "winner_mean": row["rank1_win_rate"],
                "loser_mean": row["races"],
                "difference": row["avg_winner_rank"],
                "winner_mode": str(row["pocket_id_v1"]),
                "loser_mode": "",
                "notes": "winner_mean=rank1_win_rate loser_mean=races difference=avg_winner_rank",
            }
        )

    if not worst_row.empty:
        row = worst_row.iloc[0]
        summary_rows.append(
            {
                "section": "ANSWERS",
                "item": "MOST_DANGEROUS_RANK1_PROFILE",
                "winner_mean": row["rank1_win_rate"],
                "loser_mean": row["races"],
                "difference": row["avg_winner_rank"],
                "winner_mode": str(row["pocket_id_v1"]),
                "loser_mode": "",
                "notes": "winner_mean=rank1_win_rate loser_mean=races difference=avg_winner_rank",
            }
        )

    return pd.DataFrame(summary_rows)


def main() -> None:
    profile_order = load_profile_order()
    load_dominance_reference_bands()

    replay_df = load_historical_replay()
    runners_df = add_dominance_features(replay_df)
    gap_df = load_rank_gap()

    rank1_rows = runners_df[runners_df["runner_rank"].eq(1)].copy()
    race_context_df = build_historical_trust_profiles(rank1_rows, gap_df, profile_order)
    race_df = build_rank1_race_frame(runners_df, race_context_df)
    race_df = assign_failure_reasons(race_df)

    failure_table = build_failure_reason_table(race_df)
    best_worst_df = build_best_worst_table(race_df)
    summary_df = build_summary(race_df, failure_table, best_worst_df)

    race_df.to_csv(AUDIT_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    failure_table.to_csv(FAILURE_REASONS_OUT, index=False)
    best_worst_df.to_csv(BEST_WORST_OUT, index=False)

    print(f"Wrote {AUDIT_OUT}")
    print(f"Wrote {SUMMARY_OUT}")
    print(f"Wrote {FAILURE_REASONS_OUT}")
    print(f"Wrote {BEST_WORST_OUT}")


if __name__ == "__main__":
    main()
