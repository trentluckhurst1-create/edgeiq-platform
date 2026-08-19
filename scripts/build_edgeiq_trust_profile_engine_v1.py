from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_TRUST_INDEX_PATH = DATA / "edgeiq_trust_index_v1.csv"
HIST_GAP_ENGINE_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
HIST_TRUST_REPLAY_PATH = DATA / "edgeiq_trust_band_replay_v1.csv"

PROFILE_OUT = DATA / "edgeiq_trust_profile_engine_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_trust_profile_engine_v1_summary.csv"

PROFILE_ORDER = ["ELITE", "STRONG", "STANDARD", "CHAOTIC"]
PRIOR_RACES = 300.0
FEATURE_WEIGHTS = {
    "trust_band_v1": 0.35,
    "gap_1_3_band": 0.25,
    "dominance_certainty_band": 0.20,
    "field_size_bucket": 0.10,
    "gap_1_2_band": 0.10,
}
LIVE_GAP_1_2_MAP = {
    "0_2": "ZERO_TO_2",
    "2_5": "TWO_TO_5",
    "5_10": "FIVE_TO_10",
    "10_PLUS": "TEN_PLUS",
}
LIVE_GAP_1_3_MAP = {
    "0_5": "ZERO_TO_5",
    "5_10": "FIVE_TO_10",
    "10_15": "TEN_TO_15",
    "15_PLUS": "FIFTEEN_PLUS",
}


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_join_key(df: pd.DataFrame) -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df["track"].map(normalize_track) + "|" + race_no


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


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def first_valid_text(values: pd.Series, default: str = "") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def normalize_gap_1_2_live(value: object) -> str:
    text = clean_text(value).upper()
    return LIVE_GAP_1_2_MAP.get(text, text or "UNKNOWN")


def normalize_gap_1_3_live(value: object) -> str:
    text = clean_text(value).upper()
    return LIVE_GAP_1_3_MAP.get(text, text or "UNKNOWN")


def load_historical_gap_engine() -> pd.DataFrame:
    if not HIST_GAP_ENGINE_PATH.exists():
        raise FileNotFoundError(f"Missing historical gap engine file: {HIST_GAP_ENGINE_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "field_size",
        "top_pick_won",
        "winner_rank",
        "trust_band_v1",
        "gap_1_2_band",
        "gap_1_3_band",
        "winner_top3_flag_v1",
        "winner_top5_flag_v1",
    ]
    df = pd.read_csv(HIST_GAP_ENGINE_PATH, low_memory=False, usecols=usecols)

    for col in ["meeting_date", "track", "race_key", "trust_band_v1", "gap_1_2_band", "gap_1_3_band"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
        df[col] = df[col].replace("", "UNKNOWN")

    for col in ["race_no", "field_size", "top_pick_won", "winner_rank", "winner_top3_flag_v1", "winner_top5_flag_v1"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    df["field_size_bucket"] = df["field_size"].apply(field_size_bucket)
    df["winner_top10_flag_v1"] = df["winner_rank"].le(10).fillna(False).astype(int)
    return df.copy()


def load_historical_trust_replay() -> pd.DataFrame:
    if not HIST_TRUST_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing historical trust replay file: {HIST_TRUST_REPLAY_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "dominance_certainty_band",
        "won",
    ]
    df = pd.read_csv(HIST_TRUST_REPLAY_PATH, low_memory=False, usecols=usecols)

    for col in ["meeting_date", "track", "dominance_certainty_band"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
        df[col] = df[col].replace("", "UNKNOWN")

    for col in ["race_no", "won"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    race_level = (
        df.groupby("join_key_v1", dropna=False)
        .agg(
            dominance_certainty_band=("dominance_certainty_band", lambda s: first_valid_text(s, "UNKNOWN")),
            winner_rows=("won", "sum"),
        )
        .reset_index()
    )
    race_level["winner_rows"] = to_num(race_level["winner_rows"]).fillna(0).astype(int)
    return race_level.copy()


def load_live_trust_index() -> pd.DataFrame:
    if not LIVE_TRUST_INDEX_PATH.exists():
        raise FileNotFoundError(f"Missing live trust index file: {LIVE_TRUST_INDEX_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "top_pick_horse",
        "field_size",
        "field_size_bucket",
        "gap_1_2_bucket",
        "gap_1_3_bucket",
        "dominance_certainty_band",
        "trust_band_v1",
        "trust_index_v1",
    ]
    df = pd.read_csv(LIVE_TRUST_INDEX_PATH, low_memory=False, usecols=usecols)

    for col in [
        "meeting_date",
        "track",
        "race_key",
        "top_pick_horse",
        "field_size_bucket",
        "gap_1_2_bucket",
        "gap_1_3_bucket",
        "dominance_certainty_band",
        "trust_band_v1",
    ]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)

    for col in ["race_no", "field_size", "trust_index_v1"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    df["field_size_bucket"] = df["field_size_bucket"].replace("", pd.NA)
    df["field_size_bucket"] = df["field_size_bucket"].fillna(df["field_size"].apply(field_size_bucket))
    df["dominance_certainty_band"] = df["dominance_certainty_band"].replace("", "UNKNOWN")
    df["trust_band_v1"] = df["trust_band_v1"].replace("", "UNKNOWN")
    df["gap_1_2_band"] = df["gap_1_2_bucket"].apply(normalize_gap_1_2_live)
    df["gap_1_3_band"] = df["gap_1_3_bucket"].apply(normalize_gap_1_3_live)
    return df.copy()


def build_historical_race_frame() -> pd.DataFrame:
    gap_df = load_historical_gap_engine()
    trust_df = load_historical_trust_replay()
    hist = gap_df.merge(trust_df, on="join_key_v1", how="left")
    hist["dominance_certainty_band"] = hist["dominance_certainty_band"].fillna("UNKNOWN")
    hist["winner_rows"] = hist["winner_rows"].fillna(0).astype(int)
    return hist.copy()


def build_smoothed_score_map(df: pd.DataFrame, category_col: str, outcome_col: str = "top_pick_won") -> pd.DataFrame:
    grouped = (
        df.groupby(category_col, dropna=False)
        .agg(
            races=("join_key_v1", "size"),
            wins=(outcome_col, "sum"),
        )
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


def build_feature_maps(hist_df: pd.DataFrame) -> dict[str, dict[str, float]]:
    feature_maps: dict[str, dict[str, float]] = {}
    for feature_name in FEATURE_WEIGHTS:
        feature_map_df = build_smoothed_score_map(hist_df, feature_name)
        feature_maps[feature_name] = dict(zip(feature_map_df[feature_name], feature_map_df["feature_score_v1"]))
    return feature_maps


def score_features(df: pd.DataFrame, feature_maps: dict[str, dict[str, float]]) -> pd.DataFrame:
    scored = df.copy()
    for feature_name, mapping in feature_maps.items():
        score_col = f"{feature_name}_score_v1"
        scored[score_col] = scored[feature_name].map(mapping).fillna(50.0)

    scored["trust_profile_score_v1"] = (
        FEATURE_WEIGHTS["trust_band_v1"] * scored["trust_band_v1_score_v1"]
        + FEATURE_WEIGHTS["gap_1_3_band"] * scored["gap_1_3_band_score_v1"]
        + FEATURE_WEIGHTS["dominance_certainty_band"] * scored["dominance_certainty_band_score_v1"]
        + FEATURE_WEIGHTS["field_size_bucket"] * scored["field_size_bucket_score_v1"]
        + FEATURE_WEIGHTS["gap_1_2_band"] * scored["gap_1_2_band_score_v1"]
    ).round(3)
    return scored.copy()


def profile_from_score(value: float, q25: float, q50: float, q75: float) -> str:
    if pd.isna(value):
        return "CHAOTIC"
    if value >= q75:
        return "ELITE"
    if value >= q50:
        return "STRONG"
    if value >= q25:
        return "STANDARD"
    return "CHAOTIC"


def build_profile_summary(hist_scored_df: pd.DataFrame, live_scored_df: pd.DataFrame, q25: float, q50: float, q75: float) -> pd.DataFrame:
    total_winner_rows = int(hist_scored_df["winner_rows"].sum())
    summary = (
        hist_scored_df.groupby("trust_profile_v1", dropna=False)
        .agg(
            races=("join_key_v1", "size"),
            top1=("top_pick_won", "mean"),
            top3=("winner_top3_flag_v1", "mean"),
            top5=("winner_top5_flag_v1", "mean"),
            top10=("winner_top10_flag_v1", "mean"),
            avg_winner_rank=("winner_rank", "mean"),
            winner_rows=("winner_rows", "sum"),
            profile_score_min_v1=("trust_profile_score_v1", "min"),
            profile_score_max_v1=("trust_profile_score_v1", "max"),
            avg_profile_score_v1=("trust_profile_score_v1", "mean"),
        )
        .reset_index()
    )
    summary["winner_capture"] = summary["winner_rows"].apply(lambda value: safe_div(value, total_winner_rows))

    live_counts = (
        live_scored_df.groupby("trust_profile_v1", dropna=False)
        .agg(current_live_races=("join_key_v1", "size"))
        .reset_index()
    )
    summary = summary.merge(live_counts, on="trust_profile_v1", how="left")
    summary["current_live_races"] = summary["current_live_races"].fillna(0).astype(int)
    summary["minimum_300_races_pass_v1"] = summary["races"].ge(300)

    eligible = summary[summary["minimum_300_races_pass_v1"]].copy()
    strongest_profile = eligible.sort_values(["top1", "top3", "top5", "races"], ascending=[False, False, False, False]).iloc[0]["trust_profile_v1"]
    exclude_profile = eligible.sort_values(["top1", "top3", "top5", "avg_winner_rank"], ascending=[True, True, True, False]).iloc[0]["trust_profile_v1"]

    summary["strongest_historical_profile_flag_v1"] = summary["trust_profile_v1"].eq(strongest_profile)
    summary["exclude_from_betting_flag_v1"] = summary["trust_profile_v1"].eq(exclude_profile)
    summary["learned_q25_v1"] = q25
    summary["learned_q50_v1"] = q50
    summary["learned_q75_v1"] = q75
    summary["sort_order"] = summary["trust_profile_v1"].map({name: idx for idx, name in enumerate(PROFILE_ORDER, start=1)}).fillna(999)
    summary = summary.sort_values(["sort_order", "trust_profile_v1"]).drop(columns=["sort_order"])
    return summary.copy()


def main() -> None:
    hist_df = build_historical_race_frame()
    feature_maps = build_feature_maps(hist_df)
    hist_scored_df = score_features(hist_df, feature_maps)

    q25 = float(hist_scored_df["trust_profile_score_v1"].quantile(0.25))
    q50 = float(hist_scored_df["trust_profile_score_v1"].quantile(0.50))
    q75 = float(hist_scored_df["trust_profile_score_v1"].quantile(0.75))
    hist_scored_df["trust_profile_v1"] = hist_scored_df["trust_profile_score_v1"].apply(lambda value: profile_from_score(value, q25, q50, q75))

    live_df = load_live_trust_index()
    live_scored_df = score_features(live_df, feature_maps)
    live_scored_df["trust_profile_v1"] = live_scored_df["trust_profile_score_v1"].apply(lambda value: profile_from_score(value, q25, q50, q75))

    summary_df = build_profile_summary(hist_scored_df, live_scored_df, q25, q50, q75)
    profile_metrics = summary_df[[
        "trust_profile_v1",
        "top1",
        "top3",
        "top5",
        "top10",
        "avg_winner_rank",
        "winner_capture",
        "strongest_historical_profile_flag_v1",
        "exclude_from_betting_flag_v1",
        "minimum_300_races_pass_v1",
    ]].copy()

    live_out = live_scored_df.merge(profile_metrics, on="trust_profile_v1", how="left")
    live_out = live_out[[
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "join_key_v1",
        "top_pick_horse",
        "field_size",
        "field_size_bucket",
        "trust_band_v1",
        "dominance_certainty_band",
        "gap_1_2_bucket",
        "gap_1_2_band",
        "gap_1_3_bucket",
        "gap_1_3_band",
        "trust_index_v1",
        "trust_band_v1_score_v1",
        "dominance_certainty_band_score_v1",
        "gap_1_2_band_score_v1",
        "gap_1_3_band_score_v1",
        "field_size_bucket_score_v1",
        "trust_profile_score_v1",
        "trust_profile_v1",
        "top1",
        "top3",
        "top5",
        "top10",
        "avg_winner_rank",
        "winner_capture",
        "strongest_historical_profile_flag_v1",
        "exclude_from_betting_flag_v1",
        "minimum_300_races_pass_v1",
    ]].copy()
    live_out = live_out.rename(
        columns={
            "top1": "historical_top1_profile_v1",
            "top3": "historical_top3_profile_v1",
            "top5": "historical_top5_profile_v1",
            "top10": "historical_top10_profile_v1",
            "avg_winner_rank": "historical_avg_winner_rank_profile_v1",
            "winner_capture": "historical_winner_capture_profile_v1",
        }
    )

    live_out.to_csv(PROFILE_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)

    strongest = summary_df[summary_df["strongest_historical_profile_flag_v1"]].iloc[0]
    exclude = summary_df[summary_df["exclude_from_betting_flag_v1"]].iloc[0]

    print("[EDGEIQ_TRUST_PROFILE_ENGINE_V1] COMPLETE")
    print(f"historical_races={len(hist_scored_df)}")
    print(f"live_races={len(live_out)}")
    print(f"strongest_profile={strongest['trust_profile_v1']}")
    print(f"strongest_profile_top1={float(strongest['top1']):.6f}")
    print(f"exclude_profile={exclude['trust_profile_v1']}")
    print(f"exclude_profile_top1={float(exclude['top1']):.6f}")
    print(f"profile_out={PROFILE_OUT}")
    print(f"summary_out={SUMMARY_OUT}")


if __name__ == "__main__":
    main()
