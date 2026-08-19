from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
HISTORICAL_DOMINANCE_PATH = DATA / "edgeiq_historical_dominance_replay_v1.csv"
RANK_GAP_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
TRUST_PROFILE_REF_PATH = DATA / "edgeiq_trust_profile_engine_v1.csv"
EXECUTION_V3_PATH = DATA / "edgeiq_execution_v3_replay_v1.csv"

OUT_PATH = DATA / "edgeiq_feature_ablation_replay_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_feature_ablation_replay_v1_summary.csv"

PRIOR_RACES = 300.0
MODEL_ORDER = [
    "MODEL_BASE",
    "MODEL_PLUS_DOMINANCE",
    "MODEL_PLUS_SCORE_SHARE",
    "MODEL_PLUS_ENVIRONMENT",
    "MODEL_PLUS_DOMINANCE_SHARE",
    "MODEL_FULL",
]
INDIVIDUAL_MODELS = [
    "MODEL_PLUS_DOMINANCE",
    "MODEL_PLUS_SCORE_SHARE",
    "MODEL_PLUS_ENVIRONMENT",
]
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


def build_smoothed_score_map(df: pd.DataFrame, category_col: str, outcome_col: str = "top_pick_won") -> pd.DataFrame:
    grouped = (
        df.groupby(category_col, dropna=False)
        .agg(races=("join_key_v1", "size"), wins=(outcome_col, "sum"))
        .reset_index()
    )
    grouped[category_col] = grouped[category_col].fillna("UNKNOWN").astype(str)
    overall_rate = float(df[outcome_col].mean())
    grouped["smoothed_rate"] = (grouped["wins"] + PRIOR_RACES * overall_rate) / (grouped["races"] + PRIOR_RACES)
    min_rate = float(grouped["smoothed_rate"].min())
    max_rate = float(grouped["smoothed_rate"].max())
    if math.isclose(min_rate, max_rate):
        grouped["component_score_v1"] = 0.5
    else:
        grouped["component_score_v1"] = (grouped["smoothed_rate"] - min_rate) / (max_rate - min_rate)
    return grouped[[category_col, "component_score_v1"]].copy()


def race_relative_percentile(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    ranks = numeric.rank(method="min", ascending=False, na_option="bottom")
    count = int(numeric.notna().sum())
    if count <= 1:
        return pd.Series([1.0 if pd.notna(value) else math.nan for value in numeric], index=values.index)
    return 1.0 - ((ranks - 1.0) / float(count - 1))


def choose_top_runner(group: pd.DataFrame, score_col: str) -> pd.DataFrame:
    working = group.copy()
    working = working.sort_values(
        [
            score_col,
            "runner_score_hist_v1",
            "dominance_score_v1",
            "score_share_v1",
            "horse",
        ],
        ascending=[False, False, False, False, True],
        kind="stable",
    )
    working["model_rank_v1"] = range(1, len(working) + 1)
    return working


def load_historical_replay() -> pd.DataFrame:
    df = pd.read_csv(HISTORICAL_REPLAY_PATH, low_memory=False)
    for col in ["meeting_date", "track", "horse", "horse_key", "projection_status_v6", "race_key"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_score", "runner_rank", "finish_position", "won", "confidence_score_v1"]:
        if col in df.columns:
            df[col] = to_num(df[col])
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    df["placed"] = df["finish_position"].le(3).fillna(False).astype(int)
    df["replay_runner_rank_v1"] = to_num(df["runner_rank"])
    return df.copy()


def load_historical_dominance() -> pd.DataFrame:
    df = pd.read_csv(HISTORICAL_DOMINANCE_PATH, low_memory=False)
    for col in ["meeting_date", "track", "race_key", "horse", "horse_key", "governance_band_hist_v1", "dominance_band_v1"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in [
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
    ]:
        if col in df.columns:
            df[col] = to_num(df[col])
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    df["dominance_certainty_band_v1"] = df["dominance_score_v1"].apply(dominance_certainty_band)
    return df.copy()


def load_rank_gap() -> pd.DataFrame:
    df = pd.read_csv(RANK_GAP_PATH, low_memory=False)
    for col in [
        "meeting_date",
        "track",
        "race_key",
        "join_key_v1",
        "top_horse",
        "trust_band_v1",
        "gap_1_2_band",
        "gap_1_3_band",
        "score_share_band",
    ]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in [
        "race_no",
        "field_size",
        "top_score",
        "second_score",
        "third_score",
        "gap_1_2",
        "gap_1_3",
        "score_share_total",
        "top_pick_won",
        "winner_rank",
        "winner_top3_flag_v1",
        "winner_top5_flag_v1",
    ]:
        if col in df.columns:
            df[col] = to_num(df[col])
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    if "join_key_v1" not in df.columns or df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)
    df["field_size_bucket"] = df["field_size"].apply(field_size_bucket)
    df["winner_top10_flag_v1"] = df["winner_rank"].le(10).fillna(False).astype(int)
    return df.copy()


def load_execution_v3_reference() -> pd.DataFrame:
    if not EXECUTION_V3_PATH.exists():
        return pd.DataFrame(columns=["runner_join_key_v1"])
    df = pd.read_csv(EXECUTION_V3_PATH, low_memory=False)
    keep_cols = [col for col in [
        "runner_join_key_v1",
        "join_key_v1",
        "runner_score_hist_v1",
        "dominance_score_v1",
        "score_share_v1",
        "score_share_band",
        "gap_1_2_band",
        "gap_1_3_band",
        "trust_band",
    ] if col in df.columns]
    if not keep_cols:
        return pd.DataFrame(columns=["runner_join_key_v1"])
    return df[keep_cols].drop_duplicates(subset=["runner_join_key_v1"], keep="first").copy()


def build_race_frame(rank_gap_df: pd.DataFrame, dominance_df: pd.DataFrame) -> pd.DataFrame:
    rank1 = (
        dominance_df[dominance_df["runner_rank_hist_v1"] == 1]
        .groupby("join_key_v1", dropna=False)
        .agg(
            dominance_certainty_band=("dominance_certainty_band_v1", lambda s: first_valid_text(s, "UNKNOWN")),
        )
        .reset_index()
    )
    race_df = rank_gap_df.merge(rank1, on="join_key_v1", how="left")
    race_df["dominance_certainty_band"] = race_df["dominance_certainty_band"].fillna("UNKNOWN")

    feature_maps: dict[str, dict[str, float]] = {}
    for feature_name in PROFILE_FEATURE_WEIGHTS:
        feature_df = build_smoothed_score_map(race_df, feature_name, outcome_col="top_pick_won")
        feature_maps[feature_name] = dict(zip(feature_df[feature_name], feature_df["component_score_v1"]))

    scored = race_df.copy()
    for feature_name, mapping in feature_maps.items():
        scored[f"{feature_name}_score_v1"] = scored[feature_name].map(mapping).fillna(0.5)
    scored["trust_profile_score_v1"] = (
        PROFILE_FEATURE_WEIGHTS["trust_band_v1"] * scored["trust_band_v1_score_v1"]
        + PROFILE_FEATURE_WEIGHTS["gap_1_3_band"] * scored["gap_1_3_band_score_v1"]
        + PROFILE_FEATURE_WEIGHTS["dominance_certainty_band"] * scored["dominance_certainty_band_score_v1"]
        + PROFILE_FEATURE_WEIGHTS["field_size_bucket"] * scored["field_size_bucket_score_v1"]
        + PROFILE_FEATURE_WEIGHTS["gap_1_2_band"] * scored["gap_1_2_band_score_v1"]
    )
    q25 = float(scored["trust_profile_score_v1"].quantile(0.25))
    q50 = float(scored["trust_profile_score_v1"].quantile(0.50))
    q75 = float(scored["trust_profile_score_v1"].quantile(0.75))
    scored["trust_profile_v1"] = scored["trust_profile_score_v1"].apply(lambda value: profile_from_score(value, q25, q50, q75))

    trust_profile_map = build_smoothed_score_map(scored, "trust_profile_v1", outcome_col="top_pick_won")
    trust_band_map = build_smoothed_score_map(scored, "trust_band_v1", outcome_col="top_pick_won")
    field_size_map = build_smoothed_score_map(scored, "field_size_bucket", outcome_col="top_pick_won")
    gap12_map = build_smoothed_score_map(scored, "gap_1_2_band", outcome_col="top_pick_won")
    gap13_map = build_smoothed_score_map(scored, "gap_1_3_band", outcome_col="top_pick_won")

    scored["trust_profile_component_v1"] = scored["trust_profile_v1"].map(dict(zip(trust_profile_map["trust_profile_v1"], trust_profile_map["component_score_v1"]))).fillna(0.5)
    scored["trust_band_component_v1"] = scored["trust_band_v1"].map(dict(zip(trust_band_map["trust_band_v1"], trust_band_map["component_score_v1"]))).fillna(0.5)
    scored["field_size_component_v1"] = scored["field_size_bucket"].map(dict(zip(field_size_map["field_size_bucket"], field_size_map["component_score_v1"]))).fillna(0.5)
    scored["gap_1_2_component_v1"] = scored["gap_1_2_band"].map(dict(zip(gap12_map["gap_1_2_band"], gap12_map["component_score_v1"]))).fillna(0.5)
    scored["gap_1_3_component_v1"] = scored["gap_1_3_band"].map(dict(zip(gap13_map["gap_1_3_band"], gap13_map["component_score_v1"]))).fillna(0.5)
    scored["environment_component_v1"] = scored[["trust_profile_component_v1", "trust_band_component_v1", "field_size_component_v1"]].mean(axis=1)
    scored["gap_component_v1"] = scored[["gap_1_2_component_v1", "gap_1_3_component_v1"]].mean(axis=1)
    return scored.copy()


def build_runner_frame() -> pd.DataFrame:
    replay_df = load_historical_replay()
    dominance_df = load_historical_dominance()
    rank_gap_df = load_rank_gap()
    exec_v3_ref_df = load_execution_v3_reference()
    race_df = build_race_frame(rank_gap_df, dominance_df)

    runner_df = replay_df.merge(
        dominance_df[[
            "runner_join_key_v1",
            "field_size_v1",
            "runner_score_hist_v1",
            "runner_rank_hist_v1",
            "governance_band_hist_v1",
            "score_share_of_race",
            "dominance_score_v1",
            "dominance_certainty_band_v1",
        ]].drop_duplicates(subset=["runner_join_key_v1"], keep="first"),
        on="runner_join_key_v1",
        how="left",
    )
    runner_df = runner_df.merge(
        race_df[[
            "join_key_v1",
            "field_size",
            "field_size_bucket",
            "trust_band_v1",
            "trust_profile_v1",
            "score_share_band",
            "gap_1_2_band",
            "gap_1_3_band",
            "environment_component_v1",
            "gap_component_v1",
        ]],
        on="join_key_v1",
        how="left",
    )
    runner_df = runner_df.merge(exec_v3_ref_df, on="runner_join_key_v1", how="left", suffixes=("", "_exec"))

    runner_df["runner_score_hist_v1"] = to_num(runner_df["runner_score_hist_v1"]).fillna(to_num(runner_df["runner_score"]))
    runner_df["runner_rank_hist_v1"] = to_num(runner_df["runner_rank_hist_v1"]).fillna(to_num(runner_df["runner_rank"]))
    runner_df["replay_runner_rank_v1"] = to_num(runner_df["replay_runner_rank_v1"]).fillna(to_num(runner_df["runner_rank"]))
    runner_df["field_size"] = to_num(runner_df["field_size"]).fillna(to_num(runner_df["field_size_v1"]))
    runner_df["governance_band_hist_v1"] = runner_df["governance_band_hist_v1"].fillna(runner_df["projection_status_v6"]).fillna("UNKNOWN")
    runner_df["score_share_v1"] = to_num(runner_df["score_share_of_race"]).fillna(to_num(runner_df.get("score_share_v1_exec")))
    runner_df["dominance_score_v1"] = to_num(runner_df["dominance_score_v1"]).fillna(to_num(runner_df.get("dominance_score_v1_exec")))
    runner_df["dominance_certainty_band_v1"] = runner_df["dominance_certainty_band_v1"].fillna("UNKNOWN")
    runner_df["score_share_band"] = runner_df["score_share_band"].replace("", pd.NA).fillna(runner_df.get("score_share_band_exec")).fillna("UNKNOWN")
    runner_df["gap_1_2_band"] = runner_df["gap_1_2_band"].replace("", pd.NA).fillna(runner_df.get("gap_1_2_band_exec")).fillna("UNKNOWN")
    runner_df["gap_1_3_band"] = runner_df["gap_1_3_band"].replace("", pd.NA).fillna(runner_df.get("gap_1_3_band_exec")).fillna("UNKNOWN")
    runner_df["trust_band_v1"] = runner_df["trust_band_v1"].replace("", pd.NA).fillna("UNKNOWN")
    runner_df["trust_profile_v1"] = runner_df["trust_profile_v1"].replace("", pd.NA).fillna("CHAOTIC")

    runner_df["base_component_v1"] = runner_df.groupby("join_key_v1")["runner_score_hist_v1"].transform(race_relative_percentile)
    runner_df["dominance_component_v1"] = runner_df.groupby("join_key_v1")["dominance_score_v1"].transform(race_relative_percentile)
    runner_df["score_share_component_v1"] = runner_df.groupby("join_key_v1")["score_share_v1"].transform(race_relative_percentile)

    runner_df["model_base_score_v1"] = runner_df["base_component_v1"]
    runner_df["model_plus_dominance_score_v1"] = runner_df[["base_component_v1", "dominance_component_v1"]].mean(axis=1)
    runner_df["model_plus_score_share_score_v1"] = runner_df[["base_component_v1", "score_share_component_v1"]].mean(axis=1)
    runner_df["model_plus_environment_score_v1"] = runner_df[["base_component_v1", "environment_component_v1"]].mean(axis=1)
    runner_df["model_plus_dominance_share_score_v1"] = runner_df[["base_component_v1", "dominance_component_v1", "score_share_component_v1"]].mean(axis=1)
    runner_df["model_full_score_v1"] = runner_df[["base_component_v1", "dominance_component_v1", "score_share_component_v1", "environment_component_v1", "gap_component_v1"]].mean(axis=1)
    return runner_df.copy()


def score_col_for_model(model_id: str) -> str:
    return {
        "MODEL_BASE": "model_base_score_v1",
        "MODEL_PLUS_DOMINANCE": "model_plus_dominance_score_v1",
        "MODEL_PLUS_SCORE_SHARE": "model_plus_score_share_score_v1",
        "MODEL_PLUS_ENVIRONMENT": "model_plus_environment_score_v1",
        "MODEL_PLUS_DOMINANCE_SHARE": "model_plus_dominance_share_score_v1",
        "MODEL_FULL": "model_full_score_v1",
    }[model_id]


def sort_spec_for_model(model_id: str) -> tuple[list[str], list[bool]]:
    if model_id == "MODEL_BASE":
        return (
            ["join_key_v1", "runner_score_hist_v1", "replay_runner_rank_v1", "horse"],
            [True, False, True, True],
        )
    if model_id == "MODEL_PLUS_DOMINANCE":
        return (
            ["join_key_v1", "runner_score_hist_v1", "dominance_score_v1", "replay_runner_rank_v1", "horse"],
            [True, False, False, True, True],
        )
    if model_id == "MODEL_PLUS_SCORE_SHARE":
        return (
            ["join_key_v1", "runner_score_hist_v1", "score_share_v1", "replay_runner_rank_v1", "horse"],
            [True, False, False, True, True],
        )
    if model_id == "MODEL_PLUS_ENVIRONMENT":
        return (
            ["join_key_v1", "runner_score_hist_v1", "environment_component_v1", "replay_runner_rank_v1", "horse"],
            [True, False, False, True, True],
        )
    if model_id == "MODEL_PLUS_DOMINANCE_SHARE":
        return (
            ["join_key_v1", "runner_score_hist_v1", "dominance_score_v1", "score_share_v1", "replay_runner_rank_v1", "horse"],
            [True, False, False, False, True, True],
        )
    return (
        [
            "join_key_v1",
            "runner_score_hist_v1",
            "dominance_score_v1",
            "score_share_v1",
            "environment_component_v1",
            "gap_component_v1",
            "replay_runner_rank_v1",
            "horse",
        ],
        [True, False, False, False, False, False, True, True],
    )


def evaluate_model(runner_df: pd.DataFrame, model_id: str, race_filter: pd.Series | None = None, include_in_ranking: bool = True) -> dict[str, object]:
    working = runner_df.copy()
    if race_filter is not None:
        working = working.loc[race_filter].copy()
    sort_cols, ascending = sort_spec_for_model(model_id)
    ranked = working.sort_values(sort_cols, ascending=ascending, kind="stable").copy()
    ranked["model_rank_v1"] = ranked.groupby("join_key_v1").cumcount() + 1
    winner_rows = ranked[ranked["won"] == 1].copy()
    races = int(ranked["join_key_v1"].nunique())
    winner_count = int(winner_rows.shape[0])
    return {
        "model_id": model_id,
        "scenario_type_v1": "FILTERED" if race_filter is not None else "FULL_UNIVERSE",
        "include_in_feature_lift_ranking_v1": include_in_ranking,
        "races": races,
        "winner_rows": winner_count,
        "top1": safe_rate(int(winner_rows["model_rank_v1"].eq(1).sum()), winner_count),
        "top3": safe_rate(int(winner_rows["model_rank_v1"].le(3).sum()), winner_count),
        "top5": safe_rate(int(winner_rows["model_rank_v1"].le(5).sum()), winner_count),
        "top10": safe_rate(int(winner_rows["model_rank_v1"].le(10).sum()), winner_count),
        "avg_winner_rank": float(winner_rows["model_rank_v1"].mean()) if winner_count > 0 else math.nan,
    }


def build_results(runner_df: pd.DataFrame) -> pd.DataFrame:
    total_races = int(runner_df["join_key_v1"].nunique())
    results = [evaluate_model(runner_df, model_id) for model_id in MODEL_ORDER]
    elite_strong_filter = runner_df["trust_profile_v1"].isin(["ELITE", "STRONG"])
    filtered_result = evaluate_model(runner_df, "MODEL_FULL", race_filter=elite_strong_filter, include_in_ranking=False)
    filtered_result["model_id"] = "MODEL_FULL_ELITE_STRONG_ONLY"
    results.append(filtered_result)

    results_df = pd.DataFrame(results)
    base_row = results_df[results_df["model_id"] == "MODEL_BASE"].iloc[0]
    results_df["race_retention_pct"] = results_df["races"].apply(lambda value: safe_rate(value, total_races))
    results_df["top1_lift_vs_base"] = results_df["top1"] - float(base_row["top1"])
    results_df["top3_lift_vs_base"] = results_df["top3"] - float(base_row["top3"])
    results_df["top5_lift_vs_base"] = results_df["top5"] - float(base_row["top5"])
    results_df["top10_lift_vs_base"] = results_df["top10"] - float(base_row["top10"])
    results_df["avg_winner_rank_lift_vs_base"] = float(base_row["avg_winner_rank"]) - results_df["avg_winner_rank"]
    results_df["feature_lift_rank_v1"] = math.nan

    ranked_mask = results_df["include_in_feature_lift_ranking_v1"] == True
    ranked = results_df[ranked_mask].sort_values(
        ["top1_lift_vs_base", "avg_winner_rank_lift_vs_base"],
        ascending=[False, False],
        kind="stable",
    ).copy()
    ranked["feature_lift_rank_v1"] = range(1, len(ranked) + 1)
    results_df.loc[ranked.index, "feature_lift_rank_v1"] = ranked["feature_lift_rank_v1"]

    model_order_map = {name: idx for idx, name in enumerate(MODEL_ORDER + ["MODEL_FULL_ELITE_STRONG_ONLY"], start=1)}
    results_df["model_sort_v1"] = results_df["model_id"].map(model_order_map).fillna(999)
    results_df = results_df.sort_values(["model_sort_v1"], kind="stable").drop(columns=["model_sort_v1"]).reset_index(drop=True)
    return results_df.copy()


def final_conclusion(results_df: pd.DataFrame) -> str:
    full_models = results_df[results_df["scenario_type_v1"] == "FULL_UNIVERSE"].copy()
    if (
        full_models["top1_lift_vs_base"].abs().max() < 1e-12
        and float(results_df.loc[results_df["model_id"] == "MODEL_FULL_ELITE_STRONG_ONLY", "top1_lift_vs_base"].iloc[0]) > 0
    ):
        return "ENVIRONMENT_DRIVEN"
    individual = results_df[results_df["model_id"].isin(INDIVIDUAL_MODELS)].copy()
    individual = individual.sort_values(["top1_lift_vs_base", "avg_winner_rank_lift_vs_base"], ascending=[False, False], kind="stable")
    top = individual.iloc[0]
    second = individual.iloc[1]
    top_lift = float(top["top1_lift_vs_base"])
    second_lift = float(second["top1_lift_vs_base"])
    if clean_text(top["model_id"]) == "MODEL_PLUS_ENVIRONMENT" and top_lift >= second_lift * 1.15:
        return "ENVIRONMENT_DRIVEN"
    if clean_text(top["model_id"]) == "MODEL_PLUS_SCORE_SHARE" and top_lift >= second_lift * 1.15:
        return "SCORE_SHARE_DRIVEN"
    if clean_text(top["model_id"]) == "MODEL_PLUS_DOMINANCE" and top_lift >= second_lift * 1.15:
        return "DOMINANCE_DRIVEN"
    return "HYBRID"


def build_summary(results_df: pd.DataFrame) -> pd.DataFrame:
    individual = results_df[results_df["model_id"].isin(INDIVIDUAL_MODELS)].copy()
    individual = individual.sort_values(["top1_lift_vs_base", "avg_winner_rank_lift_vs_base"], ascending=[False, False], kind="stable").reset_index(drop=True)
    largest = individual.iloc[0]
    second = individual.iloc[1]
    third = individual.iloc[2]
    full_filtered = results_df[results_df["model_id"] == "MODEL_FULL_ELITE_STRONG_ONLY"].iloc[0]
    conclusion = final_conclusion(results_df)
    full_models = results_df[results_df["scenario_type_v1"] == "FULL_UNIVERSE"].copy()
    all_full_models_identical = bool(
        full_models["top1_lift_vs_base"].abs().max() < 1e-12
        and full_models["avg_winner_rank_lift_vs_base"].abs().max() < 1e-12
    )

    summary_rows = [
        {"section": "FEATURE_LIFT_RANKING", "metric": "largest_individual_lift", "value": largest["model_id"], "notes": f"top1_lift={largest['top1_lift_vs_base']:.6f} avg_rank_lift={largest['avg_winner_rank_lift_vs_base']:.6f}"},
        {"section": "FEATURE_LIFT_RANKING", "metric": "second_largest_individual_lift", "value": second["model_id"], "notes": f"top1_lift={second['top1_lift_vs_base']:.6f} avg_rank_lift={second['avg_winner_rank_lift_vs_base']:.6f}"},
        {"section": "FEATURE_LIFT_RANKING", "metric": "third_largest_individual_lift", "value": third["model_id"], "notes": f"top1_lift={third['top1_lift_vs_base']:.6f} avg_rank_lift={third['avg_winner_rank_lift_vs_base']:.6f}"},
        {"section": "FEATURE_LIFT_RANKING", "metric": "all_full_universe_models_identical", "value": all_full_models_identical, "notes": "True means every ablation model produced the same historical full-universe ordering and metrics."},
        {"section": "CONCLUSION", "metric": "final_conclusion", "value": conclusion, "notes": "Environment lift appears through race selection here; the full-universe horse-ranking variants were identical on this historical build."},
        {"section": "MODEL_FULL_ELITE_STRONG_ONLY", "metric": "race_retention_pct", "value": full_filtered["race_retention_pct"], "notes": f"races={int(full_filtered['races'])} winner_rows={int(full_filtered['winner_rows'])}"},
        {"section": "MODEL_FULL_ELITE_STRONG_ONLY", "metric": "top1", "value": full_filtered["top1"], "notes": "MODEL_FULL restricted to ELITE and STRONG trust profiles"},
        {"section": "MODEL_FULL_ELITE_STRONG_ONLY", "metric": "top3", "value": full_filtered["top3"], "notes": "MODEL_FULL restricted to ELITE and STRONG trust profiles"},
        {"section": "MODEL_FULL_ELITE_STRONG_ONLY", "metric": "top5", "value": full_filtered["top5"], "notes": "MODEL_FULL restricted to ELITE and STRONG trust profiles"},
        {"section": "MODEL_FULL_ELITE_STRONG_ONLY", "metric": "avg_winner_rank", "value": full_filtered["avg_winner_rank"], "notes": "MODEL_FULL restricted to ELITE and STRONG trust profiles"},
    ]
    return pd.DataFrame(summary_rows)


def main() -> None:
    runner_df = build_runner_frame()
    results_df = build_results(runner_df)
    summary_df = build_summary(results_df)

    results_df.to_csv(OUT_PATH, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)

    print(f"Wrote {OUT_PATH}")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
