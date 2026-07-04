from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC_REPLAY = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded.csv"
SRC_SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"

OUT_DETAIL = DATA / "edgeiq_v6_1_probability_calibration_v2_by_match_tier_detail.csv"
OUT_SUMMARY = DATA / "edgeiq_v6_1_probability_calibration_v2_by_match_tier_summary.csv"
OUT_PROB_BUCKETS = DATA / "edgeiq_v6_1_probability_calibration_v2_by_match_tier_probability_buckets.csv"
OUT_ATE_SEGMENTS = DATA / "edgeiq_v6_1_probability_calibration_v2_by_match_tier_ate_segments.csv"

TIER_ORDER = [
    "HIGH_CONFIDENCE_ONLY",
    "HIGH_PLUS_MEDIUM",
    "ALL_V2_EXPANDED",
]

TIER_ALLOWED_STAGES = {
    "HIGH_CONFIDENCE_ONLY": {"DATE_TRACK_RACE_NO_HORSE_KEY"},
    "HIGH_PLUS_MEDIUM": {"DATE_TRACK_RACE_NO_HORSE_KEY", "DATE_TRACK_NORMALIZED_HORSE"},
    "ALL_V2_EXPANDED": {"DATE_TRACK_RACE_NO_HORSE_KEY", "DATE_TRACK_NORMALIZED_HORSE", "DATE_HORSE_KEY"},
}

PROBABILITY_BUCKETS = [
    (0.00, 0.05, "00_05"),
    (0.05, 0.10, "05_10"),
    (0.10, 0.15, "10_15"),
    (0.15, 0.20, "15_20"),
    (0.20, 0.25, "20_25"),
    (0.25, 0.30, "25_30"),
    (0.30, 0.40, "30_40"),
    (0.40, math.inf, "40_PLUS"),
]

GAP_BUCKETS = [
    (-math.inf, -20.0, "LT_NEG_20"),
    (-20.0, -15.0, "NEG_20_TO_NEG_15"),
    (-15.0, -10.0, "NEG_15_TO_NEG_10"),
    (-10.0, -8.0, "NEG_10_TO_NEG_8"),
    (-8.0, -6.0, "NEG_8_TO_NEG_6"),
    (-6.0, -4.0, "NEG_6_TO_NEG_4"),
    (-4.0, -2.0, "NEG_4_TO_NEG_2"),
    (-2.0, 0.0, "NEG_2_TO_0"),
    (0.0, 2.0, "0_TO_2"),
    (2.0, 4.0, "2_TO_4"),
    (4.0, 6.0, "4_TO_6"),
    (6.0, 8.0, "6_TO_8"),
    (8.0, 10.0, "8_TO_10"),
    (10.0, 15.0, "10_TO_15"),
    (15.0, 20.0, "15_TO_20"),
    (20.0, math.inf, "GT_20"),
]

FIELD_SIZE_ORDER = ["FIELD_1_6", "FIELD_7_8", "FIELD_9_10", "FIELD_11_12", "FIELD_13_PLUS", "FIELD_UNKNOWN"]
STARTS_ORDER = ["STARTS_0", "STARTS_1_2", "STARTS_3_5", "STARTS_6_10", "STARTS_11_PLUS", "STARTS_UNKNOWN"]
CLASS_ORDER = ["MAIDEN", "BM", "OPEN", "GROUP_LISTED", "2YO", "3YO", "UNKNOWN"]
RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_6", "RANK_7_PLUS", "UNKNOWN"]
PROB_BUCKET_ORDER = [label for _, _, label in PROBABILITY_BUCKETS] + ["UNKNOWN"]
GAP_BUCKET_ORDER = [label for _, _, label in GAP_BUCKETS] + ["UNKNOWN"]


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


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


def safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return (float(numerator) / float(denominator)) * 100.0


def fair_from_pct(win_pct: float | None) -> float | None:
    if win_pct is None or not math.isfinite(win_pct) or win_pct <= 0:
        return None
    return 100.0 / win_pct


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def norm_text(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).upper()).strip()


def canon_horse(value: object) -> str:
    text = norm_text(value).replace("â€™", "'").replace("’", "'")
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def probability_bucket(probability: float | None) -> str:
    if probability is None or (isinstance(probability, float) and math.isnan(probability)):
        return "UNKNOWN"
    for lower, upper, label in PROBABILITY_BUCKETS:
        if probability >= lower and probability < upper:
            return label
    return "UNKNOWN"


def gap_bucket(gap: float | None) -> str:
    if gap is None or (isinstance(gap, float) and math.isnan(gap)):
        return "UNKNOWN"
    for lower, upper, label in GAP_BUCKETS:
        if gap >= lower and gap < upper:
            return label
    return "UNKNOWN"


def rank_bucket(rank_value: int | float | None) -> str:
    if rank_value is None or (isinstance(rank_value, float) and math.isnan(rank_value)):
        return "UNKNOWN"
    rank_num = int(rank_value)
    if rank_num == 1:
        return "RANK_1"
    if rank_num == 2:
        return "RANK_2"
    if rank_num == 3:
        return "RANK_3"
    if 4 <= rank_num <= 6:
        return "RANK_4_6"
    return "RANK_7_PLUS"


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


def class_bucket_from_backtest_key(backtest_race_key: object) -> tuple[str, str, str]:
    key = clean(backtest_race_key)
    if key == "":
        return "", "", "UNKNOWN"

    parts = key.split("|")
    race_name = clean(parts[3]) if len(parts) > 3 else ""
    race_class_raw = clean(parts[4]) if len(parts) > 4 else ""
    combined = f"{norm_text(race_class_raw)} {norm_text(race_name)}".strip()

    if re.search(r"\bMAIDEN\b|\bMDN\b", combined):
        return race_class_raw, race_name, "MAIDEN"
    if re.search(r"\bGROUP\s*[123]\b|\bG[123]\b|\bLISTED\b", combined):
        return race_class_raw, race_name, "GROUP_LISTED"
    if re.search(r"\bBM\s*\d+\b|\bBENCHMARK\b|\b0\s*-\s*\d+\b", combined):
        return race_class_raw, race_name, "BM"
    if re.search(r"\b2YO\b|\b2Y\b|\bTWO YEAR OLD\b", combined):
        return race_class_raw, race_name, "2YO"
    if re.search(r"\b3YO\b|\b3Y\b|\bTHREE YEAR OLD\b", combined):
        return race_class_raw, race_name, "3YO"
    if re.search(r"\bHANDICAP\b|\bHCP\b|\bOPEN\b|\bPLATE\b|\bSET WEIGHTS\b|\bWFA\b|\bWEIGHT FOR AGE\b|\bVOBIS\b", combined):
        return race_class_raw, race_name, "OPEN"
    if race_class_raw != "":
        return race_class_raw, race_name, "UNKNOWN"
    return race_class_raw, race_name, "UNKNOWN"


def brier_from_series(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) == 0:
        return None
    return float(values.mean())


def build_base_enriched() -> pd.DataFrame:
    replay = load_required_csv(SRC_REPLAY)
    settled = load_required_csv(SRC_SETTLED)

    required_columns = [
        "race_key",
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "won",
        "placed",
        "finish_position",
        "sp",
        "projection_gap_V6_1_RESEARCH",
        "projected_rating_V6_1_RESEARCH",
        "race_target_rating_V6_1_RESEARCH",
        "projection_band_V6_1_RESEARCH",
        "V6_1_RESEARCH_probability",
        "V6_1_RESEARCH_fair_price",
        "source_match_stage_v2",
        "backtest_race_key",
    ]
    missing = [column for column in required_columns if column not in replay.columns]
    if missing:
        raise RuntimeError(f"Missing required replay columns: {missing}")

    settled_subset = settled[["race_key", "horse_key", "horse", "starts_before"]].copy()
    settled_subset["horse_key_join"] = settled_subset["horse_key"].map(canon_horse)
    settled_subset["horse_norm_join"] = settled_subset["horse"].map(canon_horse)
    settled_subset["settled_join_stage_1"] = settled_subset["race_key"].map(clean) + "|" + settled_subset["horse_key_join"]
    settled_subset["settled_join_stage_2"] = settled_subset["race_key"].map(clean) + "|" + settled_subset["horse_norm_join"]
    settled_subset["starts_before"] = settled_subset["starts_before"].map(to_int)
    by_key = (
        settled_subset[["settled_join_stage_1", "starts_before"]]
        .drop_duplicates(subset=["settled_join_stage_1"], keep="first")
        .rename(columns={"settled_join_stage_1": "join_key"})
    )
    by_norm = (
        settled_subset[["settled_join_stage_2", "starts_before"]]
        .drop_duplicates(subset=["settled_join_stage_2"], keep="first")
        .rename(columns={"settled_join_stage_2": "join_key"})
    )
    starts_map_key = dict(zip(by_key["join_key"], by_key["starts_before"]))
    starts_map_norm = dict(zip(by_norm["join_key"], by_norm["starts_before"]))

    base = replay.copy()
    base["meeting_date"] = base["meeting_date"].map(clean).str[:10]
    base["track"] = base["track"].map(clean)
    base["race_no"] = base["race_no"].map(clean)
    base["horse"] = base["horse"].map(clean)
    base["horse_key"] = base["horse_key"].map(canon_horse)
    base["horse_norm"] = base["horse"].map(canon_horse)
    base["projection_gap_V6_1_RESEARCH"] = base["projection_gap_V6_1_RESEARCH"].map(to_float)
    base["projected_rating_V6_1_RESEARCH"] = base["projected_rating_V6_1_RESEARCH"].map(to_float)
    base["race_target_rating_V6_1_RESEARCH"] = base["race_target_rating_V6_1_RESEARCH"].map(to_float)
    base["V6_1_RESEARCH_probability"] = base["V6_1_RESEARCH_probability"].map(to_float)
    base["V6_1_RESEARCH_fair_price"] = base["V6_1_RESEARCH_fair_price"].map(to_float)
    base["won"] = pd.to_numeric(base["won"], errors="coerce").fillna(0).astype(int)
    base["placed"] = pd.to_numeric(base["placed"], errors="coerce").fillna(0).astype(int)
    base["finish_position"] = pd.to_numeric(base["finish_position"], errors="coerce")
    base["sp"] = base["sp"].map(to_float)
    base["source_match_stage_v2"] = base["source_match_stage_v2"].map(clean)
    base["projection_band_V6_1_RESEARCH"] = base["projection_band_V6_1_RESEARCH"].map(clean)

    base["join_key_1"] = base["race_key"].map(clean) + "|" + base["horse_key"]
    base["join_key_2"] = base["race_key"].map(clean) + "|" + base["horse_norm"]
    base["starts_found"] = base["join_key_1"].map(starts_map_key)
    base.loc[base["starts_found"].isna(), "starts_found"] = base.loc[base["starts_found"].isna(), "join_key_2"].map(starts_map_norm)

    class_parts = base["backtest_race_key"].map(clean).apply(class_bucket_from_backtest_key)
    base["race_class_raw"] = class_parts.map(lambda item: item[0])
    base["race_name_backtest"] = class_parts.map(lambda item: item[1])
    base["class_bucket"] = class_parts.map(lambda item: item[2])

    return base


def summarize_group(df: pd.DataFrame) -> dict[str, object]:
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
    avg_sp = pd.to_numeric(df["sp"], errors="coerce").dropna()

    return {
        "rows": rows,
        "races": races,
        "expected_wins": round_num(expected_wins, 3),
        "actual_wins": round_num(actual_wins, 3),
        "expected_win_pct": round_num(expected_win_pct, 3),
        "actual_win_pct": round_num(actual_win_pct, 3),
        "calibration_delta_pct": round_num(calibration_delta_pct, 3),
        "avg_probability": round_num(float(avg_probability.mean()) if len(avg_probability) else None, 6),
        "avg_model_fair_price": round_num(float(avg_fair.mean()) if len(avg_fair) else None, 3),
        "empirical_fair_price": round_num(fair_from_pct(actual_win_pct), 3),
        "brier_score": round_num(brier_from_series(df["brier_component"]), 6),
        "avg_gap": round_num(float(avg_gap.mean()) if len(avg_gap) else None, 3),
        "avg_sp": round_num(float(avg_sp.mean()) if len(avg_sp) else None, 3),
        "median_sp": round_num(float(avg_sp.median()) if len(avg_sp) else None, 3),
    }


def build_tier_detail(base: pd.DataFrame, tier_name: str) -> pd.DataFrame:
    allowed = TIER_ALLOWED_STAGES[tier_name]
    total_rows_by_race = base.groupby("race_key", dropna=False).size().rename("race_total_rows")

    tier_candidates = base[
        base["source_match_stage_v2"].isin(allowed)
        & base["projection_gap_V6_1_RESEARCH"].notna()
        & base["V6_1_RESEARCH_probability"].notna()
        & base["V6_1_RESEARCH_fair_price"].notna()
    ].copy()

    candidate_counts = tier_candidates.groupby("race_key", dropna=False).size().rename("race_tier_rows")
    race_counts = pd.concat([total_rows_by_race, candidate_counts], axis=1).fillna(0)
    race_counts["race_total_rows"] = pd.to_numeric(race_counts["race_total_rows"], errors="coerce").fillna(0).astype(int)
    race_counts["race_tier_rows"] = pd.to_numeric(race_counts["race_tier_rows"], errors="coerce").fillna(0).astype(int)
    race_counts["complete_match_race_tier"] = race_counts["race_total_rows"] == race_counts["race_tier_rows"]
    complete_race_keys = set(race_counts.index[race_counts["complete_match_race_tier"]])

    tier = tier_candidates[tier_candidates["race_key"].isin(complete_race_keys)].copy()
    tier["tier_name"] = tier_name
    tier["tier_allowed_stages"] = ", ".join(sorted(allowed))
    tier["field_size"] = tier.groupby("race_key", dropna=False)["horse"].transform("count")
    tier["field_size"] = pd.to_numeric(tier["field_size"], errors="coerce")
    tier["field_size_bucket"] = tier["field_size"].map(field_size_bucket)
    tier["starts_bucket"] = tier["starts_found"].map(starts_bucket)
    tier["probability_bucket"] = tier["V6_1_RESEARCH_probability"].map(probability_bucket)
    tier["gap_bucket"] = tier["projection_gap_V6_1_RESEARCH"].map(gap_bucket)
    tier["tier_probability_rank"] = tier.groupby("race_key", dropna=False)["V6_1_RESEARCH_probability"].rank(
        method="first", ascending=False
    )
    tier["tier_probability_rank"] = pd.to_numeric(tier["tier_probability_rank"], errors="coerce").astype("Int64")
    tier["rank_bucket"] = tier["tier_probability_rank"].map(rank_bucket)
    tier["model_expected_win"] = tier["V6_1_RESEARCH_probability"]
    tier["calibration_error"] = tier["won"] - tier["V6_1_RESEARCH_probability"]
    tier["abs_calibration_error"] = tier["calibration_error"].abs()
    tier["brier_component"] = np.square(tier["V6_1_RESEARCH_probability"] - tier["won"])
    tier["ate_like_flag"] = "NO"
    tier["built_at"] = datetime.now(timezone.utc).isoformat()
    return tier


def build_ate_segment_for_tier(tier: pd.DataFrame, tier_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    negative_mask = tier["projection_band_V6_1_RESEARCH"].map(norm_text).str.contains("NEGATIVE", na=False)
    levels = [
        (
            0,
            "EXACT",
            (
                tier["class_bucket"].eq("MAIDEN")
                & tier["gap_bucket"].eq("NEG_6_TO_NEG_4")
                & negative_mask
                & tier["starts_bucket"].isin(["STARTS_1_2", "STARTS_3_5"])
                & tier["field_size_bucket"].eq("FIELD_7_8")
            ),
        ),
        (
            1,
            "RELAX_REMOVE_FIELD_SIZE",
            (
                tier["class_bucket"].eq("MAIDEN")
                & tier["gap_bucket"].eq("NEG_6_TO_NEG_4")
                & negative_mask
                & tier["starts_bucket"].isin(["STARTS_1_2", "STARTS_3_5"])
            ),
        ),
        (
            2,
            "RELAX_REMOVE_PROJECTION_BAND",
            (
                tier["class_bucket"].eq("MAIDEN")
                & tier["gap_bucket"].eq("NEG_6_TO_NEG_4")
                & tier["starts_bucket"].isin(["STARTS_1_2", "STARTS_3_5"])
            ),
        ),
        (
            3,
            "RELAX_REMOVE_STARTS_BUCKET",
            (
                tier["class_bucket"].eq("MAIDEN")
                & tier["gap_bucket"].eq("NEG_6_TO_NEG_4")
            ),
        ),
    ]

    records: list[dict[str, object]] = []
    chosen_level = ""
    chosen_mask = pd.Series(False, index=tier.index)

    for relaxation_level, level_name, mask in levels:
        subset = tier.loc[mask].copy()
        metrics = summarize_group(subset)
        metrics.update(
            {
                "tier_name": tier_name,
                "relaxation_level": relaxation_level,
                "ate_segment_level": level_name,
                "sample_floor_met": "YES" if len(subset) >= 20 else "NO",
            }
        )
        records.append(metrics)
        if chosen_level == "" and len(subset) >= 20:
            chosen_level = level_name
            chosen_mask = mask.copy()

    if chosen_level == "":
        chosen_level = levels[-1][1]
        chosen_mask = levels[-1][2].copy()

    ate_df = pd.DataFrame(records)
    ate_df["chosen_flag"] = ate_df["ate_segment_level"].eq(chosen_level).map(lambda value: "YES" if value else "NO")
    tier = tier.copy()
    tier.loc[chosen_mask, "ate_like_flag"] = "YES"
    return tier, ate_df


def build_probability_bucket_output(detail: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for tier_name in TIER_ORDER:
        tier = detail[detail["tier_name"] == tier_name].copy()
        for bucket in PROB_BUCKET_ORDER:
            subset = tier[tier["probability_bucket"] == bucket].copy()
            if subset.empty:
                continue
            metrics = summarize_group(subset)
            metrics.update({"tier_name": tier_name, "probability_bucket": bucket})
            records.append(metrics)
    result = pd.DataFrame(records)
    if result.empty:
        return result
    order_map = {value: idx for idx, value in enumerate(PROB_BUCKET_ORDER)}
    tier_map = {value: idx for idx, value in enumerate(TIER_ORDER)}
    result["_tier_order"] = result["tier_name"].map(lambda value: tier_map.get(value, 999))
    result["_bucket_order"] = result["probability_bucket"].map(lambda value: order_map.get(value, 999))
    result = result.sort_values(["_tier_order", "_bucket_order"]).drop(columns=["_tier_order", "_bucket_order"])
    return result.reset_index(drop=True)


def build_summary(detail: pd.DataFrame, ate_segments: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for tier_name in TIER_ORDER:
        tier = detail[detail["tier_name"] == tier_name].copy()
        if tier.empty:
            continue
        metrics = summarize_group(tier)

        rank1 = tier[tier["tier_probability_rank"] == 1].copy()
        rank1_expected = safe_pct(pd.to_numeric(rank1["V6_1_RESEARCH_probability"], errors="coerce").fillna(0.0).sum(), len(rank1))
        rank1_actual = safe_pct(pd.to_numeric(rank1["won"], errors="coerce").fillna(0.0).sum(), len(rank1))
        rank1_delta = None
        if rank1_expected is not None and rank1_actual is not None:
            rank1_delta = rank1_expected - rank1_actual

        ate_choice = ate_segments[(ate_segments["tier_name"] == tier_name) & (ate_segments["chosen_flag"] == "YES")].copy()
        ate_level = ""
        ate_rows = None
        ate_expected = None
        ate_actual = None
        ate_empirical_fair = None
        ate_sample_floor = ""
        if not ate_choice.empty:
            chosen = ate_choice.iloc[0]
            ate_level = clean(chosen.get("ate_segment_level"))
            ate_rows = to_int(chosen.get("rows"))
            ate_expected = to_float(chosen.get("expected_win_pct"))
            ate_actual = to_float(chosen.get("actual_win_pct"))
            ate_empirical_fair = to_float(chosen.get("empirical_fair_price"))
            ate_sample_floor = clean(chosen.get("sample_floor_met"))

        rows.append(
            {
                "status": "EDGEIQ_V6_1_PROBABILITY_CALIBRATION_V2_BY_MATCH_TIER_BUILT",
                "source": SRC_REPLAY.name,
                "tier_name": tier_name,
                "allowed_match_stages": ", ".join(sorted(TIER_ALLOWED_STAGES[tier_name])),
                "rows": metrics["rows"],
                "races": metrics["races"],
                "expected_wins": metrics["expected_wins"],
                "actual_wins": metrics["actual_wins"],
                "global_calibration_delta_pct": metrics["calibration_delta_pct"],
                "brier_score": metrics["brier_score"],
                "rank1_expected_win_pct": round_num(rank1_expected, 3),
                "rank1_actual_win_pct": round_num(rank1_actual, 3),
                "rank1_calibration_delta_pct": round_num(rank1_delta, 3),
                "ate_like_segment_level": ate_level,
                "ate_like_sample_floor_met": ate_sample_floor,
                "ate_like_segment_rows": ate_rows,
                "ate_like_expected_win_pct": round_num(ate_expected, 3),
                "ate_like_actual_win_pct": round_num(ate_actual, 3),
                "ate_like_empirical_fair": round_num(ate_empirical_fair, 3),
                "built_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    summary = pd.DataFrame(rows)
    if not summary.empty:
        summary["_tier_order"] = summary["tier_name"].map(lambda value: TIER_ORDER.index(value) if value in TIER_ORDER else 999)
        summary = summary.sort_values("_tier_order").drop(columns=["_tier_order"]).reset_index(drop=True)
    return summary


def main() -> None:
    base = build_base_enriched()

    all_tier_details: list[pd.DataFrame] = []
    all_ate_segments: list[pd.DataFrame] = []

    for tier_name in TIER_ORDER:
        tier = build_tier_detail(base, tier_name)
        tier, ate_df = build_ate_segment_for_tier(tier, tier_name)
        all_tier_details.append(tier)
        all_ate_segments.append(ate_df)

    detail = pd.concat(all_tier_details, ignore_index=True) if all_tier_details else pd.DataFrame()
    ate_segments = pd.concat(all_ate_segments, ignore_index=True) if all_ate_segments else pd.DataFrame()
    prob_buckets = build_probability_bucket_output(detail)
    summary = build_summary(detail, ate_segments)

    detail_out = detail[
        [
            "tier_name",
            "tier_allowed_stages",
            "race_key",
            "meeting_date",
            "track",
            "race_no",
            "horse",
            "horse_key",
            "source_match_stage_v2",
            "match_confidence_v2",
            "backtest_race_key",
            "race_class_raw",
            "race_name_backtest",
            "class_bucket",
            "field_size",
            "field_size_bucket",
            "starts_found",
            "starts_bucket",
            "projection_band_V6_1_RESEARCH",
            "projection_gap_V6_1_RESEARCH",
            "gap_bucket",
            "V6_1_RESEARCH_probability",
            "V6_1_RESEARCH_fair_price",
            "probability_bucket",
            "tier_probability_rank",
            "rank_bucket",
            "won",
            "placed",
            "finish_position",
            "sp",
            "model_expected_win",
            "calibration_error",
            "abs_calibration_error",
            "brier_component",
            "ate_like_flag",
            "built_at",
        ]
    ].copy()

    detail_out.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    prob_buckets.to_csv(OUT_PROB_BUCKETS, index=False)
    ate_segments.to_csv(OUT_ATE_SEGMENTS, index=False)

    print("[V6_1_PROBABILITY_CALIBRATION_V2_BY_MATCH_TIER] COMPLETE")
    if not summary.empty:
        print(summary.to_string(index=False))
        print("")
    if not ate_segments.empty:
        print("ATE SEGMENTS")
        print(ate_segments.to_string(index=False))
        print("")
    if not prob_buckets.empty:
        print("PROBABILITY BUCKETS")
        print(prob_buckets.to_string(index=False))


if __name__ == "__main__":
    main()
