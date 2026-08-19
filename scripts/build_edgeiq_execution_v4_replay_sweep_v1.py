from __future__ import annotations

import math
import re
from itertools import product
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OVERLAY_PATH = DATA / "edgeiq_real_vs_fake_overlay_replay_v1.csv"
HIST_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
TRUST_PROFILE_REFERENCE_PATH = DATA / "edgeiq_trust_profile_engine_v1.csv"
GAP_ENGINE_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
HIST_DOMINANCE_PATH = DATA / "edgeiq_historical_dominance_replay_v1.csv"

RULES_OUT = DATA / "edgeiq_execution_v4_replay_sweep_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_execution_v4_replay_sweep_v1_summary.csv"
TOP_RULES_OUT = DATA / "edgeiq_execution_v4_replay_sweep_v1_top_rules.csv"

PROFILE_ORDER = ["ELITE", "STRONG", "STANDARD", "CHAOTIC"]
PRIOR_RACES = 300.0
FEATURE_WEIGHTS = {
    "trust_band_v1": 0.35,
    "gap_1_3_band": 0.25,
    "dominance_certainty_band": 0.20,
    "field_size_bucket": 0.10,
    "gap_1_2_band": 0.10,
}

SCORE_SHARE_RULES = {
    "VERY_HIGH": {"VERY_HIGH"},
    "HIGH_OR_BETTER": {"HIGH", "VERY_HIGH"},
    "MEDIUM_OR_BETTER": {"MEDIUM", "HIGH", "VERY_HIGH"},
}
DOMINANCE_RULES = {
    "ELITE": {"ELITE"},
    "STRONG_OR_BETTER": {"ELITE", "STRONG"},
    "POSITIVE_OR_BETTER": {"ELITE", "STRONG", "POSITIVE"},
}
TRUST_PROFILE_RULES = {
    "ANY": {"ELITE", "STRONG", "STANDARD", "CHAOTIC", "UNKNOWN"},
    "EXCLUDE_CHAOTIC": {"ELITE", "STRONG", "STANDARD"},
    "ELITE_STRONG_ONLY": {"ELITE", "STRONG"},
    "ELITE_STANDARD_STRONG_ONLY": {"ELITE", "STRONG", "STANDARD"},
}
EDGE_MINS = [0.0, 5.0, 10.0, 20.0, 30.0, 50.0]
RANK_MAXES = [1, 2, 3, 5]

BENCHMARKS = {
    "positive_overlay_baseline": 0.154324,
    "elite_dominance_overlay": 0.2042,
    "very_high_score_share_overlay": 0.1977,
    "elite_very_high_overlay": 0.2114,
    "v3_best_rule": 0.211434,
}


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


def profile_from_score(value: float, q25: float, q50: float, q75: float) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    if value >= q75:
        return "ELITE"
    if value >= q50:
        return "STRONG"
    if value >= q25:
        return "STANDARD"
    return "CHAOTIC"


def first_valid_text(values: pd.Series, default: str = "UNKNOWN") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def format_rate(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.4f}"


def rule_note(row: pd.Series | None) -> str:
    if row is None or row.empty:
        return "No eligible rule."
    return (
        f"win_rate={format_rate(row['win_rate'])} "
        f"place_rate={format_rate(row['place_rate'])} "
        f"signals={int(row['signals'])} "
        f"races={int(row['races'])}"
    )


def load_profile_reference() -> list[str]:
    if not TRUST_PROFILE_REFERENCE_PATH.exists():
        return PROFILE_ORDER.copy()

    try:
        reference = pd.read_csv(TRUST_PROFILE_REFERENCE_PATH, low_memory=False, usecols=["trust_profile_v1"])
    except ValueError:
        return PROFILE_ORDER.copy()

    values = [
        clean_text(value).upper()
        for value in reference["trust_profile_v1"].dropna().tolist()
        if clean_text(value) != ""
    ]
    ordered = [profile for profile in PROFILE_ORDER if profile in set(values)]
    return ordered or PROFILE_ORDER.copy()


def load_positive_overlay_base() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "field_size",
        "runner_score",
        "runner_rank",
        "rank_bucket",
        "score_band",
        "finish_position",
        "won",
        "placed",
        "edge_proxy_pct",
        "overlay_band",
        "positive_overlay_flag",
        "dominance_score_v1",
        "dominance_band_v1",
        "score_share_of_race",
        "score_share_band_v1",
    ]
    df = pd.read_csv(OVERLAY_PATH, low_memory=False, usecols=usecols)

    for col in [
        "meeting_date",
        "track",
        "horse",
        "rank_bucket",
        "score_band",
        "overlay_band",
        "dominance_band_v1",
        "score_share_band_v1",
    ]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)

    for col in [
        "race_no",
        "field_size",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
        "placed",
        "edge_proxy_pct",
        "dominance_score_v1",
        "score_share_of_race",
    ]:
        df[col] = to_num(df[col])

    df["positive_overlay_flag"] = df["edge_proxy_pct"].gt(0)
    df = df[df["positive_overlay_flag"]].copy()
    df["join_key_v1"] = build_join_key(df)
    df["runner_key_v1"] = build_runner_key(df)
    df["runner_rank"] = df["runner_rank"].fillna(999).astype(int)
    df["won"] = df["won"].fillna(0).astype(int)
    df["placed"] = df["placed"].fillna(0).astype(int)
    return df.copy()


def load_historical_replay_lookup() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
        "projection_status_v6",
    ]
    df = pd.read_csv(HIST_REPLAY_PATH, low_memory=False, usecols=usecols)

    for col in ["meeting_date", "track", "horse", "projection_status_v6"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)

    for col in ["race_no", "runner_score", "runner_rank", "finish_position", "won"]:
        df[col] = to_num(df[col])

    df["placed"] = df["finish_position"].le(3).fillna(False).astype(int)
    df["join_key_v1"] = build_join_key(df)
    df["runner_key_v1"] = build_runner_key(df)
    df["runner_rank_hist_v1"] = df["runner_rank"].fillna(999).astype(int)
    return df[
        [
            "runner_key_v1",
            "join_key_v1",
            "runner_score",
            "runner_rank_hist_v1",
            "finish_position",
            "won",
            "placed",
            "projection_status_v6",
        ]
    ].copy()


def load_rank_gap_races() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "field_size",
        "top_pick_won",
        "winner_rank",
        "trust_band_v1",
        "gap_1_2_band",
        "gap_1_3_band",
    ]
    df = pd.read_csv(GAP_ENGINE_PATH, low_memory=False, usecols=usecols)

    for col in ["meeting_date", "track", "trust_band_v1", "gap_1_2_band", "gap_1_3_band"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
        df[col] = df[col].replace("", "UNKNOWN")

    for col in ["race_no", "field_size", "top_pick_won", "winner_rank"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    df["field_size_bucket"] = df["field_size"].apply(field_size_bucket)
    df["top_pick_won"] = df["top_pick_won"].fillna(0).astype(int)
    return df.copy()


def load_historical_dominance_runner() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "dominance_score_v1",
        "dominance_band_v1",
        "score_share_of_race",
        "runner_rank_hist_v1",
    ]
    df = pd.read_csv(HIST_DOMINANCE_PATH, low_memory=False, usecols=usecols)

    for col in ["meeting_date", "track", "horse", "dominance_band_v1"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)

    for col in ["race_no", "dominance_score_v1", "score_share_of_race", "runner_rank_hist_v1"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    df["runner_key_v1"] = build_runner_key(df)
    df["runner_rank_hist_v1"] = df["runner_rank_hist_v1"].fillna(999).astype(int)
    return df.copy()


def build_smoothed_score_map(df: pd.DataFrame, category_col: str) -> dict[str, float]:
    grouped = (
        df.groupby(category_col, dropna=False)
        .agg(races=("join_key_v1", "size"), wins=("top_pick_won", "sum"))
        .reset_index()
    )
    grouped[category_col] = grouped[category_col].fillna("UNKNOWN").astype(str)
    overall_rate = float(df["top_pick_won"].mean())
    grouped["smoothed_top1_rate_v1"] = (grouped["wins"] + PRIOR_RACES * overall_rate) / (grouped["races"] + PRIOR_RACES)

    min_rate = float(grouped["smoothed_top1_rate_v1"].min())
    max_rate = float(grouped["smoothed_top1_rate_v1"].max())
    if math.isclose(min_rate, max_rate):
        grouped["feature_score_v1"] = 50.0
    else:
        grouped["feature_score_v1"] = 100.0 * (grouped["smoothed_top1_rate_v1"] - min_rate) / (max_rate - min_rate)

    return dict(zip(grouped[category_col], grouped["feature_score_v1"]))


def reconstruct_historical_trust_profiles() -> pd.DataFrame:
    gap_df = load_rank_gap_races()
    dom_df = load_historical_dominance_runner()

    dom_top = dom_df[dom_df["runner_rank_hist_v1"].eq(1)].copy()
    dom_top = (
        dom_top.groupby("join_key_v1", dropna=False)
        .agg(
            dominance_score_v1=("dominance_score_v1", "max"),
        )
        .reset_index()
    )
    dom_top["dominance_certainty_band"] = dom_top["dominance_score_v1"].map(dominance_certainty_band)

    hist = gap_df.merge(dom_top[["join_key_v1", "dominance_certainty_band"]], on="join_key_v1", how="left")
    hist["dominance_certainty_band"] = hist["dominance_certainty_band"].fillna("UNKNOWN")

    feature_maps: dict[str, dict[str, float]] = {}
    for feature_name in FEATURE_WEIGHTS:
        feature_maps[feature_name] = build_smoothed_score_map(hist, feature_name)

    for feature_name, weight in FEATURE_WEIGHTS.items():
        score_col = f"{feature_name}_score_v1"
        hist[score_col] = hist[feature_name].map(feature_maps[feature_name]).fillna(50.0)
        hist[score_col] = hist[score_col] * weight

    hist["trust_profile_score_v1"] = sum(hist[f"{feature_name}_score_v1"] for feature_name in FEATURE_WEIGHTS)
    q25 = float(hist["trust_profile_score_v1"].quantile(0.25))
    q50 = float(hist["trust_profile_score_v1"].quantile(0.50))
    q75 = float(hist["trust_profile_score_v1"].quantile(0.75))
    hist["trust_profile_v1"] = hist["trust_profile_score_v1"].map(lambda value: profile_from_score(value, q25, q50, q75))

    return hist[
        [
            "join_key_v1",
            "field_size_bucket",
            "trust_band_v1",
            "gap_1_2_band",
            "gap_1_3_band",
            "dominance_certainty_band",
            "trust_profile_score_v1",
            "trust_profile_v1",
        ]
    ].drop_duplicates(subset=["join_key_v1"]).copy()


def enrich_overlay_universe() -> pd.DataFrame:
    overlay_df = load_positive_overlay_base()
    replay_df = load_historical_replay_lookup()
    dom_df = load_historical_dominance_runner()
    trust_profiles = reconstruct_historical_trust_profiles()

    overlay_df = overlay_df.merge(
        replay_df,
        on="runner_key_v1",
        how="left",
        suffixes=("", "_hist"),
    )
    overlay_df["runner_score"] = overlay_df["runner_score"].fillna(overlay_df["runner_score_hist"])
    overlay_df["runner_rank"] = overlay_df["runner_rank"].where(overlay_df["runner_rank"].notna(), overlay_df["runner_rank_hist_v1"])
    overlay_df["finish_position"] = overlay_df["finish_position"].fillna(overlay_df["finish_position_hist"])
    overlay_df["won"] = overlay_df["won"].where(overlay_df["won"].notna(), overlay_df["won_hist"]).fillna(0).astype(int)
    overlay_df["placed"] = overlay_df["placed"].where(overlay_df["placed"].notna(), overlay_df["placed_hist"]).fillna(0).astype(int)

    overlay_df = overlay_df.merge(
        dom_df[
            [
                "runner_key_v1",
                "dominance_score_v1",
                "dominance_band_v1",
                "score_share_of_race",
            ]
        ],
        on="runner_key_v1",
        how="left",
        suffixes=("", "_hist"),
    )
    overlay_df["dominance_score_v1"] = overlay_df["dominance_score_v1"].fillna(overlay_df["dominance_score_v1_hist"])
    overlay_df["dominance_band_v1"] = overlay_df["dominance_band_v1"].replace("", pd.NA).fillna(overlay_df["dominance_band_v1_hist"])
    overlay_df["score_share_of_race"] = overlay_df["score_share_of_race"].fillna(overlay_df["score_share_of_race_hist"])

    overlay_df = overlay_df.merge(trust_profiles, on="join_key_v1", how="left")
    overlay_df["trust_profile_v1"] = overlay_df["trust_profile_v1"].fillna("UNKNOWN")
    overlay_df["trust_band_v1"] = overlay_df["trust_band_v1"].fillna("UNKNOWN")
    overlay_df["dominance_band_v1"] = overlay_df["dominance_band_v1"].fillna("UNKNOWN")
    overlay_df["score_share_band_v1"] = overlay_df["score_share_band_v1"].fillna("UNKNOWN")

    overlay_df["runner_rank"] = to_num(overlay_df["runner_rank"]).fillna(999).astype(int)
    overlay_df["finish_position"] = to_num(overlay_df["finish_position"])
    overlay_df["runner_score"] = to_num(overlay_df["runner_score"])
    overlay_df["dominance_score_v1"] = to_num(overlay_df["dominance_score_v1"])
    overlay_df["score_share_of_race"] = to_num(overlay_df["score_share_of_race"])
    overlay_df["edge_proxy_pct"] = to_num(overlay_df["edge_proxy_pct"])

    keep_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "join_key_v1",
        "runner_key_v1",
        "field_size",
        "runner_score",
        "runner_rank",
        "rank_bucket",
        "score_band",
        "finish_position",
        "won",
        "placed",
        "edge_proxy_pct",
        "overlay_band",
        "dominance_score_v1",
        "dominance_band_v1",
        "score_share_of_race",
        "score_share_band_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "gap_1_2_band",
        "gap_1_3_band",
        "dominance_certainty_band",
        "field_size_bucket",
    ]
    return overlay_df[keep_cols].copy()


def build_rule_id(
    score_share_min: str,
    dominance_min: str,
    rank_max: int,
    edge_min: float,
    trust_profile_filter: str,
) -> str:
    return (
        f"SHARE_{score_share_min}|"
        f"DOM_{dominance_min}|"
        f"RANK_LE_{rank_max}|"
        f"EDGE_GE_{int(edge_min)}|"
        f"TRUST_{trust_profile_filter}"
    )


def calc_rule_metrics(
    filtered_df: pd.DataFrame,
    rule_id: str,
    score_share_min: str,
    dominance_min: str,
    rank_max: int,
    edge_min: float,
    trust_profile_filter: str,
    base_signals: int,
    base_races: int,
) -> dict[str, object]:
    signals = int(len(filtered_df))
    races = int(filtered_df["join_key_v1"].nunique())
    wins = int(filtered_df["won"].sum())
    places = int(filtered_df["placed"].sum())

    rank1_df = filtered_df[filtered_df["runner_rank"].eq(1)]
    rank2_df = filtered_df[filtered_df["runner_rank"].eq(2)]
    rank3_df = filtered_df[filtered_df["runner_rank"].eq(3)]

    win_rate = safe_div(wins, signals)
    place_rate = safe_div(places, signals)

    return {
        "rule_id": rule_id,
        "score_share_min": score_share_min,
        "dominance_min": dominance_min,
        "rank_max": rank_max,
        "edge_min": edge_min,
        "trust_profile_filter": trust_profile_filter,
        "signals": signals,
        "races": races,
        "signal_retention_pct": safe_div(signals, base_signals),
        "race_retention_pct": safe_div(races, base_races),
        "wins": wins,
        "places": places,
        "win_rate": win_rate,
        "place_rate": place_rate,
        "avg_finish": float(filtered_df["finish_position"].mean()) if signals else math.nan,
        "avg_rank": float(filtered_df["runner_rank"].mean()) if signals else math.nan,
        "avg_score": float(filtered_df["runner_score"].mean()) if signals else math.nan,
        "avg_dominance_score": float(filtered_df["dominance_score_v1"].mean()) if signals else math.nan,
        "avg_score_share": float(filtered_df["score_share_of_race"].mean()) if signals else math.nan,
        "avg_edge_proxy_pct": float(filtered_df["edge_proxy_pct"].mean()) if signals else math.nan,
        "rank1_signal_win_rate": safe_div(rank1_df["won"].sum(), len(rank1_df)),
        "rank2_signal_win_rate": safe_div(rank2_df["won"].sum(), len(rank2_df)),
        "rank3_signal_win_rate": safe_div(rank3_df["won"].sum(), len(rank3_df)),
        "sample_ge_300": signals >= 300,
        "sample_ge_500": signals >= 500,
        "sample_ge_1000": signals >= 1000,
        "sample_ge_2000": signals >= 2000,
    }


def run_rule_sweep(base_df: pd.DataFrame) -> pd.DataFrame:
    base_signals = int(len(base_df))
    base_races = int(base_df["join_key_v1"].nunique())
    records: list[dict[str, object]] = []

    for score_share_min, dominance_min, rank_max, edge_min, trust_profile_filter in product(
        SCORE_SHARE_RULES.keys(),
        DOMINANCE_RULES.keys(),
        RANK_MAXES,
        EDGE_MINS,
        TRUST_PROFILE_RULES.keys(),
    ):
        filtered_df = base_df[
            base_df["score_share_band_v1"].isin(SCORE_SHARE_RULES[score_share_min])
            & base_df["dominance_band_v1"].isin(DOMINANCE_RULES[dominance_min])
            & base_df["runner_rank"].le(rank_max)
            & base_df["edge_proxy_pct"].ge(edge_min)
            & base_df["trust_profile_v1"].isin(TRUST_PROFILE_RULES[trust_profile_filter])
        ].copy()

        rule_id = build_rule_id(score_share_min, dominance_min, rank_max, edge_min, trust_profile_filter)
        records.append(
            calc_rule_metrics(
                filtered_df=filtered_df,
                rule_id=rule_id,
                score_share_min=score_share_min,
                dominance_min=dominance_min,
                rank_max=rank_max,
                edge_min=edge_min,
                trust_profile_filter=trust_profile_filter,
                base_signals=base_signals,
                base_races=base_races,
            )
        )

    rules_df = pd.DataFrame.from_records(records)
    rules_df["beats_positive_overlay_baseline"] = rules_df["win_rate"].gt(BENCHMARKS["positive_overlay_baseline"])
    rules_df["beats_elite_dominance_overlay"] = rules_df["win_rate"].gt(BENCHMARKS["elite_dominance_overlay"])
    rules_df["beats_very_high_score_share_overlay"] = rules_df["win_rate"].gt(BENCHMARKS["very_high_score_share_overlay"])
    rules_df["beats_elite_very_high_overlay"] = rules_df["win_rate"].gt(BENCHMARKS["elite_very_high_overlay"])
    rules_df["beats_v3_best_rule"] = rules_df["win_rate"].gt(BENCHMARKS["v3_best_rule"])

    rules_df = rules_df.sort_values(["win_rate", "signals"], ascending=[False, False]).reset_index(drop=True)
    return rules_df.copy()


def first_matching_rule(rules_df: pd.DataFrame, min_signals: int, place_rate_min: float | None = None) -> pd.Series | None:
    eligible = rules_df[rules_df["signals"].ge(min_signals)].copy()
    if place_rate_min is not None:
        eligible = eligible[eligible["place_rate"].ge(place_rate_min)].copy()
    if eligible.empty:
        return None
    return eligible.iloc[0]


def build_summary(rules_df: pd.DataFrame, base_df: pd.DataFrame) -> pd.DataFrame:
    base_signals = int(len(base_df))
    base_races = int(base_df["join_key_v1"].nunique())

    best_300 = first_matching_rule(rules_df, 300)
    best_500 = first_matching_rule(rules_df, 500)
    best_1000 = first_matching_rule(rules_df, 1000)
    best_2000 = first_matching_rule(rules_df, 2000)
    balanced = first_matching_rule(rules_df, 1000, 0.50)

    balanced_fallback_used = False
    if balanced is None:
        balanced = first_matching_rule(rules_df, 1000)
        balanced_fallback_used = True

    balanced_beats_v3 = bool(balanced is not None and float(balanced["win_rate"]) > BENCHMARKS["v3_best_rule"])
    best_2000_beats_v3 = bool(best_2000 is not None and float(best_2000["win_rate"]) > BENCHMARKS["v3_best_rule"])

    summary_rows = [
        {"section": "OVERVIEW", "metric": "positive_overlay_signals", "value": base_signals, "notes": "edge_proxy_pct > 0 base universe"},
        {"section": "OVERVIEW", "metric": "positive_overlay_races", "value": base_races, "notes": "historical races represented in positive overlay universe"},
        {"section": "OVERVIEW", "metric": "rules_tested", "value": int(len(rules_df)), "notes": "3 score-share x 3 dominance x 4 rank x 6 edge x 4 trust filters"},
        {"section": "BENCHMARK", "metric": "positive_overlay_baseline_win_rate", "value": BENCHMARKS["positive_overlay_baseline"], "notes": "Prompt benchmark"},
        {"section": "BENCHMARK", "metric": "elite_dominance_overlay_win_rate", "value": BENCHMARKS["elite_dominance_overlay"], "notes": "Prompt benchmark"},
        {"section": "BENCHMARK", "metric": "very_high_score_share_overlay_win_rate", "value": BENCHMARKS["very_high_score_share_overlay"], "notes": "Prompt benchmark"},
        {"section": "BENCHMARK", "metric": "elite_plus_very_high_overlay_win_rate", "value": BENCHMARKS["elite_very_high_overlay"], "notes": "Prompt benchmark"},
        {"section": "BENCHMARK", "metric": "v3_best_rule_win_rate", "value": BENCHMARKS["v3_best_rule"], "notes": "RULE_F_DOM_ELITE_SHARE_VERY_HIGH"},
        {
            "section": "BEST_RULES",
            "metric": "best_rule_ge_300",
            "value": best_300["rule_id"] if best_300 is not None else "NONE",
            "notes": rule_note(best_300),
        },
        {
            "section": "BEST_RULES",
            "metric": "best_rule_ge_500",
            "value": best_500["rule_id"] if best_500 is not None else "NONE",
            "notes": rule_note(best_500),
        },
        {
            "section": "BEST_RULES",
            "metric": "best_rule_ge_1000",
            "value": best_1000["rule_id"] if best_1000 is not None else "NONE",
            "notes": rule_note(best_1000),
        },
        {
            "section": "BEST_RULES",
            "metric": "best_rule_ge_2000",
            "value": best_2000["rule_id"] if best_2000 is not None else "NONE",
            "notes": rule_note(best_2000),
        },
        {
            "section": "BEST_RULES",
            "metric": "balanced_recommendation",
            "value": balanced["rule_id"] if balanced is not None else "NONE",
            "notes": (rule_note(balanced) + (" fallback_used=TRUE" if balanced_fallback_used else "")),
        },
        {
            "section": "QUESTION",
            "metric": "can_v4_beat_v3_with_2000_plus_signals",
            "value": "YES" if best_2000_beats_v3 else "NO",
            "notes": (
                f"best_ge_2000_win_rate={format_rate(best_2000['win_rate']) if best_2000 is not None else 'NA'} "
                f"vs v3={format_rate(BENCHMARKS['v3_best_rule'])}"
            ),
        },
        {
            "section": "QUESTION",
            "metric": "balanced_recommendation_beats_v3",
            "value": "YES" if balanced_beats_v3 else "NO",
            "notes": (
                f"balanced_win_rate={format_rate(balanced['win_rate']) if balanced is not None else 'NA'} "
                f"vs v3={format_rate(BENCHMARKS['v3_best_rule'])}"
            ),
        },
    ]
    return pd.DataFrame(summary_rows)


def build_top_rules_file(rules_df: pd.DataFrame) -> pd.DataFrame:
    top_rules = rules_df.head(25).copy()
    top_rules["selection_group_v1"] = "TOP_25"

    balanced = first_matching_rule(rules_df, 1000, 0.50)
    if balanced is None:
        balanced = first_matching_rule(rules_df, 1000)

    if balanced is not None:
        balanced_df = rules_df[rules_df["rule_id"].eq(str(balanced["rule_id"]))].copy()
        if not balanced_df.empty and str(balanced["rule_id"]) not in set(top_rules["rule_id"]):
            balanced_df["selection_group_v1"] = "BALANCED_RECOMMENDATION"
            top_rules = pd.concat([top_rules, balanced_df], ignore_index=True)
        else:
            top_rules.loc[top_rules["rule_id"].eq(str(balanced["rule_id"])), "selection_group_v1"] = "TOP_25_AND_BALANCED"

    return top_rules.copy()


def main() -> None:
    load_profile_reference()
    base_df = enrich_overlay_universe()
    rules_df = run_rule_sweep(base_df)
    summary_df = build_summary(rules_df, base_df)
    top_rules_df = build_top_rules_file(rules_df)

    rules_df.to_csv(RULES_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    top_rules_df.to_csv(TOP_RULES_OUT, index=False)

    print(f"Wrote {RULES_OUT}")
    print(f"Wrote {SUMMARY_OUT}")
    print(f"Wrote {TOP_RULES_OUT}")


if __name__ == "__main__":
    main()
