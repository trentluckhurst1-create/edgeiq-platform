from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
HISTORICAL_DOMINANCE_PATH = DATA / "edgeiq_historical_dominance_replay_v1.csv"
RANK_PROBS_PATH = DATA / "edgeiq_probability_model_v1_rank_probs.csv"
SCORE_PROBS_PATH = DATA / "edgeiq_probability_model_v1_score_probs.csv"

REPLAY_OUT = DATA / "edgeiq_dominance_overlay_replay_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_dominance_overlay_replay_v1_summary.csv"
BY_DOMINANCE_OUT = DATA / "edgeiq_dominance_overlay_replay_v1_by_dominance_band.csv"
BY_SCORE_SHARE_OUT = DATA / "edgeiq_dominance_overlay_replay_v1_by_score_share_band.csv"
BY_DOMINANCE_RANK_OUT = DATA / "edgeiq_dominance_overlay_replay_v1_by_dominance_and_rank.csv"

RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]
DOMINANCE_BAND_ORDER = ["ELITE", "STRONG", "POSITIVE", "NEUTRAL", "WEAK", "POOR"]
SCORE_SHARE_BAND_ORDER = ["VERY_HIGH", "HIGH", "MEDIUM", "LOW"]
OVERLAY_BAND_ORDER = ["50+", "30-50", "20-30", "15-20", "10-15", "5-10", "0-5", "UNDERLAY"]
FEATURE_ORDER_TARGETS = [
    "dominance_score",
    "score_share",
    "runner_rank",
    "runner_score",
    "overlay_proxy",
    "trust_band",
]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def normalize_horse(value: object) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_race_key(df: pd.DataFrame) -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df["track"].map(normalize_track) + "|" + race_no


def build_runner_key(df: pd.DataFrame, horse_series: pd.Series) -> pd.Series:
    return build_race_key(df) + "|" + horse_series.map(normalize_horse)


def rank_bucket(rank_value: object) -> str:
    rank_num = pd.to_numeric(rank_value, errors="coerce")
    if pd.isna(rank_num):
        return "UNKNOWN"
    rank_int = int(rank_num)
    if rank_int == 1:
        return "RANK_1"
    if rank_int == 2:
        return "RANK_2"
    if rank_int == 3:
        return "RANK_3"
    if rank_int <= 5:
        return "RANK_4_5"
    if rank_int <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def score_band(score_value: object) -> str:
    score_num = pd.to_numeric(score_value, errors="coerce")
    if pd.isna(score_num):
        return "UNKNOWN"
    if score_num < 40:
        return "LT_40"
    if score_num < 45:
        return "40_44"
    if score_num < 50:
        return "45_49"
    if score_num < 55:
        return "50_54"
    if score_num < 60:
        return "55_59"
    if score_num < 65:
        return "60_64"
    if score_num < 70:
        return "65_69"
    if score_num < 75:
        return "70_74"
    if score_num < 80:
        return "75_79"
    return "80_PLUS"


def safe_prob(value: float) -> float:
    if pd.isna(value) or value <= 0:
        return 0.0
    return float(value)


def fair_odds(probability: float) -> float:
    probability = safe_prob(probability)
    if probability <= 0:
        return math.nan
    return 1.0 / probability


def softmax_probabilities(scores: pd.Series, temperature: float) -> pd.Series:
    numeric_scores = pd.to_numeric(scores, errors="coerce").fillna(0.0)
    scaled = numeric_scores / max(temperature, 1.0)
    scaled = scaled - scaled.max()
    exp_values = np.exp(scaled)
    denom = exp_values.sum()
    if denom <= 0:
        return pd.Series(np.repeat(1.0 / max(len(scores), 1), len(scores)), index=scores.index)
    return pd.Series(exp_values / denom, index=scores.index)


def overlay_band(edge_value: object) -> str:
    edge = pd.to_numeric(edge_value, errors="coerce")
    if pd.isna(edge) or edge < 0:
        return "UNDERLAY"
    if edge < 5:
        return "0-5"
    if edge < 10:
        return "5-10"
    if edge < 15:
        return "10-15"
    if edge < 20:
        return "15-20"
    if edge < 30:
        return "20-30"
    if edge < 50:
        return "30-50"
    return "50+"


def monotonic_pass(values: list[float]) -> bool:
    filtered = [value for value in values if pd.notna(value)]
    if len(filtered) <= 1:
        return True
    return all(filtered[idx] >= filtered[idx + 1] for idx in range(len(filtered) - 1))


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def score_share_band_from_thresholds(value: object, q25: float, q50: float, q75: float) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number >= q75:
        return "VERY_HIGH"
    if number >= q50:
        return "HIGH"
    if number >= q25:
        return "MEDIUM"
    return "LOW"


def group_summary(df: pd.DataFrame, group_cols: list[str], total_wins: int) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(
            runners=("runner_key_v1", "size"),
            races=("race_key_v1", "nunique"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_finish=("finish_position", "mean"),
            avg_runner_rank=("runner_rank", "mean"),
            avg_runner_score=("runner_score", "mean"),
            avg_dominance_score=("dominance_score_v1", "mean"),
            avg_score_share=("score_share_of_race", "mean"),
            avg_edge_proxy_pct=("edge_proxy_pct", "mean"),
        )
        .reset_index()
    )
    grouped["win_rate"] = grouped.apply(lambda row: safe_rate(row["wins"], row["runners"]), axis=1)
    grouped["place_rate"] = grouped.apply(lambda row: safe_rate(row["places"], row["runners"]), axis=1)
    grouped["winner_capture"] = grouped["wins"].apply(lambda value: safe_rate(value, total_wins))

    winner_rank = (
        df[df["won"] == 1]
        .groupby(group_cols, dropna=False)["runner_rank"]
        .mean()
        .reset_index(name="avg_winner_rank")
    )
    grouped = grouped.merge(winner_rank, on=group_cols, how="left")
    return grouped


def feature_strength(df: pd.DataFrame, feature_name: str, lower_is_better: bool = False) -> tuple[float, str]:
    values = pd.to_numeric(df[feature_name], errors="coerce")
    target = pd.to_numeric(df["won"], errors="coerce")
    mask = values.notna() & target.notna()
    if int(mask.sum()) <= 1:
        return math.nan, "INSUFFICIENT_DATA"
    working = -values[mask] if lower_is_better else values[mask]
    corr = working.corr(target[mask], method="spearman")
    return abs(float(corr)) if pd.notna(corr) else math.nan, "OK"

def main() -> None:
    replay = pd.read_csv(HISTORICAL_REPLAY_PATH, low_memory=False)
    dominance = pd.read_csv(HISTORICAL_DOMINANCE_PATH, low_memory=False)
    rank_probs = pd.read_csv(RANK_PROBS_PATH, low_memory=False)
    score_probs = pd.read_csv(SCORE_PROBS_PATH, low_memory=False)

    replay = replay.copy()
    replay["meeting_date"] = replay["meeting_date"].astype(str).str[:10]
    replay["track"] = replay["track"].fillna("").astype(str).map(clean_text)
    replay["horse"] = replay["horse"].fillna("").astype(str).map(clean_text)
    replay["horse_key"] = replay.get("horse_key", replay["horse"]).fillna("").astype(str)
    replay["race_no"] = to_num(replay["race_no"]).astype("Int64")
    replay["runner_score"] = to_num(replay["runner_score"])
    replay["runner_rank"] = to_num(replay["runner_rank"])
    replay["finish_position"] = to_num(replay["finish_position"])
    replay["won"] = to_num(replay["won"]).fillna(0).astype(int)
    replay["placed"] = replay["finish_position"].le(3).fillna(False).astype(int)
    replay["race_key_v1"] = build_race_key(replay)
    replay["runner_key_v1"] = build_runner_key(replay, replay["horse_key"].where(replay["horse_key"].astype(str).str.strip().ne(""), replay["horse"]))
    replay["field_size"] = replay.groupby("race_key_v1")["horse"].transform("size")
    replay["rank_bucket"] = replay["runner_rank"].map(rank_bucket)
    replay["score_band"] = replay["runner_score"].map(score_band)

    dominance = dominance.copy()
    dominance["meeting_date"] = dominance["meeting_date"].astype(str).str[:10]
    dominance["track"] = dominance["track"].fillna("").astype(str).map(clean_text)
    dominance["horse"] = dominance["horse"].fillna("").astype(str).map(clean_text)
    dominance["horse_key"] = dominance.get("horse_key", dominance["horse"]).fillna("").astype(str)
    dominance["race_no"] = to_num(dominance["race_no"]).astype("Int64")
    dominance["race_key_v1"] = build_race_key(dominance)
    dominance["runner_key_v1"] = build_runner_key(dominance, dominance["horse_key"].where(dominance["horse_key"].astype(str).str.strip().ne(""), dominance["horse"]))
    numeric_cols = [
        "field_size_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "score_rank_1",
        "score_rank_2",
        "score_rank_3",
        "race_avg_score_v1",
        "race_total_score_v1",
        "dominance_gap_rank2",
        "dominance_gap_rank3",
        "dominance_vs_avg",
        "score_share_of_race",
        "dominance_score_v1",
        "dominance_rank_v1",
        "dominance_percentile",
        "finish_position",
        "won",
        "placed",
    ]
    for col in numeric_cols:
        if col in dominance.columns:
            dominance[col] = to_num(dominance[col])
    dominance["dominance_band_v1"] = dominance["dominance_band_v1"].fillna("").astype(str).map(clean_text)
    dominance["dominance_rank_bucket_v1"] = dominance["dominance_rank_bucket_v1"].fillna("").astype(str).map(clean_text)
    dominance["governance_band_hist_v1"] = dominance["governance_band_hist_v1"].fillna("").astype(str).map(clean_text)
    dominance_keep = [
        "runner_key_v1",
        "governance_band_hist_v1",
        "score_rank_1",
        "score_rank_2",
        "score_rank_3",
        "race_avg_score_v1",
        "race_total_score_v1",
        "dominance_gap_rank2",
        "dominance_gap_rank3",
        "dominance_vs_avg",
        "score_share_of_race",
        "dominance_score_v1",
        "dominance_band_v1",
        "dominance_rank_v1",
        "dominance_rank_bucket_v1",
        "dominance_percentile",
    ]
    replay = replay.merge(dominance[dominance_keep].drop_duplicates("runner_key_v1", keep="first"), on="runner_key_v1", how="left")

    q25 = float(replay["score_share_of_race"].quantile(0.25))
    q50 = float(replay["score_share_of_race"].quantile(0.50))
    q75 = float(replay["score_share_of_race"].quantile(0.75))
    replay["score_share_band_v1"] = replay["score_share_of_race"].map(lambda value: score_share_band_from_thresholds(value, q25, q50, q75))

    rank_map = rank_probs[["rank_bucket", "true_win_rate"]].copy().rename(columns={"true_win_rate": "historical_rank_prob"})
    score_map = score_probs[["score_band", "true_win_rate"]].copy().rename(columns={"true_win_rate": "historical_score_band_prob"})
    replay = replay.merge(rank_map, on="rank_bucket", how="left")
    replay = replay.merge(score_map, on="score_band", how="left")

    temperature = float(replay["runner_score"].std())
    if pd.isna(temperature) or temperature <= 0:
        temperature = 15.0

    replay["race_softmax_prob"] = replay.groupby("race_key_v1")["runner_score"].transform(lambda values: softmax_probabilities(values, temperature))
    replay["empirical_probability_raw"] = pd.concat(
        [replay["historical_rank_prob"], replay["historical_score_band_prob"], replay["race_softmax_prob"]], axis=1
    ).mean(axis=1)
    replay["empirical_probability"] = replay["empirical_probability_raw"] / replay.groupby("race_key_v1")["empirical_probability_raw"].transform("sum")
    replay["empirical_probability"] = replay["empirical_probability"].fillna(0.0)
    replay["empirical_fair_odds"] = replay["empirical_probability"].map(fair_odds)
    replay["market_proxy_probability"] = np.where(replay["field_size"].gt(0), 1.0 / replay["field_size"], np.nan)
    replay["market_proxy_fair_odds"] = replay["field_size"].astype(float)
    replay["edge_proxy_pct"] = ((replay["market_proxy_fair_odds"] / replay["empirical_fair_odds"]) - 1.0) * 100.0
    replay["overlay_band"] = replay["edge_proxy_pct"].map(overlay_band)
    replay["positive_overlay_flag"] = replay["edge_proxy_pct"].gt(0).fillna(False)
    replay["dominance_available_flag"] = replay["dominance_score_v1"].notna()
    replay["trust_band"] = "UNAVAILABLE_FROM_INPUTS"

    out_cols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key_v1",
        "horse",
        "horse_key",
        "field_size",
        "runner_score",
        "runner_rank",
        "rank_bucket",
        "score_band",
        "finish_position",
        "won",
        "placed",
        "governance_band_hist_v1",
        "score_rank_1",
        "score_rank_2",
        "score_rank_3",
        "race_avg_score_v1",
        "race_total_score_v1",
        "dominance_gap_rank2",
        "dominance_gap_rank3",
        "dominance_vs_avg",
        "score_share_of_race",
        "score_share_band_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "dominance_rank_v1",
        "dominance_rank_bucket_v1",
        "dominance_percentile",
        "historical_rank_prob",
        "historical_score_band_prob",
        "race_softmax_prob",
        "empirical_probability",
        "empirical_fair_odds",
        "market_proxy_probability",
        "market_proxy_fair_odds",
        "edge_proxy_pct",
        "overlay_band",
        "positive_overlay_flag",
        "dominance_available_flag",
        "trust_band",
    ]
    replay[out_cols].to_csv(REPLAY_OUT, index=False)

    positive_all_df = replay[replay["positive_overlay_flag"]].copy()
    positive_df = positive_all_df[positive_all_df["dominance_available_flag"]].copy()
    positive_wins = int(positive_df["won"].sum())

    by_dominance = group_summary(positive_df, ["dominance_band_v1"], positive_wins)
    by_dominance["dominance_band_v1"] = pd.Categorical(by_dominance["dominance_band_v1"], categories=DOMINANCE_BAND_ORDER, ordered=True)
    by_dominance = by_dominance.sort_values("dominance_band_v1").reset_index(drop=True)
    by_dominance.to_csv(BY_DOMINANCE_OUT, index=False)

    by_score_share = group_summary(positive_df, ["score_share_band_v1"], positive_wins)
    by_score_share["score_share_band_v1"] = pd.Categorical(by_score_share["score_share_band_v1"], categories=SCORE_SHARE_BAND_ORDER, ordered=True)
    by_score_share = by_score_share.sort_values("score_share_band_v1").reset_index(drop=True)
    by_score_share.to_csv(BY_SCORE_SHARE_OUT, index=False)

    by_dominance_rank = group_summary(positive_df, ["dominance_band_v1", "rank_bucket"], positive_wins)
    by_dominance_rank["dominance_band_v1"] = pd.Categorical(by_dominance_rank["dominance_band_v1"], categories=DOMINANCE_BAND_ORDER, ordered=True)
    by_dominance_rank["rank_bucket"] = pd.Categorical(by_dominance_rank["rank_bucket"], categories=RANK_BUCKET_ORDER, ordered=True)
    by_dominance_rank = by_dominance_rank.sort_values(["dominance_band_v1", "rank_bucket"]).reset_index(drop=True)
    by_dominance_rank.to_csv(BY_DOMINANCE_RANK_OUT, index=False)

    by_overlay = group_summary(replay, ["overlay_band"], int(replay["won"].sum()))
    by_overlay["overlay_band"] = pd.Categorical(by_overlay["overlay_band"], categories=OVERLAY_BAND_ORDER, ordered=True)
    by_overlay = by_overlay.sort_values("overlay_band").reset_index(drop=True)

    positive_rank = group_summary(positive_df, ["rank_bucket"], positive_wins)
    positive_rank["rank_bucket"] = pd.Categorical(positive_rank["rank_bucket"], categories=RANK_BUCKET_ORDER, ordered=True)
    positive_rank = positive_rank.sort_values("rank_bucket").reset_index(drop=True)

    high_dom_mask = positive_df["dominance_band_v1"].isin(["ELITE", "STRONG", "POSITIVE"])
    low_dom_mask = positive_df["dominance_band_v1"].isin(["NEUTRAL", "WEAK", "POOR"])
    rank1_df = positive_df[positive_df["runner_rank"] == 1].copy()
    rank2_df = positive_df[positive_df["runner_rank"] == 2].copy()

    q1_high = safe_rate(int(positive_df.loc[high_dom_mask, "won"].sum()), int(high_dom_mask.sum()))
    q1_low = safe_rate(int(positive_df.loc[low_dom_mask, "won"].sum()), int(low_dom_mask.sum()))
    q2_high = safe_rate(int(rank1_df.loc[rank1_df["dominance_band_v1"].isin(["ELITE", "STRONG", "POSITIVE"]), "won"].sum()), int(rank1_df["dominance_band_v1"].isin(["ELITE", "STRONG", "POSITIVE"]).sum()))
    q2_low = safe_rate(int(rank1_df.loc[rank1_df["dominance_band_v1"].isin(["NEUTRAL", "WEAK", "POOR"]), "won"].sum()), int(rank1_df["dominance_band_v1"].isin(["NEUTRAL", "WEAK", "POOR"]).sum()))
    q3_high = safe_rate(int(rank2_df.loc[rank2_df["dominance_band_v1"].isin(["ELITE", "STRONG", "POSITIVE"]), "won"].sum()), int(rank2_df["dominance_band_v1"].isin(["ELITE", "STRONG", "POSITIVE"]).sum()))
    q3_low = safe_rate(int(rank2_df.loc[rank2_df["dominance_band_v1"].isin(["NEUTRAL", "WEAK", "POOR"]), "won"].sum()), int(rank2_df["dominance_band_v1"].isin(["NEUTRAL", "WEAK", "POOR"]).sum()))

    dominance_mono = monotonic_pass(by_dominance["win_rate"].tolist())
    score_share_mono = monotonic_pass(by_score_share["win_rate"].tolist())
    rank_mono = monotonic_pass(positive_rank["win_rate"].tolist())
    overlay_mono = monotonic_pass(by_overlay["win_rate"].tolist())

    best_score_share = by_score_share.dropna(subset=["win_rate"]).sort_values(["win_rate", "runners"], ascending=[False, False]).head(1)
    best_score_share_band = clean_text(best_score_share.iloc[0]["score_share_band_v1"]) if not best_score_share.empty else "UNKNOWN"
    best_score_share_win_rate = float(best_score_share.iloc[0]["win_rate"]) if not best_score_share.empty else math.nan

    feature_rows: list[dict[str, object]] = []
    feature_configs = [
        ("dominance_score", "dominance_score_v1", False),
        ("score_share", "score_share_of_race", False),
        ("runner_rank", "runner_rank", True),
        ("runner_score", "runner_score", False),
        ("overlay_proxy", "edge_proxy_pct", False),
    ]
    for label, col, lower_is_better in feature_configs:
        strength, status = feature_strength(positive_df, col, lower_is_better=lower_is_better)
        feature_rows.append({"feature_name": label, "predictive_strength": strength, "status": status})
    feature_rows.append({"feature_name": "trust_band", "predictive_strength": math.nan, "status": "UNAVAILABLE_FROM_INPUTS"})
    feature_df = pd.DataFrame(feature_rows)
    feature_df["sort_strength"] = feature_df["predictive_strength"].fillna(-1)
    feature_df = feature_df.sort_values(["sort_strength", "feature_name"], ascending=[False, True]).reset_index(drop=True)
    feature_df["feature_order_rank"] = range(1, len(feature_df) + 1)

    score_share_strength = float(feature_df.loc[feature_df["feature_name"] == "score_share", "predictive_strength"].iloc[0])
    overlay_strength = float(feature_df.loc[feature_df["feature_name"] == "overlay_proxy", "predictive_strength"].iloc[0])
    score_share_stronger = score_share_strength > overlay_strength if not (pd.isna(score_share_strength) or pd.isna(overlay_strength)) else False

    summary_rows: list[dict[str, object]] = [
        {"section": "OVERVIEW", "metric": "total_rows", "value": int(len(replay)), "notes": "all historical runners"},
        {"section": "OVERVIEW", "metric": "total_races", "value": int(replay["race_key_v1"].nunique()), "notes": "all historical races"},
        {"section": "OVERVIEW", "metric": "positive_overlay_rows", "value": int(len(positive_all_df)), "notes": "edge_proxy_pct > 0"},
        {"section": "OVERVIEW", "metric": "positive_overlay_rows_dominance_available", "value": int(len(positive_df)), "notes": "positive overlays with dominance data"},
        {"section": "OVERVIEW", "metric": "dominance_missing_rows", "value": int((~replay["dominance_available_flag"]).sum()), "notes": "all replay rows missing dominance data"},
        {"section": "OVERVIEW", "metric": "positive_overlay_races", "value": int(positive_all_df["race_key_v1"].nunique()), "notes": "races with at least one positive overlay runner"},
        {"section": "OVERVIEW", "metric": "positive_overlay_races_dominance_available", "value": int(positive_df["race_key_v1"].nunique()), "notes": "positive overlay races with dominance data"},
        {"section": "OVERVIEW", "metric": "positive_overlay_win_rate", "value": round(float(positive_df["won"].mean()), 6), "notes": "win rate inside dominance-available positive-overlay universe"},
        {"section": "OVERVIEW", "metric": "positive_overlay_place_rate", "value": round(float(positive_df["placed"].mean()), 6), "notes": "place rate inside dominance-available positive-overlay universe"},
        {"section": "QUESTION_1", "metric": "dominance_improves_positive_overlay_win_rate", "value": "YES" if q1_high > q1_low else "NO", "notes": f"high={round(q1_high, 6) if pd.notna(q1_high) else 'NA'} low={round(q1_low, 6) if pd.notna(q1_low) else 'NA'}"},
        {"section": "QUESTION_2", "metric": "dominance_improves_rank1_positive_overlay_win_rate", "value": "YES" if q2_high > q2_low else "NO", "notes": f"high={round(q2_high, 6) if pd.notna(q2_high) else 'NA'} low={round(q2_low, 6) if pd.notna(q2_low) else 'NA'}"},
        {"section": "QUESTION_3", "metric": "dominance_improves_rank2_positive_overlay_win_rate", "value": "YES" if q3_high > q3_low else "NO", "notes": f"high={round(q3_high, 6) if pd.notna(q3_high) else 'NA'} low={round(q3_low, 6) if pd.notna(q3_low) else 'NA'}"},
        {"section": "QUESTION_4", "metric": "best_score_share_band", "value": best_score_share_band, "notes": f"win_rate={round(best_score_share_win_rate, 6) if pd.notna(best_score_share_win_rate) else 'NA'}"},
        {"section": "QUESTION_5", "metric": "score_share_stronger_than_raw_overlay", "value": "YES" if score_share_stronger else "NO", "notes": f"score_share={round(score_share_strength, 6) if pd.notna(score_share_strength) else 'NA'} overlay_proxy={round(overlay_strength, 6) if pd.notna(overlay_strength) else 'NA'}"},
        {"section": "MONOTONICITY", "metric": "dominance_band", "value": "PASS" if dominance_mono else "FAIL", "notes": "positive overlays only"},
        {"section": "MONOTONICITY", "metric": "score_share_band", "value": "PASS" if score_share_mono else "FAIL", "notes": "positive overlays only"},
        {"section": "MONOTONICITY", "metric": "rank_bucket", "value": "PASS" if rank_mono else "FAIL", "notes": "positive overlays only"},
        {"section": "MONOTONICITY", "metric": "overlay_band", "value": "PASS" if overlay_mono else "FAIL", "notes": "all runners"},
        {"section": "FEATURE_ORDERING", "metric": "ordering_metric", "value": "ABS_SPEARMAN_WITH_WIN_ON_POSITIVE_OVERLAYS", "notes": "higher means more predictive"},
    ]

    for row in feature_df.itertuples(index=False):
        summary_rows.append(
            {
                "section": "FEATURE_ORDERING",
                "metric": f"rank_{int(row.feature_order_rank)}",
                "value": row.feature_name,
                "notes": f"strength={round(row.predictive_strength, 6) if pd.notna(row.predictive_strength) else 'NA'} status={row.status}",
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_OUT, index=False)

    print("[EDGEIQ_DOMINANCE_OVERLAY_REPLAY_V1] COMPLETE")
    print(summary_df.to_string(index=False))
    print("\nBy Dominance Band")
    print(by_dominance.to_string(index=False))
    print("\nBy Score Share Band")
    print(by_score_share.to_string(index=False))
    print("\nBy Dominance And Rank")
    print(by_dominance_rank.to_string(index=False))


if __name__ == "__main__":
    main()

