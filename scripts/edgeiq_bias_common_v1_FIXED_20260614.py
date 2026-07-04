from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TRACK_SPONSOR_TOKENS = [
    "BET365",
    "SPORTSBET",
    "LADBROKES",
    "TAB",
    "RACINGCOM",
    "RACING COM",
]

BIAS_PLACE_WEIGHT = 0.35


def data_path(name: str) -> Path:
    return DATA / name


def read_csv(name: str, **kwargs) -> pd.DataFrame:
    path = data_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}")
    if "low_memory" not in kwargs:
        kwargs["low_memory"] = False
    return pd.read_csv(path, **kwargs)


def write_csv(df: pd.DataFrame, name: str) -> Path:
    path = data_path(name)
    df.to_csv(path, index=False)
    return path


def write_json(payload: dict, name: str) -> Path:
    path = data_path(name)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def normalize_track(value) -> str:
    text = "" if pd.isna(value) else str(value).upper()
    for token in TRACK_SPONSOR_TOKENS:
        text = text.replace(token, " ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_horse_key(value) -> str:
    return clean_text(value)


def safe_num(series_or_value):
    return pd.to_numeric(series_or_value, errors="coerce")


def pct_from_counts(numerator, denominator):
    if denominator in (0, None) or pd.isna(denominator):
        return np.nan
    return round(float(numerator) / float(denominator) * 100.0, 2)


def win_place_score(win_pct, place_pct, baseline_win_pct, baseline_place_pct):
    if any(pd.isna(v) for v in [win_pct, place_pct, baseline_win_pct, baseline_place_pct]):
        return np.nan
    return round((win_pct - baseline_win_pct) + BIAS_PLACE_WEIGHT * (place_pct - baseline_place_pct), 3)


def bias_band(score) -> str:
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 2.0:
        return "STRONG_POSITIVE"
    if score >= 0.75:
        return "POSITIVE"
    if score <= -2.0:
        return "STRONG_NEGATIVE"
    if score <= -0.75:
        return "NEGATIVE"
    return "NEUTRAL"


def parse_distance_m(value):
    if pd.isna(value):
        return np.nan
    match = re.search(r"(\d+)", str(value))
    return float(match.group(1)) if match else np.nan


def distance_band_from_meters(value) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    meters = float(value)
    if meters < 1000:
        return "<1000"
    if meters <= 1199:
        return "1000-1199"
    if meters <= 1399:
        return "1200-1399"
    if meters <= 1599:
        return "1400-1599"
    if meters <= 1799:
        return "1600-1799"
    if meters <= 1999:
        return "1800-1999"
    return "2000+"


def condition_group(value) -> str:
    text = "" if pd.isna(value) else str(value).upper()
    if "HEAVY" in text:
        return "HEAVY"
    if "SOFT" in text:
        return "SOFT"
    if "GOOD" in text or "FIRM" in text:
        return "GOOD"
    if "SYNTHETIC" in text:
        return "SYNTHETIC"
    return "UNKNOWN"


def wet_flag(group_value) -> bool:
    return str(group_value).upper() in {"SOFT", "HEAVY"}


def barrier_bucket(value) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    barrier = int(value)
    if barrier <= 0:
        return "UNKNOWN"
    if barrier <= 2:
        return "1-2"
    if barrier <= 4:
        return "3-4"
    if barrier <= 6:
        return "5-6"
    if barrier <= 8:
        return "7-8"
    if barrier <= 10:
        return "9-10"
    if barrier <= 12:
        return "11-12"
    return "13+"


def map_run_style(value) -> str:
    text = "" if pd.isna(value) else str(value).upper().replace("_", " ").strip()
    if text == "LEADER":
        return "LEADER"
    if text in {"ON PACE", "ONPACE"}:
        return "ON_PACE"
    if text == "MIDFIELD":
        return "MIDFIELD"
    if text == "BACKMARKER":
        return "BACKMARKER"
    return "UNKNOWN"


def representative_track_name(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if "track_raw" not in df.columns:
        return pd.DataFrame(columns=group_cols + ["track_display_v1"])
    return (
        df.groupby(group_cols, dropna=False)["track_raw"]
        .agg(lambda s: s.mode().iat[0] if not s.mode().empty else s.iloc[0])
        .reset_index(name="track_display_v1")
    )


def aggregate_bias_table(
    df: pd.DataFrame,
    group_cols: list[str],
    context_cols: list[str],
    score_col: str,
    band_col: str,
) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(
            starts=("won", "size"),
            races=("race_key_norm", "nunique"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_field_size_v1=("field_size_v1", "mean"),
        )
        .reset_index()
    )

    track_display = representative_track_name(df, group_cols)
    if not track_display.empty:
        grouped = grouped.merge(track_display, on=group_cols, how="left")

    if context_cols:
        context = (
            df.groupby(context_cols, dropna=False)
            .agg(
                context_starts=("won", "size"),
                context_races=("race_key_norm", "nunique"),
                context_wins=("won", "sum"),
                context_places=("placed", "sum"),
            )
            .reset_index()
        )
        grouped = grouped.merge(context, on=context_cols, how="left")
    else:
        context_starts = len(df)
        context_races = df["race_key_norm"].nunique()
        context_wins = int(df["won"].sum())
        context_places = int(df["placed"].sum())
        grouped["context_starts"] = context_starts
        grouped["context_races"] = context_races
        grouped["context_wins"] = context_wins
        grouped["context_places"] = context_places

    grouped["win_pct"] = np.where(grouped["starts"] > 0, grouped["wins"] / grouped["starts"] * 100.0, np.nan)
    grouped["place_pct"] = np.where(grouped["starts"] > 0, grouped["places"] / grouped["starts"] * 100.0, np.nan)
    grouped["context_win_pct"] = np.where(
        grouped["context_starts"] > 0,
        grouped["context_wins"] / grouped["context_starts"] * 100.0,
        np.nan,
    )
    grouped["context_place_pct"] = np.where(
        grouped["context_starts"] > 0,
        grouped["context_places"] / grouped["context_starts"] * 100.0,
        np.nan,
    )
    grouped["win_pct"] = grouped["win_pct"].round(2)
    grouped["place_pct"] = grouped["place_pct"].round(2)
    grouped["context_win_pct"] = grouped["context_win_pct"].round(2)
    grouped["context_place_pct"] = grouped["context_place_pct"].round(2)
    grouped["win_delta_pct_pts"] = (grouped["win_pct"] - grouped["context_win_pct"]).round(2)
    grouped["place_delta_pct_pts"] = (grouped["place_pct"] - grouped["context_place_pct"]).round(2)
    grouped[score_col] = grouped.apply(
        lambda row: win_place_score(
            row["win_pct"],
            row["place_pct"],
            row["context_win_pct"],
            row["context_place_pct"],
        ),
        axis=1,
    )
    grouped[band_col] = grouped[score_col].map(bias_band)
    for threshold in [50, 100, 300, 500, 1000]:
        grouped[f"sample_ge_{threshold}_v1"] = grouped["starts"] >= threshold
    return grouped


def load_results_base() -> pd.DataFrame:
    df = read_csv("edgeiq_racingcom_results_warehouse_all_v1.csv")
    out = pd.DataFrame()
    out["meeting_date"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["track_raw"] = df["track"].fillna("").astype(str)
    out["track_norm"] = df["track"].map(normalize_track)
    out["race_no"] = safe_num(df["race_no"]).astype("Int64")
    out["race_key_norm"] = (
        out["meeting_date"].fillna("")
        + "|"
        + out["track_norm"].fillna("")
        + "|R"
        + out["race_no"].fillna(0).astype(int).astype(str)
    )
    out["race_key_source"] = df.get("race_key", "")
    out["source_url"] = df.get("source_url", "")
    out["horse"] = df["horseName"].fillna("").astype(str)
    out["horse_key"] = df["horseKey"].fillna("").astype(str)
    out["horse_key_norm"] = df["horseKey"].fillna(df["horseName"]).map(normalize_horse_key)
    out["barrier_num"] = safe_num(df["barrier"])
    out["barrier_bucket_v1"] = out["barrier_num"].map(barrier_bucket)
    out["distance_raw"] = df["distance"].fillna("").astype(str)
    out["distance_m"] = out["distance_raw"].map(parse_distance_m)
    out["distance_band_v1"] = out["distance_m"].map(distance_band_from_meters)
    out["race_class"] = df.get("raceClass", "").fillna("").astype(str)
    out["track_condition_raw"] = df.get("trackCondition", "").fillna("").astype(str)
    out["condition_group_v1"] = out["track_condition_raw"].map(condition_group)
    out["finish_position_num"] = safe_num(df["finishPosition"])
    out = out[out["finish_position_num"].notna()].copy()
    out["won"] = (out["finish_position_num"] == 1).astype(int)
    out["placed"] = ((out["finish_position_num"] >= 1) & (out["finish_position_num"] <= 3)).astype(int)
    out["trainer"] = df.get("trainer", "").fillna("").astype(str)
    out["jockey"] = df.get("jockey", "").fillna("").astype(str)
    out["field_size_v1"] = out.groupby("race_key_norm")["horse_key_norm"].transform("nunique")
    out = out[(out["meeting_date"] != "") & (out["track_norm"] != "") & out["race_no"].notna() & (out["horse_key_norm"] != "")].copy()
    return out


def load_tactical_dna_base() -> pd.DataFrame:
    df = read_csv("edgeiq_tactical_dna_v2.csv")
    out = pd.DataFrame()
    out["horse_key_norm"] = df["horse_key"].map(normalize_horse_key)
    out["run_style_v1"] = df["tactical_speed_bucket_v2"].map(map_run_style)
    out["dna_source"] = df.get("dna_source", "").fillna("").astype(str)
    out["dna_confidence_v2"] = df.get("dna_confidence_v2", "").fillna("").astype(str)
    out["tactical_speed_bucket_v2"] = df.get("tactical_speed_bucket_v2", "").fillna("").astype(str)
    out = out[out["horse_key_norm"] != ""].drop_duplicates(subset=["horse_key_norm"], keep="first")
    return out


def load_results_with_run_style() -> pd.DataFrame:
    results = load_results_base()
    dna = load_tactical_dna_base()
    merged = results.merge(dna, on="horse_key_norm", how="left")
    merged["run_style_v1"] = merged["run_style_v1"].fillna("UNKNOWN")
    merged["dna_source"] = merged["dna_source"].fillna("UNKNOWN")
    merged["dna_confidence_v2"] = merged["dna_confidence_v2"].fillna("UNKNOWN")
    return merged

