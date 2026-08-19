from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_v6_1_settled_gap_replay_v1.csv"

OUT_DETAIL = DATA / "edgeiq_v6_1_probability_calibration_replay_v1_detail.csv"
OUT_PROB_BUCKETS = DATA / "edgeiq_v6_1_probability_calibration_replay_v1_probability_buckets.csv"
OUT_GAP_BUCKETS = DATA / "edgeiq_v6_1_probability_calibration_replay_v1_gap_buckets.csv"
OUT_RANK_BUCKETS = DATA / "edgeiq_v6_1_probability_calibration_replay_v1_rank_buckets.csv"
OUT_SUMMARY = DATA / "edgeiq_v6_1_probability_calibration_replay_v1_summary.csv"

SOURCE_FILE_NAME = SRC.name

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

RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_6", "RANK_7_PLUS"]
PROB_BUCKET_ORDER = [label for _, _, label in PROBABILITY_BUCKETS]
GAP_BUCKET_ORDER = [label for _, _, label in GAP_BUCKETS]

ATE_IRON_GAP_TEST = -5.66
ATE_IRON_EXPECTED_FROM_LIVE = 10.6
TRIUMVIRATE_GAP_TEST = 8.92
TRIUMVIRATE_EXPECTED_FROM_LIVE = 22.15


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def first_existing(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


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


def safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return (float(numerator) / float(denominator)) * 100.0


def round_num(value: float | None, places: int = 3) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return round(float(value), places)


def fair_from_probability(probability: float | None) -> float | None:
    if probability is None or not math.isfinite(probability) or probability <= 0:
        return None
    return 1.0 / probability


def fair_from_pct(win_pct: float | None) -> float | None:
    if win_pct is None or not math.isfinite(win_pct) or win_pct <= 0:
        return None
    return 100.0 / win_pct


def brier_from_arrays(probabilities: pd.Series, outcomes: pd.Series) -> float | None:
    if len(probabilities) == 0:
        return None
    probs = pd.to_numeric(probabilities, errors="coerce").fillna(0.0).astype(float)
    wins = pd.to_numeric(outcomes, errors="coerce").fillna(0.0).astype(float)
    return float(np.mean(np.square(probs - wins)))


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def build_detail() -> pd.DataFrame:
    df = load_required_csv(SRC)
    columns = list(df.columns)

    race_col = first_existing(columns, ["race_key"])
    date_col = first_existing(columns, ["meeting_date", "race_date"])
    track_col = first_existing(columns, ["track"])
    race_no_col = first_existing(columns, ["race_no"])
    horse_col = first_existing(columns, ["horse"])
    horse_key_col = first_existing(columns, ["horse_key"])
    won_col = first_existing(columns, ["won"])
    placed_col = first_existing(columns, ["placed"])
    finish_col = first_existing(columns, ["finish_position"])
    sp_col = first_existing(columns, ["sp_num_settled", "sp_settled", "sp"])
    gap_col = first_existing(columns, ["projection_gap_V6_1_RESEARCH"])
    rating_col = first_existing(columns, ["projected_rating_V6_1_RESEARCH"])
    band_col = first_existing(columns, ["projection_band_V6_1_RESEARCH"])
    prob_col = first_existing(columns, ["V6_1_RESEARCH_probability"])
    fair_col = first_existing(columns, ["V6_1_RESEARCH_fair_price"])
    price_rank_col = first_existing(columns, ["V6_1_RESEARCH_price_rank"])

    missing = []
    for label, col in [
        ("race_key", race_col),
        ("meeting_date/race_date", date_col),
        ("track", track_col),
        ("race_no", race_no_col),
        ("horse", horse_col),
        ("horse_key", horse_key_col),
        ("won", won_col),
        ("finish_position", finish_col),
        ("projection_gap_V6_1_RESEARCH", gap_col),
        ("projected_rating_V6_1_RESEARCH", rating_col),
        ("projection_band_V6_1_RESEARCH", band_col),
        ("V6_1_RESEARCH_probability", prob_col),
        ("V6_1_RESEARCH_fair_price", fair_col),
    ]:
        if col is None:
            missing.append(label)

    if missing:
        raise RuntimeError(f"Missing required columns: {missing}. Available columns: {columns}")

    detail = pd.DataFrame()
    detail["race_key"] = df[race_col].map(clean)
    detail["meeting_date"] = df[date_col].map(clean).str[:10]
    detail["track"] = df[track_col].map(clean)
    detail["race_no"] = df[race_no_col].map(clean)
    detail["horse"] = df[horse_col].map(clean)
    detail["horse_key"] = df[horse_key_col].map(clean)
    detail["projection_gap_V6_1_RESEARCH"] = df[gap_col].map(to_float)
    detail["projected_rating_V6_1_RESEARCH"] = df[rating_col].map(to_float)
    detail["projection_band_V6_1_RESEARCH"] = df[band_col].map(clean)
    detail["V6_1_RESEARCH_probability"] = df[prob_col].map(to_float)
    detail["V6_1_RESEARCH_fair_price"] = df[fair_col].map(to_float)
    if price_rank_col:
        detail["V6_1_RESEARCH_price_rank"] = pd.to_numeric(df[price_rank_col], errors="coerce")
    else:
        detail["V6_1_RESEARCH_price_rank"] = np.nan
    detail["won"] = pd.to_numeric(df[won_col], errors="coerce").fillna(0).astype(int)
    if placed_col:
        detail["placed"] = pd.to_numeric(df[placed_col], errors="coerce").fillna(0).astype(int)
    else:
        finish_temp = pd.to_numeric(df[finish_col], errors="coerce")
        detail["placed"] = ((finish_temp >= 1) & (finish_temp <= 3)).astype(int)
    detail["finish_position"] = pd.to_numeric(df[finish_col], errors="coerce")
    detail["sp"] = df[sp_col].map(to_float) if sp_col else np.nan

    if "source_match_status" in df.columns:
        detail["source_match_status"] = df["source_match_status"].map(clean)
    else:
        detail["source_match_status"] = ""

    race_source_counts = (
        detail.groupby("race_key", dropna=False)
        .agg(race_total_rows_in_source=("horse", "count"))
        .reset_index()
    )

    detail = detail[
        detail["projection_gap_V6_1_RESEARCH"].notna()
        & detail["V6_1_RESEARCH_probability"].notna()
        & detail["V6_1_RESEARCH_fair_price"].notna()
    ].copy()

    matched_counts = (
        detail.groupby("race_key", dropna=False)
        .agg(race_matched_rows_in_source=("horse", "count"))
        .reset_index()
    )
    race_counts = race_source_counts.merge(matched_counts, on="race_key", how="left")
    race_counts["race_matched_rows_in_source"] = pd.to_numeric(race_counts["race_matched_rows_in_source"], errors="coerce").fillna(0).astype(int)
    race_counts["complete_match_race_v1"] = race_counts["race_total_rows_in_source"] == race_counts["race_matched_rows_in_source"]
    complete_race_keys = set(race_counts.loc[race_counts["complete_match_race_v1"], "race_key"])
    detail = detail[detail["race_key"].isin(complete_race_keys)].copy()

    detail["V6_1_RESEARCH_probability_pct"] = detail["V6_1_RESEARCH_probability"] * 100.0
    detail["calculated_probability_rank"] = (
        detail.groupby("race_key", dropna=False)["V6_1_RESEARCH_probability"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    detail["final_probability_rank_used"] = detail["V6_1_RESEARCH_price_rank"].where(
        detail["V6_1_RESEARCH_price_rank"].notna(),
        detail["calculated_probability_rank"],
    )
    detail["final_probability_rank_used"] = pd.to_numeric(detail["final_probability_rank_used"], errors="coerce").astype(int)
    detail["probability_bucket"] = detail["V6_1_RESEARCH_probability"].apply(probability_bucket)
    detail["gap_bucket"] = detail["projection_gap_V6_1_RESEARCH"].apply(gap_bucket)
    detail["rank_bucket"] = detail["final_probability_rank_used"].apply(rank_bucket)
    detail["model_expected_win"] = detail["V6_1_RESEARCH_probability"]
    detail["calibration_error"] = detail["won"] - detail["V6_1_RESEARCH_probability"]
    detail["abs_calibration_error"] = detail["calibration_error"].abs()
    detail["brier_component"] = np.square(detail["won"] - detail["V6_1_RESEARCH_probability"])
    detail["overlay_pct_vs_sp"] = np.where(
        detail["sp"].notna() & detail["V6_1_RESEARCH_fair_price"].notna() & (detail["V6_1_RESEARCH_fair_price"] > 0),
        ((detail["sp"] / detail["V6_1_RESEARCH_fair_price"]) - 1.0) * 100.0,
        np.nan,
    )
    detail["source_file"] = SOURCE_FILE_NAME
    detail["built_at"] = datetime.now(timezone.utc).isoformat()

    for column in [
        "projection_gap_V6_1_RESEARCH",
        "projected_rating_V6_1_RESEARCH",
        "V6_1_RESEARCH_probability",
        "V6_1_RESEARCH_probability_pct",
        "V6_1_RESEARCH_fair_price",
        "model_expected_win",
        "calibration_error",
        "abs_calibration_error",
        "brier_component",
        "overlay_pct_vs_sp",
    ]:
        detail[column] = pd.to_numeric(detail[column], errors="coerce")

    return detail[
        [
            "race_key",
            "meeting_date",
            "track",
            "race_no",
            "horse",
            "horse_key",
            "projection_gap_V6_1_RESEARCH",
            "projected_rating_V6_1_RESEARCH",
            "projection_band_V6_1_RESEARCH",
            "V6_1_RESEARCH_probability",
            "V6_1_RESEARCH_probability_pct",
            "V6_1_RESEARCH_fair_price",
            "V6_1_RESEARCH_price_rank",
            "calculated_probability_rank",
            "final_probability_rank_used",
            "probability_bucket",
            "gap_bucket",
            "rank_bucket",
            "won",
            "placed",
            "finish_position",
            "sp",
            "model_expected_win",
            "calibration_error",
            "abs_calibration_error",
            "brier_component",
            "overlay_pct_vs_sp",
            "source_file",
            "built_at",
        ]
    ].copy()


def build_probability_bucket_table(detail: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        detail.groupby("probability_bucket", dropna=False)
        .agg(
            rows=("horse", "count"),
            races=("race_key", "nunique"),
            expected_wins=("model_expected_win", "sum"),
            actual_wins=("won", "sum"),
            avg_probability=("V6_1_RESEARCH_probability", "mean"),
            avg_model_fair_price=("V6_1_RESEARCH_fair_price", "mean"),
            avg_sp=("sp", "mean"),
            median_sp=("sp", "median"),
            brier_score=("brier_component", "mean"),
        )
        .reset_index()
    )
    grouped["expected_win_pct"] = grouped.apply(lambda row: safe_pct(row["expected_wins"], row["rows"]), axis=1)
    grouped["actual_win_pct"] = grouped.apply(lambda row: safe_pct(row["actual_wins"], row["rows"]), axis=1)
    grouped["calibration_delta_pct"] = grouped["expected_win_pct"] - grouped["actual_win_pct"]
    grouped["expected_fair_price"] = grouped["expected_win_pct"].apply(fair_from_pct)
    grouped["empirical_fair_price"] = grouped["actual_win_pct"].apply(fair_from_pct)

    grouped["probability_bucket"] = pd.Categorical(grouped["probability_bucket"], categories=PROB_BUCKET_ORDER, ordered=True)
    grouped = grouped.sort_values("probability_bucket").reset_index(drop=True)
    grouped["probability_bucket"] = grouped["probability_bucket"].astype(str)

    for column in [
        "expected_wins",
        "expected_win_pct",
        "actual_win_pct",
        "calibration_delta_pct",
        "expected_fair_price",
        "empirical_fair_price",
        "brier_score",
        "avg_probability",
        "avg_model_fair_price",
        "avg_sp",
        "median_sp",
    ]:
        grouped[column] = grouped[column].apply(round_num)

    return grouped[
        [
            "probability_bucket",
            "rows",
            "races",
            "expected_wins",
            "actual_wins",
            "expected_win_pct",
            "actual_win_pct",
            "calibration_delta_pct",
            "expected_fair_price",
            "empirical_fair_price",
            "brier_score",
            "avg_probability",
            "avg_model_fair_price",
            "avg_sp",
            "median_sp",
        ]
    ].copy()


def build_gap_bucket_table(detail: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        detail.groupby("gap_bucket", dropna=False)
        .agg(
            rows=("horse", "count"),
            races=("race_key", "nunique"),
            expected_wins=("model_expected_win", "sum"),
            actual_wins=("won", "sum"),
            avg_gap=("projection_gap_V6_1_RESEARCH", "mean"),
            avg_probability=("V6_1_RESEARCH_probability", "mean"),
            avg_model_fair_price=("V6_1_RESEARCH_fair_price", "mean"),
            brier_score=("brier_component", "mean"),
        )
        .reset_index()
    )
    grouped["expected_win_pct"] = grouped.apply(lambda row: safe_pct(row["expected_wins"], row["rows"]), axis=1)
    grouped["actual_win_pct"] = grouped.apply(lambda row: safe_pct(row["actual_wins"], row["rows"]), axis=1)
    grouped["calibration_delta_pct"] = grouped["expected_win_pct"] - grouped["actual_win_pct"]
    grouped["empirical_fair_price"] = grouped["actual_win_pct"].apply(fair_from_pct)

    grouped["gap_bucket"] = pd.Categorical(grouped["gap_bucket"], categories=GAP_BUCKET_ORDER, ordered=True)
    grouped = grouped.sort_values("gap_bucket").reset_index(drop=True)
    grouped["gap_bucket"] = grouped["gap_bucket"].astype(str)

    for column in [
        "expected_wins",
        "expected_win_pct",
        "actual_win_pct",
        "calibration_delta_pct",
        "avg_gap",
        "avg_probability",
        "avg_model_fair_price",
        "empirical_fair_price",
        "brier_score",
    ]:
        grouped[column] = grouped[column].apply(round_num)

    return grouped[
        [
            "gap_bucket",
            "rows",
            "races",
            "expected_wins",
            "actual_wins",
            "expected_win_pct",
            "actual_win_pct",
            "calibration_delta_pct",
            "avg_gap",
            "avg_probability",
            "avg_model_fair_price",
            "empirical_fair_price",
            "brier_score",
        ]
    ].copy()


def build_rank_bucket_table(detail: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        detail.groupby("rank_bucket", dropna=False)
        .agg(
            rows=("horse", "count"),
            races=("race_key", "nunique"),
            expected_wins=("model_expected_win", "sum"),
            actual_wins=("won", "sum"),
            avg_probability=("V6_1_RESEARCH_probability", "mean"),
            avg_model_fair_price=("V6_1_RESEARCH_fair_price", "mean"),
            brier_score=("brier_component", "mean"),
        )
        .reset_index()
    )
    grouped["expected_win_pct"] = grouped.apply(lambda row: safe_pct(row["expected_wins"], row["rows"]), axis=1)
    grouped["actual_win_pct"] = grouped.apply(lambda row: safe_pct(row["actual_wins"], row["rows"]), axis=1)
    grouped["calibration_delta_pct"] = grouped["expected_win_pct"] - grouped["actual_win_pct"]
    grouped["empirical_fair_price"] = grouped["actual_win_pct"].apply(fair_from_pct)

    grouped["rank_bucket"] = pd.Categorical(grouped["rank_bucket"], categories=RANK_BUCKET_ORDER, ordered=True)
    grouped = grouped.sort_values("rank_bucket").reset_index(drop=True)
    grouped["rank_bucket"] = grouped["rank_bucket"].astype(str)

    for column in [
        "expected_wins",
        "expected_win_pct",
        "actual_win_pct",
        "calibration_delta_pct",
        "avg_probability",
        "avg_model_fair_price",
        "empirical_fair_price",
        "brier_score",
    ]:
        grouped[column] = grouped[column].apply(round_num)

    return grouped[
        [
            "rank_bucket",
            "rows",
            "races",
            "expected_wins",
            "actual_wins",
            "expected_win_pct",
            "actual_win_pct",
            "calibration_delta_pct",
            "avg_probability",
            "avg_model_fair_price",
            "empirical_fair_price",
            "brier_score",
        ]
    ].copy()


def lookup_bucket_row(frame: pd.DataFrame, bucket_col: str, bucket_value: str) -> pd.Series | None:
    match = frame[frame[bucket_col] == bucket_value]
    if match.empty:
        return None
    return match.iloc[0]


def build_summary(detail: pd.DataFrame, prob_buckets: pd.DataFrame, gap_buckets: pd.DataFrame) -> pd.DataFrame:
    rows_used = int(len(detail))
    races_used = int(detail["race_key"].nunique())
    expected_total_wins = float(detail["model_expected_win"].sum())
    actual_total_wins = int(detail["won"].sum())
    brier_score = brier_from_arrays(detail["V6_1_RESEARCH_probability"], detail["won"])

    prob_weighted_abs = 0.0
    for row in prob_buckets.to_dict("records"):
        bucket_rows = int(row["rows"])
        if bucket_rows <= 0:
            continue
        delta = row.get("calibration_delta_pct")
        if delta is None or (isinstance(delta, float) and math.isnan(delta)):
            continue
        prob_weighted_abs += abs(float(delta)) * (bucket_rows / rows_used)

    rank1 = detail[detail["final_probability_rank_used"] == 1].copy()
    rank1_expected_win_pct = safe_pct(rank1["model_expected_win"].sum(), len(rank1))
    rank1_actual_win_pct = safe_pct(rank1["won"].sum(), len(rank1))
    rank1_delta = (rank1_expected_win_pct or 0.0) - (rank1_actual_win_pct or 0.0)
    rank1_avg_fair_price = pd.to_numeric(rank1["V6_1_RESEARCH_fair_price"], errors="coerce").mean() if len(rank1) else None

    ate_bucket_label = gap_bucket(ATE_IRON_GAP_TEST)
    ate_bucket_row = lookup_bucket_row(gap_buckets, "gap_bucket", ate_bucket_label)
    tri_bucket_label = gap_bucket(TRIUMVIRATE_GAP_TEST)
    tri_bucket_row = lookup_bucket_row(gap_buckets, "gap_bucket", tri_bucket_label)

    top_prob_buckets = prob_buckets[prob_buckets["probability_bucket"].isin(["20_25", "25_30", "30_40", "40_PLUS"])].copy()
    low_prob_buckets = prob_buckets[prob_buckets["probability_bucket"].isin(["00_05", "05_10", "10_15"])].copy()
    top_overstated = (
        top_prob_buckets["calibration_delta_pct"].dropna().gt(0).all()
        if not top_prob_buckets.empty else False
    )
    low_understated = (
        low_prob_buckets["calibration_delta_pct"].dropna().lt(0).all()
        if not low_prob_buckets.empty else False
    )

    if rank1_delta > 3.0:
        verdict = "PROBABILITY_TOO_AGGRESSIVE_AT_TOP"
    elif abs(expected_total_wins - actual_total_wins) <= max(3.0, races_used * 0.01) and top_overstated and low_understated:
        verdict = "PROBABILITY_DISTRIBUTION_TOO_SHARP"
    else:
        verdict = "PROBABILITY_CALIBRATION_ACCEPTABLE_ON_MATCHED_SUBSET"

    summary = pd.DataFrame(
        [
            {
                "status": "EDGEIQ_V6_1_PROBABILITY_CALIBRATION_REPLAY_V1_BUILT",
                "source": SRC.name,
                "rows_used": rows_used,
                "races_used": races_used,
                "race_scope": "COMPLETE_MATCHED_RACES_ONLY",
                "expected_total_wins": round_num(expected_total_wins),
                "actual_total_wins": actual_total_wins,
                "total_expected_vs_actual_delta": round_num(expected_total_wins - actual_total_wins),
                "brier_score": round_num(brier_score, 6),
                "weighted_abs_calibration_delta_pct": round_num(prob_weighted_abs),
                "rank1_rows": int(len(rank1)),
                "rank1_expected_win_pct": round_num(rank1_expected_win_pct),
                "rank1_actual_win_pct": round_num(rank1_actual_win_pct),
                "rank1_calibration_delta_pct": round_num(rank1_delta),
                "rank1_avg_fair_price": round_num(rank1_avg_fair_price),
                "ate_iron_gap_test": ATE_IRON_GAP_TEST,
                "ate_iron_expected_from_live": ATE_IRON_EXPECTED_FROM_LIVE,
                "ate_iron_empirical_gap_bucket_win_pct": round_num(float(ate_bucket_row["actual_win_pct"])) if ate_bucket_row is not None and pd.notna(ate_bucket_row["actual_win_pct"]) else None,
                "ate_iron_empirical_gap_bucket_fair": round_num(float(ate_bucket_row["empirical_fair_price"])) if ate_bucket_row is not None and pd.notna(ate_bucket_row["empirical_fair_price"]) else None,
                "triumvirate_gap_test": TRIUMVIRATE_GAP_TEST,
                "triumvirate_expected_from_live": TRIUMVIRATE_EXPECTED_FROM_LIVE,
                "triumvirate_empirical_gap_bucket_win_pct": round_num(float(tri_bucket_row["actual_win_pct"])) if tri_bucket_row is not None and pd.notna(tri_bucket_row["actual_win_pct"]) else None,
                "triumvirate_empirical_gap_bucket_fair": round_num(float(tri_bucket_row["empirical_fair_price"])) if tri_bucket_row is not None and pd.notna(tri_bucket_row["empirical_fair_price"]) else None,
                "verdict": verdict,
                "built_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )
    return summary


def print_section(title: str, frame: pd.DataFrame) -> None:
    print("")
    print(title)
    if frame.empty:
        print("(no rows)")
        return
    print(frame.to_string(index=False))


def main() -> None:
    detail = build_detail()
    prob_buckets = build_probability_bucket_table(detail)
    gap_buckets = build_gap_bucket_table(detail)
    rank_buckets = build_rank_bucket_table(detail)
    summary = build_summary(detail, prob_buckets, gap_buckets)

    detail.to_csv(OUT_DETAIL, index=False)
    prob_buckets.to_csv(OUT_PROB_BUCKETS, index=False)
    gap_buckets.to_csv(OUT_GAP_BUCKETS, index=False)
    rank_buckets.to_csv(OUT_RANK_BUCKETS, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    print("[V6_1_PROBABILITY_CALIBRATION_REPLAY_V1] COMPLETE")
    print_section("SUMMARY", summary)
    print_section("PROBABILITY BUCKETS", prob_buckets)
    print_section("GAP BUCKETS", gap_buckets)
    print_section("RANK BUCKETS", rank_buckets)


if __name__ == "__main__":
    main()
