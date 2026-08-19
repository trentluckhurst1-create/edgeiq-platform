from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

SETTLED_PATH = DATA_DIR / "edgeiq_execution_tracking_v3_settled.csv"
RUNNER_V6_PATH = DATA_DIR / "edgeiq_runner_score_v6.csv"
DOMINANCE_PATH = DATA_DIR / "edgeiq_dominance_engine_v1.csv"
RANK_GAP_PATH = DATA_DIR / "edgeiq_rank_gap_engine_v1.csv"
TRUST_INDEX_PATH = DATA_DIR / "edgeiq_trust_index_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_live_winner_separation_replay_v2.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_live_winner_separation_replay_v2_summary.csv"
RANKINGS_PATH = DATA_DIR / "edgeiq_live_winner_separation_replay_v2_feature_rankings.csv"

FEATURE_SPECS = [
    {"feature_name": "runner_rank_v6", "feature_family": "HORSE", "feature_type": "numeric"},
    {"feature_name": "runner_score_v6", "feature_family": "HORSE", "feature_type": "numeric"},
    {"feature_name": "dominance_score_v1", "feature_family": "HORSE", "feature_type": "numeric"},
    {"feature_name": "dominance_certainty_band", "feature_family": "HORSE", "feature_type": "ordinal"},
    {"feature_name": "score_share_of_race", "feature_family": "HORSE", "feature_type": "numeric"},
    {"feature_name": "score_share_band", "feature_family": "HORSE", "feature_type": "ordinal"},
    {"feature_name": "score_gap_1_2_v1", "feature_family": "RACE", "feature_type": "numeric"},
    {"feature_name": "score_gap_1_3_v1", "feature_family": "RACE", "feature_type": "numeric"},
    {"feature_name": "trust_profile_v1", "feature_family": "RACE", "feature_type": "ordinal"},
    {"feature_name": "trust_index_v1", "feature_family": "RACE", "feature_type": "numeric"},
    {"feature_name": "edge_pct_v1", "feature_family": "MARKET", "feature_type": "numeric"},
    {"feature_name": "market_price_v1", "feature_family": "MARKET", "feature_type": "numeric"},
]

ORDINAL_MAPS = {
    "dominance_certainty_band": {
        "POOR": 1,
        "WEAK": 2,
        "NEUTRAL": 3,
        "POSITIVE": 4,
        "STRONG": 5,
        "ELITE": 6,
        "UNKNOWN": 0,
    },
    "score_share_band": {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "VERY_HIGH": 4,
        "UNKNOWN": 0,
    },
    "trust_profile_v1": {
        "CHAOTIC": 1,
        "STANDARD": 2,
        "STRONG": 3,
        "ELITE": 4,
        "UNKNOWN": 0,
    },
}

OUTPUT_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "horse",
    "execution_action_v3",
    "trust_profile_v1",
    "trust_index_v1",
    "runner_rank_v6",
    "runner_score_v6",
    "dominance_score_v1",
    "dominance_certainty_band",
    "score_share_of_race",
    "score_share_band",
    "score_gap_1_2_v1",
    "score_gap_1_3_v1",
    "edge_pct_v1",
    "market_price_v1",
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
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM ", "TAB ", "TABTOUCH "]:
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


def build_runner_key(
    df: pd.DataFrame,
    horse_col: str = "horse",
    horse_key_col: str | None = None,
    date_col: str = "meeting_date",
    track_col: str = "track",
    race_col: str = "race_no",
) -> pd.Series:
    if horse_key_col is not None and horse_key_col in df.columns:
        horse_source = df[horse_key_col].where(df[horse_key_col].fillna("").astype(str).str.strip().ne(""), df[horse_col])
    else:
        horse_source = df[horse_col]
    return build_race_key(df, date_col=date_col, track_col=track_col, race_col=race_col) + "|" + horse_source.map(canonical_horse)


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


def cohen_d(winner_values: pd.Series, loser_values: pd.Series) -> float:
    winner_values = pd.to_numeric(winner_values, errors="coerce").dropna()
    loser_values = pd.to_numeric(loser_values, errors="coerce").dropna()
    if winner_values.empty or loser_values.empty:
        return math.nan

    winner_mean = float(winner_values.mean())
    loser_mean = float(loser_values.mean())
    raw_difference = winner_mean - loser_mean

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
    if pd.isna(pooled_sd) or pooled_sd == 0:
        combined = pd.concat([winner_values, loser_values], ignore_index=True)
        fallback_sd = float(combined.std(ddof=1)) if len(combined) > 1 else math.nan
        if pd.isna(fallback_sd) or fallback_sd == 0:
            return math.nan
        return raw_difference / fallback_sd
    return raw_difference / pooled_sd


def mode_with_share(series: pd.Series) -> tuple[str, float]:
    cleaned = series.fillna("").astype(str).map(clean_text)
    cleaned = cleaned[cleaned.ne("")]
    if cleaned.empty:
        return "UNKNOWN", math.nan
    counts = cleaned.value_counts(dropna=False)
    mode_value = str(counts.index[0])
    mode_share = float(counts.iloc[0] / len(cleaned))
    return mode_value, mode_share


def compute_feature_rankings(df: pd.DataFrame) -> pd.DataFrame:
    winners = df[df["won_num_v1"] == 1].copy()
    losers = df[df["won_num_v1"] == 0].copy()
    rows: list[dict[str, object]] = []

    for spec in FEATURE_SPECS:
        feature_name = spec["feature_name"]
        feature_type = spec["feature_type"]
        feature_family = spec["feature_family"]
        if feature_name not in df.columns:
            rows.append(
                {
                    "feature_name": feature_name,
                    "feature_family": feature_family,
                    "feature_type": feature_type,
                    "winner_mean": math.nan,
                    "loser_mean": math.nan,
                    "difference": math.nan,
                    "effect_size": math.nan,
                    "abs_effect_size": math.nan,
                    "winner_mode": "UNAVAILABLE",
                    "loser_mode": "UNAVAILABLE",
                    "winner_mode_share": math.nan,
                    "loser_mode_share": math.nan,
                    "direction": "UNAVAILABLE",
                    "notes": "feature missing from enriched live sample",
                }
            )
            continue

        if feature_type == "numeric":
            winner_values = to_num(winners[feature_name]).dropna()
            loser_values = to_num(losers[feature_name]).dropna()
            winner_mean = float(winner_values.mean()) if not winner_values.empty else math.nan
            loser_mean = float(loser_values.mean()) if not loser_values.empty else math.nan
            difference = winner_mean - loser_mean if not (pd.isna(winner_mean) or pd.isna(loser_mean)) else math.nan
            effect_size = cohen_d(winner_values, loser_values)
            direction = "WINNER_HIGHER" if not pd.isna(difference) and difference > 0 else ("WINNER_LOWER" if not pd.isna(difference) and difference < 0 else "NEUTRAL")
            rows.append(
                {
                    "feature_name": feature_name,
                    "feature_family": feature_family,
                    "feature_type": feature_type,
                    "winner_mean": winner_mean,
                    "loser_mean": loser_mean,
                    "difference": difference,
                    "effect_size": effect_size,
                    "abs_effect_size": abs(effect_size) if not pd.isna(effect_size) else math.nan,
                    "winner_mode": "",
                    "loser_mode": "",
                    "winner_mode_share": math.nan,
                    "loser_mode_share": math.nan,
                    "direction": direction,
                    "notes": "cohen_d on settled winners vs losers",
                }
            )
        else:
            value_map = ORDINAL_MAPS[feature_name]
            winner_raw = winners[feature_name].fillna("").astype(str).map(clean_text).str.upper()
            loser_raw = losers[feature_name].fillna("").astype(str).map(clean_text).str.upper()
            winner_values = winner_raw.map(lambda value: value_map.get(value, value_map.get("UNKNOWN", 0)))
            loser_values = loser_raw.map(lambda value: value_map.get(value, value_map.get("UNKNOWN", 0)))
            winner_mean = float(winner_values.mean()) if not winner_values.empty else math.nan
            loser_mean = float(loser_values.mean()) if not loser_values.empty else math.nan
            difference = winner_mean - loser_mean if not (pd.isna(winner_mean) or pd.isna(loser_mean)) else math.nan
            effect_size = cohen_d(winner_values, loser_values)
            winner_mode, winner_mode_share = mode_with_share(winner_raw)
            loser_mode, loser_mode_share = mode_with_share(loser_raw)
            direction = "WINNER_HIGHER_BAND" if not pd.isna(difference) and difference > 0 else ("WINNER_LOWER_BAND" if not pd.isna(difference) and difference < 0 else "NEUTRAL")
            rows.append(
                {
                    "feature_name": feature_name,
                    "feature_family": feature_family,
                    "feature_type": feature_type,
                    "winner_mean": winner_mean,
                    "loser_mean": loser_mean,
                    "difference": difference,
                    "effect_size": effect_size,
                    "abs_effect_size": abs(effect_size) if not pd.isna(effect_size) else math.nan,
                    "winner_mode": winner_mode,
                    "loser_mode": loser_mode,
                    "winner_mode_share": winner_mode_share,
                    "loser_mode_share": loser_mode_share,
                    "direction": direction,
                    "notes": "ordinal encoding plus mode comparison",
                }
            )

    out = pd.DataFrame(rows)
    out = out.sort_values(["abs_effect_size", "feature_name"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    out["importance_rank"] = range(1, len(out) + 1)
    return out


def decide_conclusion(feature_rankings_df: pd.DataFrame) -> str:
    valid = feature_rankings_df[feature_rankings_df["abs_effect_size"].notna()].copy()
    if valid.empty:
        return "HYBRID"

    family_scores = valid.groupby("feature_family", dropna=False)["abs_effect_size"].mean().to_dict()
    horse_score = float(family_scores.get("HORSE", 0.0))
    race_score = float(family_scores.get("RACE", 0.0))

    top3 = valid.head(3)
    top3_horse = int((top3["feature_family"] == "HORSE").sum())
    top3_race = int((top3["feature_family"] == "RACE").sum())

    if top3_horse >= 2 and horse_score > race_score * 1.15:
        return "HORSE_DRIVEN"
    if top3_race >= 2 and race_score > horse_score * 1.15:
        return "RACE_DRIVEN"
    return "HYBRID"


def feature_effect(feature_rankings_df: pd.DataFrame, feature_name: str) -> float:
    row = feature_rankings_df.loc[feature_rankings_df["feature_name"] == feature_name, "abs_effect_size"]
    if row.empty:
        return math.nan
    return float(row.iloc[0]) if pd.notna(row.iloc[0]) else math.nan


def comparison_answer(left: float, right: float) -> str:
    if pd.isna(left) or pd.isna(right):
        return "NO_DATA"
    return "YES" if left > right else "NO"


def build_summary(df: pd.DataFrame, feature_rankings_df: pd.DataFrame, trust_index_source: str) -> pd.DataFrame:
    winners = df[df["won_num_v1"] == 1].copy()
    losers = df[df["won_num_v1"] == 0].copy()
    top_features = feature_rankings_df[feature_rankings_df["abs_effect_size"].notna()].head(3)
    strongest = top_features.iloc[0]["feature_name"] if len(top_features) >= 1 else "NA"
    second = top_features.iloc[1]["feature_name"] if len(top_features) >= 2 else "NA"
    third = top_features.iloc[2]["feature_name"] if len(top_features) >= 3 else "NA"

    dominance_strength = max(
        [value for value in [feature_effect(feature_rankings_df, "dominance_score_v1"), feature_effect(feature_rankings_df, "dominance_certainty_band")] if not pd.isna(value)],
        default=math.nan,
    )
    score_share_strength = max(
        [value for value in [feature_effect(feature_rankings_df, "score_share_of_race"), feature_effect(feature_rankings_df, "score_share_band")] if not pd.isna(value)],
        default=math.nan,
    )
    trust_strength = max(
        [value for value in [feature_effect(feature_rankings_df, "trust_profile_v1"), feature_effect(feature_rankings_df, "trust_index_v1")] if not pd.isna(value)],
        default=math.nan,
    )
    edge_strength = feature_effect(feature_rankings_df, "edge_pct_v1")
    rank_strength = feature_effect(feature_rankings_df, "runner_rank_v6")

    rows = [
        {"section": "OVERVIEW", "item": "settled_v3_runners", "value": int(len(df)), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "settled V3 rows only"},
        {"section": "OVERVIEW", "item": "winner_runners", "value": int(len(winners)), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "won == 1"},
        {"section": "OVERVIEW", "item": "loser_runners", "value": int(len(losers)), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "won == 0"},
        {"section": "OVERVIEW", "item": "winner_horses", "value": " | ".join(winners["horse"].astype(str).tolist()), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "settled live V3 winners"},
        {"section": "OVERVIEW", "item": "loser_horses", "value": " | ".join(losers["horse"].astype(str).tolist()), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "settled live V3 losers"},
        {"section": "OVERVIEW", "item": "trust_index_source", "value": trust_index_source, "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "numeric trust index backfill source"},
        {"section": "TOP_FEATURES", "item": "strongest_winner_separator", "value": strongest, "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": feature_effect(feature_rankings_df, strongest) if strongest != "NA" else math.nan, "notes": "highest absolute effect size"},
        {"section": "TOP_FEATURES", "item": "second_strongest_separator", "value": second, "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": feature_effect(feature_rankings_df, second) if second != "NA" else math.nan, "notes": "second-highest absolute effect size"},
        {"section": "TOP_FEATURES", "item": "third_strongest_separator", "value": third, "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": feature_effect(feature_rankings_df, third) if third != "NA" else math.nan, "notes": "third-highest absolute effect size"},
        {"section": "COMPARISONS", "item": "dominance_beats_trust_profile", "value": comparison_answer(dominance_strength, feature_effect(feature_rankings_df, "trust_profile_v1")), "winner_value": dominance_strength, "loser_value": feature_effect(feature_rankings_df, "trust_profile_v1"), "difference": dominance_strength - feature_effect(feature_rankings_df, "trust_profile_v1") if not pd.isna(dominance_strength) and not pd.isna(feature_effect(feature_rankings_df, "trust_profile_v1")) else math.nan, "effect_size": math.nan, "notes": "max dominance effect vs trust_profile effect"},
        {"section": "COMPARISONS", "item": "score_share_beats_overlay_size", "value": comparison_answer(score_share_strength, edge_strength), "winner_value": score_share_strength, "loser_value": edge_strength, "difference": score_share_strength - edge_strength if not pd.isna(score_share_strength) and not pd.isna(edge_strength) else math.nan, "effect_size": math.nan, "notes": "max score-share effect vs edge_pct effect"},
        {"section": "COMPARISONS", "item": "runner_rank_beats_edge_pct", "value": comparison_answer(rank_strength, edge_strength), "winner_value": rank_strength, "loser_value": edge_strength, "difference": rank_strength - edge_strength if not pd.isna(rank_strength) and not pd.isna(edge_strength) else math.nan, "effect_size": math.nan, "notes": "runner rank effect vs edge_pct effect"},
        {"section": "CONCLUSION", "item": "final_conclusion", "value": decide_conclusion(feature_rankings_df), "winner_value": math.nan, "loser_value": math.nan, "difference": math.nan, "effect_size": math.nan, "notes": "based on settled live V3 runner effect-size mix"},
    ]

    for row in feature_rankings_df.itertuples(index=False):
        rows.append(
            {
                "section": "FEATURE_DETAIL",
                "item": row.feature_name,
                "value": row.feature_family,
                "winner_value": row.winner_mean,
                "loser_value": row.loser_mean,
                "difference": row.difference,
                "effect_size": row.effect_size,
                "notes": row.notes,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    settled_df = pd.read_csv(SETTLED_PATH, dtype=str, keep_default_na=False)
    runner_df = pd.read_csv(RUNNER_V6_PATH, low_memory=False)
    dominance_df = pd.read_csv(DOMINANCE_PATH, low_memory=False)
    rank_gap_df = pd.read_csv(RANK_GAP_PATH, low_memory=False)

    settled_df = settled_df.copy()
    settled_df = settled_df[settled_df["result_status"].astype(str).str.upper().eq("SETTLED")].copy()
    settled_df["meeting_date"] = settled_df["meeting_date"].astype(str).str[:10]
    settled_df["race_no"] = to_num(settled_df["race_no"]).astype("Int64")
    settled_df["runner_key_v2"] = build_runner_key(settled_df, horse_col="horse")
    settled_df["race_key_v2"] = build_race_key(settled_df)
    settled_df["won_num_v1"] = to_num(settled_df["won"]).fillna(0).astype(int)

    runner_df = runner_df.copy()
    runner_df["meeting_date"] = runner_df["meeting_date"].astype(str).str[:10]
    runner_df["race_no"] = to_num(runner_df["race_no"]).astype("Int64")
    runner_df["runner_key_v2"] = build_runner_key(runner_df, horse_col="horse", horse_key_col="horse_key")
    runner_lookup = runner_df[["runner_key_v2", "runner_score_v6", "runner_rank_v6"]].copy()
    runner_lookup["runner_score_v6"] = to_num(runner_lookup["runner_score_v6"])
    runner_lookup["runner_rank_v6"] = to_num(runner_lookup["runner_rank_v6"])
    runner_lookup = runner_lookup.drop_duplicates("runner_key_v2", keep="first")

    dominance_df = dominance_df.copy()
    dominance_df["meeting_date"] = dominance_df["meeting_date"].astype(str).str[:10]
    dominance_df["race_no"] = to_num(dominance_df["race_no"]).astype("Int64")
    dominance_df["runner_key_v2"] = build_runner_key(dominance_df, horse_col="horse", horse_key_col="horse_key")
    dominance_df["dominance_score_v1"] = to_num(dominance_df["dominance_score_v1"])
    dominance_df["score_share_of_race"] = to_num(dominance_df["score_share_of_race"])

    score_share_thresholds = infer_score_share_thresholds(rank_gap_df)
    dominance_df["dominance_certainty_band"] = dominance_df["dominance_band_v1"].fillna("").astype(str).map(clean_text).str.upper()
    dominance_df["score_share_band"] = dominance_df["score_share_of_race"].map(lambda value: classify_score_share_band(value, score_share_thresholds))

    dominance_lookup = dominance_df[
        ["runner_key_v2", "dominance_score_v1", "dominance_certainty_band", "score_share_of_race", "score_share_band"]
    ].copy()
    dominance_lookup = dominance_lookup.drop_duplicates("runner_key_v2", keep="first")

    rank_gap_df = rank_gap_df.copy()
    rank_gap_df["meeting_date"] = rank_gap_df["meeting_date"].astype(str).str[:10]
    rank_gap_df["race_no"] = to_num(rank_gap_df["race_no"]).astype("Int64")
    rank_gap_df["race_key_v2"] = build_race_key(rank_gap_df)
    rank_gap_lookup = rank_gap_df[["race_key_v2", "gap_1_2", "gap_1_3"]].copy()
    rank_gap_lookup = rank_gap_lookup.rename(columns={"gap_1_2": "score_gap_1_2_v1", "gap_1_3": "score_gap_1_3_v1"})
    rank_gap_lookup["score_gap_1_2_v1"] = to_num(rank_gap_lookup["score_gap_1_2_v1"])
    rank_gap_lookup["score_gap_1_3_v1"] = to_num(rank_gap_lookup["score_gap_1_3_v1"])
    rank_gap_lookup = rank_gap_lookup.drop_duplicates("race_key_v2", keep="first")

    trust_index_source = "UNAVAILABLE"
    trust_index_lookup = pd.DataFrame(columns=["race_key_v2", "trust_index_v1"])
    if TRUST_INDEX_PATH.exists():
        trust_index_df = pd.read_csv(TRUST_INDEX_PATH, low_memory=False)
        trust_index_df = trust_index_df.copy()
        trust_index_df["meeting_date"] = trust_index_df["meeting_date"].astype(str).str[:10]
        trust_index_df["race_no"] = to_num(trust_index_df["race_no"]).astype("Int64")
        trust_index_df["race_key_v2"] = build_race_key(trust_index_df)
        trust_index_lookup = trust_index_df[["race_key_v2", "trust_index_v1"]].copy()
        trust_index_lookup["trust_index_v1"] = to_num(trust_index_lookup["trust_index_v1"])
        trust_index_lookup = trust_index_lookup.drop_duplicates("race_key_v2", keep="first")
        trust_index_source = str(TRUST_INDEX_PATH.name)

    enriched_df = settled_df.merge(runner_lookup, on="runner_key_v2", how="left", suffixes=("", "_runner"))
    enriched_df = enriched_df.merge(dominance_lookup, on="runner_key_v2", how="left")
    enriched_df = enriched_df.merge(rank_gap_lookup, on="race_key_v2", how="left")
    enriched_df = enriched_df.merge(trust_index_lookup, on="race_key_v2", how="left", suffixes=("", "_lookup"))

    enriched_df["runner_score_v6"] = to_num(enriched_df["runner_score_v6"]).fillna(to_num(enriched_df.get("runner_score_v6_runner", pd.Series(dtype=float))))
    enriched_df["runner_rank_v6"] = to_num(enriched_df["runner_rank_v6"]).fillna(to_num(enriched_df.get("runner_rank_v6_runner", pd.Series(dtype=float))))
    if "trust_index_v1_lookup" in enriched_df.columns:
        enriched_df["trust_index_v1"] = to_num(enriched_df["trust_index_v1_lookup"]).fillna(to_num(enriched_df.get("trust_index_v1", pd.Series(dtype=float))))
    else:
        enriched_df["trust_index_v1"] = to_num(enriched_df.get("trust_index_v1", pd.Series(dtype=float)))

    enriched_df["dominance_certainty_band"] = enriched_df["dominance_certainty_band"].fillna("").astype(str).map(clean_text).str.upper()
    enriched_df["score_share_band"] = enriched_df["score_share_band"].fillna("").astype(str).map(clean_text).str.upper()
    enriched_df["trust_profile_v1"] = enriched_df["trust_profile_v1"].fillna("").astype(str).map(clean_text).str.upper()
    enriched_df["edge_pct_v1"] = to_num(enriched_df["edge_pct_v1"])
    enriched_df["market_price_v1"] = to_num(enriched_df["market_price_v1"])
    enriched_df["finish_position"] = to_num(enriched_df["finish_position"])
    enriched_df["won"] = to_num(enriched_df["won"]).fillna(0).astype(int)
    enriched_df["placed"] = to_num(enriched_df["placed"]).fillna(0).astype(int)
    enriched_df["profit_1u_win"] = to_num(enriched_df["profit_1u_win"])

    output_df = enriched_df[OUTPUT_COLUMNS].copy()
    output_df.to_csv(OUTPUT_PATH, index=False)

    feature_rankings_df = compute_feature_rankings(enriched_df)
    feature_rankings_df.to_csv(RANKINGS_PATH, index=False)

    summary_df = build_summary(enriched_df, feature_rankings_df, trust_index_source)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    top_features = feature_rankings_df[feature_rankings_df["abs_effect_size"].notna()].head(8)
    print("[EDGEIQ_LIVE_WINNER_SEPARATION_REPLAY_V2] COMPLETE")
    print(summary_df[summary_df["section"].isin(["OVERVIEW", "TOP_FEATURES", "COMPARISONS", "CONCLUSION"])].to_string(index=False))
    print("\nTop Feature Rankings")
    if top_features.empty:
        print("No valid feature effect sizes were available.")
    else:
        preview_cols = [
            "importance_rank",
            "feature_name",
            "feature_family",
            "feature_type",
            "winner_mean",
            "loser_mean",
            "difference",
            "effect_size",
            "direction",
            "winner_mode",
            "loser_mode",
        ]
        print(top_features[preview_cols].to_string(index=False))


if __name__ == "__main__":
    main()
