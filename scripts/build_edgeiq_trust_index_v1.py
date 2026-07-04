from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST_CERTAINTY_PATH = DATA / "edgeiq_certainty_engine_v1.csv"
HIST_PACE_TRUST_PATH = DATA / "edgeiq_historical_pace_trust_replay_v1.csv"
LIVE_RUNNER_SCORE_PATH = DATA / "edgeiq_runner_score_v6.csv"

TRUST_INDEX_OUT = DATA / "edgeiq_trust_index_v1.csv"
TRUST_AUDIT_OUT = DATA / "edgeiq_trust_index_v1_audit.csv"

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


def build_smoothed_score_map(df: pd.DataFrame, category_col: str, outcome_col: str = "top_pick_won") -> pd.DataFrame:
    grouped = (
        df.groupby(category_col, dropna=False)
        .agg(
            races=("race_key", "size"),
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
    df["winner_top3"] = df["winner_rank"].le(3).astype(int)
    return df.copy()


def load_historical_pace_race_level() -> pd.DataFrame:
    if not HIST_PACE_TRUST_PATH.exists():
        return pd.DataFrame(columns=["race_key_norm_v1", "pace_trust_band_v1", "pace_trust_score_raw_v1"])

    df = pd.read_csv(HIST_PACE_TRUST_PATH, low_memory=False)
    if "race_key" not in df.columns:
        return pd.DataFrame(columns=["race_key_norm_v1", "pace_trust_band_v1", "pace_trust_score_raw_v1"])

    if "pace_trust_score_v1" in df.columns:
        df["pace_trust_score_v1"] = to_num(df["pace_trust_score_v1"])
    else:
        df["pace_trust_score_v1"] = math.nan

    if "pace_trust_band_v1" not in df.columns:
        df["pace_trust_band_v1"] = "UNKNOWN"

    df["race_key_norm_v1"] = df["race_key"].map(normalize_race_key)
    grouped = (
        df.groupby("race_key_norm_v1", dropna=False)
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
    value = pd.to_numeric(subset[value_col], errors="coerce").dropna()
    if value.empty:
        return math.nan
    return float(value.iloc[0])


def predict_dominance_score(row: pd.Series, maps: dict[str, pd.DataFrame | float]) -> float:
    filters_triple = {
        "field_size_bucket": row["field_size_bucket"],
        "gap_1_2_bucket": row["gap_1_2_bucket"],
        "gap_1_3_bucket": row["gap_1_3_bucket"],
    }
    value = lookup_mean(maps["triple"], filters_triple, "dominance_score_mean")
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


def add_historical_components(hist_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, float]], dict[str, pd.DataFrame | float]]:
    hist_df = hist_df.copy()
    hist_pace = load_historical_pace_race_level()
    hist_df = hist_df.merge(hist_pace, on="race_key_norm_v1", how="left")
    hist_df["pace_trust_band_v1"] = hist_df["pace_trust_band_v1"].fillna("UNKNOWN").astype(str)
    hist_df["pace_trust_score_raw_v1"] = to_num(hist_df["pace_trust_score_raw_v1"]).fillna(0)

    field_map_df = build_smoothed_score_map(hist_df, "field_size_bucket")
    gap12_map_df = build_smoothed_score_map(hist_df, "gap_1_2_bucket")
    gap13_map_df = build_smoothed_score_map(hist_df, "gap_1_3_bucket")
    gov_map_df = build_smoothed_score_map(hist_df, "top_pick_governance_band")
    pace_map_df = build_smoothed_score_map(hist_df, "pace_trust_band_v1")

    field_map = dict(zip(field_map_df["field_size_bucket"], field_map_df["score"]))
    gap12_map = dict(zip(gap12_map_df["gap_1_2_bucket"], gap12_map_df["score"]))
    gap13_map = dict(zip(gap13_map_df["gap_1_3_bucket"], gap13_map_df["score"]))
    gov_map = dict(zip(gov_map_df["top_pick_governance_band"], gov_map_df["score"]))
    pace_map = dict(zip(pace_map_df["pace_trust_band_v1"], pace_map_df["score"]))

    hist_df["field_size_score"] = hist_df["field_size_bucket"].map(field_map).fillna(50.0)
    hist_df["gap_1_2_score"] = hist_df["gap_1_2_bucket"].map(gap12_map).fillna(50.0)
    hist_df["gap_1_3_score"] = hist_df["gap_1_3_bucket"].map(gap13_map).fillna(50.0)
    hist_df["governance_score"] = hist_df["top_pick_governance_band"].map(gov_map).fillna(50.0)
    hist_df["pace_trust_score"] = hist_df["pace_trust_band_v1"].map(pace_map).fillna(50.0)
    hist_df["dominance_score"] = to_num(hist_df["dominance_certainty_score"]).fillna(to_num(hist_df["dominance_certainty_score"]).mean()).clip(0, 100)

    dominance_maps = build_dominance_proxy_maps(hist_df)

    component_maps = {
        "field": field_map,
        "gap12": gap12_map,
        "gap13": gap13_map,
        "governance": gov_map,
        "pace": pace_map,
    }
    return hist_df, component_maps, dominance_maps


def compute_trust_index(df: pd.DataFrame) -> pd.Series:
    return (
        WEIGHTS["field_size_score"] * df["field_size_score"]
        + WEIGHTS["gap_1_2_score"] * df["gap_1_2_score"]
        + WEIGHTS["gap_1_3_score"] * df["gap_1_3_score"]
        + WEIGHTS["dominance_score"] * df["dominance_score"]
        + WEIGHTS["governance_score"] * df["governance_score"]
        + WEIGHTS["pace_trust_score"] * df["pace_trust_score"]
    ).round(3)


def build_historical_audit(hist_df: pd.DataFrame) -> pd.DataFrame:
    hist_df = hist_df.copy()
    hist_df["winner_top3"] = hist_df["winner_rank"].le(3).astype(int)

    grouped = (
        hist_df.groupby("trust_band_v1", dropna=False)
        .agg(
            races=("race_key", "size"),
            top_pick_wins=("top_pick_won", "sum"),
            historical_top_pick_win_rate=("top_pick_won", "mean"),
            top3_hits=("winner_top3", "sum"),
            historical_top3_rate=("winner_top3", "mean"),
            historical_avg_winner_rank=("winner_rank", "mean"),
            avg_trust_index_v1=("trust_index_v1", "mean"),
            avg_field_size_score=("field_size_score", "mean"),
            avg_gap_1_2_score=("gap_1_2_score", "mean"),
            avg_gap_1_3_score=("gap_1_3_score", "mean"),
            avg_dominance_score=("dominance_score", "mean"),
            avg_governance_score=("governance_score", "mean"),
            avg_pace_trust_score=("pace_trust_score", "mean"),
            avg_field_size=("field_size", "mean"),
            avg_gap_1_2=("score_gap_1_2", "mean"),
            avg_gap_1_3=("score_gap_1_3", "mean"),
        )
        .reset_index()
    )
    grouped["sort_order"] = grouped["trust_band_v1"].map({band: idx for idx, band in enumerate(TRUST_BAND_ORDER, start=1)}).fillna(999)
    grouped = grouped.sort_values(["sort_order", "historical_top_pick_win_rate"], ascending=[True, False]).drop(columns=["sort_order"])

    overall = pd.DataFrame(
        [
            {
                "trust_band_v1": "OVERALL",
                "races": int(len(hist_df)),
                "top_pick_wins": int(hist_df["top_pick_won"].sum()),
                "historical_top_pick_win_rate": float(hist_df["top_pick_won"].mean()),
                "top3_hits": int(hist_df["winner_top3"].sum()),
                "historical_top3_rate": float(hist_df["winner_top3"].mean()),
                "historical_avg_winner_rank": float(hist_df["winner_rank"].mean()),
                "avg_trust_index_v1": float(hist_df["trust_index_v1"].mean()),
                "avg_field_size_score": float(hist_df["field_size_score"].mean()),
                "avg_gap_1_2_score": float(hist_df["gap_1_2_score"].mean()),
                "avg_gap_1_3_score": float(hist_df["gap_1_3_score"].mean()),
                "avg_dominance_score": float(hist_df["dominance_score"].mean()),
                "avg_governance_score": float(hist_df["governance_score"].mean()),
                "avg_pace_trust_score": float(hist_df["pace_trust_score"].mean()),
                "avg_field_size": float(hist_df["field_size"].mean()),
                "avg_gap_1_2": float(hist_df["score_gap_1_2"].mean()),
                "avg_gap_1_3": float(hist_df["score_gap_1_3"].mean()),
            }
        ]
    )
    audit_df = pd.concat([overall, grouped], ignore_index=True)
    return audit_df


def load_live_runner_scores() -> pd.DataFrame:
    if not LIVE_RUNNER_SCORE_PATH.exists():
        raise FileNotFoundError(f"Missing live runner score file: {LIVE_RUNNER_SCORE_PATH}")

    df = pd.read_csv(LIVE_RUNNER_SCORE_PATH, low_memory=False).copy()

    numeric_cols = [
        "race_no",
        "join_race_no",
        "runner_score_v6",
        "runner_rank_v6",
        "runner_order_v6",
        "field_size",
        "current_field_size_v5_2",
        "pace_trust_score_v1",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_num(df[col])

    for col in ["meeting_date", "race_date", "track", "join_track", "race_key_v6", "horse", "governance_band_v7_2", "pace_trust_band_v1"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)

    if "meeting_date" not in df.columns and "race_date" in df.columns:
        df["meeting_date"] = df["race_date"]
    if "meeting_date" in df.columns:
        df["meeting_date"] = df["meeting_date"].astype(str).str[:10]

    if "track" not in df.columns or df["track"].eq("").all():
        if "join_track" in df.columns:
            df["track"] = df["join_track"]

    if "race_no" not in df.columns or df["race_no"].isna().all():
        if "join_race_no" in df.columns:
            df["race_no"] = df["join_race_no"]

    if "race_key_v6" in df.columns:
        race_key_live = df["race_key_v6"].replace("", np.nan)
    else:
        race_key_live = pd.Series(np.nan, index=df.index)
    fallback_key = (
        df["meeting_date"].astype(str)
        + "|"
        + df["track"].astype(str)
        + "|R"
        + df["race_no"].fillna(0).astype(int).astype(str)
    )
    df["race_key_live_v1"] = race_key_live.fillna(fallback_key)

    if "field_size" not in df.columns:
        df["field_size"] = math.nan
    if "current_field_size_v5_2" in df.columns:
        df["field_size"] = df["field_size"].fillna(df["current_field_size_v5_2"])
    return df.copy()


def build_live_race_table(live_df: pd.DataFrame) -> pd.DataFrame:
    sort_rank = live_df["runner_rank_v6"] if "runner_rank_v6" in live_df.columns else pd.Series(np.nan, index=live_df.index)
    live_df = live_df.copy()
    live_df["sort_rank_v1"] = sort_rank.fillna(9999)
    live_df = live_df.sort_values(
        ["race_key_live_v1", "sort_rank_v1", "runner_score_v6", "horse"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)

    race_rows: list[dict[str, object]] = []
    for race_key, group in live_df.groupby("race_key_live_v1", sort=False):
        group = group.copy().sort_values(["sort_rank_v1", "runner_score_v6", "horse"], ascending=[True, False, True])
        top_row = group.iloc[0]
        top_three = group.head(3)
        scores = to_num(top_three["runner_score_v6"]).tolist()
        top_score = float(scores[0]) if len(scores) >= 1 and pd.notna(scores[0]) else math.nan
        second_score = float(scores[1]) if len(scores) >= 2 and pd.notna(scores[1]) else math.nan
        third_score = float(scores[2]) if len(scores) >= 3 and pd.notna(scores[2]) else math.nan
        score_gap_1_2 = top_score - second_score if pd.notna(top_score) and pd.notna(second_score) else math.nan
        score_gap_1_3 = top_score - third_score if pd.notna(top_score) and pd.notna(third_score) else math.nan

        field_size_value = first_valid_numeric(group["field_size"])
        field_size = int(round(field_size_value)) if pd.notna(field_size_value) else int(len(group))

        race_rows.append(
            {
                "meeting_date": first_valid_text(group["meeting_date"], ""),
                "track": first_valid_text(group["track"], ""),
                "race_no": int(first_valid_numeric(group["race_no"])) if pd.notna(first_valid_numeric(group["race_no"])) else math.nan,
                "race_key": race_key,
                "top_pick_horse": first_valid_text(pd.Series([top_row.get("horse", "")]), ""),
                "top_pick_governance_band": first_valid_text(pd.Series([top_row.get("governance_band_v7_2", "UNKNOWN")]), "UNKNOWN"),
                "pace_trust_band_v1": first_valid_text(group["pace_trust_band_v1"], "UNKNOWN"),
                "pace_trust_score_raw_v1": first_valid_numeric(group["pace_trust_score_v1"]),
                "field_size": field_size,
                "top_score": top_score,
                "second_score": second_score,
                "third_score": third_score,
                "score_gap_1_2": score_gap_1_2,
                "score_gap_1_3": score_gap_1_3,
            }
        )

    race_df = pd.DataFrame(race_rows)
    race_df["field_size_bucket"] = race_df["field_size"].apply(field_size_bucket)
    race_df["gap_1_2_bucket"] = race_df["score_gap_1_2"].apply(gap_1_2_bucket)
    race_df["gap_1_3_bucket"] = race_df["score_gap_1_3"].apply(gap_1_3_bucket)
    return race_df


def build_component_scores_for_live(
    live_race_df: pd.DataFrame,
    component_maps: dict[str, dict[str, float]],
    dominance_maps: dict[str, pd.DataFrame | float],
) -> pd.DataFrame:
    df = live_race_df.copy()
    df["field_size_score"] = df["field_size_bucket"].map(component_maps["field"]).fillna(50.0)
    df["gap_1_2_score"] = df["gap_1_2_bucket"].map(component_maps["gap12"]).fillna(50.0)
    df["gap_1_3_score"] = df["gap_1_3_bucket"].map(component_maps["gap13"]).fillna(50.0)
    df["governance_score"] = df["top_pick_governance_band"].map(component_maps["governance"]).fillna(50.0)
    df["pace_trust_score"] = df["pace_trust_band_v1"].map(component_maps["pace"]).fillna(50.0)
    df["dominance_score"] = df.apply(lambda row: predict_dominance_score(row, dominance_maps), axis=1).clip(0, 100).round(3)
    df["dominance_certainty_band"] = df["dominance_score"].apply(dominance_band)
    df["trust_index_v1"] = compute_trust_index(df)
    df["trust_band_v1"] = df["trust_index_v1"].apply(trust_band)
    return df


def build_historical_with_trust(hist_df: pd.DataFrame) -> pd.DataFrame:
    hist_df = hist_df.copy()
    hist_df["trust_index_v1"] = compute_trust_index(hist_df)
    hist_df["trust_band_v1"] = hist_df["trust_index_v1"].apply(trust_band)
    return hist_df


def main() -> None:
    hist_df = load_historical_certainty()
    hist_df, component_maps, dominance_maps = add_historical_components(hist_df)
    hist_df = build_historical_with_trust(hist_df)
    audit_df = build_historical_audit(hist_df)

    live_runner_df = load_live_runner_scores()
    live_race_df = build_live_race_table(live_runner_df)
    live_race_df = build_component_scores_for_live(live_race_df, component_maps, dominance_maps)

    band_lookup = audit_df[audit_df["trust_band_v1"].isin(TRUST_BAND_ORDER)].copy()
    band_lookup = band_lookup[[
        "trust_band_v1",
        "historical_top_pick_win_rate",
        "historical_top3_rate",
        "historical_avg_winner_rank",
    ]]
    band_lookup = band_lookup.rename(
        columns={
            "historical_top_pick_win_rate": "historical_top_pick_win_rate_trust_band_v1",
            "historical_top3_rate": "historical_top3_rate_trust_band_v1",
            "historical_avg_winner_rank": "historical_avg_winner_rank_trust_band_v1",
        }
    )
    live_race_df = live_race_df.merge(band_lookup, on="trust_band_v1", how="left")

    live_race_df = live_race_df[
        [
            "meeting_date",
            "track",
            "race_no",
            "race_key",
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
            "historical_top_pick_win_rate_trust_band_v1",
            "historical_top3_rate_trust_band_v1",
            "historical_avg_winner_rank_trust_band_v1",
        ]
    ].copy()

    live_race_df.to_csv(TRUST_INDEX_OUT, index=False)
    audit_df.to_csv(TRUST_AUDIT_OUT, index=False)

    best_live = live_race_df.sort_values(["trust_index_v1", "field_size_score", "gap_1_3_score"], ascending=[False, False, False]).iloc[0]
    print("[EDGEIQ_TRUST_INDEX_V1] COMPLETE")
    print(f"historical_races={len(hist_df)}")
    print(f"live_races={len(live_race_df)}")
    print(f"overall_historical_top_pick_win_rate={float(hist_df['top_pick_won'].mean()):.6f}")
    print(f"best_live_race={best_live['race_key']}")
    print(f"best_live_trust_band={best_live['trust_band_v1']}")
    print(f"best_live_trust_index={float(best_live['trust_index_v1']):.3f}")
    print(f"trust_index_out={TRUST_INDEX_OUT}")
    print(f"audit_out={TRUST_AUDIT_OUT}")


if __name__ == "__main__":
    main()
