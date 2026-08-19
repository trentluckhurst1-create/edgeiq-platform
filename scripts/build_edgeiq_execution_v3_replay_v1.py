from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DOMINANCE_OVERLAY_PATH = DATA / "edgeiq_dominance_overlay_replay_v1.csv"
HISTORICAL_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
HISTORICAL_DOMINANCE_PATH = DATA / "edgeiq_historical_dominance_replay_v1.csv"
RANK_GAP_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"

REPLAY_OUT = DATA / "edgeiq_execution_v3_replay_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_execution_v3_replay_v1_summary.csv"
BY_RULE_OUT = DATA / "edgeiq_execution_v3_replay_v1_by_rule.csv"
BY_RULE_AND_RANK_OUT = DATA / "edgeiq_execution_v3_replay_v1_by_rule_and_rank.csv"

RULE_ORDER = [
    "RULE_A_POSITIVE_OVERLAY",
    "RULE_B_DOM_POSITIVE",
    "RULE_C_DOM_STRONG",
    "RULE_D_DOM_STRONG_SHARE_HIGH",
    "RULE_E_DOM_STRONG_SHARE_VERY_HIGH",
    "RULE_F_DOM_ELITE_SHARE_VERY_HIGH",
    "RULE_G_DOM_STRONG_RANK_LE_2",
    "RULE_H_DOM_STRONG_RANK_LE_3",
    "RULE_I_DOM_STRONG_RANK_LE_2_SHARE_HIGH",
]

RULE_DESCRIPTIONS = {
    "RULE_A_POSITIVE_OVERLAY": "edge_proxy_pct > 0",
    "RULE_B_DOM_POSITIVE": "edge_proxy_pct > 0 and dominance_band in ELITE/STRONG/POSITIVE",
    "RULE_C_DOM_STRONG": "edge_proxy_pct > 0 and dominance_band in ELITE/STRONG",
    "RULE_D_DOM_STRONG_SHARE_HIGH": "RULE_C and score_share_band in HIGH/VERY_HIGH",
    "RULE_E_DOM_STRONG_SHARE_VERY_HIGH": "RULE_C and score_share_band = VERY_HIGH",
    "RULE_F_DOM_ELITE_SHARE_VERY_HIGH": "edge_proxy_pct > 0 and dominance_band = ELITE and score_share_band = VERY_HIGH",
    "RULE_G_DOM_STRONG_RANK_LE_2": "RULE_C and runner_rank <= 2",
    "RULE_H_DOM_STRONG_RANK_LE_3": "RULE_C and runner_rank <= 3",
    "RULE_I_DOM_STRONG_RANK_LE_2_SHARE_HIGH": "RULE_C and runner_rank <= 2 and score_share_band in HIGH/VERY_HIGH",
}

RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS", "UNKNOWN"]


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


def score_band(score_value: object) -> str:
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


def score_share_band(value: object, q25: float, q50: float, q75: float) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number >= q75:
        return "VERY_HIGH"
    if number >= q50:
        return "HIGH"
    if number >= q25:
        return "MEDIUM"
    return "LOW"


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def group_rates(df: pd.DataFrame, mask: pd.Series, group_col: str) -> pd.Series:
    subset = df[mask].groupby(group_col, dropna=False).agg(wins=("won", "sum"), runners=("runner_join_key_v1", "size"))
    return subset.apply(lambda row: safe_rate(row["wins"], row["runners"]), axis=1)


def load_dominance_overlay() -> pd.DataFrame:
    df = pd.read_csv(DOMINANCE_OVERLAY_PATH, low_memory=False)
    text_cols = [
        "meeting_date",
        "track",
        "horse",
        "horse_key",
        "rank_bucket",
        "score_band",
        "governance_band_hist_v1",
        "score_share_band_v1",
        "dominance_band_v1",
        "dominance_rank_bucket_v1",
        "overlay_band",
        "trust_band",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).map(clean_text)

    numeric_cols = [
        "race_no",
        "field_size",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
        "placed",
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

    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    df["race_key_v1"] = df.get("race_key_v1", df["join_key_v1"]).fillna("").astype(str)
    df["positive_overlay_flag"] = df["edge_proxy_pct"].gt(0)
    return df.copy()


def load_historical_replay() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
        "projection_status_v6",
        "confidence_score_v1",
        "race_key",
    ]
    df = pd.read_csv(HISTORICAL_REPLAY_PATH, usecols=usecols, low_memory=False)
    for col in ["meeting_date", "track", "horse", "horse_key", "projection_status_v6", "race_key"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_score", "runner_rank", "finish_position", "won", "confidence_score_v1"]:
        df[col] = to_num(df[col])
    df["placed_backfill"] = df["finish_position"].le(3).fillna(False).astype(int)
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    return df.rename(
        columns={
            "runner_score": "runner_score_hist_backfill",
            "runner_rank": "runner_rank_hist_backfill",
            "finish_position": "finish_position_backfill",
            "won": "won_backfill",
            "projection_status_v6": "governance_backfill",
            "confidence_score_v1": "confidence_score_backfill",
            "race_key": "race_key_backfill",
        }
    )[
        [
            "runner_join_key_v1",
            "runner_score_hist_backfill",
            "runner_rank_hist_backfill",
            "finish_position_backfill",
            "won_backfill",
            "placed_backfill",
            "governance_backfill",
            "confidence_score_backfill",
            "race_key_backfill",
        ]
    ].copy()


def load_historical_dominance() -> pd.DataFrame:
    df = pd.read_csv(HISTORICAL_DOMINANCE_PATH, low_memory=False)
    for col in ["meeting_date", "track", "horse", "horse_key", "governance_band_hist_v1", "dominance_band_v1", "dominance_rank_bucket_v1"]:
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
    return df.rename(
        columns={
            "field_size_v1": "field_size_dom_backfill",
            "runner_score_hist_v1": "runner_score_dom_backfill",
            "runner_rank_hist_v1": "runner_rank_dom_backfill",
            "score_rank_1": "score_rank_1_backfill",
            "score_rank_2": "score_rank_2_backfill",
            "score_rank_3": "score_rank_3_backfill",
            "race_avg_score_v1": "race_avg_score_backfill",
            "race_total_score_v1": "race_total_score_backfill",
            "dominance_gap_rank2": "dominance_gap_rank2_backfill",
            "dominance_gap_rank3": "dominance_gap_rank3_backfill",
            "dominance_vs_avg": "dominance_vs_avg_backfill",
            "score_share_of_race": "score_share_backfill",
            "dominance_score_v1": "dominance_score_backfill",
            "dominance_band_v1": "dominance_band_backfill",
            "dominance_rank_v1": "dominance_rank_backfill",
            "dominance_rank_bucket_v1": "dominance_rank_bucket_backfill",
            "dominance_percentile": "dominance_percentile_backfill",
            "governance_band_hist_v1": "governance_dom_backfill",
        }
    )[
        [
            "runner_join_key_v1",
            "field_size_dom_backfill",
            "runner_score_dom_backfill",
            "runner_rank_dom_backfill",
            "score_rank_1_backfill",
            "score_rank_2_backfill",
            "score_rank_3_backfill",
            "race_avg_score_backfill",
            "race_total_score_backfill",
            "dominance_gap_rank2_backfill",
            "dominance_gap_rank3_backfill",
            "dominance_vs_avg_backfill",
            "score_share_backfill",
            "dominance_score_backfill",
            "dominance_band_backfill",
            "dominance_rank_backfill",
            "dominance_rank_bucket_backfill",
            "dominance_percentile_backfill",
            "governance_dom_backfill",
        ]
    ].copy()


def load_rank_gap() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "gap_1_2",
        "gap_1_3",
        "gap_1_2_band",
        "gap_1_3_band",
        "score_share_band",
        "winner_top3_flag_v1",
        "winner_top5_flag_v1",
    ]
    df = pd.read_csv(RANK_GAP_PATH, usecols=usecols, low_memory=False)
    for col in ["meeting_date", "track", "gap_1_2_band", "gap_1_3_band", "score_share_band"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "gap_1_2", "gap_1_3", "winner_top3_flag_v1", "winner_top5_flag_v1"]:
        df[col] = to_num(df[col])
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["join_key_v1"] = build_join_key(df)
    return df.rename(
        columns={
            "score_share_band": "race_top_score_share_band_v1",
        }
    )[[
        "join_key_v1",
        "gap_1_2",
        "gap_1_3",
        "gap_1_2_band",
        "gap_1_3_band",
        "race_top_score_share_band_v1",
        "winner_top3_flag_v1",
        "winner_top5_flag_v1",
    ]].drop_duplicates(subset=["join_key_v1"]).copy()


def prepare_base_frame() -> pd.DataFrame:
    overlay_df = load_dominance_overlay()
    replay_backfill_df = load_historical_replay()
    dominance_backfill_df = load_historical_dominance()
    rank_gap_df = load_rank_gap()

    df = overlay_df.merge(replay_backfill_df, on="runner_join_key_v1", how="left")
    df = df.merge(dominance_backfill_df, on="runner_join_key_v1", how="left")
    df = df.merge(rank_gap_df, on="join_key_v1", how="left")

    df["runner_score"] = to_num(df["runner_score"]).fillna(to_num(df["runner_score_hist_backfill"])).fillna(to_num(df["runner_score_dom_backfill"]))
    df["runner_rank"] = to_num(df["runner_rank"]).fillna(to_num(df["runner_rank_hist_backfill"])).fillna(to_num(df["runner_rank_dom_backfill"]))
    df["finish_position"] = to_num(df["finish_position"]).fillna(to_num(df["finish_position_backfill"]))
    df["won"] = to_num(df["won"]).fillna(to_num(df["won_backfill"])).fillna(0).astype(int)
    df["placed"] = to_num(df["placed"]).fillna(to_num(df["placed_backfill"])).fillna(df["finish_position"].le(3)).astype(int)
    df["field_size"] = to_num(df["field_size"]).fillna(to_num(df["field_size_dom_backfill"]))

    df["score_rank_1"] = to_num(df["score_rank_1"]).fillna(to_num(df["score_rank_1_backfill"]))
    df["score_rank_2"] = to_num(df["score_rank_2"]).fillna(to_num(df["score_rank_2_backfill"]))
    df["score_rank_3"] = to_num(df["score_rank_3"]).fillna(to_num(df["score_rank_3_backfill"]))
    df["race_avg_score_v1"] = to_num(df["race_avg_score_v1"]).fillna(to_num(df["race_avg_score_backfill"]))
    df["race_total_score_v1"] = to_num(df["race_total_score_v1"]).fillna(to_num(df["race_total_score_backfill"]))
    df["dominance_gap_rank2"] = to_num(df["dominance_gap_rank2"]).fillna(to_num(df["dominance_gap_rank2_backfill"]))
    df["dominance_gap_rank3"] = to_num(df["dominance_gap_rank3"]).fillna(to_num(df["dominance_gap_rank3_backfill"]))
    df["dominance_vs_avg"] = to_num(df["dominance_vs_avg"]).fillna(to_num(df["dominance_vs_avg_backfill"]))
    df["score_share_of_race"] = to_num(df["score_share_of_race"]).fillna(to_num(df["score_share_backfill"]))
    df["dominance_score_v1"] = to_num(df["dominance_score_v1"]).fillna(to_num(df["dominance_score_backfill"]))
    df["dominance_rank_v1"] = to_num(df["dominance_rank_v1"]).fillna(to_num(df["dominance_rank_backfill"]))
    df["dominance_percentile"] = to_num(df["dominance_percentile"]).fillna(to_num(df["dominance_percentile_backfill"]))
    df["confidence_score_v1"] = to_num(df["confidence_score_backfill"]) 

    df["race_key_v1"] = df["race_key_v1"].replace("", pd.NA).fillna(df["race_key_backfill"]).fillna(df["join_key_v1"])
    df["rank_bucket"] = df["rank_bucket"].replace("", pd.NA)
    df["rank_bucket"] = df["rank_bucket"].fillna(df["runner_rank"].map(rank_bucket)).fillna("UNKNOWN")
    df["score_band"] = df["score_band"].replace("", pd.NA)
    df["score_band"] = df["score_band"].fillna(df["runner_score"].map(score_band)).fillna("UNKNOWN")

    for primary_col, fallback_col in [
        ("governance_band_hist_v1", "governance_dom_backfill"),
        ("governance_band_hist_v1", "governance_backfill"),
        ("dominance_band_v1", "dominance_band_backfill"),
        ("dominance_rank_bucket_v1", "dominance_rank_bucket_backfill"),
    ]:
        df[primary_col] = df[primary_col].replace("", pd.NA)
        df[primary_col] = df[primary_col].fillna(df[fallback_col])

    valid_share = df["score_share_of_race"].dropna()
    if valid_share.empty:
        q25 = q50 = q75 = math.nan
    else:
        q25 = float(valid_share.quantile(0.25))
        q50 = float(valid_share.quantile(0.50))
        q75 = float(valid_share.quantile(0.75))

    df["score_share_band_v1"] = df["score_share_band_v1"].replace("", pd.NA)
    df["score_share_band_v1"] = df["score_share_band_v1"].fillna(df["score_share_of_race"].map(lambda value: score_share_band(value, q25, q50, q75)))

    df["dominance_band"] = df["dominance_band_v1"].fillna("UNKNOWN")
    df["score_share_band"] = df["score_share_band_v1"].fillna("UNKNOWN")
    df["governance"] = df["governance_band_hist_v1"].fillna("UNKNOWN")
    df["edge_proxy_pct"] = to_num(df["edge_proxy_pct"])
    df["positive_overlay_flag"] = df["edge_proxy_pct"].gt(0)
    df["dominance_available_flag"] = df["dominance_score_v1"].notna()

    df = df[df["positive_overlay_flag"]].copy()
    df = df.sort_values(["meeting_date", "track", "race_no", "runner_rank", "horse"], kind="stable").reset_index(drop=True)
    return df


def build_rule_frames(base_df: pd.DataFrame) -> pd.DataFrame:
    dom_positive = base_df["dominance_band"].isin(["ELITE", "STRONG", "POSITIVE"])
    dom_strong = base_df["dominance_band"].isin(["ELITE", "STRONG"])
    share_high = base_df["score_share_band"].isin(["HIGH", "VERY_HIGH"])
    share_very_high = base_df["score_share_band"].eq("VERY_HIGH")
    rank_le_2 = base_df["runner_rank"].le(2)
    rank_le_3 = base_df["runner_rank"].le(3)

    rule_masks = {
        "RULE_A_POSITIVE_OVERLAY": base_df["edge_proxy_pct"].gt(0),
        "RULE_B_DOM_POSITIVE": base_df["edge_proxy_pct"].gt(0) & dom_positive,
        "RULE_C_DOM_STRONG": base_df["edge_proxy_pct"].gt(0) & dom_strong,
        "RULE_D_DOM_STRONG_SHARE_HIGH": base_df["edge_proxy_pct"].gt(0) & dom_strong & share_high,
        "RULE_E_DOM_STRONG_SHARE_VERY_HIGH": base_df["edge_proxy_pct"].gt(0) & dom_strong & share_very_high,
        "RULE_F_DOM_ELITE_SHARE_VERY_HIGH": base_df["edge_proxy_pct"].gt(0) & base_df["dominance_band"].eq("ELITE") & share_very_high,
        "RULE_G_DOM_STRONG_RANK_LE_2": base_df["edge_proxy_pct"].gt(0) & dom_strong & rank_le_2,
        "RULE_H_DOM_STRONG_RANK_LE_3": base_df["edge_proxy_pct"].gt(0) & dom_strong & rank_le_3,
        "RULE_I_DOM_STRONG_RANK_LE_2_SHARE_HIGH": base_df["edge_proxy_pct"].gt(0) & dom_strong & rank_le_2 & share_high,
    }

    frames: list[pd.DataFrame] = []
    for idx, rule_id in enumerate(RULE_ORDER, start=1):
        selected = base_df.loc[rule_masks[rule_id]].copy()
        selected["rule_id"] = rule_id
        selected["rule_description"] = RULE_DESCRIPTIONS[rule_id]
        selected["rule_sort_order_v1"] = idx
        frames.append(selected)

    signal_df = pd.concat(frames, ignore_index=True)
    signal_df = signal_df.rename(
        columns={
            "race_key_v1": "race_key",
            "runner_score": "runner_score_hist_v1",
            "runner_rank": "runner_rank_hist_v1",
            "score_share_of_race": "score_share_v1",
        }
    )
    preferred_columns = [
        "rule_id",
        "rule_description",
        "rule_sort_order_v1",
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "field_size",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "rank_bucket",
        "score_band",
        "finish_position",
        "won",
        "placed",
        "governance",
        "confidence_score_v1",
        "dominance_score_v1",
        "dominance_band",
        "dominance_rank_v1",
        "dominance_rank_bucket_v1",
        "dominance_percentile",
        "score_rank_1",
        "score_rank_2",
        "score_rank_3",
        "dominance_gap_rank2",
        "dominance_gap_rank3",
        "dominance_vs_avg",
        "score_share_v1",
        "score_share_band",
        "gap_1_2",
        "gap_1_3",
        "gap_1_2_band",
        "gap_1_3_band",
        "race_top_score_share_band_v1",
        "historical_rank_prob",
        "historical_score_band_prob",
        "race_softmax_prob",
        "empirical_probability",
        "empirical_fair_odds",
        "market_proxy_probability",
        "market_proxy_fair_odds",
        "edge_proxy_pct",
        "overlay_band",
        "trust_band",
        "runner_join_key_v1",
        "join_key_v1",
    ]
    existing_columns = [col for col in preferred_columns if col in signal_df.columns]
    signal_df = signal_df[existing_columns].sort_values(
        ["rule_sort_order_v1", "meeting_date", "track", "race_no", "runner_rank_hist_v1", "horse"],
        kind="stable",
    ).reset_index(drop=True)
    return signal_df


def summarize_rules(signal_df: pd.DataFrame, positive_overlay_rows: int, total_races: int, total_winners: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    grouped = (
        signal_df.groupby(["rule_id", "rule_description", "rule_sort_order_v1"], dropna=False)
        .agg(
            signals=("runner_join_key_v1", "size"),
            races=("race_key", "nunique"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_finish=("finish_position", "mean"),
            avg_rank=("runner_rank_hist_v1", "mean"),
            avg_score=("runner_score_hist_v1", "mean"),
            avg_dominance_score=("dominance_score_v1", "mean"),
            avg_score_share=("score_share_v1", "mean"),
            avg_edge_proxy_pct=("edge_proxy_pct", "mean"),
        )
        .reset_index()
    )
    grouped["signal_retention_pct"] = grouped["signals"].apply(lambda value: safe_rate(value, positive_overlay_rows))
    grouped["race_retention_pct"] = grouped["races"].apply(lambda value: safe_rate(value, total_races))
    grouped["win_rate"] = grouped.apply(lambda row: safe_rate(row["wins"], row["signals"]), axis=1)
    grouped["place_rate"] = grouped.apply(lambda row: safe_rate(row["places"], row["signals"]), axis=1)
    grouped["winner_capture_pct"] = grouped["wins"].apply(lambda value: safe_rate(value, total_winners))

    rank1_rates = group_rates(signal_df, signal_df["runner_rank_hist_v1"].eq(1), "rule_id")
    rank2_rates = group_rates(signal_df, signal_df["runner_rank_hist_v1"].eq(2), "rule_id")
    rank3_rates = group_rates(signal_df, signal_df["runner_rank_hist_v1"].eq(3), "rule_id")

    grouped["rank1_signal_win_rate"] = grouped["rule_id"].map(rank1_rates)
    grouped["rank2_signal_win_rate"] = grouped["rule_id"].map(rank2_rates)
    grouped["rank3_signal_win_rate"] = grouped["rule_id"].map(rank3_rates)
    grouped["sample_ge_300"] = grouped["signals"].ge(300)
    grouped["sample_ge_1000"] = grouped["signals"].ge(1000)
    grouped["sample_ge_2000"] = grouped["signals"].ge(2000)

    grouped = grouped.sort_values(["win_rate", "signals"], ascending=[False, False], kind="stable").reset_index(drop=True)
    grouped["ranked_order_v1"] = grouped.index + 1

    rank_grouped = (
        signal_df.groupby(["rule_id", "rank_bucket"], dropna=False)
        .agg(
            signals=("runner_join_key_v1", "size"),
            races=("race_key", "nunique"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_finish=("finish_position", "mean"),
            avg_rank=("runner_rank_hist_v1", "mean"),
            avg_score=("runner_score_hist_v1", "mean"),
            avg_dominance_score=("dominance_score_v1", "mean"),
            avg_score_share=("score_share_v1", "mean"),
            avg_edge_proxy_pct=("edge_proxy_pct", "mean"),
        )
        .reset_index()
    )
    rank_grouped["win_rate"] = rank_grouped.apply(lambda row: safe_rate(row["wins"], row["signals"]), axis=1)
    rank_grouped["place_rate"] = rank_grouped.apply(lambda row: safe_rate(row["places"], row["signals"]), axis=1)
    rank_grouped["winner_capture_pct"] = rank_grouped["wins"].apply(lambda value: safe_rate(value, total_winners))
    rule_order_map = grouped.set_index("rule_id")["ranked_order_v1"].to_dict()
    rank_order_map = {name: idx for idx, name in enumerate(RANK_BUCKET_ORDER, start=1)}
    rank_grouped["rule_ranked_order_v1"] = rank_grouped["rule_id"].map(rule_order_map)
    rank_grouped["rank_bucket_sort_v1"] = rank_grouped["rank_bucket"].map(rank_order_map).fillna(999)
    rank_grouped = rank_grouped.sort_values(["rule_ranked_order_v1", "rank_bucket_sort_v1"], kind="stable").reset_index(drop=True)

    return grouped, rank_grouped


def choose_best_rule(by_rule_df: pd.DataFrame, min_signals: int, require_place_rate: bool = False) -> pd.Series | None:
    eligible = by_rule_df[by_rule_df["signals"] >= min_signals].copy()
    if require_place_rate:
        eligible = eligible[eligible["place_rate"] >= 0.50].copy()
    if eligible.empty:
        return None
    eligible = eligible.sort_values(["win_rate", "signals"], ascending=[False, False], kind="stable")
    return eligible.iloc[0]


def build_summary(base_df: pd.DataFrame, by_rule_df: pd.DataFrame, total_rows: int, total_races: int, total_winners: int) -> pd.DataFrame:
    positive_overlay_rows = int(base_df.shape[0])
    positive_overlay_races = int(base_df["race_key_v1"].nunique())
    dominance_available_rows = int(base_df["dominance_available_flag"].sum())

    best_300 = choose_best_rule(by_rule_df, 300)
    best_1000 = choose_best_rule(by_rule_df, 1000)
    best_2000 = choose_best_rule(by_rule_df, 2000)
    best_balanced = choose_best_rule(by_rule_df, 2000, require_place_rate=True)
    if best_balanced is None:
        best_balanced = choose_best_rule(by_rule_df, 2000, require_place_rate=False)

    can_push = False
    can_push_notes = "No rule reached 30% win rate with 2,000+ signals."
    if best_2000 is not None and float(best_2000["win_rate"]) >= 0.30:
        can_push = True
        can_push_notes = (
            f"{best_2000['rule_id']} win_rate={best_2000['win_rate']:.6f} "
            f"signals={int(best_2000['signals'])} place_rate={best_2000['place_rate']:.6f}"
        )

    summary_rows: list[dict[str, object]] = [
        {"section": "OVERVIEW", "metric": "total_rows", "value": total_rows, "notes": "all historical replay runners"},
        {"section": "OVERVIEW", "metric": "total_races", "value": total_races, "notes": "all historical replay races"},
        {"section": "OVERVIEW", "metric": "total_winners", "value": total_winners, "notes": "all historical replay winners"},
        {"section": "OVERVIEW", "metric": "positive_overlay_rows", "value": positive_overlay_rows, "notes": "edge_proxy_pct > 0"},
        {"section": "OVERVIEW", "metric": "positive_overlay_races", "value": positive_overlay_races, "notes": "positive overlay universe"},
        {"section": "OVERVIEW", "metric": "dominance_available_positive_overlay_rows", "value": dominance_available_rows, "notes": "positive overlay rows with dominance data"},
        {"section": "QUESTION", "metric": "can_dominance_and_score_share_push_to_30_35_win_rate_with_2000_plus_signals", "value": "YES" if can_push else "NO", "notes": can_push_notes},
    ]

    best_map = {
        "best_rule_by_win_rate_ge_300": best_300,
        "best_rule_by_win_rate_ge_1000": best_1000,
        "best_rule_by_win_rate_ge_2000": best_2000,
        "best_rule_balanced": best_balanced,
    }
    for metric, row in best_map.items():
        if row is None:
            summary_rows.append({"section": "BEST_RULES", "metric": metric, "value": "NONE", "notes": "No eligible rule."})
            continue
        notes = (
            f"win_rate={row['win_rate']:.6f} place_rate={row['place_rate']:.6f} "
            f"signals={int(row['signals'])} races={int(row['races'])}"
        )
        summary_rows.append({"section": "BEST_RULES", "metric": metric, "value": row["rule_id"], "notes": notes})

    baseline = by_rule_df[by_rule_df["rule_id"] == "RULE_A_POSITIVE_OVERLAY"]
    if not baseline.empty:
        baseline_row = baseline.iloc[0]
        summary_rows.append(
            {
                "section": "BASELINE", 
                "metric": "positive_overlay_baseline_rule", 
                "value": baseline_row["rule_id"], 
                "notes": f"win_rate={baseline_row['win_rate']:.6f} place_rate={baseline_row['place_rate']:.6f} signals={int(baseline_row['signals'])}",
            }
        )

    return pd.DataFrame(summary_rows)


def main() -> None:
    base_df = prepare_base_frame()
    total_rows = int(pd.read_csv(HISTORICAL_REPLAY_PATH, usecols=["meeting_date"]).shape[0])
    total_races = int(base_df["join_key_v1"].nunique())
    total_winners = int(base_df[["runner_join_key_v1", "won"]].drop_duplicates()["won"].sum())

    signal_df = build_rule_frames(base_df)
    by_rule_df, by_rule_and_rank_df = summarize_rules(signal_df, int(base_df.shape[0]), total_races, total_winners)
    summary_df = build_summary(base_df, by_rule_df, total_rows, total_races, total_winners)

    signal_df.to_csv(REPLAY_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    by_rule_df.to_csv(BY_RULE_OUT, index=False)
    by_rule_and_rank_df.to_csv(BY_RULE_AND_RANK_OUT, index=False)

    print(f"Wrote {REPLAY_OUT}")
    print(f"Wrote {SUMMARY_OUT}")
    print(f"Wrote {BY_RULE_OUT}")
    print(f"Wrote {BY_RULE_AND_RANK_OUT}")


if __name__ == "__main__":
    main()
