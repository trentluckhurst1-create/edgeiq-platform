from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
import math
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC_EXPANDED = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded.csv"
SRC_SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"
SRC_BACKTEST = DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv"

OUT_ARCHETYPES = DATA / "edgeiq_v6_1_overconfidence_archetypes_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_v6_1_overconfidence_archetypes_v1_summary.csv"
OUT_RANKED = DATA / "edgeiq_v6_1_overconfidence_archetypes_v1_ranked.csv"

SOURCE_NAME = SRC_EXPANDED.name
BACKTEST_MODEL = "V6_1_RESEARCH_PRIOR"
MIN_ROWS_BASE = 25
SAMPLE_THRESHOLDS = [25, 50, 100]

PROBABILITY_BUCKET_ORDER = ["00_05", "05_10", "10_15", "15_20", "20_25", "25_30", "30_40", "40_PLUS", "UNKNOWN"]
FIELD_SIZE_BUCKET_ORDER = ["FIELD_1_6", "FIELD_7_8", "FIELD_9_10", "FIELD_11_12", "FIELD_13_PLUS", "FIELD_UNKNOWN"]
STARTS_BUCKET_ORDER = ["STARTS_0", "STARTS_1_2", "STARTS_3_5", "STARTS_6_10", "STARTS_11_PLUS", "STARTS_UNKNOWN"]
CLASS_BUCKET_ORDER = ["MAIDEN", "BM", "OPEN", "GROUP_LISTED", "2YO", "3YO", "UNKNOWN"]
DISTANCE_BUCKET_ORDER = ["LT_1200", "DIST_1200_1399", "DIST_1400_1599", "DIST_1600_1999", "DIST_2000_PLUS", "UNKNOWN"]
CONDITION_GROUP_ORDER = ["GOOD", "SOFT", "HEAVY", "SYNTHETIC", "UNKNOWN"]
PRICE_RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_6", "RANK_7_PLUS", "UNKNOWN"]
PROJECTION_BAND_ORDER = ["ELITE", "POSITIVE", "NEUTRAL", "NEGATIVE", "POOR", "UNKNOWN"]

DIMENSION_COLUMNS = [
    "projection_band_V6_1_RESEARCH",
    "starts_bucket_v1",
    "field_size_bucket_v1",
    "class_bucket_v1",
    "distance_bucket_v1",
    "condition_group_v1",
    "price_rank_bucket_v1",
    "probability_bucket_v1",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


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


def normalise_track(value: object) -> str:
    text = upper(value)
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_horse_key(value: object) -> str:
    text = upper(value)
    text = re.sub(r"\(.*?\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def probability_bucket(probability: float | None) -> str:
    if probability is None or (isinstance(probability, float) and math.isnan(probability)):
        return "UNKNOWN"
    if probability < 0.05:
        return "00_05"
    if probability < 0.10:
        return "05_10"
    if probability < 0.15:
        return "10_15"
    if probability < 0.20:
        return "15_20"
    if probability < 0.25:
        return "20_25"
    if probability < 0.30:
        return "25_30"
    if probability < 0.40:
        return "30_40"
    return "40_PLUS"


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


def distance_bucket(distance_value: int | float | None) -> str:
    if distance_value is None or (isinstance(distance_value, float) and math.isnan(distance_value)):
        return "UNKNOWN"
    distance_num = float(distance_value)
    if distance_num < 1200:
        return "LT_1200"
    if distance_num < 1400:
        return "DIST_1200_1399"
    if distance_num < 1600:
        return "DIST_1400_1599"
    if distance_num < 2000:
        return "DIST_1600_1999"
    return "DIST_2000_PLUS"


def price_rank_bucket(rank_value: int | float | None) -> str:
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


def projection_band(value: object) -> str:
    text = upper(value)
    return text if text != "" else "UNKNOWN"


def is_condition_token(value: object) -> bool:
    text = upper(value).replace(" ", "")
    if text == "":
        return False
    patterns = [
        r"^GOOD\d*$",
        r"^SOFT\d*$",
        r"^HEAVY\d*$",
        r"^SYNTHETIC$",
        r"^SYN$",
        r"^FIRM\d*$",
        r"^SLOW\d*$",
        r"^YIELDING\d*$",
    ]
    return any(re.match(pattern, text) for pattern in patterns)


def condition_group(value: object) -> str:
    text = upper(value).replace(" ", "")
    if text == "":
        return "UNKNOWN"
    if "SYN" in text:
        return "SYNTHETIC"
    if text.startswith("GOOD") or text.startswith("FIRM"):
        return "GOOD"
    if text.startswith("SOFT") or text.startswith("SLOW"):
        return "SOFT"
    if text.startswith("HEAVY") or text.startswith("YIELDING"):
        return "HEAVY"
    return "UNKNOWN"


def class_bucket_from_text(race_class_raw: object, race_name: object) -> str:
    raw = upper(race_class_raw)
    name = upper(race_name)
    combined = f"{raw} {name}".strip()

    if re.search(r"\bGROUP\s*[123]\b|\bG[123]\b|\bLISTED\b|\bLR\b", combined):
        return "GROUP_LISTED"
    if re.search(r"\bMAIDEN\b|\bMDN\b", combined):
        return "MAIDEN"
    if re.search(r"\b2YO\b|\b2Y\b|\bTWO YEAR OLD\b", combined):
        return "2YO"
    if re.search(r"\b3YO\b|\b3Y\b|\bTHREE YEAR OLD\b", combined):
        return "3YO"
    if re.search(r"\bBM\s*\d+\b|\bBENCHMARK\b|\b0\s*-\s*\d+\b|\bCLASS\s*\d+\b|\bCL\s*\d+\b", combined):
        return "BM"
    if re.search(r"\bHANDICAP\b|\bHCP\b|\bOPEN\b|\bPLATE\b|\bSET WEIGHTS\b|\bWFA\b|\bWEIGHT FOR AGE\b|\bVOBIS\b", combined):
        return "OPEN"
    if raw != "":
        return "OPEN"
    return "UNKNOWN"


def fair_from_pct(win_pct: float | None) -> float | None:
    if win_pct is None or not math.isfinite(win_pct) or win_pct <= 0:
        return None
    return 100.0 / float(win_pct)


def safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return (float(numerator) / float(denominator)) * 100.0


def parse_race_key_tail(backtest_race_key: object) -> tuple[str, str]:
    parts = clean(backtest_race_key).split("|")
    if len(parts) <= 3:
        return "", ""
    tail = [clean(part) for part in parts[3:]]
    condition_raw = ""
    class_raw = ""
    condition_index = None
    for idx in range(len(tail) - 1, -1, -1):
        if is_condition_token(tail[idx]):
            condition_index = idx
            condition_raw = tail[idx]
            break
    if condition_index is not None and condition_index - 1 >= 0:
        class_raw = tail[condition_index - 1]
    elif len(tail) >= 2:
        class_raw = tail[-2]
    elif len(tail) == 1:
        class_raw = tail[0]
    return class_raw, condition_raw


def build_clean_detail() -> tuple[pd.DataFrame, dict[str, object]]:
    expanded = load_required_csv(SRC_EXPANDED)
    settled = load_required_csv(SRC_SETTLED)
    backtest = load_required_csv(SRC_BACKTEST)
    backtest = backtest[backtest["model"].map(upper).eq(BACKTEST_MODEL)].copy()

    if backtest.empty:
        raise RuntimeError(f"No backtest rows found for model={BACKTEST_MODEL}")

    detail = expanded.copy()
    detail["meeting_date"] = detail["meeting_date"].map(clean).str[:10]
    detail["race_key"] = detail["race_key"].map(clean)
    detail["track"] = detail["track"].map(clean)
    detail["race_no"] = detail["race_no"].map(clean)
    detail["horse"] = detail["horse"].map(clean)
    detail["horse_key"] = detail["horse_key"].map(normalise_horse_key)
    detail["backtest_race_key"] = detail["backtest_race_key"].map(clean)
    detail["complete_match_race_v2"] = detail["complete_match_race_v2"].map(upper)
    detail["V6_1_RESEARCH_probability"] = detail["V6_1_RESEARCH_probability"].map(to_float)
    detail["V6_1_RESEARCH_fair_price"] = detail["V6_1_RESEARCH_fair_price"].map(to_float)
    detail["projection_gap_V6_1_RESEARCH"] = detail["projection_gap_V6_1_RESEARCH"].map(to_float)
    detail["projection_band_V6_1_RESEARCH"] = detail["projection_band_V6_1_RESEARCH"].map(projection_band)
    detail["won"] = pd.to_numeric(detail["won"], errors="coerce").fillna(0).astype(int)
    detail["placed"] = pd.to_numeric(detail["placed"], errors="coerce").fillna(0).astype(int)
    detail["finish_position"] = pd.to_numeric(detail["finish_position"], errors="coerce")
    detail["sp"] = detail["sp"].map(to_float)

    base_rows = int(len(detail))
    detail = detail[
        detail["complete_match_race_v2"].eq("TRUE")
        & detail["backtest_race_key"].ne("")
        & detail["V6_1_RESEARCH_probability"].notna()
        & detail["V6_1_RESEARCH_fair_price"].notna()
    ].copy()
    matched_rows = int(len(detail))

    backtest["horse_key_v1"] = backtest["horse"].map(normalise_horse_key)
    backtest["backtest_race_key"] = backtest["race_key"].map(clean)
    backtest["backtest_join_key_v1"] = backtest["backtest_race_key"] + "|" + backtest["horse_key_v1"]
    backtest = backtest.sort_values(["backtest_race_key", "horse"]).drop_duplicates(
        subset=["backtest_join_key_v1"],
        keep="first",
    )
    backtest["distance_v1"] = backtest["distance"].map(to_float)
    backtest["prior_starts_v1"] = backtest["prior_starts"].map(to_int)
    parsed = backtest["backtest_race_key"].map(parse_race_key_tail)
    backtest["race_class_raw_v1"] = parsed.map(lambda value: value[0])
    backtest["condition_raw_v1"] = parsed.map(lambda value: value[1])
    backtest_subset = backtest[
        [
            "backtest_join_key_v1",
            "race_name",
            "distance_v1",
            "field_size",
            "prior_starts_v1",
            "race_class_raw_v1",
            "condition_raw_v1",
        ]
    ].copy()
    backtest_subset["field_size_backtest_v1"] = backtest_subset["field_size"].map(to_int)
    backtest_subset = backtest_subset.drop(columns=["field_size"])

    settled["settled_join_key_v1"] = settled["race_key"].map(clean) + "|" + settled["horse_key"].map(normalise_horse_key)
    settled_subset = settled[["settled_join_key_v1", "starts_before"]].copy()
    settled_subset["starts_before_v1"] = settled_subset["starts_before"].map(to_int)
    settled_subset = settled_subset.drop(columns=["starts_before"])

    detail["settled_join_key_v1"] = detail["race_key"] + "|" + detail["horse_key"]
    detail["backtest_join_key_v1"] = detail["backtest_race_key"] + "|" + detail["horse_key"]

    detail = detail.merge(settled_subset, on="settled_join_key_v1", how="left")
    detail = detail.merge(backtest_subset, on="backtest_join_key_v1", how="left")

    duplicate_backtest = (
        detail.groupby("backtest_race_key", dropna=False)
        .agg(distinct_settled_races_v1=("race_key", pd.Series.nunique))
        .reset_index()
    )
    duplicate_keys = set(
        duplicate_backtest[duplicate_backtest["distinct_settled_races_v1"].gt(1)]["backtest_race_key"].tolist()
    )
    duplicate_rows_excluded = int(detail[detail["backtest_race_key"].isin(duplicate_keys)].shape[0])
    duplicate_races_excluded = int(len(duplicate_keys))

    detail = detail[~detail["backtest_race_key"].isin(duplicate_keys)].copy()

    detail["race_row_count_v1"] = detail.groupby("backtest_race_key", dropna=False)["horse"].transform("count")
    detail["field_size_v1"] = detail["race_row_count_v1"].map(to_int)
    detail["starts_found_v1"] = detail["starts_before_v1"]
    detail["starts_found_v1"] = detail["starts_found_v1"].fillna(detail["prior_starts_v1"])

    detail["field_size_bucket_v1"] = detail["field_size_v1"].map(field_size_bucket)
    detail["starts_bucket_v1"] = detail["starts_found_v1"].map(starts_bucket)
    detail["distance_bucket_v1"] = detail["distance_v1"].map(distance_bucket)
    detail["class_bucket_v1"] = detail.apply(
        lambda row: class_bucket_from_text(row.get("race_class_raw_v1", ""), row.get("race_name", "")),
        axis=1,
    )
    detail["condition_group_v1"] = detail["condition_raw_v1"].map(condition_group)
    detail["probability_bucket_v1"] = detail["V6_1_RESEARCH_probability"].map(probability_bucket)

    detail = detail.sort_values(
        ["backtest_race_key", "V6_1_RESEARCH_probability", "horse_key"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    detail["price_rank_v1"] = detail.groupby("backtest_race_key", dropna=False).cumcount() + 1
    detail["price_rank_bucket_v1"] = detail["price_rank_v1"].map(price_rank_bucket)

    detail["expected_win_v1"] = detail["V6_1_RESEARCH_probability"]
    detail["actual_win_v1"] = detail["won"].astype(float)
    detail["calibration_error_v1"] = detail["expected_win_v1"] - detail["actual_win_v1"]
    detail["sp_valid_v1"] = detail["sp"].map(lambda value: "YES" if value is not None and value > 0 else "NO")
    detail["profit_1u_v1"] = detail.apply(
        lambda row: (float(row["sp"]) - 1.0) if row["sp_valid_v1"] == "YES" and int(row["won"]) == 1 else (-1.0 if row["sp_valid_v1"] == "YES" else None),
        axis=1,
    )
    detail["built_at_v1"] = datetime.now(timezone.utc).isoformat()

    metrics = {
        "source_rows_v1": base_rows,
        "complete_matched_probability_rows_v1": matched_rows,
        "duplicate_backtest_rows_excluded_v1": duplicate_rows_excluded,
        "duplicate_backtest_races_excluded_v1": duplicate_races_excluded,
        "clean_rows_v1": int(len(detail)),
        "clean_races_v1": int(detail["backtest_race_key"].nunique()),
    }
    return detail, metrics


def summarize_segment(df: pd.DataFrame, segment_fields: list[str], segment_values: tuple[object, ...]) -> dict[str, object]:
    rows = int(len(df))
    races = int(df["backtest_race_key"].nunique())
    expected_wins = float(df["expected_win_v1"].fillna(0.0).sum())
    actual_wins = float(df["won"].fillna(0).sum())
    expected_win_pct = safe_pct(expected_wins, rows)
    actual_win_pct = safe_pct(actual_wins, rows)
    calibration_delta_pct = None
    if expected_win_pct is not None and actual_win_pct is not None:
        calibration_delta_pct = expected_win_pct - actual_win_pct

    sp_valid = df["sp_valid_v1"].eq("YES")
    sp_valid_rows = int(sp_valid.sum())
    roi_if_backed = None
    roi_net_units = None
    avg_sp = None
    median_sp = None
    if sp_valid_rows > 0:
        profits = pd.to_numeric(df.loc[sp_valid, "profit_1u_v1"], errors="coerce").dropna()
        roi_net_units = float(profits.sum()) if len(profits) else 0.0
        roi_if_backed = safe_pct(roi_net_units, sp_valid_rows)
        sp_vals = pd.to_numeric(df.loc[sp_valid, "sp"], errors="coerce").dropna()
        if len(sp_vals):
            avg_sp = float(sp_vals.mean())
            median_sp = float(sp_vals.median())

    avg_fair = pd.to_numeric(df["V6_1_RESEARCH_fair_price"], errors="coerce").dropna()
    avg_gap = pd.to_numeric(df["projection_gap_V6_1_RESEARCH"], errors="coerce").dropna()
    avg_prob = pd.to_numeric(df["V6_1_RESEARCH_probability"], errors="coerce").dropna()

    record: dict[str, object] = {
        "segment_level_v1": len(segment_fields),
        "segment_fields_v1": "|".join(segment_fields),
        "segment_key_v1": " | ".join(f"{field}={clean(value) or 'UNKNOWN'}" for field, value in zip(segment_fields, segment_values)),
        "rows_v1": rows,
        "races_v1": races,
        "sp_valid_rows_v1": sp_valid_rows,
        "expected_wins_v1": round_num(expected_wins, 3),
        "actual_wins_v1": round_num(actual_wins, 3),
        "expected_win_pct_v1": round_num(expected_win_pct, 3),
        "actual_win_pct_v1": round_num(actual_win_pct, 3),
        "calibration_delta_pct_v1": round_num(calibration_delta_pct, 3),
        "abs_calibration_delta_pct_v1": round_num(abs(calibration_delta_pct) if calibration_delta_pct is not None else None, 3),
        "roi_if_backed_pct_v1": round_num(roi_if_backed, 3),
        "roi_net_units_v1": round_num(roi_net_units, 3),
        "avg_fair_price_v1": round_num(float(avg_fair.mean()) if len(avg_fair) else None, 3),
        "avg_gap_v1": round_num(float(avg_gap.mean()) if len(avg_gap) else None, 3),
        "avg_probability_pct_v1": round_num(float(avg_prob.mean() * 100.0) if len(avg_prob) else None, 3),
        "avg_sp_v1": round_num(avg_sp, 3),
        "median_sp_v1": round_num(median_sp, 3),
        "empirical_fair_price_v1": round_num(fair_from_pct(actual_win_pct), 3),
        "rows_ge_25_v1": "YES" if rows >= 25 else "NO",
        "rows_ge_50_v1": "YES" if rows >= 50 else "NO",
        "rows_ge_100_v1": "YES" if rows >= 100 else "NO",
        "calibration_direction_v1": (
            "OVERCONFIDENT"
            if calibration_delta_pct is not None and calibration_delta_pct > 0
            else ("UNDERCONFIDENT" if calibration_delta_pct is not None and calibration_delta_pct < 0 else "FLAT")
        ),
        "built_at_v1": datetime.now(timezone.utc).isoformat(),
    }

    for column in DIMENSION_COLUMNS:
        record[column] = "ALL"
    for column, value in zip(segment_fields, segment_values):
        record[column] = clean(value) or "UNKNOWN"
    return record


def build_segments(detail: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for combo_size in range(1, len(DIMENSION_COLUMNS) + 1):
        for fields in combinations(DIMENSION_COLUMNS, combo_size):
            grouped = detail.groupby(list(fields), dropna=False)
            for keys, group in grouped:
                if not isinstance(keys, tuple):
                    keys = (keys,)
                if len(group) < MIN_ROWS_BASE:
                    continue
                records.append(summarize_segment(group.copy(), list(fields), keys))

    result = pd.DataFrame(records)
    if result.empty:
        raise RuntimeError("No archetype segments met the minimum row threshold.")

    result = result.sort_values(
        ["calibration_delta_pct_v1", "rows_v1", "segment_level_v1", "segment_key_v1"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)
    return result


def build_ranked(segments: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for threshold in SAMPLE_THRESHOLDS:
        eligible = segments[segments["rows_v1"] >= threshold].copy()
        over = eligible.sort_values(
            ["calibration_delta_pct_v1", "rows_v1", "segment_level_v1"],
            ascending=[False, False, True],
        ).head(50)
        under = eligible.sort_values(
            ["calibration_delta_pct_v1", "rows_v1", "segment_level_v1"],
            ascending=[True, False, True],
        ).head(50)

        over = over.copy()
        over["ranking_set_v1"] = f"TOP_50_OVERCONFIDENT_GE_{threshold}"
        over["ranking_threshold_v1"] = threshold
        over["ranking_position_v1"] = range(1, len(over) + 1)
        rows.extend(over.to_dict("records"))

        under = under.copy()
        under["ranking_set_v1"] = f"TOP_50_UNDERCONFIDENT_GE_{threshold}"
        under["ranking_threshold_v1"] = threshold
        under["ranking_position_v1"] = range(1, len(under) + 1)
        rows.extend(under.to_dict("records"))

    ranked = pd.DataFrame(rows)
    if ranked.empty:
        return ranked
    ranked = ranked.sort_values(
        ["ranking_threshold_v1", "ranking_set_v1", "ranking_position_v1"],
        ascending=[True, True, True],
    ).reset_index(drop=True)
    return ranked


def build_summary(segments: pd.DataFrame, metrics: dict[str, object]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add_row(section: str, rank_v1: int, label: str, value: object, notes: str = "") -> None:
        rows.append(
            {
                "section": section,
                "rank_v1": rank_v1,
                "label": label,
                "value": value,
                "notes": notes,
            }
        )

    add_row("OVERALL", 1, "status", "EDGEIQ_V6_1_OVERCONFIDENCE_ARCHETYPES_V1_BUILT")
    add_row("OVERALL", 2, "source", SOURCE_NAME)
    add_row("OVERALL", 3, "source_rows", metrics["source_rows_v1"])
    add_row("OVERALL", 4, "complete_matched_probability_rows", metrics["complete_matched_probability_rows_v1"])
    add_row("OVERALL", 5, "duplicate_backtest_rows_excluded", metrics["duplicate_backtest_rows_excluded_v1"])
    add_row("OVERALL", 6, "duplicate_backtest_races_excluded", metrics["duplicate_backtest_races_excluded_v1"])
    add_row("OVERALL", 7, "clean_rows_used", metrics["clean_rows_v1"])
    add_row("OVERALL", 8, "clean_races_used", metrics["clean_races_v1"])
    add_row("OVERALL", 9, "segment_rows_ge_25", int((segments["rows_v1"] >= 25).sum()))
    add_row("OVERALL", 10, "segment_rows_ge_50", int((segments["rows_v1"] >= 50).sum()))
    add_row("OVERALL", 11, "segment_rows_ge_100", int((segments["rows_v1"] >= 100).sum()))

    ge25 = segments[segments["rows_v1"] >= 25].copy()
    if not ge25.empty:
        over = ge25.sort_values(["calibration_delta_pct_v1", "rows_v1"], ascending=[False, False]).iloc[0]
        under = ge25.sort_values(["calibration_delta_pct_v1", "rows_v1"], ascending=[True, False]).iloc[0]
        roi_loss = ge25.dropna(subset=["roi_if_backed_pct_v1"]).sort_values(["roi_if_backed_pct_v1", "rows_v1"], ascending=[True, False]).iloc[0]
        roi_gain = ge25.dropna(subset=["roi_if_backed_pct_v1"]).sort_values(["roi_if_backed_pct_v1", "rows_v1"], ascending=[False, False]).iloc[0]

        add_row("KEY_FINDING", 1, "largest_overconfident_segment", clean(over["segment_key_v1"]), notes=f"delta_pct={clean(over['calibration_delta_pct_v1'])} rows={clean(over['rows_v1'])}")
        add_row("KEY_FINDING", 2, "largest_underconfident_segment", clean(under["segment_key_v1"]), notes=f"delta_pct={clean(under['calibration_delta_pct_v1'])} rows={clean(under['rows_v1'])}")
        add_row("KEY_FINDING", 3, "largest_roi_loss_segment", clean(roi_loss["segment_key_v1"]), notes=f"roi_pct={clean(roi_loss['roi_if_backed_pct_v1'])} rows={clean(roi_loss['rows_v1'])}")
        add_row("KEY_FINDING", 4, "largest_roi_gain_segment", clean(roi_gain["segment_key_v1"]), notes=f"roi_pct={clean(roi_gain['roi_if_backed_pct_v1'])} rows={clean(roi_gain['rows_v1'])}")

    for threshold in SAMPLE_THRESHOLDS:
        eligible = segments[segments["rows_v1"] >= threshold].copy()
        if eligible.empty:
            continue
        over = eligible.sort_values(["calibration_delta_pct_v1", "rows_v1"], ascending=[False, False]).iloc[0]
        under = eligible.sort_values(["calibration_delta_pct_v1", "rows_v1"], ascending=[True, False]).iloc[0]
        add_row(
            f"TOP_SEGMENT_GE_{threshold}",
            1,
            "overconfident",
            clean(over["segment_key_v1"]),
            notes=f"delta_pct={clean(over['calibration_delta_pct_v1'])} rows={clean(over['rows_v1'])}",
        )
        add_row(
            f"TOP_SEGMENT_GE_{threshold}",
            2,
            "underconfident",
            clean(under["segment_key_v1"]),
            notes=f"delta_pct={clean(under['calibration_delta_pct_v1'])} rows={clean(under['rows_v1'])}",
        )

    return pd.DataFrame(rows)


def main() -> None:
    detail, metrics = build_clean_detail()
    segments = build_segments(detail)
    ranked = build_ranked(segments)
    summary = build_summary(segments, metrics)

    segments.to_csv(OUT_ARCHETYPES, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    ranked.to_csv(OUT_RANKED, index=False)

    overall = summary[summary["section"].eq("OVERALL")].copy()
    key_findings = summary[summary["section"].eq("KEY_FINDING")].copy()
    print("[EDGEIQ_V6_1_OVERCONFIDENCE_ARCHETYPES_V1] COMPLETE")
    print(overall.to_string(index=False))
    if not key_findings.empty:
        print(key_findings.to_string(index=False))
    print(f"wrote={OUT_ARCHETYPES}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_RANKED}")


if __name__ == "__main__":
    main()
