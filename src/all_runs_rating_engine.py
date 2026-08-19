from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


RATING_VERSION = "v1.1_all_runs_backbone"


# =========================================================
# ALL RUNS RATING ENGINE
# ---------------------------------------------------------
# Purpose:
#   Rate every historical run of every horse from horse_runs_ra.csv
#   into durable master outputs for modelling and UI use.
#
# Outputs:
#   1. all_horse_runs_rated.csv
#   2. all_horse_rating_summary.csv
#   3. all_horse_runs_excluded.csv
# =========================================================


# -----------------------------
# Helpers
# -----------------------------


def norm_text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {"nan", "none", "null", "na", "n/a"}:
        return ""
    return text



def upper_text(value: object) -> str:
    return norm_text(value).upper()



def safe_float(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        if pd.isna(value):
            return None
        return float(value)
    text = norm_text(value)
    if not text:
        return None
    text = text.replace(",", "")
    text = text.replace("kg", "")
    text = text.replace("m", "")
    text = text.replace("%", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None



def safe_int(value: object) -> Optional[int]:
    number = safe_float(value)
    if number is None:
        return None
    return int(round(number))



def first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    lower_map = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        actual = lower_map.get(candidate.lower())
        if actual is not None:
            return actual
    return None



def parse_date_series(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    parsed = pd.to_datetime(s, format="%d%b%y", errors="coerce")
    fallback = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return parsed.fillna(fallback)



def minmax_scale(series: pd.Series, floor: float = 0.0, ceiling: float = 1.0) -> pd.Series:
    valid = pd.to_numeric(series, errors="coerce")
    s_min = valid.min(skipna=True)
    s_max = valid.max(skipna=True)
    if pd.isna(s_min) or pd.isna(s_max) or s_min == s_max:
        return pd.Series(np.where(valid.notna(), (floor + ceiling) / 2.0, np.nan), index=series.index)
    scaled = (valid - s_min) / (s_max - s_min)
    return floor + scaled * (ceiling - floor)


# -----------------------------
# Column mapping
# -----------------------------


@dataclass
class RunColumns:
    horse_name: str
    horse_key: str
    run_date: str
    track: str
    distance: str
    race_name: str
    race_class: str
    finish_pos: str
    field_size: str
    margin: str
    jockey: str
    weight: str
    barrier: str
    odds: str
    track_condition: str
    run_rating_raw: str
    prizemoney: str
    in_run: str
    raw_run_text: str
    run_type: str



def detect_columns(df: pd.DataFrame) -> RunColumns:
    def required(name: str, candidates: List[str]) -> str:
        col = first_existing(df, candidates)
        if col is None:
            raise ValueError(f"Missing required column for {name}. Tried: {candidates}")
        return col

    def optional(candidates: List[str], fallback_name: str) -> str:
        col = first_existing(df, candidates)
        if col is not None:
            return col
        if fallback_name not in df.columns:
            df[fallback_name] = np.nan
        return fallback_name

    return RunColumns(
        horse_name=required("horse_name", ["horse", "horse_name", "runner", "horse_nm"]),
        horse_key=optional(["horse_key", "runner_key", "horse_id", "horse_slug", "horse_code"], "horse_key"),
        run_date=required("run_date", ["run_date", "date", "race_date"]),
        track=required("track", ["track", "track_code", "venue", "race_track"]),
        distance=required("distance", ["distance", "dist", "race_distance"]),
        race_name=optional(["race_name", "race", "event_name"], "race_name"),
        race_class=optional(["race_class", "class", "grade", "race_grade"], "race_class"),
        finish_pos=required("finish_pos", ["finish", "finish_pos", "placing", "position", "result"]),
        field_size=optional(["field_size", "field", "runners", "starter_count"], "field_size"),
        margin=optional(["margin", "margin_beaten", "btn_margin", "beaten_margin"], "margin"),
        jockey=optional(["jockey", "jockey_name", "rider"], "jockey"),
        weight=optional(["weight", "wt", "carried_weight"], "weight"),
        barrier=optional(["barrier", "gate", "draw"], "barrier"),
        odds=optional(["odds", "sp", "starting_price", "price"], "odds"),
        track_condition=optional(["going", "track_condition", "surface", "track_rating"], "track_condition"),
        run_rating_raw=optional(["rating", "run_rating", "ra_rating", "performance_rating", "run_rating_raw"], "run_rating_raw"),
        prizemoney=optional(["prizemoney", "prize_money", "stake", "prizemoney_earned", "prizemoney_race"], "prizemoney"),
        in_run=optional(["in_run", "inrun", "settling", "positions", "in_run_positions_raw"], "in_run"),
        raw_run_text=optional(["raw_run_text", "raw_text", "run_text", "comment_raw"], "raw_run_text"),
        run_type=optional(["run_type", "run_type_code"], "run_type"),
    )


# -----------------------------
# Parsing and classification
# -----------------------------


TRIAL_PATTERNS = [
    r"\bTRIAL\b",
    r"\bJUMP\s?OUT\b",
    r"\bJUMPOUT\b",
    r"\bHEAT\b",
    r"\bBARRIER\s+TRIAL\b",
    r"\bMDN-BT\b",
    r"\bBT\b",
]


CLASS_SCORES = {
    "GROUP 1": 112,
    "G1": 112,
    "GROUP 2": 109,
    "G2": 109,
    "GROUP 3": 106,
    "G3": 106,
    "LISTED": 103,
    "LR": 103,
    "OPEN": 100,
    "BENCHMARK": 96,
    "BM": 96,
    "HANDICAP": 95,
    "QUALITY": 95,
    "SET WEIGHTS": 96,
    "MAIDEN": 86,
    "MDN": 86,
    "CLASS 1": 89,
    "CLASS 2": 91,
    "CLASS 3": 93,
    "CLASS 4": 95,
    "CLASS 5": 97,
    "CLASS 6": 99,
    "SUPER": 98,
    "3YO": 94,
    "2YO": 90,
}


GOING_SCORES = {
    "HEAVY": -4.0,
    "SOFT": -2.0,
    "GOOD": 0.0,
    "FIRM": 0.5,
    "SYNTHETIC": -1.0,
    "POLY": -1.0,
}


DISTANCE_BUCKETS = [
    (0, 1100, "sprint"),
    (1101, 1400, "short_middle"),
    (1401, 1800, "middle"),
    (1801, 2200, "staying"),
    (2201, 5000, "long_staying"),
]



def infer_trial_from_text(run_type: object, race_name: object, race_class: object, raw_run_text: object, weight: object, barrier: object) -> bool:
    rt = upper_text(run_type)
    if rt in {"T", "TRIAL"}:
        return True
    if rt in {"J", "JUMPOUT", "JUMP OUT"}:
        return True
    text_parts = [upper_text(race_name), upper_text(race_class), upper_text(raw_run_text)]
    combined = " | ".join(part for part in text_parts if part)
    if any(re.search(pattern, combined) for pattern in TRIAL_PATTERNS):
        return True
    wt = safe_float(weight)
    bar = safe_int(barrier)
    if wt == 0 and bar == 0:
        return True
    return False



def parse_finish_position(value: object) -> Tuple[Optional[int], bool]:
    text = upper_text(value)
    if not text:
        return None, False
    if any(tag in text for tag in ["SCR", "SCRATCH", "DNS", "DID NOT START", "ABANDONED", "VOID"]):
        return None, True
    match = re.search(r"\d+", text)
    if not match:
        return None, False
    return int(match.group()), False



def infer_field_size(finish_pos: Optional[int], field_size_raw: object) -> Optional[int]:
    field_size = safe_int(field_size_raw)
    if field_size is not None and field_size > 0:
        return field_size
    return finish_pos if finish_pos is not None else None



def parse_margin(value: object) -> float:
    text = upper_text(value)
    if not text:
        return 0.0
    if any(token in text for token in ["NSE", "NOSE"]):
        return 0.05
    if "SH" in text and "L" not in text:
        return 0.1
    if "HD" in text or text == "HEAD":
        return 0.2
    if "NK" in text:
        return 0.3
    num = safe_float(text)
    if num is None:
        return 0.0
    return max(num, 0.0)



def parse_distance(value: object) -> Optional[int]:
    distance = safe_int(value)
    if distance is None:
        return None
    if distance < 300 or distance > 5000:
        return None
    return distance

def extract_race_class_from_name(race_name: object) -> str:
    text = upper_text(race_name)
    if not text:
        return "UNKNOWN"

    # Group / Listed
    if "GROUP 1" in text or re.search(r"\bG1\b", text):
        return "GROUP 1"
    if "GROUP 2" in text or re.search(r"\bG2\b", text):
        return "GROUP 2"
    if "GROUP 3" in text or re.search(r"\bG3\b", text):
        return "GROUP 3"
    if "LISTED" in text or re.search(r"\bLR\b", text):
        return "LISTED"

    # Benchmark
    bm = re.search(r"\b(?:BM|BENCHMARK)\s*(\d{2,3})\b", text)
    if bm:
        return f"BM{bm.group(1)}"

    # Class races
    cls = re.search(r"\bCLASS\s*(\d)\b", text)
    if cls:
        return f"CLASS {cls.group(1)}"

    # Common Australian race types
    if "MAIDEN" in text or re.search(r"\bMDN\b", text):
        if "SET WEIGHTS" in text or "SW" in text:
            return "MAIDEN SW"
        return "MAIDEN"

    if "HCP" in text or "HANDICAP" in text:
        if "2Y" in text:
            return "2YO HANDICAP"
        if "3Y" in text:
            return "3YO HANDICAP"
        return "HANDICAP"

    if "SUPER" in text and ("MDN" in text or "MAIDEN" in text):
        return "SUPER MAIDEN"

    if "PROV" in text and ("MDN" in text or "MAIDEN" in text):
        return "PROV MAIDEN"

    if "CG&E" in text and ("MDN" in text or "MAIDEN" in text):
        return "CG&E MAIDEN"

    if "F&M" in text and ("MDN" in text or "MAIDEN" in text):
        return "F&M MAIDEN"

    if "2Y" in text and ("MDN" in text or "MAIDEN" in text):
        return "2YO MAIDEN"
    if "3Y" in text and ("MDN" in text or "MAIDEN" in text):
        return "3YO MAIDEN"

    if "2Y" in text:
        return "2YO"
    if "3Y" in text:
        return "3YO"

    if "OPEN" in text:
        return "OPEN"

    return "UNKNOWN"


def normalize_class(value: object) -> str:
    text = upper_text(value)
    if not text:
        return "UNKNOWN"
    text = re.sub(r"\s+", " ", text)
    return extract_race_class_from_name(text)



def class_base_score(class_text: str) -> float:
    text = upper_text(class_text)

    if not text or text == "UNKNOWN":
        return 92.0

    fixed_scores = {
        "GROUP 1": 112.0,
        "GROUP 2": 109.0,
        "GROUP 3": 106.0,
        "LISTED": 103.0,
        "OPEN": 100.0,
        "HANDICAP": 95.0,
        "2YO HANDICAP": 91.0,
        "3YO HANDICAP": 94.0,
        "MAIDEN": 86.0,
        "MAIDEN SW": 87.0,
        "SUPER MAIDEN": 88.0,
        "PROV MAIDEN": 87.0,
        "CG&E MAIDEN": 87.0,
        "F&M MAIDEN": 87.0,
        "2YO MAIDEN": 84.0,
        "3YO MAIDEN": 86.0,
        "2YO": 90.0,
        "3YO": 94.0,
        "CLASS 1": 89.0,
        "CLASS 2": 91.0,
        "CLASS 3": 93.0,
        "CLASS 4": 95.0,
        "CLASS 5": 97.0,
        "CLASS 6": 99.0,
    }

    if text in fixed_scores:
        return fixed_scores[text]

    bm = re.search(r"\bBM\s*(\d{2,3})\b", text)
    if bm:
        return float(bm.group(1))

    return 92.0



def going_adjustment(value: object) -> float:
    text = upper_text(value)
    if not text:
        return 0.0
    for key, adj in GOING_SCORES.items():
        if key in text:
            return adj
    return 0.0



def distance_bucket(distance: Optional[int]) -> str:
    if distance is None:
        return "unknown"
    for lo, hi, label in DISTANCE_BUCKETS:
        if lo <= distance <= hi:
            return label
    return "unknown"



def odds_implied_prob(value: object) -> Optional[float]:
    odds = safe_float(value)
    if odds is None or odds <= 1.0:
        return None
    return 1.0 / odds



def recency_weight(days_since: Optional[float]) -> float:
    if days_since is None or pd.isna(days_since):
        return 0.65
    if days_since <= 30:
        return 1.00
    if days_since <= 90:
        return 0.96
    if days_since <= 180:
        return 0.91
    if days_since <= 365:
        return 0.84
    if days_since <= 730:
        return 0.75
    return 0.67


# -----------------------------
# Rating engine
# -----------------------------



def build_base_rating(df: pd.DataFrame) -> pd.Series:
    finish_component = np.where(
        df["finish_pos_num"].notna() & df["field_size_num"].notna() & (df["field_size_num"] > 1),
        100.0 * (1.0 - ((df["finish_pos_num"] - 1.0) / (df["field_size_num"] - 1.0))),
        np.nan,
    )
    finish_component = pd.Series(finish_component, index=df.index).fillna(50.0)

    margin_penalty = np.clip(df["margin_num"].fillna(0.0) * 2.4, 0.0, 25.0)
    class_component = df["class_score"].fillna(92.0)

    raw_existing = pd.to_numeric(df["run_rating_raw_num"], errors="coerce")
    raw_existing_scaled = pd.Series(np.nan, index=df.index)
    if raw_existing.notna().sum() >= 10:
        raw_existing_scaled = minmax_scale(raw_existing, 78.0, 108.0)

    odds_prob = df["odds_prob"].fillna(df["finish_market_proxy"])
    market_component = np.clip(odds_prob * 38.0, 0.0, 24.0)

    field_strength_adj = np.clip((df["field_size_num"].fillna(8) - 8.0) * 0.65, -4.0, 6.0)
    weight_adj = np.clip((58.0 - df["weight_num"].fillna(56.0)) * 0.55, -5.0, 5.0)
    barrier_adj = np.clip((8.0 - df["barrier_num"].fillna(8.0)) * 0.25, -3.0, 2.5)
    going_adj = df["going_adj"].fillna(0.0)

    base = (
        0.52 * finish_component
        + 0.28 * class_component
        + 0.20 * market_component
        + field_strength_adj
        + weight_adj
        + barrier_adj
        + going_adj
        - margin_penalty
    )

    use_existing_mask = raw_existing_scaled.notna()
    base = np.where(use_existing_mask, 0.65 * base + 0.35 * raw_existing_scaled, base)
    return pd.Series(np.clip(base, 35.0, 125.0), index=df.index)



def add_relative_race_strength(df: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["run_date_dt", "track_norm", "distance_num", "race_name_norm"]
    df["race_strength"] = df.groupby(group_cols)["base_rating"].transform("mean")
    df["race_strength"] = df["race_strength"].fillna(df["class_score"])
    df["relative_to_race"] = df["base_rating"] - df["race_strength"]
    return df



def smooth_horse_ratings(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["horse_name_norm", "run_date_dt", "finish_pos_num", "track_norm"]).copy()

    def _smooth(group: pd.DataFrame) -> pd.DataFrame:
        g = group.copy()
        g["horse_run_number"] = np.arange(1, len(g) + 1)
        g["prior_peak_rating"] = g["base_rating"].cummax().shift(1)
        g["prior_peak_rating"] = g["prior_peak_rating"].fillna(g["base_rating"])
        g["prior_3_avg"] = g["base_rating"].shift(1).rolling(3, min_periods=1).mean()
        g["prior_5_avg"] = g["base_rating"].shift(1).rolling(5, min_periods=1).mean()
        g["prior_3_avg"] = g["prior_3_avg"].fillna(g["base_rating"])
        g["prior_5_avg"] = g["prior_5_avg"].fillna(g["base_rating"])

        latest_date = g["run_date_dt"].max()
        g["days_since_latest_in_file"] = (latest_date - g["run_date_dt"]).dt.days
        g["recency_weight"] = g["days_since_latest_in_file"].apply(recency_weight)

        g["trend_vs_last3"] = g["base_rating"] - g["prior_3_avg"]
        g["consistency_5"] = g["base_rating"].rolling(5, min_periods=2).std().fillna(0.0)

        adjusted = (
            0.70 * g["base_rating"]
            + 0.15 * g["prior_3_avg"]
            + 0.10 * g["prior_peak_rating"]
            + 0.05 * g["race_strength"]
        )
        adjusted += np.clip(g["trend_vs_last3"], -4.0, 4.0) * 0.35
        adjusted -= np.clip(g["consistency_5"], 0.0, 12.0) * 0.22
        adjusted = adjusted * g["recency_weight"] + g["base_rating"] * (1.0 - g["recency_weight"])

        g["run_rating"] = np.clip(adjusted, 35.0, 130.0)
        g["peak_to_date"] = g["run_rating"].cummax()
        return g

    return df.groupby("horse_name_norm", group_keys=False).apply(_smooth)



def summarize_horses(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "horse_name_norm" not in df.columns:
        df["horse_name_norm"] = df["horse_name"].map(upper_text)

    if "horse_key" not in df.columns:
        df["horse_key"] = df["horse_name"]

    df["horse_key"] = df["horse_key"].fillna("").astype(str)
    bad_key = df["horse_key"].isin(["", "nan", "None"])
    df.loc[bad_key, "horse_key"] = df.loc[bad_key, "horse_name"]

    if "horse_key_norm" not in df.columns:
        df["horse_key_norm"] = df["horse_key"].map(upper_text)

    def mode_or_blank(series: pd.Series) -> str:
        clean = series.dropna().astype(str)
        if clean.empty:
            return ""
        mode = clean.mode()
        return mode.iloc[0] if not mode.empty else clean.iloc[0]

    summary = df.groupby(["horse_name_norm", "horse_key_norm"], dropna=False).agg(
        horse_name=("horse_name", "last"),
        horse_key=("horse_key", "last"),
        total_runs=("run_rating", "size"),
        latest_run_date=("run_date_dt", "max"),
        first_run_date=("run_date_dt", "min"),
        latest_rating=("run_rating", "last"),
        peak_rating=("run_rating", "max"),
        average_rating=("run_rating", "mean"),
        last_3_avg=("run_rating", lambda s: s.tail(3).mean()),
        last_5_avg=("run_rating", lambda s: s.tail(5).mean()),
        best_distance_bucket=("distance_bucket", mode_or_blank),
        preferred_condition=("going_group", mode_or_blank),
        wins=("is_win", "sum"),
        placings=("is_place", "sum"),
        avg_margin=("margin_num", "mean"),
        avg_field_size=("field_size_num", "mean"),
    ).reset_index(drop=True)

    summary["win_rate"] = np.where(summary["total_runs"] > 0, summary["wins"] / summary["total_runs"], np.nan)
    summary["place_rate"] = np.where(summary["total_runs"] > 0, summary["placings"] / summary["total_runs"], np.nan)
    summary["rating_delta_peak_vs_latest"] = summary["latest_rating"] - summary["peak_rating"]
    summary["rating_delta_last3_vs_peak"] = summary["last_3_avg"] - summary["peak_rating"]
    summary["career_stage"] = np.select(
        [summary["total_runs"] <= 3, summary["total_runs"].between(4, 10), summary["total_runs"] > 10],
        ["early", "developing", "established"],
        default="unknown",
    )
    summary["rating_version"] = RATING_VERSION
    return summary.sort_values(["peak_rating", "latest_rating"], ascending=[False, False])


# -----------------------------
# Main transform
# -----------------------------



def prepare_runs(df: pd.DataFrame, cols: RunColumns) -> Tuple[pd.DataFrame, pd.DataFrame]:
    runs = df.copy()

    runs["horse_name"] = runs[cols.horse_name].astype(str).str.strip()
    runs["horse_key"] = runs[cols.horse_key].astype(str).str.strip()
    runs["horse_key"] = runs["horse_key"].replace({"nan": "", "None": ""})
    runs.loc[runs["horse_key"] == "", "horse_key"] = runs.loc[runs["horse_key"] == "", "horse_name"]

    runs["run_date"] = runs[cols.run_date]
    runs["track"] = runs[cols.track]
    runs["distance"] = runs[cols.distance]
    runs["race_name"] = runs[cols.race_name]
    runs["race_class"] = runs[cols.race_class]

    runs["race_name"] = runs["race_name"].fillna("").astype(str)
    runs["race_class"] = runs["race_class"].fillna("").astype(str)

    blank_class = runs["race_class"].str.strip().isin(["", "nan", "None"])
    runs.loc[blank_class, "race_class"] = runs.loc[blank_class, "race_name"].apply(extract_race_class_from_name)
    runs["finish_pos"] = runs[cols.finish_pos]
    runs["field_size"] = runs[cols.field_size]
    runs["margin"] = runs[cols.margin]
    runs["jockey"] = runs[cols.jockey]
    runs["weight"] = runs[cols.weight]
    runs["barrier"] = runs[cols.barrier]
    runs["odds"] = runs[cols.odds]
    runs["track_condition"] = runs[cols.track_condition]
    runs["run_rating_raw"] = runs[cols.run_rating_raw]
    runs["prizemoney"] = runs[cols.prizemoney]
    runs["in_run"] = runs[cols.in_run]
    runs["raw_run_text"] = runs[cols.raw_run_text]
    runs["run_type"] = runs[cols.run_type]

    runs["horse_name_norm"] = runs["horse_name"].map(upper_text)
    runs["horse_key_norm"] = runs["horse_key"].map(upper_text)
    runs["track_norm"] = runs["track"].map(upper_text)
    runs["race_name_norm"] = runs["race_name"].map(upper_text)
    runs["race_class_norm"] = runs["race_class"].map(normalize_class)
    runs["run_date_dt"] = parse_date_series(runs["run_date"])

    finish_parsed = runs["finish_pos"].apply(parse_finish_position)
    runs["finish_pos_num"] = [x[0] for x in finish_parsed]
    runs["non_runner"] = [x[1] for x in finish_parsed]

    runs["field_size_num"] = [infer_field_size(fp, fs) for fp, fs in zip(runs["finish_pos_num"], runs["field_size"])]
    runs["margin_num"] = runs["margin"].apply(parse_margin)
    runs["distance_num"] = runs["distance"].apply(parse_distance)
    runs["weight_num"] = runs["weight"].apply(safe_float)
    runs["barrier_num"] = runs["barrier"].apply(safe_int)
    runs["odds_num"] = runs["odds"].apply(safe_float)
    runs["odds_prob"] = runs["odds_num"].apply(odds_implied_prob)
    runs["run_rating_raw_num"] = runs["run_rating_raw"].apply(safe_float)
    runs["prizemoney_num"] = runs["prizemoney"].apply(safe_float)

    runs["is_trial"] = runs.apply(
        lambda row: infer_trial_from_text(
            row.get("run_type"),
            row.get("race_name"),
            row.get("race_class"),
            row.get("raw_run_text"),
            row.get("weight"),
            row.get("barrier"),
        ),
        axis=1,
    )
    runs["missing_date"] = runs["run_date_dt"].isna()
    runs["missing_horse"] = runs["horse_name_norm"].eq("")
    runs["missing_track"] = runs["track_norm"].eq("")
    runs["invalid_finish"] = runs["finish_pos_num"].isna()

    exclusion_reasons = np.select(
        [
            runs["is_trial"],
            runs["non_runner"],
            runs["missing_date"],
            runs["missing_horse"],
            runs["missing_track"],
            runs["invalid_finish"],
        ],
        [
            "trial_or_jumpout",
            "non_runner_or_void",
            "missing_date",
            "missing_horse_name",
            "missing_track",
            "invalid_finish_position",
        ],
        default="",
    )
    runs["exclusion_reason"] = exclusion_reasons

    excluded = runs[runs["exclusion_reason"] != ""].copy()
    clean = runs[runs["exclusion_reason"] == ""].copy()

    clean["class_score"] = clean["race_class_norm"].apply(class_base_score)
    clean["going_adj"] = clean["track_condition"].apply(going_adjustment)
    clean["going_group"] = clean["track_condition"].map(lambda x: upper_text(x).split()[0] if upper_text(x) else "UNKNOWN")
    clean["distance_bucket"] = clean["distance_num"].apply(distance_bucket)
    clean["is_win"] = (clean["finish_pos_num"] == 1).astype(int)
    clean["is_place"] = (clean["finish_pos_num"] <= 3).astype(int)
    clean["finish_market_proxy"] = np.where(
        clean["finish_pos_num"] == 1,
        0.34,
        np.where(clean["finish_pos_num"] <= 3, 0.20, 0.08),
    )

    return clean, excluded



def finalize_run_table(df: pd.DataFrame) -> pd.DataFrame:
    ordered_cols = [
        "horse_name",
        "horse_key",
        "run_date_dt",
        "track",
        "distance_num",
        "distance_bucket",
        "race_name",
        "race_class",
        "track_condition",
        "going_group",
        "finish_pos_num",
        "field_size_num",
        "margin_num",
        "jockey",
        "weight_num",
        "barrier_num",
        "odds_num",
        "odds_prob",
        "run_rating_raw_num",
        "class_score",
        "going_adj",
        "base_rating",
        "race_strength",
        "relative_to_race",
        "prior_peak_rating",
        "prior_3_avg",
        "prior_5_avg",
        "trend_vs_last3",
        "consistency_5",
        "recency_weight",
        "run_rating",
        "peak_to_date",
        "horse_run_number",
        "is_win",
        "is_place",
        "in_run",
        "prizemoney_num",
        "raw_run_text",
    ]
    remainder = [c for c in df.columns if c not in ordered_cols]
    out = df[ordered_cols + remainder].copy()
    out = out.rename(columns={"run_date_dt": "run_date", "distance_num": "distance"})
    out["rating_version"] = RATING_VERSION
    return out



def run_engine(input_csv: Path, output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    source = pd.read_csv(input_csv, low_memory=False)
    cols = detect_columns(source)
    clean, excluded = prepare_runs(source, cols)

    if clean.empty:
        raise ValueError("No valid race runs available after exclusions. Check source data and column mapping.")

    clean = clean.sort_values(["horse_name_norm", "run_date_dt", "track_norm", "finish_pos_num"]).copy()
    clean["base_rating"] = build_base_rating(clean)
    clean = add_relative_race_strength(clean)
    clean = smooth_horse_ratings(clean)

    run_table = finalize_run_table(clean)
    summary_table = summarize_horses(clean)

    excluded_out = excluded.copy()
    if "run_date_dt" in excluded_out.columns:
        excluded_out = excluded_out.rename(columns={"run_date_dt": "run_date"})

    runs_path = output_dir / "all_horse_runs_rated.csv"
    summary_path = output_dir / "all_horse_rating_summary.csv"
    excluded_path = output_dir / "all_horse_runs_excluded.csv"

    run_table.to_csv(runs_path, index=False)
    summary_table.to_csv(summary_path, index=False)
    excluded_out.to_csv(excluded_path, index=False)

    return {
        "runs": runs_path,
        "summary": summary_path,
        "excluded": excluded_path,
    }


# -----------------------------
# CLI
# -----------------------------



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rate every historical horse run into a durable master dataset.")
    parser.add_argument(
        "--input-csv",
        default="outputs/ra_form/horse_runs_ra.csv",
        help="Path to source horse runs CSV",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/ratings",
        help="Directory for rated outputs",
    )
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    output_dir = Path(args.output_dir)

    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv.resolve()}")

    print("=== ALL RUNS RATING ENGINE ===")
    print(f"Source: {input_csv.resolve()}")
    print(f"Output: {output_dir.resolve()}")
    print(f"Rating version: {RATING_VERSION}")

    paths = run_engine(input_csv=input_csv, output_dir=output_dir)

    print("\n✅ Completed")
    for key, path in paths.items():
        print(f"  {key}: {path.resolve()}")


if __name__ == "__main__":
    main()
