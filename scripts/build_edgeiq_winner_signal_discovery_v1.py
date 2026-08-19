from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

SETTLED_PATH = DATA_DIR / "edgeiq_execution_tracking_v2_settled.csv"
RUNNER_V6_PATH = DATA_DIR / "edgeiq_runner_score_v6.csv"
TRUST_PROFILE_PATH = DATA_DIR / "edgeiq_trust_profile_engine_v1.csv"
TRUST_INDEX_PATH = DATA_DIR / "edgeiq_trust_index_v1.csv"
RANK_GAP_PATH = DATA_DIR / "edgeiq_rank_gap_engine_v1.csv"
EXECUTION_ENGINE_V1_PATH = DATA_DIR / "edgeiq_execution_engine_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_winner_signal_discovery_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_winner_signal_discovery_v1_summary.csv"
RANKINGS_PATH = DATA_DIR / "edgeiq_winner_signal_discovery_v1_feature_rankings.csv"

DOMINANCE_WEIGHTS = {
    "score_share_v1": 0.35,
    "dominance_gap_rank2_v1": 0.25,
    "dominance_gap_rank3_v1": 0.20,
    "dominance_vs_avg_v1": 0.20,
}

NUMERIC_FEATURES = [
    ("runner_rank_v6", "lower"),
    ("runner_score_v6", "higher"),
    ("confidence_score_v1", "higher"),
    ("trust_index_v1", "higher"),
    ("dominance_score_v1", "higher"),
    ("score_share_v1", "higher"),
    ("dominance_gap_rank2_v1", "higher"),
    ("dominance_gap_rank3_v1", "higher"),
    ("dominance_vs_avg_v1", "higher"),
    ("score_gap_1_2_v1", "higher"),
    ("score_gap_1_3_v1", "higher"),
    ("edge_pct_v1", "higher"),
    ("historical_profile_top1_rate_v1", "higher"),
    ("historical_trust_band_top1_rate_v1", "higher"),
    ("historical_confidence_proxy_v1", "higher"),
]

CATEGORICAL_FEATURES = [
    "rank_bucket_v1",
    "score_band_v1",
    "governance",
    "trust_profile_v1",
    "trust_band_v1",
    "dominance_certainty",
    "race_dominance_certainty_v1",
    "runner_score_share_band_v1",
    "race_score_share_band_v1",
    "execution_action_v2",
]

DISCOVERY_COLUMNS = [
    "signal_date",
    "meeting_date",
    "track",
    "race_no",
    "horse",
    "execution_action_v2",
    "runner_rank_v6",
    "rank_bucket_v1",
    "runner_score_v6",
    "score_band_v1",
    "confidence_score_v1",
    "trust_index_v1",
    "trust_profile_v1",
    "trust_band_v1",
    "historical_profile_top1_rate_v1",
    "historical_trust_band_top1_rate_v1",
    "historical_confidence_proxy_v1",
    "dominance_score_v1",
    "dominance_certainty",
    "race_dominance_score_v1",
    "race_dominance_certainty_v1",
    "score_share_v1",
    "runner_score_share_band_v1",
    "race_score_share_band_v1",
    "dominance_gap_rank2_v1",
    "dominance_gap_rank3_v1",
    "dominance_vs_avg_v1",
    "score_gap_1_2_v1",
    "score_gap_1_3_v1",
    "edge_pct_v1",
    "market_price_v1",
    "empirical_fair_price_v1",
    "governance",
    "result_status",
    "finish_position",
    "won",
    "placed",
    "profit_1u_win",
]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def fix_mojibake(text: str) -> str:
    if text == "":
        return ""
    if any(ord(ch) > 127 for ch in text):
        try:
            return text.encode("latin1").decode("utf-8")
        except Exception:
            return text
    return text


def normalize_track(value: object) -> str:
    text = fix_mojibake(clean_text(value))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.upper()
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM "]:
        text = text.replace(prefix, "")
    return re.sub(r"[^A-Z0-9]+", "", text)


def canonical_horse(value: object) -> str:
    text = fix_mojibake(clean_text(value))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.upper().strip()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("&", " AND ")
    return re.sub(r"[^A-Z0-9]+", "", text)


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_race_key(df: pd.DataFrame, date_col: str = "meeting_date", track_col: str = "track", race_col: str = "race_no") -> pd.Series:
    race_no = to_num(df[race_col]).fillna(-1).astype(int).astype(str)
    return df[date_col].astype(str).str[:10] + "|" + df[track_col].map(normalize_track) + "|" + race_no


def build_runner_key(df: pd.DataFrame, horse_series: pd.Series, date_col: str = "meeting_date", track_col: str = "track", race_col: str = "race_no") -> pd.Series:
    return build_race_key(df, date_col=date_col, track_col=track_col, race_col=race_col) + "|" + horse_series.map(canonical_horse)


def score_band(score: object) -> str:
    value = pd.to_numeric(score, errors="coerce")
    if pd.isna(value):
        return "UNKNOWN"
    value = float(value)
    if value < 40:
        return "LT_40"
    if value < 45:
        return "40_44"
    if value < 50:
        return "45_49"
    if value < 55:
        return "50_54"
    if value < 60:
        return "55_59"
    if value < 65:
        return "60_64"
    if value < 70:
        return "65_69"
    if value < 75:
        return "70_74"
    if value < 80:
        return "75_79"
    return "80_PLUS"


def rank_bucket(rank: object) -> str:
    value = pd.to_numeric(rank, errors="coerce")
    if pd.isna(value):
        return "UNKNOWN"
    value = int(value)
    if value == 1:
        return "RANK_1"
    if value == 2:
        return "RANK_2"
    if value == 3:
        return "RANK_3"
    if value <= 5:
        return "RANK_4_5"
    if value <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def dominance_band(score: object) -> str:
    value = pd.to_numeric(score, errors="coerce")
    if pd.isna(value):
        return "UNKNOWN"
    value = float(value)
    if value >= 80:
        return "ELITE"
    if value >= 68:
        return "STRONG"
    if value >= 56:
        return "POSITIVE"
    if value >= 44:
        return "NEUTRAL"
    if value >= 32:
        return "WEAK"
    return "POOR"


def midpoint(a: float | None, b: float | None, fallback: float) -> float:
    if a is None and b is None:
        return fallback
    if a is None:
        return float(b)
    if b is None:
        return float(a)
    return (float(a) + float(b)) / 2.0


def infer_score_share_thresholds(rank_gap_df: pd.DataFrame) -> dict[str, float]:
    df = rank_gap_df.copy()
    df["score_share_total"] = to_num(df.get("score_share_total", pd.Series(dtype=float)))
    df["score_share_band"] = df.get("score_share_band", pd.Series(dtype=str)).fillna("").astype(str).str.upper()
    df = df[df["score_share_total"].notna() & df["score_share_band"].ne("")]

    low_values = df.loc[df["score_share_band"] == "LOW", "score_share_total"]
    medium_values = df.loc[df["score_share_band"] == "MEDIUM", "score_share_total"]
    high_values = df.loc[df["score_share_band"] == "HIGH", "score_share_total"]
    very_high_values = df.loc[df["score_share_band"] == "VERY_HIGH", "score_share_total"]

    return {
        "low_to_medium": midpoint(float(low_values.max()) if not low_values.empty else None, float(medium_values.min()) if not medium_values.empty else None, 0.115),
        "medium_to_high": midpoint(float(medium_values.max()) if not medium_values.empty else None, float(high_values.min()) if not high_values.empty else None, 0.18),
        "high_to_very_high": midpoint(float(high_values.max()) if not high_values.empty else None, float(very_high_values.min()) if not very_high_values.empty else None, 0.24),
    }


def classify_score_share_band(value: object, thresholds: dict[str, float]) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    number = float(number)
    if number >= thresholds["high_to_very_high"]:
        return "VERY_HIGH"
    if number >= thresholds["medium_to_high"]:
        return "HIGH"
    if number >= thresholds["low_to_medium"]:
        return "MEDIUM"
    return "LOW"


def empirical_cdf_scaler(reference: pd.Series, values: pd.Series) -> pd.Series:
    ref = pd.to_numeric(reference, errors="coerce").dropna().to_numpy(dtype=float)
    vals = pd.to_numeric(values, errors="coerce")
    if ref.size == 0:
        return pd.Series(np.nan, index=values.index)
    ref = np.sort(ref.copy())
    arr = vals.to_numpy(dtype=float)
    out = np.full(arr.shape, np.nan, dtype=float)
    mask = np.isfinite(arr)
    if mask.any():
        out[mask] = np.searchsorted(ref, arr[mask], side="right") / ref.size
    return pd.Series(out, index=values.index)

def add_live_dominance_features(runner_df: pd.DataFrame) -> pd.DataFrame:
    df = runner_df.copy()
    df["runner_score_v6"] = to_num(df["runner_score_v6"])

    top_scores = (
        df.sort_values(["race_key_v1", "runner_score_v6", "horse"], ascending=[True, False, True])
        .groupby("race_key_v1")["runner_score_v6"]
        .apply(
            lambda s: pd.Series(
                {
                    "score_rank_1": s.iloc[0] if len(s) >= 1 else math.nan,
                    "score_rank_2": s.iloc[1] if len(s) >= 2 else math.nan,
                    "score_rank_3": s.iloc[2] if len(s) >= 3 else math.nan,
                }
            )
        )
        .reset_index()
    )
    top_scores = top_scores.pivot(index="race_key_v1", columns="level_1", values="runner_score_v6").reset_index()
    top_scores.columns.name = None

    race_stats = (
        df.groupby("race_key_v1", dropna=False)
        .agg(
            race_avg_score_v1=("runner_score_v6", "mean"),
            race_total_score_v1=("runner_score_v6", "sum"),
            field_size_v1=("horse", "size"),
        )
        .reset_index()
    )

    df = df.merge(top_scores, on="race_key_v1", how="left")
    df = df.merge(race_stats, on="race_key_v1", how="left")
    df["score_share_v1"] = np.where(
        df["race_total_score_v1"].ne(0) & df["race_total_score_v1"].notna(),
        df["runner_score_v6"] / df["race_total_score_v1"],
        np.nan,
    )
    df["dominance_gap_rank2_v1"] = df["runner_score_v6"] - df["score_rank_2"]
    df["dominance_gap_rank3_v1"] = df["runner_score_v6"] - df["score_rank_3"]
    df["dominance_vs_avg_v1"] = df["runner_score_v6"] - df["race_avg_score_v1"]

    reference = df.copy()
    df["score_share_scaled_v1"] = empirical_cdf_scaler(reference["score_share_v1"], df["score_share_v1"])
    df["gap_rank2_scaled_v1"] = empirical_cdf_scaler(reference["dominance_gap_rank2_v1"], df["dominance_gap_rank2_v1"])
    df["gap_rank3_scaled_v1"] = empirical_cdf_scaler(reference["dominance_gap_rank3_v1"], df["dominance_gap_rank3_v1"])
    df["vs_avg_scaled_v1"] = empirical_cdf_scaler(reference["dominance_vs_avg_v1"], df["dominance_vs_avg_v1"])
    df["dominance_score_v1"] = (
        100.0
        * (
            DOMINANCE_WEIGHTS["score_share_v1"] * df["score_share_scaled_v1"]
            + DOMINANCE_WEIGHTS["dominance_gap_rank2_v1"] * df["gap_rank2_scaled_v1"]
            + DOMINANCE_WEIGHTS["dominance_gap_rank3_v1"] * df["gap_rank3_scaled_v1"]
            + DOMINANCE_WEIGHTS["dominance_vs_avg_v1"] * df["vs_avg_scaled_v1"]
        )
    ).round(3)
    df["dominance_certainty"] = df["dominance_score_v1"].map(dominance_band)
    return df


def safe_lookup_rate(df: pd.DataFrame, key_col: str, value_col: str) -> pd.Series:
    table = (
        df[[key_col, value_col]]
        .copy()
        .dropna(subset=[key_col])
        .groupby(key_col, dropna=False)[value_col]
        .mean()
        .reset_index()
    )
    return table.set_index(key_col)[value_col]


def compute_numeric_feature_rows(df: pd.DataFrame) -> pd.DataFrame:
    winners = df[df["won_num_v1"] == 1].copy()
    losers = df[df["won_num_v1"] == 0].copy()
    rows: list[dict[str, object]] = []

    for feature_name, direction in NUMERIC_FEATURES:
        if feature_name not in df.columns:
            continue
        winner_values = pd.to_numeric(winners[feature_name], errors="coerce").dropna()
        loser_values = pd.to_numeric(losers[feature_name], errors="coerce").dropna()
        if winner_values.empty and loser_values.empty:
            continue

        winner_mean = float(winner_values.mean()) if not winner_values.empty else math.nan
        loser_mean = float(loser_values.mean()) if not loser_values.empty else math.nan
        raw_difference = winner_mean - loser_mean if not (pd.isna(winner_mean) or pd.isna(loser_mean)) else math.nan

        winner_sd = float(winner_values.std(ddof=1)) if len(winner_values) > 1 else math.nan
        loser_sd = float(loser_values.std(ddof=1)) if len(loser_values) > 1 else math.nan
        pooled_num = 0.0
        pooled_den = 0
        if len(winner_values) > 1 and not pd.isna(winner_sd):
            pooled_num += (len(winner_values) - 1) * (winner_sd ** 2)
            pooled_den += len(winner_values) - 1
        if len(loser_values) > 1 and not pd.isna(loser_sd):
            pooled_num += (len(loser_values) - 1) * (loser_sd ** 2)
            pooled_den += len(loser_values) - 1
        pooled_sd = math.sqrt(pooled_num / pooled_den) if pooled_den > 0 else math.nan

        combined_values = pd.to_numeric(df[feature_name], errors="coerce").dropna()
        fallback_sd = float(combined_values.std(ddof=1)) if len(combined_values) > 1 else math.nan
        scale = pooled_sd if not pd.isna(pooled_sd) and pooled_sd > 0 else fallback_sd
        raw_effect = raw_difference / scale if scale and not pd.isna(scale) and scale > 0 else math.nan

        if direction == "lower":
            winner_edge_difference = -raw_difference if not pd.isna(raw_difference) else math.nan
            winner_edge_effect = -raw_effect if not pd.isna(raw_effect) else math.nan
        else:
            winner_edge_difference = raw_difference
            winner_edge_effect = raw_effect

        rows.append(
            {
                "feature_name": feature_name,
                "feature_type": "numeric",
                "feature_value": "",
                "directionality": direction,
                "winner_count": int(len(winner_values)),
                "loser_count": int(len(loser_values)),
                "winner_mean": winner_mean,
                "loser_mean": loser_mean,
                "winner_share": math.nan,
                "loser_share": math.nan,
                "raw_difference": raw_difference,
                "winner_favoring_difference": winner_edge_difference,
                "effect_size": winner_edge_effect,
                "abs_effect_size": abs(winner_edge_effect) if not pd.isna(winner_edge_effect) else math.nan,
                "notes": "positive effect means winner-favoring" if direction == "higher" else "positive effect means lower winner values were favorable",
            }
        )

    out = pd.DataFrame(rows)
    if len(out) > 0:
        out = out.sort_values(["abs_effect_size", "feature_name"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
        out["importance_rank_within_type"] = range(1, len(out) + 1)
    return out


def compute_categorical_feature_rows(df: pd.DataFrame) -> pd.DataFrame:
    winners = df[df["won_num_v1"] == 1].copy()
    losers = df[df["won_num_v1"] == 0].copy()
    winner_total = max(int(len(winners)), 1)
    loser_total = max(int(len(losers)), 1)
    rows: list[dict[str, object]] = []

    for feature_name in CATEGORICAL_FEATURES:
        if feature_name not in df.columns:
            continue
        feature_series = df[feature_name].fillna("").astype(str).map(clean_text)
        values = sorted([value for value in feature_series.unique().tolist() if value != ""])
        for value in values:
            winner_count = int((winners[feature_name].fillna("").astype(str).map(clean_text) == value).sum())
            loser_count = int((losers[feature_name].fillna("").astype(str).map(clean_text) == value).sum())
            winner_share = winner_count / winner_total if winner_total else math.nan
            loser_share = loser_count / loser_total if loser_total else math.nan
            share_difference = winner_share - loser_share if not (pd.isna(winner_share) or pd.isna(loser_share)) else math.nan
            rows.append(
                {
                    "feature_name": feature_name,
                    "feature_type": "categorical",
                    "feature_value": value,
                    "directionality": "winner_share_minus_loser_share",
                    "winner_count": winner_count,
                    "loser_count": loser_count,
                    "winner_mean": math.nan,
                    "loser_mean": math.nan,
                    "winner_share": winner_share,
                    "loser_share": loser_share,
                    "raw_difference": share_difference,
                    "winner_favoring_difference": share_difference,
                    "effect_size": share_difference,
                    "abs_effect_size": abs(share_difference) if not pd.isna(share_difference) else math.nan,
                    "notes": "positive effect means category was overrepresented among winners",
                }
            )

    out = pd.DataFrame(rows)
    if len(out) > 0:
        out = out.sort_values(["abs_effect_size", "feature_name", "feature_value"], ascending=[False, True, True], kind="mergesort").reset_index(drop=True)
        out["importance_rank_within_type"] = range(1, len(out) + 1)
    return out


def build_summary(discovery_df: pd.DataFrame, feature_df: pd.DataFrame) -> pd.DataFrame:
    winners = discovery_df[discovery_df["won_num_v1"] == 1].copy()
    losers = discovery_df[discovery_df["won_num_v1"] == 0].copy()

    rows: list[dict[str, object]] = [
        {"section": "OVERVIEW", "item": "settled_signals", "value": int(len(discovery_df)), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "settled rows only"},
        {"section": "OVERVIEW", "item": "winner_signals", "value": int(len(winners)), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "won == 1"},
        {"section": "OVERVIEW", "item": "loser_signals", "value": int(len(losers)), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "won == 0"},
        {"section": "OVERVIEW", "item": "winner_horses", "value": " | ".join(winners["horse"].astype(str).tolist()), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "current settled winners"},
        {"section": "OVERVIEW", "item": "loser_horses", "value": " | ".join(losers["horse"].astype(str).tolist()), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "current settled losers"},
    ]

    numeric_top = feature_df[feature_df["feature_type"] == "numeric"].head(5)
    for row in numeric_top.itertuples(index=False):
        rows.append(
            {
                "section": "TOP_NUMERIC",
                "item": row.feature_name,
                "value": int(row.importance_rank_within_type),
                "winner_value": row.winner_mean,
                "loser_value": row.loser_mean,
                "difference": row.winner_favoring_difference,
                "effect_size": row.effect_size,
                "notes": row.notes,
            }
        )

    categorical_top = feature_df[feature_df["feature_type"] == "categorical"].head(5)
    for row in categorical_top.itertuples(index=False):
        rows.append(
            {
                "section": "TOP_CATEGORICAL",
                "item": f"{row.feature_name}={row.feature_value}",
                "value": int(row.importance_rank_within_type),
                "winner_value": row.winner_share,
                "loser_value": row.loser_share,
                "difference": row.winner_favoring_difference,
                "effect_size": row.effect_size,
                "notes": row.notes,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    tracking_df = pd.read_csv(SETTLED_PATH, dtype=str, keep_default_na=False)
    runner_df = pd.read_csv(RUNNER_V6_PATH, low_memory=False)
    trust_profile_df = pd.read_csv(TRUST_PROFILE_PATH, low_memory=False)
    trust_index_df = pd.read_csv(TRUST_INDEX_PATH, low_memory=False)
    rank_gap_df = pd.read_csv(RANK_GAP_PATH, low_memory=False)
    historical_exec_df = pd.read_csv(EXECUTION_ENGINE_V1_PATH, low_memory=False)

    tracking_df = tracking_df.copy()
    tracking_df["meeting_date"] = tracking_df["meeting_date"].astype(str).str[:10]
    tracking_df["race_no"] = to_num(tracking_df["race_no"]).astype("Int64")
    tracking_df["won_num_v1"] = to_num(tracking_df["won"]).fillna(0).astype(int)
    tracking_df = tracking_df[tracking_df["result_status"].astype(str).str.upper() == "SETTLED"].copy()
    tracking_df["race_key_v1"] = build_race_key(tracking_df)
    tracking_df["runner_key_v1"] = build_runner_key(tracking_df, tracking_df["horse"])

    runner_df = runner_df.copy()
    date_col = "meeting_date" if "meeting_date" in runner_df.columns else "race_date"
    runner_df[date_col] = runner_df[date_col].astype(str).str[:10]
    runner_df["meeting_date"] = runner_df[date_col]
    runner_df["race_no"] = to_num(runner_df["race_no"]).astype("Int64")
    runner_df["track"] = runner_df["track"].fillna("")
    runner_df["horse"] = runner_df["horse"].fillna("")
    runner_df["race_key_v1"] = build_race_key(runner_df)
    horse_key_series = runner_df["horse_key"] if "horse_key" in runner_df.columns else runner_df["horse"]
    runner_df["runner_key_v1"] = build_runner_key(runner_df, horse_key_series.where(horse_key_series.fillna("").astype(str).str.strip().ne(""), runner_df["horse"]))
    runner_df["runner_score_v6"] = to_num(runner_df.get("runner_score_v6", pd.Series(dtype=float)))
    runner_df["runner_rank_v6"] = to_num(runner_df.get("runner_rank_v6", pd.Series(dtype=float)))
    confidence_source = runner_df["runner_confidence_score_v4"] if "runner_confidence_score_v4" in runner_df.columns else runner_df.get("confidence_adjusted_rating_v6", pd.Series(dtype=float))
    runner_df["confidence_score_v1"] = to_num(confidence_source)
    runner_df["governance"] = runner_df["governance_band_v7_2"].fillna("").astype(str).map(clean_text) if "governance_band_v7_2" in runner_df.columns else "UNKNOWN"
    runner_df = add_live_dominance_features(runner_df)
    score_share_thresholds = infer_score_share_thresholds(rank_gap_df)
    runner_df["runner_score_share_band_v1"] = runner_df["score_share_v1"].map(lambda value: classify_score_share_band(value, score_share_thresholds))
    runner_df["rank_bucket_v1"] = runner_df["runner_rank_v6"].map(rank_bucket)
    runner_df["score_band_v1"] = runner_df["runner_score_v6"].map(score_band)

    runner_lookup_cols = [
        "runner_key_v1",
        "runner_rank_v6",
        "rank_bucket_v1",
        "runner_score_v6",
        "score_band_v1",
        "confidence_score_v1",
        "governance",
        "score_share_v1",
        "runner_score_share_band_v1",
        "dominance_gap_rank2_v1",
        "dominance_gap_rank3_v1",
        "dominance_vs_avg_v1",
        "dominance_score_v1",
        "dominance_certainty",
    ]
    runner_lookup = runner_df[runner_lookup_cols].drop_duplicates("runner_key_v1", keep="first")

    race_score_share_lookup = (
        runner_df.groupby("race_key_v1", dropna=False)["score_share_v1"]
        .max()
        .reset_index(name="race_top_score_share_v1")
    )
    race_score_share_lookup["race_score_share_band_v1"] = race_score_share_lookup["race_top_score_share_v1"].map(
        lambda value: classify_score_share_band(value, score_share_thresholds)
    )

    trust_profile_df = trust_profile_df.copy()
    trust_profile_df["meeting_date"] = trust_profile_df["meeting_date"].astype(str).str[:10]
    trust_profile_df["race_no"] = to_num(trust_profile_df["race_no"]).astype("Int64")
    trust_profile_df["race_key_v1"] = build_race_key(trust_profile_df)
    trust_profile_lookup = trust_profile_df[["race_key_v1", "trust_profile_v1", "historical_top1_profile_v1"]].copy()
    trust_profile_lookup["trust_profile_race_v1"] = trust_profile_lookup["trust_profile_v1"].fillna("").astype(str).map(clean_text)
    trust_profile_lookup["historical_profile_top1_rate_v1"] = to_num(trust_profile_lookup["historical_top1_profile_v1"])
    trust_profile_lookup = trust_profile_lookup[["race_key_v1", "trust_profile_race_v1", "historical_profile_top1_rate_v1"]].drop_duplicates("race_key_v1", keep="first")
    trust_profile_lookup = trust_profile_lookup.merge(
        race_score_share_lookup[["race_key_v1", "race_score_share_band_v1"]],
        on="race_key_v1",
        how="left",
    )

    trust_index_df = trust_index_df.copy()
    trust_index_df["meeting_date"] = trust_index_df["meeting_date"].astype(str).str[:10]
    trust_index_df["race_no"] = to_num(trust_index_df["race_no"]).astype("Int64")
    trust_index_df["race_key_v1"] = build_race_key(trust_index_df)
    trust_index_lookup = trust_index_df[["race_key_v1", "trust_index_v1", "trust_band_v1", "score_gap_1_2", "score_gap_1_3", "dominance_score", "dominance_certainty_band", "historical_top_pick_win_rate_trust_band_v1"]].copy()
    trust_index_lookup["trust_index_race_v1"] = to_num(trust_index_lookup["trust_index_v1"])
    trust_index_lookup["trust_band_race_v1"] = trust_index_lookup["trust_band_v1"].fillna("").astype(str).map(clean_text)
    trust_index_lookup["score_gap_1_2_v1"] = to_num(trust_index_lookup["score_gap_1_2"])
    trust_index_lookup["score_gap_1_3_v1"] = to_num(trust_index_lookup["score_gap_1_3"])
    trust_index_lookup["race_dominance_score_v1"] = to_num(trust_index_lookup["dominance_score"])
    trust_index_lookup["race_dominance_certainty_v1"] = trust_index_lookup["dominance_certainty_band"].fillna("").astype(str).map(clean_text)
    trust_index_lookup["historical_trust_band_top1_rate_v1"] = to_num(trust_index_lookup["historical_top_pick_win_rate_trust_band_v1"])
    trust_index_lookup = trust_index_lookup[["race_key_v1", "trust_index_race_v1", "trust_band_race_v1", "score_gap_1_2_v1", "score_gap_1_3_v1", "race_dominance_score_v1", "race_dominance_certainty_v1", "historical_trust_band_top1_rate_v1"]].drop_duplicates("race_key_v1", keep="first")

    historical_exec_df = historical_exec_df.copy()
    historical_exec_df["won_num_v1"] = to_num(historical_exec_df.get("won", pd.Series(dtype=float))).fillna(0)
    historical_exec_df["rank_bucket_v1"] = historical_exec_df.get("rank_bucket", pd.Series(dtype=str)).fillna("").astype(str).map(clean_text)
    historical_exec_df["trust_profile_v1"] = historical_exec_df.get("trust_profile_v1", pd.Series(dtype=str)).fillna("").astype(str).map(clean_text)
    historical_exec_df["trust_band_v1"] = historical_exec_df.get("trust_band_v1", pd.Series(dtype=str)).fillna("").astype(str).map(clean_text)
    historical_exec_df["race_dominance_certainty_v1"] = historical_exec_df.get("dominance_certainty_band", pd.Series(dtype=str)).fillna("").astype(str).map(clean_text)
    historical_exec_df["race_score_share_band_v1"] = historical_exec_df.get("score_share_band", pd.Series(dtype=str)).fillna("").astype(str).map(clean_text)

    hist_rank_rate = safe_lookup_rate(historical_exec_df, "rank_bucket_v1", "won_num_v1")
    hist_profile_rate = safe_lookup_rate(historical_exec_df, "trust_profile_v1", "won_num_v1")
    hist_trust_band_rate = safe_lookup_rate(historical_exec_df, "trust_band_v1", "won_num_v1")
    hist_dom_rate = safe_lookup_rate(historical_exec_df, "race_dominance_certainty_v1", "won_num_v1")
    hist_score_share_rate = safe_lookup_rate(historical_exec_df, "race_score_share_band_v1", "won_num_v1")

    discovery_df = tracking_df.merge(runner_lookup, on="runner_key_v1", how="left", suffixes=("", "_runner"))
    discovery_df = discovery_df.merge(trust_profile_lookup, on="race_key_v1", how="left")
    discovery_df = discovery_df.merge(trust_index_lookup, on="race_key_v1", how="left")

    discovery_df["runner_rank_v6"] = to_num(discovery_df["runner_rank_v6"]).fillna(to_num(discovery_df.get("runner_rank_v6_runner", pd.Series(dtype=float))))
    discovery_df["runner_score_v6"] = to_num(discovery_df["runner_score_v6"]).fillna(to_num(discovery_df.get("runner_score_v6_runner", pd.Series(dtype=float))))
    discovery_df["trust_profile_v1"] = discovery_df.get("trust_profile_v1", pd.Series(index=discovery_df.index, dtype=object)).fillna("").astype(str)
    discovery_df["trust_profile_v1"] = discovery_df["trust_profile_v1"].where(discovery_df["trust_profile_v1"].str.strip().ne(""), discovery_df.get("trust_profile_race_v1", pd.Series(index=discovery_df.index, dtype=object)))
    discovery_df["trust_profile_v1"] = discovery_df["trust_profile_v1"].fillna("").astype(str).map(clean_text)
    discovery_df["trust_band_v1"] = discovery_df.get("trust_band_v1", pd.Series(index=discovery_df.index, dtype=object)).fillna("").astype(str)
    discovery_df["trust_band_v1"] = discovery_df["trust_band_v1"].where(discovery_df["trust_band_v1"].str.strip().ne(""), discovery_df.get("trust_band_race_v1", pd.Series(index=discovery_df.index, dtype=object)))
    discovery_df["trust_band_v1"] = discovery_df["trust_band_v1"].fillna("").astype(str).map(clean_text)
    discovery_df["trust_index_v1"] = to_num(discovery_df.get("trust_index_v1", pd.Series(index=discovery_df.index, dtype=float))).fillna(to_num(discovery_df.get("trust_index_race_v1", pd.Series(dtype=float))))
    discovery_df["rank_bucket_v1"] = discovery_df["rank_bucket_v1"].fillna("").astype(str).map(clean_text)
    discovery_df["score_band_v1"] = discovery_df["score_band_v1"].fillna("").astype(str).map(clean_text)
    discovery_df["governance"] = discovery_df["governance"].fillna("").astype(str).map(clean_text)
    discovery_df["dominance_certainty"] = discovery_df["dominance_certainty"].fillna("").astype(str).map(clean_text)
    discovery_df["race_dominance_certainty_v1"] = discovery_df["race_dominance_certainty_v1"].fillna("").astype(str).map(clean_text)
    discovery_df["runner_score_share_band_v1"] = discovery_df["runner_score_share_band_v1"].fillna("").astype(str).map(clean_text)
    discovery_df["race_score_share_band_v1"] = discovery_df["race_score_share_band_v1"].fillna("").astype(str).map(clean_text)

    discovery_df["historical_rank_bucket_win_rate_v1"] = discovery_df["rank_bucket_v1"].map(hist_rank_rate)
    discovery_df["historical_structural_profile_win_rate_v1"] = discovery_df["trust_profile_v1"].map(hist_profile_rate)
    discovery_df["historical_structural_trust_band_win_rate_v1"] = discovery_df["trust_band_v1"].map(hist_trust_band_rate)
    discovery_df["historical_structural_dominance_win_rate_v1"] = discovery_df["race_dominance_certainty_v1"].map(hist_dom_rate)
    discovery_df["historical_structural_score_share_win_rate_v1"] = discovery_df["race_score_share_band_v1"].map(hist_score_share_rate)

    proxy_cols = [
        "historical_rank_bucket_win_rate_v1",
        "historical_structural_profile_win_rate_v1",
        "historical_structural_trust_band_win_rate_v1",
        "historical_structural_dominance_win_rate_v1",
        "historical_structural_score_share_win_rate_v1",
        "historical_profile_top1_rate_v1",
        "historical_trust_band_top1_rate_v1",
    ]
    discovery_df["historical_confidence_proxy_v1"] = discovery_df[proxy_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)

    discovery_df["won_num_v1"] = to_num(discovery_df["won"]).fillna(0).astype(int)
    discovery_df["placed_num_v1"] = to_num(discovery_df["placed"]).fillna(0).astype(int)

    discovery_out = discovery_df[DISCOVERY_COLUMNS].copy()
    discovery_out.to_csv(OUTPUT_PATH, index=False)

    numeric_rows = compute_numeric_feature_rows(discovery_df)
    categorical_rows = compute_categorical_feature_rows(discovery_df)
    feature_rankings_df = pd.concat([numeric_rows, categorical_rows], ignore_index=True)
    feature_rankings_df.to_csv(RANKINGS_PATH, index=False)

    summary_df = build_summary(discovery_df, feature_rankings_df)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    print("[EDGEIQ_WINNER_SIGNAL_DISCOVERY_V1] COMPLETE")
    print(f"settled_rows={len(discovery_df)}")
    print(f"winners={int(discovery_df['won_num_v1'].sum())}")
    print(f"losers={int((discovery_df['won_num_v1'] == 0).sum())}")
    print("\nTop Numeric Features")
    if len(numeric_rows) == 0:
        print("No numeric features available.")
    else:
        print(numeric_rows.head(8)[['feature_name','winner_mean','loser_mean','winner_favoring_difference','effect_size']].to_string(index=False))
    print("\nTop Categorical Features")
    if len(categorical_rows) == 0:
        print("No categorical features available.")
    else:
        print(categorical_rows.head(8)[['feature_name','feature_value','winner_share','loser_share','winner_favoring_difference']].to_string(index=False))


if __name__ == "__main__":
    main()


