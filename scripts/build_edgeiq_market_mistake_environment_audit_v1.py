from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
TRUST_PROFILE_REF_PATH = DATA / "edgeiq_trust_profile_engine_v1.csv"
TRUST_INDEX_REF_PATH = DATA / "edgeiq_trust_index_v1.csv"
RANK_GAP_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
HISTORICAL_DOMINANCE_PATH = DATA / "edgeiq_historical_dominance_replay_v1.csv"
EXECUTION_V3_PATH = DATA / "edgeiq_execution_v3_replay_v1.csv"

AUDIT_OUT = DATA / "edgeiq_market_mistake_environment_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_market_mistake_environment_audit_v1_summary.csv"
ENVIRONMENTS_OUT = DATA / "edgeiq_market_mistake_environment_audit_v1_environments.csv"

PRIOR_RACES = 300.0
PREFERRED_PROFILE_ORDER = ["ELITE", "STRONG", "STANDARD", "CHAOTIC"]
PREFERRED_TRUST_BAND_ORDER = ["A_PLUS", "A", "B", "C", "D"]
PREFERRED_DOMINANCE_BAND_ORDER = ["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
PREFERRED_FIELD_SIZE_ORDER = ["LE_7", "8_10", "11_13", "14_PLUS", "UNKNOWN"]
PREFERRED_SCORE_SHARE_ORDER = ["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
PREFERRED_GAP_12_ORDER = ["TEN_PLUS", "FIVE_TO_10", "TWO_TO_5", "ZERO_TO_2", "UNKNOWN"]
PREFERRED_GAP_13_ORDER = ["FIFTEEN_PLUS", "TEN_TO_15", "FIVE_TO_10", "ZERO_TO_5", "UNKNOWN"]
PREFERRED_OVERLAY_ORDER = ["50+", "30-50", "20-30", "15-20", "10-15", "5-10", "0-5", "UNDERLAY"]
PROFILE_FEATURE_WEIGHTS = {
    "trust_band_v1": 0.35,
    "gap_1_3_band": 0.25,
    "dominance_certainty_band": 0.20,
    "field_size_bucket": 0.10,
    "gap_1_2_band": 0.10,
}


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def normalize_horse(value: object) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_join_key(df: pd.DataFrame, track_col: str = "track") -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df[track_col].map(normalize_track) + "|" + race_no


def build_runner_key(df: pd.DataFrame, track_col: str = "track", horse_key_col: str = "horse_key", horse_col: str = "horse") -> pd.Series:
    horse_component = []
    for horse_key, horse in zip(df[horse_key_col], df[horse_col]):
        candidate = clean_text(horse_key)
        if candidate == "":
            candidate = clean_text(horse)
        horse_component.append(normalize_horse(candidate))
    return build_join_key(df, track_col=track_col) + "|" + pd.Series(horse_component, index=df.index)


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def first_valid_text(values: pd.Series, default: str = "UNKNOWN") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def merge_order(preferred: list[str], seen: list[str]) -> list[str]:
    merged: list[str] = []
    for value in preferred + seen:
        text = clean_text(value)
        if text != "" and text not in merged:
            merged.append(text)
    return merged


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


def profile_from_score(value: object, q25: float, q50: float, q75: float) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "CHAOTIC"
    if number >= q75:
        return "ELITE"
    if number >= q50:
        return "STRONG"
    if number >= q25:
        return "STANDARD"
    return "CHAOTIC"


def environment_id_from_row(row: pd.Series) -> str:
    parts = [
        clean_text(row.get("trust_profile_v1", "UNKNOWN")) or "UNKNOWN",
        clean_text(row.get("trust_band_v1", "UNKNOWN")) or "UNKNOWN",
        clean_text(row.get("field_size_bucket", "UNKNOWN")) or "UNKNOWN",
        clean_text(row.get("score_share_band", "UNKNOWN")) or "UNKNOWN",
        clean_text(row.get("gap_1_2_band", "UNKNOWN")) or "UNKNOWN",
        clean_text(row.get("gap_1_3_band", "UNKNOWN")) or "UNKNOWN",
        clean_text(row.get("dominance_certainty_band", "UNKNOWN")) or "UNKNOWN",
    ]
    return "|".join(parts)


def build_smoothed_score_map(df: pd.DataFrame, category_col: str, outcome_col: str = "top_pick_won") -> pd.DataFrame:
    grouped = (
        df.groupby(category_col, dropna=False)
        .agg(races=("join_key_v1", "size"), wins=(outcome_col, "sum"))
        .reset_index()
    )
    grouped[category_col] = grouped[category_col].fillna("UNKNOWN").astype(str)
    overall_rate = float(df[outcome_col].mean())
    grouped["raw_top1_rate_v1"] = grouped["wins"] / grouped["races"]
    grouped["smoothed_top1_rate_v1"] = (grouped["wins"] + PRIOR_RACES * overall_rate) / (grouped["races"] + PRIOR_RACES)
    min_rate = float(grouped["smoothed_top1_rate_v1"].min())
    max_rate = float(grouped["smoothed_top1_rate_v1"].max())
    if math.isclose(min_rate, max_rate):
        grouped["feature_score_v1"] = 50.0
    else:
        grouped["feature_score_v1"] = 100.0 * (grouped["smoothed_top1_rate_v1"] - min_rate) / (max_rate - min_rate)
    grouped["feature_score_v1"] = grouped["feature_score_v1"].round(3)
    return grouped

def load_reference_orders() -> dict[str, list[str]]:
    profile_seen: list[str] = []
    trust_band_seen: list[str] = []
    dominance_seen: list[str] = []
    if TRUST_PROFILE_REF_PATH.exists():
        profile_df = pd.read_csv(TRUST_PROFILE_REF_PATH, usecols=["trust_profile_v1"], low_memory=False)
        profile_seen = [clean_text(value) for value in profile_df["trust_profile_v1"].dropna().tolist()]
    if TRUST_INDEX_REF_PATH.exists():
        trust_df = pd.read_csv(TRUST_INDEX_REF_PATH, usecols=["trust_band_v1", "dominance_certainty_band"], low_memory=False)
        trust_band_seen = [clean_text(value) for value in trust_df["trust_band_v1"].dropna().tolist()]
        dominance_seen = [clean_text(value) for value in trust_df["dominance_certainty_band"].dropna().tolist()]
    return {
        "profile_order": merge_order(PREFERRED_PROFILE_ORDER, profile_seen),
        "trust_band_order": merge_order(PREFERRED_TRUST_BAND_ORDER, trust_band_seen),
        "dominance_band_order": merge_order(PREFERRED_DOMINANCE_BAND_ORDER, dominance_seen),
        "field_size_order": PREFERRED_FIELD_SIZE_ORDER,
        "score_share_order": PREFERRED_SCORE_SHARE_ORDER,
        "gap_1_2_order": PREFERRED_GAP_12_ORDER,
        "gap_1_3_order": PREFERRED_GAP_13_ORDER,
        "overlay_order": PREFERRED_OVERLAY_ORDER,
    }


def load_historical_replay_counts() -> tuple[int, int]:
    replay = pd.read_csv(HISTORICAL_REPLAY_PATH, usecols=["meeting_date", "track", "race_no"], low_memory=False)
    replay["meeting_date"] = replay["meeting_date"].astype(str).str[:10]
    replay["track"] = replay["track"].fillna("").astype(str).map(clean_text)
    replay["race_no"] = to_num(replay["race_no"])
    replay["join_key_v1"] = build_join_key(replay)
    return int(replay.shape[0]), int(replay["join_key_v1"].nunique())


def load_rank_gap() -> pd.DataFrame:
    df = pd.read_csv(RANK_GAP_PATH, low_memory=False)
    text_cols = [
        "meeting_date",
        "track",
        "race_key",
        "join_key_v1",
        "top_horse",
        "trust_band_v1",
        "gap_1_2_band",
        "gap_1_3_band",
        "score_share_band",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).map(clean_text)
    numeric_cols = [
        "race_no",
        "field_size",
        "top_score",
        "second_score",
        "third_score",
        "gap_1_2",
        "gap_1_3",
        "total_race_score",
        "score_share_total",
        "top_pick_finish",
        "top_pick_won",
        "winner_rank",
        "winner_top3_flag_v1",
        "winner_top5_flag_v1",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_num(df[col])
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    if "join_key_v1" not in df.columns or df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)
    df["field_size_bucket"] = df["field_size"].apply(field_size_bucket)
    df["winner_top10_flag_v1"] = df["winner_rank"].le(10).fillna(False).astype(int)
    return df.copy()


def load_historical_dominance() -> pd.DataFrame:
    df = pd.read_csv(HISTORICAL_DOMINANCE_PATH, low_memory=False)
    text_cols = [
        "meeting_date",
        "track",
        "race_key",
        "horse",
        "horse_key",
        "governance_band_hist_v1",
        "dominance_band_v1",
        "dominance_rank_bucket_v1",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).map(clean_text)
    numeric_cols = [
        "race_no",
        "field_size_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
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
        "dominance_rank_v1",
        "dominance_percentile",
        "finish_position",
        "won",
        "placed",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_num(df[col])
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    df["placed"] = to_num(df["placed"]).fillna(df["finish_position"].le(3)).fillna(0).astype(int)
    df["dominance_certainty_band_runner_v1"] = df["dominance_score_v1"].apply(dominance_band)
    df["rank_bucket_v1"] = df["runner_rank_hist_v1"].apply(
        lambda value: "RANK_1" if pd.to_numeric(value, errors="coerce") == 1 else (
            "RANK_2" if pd.to_numeric(value, errors="coerce") == 2 else (
                "RANK_3" if pd.to_numeric(value, errors="coerce") == 3 else (
                    "RANK_4_5" if pd.notna(pd.to_numeric(value, errors="coerce")) and pd.to_numeric(value, errors="coerce") <= 5 else (
                        "RANK_6_10" if pd.notna(pd.to_numeric(value, errors="coerce")) and pd.to_numeric(value, errors="coerce") <= 10 else "RANK_11_PLUS"
                    )
                )
            )
        )
    )
    return df.copy()


def build_race_dominance_summary(dominance_df: pd.DataFrame) -> pd.DataFrame:
    rank1 = (
        dominance_df[dominance_df["runner_rank_hist_v1"] == 1]
        .groupby("join_key_v1", dropna=False)
        .agg(
            rank1_horse=("horse", lambda s: first_valid_text(s, "UNKNOWN")),
            rank1_governance=("governance_band_hist_v1", lambda s: first_valid_text(s, "UNKNOWN")),
            rank1_dominance_score=("dominance_score_v1", "mean"),
            rank1_score_share=("score_share_of_race", "mean"),
            rank1_runner_score=("runner_score_hist_v1", "mean"),
        )
        .reset_index()
    )
    rank2 = (
        dominance_df[dominance_df["runner_rank_hist_v1"] == 2]
        .groupby("join_key_v1", dropna=False)
        .agg(
            rank2_dominance_score=("dominance_score_v1", "mean"),
            rank2_score_share=("score_share_of_race", "mean"),
            rank2_runner_score=("runner_score_hist_v1", "mean"),
        )
        .reset_index()
    )
    rank3 = (
        dominance_df[dominance_df["runner_rank_hist_v1"] == 3]
        .groupby("join_key_v1", dropna=False)
        .agg(
            rank3_dominance_score=("dominance_score_v1", "mean"),
            rank3_score_share=("score_share_of_race", "mean"),
            rank3_runner_score=("runner_score_hist_v1", "mean"),
        )
        .reset_index()
    )
    race_summary = rank1.merge(rank2, on="join_key_v1", how="left").merge(rank3, on="join_key_v1", how="left")
    race_summary["dominance_certainty_score_v1"] = race_summary["rank1_dominance_score"]
    race_summary["dominance_certainty_band"] = race_summary["dominance_certainty_score_v1"].apply(dominance_band)
    race_summary["dominance_separation_race"] = race_summary["rank1_dominance_score"] - race_summary["rank2_dominance_score"]
    race_summary["score_share_separation_race"] = race_summary["rank1_score_share"] - race_summary["rank2_score_share"]
    race_summary["runner_score_separation_race"] = race_summary["rank1_runner_score"] - race_summary["rank2_runner_score"]
    return race_summary.copy()

def build_historical_trust_profiles(race_df: pd.DataFrame) -> pd.DataFrame:
    feature_maps: dict[str, dict[str, float]] = {}
    for feature_name in PROFILE_FEATURE_WEIGHTS:
        feature_map_df = build_smoothed_score_map(race_df, feature_name, outcome_col="top_pick_won")
        feature_maps[feature_name] = dict(zip(feature_map_df[feature_name], feature_map_df["feature_score_v1"]))

    scored = race_df.copy()
    for feature_name, mapping in feature_maps.items():
        scored[f"{feature_name}_score_v1"] = scored[feature_name].map(mapping).fillna(50.0)

    scored["trust_profile_score_v1"] = (
        PROFILE_FEATURE_WEIGHTS["trust_band_v1"] * scored["trust_band_v1_score_v1"]
        + PROFILE_FEATURE_WEIGHTS["gap_1_3_band"] * scored["gap_1_3_band_score_v1"]
        + PROFILE_FEATURE_WEIGHTS["dominance_certainty_band"] * scored["dominance_certainty_band_score_v1"]
        + PROFILE_FEATURE_WEIGHTS["field_size_bucket"] * scored["field_size_bucket_score_v1"]
        + PROFILE_FEATURE_WEIGHTS["gap_1_2_band"] * scored["gap_1_2_band_score_v1"]
    ).round(3)

    q25 = float(scored["trust_profile_score_v1"].quantile(0.25))
    q50 = float(scored["trust_profile_score_v1"].quantile(0.50))
    q75 = float(scored["trust_profile_score_v1"].quantile(0.75))
    scored["trust_profile_v1"] = scored["trust_profile_score_v1"].apply(lambda value: profile_from_score(value, q25, q50, q75))
    scored["learned_profile_q25_v1"] = q25
    scored["learned_profile_q50_v1"] = q50
    scored["learned_profile_q75_v1"] = q75
    return scored.copy()


def load_execution_v3() -> pd.DataFrame:
    df = pd.read_csv(EXECUTION_V3_PATH, low_memory=False)
    text_cols = [
        "rule_id",
        "rule_description",
        "meeting_date",
        "track",
        "race_key",
        "horse",
        "horse_key",
        "rank_bucket",
        "score_band",
        "governance",
        "dominance_band",
        "dominance_rank_bucket_v1",
        "score_share_band",
        "gap_1_2_band",
        "gap_1_3_band",
        "overlay_band",
        "trust_band",
        "runner_join_key_v1",
        "join_key_v1",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).map(clean_text)
    numeric_cols = [
        "rule_sort_order_v1",
        "race_no",
        "field_size",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "finish_position",
        "won",
        "placed",
        "confidence_score_v1",
        "dominance_score_v1",
        "dominance_rank_v1",
        "dominance_percentile",
        "score_rank_1",
        "score_rank_2",
        "score_rank_3",
        "dominance_gap_rank2",
        "dominance_gap_rank3",
        "dominance_vs_avg",
        "score_share_v1",
        "gap_1_2",
        "gap_1_3",
        "historical_rank_prob",
        "historical_score_band_prob",
        "race_softmax_prob",
        "empirical_probability",
        "empirical_fair_odds",
        "market_proxy_probability",
        "market_proxy_fair_odds",
        "edge_proxy_pct",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_num(df[col])
    return df.copy()


def prepare_race_environment_frame() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rank_gap_df = load_rank_gap()
    dominance_df = load_historical_dominance()
    race_dom_df = build_race_dominance_summary(dominance_df)

    race_df = rank_gap_df.merge(race_dom_df, on="join_key_v1", how="left")
    race_df["dominance_certainty_band"] = race_df["dominance_certainty_band"].fillna("UNKNOWN")
    race_df["rank1_governance"] = race_df["rank1_governance"].fillna("UNKNOWN")
    race_df = build_historical_trust_profiles(race_df)
    race_df["environment_id"] = race_df.apply(environment_id_from_row, axis=1)

    runner_df = dominance_df.merge(
        race_df[[
            "join_key_v1",
            "environment_id",
            "trust_profile_v1",
            "trust_band_v1",
            "field_size_bucket",
            "score_share_band",
            "gap_1_2_band",
            "gap_1_3_band",
            "dominance_certainty_band",
        ]],
        on="join_key_v1",
        how="left",
    )
    return race_df.copy(), runner_df.copy(), dominance_df.copy()


def build_environment_metrics(race_df: pd.DataFrame, runner_df: pd.DataFrame, execution_df: pd.DataFrame, orders: dict[str, list[str]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    env_metrics = (
        race_df.groupby(
            [
                "environment_id",
                "trust_profile_v1",
                "trust_band_v1",
                "field_size_bucket",
                "score_share_band",
                "gap_1_2_band",
                "gap_1_3_band",
                "dominance_certainty_band",
            ],
            dropna=False,
        )
        .agg(
            races=("join_key_v1", "nunique"),
            top1_rate=("top_pick_won", "mean"),
            top3_rate=("winner_top3_flag_v1", "mean"),
            top5_rate=("winner_top5_flag_v1", "mean"),
            avg_winner_rank=("winner_rank", "mean"),
            dominance_separation=("dominance_separation_race", "mean"),
            score_share_separation=("score_share_separation_race", "mean"),
            avg_trust_profile_score_v1=("trust_profile_score_v1", "mean"),
        )
        .reset_index()
    )

    rank_rates = (
        runner_df[runner_df["runner_rank_hist_v1"].isin([1, 2, 3])]
        .groupby(["environment_id", "runner_rank_hist_v1"], dropna=False)
        .agg(runners=("runner_join_key_v1", "size"), wins=("won", "sum"))
        .reset_index()
    )
    rank_rates["win_rate"] = rank_rates.apply(lambda row: safe_rate(row["wins"], row["runners"]), axis=1)
    rank_pivot = rank_rates.pivot(index="environment_id", columns="runner_rank_hist_v1", values="win_rate").reset_index()
    rank_pivot = rank_pivot.rename(columns={1.0: "rank1_win_rate", 2.0: "rank2_win_rate", 3.0: "rank3_win_rate", 1: "rank1_win_rate", 2: "rank2_win_rate", 3: "rank3_win_rate"})
    env_metrics = env_metrics.merge(rank_pivot, on="environment_id", how="left")
    env_metrics["rank1_minus_rank2_gap"] = env_metrics["rank1_win_rate"] - env_metrics["rank2_win_rate"]
    env_metrics["rank1_minus_rank3_gap"] = env_metrics["rank1_win_rate"] - env_metrics["rank3_win_rate"]

    exec_env = execution_df.merge(
        race_df[["join_key_v1", "environment_id"]].drop_duplicates(),
        on="join_key_v1",
        how="left",
    )
    exec_grouped = (
        exec_env.groupby(["environment_id", "rule_id"], dropna=False)
        .agg(signals=("runner_join_key_v1", "size"), wins=("won", "sum"), places=("placed", "sum"))
        .reset_index()
    )
    exec_grouped["win_rate"] = exec_grouped.apply(lambda row: safe_rate(row["wins"], row["signals"]), axis=1)
    exec_grouped["place_rate"] = exec_grouped.apply(lambda row: safe_rate(row["places"], row["signals"]), axis=1)
    exec_grouped = exec_grouped.sort_values(["environment_id", "win_rate", "signals"], ascending=[True, False, False], kind="stable")
    best_exec = exec_grouped.groupby("environment_id", dropna=False).head(1).copy()
    best_exec = best_exec.rename(
        columns={
            "rule_id": "best_execution_v3_rule",
            "signals": "best_execution_v3_signals",
            "wins": "best_execution_v3_wins",
            "places": "best_execution_v3_places",
            "win_rate": "best_execution_v3_win_rate",
            "place_rate": "best_execution_v3_place_rate",
        }
    )
    env_metrics = env_metrics.merge(best_exec, on="environment_id", how="left")

    env_metrics["sample_ge_300"] = env_metrics["races"].ge(300)
    env_metrics["sample_ge_1000"] = env_metrics["races"].ge(1000)
    env_metrics["sample_ge_2000"] = env_metrics["races"].ge(2000)

    profile_order = {name: idx for idx, name in enumerate(orders["profile_order"], start=1)}
    trust_band_order = {name: idx for idx, name in enumerate(orders["trust_band_order"], start=1)}
    field_order = {name: idx for idx, name in enumerate(orders["field_size_order"], start=1)}
    share_order = {name: idx for idx, name in enumerate(orders["score_share_order"], start=1)}
    gap12_order = {name: idx for idx, name in enumerate(orders["gap_1_2_order"], start=1)}
    gap13_order = {name: idx for idx, name in enumerate(orders["gap_1_3_order"], start=1)}
    dom_order = {name: idx for idx, name in enumerate(orders["dominance_band_order"], start=1)}

    env_metrics["profile_sort_v1"] = env_metrics["trust_profile_v1"].map(profile_order).fillna(999)
    env_metrics["trust_band_sort_v1"] = env_metrics["trust_band_v1"].map(trust_band_order).fillna(999)
    env_metrics["field_size_sort_v1"] = env_metrics["field_size_bucket"].map(field_order).fillna(999)
    env_metrics["score_share_sort_v1"] = env_metrics["score_share_band"].map(share_order).fillna(999)
    env_metrics["gap_1_2_sort_v1"] = env_metrics["gap_1_2_band"].map(gap12_order).fillna(999)
    env_metrics["gap_1_3_sort_v1"] = env_metrics["gap_1_3_band"].map(gap13_order).fillna(999)
    env_metrics["dominance_sort_v1"] = env_metrics["dominance_certainty_band"].map(dom_order).fillna(999)

    env_metrics = env_metrics.sort_values(["top1_rate", "races", "profile_sort_v1"], ascending=[False, False, True], kind="stable").reset_index(drop=True)
    env_metrics["environment_rank_v1"] = env_metrics.index + 1

    audit_df = race_df.merge(
        env_metrics[[
            "environment_id",
            "environment_rank_v1",
            "best_execution_v3_rule",
            "best_execution_v3_signals",
            "best_execution_v3_win_rate",
            "best_execution_v3_place_rate",
        ]],
        on="environment_id",
        how="left",
    )
    return audit_df.copy(), env_metrics.copy()


def choose_environment(env_df: pd.DataFrame, min_races: int, metric: str = "top1_rate", ascending: bool = False, require_exec_signals: int | None = None) -> pd.Series | None:
    eligible = env_df[env_df["races"] >= min_races].copy()
    if require_exec_signals is not None:
        eligible = eligible[eligible["best_execution_v3_signals"].fillna(0) >= require_exec_signals].copy()
    if eligible.empty:
        return None
    eligible = eligible.sort_values([metric, "races"], ascending=[ascending, False], kind="stable")
    return eligible.iloc[0]


def build_overlay_band_effects(execution_df: pd.DataFrame, orders: dict[str, list[str]]) -> pd.DataFrame:
    rank1_df = execution_df[(execution_df["rule_id"] == "RULE_A_POSITIVE_OVERLAY") & (execution_df["runner_rank_hist_v1"] == 1)].copy()
    grouped = (
        rank1_df.groupby("overlay_band", dropna=False)
        .agg(races=("join_key_v1", "nunique"), signals=("runner_join_key_v1", "size"), wins=("won", "sum"))
        .reset_index()
    )
    grouped["top_pick_overlay_win_rate"] = grouped.apply(lambda row: safe_rate(row["wins"], row["signals"]), axis=1)
    overlay_order = {name: idx for idx, name in enumerate(orders["overlay_order"], start=1)}
    grouped["overlay_sort_v1"] = grouped["overlay_band"].map(overlay_order).fillna(999)
    grouped = grouped.sort_values(["overlay_sort_v1"], kind="stable").reset_index(drop=True)
    return grouped.copy()


def determine_final_conclusion(environment_gap: float, overlay_gap: float) -> str:
    if pd.isna(environment_gap) and pd.isna(overlay_gap):
        return "HYBRID"
    if pd.isna(overlay_gap):
        return "RACE_DRIVEN"
    if pd.isna(environment_gap):
        return "HORSE_DRIVEN"
    if environment_gap >= overlay_gap * 1.15:
        return "RACE_DRIVEN"
    if overlay_gap >= environment_gap * 1.15:
        return "HORSE_DRIVEN"
    return "HYBRID"


def build_summary(audit_df: pd.DataFrame, env_df: pd.DataFrame, overlay_effect_df: pd.DataFrame, total_rows: int, total_races: int) -> pd.DataFrame:
    best_300 = choose_environment(env_df, 300)
    best_1000 = choose_environment(env_df, 1000)
    best_2000 = choose_environment(env_df, 2000)
    lowest_rank_300 = choose_environment(env_df, 300, metric="avg_winner_rank", ascending=True)
    strongest_dom_300 = choose_environment(env_df, 300, metric="dominance_separation", ascending=False)
    strongest_share_300 = choose_environment(env_df, 300, metric="score_share_separation", ascending=False)
    best_exec_300 = choose_environment(env_df, 300, metric="best_execution_v3_win_rate", ascending=False, require_exec_signals=300)

    eligible_env = env_df[env_df["races"] >= 300].copy()
    environment_gap = float(eligible_env["top1_rate"].max() - eligible_env["top1_rate"].min()) if not eligible_env.empty else math.nan

    eligible_overlay = overlay_effect_df[overlay_effect_df["signals"] >= 300].copy()
    if eligible_overlay.empty:
        overlay_gap = math.nan
        best_overlay_band = None
        worst_overlay_band = None
    else:
        overlay_gap = float(eligible_overlay["top_pick_overlay_win_rate"].max() - eligible_overlay["top_pick_overlay_win_rate"].min())
        best_overlay_band = eligible_overlay.sort_values(["top_pick_overlay_win_rate", "signals"], ascending=[False, False], kind="stable").iloc[0]
        worst_overlay_band = eligible_overlay.sort_values(["top_pick_overlay_win_rate", "signals"], ascending=[True, False], kind="stable").iloc[0]

    final_conclusion = determine_final_conclusion(environment_gap, overlay_gap)
    environment_more_than_overlay = "YES" if (pd.notna(environment_gap) and pd.notna(overlay_gap) and environment_gap > overlay_gap) else "NO"

    summary_rows: list[dict[str, object]] = [
        {"section": "OVERVIEW", "metric": "total_rows", "value": total_rows, "notes": "all historical replay runners"},
        {"section": "OVERVIEW", "metric": "total_races", "value": total_races, "notes": "all historical replay races"},
        {"section": "OVERVIEW", "metric": "environment_rows", "value": int(audit_df.shape[0]), "notes": "race-level environment audit rows"},
        {"section": "OVERVIEW", "metric": "environment_count", "value": int(env_df.shape[0]), "notes": "unique environment buckets"},
        {"section": "OVERVIEW", "metric": "environment_count_ge_300", "value": int(env_df[env_df["races"] >= 300].shape[0]), "notes": "minimum 300 races"},
        {"section": "OVERVIEW", "metric": "environment_count_ge_1000", "value": int(env_df[env_df["races"] >= 1000].shape[0]), "notes": "minimum 1000 races"},
        {"section": "OVERVIEW", "metric": "environment_count_ge_2000", "value": int(env_df[env_df["races"] >= 2000].shape[0]), "notes": "minimum 2000 races"},
    ]

    best_map = {
        "best_environment_ge_300": best_300,
        "best_environment_ge_1000": best_1000,
        "best_environment_ge_2000": best_2000,
        "lowest_avg_winner_rank_environment_ge_300": lowest_rank_300,
        "strongest_dominance_separation_environment_ge_300": strongest_dom_300,
        "strongest_score_share_separation_environment_ge_300": strongest_share_300,
        "best_execution_v3_environment_ge_300": best_exec_300,
    }
    for metric, row in best_map.items():
        if row is None:
            summary_rows.append({"section": "ENVIRONMENT_SELECTION", "metric": metric, "value": "NONE", "notes": "No eligible environment."})
            continue
        exec_win_rate = pd.to_numeric(row.get("best_execution_v3_win_rate"), errors="coerce")
        exec_signals = pd.to_numeric(row.get("best_execution_v3_signals"), errors="coerce")
        notes = (
            f"races={int(row['races'])} top1={row['top1_rate']:.6f} top3={row['top3_rate']:.6f} "
            f"top5={row['top5_rate']:.6f} avg_winner_rank={row['avg_winner_rank']:.6f} "
            f"best_exec_rule={clean_text(row.get('best_execution_v3_rule', '')) or 'NA'} "
            f"best_exec_win_rate={(f'{float(exec_win_rate):.6f}' if pd.notna(exec_win_rate) else 'NA')} "
            f"best_exec_signals={(int(exec_signals) if pd.notna(exec_signals) else 'NA')}"
        )
        summary_rows.append({"section": "ENVIRONMENT_SELECTION", "metric": metric, "value": row["environment_id"], "notes": notes})

    if best_overlay_band is not None:
        summary_rows.append({
            "section": "OVERLAY_EFFECT",
            "metric": "best_top_pick_overlay_band_ge_300",
            "value": best_overlay_band["overlay_band"],
            "notes": f"signals={int(best_overlay_band['signals'])} win_rate={best_overlay_band['top_pick_overlay_win_rate']:.6f}",
        })
    if worst_overlay_band is not None:
        summary_rows.append({
            "section": "OVERLAY_EFFECT",
            "metric": "worst_top_pick_overlay_band_ge_300",
            "value": worst_overlay_band["overlay_band"],
            "notes": f"signals={int(worst_overlay_band['signals'])} win_rate={worst_overlay_band['top_pick_overlay_win_rate']:.6f}",
        })

    summary_rows.extend([
        {"section": "EFFECT_SIZE", "metric": "environment_top1_rate_gap_ge_300", "value": environment_gap, "notes": "best minus worst eligible environment top1 rate"},
        {"section": "EFFECT_SIZE", "metric": "overlay_band_top_pick_win_rate_gap_ge_300", "value": overlay_gap, "notes": "best minus worst eligible top-pick overlay band win rate"},
        {"section": "EFFECT_SIZE", "metric": "does_race_environment_explain_more_than_overlay_size", "value": environment_more_than_overlay, "notes": "YES when environment gap > overlay band gap"},
        {"section": "CONCLUSION", "metric": "final_conclusion", "value": final_conclusion, "notes": "RACE_DRIVEN if environment effect is materially larger than overlay-size effect; HORSE_DRIVEN if the reverse; otherwise HYBRID."},
    ])

    return pd.DataFrame(summary_rows)


def main() -> None:
    orders = load_reference_orders()
    total_rows, total_races = load_historical_replay_counts()
    race_df, runner_df, _dominance_df = prepare_race_environment_frame()
    execution_df = load_execution_v3()
    audit_df, env_df = build_environment_metrics(race_df, runner_df, execution_df, orders)
    overlay_effect_df = build_overlay_band_effects(execution_df, orders)
    summary_df = build_summary(audit_df, env_df, overlay_effect_df, total_rows, total_races)

    audit_columns = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "join_key_v1",
        "environment_id",
        "environment_rank_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "field_size",
        "field_size_bucket",
        "score_share_band",
        "gap_1_2_band",
        "gap_1_3_band",
        "dominance_certainty_score_v1",
        "dominance_certainty_band",
        "top_horse",
        "rank1_horse",
        "rank1_governance",
        "top_pick_won",
        "winner_rank",
        "winner_top3_flag_v1",
        "winner_top5_flag_v1",
        "winner_top10_flag_v1",
        "top_score",
        "second_score",
        "third_score",
        "gap_1_2",
        "gap_1_3",
        "score_share_total",
        "rank1_dominance_score",
        "rank2_dominance_score",
        "rank3_dominance_score",
        "dominance_separation_race",
        "rank1_score_share",
        "rank2_score_share",
        "rank3_score_share",
        "score_share_separation_race",
        "runner_score_separation_race",
        "trust_profile_score_v1",
        "best_execution_v3_rule",
        "best_execution_v3_signals",
        "best_execution_v3_win_rate",
        "best_execution_v3_place_rate",
    ]
    audit_out = audit_df[[col for col in audit_columns if col in audit_df.columns]].sort_values(
        ["environment_rank_v1", "meeting_date", "track", "race_no"], kind="stable"
    )

    env_columns = [
        "environment_rank_v1",
        "environment_id",
        "trust_profile_v1",
        "trust_band_v1",
        "field_size_bucket",
        "score_share_band",
        "gap_1_2_band",
        "gap_1_3_band",
        "dominance_certainty_band",
        "races",
        "top1_rate",
        "top3_rate",
        "top5_rate",
        "avg_winner_rank",
        "rank1_win_rate",
        "rank2_win_rate",
        "rank3_win_rate",
        "rank1_minus_rank2_gap",
        "rank1_minus_rank3_gap",
        "dominance_separation",
        "score_share_separation",
        "avg_trust_profile_score_v1",
        "best_execution_v3_rule",
        "best_execution_v3_signals",
        "best_execution_v3_wins",
        "best_execution_v3_places",
        "best_execution_v3_win_rate",
        "best_execution_v3_place_rate",
        "sample_ge_300",
        "sample_ge_1000",
        "sample_ge_2000",
    ]
    env_out = env_df[[col for col in env_columns if col in env_df.columns]].copy()

    audit_out.to_csv(AUDIT_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    env_out.to_csv(ENVIRONMENTS_OUT, index=False)

    print(f"Wrote {AUDIT_OUT}")
    print(f"Wrote {SUMMARY_OUT}")
    print(f"Wrote {ENVIRONMENTS_OUT}")


if __name__ == "__main__":
    main()
