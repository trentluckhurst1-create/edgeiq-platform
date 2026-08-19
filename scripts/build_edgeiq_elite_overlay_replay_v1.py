from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
HISTORICAL_RUNNER_SCORES_PATH = DATA / "edgeiq_historical_runner_scores_v1.csv"
EXECUTION_REPLAY_PATH = DATA / "historical_execution_governance_replay_v1.csv"
TRUST_PROFILE_ENGINE_PATH = DATA / "edgeiq_trust_profile_engine_v1.csv"
RANK_GAP_ENGINE_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
RANK_PROBS_PATH = DATA / "edgeiq_probability_model_v1_rank_probs.csv"
SCORE_PROBS_PATH = DATA / "edgeiq_probability_model_v1_score_probs.csv"
HISTORICAL_DOMINANCE_REPLAY_PATH = DATA / "edgeiq_historical_dominance_replay_v1.csv"

REPLAY_OUT = DATA / "edgeiq_elite_overlay_replay_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_elite_overlay_replay_v1_summary.csv"
BY_OVERLAY_BAND_OUT = DATA / "edgeiq_elite_overlay_replay_v1_by_overlay_band.csv"
BY_RANK_OUT = DATA / "edgeiq_elite_overlay_replay_v1_by_rank.csv"
ELITE_VS_NON_ELITE_OUT = DATA / "edgeiq_elite_overlay_replay_v1_elite_vs_non_elite.csv"

RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]
SCORE_BAND_MODEL_ORDER = ["LT_40", "40_44", "45_49", "50_54", "55_59", "60_64", "65_69", "70_74", "75_79", "80_PLUS"]
SCORE_BAND_DISPLAY_MAP = {
    "LT_40": "<40",
    "40_44": "40-44",
    "45_49": "45-49",
    "50_54": "50-54",
    "55_59": "55-59",
    "60_64": "60-64",
    "65_69": "65-69",
    "70_74": "70-74",
    "75_79": "75-79",
    "80_PLUS": "80+",
}
SCORE_BAND_DISPLAY_ORDER = ["<40", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+"]
OVERLAY_BAND_ORDER = ["UNDERLAY", "0-5", "5-10", "10-15", "15-20", "20-30", "30-50", "50+"]
ELITE_BUCKET_ORDER = ["ALL_OVERLAYS", "ELITE_OVERLAYS", "NON_ELITE_OVERLAYS", "RULE_F_ALL_RUNNERS", "NON_RULE_F_ALL_RUNNERS"]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def normalize_horse_key(value: object, fallback: object = "") -> str:
    raw = clean_text(value)
    if raw == "":
        raw = clean_text(fallback)
    return re.sub(r"[^A-Z0-9]+", "", raw.upper())


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_join_key(df: pd.DataFrame, track_col: str = "track") -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df[track_col].map(normalize_track) + "|" + race_no


def build_runner_key(df: pd.DataFrame, track_col: str = "track", horse_key_col: str = "horse_key", horse_col: str = "horse") -> pd.Series:
    horse_component = [normalize_horse_key(horse_key, horse) for horse_key, horse in zip(df[horse_key_col], df[horse_col])]
    return build_join_key(df, track_col=track_col) + "|" + pd.Series(horse_component, index=df.index)


def rank_bucket(rank_value: object) -> str:
    rank_num = pd.to_numeric(rank_value, errors="coerce")
    if pd.isna(rank_num):
        return "UNKNOWN"
    rank_int = int(rank_num)
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


def score_band_model(score_value: object) -> str:
    score_num = pd.to_numeric(score_value, errors="coerce")
    if pd.isna(score_num):
        return "UNKNOWN"
    if score_num < 40:
        return "LT_40"
    if score_num < 45:
        return "40_44"
    if score_num < 50:
        return "45_49"
    if score_num < 55:
        return "50_54"
    if score_num < 60:
        return "55_59"
    if score_num < 65:
        return "60_64"
    if score_num < 70:
        return "65_69"
    if score_num < 75:
        return "70_74"
    if score_num < 80:
        return "75_79"
    return "80_PLUS"


def score_band_display(model_band: object) -> str:
    return SCORE_BAND_DISPLAY_MAP.get(clean_text(model_band), "UNKNOWN")


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


def first_valid_text(values: pd.Series, default: str = "") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def first_valid_numeric(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return math.nan
    return float(clean.iloc[0])


def safe_prob(value: float) -> float:
    if pd.isna(value) or value <= 0:
        return 0.0
    return float(value)


def fair_odds(probability: float) -> float:
    probability = safe_prob(probability)
    if probability <= 0:
        return math.nan
    return 1.0 / probability


def softmax_probabilities(scores: pd.Series, temperature: float) -> pd.Series:
    numeric_scores = pd.to_numeric(scores, errors="coerce").fillna(0.0)
    scaled = numeric_scores / max(temperature, 1.0)
    scaled = scaled - scaled.max()
    exp_values = np.exp(scaled)
    denom = exp_values.sum()
    if denom <= 0:
        return pd.Series(np.repeat(1.0 / max(len(scores), 1), len(scores)), index=scores.index)
    return pd.Series(exp_values / denom, index=scores.index)


def overlay_band(edge_value: object) -> str:
    edge = pd.to_numeric(edge_value, errors="coerce")
    if pd.isna(edge):
        return "UNDERLAY"
    if edge < 0:
        return "UNDERLAY"
    if edge < 5:
        return "0-5"
    if edge < 10:
        return "5-10"
    if edge < 15:
        return "10-15"
    if edge < 20:
        return "15-20"
    if edge < 30:
        return "20-30"
    if edge < 50:
        return "30-50"
    return "50+"


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def load_probability_maps() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not RANK_PROBS_PATH.exists():
        raise FileNotFoundError(f"Missing rank probability file: {RANK_PROBS_PATH}")
    if not SCORE_PROBS_PATH.exists():
        raise FileNotFoundError(f"Missing score probability file: {SCORE_PROBS_PATH}")

    rank_df = pd.read_csv(RANK_PROBS_PATH, low_memory=False)
    score_df = pd.read_csv(SCORE_PROBS_PATH, low_memory=False)
    rank_df["rank_bucket"] = rank_df["rank_bucket"].fillna("").astype(str).map(clean_text)
    score_df["score_band"] = score_df["score_band"].fillna("").astype(str).map(clean_text)
    rank_df["true_win_rate"] = to_num(rank_df["true_win_rate"])
    score_df["true_win_rate"] = to_num(score_df["true_win_rate"])
    return rank_df, score_df


def load_historical_replay() -> pd.DataFrame:
    if not HISTORICAL_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing historical replay file: {HISTORICAL_REPLAY_PATH}")

    usecols = ["meeting_date", "track", "race_no", "horse", "horse_key", "runner_score", "runner_rank", "finish_position", "won"]
    df = pd.read_csv(HISTORICAL_REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "horse", "horse_key"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_score", "runner_rank", "finish_position", "won"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    df["placed"] = df["finish_position"].le(3).fillna(False).astype(int)
    df["field_size"] = df.groupby("join_key_v1")["horse"].transform("size")
    return df.copy()


def load_historical_runner_scores() -> pd.DataFrame:
    if not HISTORICAL_RUNNER_SCORES_PATH.exists():
        raise FileNotFoundError(f"Missing historical runner scores file: {HISTORICAL_RUNNER_SCORES_PATH}")

    usecols = ["meeting_date", "track", "race_no", "horse", "horse_key", "governance_band_hist_v1", "runner_score_hist_v1", "runner_rank_hist_v1"]
    df = pd.read_csv(HISTORICAL_RUNNER_SCORES_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "horse", "horse_key", "governance_band_hist_v1"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_score_hist_v1", "runner_rank_hist_v1"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    return df[["runner_join_key_v1", "governance_band_hist_v1", "runner_score_hist_v1", "runner_rank_hist_v1"]].copy()


def load_execution_replay() -> pd.DataFrame:
    if not EXECUTION_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing execution governance replay file: {EXECUTION_REPLAY_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "governance_band_hist_v1",
        "trust_index_v1",
        "trust_band_v1",
        "trust_profile_score_v1",
        "trust_profile_v1",
        "race_execution_class_v1",
        "join_key_v1",
        "runner_join_key_v1",
    ]
    df = pd.read_csv(EXECUTION_REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in [
        "meeting_date",
        "track",
        "horse",
        "horse_key",
        "governance_band_hist_v1",
        "trust_band_v1",
        "trust_profile_v1",
        "race_execution_class_v1",
        "join_key_v1",
        "runner_join_key_v1",
    ]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "trust_index_v1", "trust_profile_score_v1"]:
        df[col] = to_num(df[col])

    if df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)
    if df["runner_join_key_v1"].eq("").all():
        df["runner_join_key_v1"] = build_runner_key(df)

    return df[[
        "runner_join_key_v1",
        "governance_band_hist_v1",
        "trust_index_v1",
        "trust_band_v1",
        "trust_profile_score_v1",
        "trust_profile_v1",
        "race_execution_class_v1",
        "join_key_v1",
    ]].copy()


def load_rank_gap_race() -> pd.DataFrame:
    if not RANK_GAP_ENGINE_PATH.exists():
        raise FileNotFoundError(f"Missing rank gap engine file: {RANK_GAP_ENGINE_PATH}")

    usecols = ["meeting_date", "track", "race_no", "join_key_v1", "gap_1_2_band", "gap_1_3_band", "score_share_band"]
    df = pd.read_csv(RANK_GAP_ENGINE_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "join_key_v1", "gap_1_2_band", "gap_1_3_band", "score_share_band"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no"]:
        df[col] = to_num(df[col])

    if df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)

    race_df = (
        df.groupby("join_key_v1", dropna=False)
        .agg(
            gap_1_2_band=("gap_1_2_band", lambda s: first_valid_text(s, "UNKNOWN")),
            gap_1_3_band=("gap_1_3_band", lambda s: first_valid_text(s, "UNKNOWN")),
            score_share_band=("score_share_band", lambda s: first_valid_text(s, "UNKNOWN")),
        )
        .reset_index()
    )
    return race_df


def load_dominance_race() -> pd.DataFrame:
    if not HISTORICAL_DOMINANCE_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing historical dominance replay file: {HISTORICAL_DOMINANCE_REPLAY_PATH}")

    usecols = ["meeting_date", "track", "race_no", "horse", "runner_rank_hist_v1", "runner_score_hist_v1", "dominance_score_v1", "dominance_band_v1"]
    df = pd.read_csv(HISTORICAL_DOMINANCE_REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "horse", "dominance_band_v1"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_rank_hist_v1", "runner_score_hist_v1", "dominance_score_v1"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    df = df.sort_values(["join_key_v1", "runner_rank_hist_v1", "runner_score_hist_v1", "horse"], ascending=[True, True, False, True]).reset_index(drop=True)

    top_df = (
        df.groupby("join_key_v1", dropna=False)
        .agg(
            dominance_score_v1=("dominance_score_v1", first_valid_numeric),
            dominance_band_v1=("dominance_band_v1", lambda s: first_valid_text(s, "UNKNOWN")),
        )
        .reset_index()
    )
    top_df["dominance_certainty_band"] = top_df["dominance_score_v1"].apply(dominance_certainty_band)
    return top_df


def load_trust_profile_catalog() -> pd.DataFrame:
    if not TRUST_PROFILE_ENGINE_PATH.exists():
        return pd.DataFrame(columns=["trust_profile_v1"])
    df = pd.read_csv(TRUST_PROFILE_ENGINE_PATH, low_memory=False, usecols=["trust_profile_v1"])
    df["trust_profile_v1"] = df["trust_profile_v1"].fillna("").astype(str).map(clean_text)
    return df.drop_duplicates().reset_index(drop=True)


def build_runner_frame() -> pd.DataFrame:
    replay_df = load_historical_replay()
    score_df = load_historical_runner_scores()
    execution_df = load_execution_replay()
    gap_df = load_rank_gap_race()
    dominance_df = load_dominance_race()
    _trust_catalog_df = load_trust_profile_catalog()
    rank_probs_df, score_probs_df = load_probability_maps()

    df = replay_df.merge(score_df, on="runner_join_key_v1", how="left", suffixes=("", "_hist"))
    df = df.merge(execution_df, on="runner_join_key_v1", how="left", suffixes=("", "_exec"))
    df = df.merge(gap_df, on="join_key_v1", how="left")
    df = df.merge(dominance_df, on="join_key_v1", how="left")

    df["runner_score"] = to_num(df["runner_score"])
    df["runner_rank"] = to_num(df["runner_rank"])
    df["governance_band_hist_v1"] = df["governance_band_hist_v1"].replace("", pd.NA)
    if "governance_band_hist_v1_exec" in df.columns:
        df["governance_band_hist_v1"] = df["governance_band_hist_v1"].fillna(df["governance_band_hist_v1_exec"])
    df["governance_band_hist_v1"] = df["governance_band_hist_v1"].fillna("UNKNOWN")

    df["execution_class_v1"] = df["race_execution_class_v1"].fillna("UNKNOWN")
    df["trust_profile_v1"] = df["trust_profile_v1"].fillna("UNKNOWN")
    df["trust_band_v1"] = df["trust_band_v1"].fillna("UNKNOWN")
    df["dominance_certainty_band"] = df["dominance_certainty_band"].fillna(df["dominance_score_v1"].apply(dominance_certainty_band)).fillna("UNKNOWN")
    df["score_share_band"] = df["score_share_band"].fillna("UNKNOWN")

    df["rank_bucket"] = df["runner_rank"].apply(rank_bucket)
    df["score_band_model_v1"] = df["runner_score"].apply(score_band_model)
    df["score_band"] = df["score_band_model_v1"].apply(score_band_display)

    rank_map = rank_probs_df.rename(columns={"true_win_rate": "historical_rank_prob"})[["rank_bucket", "historical_rank_prob"]]
    score_map = score_probs_df.rename(columns={"true_win_rate": "historical_score_band_prob"})[["score_band", "historical_score_band_prob"]]

    df = df.merge(rank_map, on="rank_bucket", how="left")
    df = df.merge(score_map, left_on="score_band_model_v1", right_on="score_band", how="left", suffixes=("", "_prob"))
    if "score_band_prob" in df.columns:
        df = df.drop(columns=["score_band_prob"])
    if "score_band_y" in df.columns:
        df = df.drop(columns=["score_band_y"])
    if "score_band_x" in df.columns:
        df = df.rename(columns={"score_band_x": "score_band"})

    temperature = float(to_num(df["runner_score"]).std())
    if pd.isna(temperature) or temperature <= 0:
        temperature = 15.0

    df["race_softmax_prob"] = df.groupby("join_key_v1")["runner_score"].transform(lambda values: softmax_probabilities(values, temperature))
    df["blended_raw_prob_v1"] = pd.concat(
        [df["historical_rank_prob"], df["historical_score_band_prob"], df["race_softmax_prob"]],
        axis=1,
    ).mean(axis=1)
    df["empirical_probability"] = df["blended_raw_prob_v1"] / df.groupby("join_key_v1")["blended_raw_prob_v1"].transform("sum")
    df["empirical_probability"] = df["empirical_probability"].fillna(0.0)
    df["empirical_fair_odds"] = df["empirical_probability"].apply(fair_odds)
    df["market_proxy_fair_odds"] = to_num(df["field_size"])
    df["market_proxy_probability"] = 1.0 / df["market_proxy_fair_odds"]
    df["edge_proxy_pct"] = ((df["market_proxy_fair_odds"] / df["empirical_fair_odds"]) - 1.0) * 100.0
    df.loc[df["empirical_fair_odds"].isna() | df["market_proxy_fair_odds"].isna(), "edge_proxy_pct"] = math.nan
    df["overlay_band"] = df["edge_proxy_pct"].apply(overlay_band)
    df["elite_execution_flag"] = (
        df["execution_class_v1"].eq("FULL_EXECUTION")
        & df["trust_profile_v1"].isin(["ELITE", "STRONG"])
        & df["dominance_certainty_band"].isin(["VERY_HIGH", "HIGH"])
        & df["score_share_band"].eq("VERY_HIGH")
    )
    df["elite_execution_flag"] = df["elite_execution_flag"].map({True: "TRUE", False: "FALSE"})
    df["overlay_flag_v1"] = df["edge_proxy_pct"].gt(0).fillna(False)

    out_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "runner_rank",
        "runner_score",
        "rank_bucket",
        "score_band",
        "field_size",
        "finish_position",
        "won",
        "placed",
        "trust_profile_v1",
        "execution_class_v1",
        "dominance_certainty_band",
        "score_share_band",
        "historical_rank_prob",
        "historical_score_band_prob",
        "race_softmax_prob",
        "empirical_probability",
        "empirical_fair_odds",
        "market_proxy_fair_odds",
        "market_proxy_probability",
        "edge_proxy_pct",
        "overlay_band",
        "elite_execution_flag",
        "join_key_v1",
        "runner_join_key_v1",
        "trust_index_v1",
        "trust_band_v1",
        "trust_profile_score_v1",
        "gap_1_2_band",
        "gap_1_3_band",
        "dominance_score_v1",
        "overlay_flag_v1",
    ]
    return df[out_cols].copy()


def summarise_overlay_band(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby("overlay_band", dropna=False)
        .agg(
            runners=("horse", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_rank=("runner_rank", "mean"),
            avg_score=("runner_score", "mean"),
            avg_edge_proxy_pct=("edge_proxy_pct", "mean"),
        )
        .reset_index()
    )
    grouped["win_rate"] = grouped["wins"] / grouped["runners"]
    grouped["place_rate"] = grouped["places"] / grouped["runners"]
    grouped["sort_order_v1"] = grouped["overlay_band"].map({name: idx for idx, name in enumerate(OVERLAY_BAND_ORDER, start=1)}).fillna(999)
    grouped = grouped.sort_values(["sort_order_v1", "overlay_band"]).drop(columns=["sort_order_v1"]).reset_index(drop=True)
    return grouped[["overlay_band", "runners", "wins", "places", "win_rate", "place_rate", "avg_rank", "avg_score", "avg_edge_proxy_pct"]].copy()


def summarise_by_rank(df: pd.DataFrame) -> pd.DataFrame:
    overlay_df = df[df["overlay_flag_v1"]].copy()
    grouped = (
        overlay_df.groupby(["elite_execution_flag", "rank_bucket"], dropna=False)
        .agg(
            runners=("horse", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_edge_proxy_pct=("edge_proxy_pct", "mean"),
        )
        .reset_index()
    )
    grouped["win_rate"] = grouped["wins"] / grouped["runners"]
    grouped["place_rate"] = grouped["places"] / grouped["runners"]
    grouped["elite_sort_v1"] = grouped["elite_execution_flag"].map({"TRUE": 1, "FALSE": 2}).fillna(999)
    grouped["rank_sort_v1"] = grouped["rank_bucket"].map({name: idx for idx, name in enumerate(RANK_BUCKET_ORDER, start=1)}).fillna(999)
    grouped = grouped.sort_values(["elite_sort_v1", "rank_sort_v1"]).drop(columns=["elite_sort_v1", "rank_sort_v1"]).reset_index(drop=True)
    return grouped[["elite_execution_flag", "rank_bucket", "runners", "wins", "places", "win_rate", "place_rate", "avg_edge_proxy_pct"]].copy()


def summarise_elite_vs_non_elite(df: pd.DataFrame) -> pd.DataFrame:
    buckets = {
        "ALL_OVERLAYS": df[df["overlay_flag_v1"]].copy(),
        "ELITE_OVERLAYS": df[df["overlay_flag_v1"] & df["elite_execution_flag"].eq("TRUE")].copy(),
        "NON_ELITE_OVERLAYS": df[df["overlay_flag_v1"] & df["elite_execution_flag"].eq("FALSE")].copy(),
        "RULE_F_ALL_RUNNERS": df[df["elite_execution_flag"].eq("TRUE")].copy(),
        "NON_RULE_F_ALL_RUNNERS": df[df["elite_execution_flag"].eq("FALSE")].copy(),
    }
    rows: list[dict[str, object]] = []
    for bucket_name in ELITE_BUCKET_ORDER:
        subset = buckets[bucket_name]
        rows.append(
            {
                "bucket": bucket_name,
                "runners": int(len(subset)),
                "races": int(subset["join_key_v1"].nunique()),
                "wins": int(subset["won"].sum()),
                "places": int(subset["placed"].sum()),
                "win_rate": float(subset["won"].mean()) if len(subset) else math.nan,
                "place_rate": float(subset["placed"].mean()) if len(subset) else math.nan,
                "avg_finish": float(subset["finish_position"].mean()) if len(subset) else math.nan,
                "avg_rank": float(subset["runner_rank"].mean()) if len(subset) else math.nan,
                "avg_score": float(subset["runner_score"].mean()) if len(subset) else math.nan,
            }
        )
    return pd.DataFrame(rows)


def build_summary(df: pd.DataFrame, elite_vs_df: pd.DataFrame) -> pd.DataFrame:
    overlay_df = df[df["overlay_flag_v1"]].copy()
    elite_overlay_df = overlay_df[overlay_df["elite_execution_flag"].eq("TRUE")].copy()
    non_elite_overlay_df = overlay_df[overlay_df["elite_execution_flag"].eq("FALSE")].copy()

    rows = [
        {"metric": "total_rows", "value": int(len(df))},
        {"metric": "total_races", "value": int(df["join_key_v1"].nunique())},
        {"metric": "overlay_rows", "value": int(len(overlay_df))},
        {"metric": "elite_overlay_rows", "value": int(len(elite_overlay_df))},
        {"metric": "non_elite_overlay_rows", "value": int(len(non_elite_overlay_df))},
        {"metric": "all_overlay_win_rate", "value": float(overlay_df["won"].mean()) if len(overlay_df) else math.nan},
        {"metric": "elite_overlay_win_rate", "value": float(elite_overlay_df["won"].mean()) if len(elite_overlay_df) else math.nan},
        {"metric": "non_elite_overlay_win_rate", "value": float(non_elite_overlay_df["won"].mean()) if len(non_elite_overlay_df) else math.nan},
        {"metric": "all_overlay_place_rate", "value": float(overlay_df["placed"].mean()) if len(overlay_df) else math.nan},
        {"metric": "elite_overlay_place_rate", "value": float(elite_overlay_df["placed"].mean()) if len(elite_overlay_df) else math.nan},
        {"metric": "non_elite_overlay_place_rate", "value": float(non_elite_overlay_df["placed"].mean()) if len(non_elite_overlay_df) else math.nan},
    ]

    elite_row = elite_vs_df[elite_vs_df["bucket"].eq("ELITE_OVERLAYS")]
    non_elite_row = elite_vs_df[elite_vs_df["bucket"].eq("NON_ELITE_OVERLAYS")]
    if not elite_row.empty and not non_elite_row.empty:
        elite_win = float(elite_row["win_rate"].iloc[0])
        non_elite_win = float(non_elite_row["win_rate"].iloc[0])
        elite_place = float(elite_row["place_rate"].iloc[0])
        non_elite_place = float(non_elite_row["place_rate"].iloc[0])
        answer = "YES" if elite_win > non_elite_win and elite_place > non_elite_place else "PARTIAL" if elite_win > non_elite_win or elite_place > non_elite_place else "NO"
        rows.extend(
            [
                {"metric": "elite_vs_non_elite_overlay_answer", "value": answer},
                {"metric": "elite_minus_non_elite_overlay_win_rate", "value": elite_win - non_elite_win},
                {"metric": "elite_minus_non_elite_overlay_place_rate", "value": elite_place - non_elite_place},
            ]
        )

    return pd.DataFrame(rows)


def main() -> None:
    df = build_runner_frame()
    by_overlay_band_df = summarise_overlay_band(df)
    by_rank_df = summarise_by_rank(df)
    elite_vs_df = summarise_elite_vs_non_elite(df)
    summary_df = build_summary(df, elite_vs_df)

    out_df = df[[
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "runner_rank",
        "runner_score",
        "rank_bucket",
        "score_band",
        "field_size",
        "finish_position",
        "won",
        "placed",
        "trust_profile_v1",
        "execution_class_v1",
        "dominance_certainty_band",
        "score_share_band",
        "historical_rank_prob",
        "historical_score_band_prob",
        "race_softmax_prob",
        "empirical_probability",
        "empirical_fair_odds",
        "market_proxy_fair_odds",
        "edge_proxy_pct",
        "overlay_band",
        "elite_execution_flag",
    ]].copy()

    out_df.to_csv(REPLAY_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    by_overlay_band_df.to_csv(BY_OVERLAY_BAND_OUT, index=False)
    by_rank_df.to_csv(BY_RANK_OUT, index=False)
    elite_vs_df.to_csv(ELITE_VS_NON_ELITE_OUT, index=False)

    print("[EDGEIQ_ELITE_OVERLAY_REPLAY_V1] COMPLETE")
    print(f"replay_out={REPLAY_OUT}")
    print(f"summary_out={SUMMARY_OUT}")
    print(f"by_overlay_band_out={BY_OVERLAY_BAND_OUT}")
    print(f"by_rank_out={BY_RANK_OUT}")
    print(f"elite_vs_non_elite_out={ELITE_VS_NON_ELITE_OUT}")
    print(f"rows={len(out_df)}")
    print(f"races={out_df['meeting_date'].astype(str).str[:10].count() and out_df.groupby(['meeting_date','track','race_no']).ngroups}")


if __name__ == "__main__":
    main()
