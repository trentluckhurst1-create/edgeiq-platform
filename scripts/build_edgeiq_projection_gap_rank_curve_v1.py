from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_CANDIDATES = [
    DATA / "edgeiq_v6_1_settled_gap_replay_v1.csv",
    DATA / "edgeiq_historical_replay_settled_v1.csv",
]

OUT_DETAIL = DATA / "edgeiq_projection_gap_rank_curve_v1_detail.csv"
OUT_GAP_BUCKETS = DATA / "edgeiq_projection_gap_rank_curve_v1_gap_buckets.csv"
OUT_RANK_BUCKETS = DATA / "edgeiq_projection_gap_rank_curve_v1_rank_buckets.csv"
OUT_RANK1_GAP_BUCKETS = DATA / "edgeiq_projection_gap_rank_curve_v1_rank1_gap_buckets.csv"
OUT_SUMMARY = DATA / "edgeiq_projection_gap_rank_curve_v1_summary.csv"

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

GAP_BUCKET_ORDER = [label for _, _, label in GAP_BUCKETS]
RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_6", "RANK_7_PLUS"]

ATE_IRON_GAP_TEST = -5.66
TRIUMVIRATE_GAP_TEST = 8.92


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


def gap_bucket(value: float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "UNKNOWN"
    for lower, upper, label in GAP_BUCKETS:
        if value >= lower and value < upper:
            return label
    return "UNKNOWN"


def rank_bucket(value: int | float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "UNKNOWN"
    rank_value = int(value)
    if rank_value == 1:
        return "RANK_1"
    if rank_value == 2:
        return "RANK_2"
    if rank_value == 3:
        return "RANK_3"
    if 4 <= rank_value <= 6:
        return "RANK_4_6"
    return "RANK_7_PLUS"


def safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return (float(numerator) / float(denominator)) * 100.0


def fair_from_pct(win_pct: float | None) -> float | None:
    if win_pct is None or not math.isfinite(win_pct) or win_pct <= 0:
        return None
    return 100.0 / win_pct


def round_num(value: float | None, places: int = 3) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return round(float(value), places)


def select_source() -> Path:
    for path in SOURCE_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError(f"No source found from candidates: {[str(path) for path in SOURCE_CANDIDATES]}")


def load_source(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def build_detail(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    columns = list(df.columns)

    race_col = first_existing(columns, ["race_key"])
    date_col = first_existing(columns, ["meeting_date", "race_date"])
    track_col = first_existing(columns, ["track"])
    race_no_col = first_existing(columns, ["race_no"])
    horse_col = first_existing(columns, ["horse", "runner", "horse_name"])
    gap_col = first_existing(columns, ["projection_gap_V6_1_RESEARCH", "projection_gap_v5_2"])
    won_col = first_existing(columns, ["won"])
    placed_col = first_existing(columns, ["placed"])
    finish_col = first_existing(columns, ["finish_position"])
    sp_col = first_existing(columns, ["sp_num_settled", "sp", "sp_settled"])

    missing = []
    for label, col in [
        ("race_key", race_col),
        ("meeting_date/race_date", date_col),
        ("track", track_col),
        ("race_no", race_no_col),
        ("horse", horse_col),
        ("projection_gap", gap_col),
        ("won", won_col),
        ("finish_position", finish_col),
    ]:
        if col is None:
            missing.append(label)

    if missing:
        raise RuntimeError(f"Missing required columns: {missing}. Available columns: {columns}")

    detail = pd.DataFrame()
    detail["race_key"] = df[race_col].map(clean)
    detail["meeting_date"] = df[date_col].map(clean)
    detail["track"] = df[track_col].map(clean)
    detail["race_no"] = df[race_no_col].map(clean)
    detail["horse"] = df[horse_col].map(clean)
    detail["projection_gap_used"] = df[gap_col].map(to_float)
    detail["gap_col_used"] = gap_col
    detail["won"] = pd.to_numeric(df[won_col], errors="coerce").fillna(0).astype(int)
    detail["finish_position"] = pd.to_numeric(df[finish_col], errors="coerce")
    if placed_col:
        detail["placed"] = pd.to_numeric(df[placed_col], errors="coerce").fillna(0).astype(int)
    else:
        detail["placed"] = ((detail["finish_position"] >= 1) & (detail["finish_position"] <= 3)).astype(int)
    detail["sp"] = df[sp_col].map(to_float) if sp_col else np.nan

    detail = detail[detail["race_key"].ne("") & detail["horse"].ne("") & detail["projection_gap_used"].notna()].copy()
    detail["field_size"] = detail.groupby("race_key", dropna=False)["horse"].transform("count").astype(int)
    detail["gap_rank_in_race"] = (
        detail.groupby("race_key", dropna=False)["projection_gap_used"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    detail["gap_bucket"] = detail["projection_gap_used"].apply(gap_bucket)
    detail["gap_rank_bucket"] = detail["gap_rank_in_race"].apply(rank_bucket)
    detail["built_at"] = datetime.now(timezone.utc).isoformat()

    ordered_columns = [
        "race_key",
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "projection_gap_used",
        "gap_col_used",
        "gap_bucket",
        "gap_rank_in_race",
        "gap_rank_bucket",
        "field_size",
        "won",
        "placed",
        "finish_position",
        "sp",
        "built_at",
    ]
    return detail[ordered_columns].copy(), gap_col


def build_gap_bucket_table(detail: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        detail.groupby("gap_bucket", dropna=False)
        .agg(
            runners=("horse", "count"),
            races=("race_key", "nunique"),
            winners=("won", "sum"),
            placers=("placed", "sum"),
            avg_gap=("projection_gap_used", "mean"),
            avg_gap_rank=("gap_rank_in_race", "mean"),
            avg_finish_position=("finish_position", "mean"),
            avg_sp=("sp", "mean"),
            median_sp=("sp", "median"),
        )
        .reset_index()
    )
    grouped["win_pct"] = grouped.apply(lambda row: safe_pct(row["winners"], row["runners"]), axis=1)
    grouped["place_pct"] = grouped.apply(lambda row: safe_pct(row["placers"], row["runners"]), axis=1)
    grouped["empirical_fair_price"] = grouped["win_pct"].apply(fair_from_pct)

    grouped["gap_bucket"] = pd.Categorical(grouped["gap_bucket"], categories=GAP_BUCKET_ORDER, ordered=True)
    grouped = grouped.sort_values("gap_bucket").reset_index(drop=True)
    grouped["gap_bucket"] = grouped["gap_bucket"].astype(str)

    for column in ["win_pct", "place_pct", "empirical_fair_price", "avg_gap", "avg_gap_rank", "avg_finish_position", "avg_sp", "median_sp"]:
        grouped[column] = grouped[column].apply(round_num)

    return grouped[
        [
            "gap_bucket",
            "runners",
            "races",
            "winners",
            "placers",
            "win_pct",
            "place_pct",
            "empirical_fair_price",
            "avg_gap",
            "avg_gap_rank",
            "avg_finish_position",
            "avg_sp",
            "median_sp",
        ]
    ].copy()


def build_rank_bucket_table(detail: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        detail.groupby("gap_rank_bucket", dropna=False)
        .agg(
            runners=("horse", "count"),
            races=("race_key", "nunique"),
            winners=("won", "sum"),
            placers=("placed", "sum"),
            avg_gap=("projection_gap_used", "mean"),
            avg_finish_position=("finish_position", "mean"),
            avg_sp=("sp", "mean"),
            median_sp=("sp", "median"),
        )
        .reset_index()
    )
    grouped["win_pct"] = grouped.apply(lambda row: safe_pct(row["winners"], row["runners"]), axis=1)
    grouped["place_pct"] = grouped.apply(lambda row: safe_pct(row["placers"], row["runners"]), axis=1)
    grouped["empirical_fair_price"] = grouped["win_pct"].apply(fair_from_pct)

    grouped["gap_rank_bucket"] = pd.Categorical(grouped["gap_rank_bucket"], categories=RANK_BUCKET_ORDER, ordered=True)
    grouped = grouped.sort_values("gap_rank_bucket").reset_index(drop=True)
    grouped["gap_rank_bucket"] = grouped["gap_rank_bucket"].astype(str)

    for column in ["win_pct", "place_pct", "empirical_fair_price", "avg_gap", "avg_finish_position", "avg_sp", "median_sp"]:
        grouped[column] = grouped[column].apply(round_num)

    return grouped[
        [
            "gap_rank_bucket",
            "runners",
            "races",
            "winners",
            "placers",
            "win_pct",
            "place_pct",
            "empirical_fair_price",
            "avg_gap",
            "avg_finish_position",
            "avg_sp",
            "median_sp",
        ]
    ].copy()


def build_rank1_gap_bucket_table(detail: pd.DataFrame) -> pd.DataFrame:
    rank1 = detail[detail["gap_rank_in_race"] == 1].copy()
    grouped = (
        rank1.groupby("gap_bucket", dropna=False)
        .agg(
            races=("race_key", "nunique"),
            rank1_runners=("horse", "count"),
            rank1_winners=("won", "sum"),
            rank1_placers=("placed", "sum"),
            avg_rank1_gap=("projection_gap_used", "mean"),
            avg_rank1_sp=("sp", "mean"),
            median_rank1_sp=("sp", "median"),
        )
        .reset_index()
    )
    grouped["rank1_win_pct"] = grouped.apply(lambda row: safe_pct(row["rank1_winners"], row["rank1_runners"]), axis=1)
    grouped["rank1_place_pct"] = grouped.apply(lambda row: safe_pct(row["rank1_placers"], row["rank1_runners"]), axis=1)

    grouped["gap_bucket"] = pd.Categorical(grouped["gap_bucket"], categories=GAP_BUCKET_ORDER, ordered=True)
    grouped = grouped.sort_values("gap_bucket").reset_index(drop=True)
    grouped["gap_bucket"] = grouped["gap_bucket"].astype(str)

    for column in ["rank1_win_pct", "rank1_place_pct", "avg_rank1_gap", "avg_rank1_sp", "median_rank1_sp"]:
        grouped[column] = grouped[column].apply(round_num)

    return grouped[
        [
            "gap_bucket",
            "races",
            "rank1_runners",
            "rank1_winners",
            "rank1_placers",
            "rank1_win_pct",
            "rank1_place_pct",
            "avg_rank1_gap",
            "avg_rank1_sp",
            "median_rank1_sp",
        ]
    ].copy()


def lookup_bucket_row(table: pd.DataFrame, bucket_label: str) -> pd.Series | None:
    match = table[table["gap_bucket"] == bucket_label]
    if match.empty:
        return None
    return match.iloc[0]


def build_summary(source_path: Path, detail: pd.DataFrame, gap_table: pd.DataFrame, gap_col_used: str) -> pd.DataFrame:
    rank1 = detail[detail["gap_rank_in_race"] == 1].copy()

    ate_bucket = gap_bucket(ATE_IRON_GAP_TEST)
    triumvirate_bucket = gap_bucket(TRIUMVIRATE_GAP_TEST)

    ate_row = lookup_bucket_row(gap_table, ate_bucket)
    triumvirate_row = lookup_bucket_row(gap_table, triumvirate_bucket)

    warning = ""
    if gap_col_used == "projection_gap_v5_2":
        warning = "WARNING_USING_PROJECTION_GAP_V5_2_NOT_TRUE_V6_1"

    summary = pd.DataFrame(
        [
            {
                "status": "PROJECTION_GAP_RANK_CURVE_V1_BUILT",
                "source": source_path.name,
                "gap_col_used": gap_col_used,
                "rows_used": int(len(detail)),
                "races_used": int(detail["race_key"].nunique()),
                "rank1_win_pct": round_num(safe_pct(rank1["won"].sum(), len(rank1))),
                "rank1_place_pct": round_num(safe_pct(rank1["placed"].sum(), len(rank1))),
                "rank1_avg_gap": round_num(rank1["projection_gap_used"].mean()),
                "rank1_median_gap": round_num(rank1["projection_gap_used"].median()),
                "ate_iron_gap_test": ATE_IRON_GAP_TEST,
                "ate_iron_bucket": ate_bucket,
                "ate_iron_bucket_win_pct": round_num(float(ate_row["win_pct"])) if ate_row is not None and pd.notna(ate_row["win_pct"]) else None,
                "ate_iron_bucket_empirical_fair": round_num(float(ate_row["empirical_fair_price"])) if ate_row is not None and pd.notna(ate_row["empirical_fair_price"]) else None,
                "triumvirate_gap_test": TRIUMVIRATE_GAP_TEST,
                "triumvirate_bucket": triumvirate_bucket,
                "triumvirate_bucket_win_pct": round_num(float(triumvirate_row["win_pct"])) if triumvirate_row is not None and pd.notna(triumvirate_row["win_pct"]) else None,
                "triumvirate_bucket_empirical_fair": round_num(float(triumvirate_row["empirical_fair_price"])) if triumvirate_row is not None and pd.notna(triumvirate_row["empirical_fair_price"]) else None,
                "warning": warning,
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
    source_path = select_source()
    df = load_source(source_path)
    detail, gap_col_used = build_detail(df)
    gap_buckets = build_gap_bucket_table(detail)
    rank_buckets = build_rank_bucket_table(detail)
    rank1_gap_buckets = build_rank1_gap_bucket_table(detail)
    summary = build_summary(source_path, detail, gap_buckets, gap_col_used)

    detail.to_csv(OUT_DETAIL, index=False)
    gap_buckets.to_csv(OUT_GAP_BUCKETS, index=False)
    rank_buckets.to_csv(OUT_RANK_BUCKETS, index=False)
    rank1_gap_buckets.to_csv(OUT_RANK1_GAP_BUCKETS, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    print("[PROJECTION_GAP_RANK_CURVE_V1] COMPLETE")
    print_section("SUMMARY", summary)
    print_section("GAP BUCKETS", gap_buckets)
    print_section("RANK BUCKETS", rank_buckets)
    print_section("RANK1 GAP BUCKETS", rank1_gap_buckets)


if __name__ == "__main__":
    main()
