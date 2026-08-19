from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC_DETAIL = DATA / "edgeiq_v6_1_probability_calibration_replay_v1_detail.csv"
SRC_SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"
SRC_BACKTEST = DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv"

OUT_DETAIL = DATA / "edgeiq_v6_1_probability_segment_calibration_v1_detail.csv"
OUT_BY_CLASS = DATA / "edgeiq_v6_1_probability_segment_calibration_v1_by_class.csv"
OUT_BY_FIELD = DATA / "edgeiq_v6_1_probability_segment_calibration_v1_by_field_size.csv"
OUT_BY_STARTS = DATA / "edgeiq_v6_1_probability_segment_calibration_v1_by_starts.csv"
OUT_BY_BAND = DATA / "edgeiq_v6_1_probability_segment_calibration_v1_by_projection_band.csv"
OUT_BY_GAP = DATA / "edgeiq_v6_1_probability_segment_calibration_v1_by_gap_bucket.csv"
OUT_BY_PROB = DATA / "edgeiq_v6_1_probability_segment_calibration_v1_by_prob_bucket.csv"
OUT_INTERACTIONS = DATA / "edgeiq_v6_1_probability_segment_calibration_v1_interactions.csv"
OUT_ATE_IRON = DATA / "edgeiq_v6_1_probability_segment_calibration_v1_ate_iron_segment.csv"
OUT_SUMMARY = DATA / "edgeiq_v6_1_probability_segment_calibration_v1_summary.csv"

DETAIL_SOURCE_NAME = SRC_DETAIL.name
SETTLED_SOURCE_NAME = SRC_SETTLED.name
BACKTEST_SOURCE_NAME = SRC_BACKTEST.name

ATE_IRON_LIVE_EXPECTED_WIN_PCT = 10.6
ATE_IRON_LIVE_FAIR = 9.43

FIELD_SIZE_ORDER = ["FIELD_1_6", "FIELD_7_8", "FIELD_9_10", "FIELD_11_12", "FIELD_13_PLUS", "FIELD_UNKNOWN"]
STARTS_ORDER = ["STARTS_0", "STARTS_1_2", "STARTS_3_5", "STARTS_6_10", "STARTS_11_PLUS", "STARTS_UNKNOWN"]
CLASS_ORDER = ["MAIDEN", "BM", "OPEN", "GROUP_LISTED", "2YO", "3YO", "UNKNOWN"]
RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_6", "RANK_7_PLUS", "UNKNOWN"]
PROBABILITY_BUCKET_ORDER = ["00_05", "05_10", "10_15", "15_20", "20_25", "25_30", "30_40", "40_PLUS", "UNKNOWN"]
GAP_BUCKET_ORDER = [
    "LT_NEG_20",
    "NEG_20_TO_NEG_15",
    "NEG_15_TO_NEG_10",
    "NEG_10_TO_NEG_8",
    "NEG_8_TO_NEG_6",
    "NEG_6_TO_NEG_4",
    "NEG_4_TO_NEG_2",
    "NEG_2_TO_0",
    "0_TO_2",
    "2_TO_4",
    "4_TO_6",
    "6_TO_8",
    "8_TO_10",
    "10_TO_15",
    "15_TO_20",
    "GT_20",
    "UNKNOWN",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def to_float(value: object) -> float | None:
    text = clean(value)
    if text == "":
        return None
    text = text.replace(",", "").replace("$", "")
    try:
        parsed = float(text)
    except Exception:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def to_int(value: object) -> int | None:
    number = to_float(value)
    if number is None:
        return None
    return int(round(number))


def round_num(value: float | None, places: int = 3) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return round(float(value), places)


def fair_from_pct(win_pct: float | None) -> float | None:
    if win_pct is None or not math.isfinite(win_pct) or win_pct <= 0:
        return None
    return 100.0 / float(win_pct)


def safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return (float(numerator) / float(denominator)) * 100.0


def normalise_text(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalise_track(value: object) -> str:
    text = normalise_text(value)
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_horse_key(value: object) -> str:
    text = normalise_text(value)
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def field_size_bucket(field_size: int | float | None) -> str:
    if field_size is None or (isinstance(field_size, float) and math.isnan(field_size)):
        return "FIELD_UNKNOWN"
    field_num = int(field_size)
    if field_num <= 6:
        return "FIELD_1_6"
    if field_num <= 8:
        return "FIELD_7_8"
    if field_num <= 10:
        return "FIELD_9_10"
    if field_num <= 12:
        return "FIELD_11_12"
    return "FIELD_13_PLUS"


def starts_bucket(starts_value: int | float | None) -> str:
    if starts_value is None or (isinstance(starts_value, float) and math.isnan(starts_value)):
        return "STARTS_UNKNOWN"
    starts_num = int(starts_value)
    if starts_num == 0:
        return "STARTS_0"
    if starts_num <= 2:
        return "STARTS_1_2"
    if starts_num <= 5:
        return "STARTS_3_5"
    if starts_num <= 10:
        return "STARTS_6_10"
    return "STARTS_11_PLUS"


def projection_confidence_from_status(status: object) -> str:
    text = normalise_text(status)
    if text == "PROVEN":
        return "HIGH"
    if text in {"LIMITED_DATA_3_4_STARTS", "LIMITED_DATA_2_STARTS"}:
        return "MEDIUM"
    if text in {"LIMITED_DATA_1_START", "FIRST_STARTER_OR_UNKNOWN", "IMPORT_UNKNOWN"}:
        return "LOW"
    return ""


def class_bucket_from_text(race_class_raw: object, race_name: object) -> str:
    raw = normalise_text(race_class_raw)
    name = normalise_text(race_name)
    combined = f"{raw} {name}".strip()

    if re.search(r"\bMAIDEN\b|\bMDN\b", combined):
        return "MAIDEN"

    if re.search(r"\bGROUP\s*[123]\b|\bG[123]\b|\bLISTED\b", combined):
        return "GROUP_LISTED"

    if re.search(r"\bBM\s*\d+\b|\bBENCHMARK\b|\b0\s*-\s*\d+\b", combined):
        return "BM"

    if re.search(r"\b2YO\b|\b2Y\b|\bTWO YEAR OLD\b", combined):
        return "2YO"

    if re.search(r"\b3YO\b|\b3Y\b|\bTHREE YEAR OLD\b", combined):
        return "3YO"

    if re.search(r"\bHANDICAP\b|\bHCP\b|\bOPEN\b|\bPLATE\b|\bSET WEIGHTS\b|\bWFA\b|\bWEIGHT FOR AGE\b|\bVOBIS\b", combined):
        return "OPEN"

    if raw in {"UNKNOWN", "GOOD", "GOOD3", "GOOD4", "SOFT", "SOFT5", "SOFT6", "HEAVY", "HEAVY8"}:
        return "UNKNOWN"

    if raw != "":
        return "OPEN"
    if name != "":
        return "UNKNOWN"
    return "UNKNOWN"


def brier_from_series(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) == 0:
        return None
    return float(values.mean())


def build_enriched_detail() -> pd.DataFrame:
    detail = load_required_csv(SRC_DETAIL)
    settled = load_required_csv(SRC_SETTLED)
    backtest = load_required_csv(SRC_BACKTEST)

    backtest = backtest[backtest["model"].map(normalise_text).eq("V6_1_RESEARCH_PRIOR")].copy()

    detail["race_key"] = detail["race_key"].map(clean)
    detail["meeting_date"] = detail["meeting_date"].map(clean).str[:10]
    detail["track"] = detail["track"].map(clean)
    detail["race_no"] = detail["race_no"].map(clean)
    detail["horse"] = detail["horse"].map(clean)
    detail["horse_key"] = detail["horse_key"].map(clean)
    detail["detail_join_key"] = detail["race_key"].map(normalise_text) + "|" + detail["horse_key"].map(normalise_horse_key)
    detail["backtest_join_key"] = (
        detail["meeting_date"].map(clean).str[:10]
        + "|"
        + detail["track"].map(normalise_track)
        + "|"
        + detail["horse_key"].map(normalise_horse_key)
    )

    settled["settled_join_key"] = settled["race_key"].map(normalise_text) + "|" + settled["horse_key"].map(normalise_horse_key)
    settled_subset = settled[["settled_join_key", "starts_before", "projection_status_v6"]].copy()
    settled_subset["starts_before"] = settled_subset["starts_before"].map(to_int)
    settled_subset["projection_status_v6"] = settled_subset["projection_status_v6"].map(clean)

    backtest["backtest_join_key"] = (
        backtest["race_date"].map(clean).str[:10]
        + "|"
        + backtest["track"].map(normalise_track)
        + "|"
        + backtest["horse"].map(normalise_horse_key)
    )
    backtest["backtest_race_key"] = backtest["race_key"].map(clean)
    race_key_parts = backtest["backtest_race_key"].str.split("|")
    backtest["race_class_raw"] = race_key_parts.str[4].fillna("").map(clean)
    backtest["condition_from_race_key"] = race_key_parts.str[5].fillna("").map(clean)
    backtest_subset = backtest[
        [
            "backtest_join_key",
            "backtest_race_key",
            "race_name",
            "distance",
            "field_size",
            "prior_starts",
            "projection_band",
            "race_class_raw",
            "condition_from_race_key",
        ]
    ].copy()
    backtest_subset["distance"] = backtest_subset["distance"].map(to_float)
    backtest_subset["field_size"] = backtest_subset["field_size"].map(to_int)
    backtest_subset["prior_starts"] = backtest_subset["prior_starts"].map(to_int)
    backtest_subset["projection_band"] = backtest_subset["projection_band"].map(clean)
    backtest_subset["race_name"] = backtest_subset["race_name"].map(clean)
    backtest_subset["race_class_raw"] = backtest_subset["race_class_raw"].map(clean)
    backtest_subset["condition_from_race_key"] = backtest_subset["condition_from_race_key"].map(clean)

    race_field_sizes = (
        detail.groupby("race_key", dropna=False)
        .agg(field_size_detail=("horse", "count"))
        .reset_index()
    )

    merged = detail.merge(
        settled_subset,
        left_on="detail_join_key",
        right_on="settled_join_key",
        how="left",
    )
    merged = merged.merge(
        backtest_subset,
        on="backtest_join_key",
        how="left",
    )
    merged = merged.merge(race_field_sizes, on="race_key", how="left")

    merged["field_size"] = merged["field_size_detail"]
    merged.loc[merged["field_size"].isna(), "field_size"] = merged["field_size"]
    merged["field_size"] = pd.to_numeric(merged["field_size"], errors="coerce")
    back_field = pd.to_numeric(merged["field_size"], errors="coerce")
    detail_field = pd.to_numeric(merged["field_size_detail"], errors="coerce")
    merged["field_size"] = detail_field.fillna(back_field)

    merged["starts_found"] = pd.to_numeric(merged["starts_before"], errors="coerce")
    prior_starts = pd.to_numeric(merged["prior_starts"], errors="coerce")
    merged["starts_found"] = merged["starts_found"].fillna(prior_starts)

    merged["race_class_raw"] = merged["race_class_raw"].map(clean)
    merged["race_class"] = merged["race_class_raw"]
    merged["class_bucket"] = merged.apply(
        lambda row: class_bucket_from_text(row.get("race_class_raw", ""), row.get("race_name", "")),
        axis=1,
    )
    merged["field_size_bucket"] = merged["field_size"].map(field_size_bucket)
    merged["starts_bucket"] = merged["starts_found"].map(starts_bucket)
    merged["projection_confidence"] = merged["projection_status_v6"].map(projection_confidence_from_status)
    merged["projection_band_V6_1_RESEARCH"] = merged["projection_band_V6_1_RESEARCH"].map(clean)
    merged["probability_bucket"] = merged["probability_bucket"].map(clean)
    merged["gap_bucket"] = merged["gap_bucket"].map(clean)
    merged["rank_bucket"] = merged["rank_bucket"].map(clean)
    merged["V6_1_RESEARCH_probability"] = merged["V6_1_RESEARCH_probability"].map(to_float)
    merged["V6_1_RESEARCH_probability_pct"] = merged["V6_1_RESEARCH_probability_pct"].map(to_float)
    merged["V6_1_RESEARCH_fair_price"] = merged["V6_1_RESEARCH_fair_price"].map(to_float)
    merged["projection_gap_V6_1_RESEARCH"] = merged["projection_gap_V6_1_RESEARCH"].map(to_float)
    merged["projected_rating_V6_1_RESEARCH"] = merged["projected_rating_V6_1_RESEARCH"].map(to_float)
    merged["final_probability_rank_used"] = pd.to_numeric(merged["final_probability_rank_used"], errors="coerce")
    merged["won"] = pd.to_numeric(merged["won"], errors="coerce").fillna(0).astype(int)
    merged["placed"] = pd.to_numeric(merged["placed"], errors="coerce").fillna(0).astype(int)
    merged["finish_position"] = pd.to_numeric(merged["finish_position"], errors="coerce")
    merged["sp"] = merged["sp"].map(to_float)
    merged["calibration_error"] = merged["calibration_error"].map(to_float)
    merged["abs_calibration_error"] = merged["abs_calibration_error"].map(to_float)
    merged["brier_component"] = merged["brier_component"].map(to_float)
    merged["ate_iron_like_flag"] = "NO"
    merged["built_at"] = datetime.now(timezone.utc).isoformat()

    return merged


def summarize_segment(df: pd.DataFrame, segment_type: str, segment_value: str) -> dict[str, object]:
    rows = int(len(df))
    races = int(df["race_key"].nunique()) if "race_key" in df.columns else 0
    expected_wins = float(pd.to_numeric(df["V6_1_RESEARCH_probability"], errors="coerce").fillna(0.0).sum())
    actual_wins = float(pd.to_numeric(df["won"], errors="coerce").fillna(0.0).sum())
    expected_win_pct = safe_pct(expected_wins, rows)
    actual_win_pct = safe_pct(actual_wins, rows)
    calibration_delta_pct = None
    if expected_win_pct is not None and actual_win_pct is not None:
        calibration_delta_pct = expected_win_pct - actual_win_pct
    avg_probability = pd.to_numeric(df["V6_1_RESEARCH_probability"], errors="coerce").dropna()
    avg_fair = pd.to_numeric(df["V6_1_RESEARCH_fair_price"], errors="coerce").dropna()
    avg_gap = pd.to_numeric(df["projection_gap_V6_1_RESEARCH"], errors="coerce").dropna()
    avg_sp = pd.to_numeric(df["sp"], errors="coerce").dropna() if "sp" in df.columns else pd.Series(dtype=float)
    return {
        "segment_type": segment_type,
        "segment": segment_value,
        "rows": rows,
        "races": races,
        "expected_wins": round_num(expected_wins, 3),
        "actual_wins": round_num(actual_wins, 3),
        "expected_win_pct": round_num(expected_win_pct, 3),
        "actual_win_pct": round_num(actual_win_pct, 3),
        "calibration_delta_pct": round_num(calibration_delta_pct, 3),
        "abs_calibration_delta_pct": round_num(abs(calibration_delta_pct) if calibration_delta_pct is not None else None, 3),
        "avg_probability": round_num(float(avg_probability.mean()) if len(avg_probability) else None, 6),
        "avg_model_fair_price": round_num(float(avg_fair.mean()) if len(avg_fair) else None, 3),
        "empirical_fair_price": round_num(fair_from_pct(actual_win_pct), 3),
        "brier_score": round_num(brier_from_series(df["brier_component"]), 6),
        "avg_gap": round_num(float(avg_gap.mean()) if len(avg_gap) else None, 3),
        "avg_sp": round_num(float(avg_sp.mean()) if len(avg_sp) else None, 3),
        "median_sp": round_num(float(avg_sp.median()) if len(avg_sp) else None, 3),
    }


def aggregate_by_segment(df: pd.DataFrame, column: str, segment_type: str, order: list[str] | None = None) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for segment_value, group in df.groupby(column, dropna=False):
        value = clean(segment_value) or "UNKNOWN"
        record = summarize_segment(group.copy(), segment_type, value)
        record[column] = value
        records.append(record)
    result = pd.DataFrame(records)
    if result.empty:
        return result
    if order:
        order_map = {value: idx for idx, value in enumerate(order)}
        result["_order"] = result["segment"].map(lambda value: order_map.get(value, len(order_map) + 999))
        result = result.sort_values(["_order", "rows", "segment"], ascending=[True, False, True]).drop(columns=["_order"])
    else:
        result = result.sort_values(["rows", "segment"], ascending=[False, True])
    return result.reset_index(drop=True)


def build_interactions(detail: pd.DataFrame) -> pd.DataFrame:
    interaction_specs = [
        ("CLASS_PLUS_STARTS", ["class_bucket", "starts_bucket"]),
        ("CLASS_PLUS_GAP", ["class_bucket", "gap_bucket"]),
        ("CLASS_PLUS_PROJECTION_BAND", ["class_bucket", "projection_band_V6_1_RESEARCH"]),
        ("STARTS_PLUS_GAP", ["starts_bucket", "gap_bucket"]),
        ("PROJECTION_BAND_PLUS_GAP", ["projection_band_V6_1_RESEARCH", "gap_bucket"]),
        ("CLASS_PLUS_STARTS_PLUS_GAP", ["class_bucket", "starts_bucket", "gap_bucket"]),
        (
            "CLASS_PLUS_STARTS_PLUS_PROJECTION_BAND_PLUS_GAP",
            ["class_bucket", "starts_bucket", "projection_band_V6_1_RESEARCH", "gap_bucket"],
        ),
    ]

    records: list[dict[str, object]] = []
    for interaction_type, columns in interaction_specs:
        grouped = detail.groupby(columns, dropna=False)
        for keys, group in grouped:
            if len(group) < 20:
                continue
            if not isinstance(keys, tuple):
                keys = (keys,)
            parts = []
            for column, value in zip(columns, keys):
                parts.append(f"{column}={clean(value) or 'UNKNOWN'}")
            interaction_segment = " | ".join(parts)
            record = summarize_segment(group.copy(), interaction_type, interaction_segment)
            record["interaction_type"] = interaction_type
            record["interaction_segment"] = interaction_segment
            records.append(record)

    result = pd.DataFrame(records)
    if result.empty:
        return result
    result = result[
        [
            "interaction_type",
            "interaction_segment",
            "segment_type",
            "segment",
            "rows",
            "races",
            "expected_wins",
            "actual_wins",
            "expected_win_pct",
            "actual_win_pct",
            "calibration_delta_pct",
            "abs_calibration_delta_pct",
            "avg_probability",
            "avg_model_fair_price",
            "empirical_fair_price",
            "brier_score",
            "avg_gap",
            "avg_sp",
            "median_sp",
        ]
    ].sort_values(
        ["calibration_delta_pct", "abs_calibration_delta_pct", "rows"],
        ascending=[False, False, False],
    )
    return result.reset_index(drop=True)


def build_ate_iron_segment(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    levels = [
        (
            0,
            "EXACT",
            (
                detail["class_bucket"].eq("MAIDEN")
                & detail["starts_bucket"].isin(["STARTS_1_2", "STARTS_3_5"])
                & detail["gap_bucket"].eq("NEG_6_TO_NEG_4")
                & detail["projection_band_V6_1_RESEARCH"].map(normalise_text).str.contains("NEGATIVE", na=False)
                & detail["field_size_bucket"].eq("FIELD_7_8")
            ),
        ),
        (
            1,
            "RELAX_REMOVE_FIELD_SIZE",
            (
                detail["class_bucket"].eq("MAIDEN")
                & detail["starts_bucket"].isin(["STARTS_1_2", "STARTS_3_5"])
                & detail["gap_bucket"].eq("NEG_6_TO_NEG_4")
                & detail["projection_band_V6_1_RESEARCH"].map(normalise_text).str.contains("NEGATIVE", na=False)
            ),
        ),
        (
            2,
            "RELAX_REMOVE_PROJECTION_BAND",
            (
                detail["class_bucket"].eq("MAIDEN")
                & detail["starts_bucket"].isin(["STARTS_1_2", "STARTS_3_5"])
                & detail["gap_bucket"].eq("NEG_6_TO_NEG_4")
            ),
        ),
        (
            3,
            "RELAX_REMOVE_STARTS_BUCKET",
            (
                detail["class_bucket"].eq("MAIDEN")
                & detail["gap_bucket"].eq("NEG_6_TO_NEG_4")
            ),
        ),
    ]

    records: list[dict[str, object]] = []
    chosen_level_name = ""
    chosen_mask = pd.Series(False, index=detail.index)
    for relaxation_level, level_name, mask in levels:
        subset = detail.loc[mask].copy()
        record = summarize_segment(subset, "ATE_IRON_SEGMENT", level_name)
        record["relaxation_level"] = relaxation_level
        record["ate_iron_segment_level"] = level_name
        record["sample_floor_met"] = "YES" if len(subset) >= 20 else "NO"
        records.append(record)
        if chosen_level_name == "" and len(subset) >= 20:
            chosen_level_name = level_name
            chosen_mask = mask.copy()

    if chosen_level_name == "":
        chosen_level_name = "RELAX_REMOVE_STARTS_BUCKET"
        chosen_mask = levels[-1][2].copy()

    chosen_rows = detail.loc[chosen_mask].copy()
    chosen_summary = summarize_segment(chosen_rows, "ATE_IRON_SEGMENT", chosen_level_name)
    chosen_summary["relaxation_level"] = next(level[0] for level in levels if level[1] == chosen_level_name)
    chosen_summary["ate_iron_segment_level"] = chosen_level_name
    chosen_summary["sample_floor_met"] = "YES" if len(chosen_rows) >= 20 else "NO"

    ate_df = pd.DataFrame(records)
    ate_df["chosen_flag"] = ate_df["ate_iron_segment_level"].eq(chosen_level_name).map(lambda value: "YES" if value else "NO")
    ate_df = ate_df[
        [
            "relaxation_level",
            "ate_iron_segment_level",
            "chosen_flag",
            "sample_floor_met",
            "segment_type",
            "segment",
            "rows",
            "races",
            "expected_wins",
            "actual_wins",
            "expected_win_pct",
            "actual_win_pct",
            "calibration_delta_pct",
            "abs_calibration_delta_pct",
            "avg_probability",
            "avg_model_fair_price",
            "empirical_fair_price",
            "brier_score",
            "avg_gap",
            "avg_sp",
            "median_sp",
        ]
    ]

    detail = detail.copy()
    detail.loc[chosen_mask, "ate_iron_like_flag"] = "YES"
    return detail, ate_df


def build_summary(
    detail: pd.DataFrame,
    interactions: pd.DataFrame,
    ate_iron_df: pd.DataFrame,
) -> pd.DataFrame:
    rows_used = int(len(detail))
    races_used = int(detail["race_key"].nunique())
    expected_total_wins = float(pd.to_numeric(detail["V6_1_RESEARCH_probability"], errors="coerce").fillna(0.0).sum())
    actual_total_wins = float(pd.to_numeric(detail["won"], errors="coerce").fillna(0.0).sum())
    global_expected_win_pct = safe_pct(expected_total_wins, rows_used)
    global_actual_win_pct = safe_pct(actual_total_wins, rows_used)
    global_delta = None
    if global_expected_win_pct is not None and global_actual_win_pct is not None:
        global_delta = global_expected_win_pct - global_actual_win_pct

    worst_segment = ""
    worst_delta = None
    worst_rows = None
    if not interactions.empty:
        positive = interactions[pd.to_numeric(interactions["calibration_delta_pct"], errors="coerce").fillna(-999999) > 0].copy()
        source = positive if not positive.empty else interactions.copy()
        source = source.sort_values(
            ["calibration_delta_pct", "abs_calibration_delta_pct", "rows"],
            ascending=[False, False, False],
        )
        first = source.iloc[0]
        worst_segment = clean(first.get("interaction_segment", ""))
        worst_delta = to_float(first.get("calibration_delta_pct"))
        worst_rows = to_int(first.get("rows"))

    chosen_ate = ate_iron_df[ate_iron_df["chosen_flag"] == "YES"].copy()
    ate_level = ""
    ate_rows = None
    ate_expected = None
    ate_actual = None
    ate_empirical_fair = None
    if not chosen_ate.empty:
        chosen_row = chosen_ate.iloc[0]
        ate_level = clean(chosen_row.get("ate_iron_segment_level", ""))
        ate_rows = to_int(chosen_row.get("rows"))
        ate_expected = to_float(chosen_row.get("expected_win_pct"))
        ate_actual = to_float(chosen_row.get("actual_win_pct"))
        ate_empirical_fair = to_float(chosen_row.get("empirical_fair_price"))

    verdict = "ATE_IRON_PRICE_NOT_DISPROVEN_BY_SEGMENT"
    if ate_actual is not None and (ATE_IRON_LIVE_EXPECTED_WIN_PCT - ate_actual) >= 3.0:
        verdict = "ATE_IRON_SEGMENT_OVERPRICED_BY_MODEL"

    summary_row = {
        "status": "EDGEIQ_V6_1_PROBABILITY_SEGMENT_CALIBRATION_V1_BUILT",
        "source_detail": DETAIL_SOURCE_NAME,
        "enrich_source_used": f"{SETTLED_SOURCE_NAME};{BACKTEST_SOURCE_NAME}",
        "rows_used": rows_used,
        "races_used": races_used,
        "global_expected_win_pct": round_num(global_expected_win_pct, 3),
        "global_actual_win_pct": round_num(global_actual_win_pct, 3),
        "global_calibration_delta_pct": round_num(global_delta, 3),
        "worst_overconfident_segment": worst_segment,
        "worst_overconfident_segment_delta": round_num(worst_delta, 3),
        "worst_overconfident_segment_rows": worst_rows,
        "ate_iron_segment_level": ate_level,
        "ate_iron_segment_rows": ate_rows,
        "ate_iron_segment_expected_win_pct": round_num(ate_expected, 3),
        "ate_iron_segment_actual_win_pct": round_num(ate_actual, 3),
        "ate_iron_segment_empirical_fair": round_num(ate_empirical_fair, 3),
        "ate_iron_live_expected_win_pct": ATE_IRON_LIVE_EXPECTED_WIN_PCT,
        "ate_iron_live_fair": ATE_IRON_LIVE_FAIR,
        "verdict": verdict,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    return pd.DataFrame([summary_row])


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


def print_table(title: str, df: pd.DataFrame, max_rows: int = 20) -> None:
    print(title)
    if df.empty:
        print("  <empty>")
        return
    print(df.head(max_rows).to_string(index=False))
    print("")


def main() -> None:
    detail = build_enriched_detail()
    detail, ate_iron_df = build_ate_iron_segment(detail)

    detail = detail[
        [
            "race_key",
            "meeting_date",
            "track",
            "race_no",
            "horse",
            "horse_key",
            "race_class_raw",
            "race_class",
            "class_bucket",
            "field_size",
            "field_size_bucket",
            "starts_found",
            "starts_before",
            "prior_starts",
            "starts_bucket",
            "projection_status_v6",
            "projection_confidence",
            "projection_band_V6_1_RESEARCH",
            "projection_gap_V6_1_RESEARCH",
            "gap_bucket",
            "V6_1_RESEARCH_probability",
            "V6_1_RESEARCH_probability_pct",
            "V6_1_RESEARCH_fair_price",
            "probability_bucket",
            "final_probability_rank_used",
            "rank_bucket",
            "won",
            "placed",
            "finish_position",
            "sp",
            "calibration_error",
            "abs_calibration_error",
            "brier_component",
            "ate_iron_like_flag",
            "source_file",
            "built_at",
        ]
    ].copy()

    by_class = aggregate_by_segment(detail, "class_bucket", "CLASS_BUCKET", CLASS_ORDER)
    by_field = aggregate_by_segment(detail, "field_size_bucket", "FIELD_SIZE_BUCKET", FIELD_SIZE_ORDER)
    by_starts = aggregate_by_segment(detail, "starts_bucket", "STARTS_BUCKET", STARTS_ORDER)
    by_band = aggregate_by_segment(detail, "projection_band_V6_1_RESEARCH", "PROJECTION_BAND", None)
    by_gap = aggregate_by_segment(detail, "gap_bucket", "GAP_BUCKET", GAP_BUCKET_ORDER)
    by_prob = aggregate_by_segment(detail, "probability_bucket", "PROBABILITY_BUCKET", PROBABILITY_BUCKET_ORDER)
    interactions = build_interactions(detail)
    summary = build_summary(detail, interactions, ate_iron_df)

    write_csv(detail, OUT_DETAIL)
    write_csv(by_class, OUT_BY_CLASS)
    write_csv(by_field, OUT_BY_FIELD)
    write_csv(by_starts, OUT_BY_STARTS)
    write_csv(by_band, OUT_BY_BAND)
    write_csv(by_gap, OUT_BY_GAP)
    write_csv(by_prob, OUT_BY_PROB)
    write_csv(interactions, OUT_INTERACTIONS)
    write_csv(ate_iron_df, OUT_ATE_IRON)
    write_csv(summary, OUT_SUMMARY)

    print("[V6_1_PROBABILITY_SEGMENT_CALIBRATION_V1] COMPLETE")
    print(summary.to_string(index=False))
    print("")
    print_table("ATE IRON SEGMENT", ate_iron_df, max_rows=10)
    print_table("TOP OVERCONFIDENT INTERACTIONS", interactions, max_rows=20)
    print_table("BY CLASS", by_class, max_rows=20)


if __name__ == "__main__":
    main()
