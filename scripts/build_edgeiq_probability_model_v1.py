from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

MARKET_PROXY = DATA / "edgeiq_replay_market_proxy_v1.csv"
HISTORICAL_REPLAY = DATA / "edgeiq_historical_replay_v1.csv"
RUNNER_SCORE_V5 = DATA / "edgeiq_runner_score_v5.csv"
RUNNER_SCORE_V6 = DATA / "edgeiq_runner_score_v6.csv"

RANK_OUT = DATA / "edgeiq_probability_model_v1_rank_probs.csv"
SCORE_OUT = DATA / "edgeiq_probability_model_v1_score_probs.csv"
CALIBRATION_OUT = DATA / "edgeiq_probability_model_v1_calibration.csv"
FAIR_PRICE_OUT = DATA / "edgeiq_fair_price_empirical_v1.csv"

RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]
SCORE_BAND_ORDER = ["LT_40", "40_44", "45_49", "50_54", "55_59", "60_64", "65_69", "70_74", "75_79", "80_PLUS"]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def upper_text(value: object) -> str:
    return clean_text(value).upper()


def canon_horse(value: object) -> str:
    text = upper_text(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def rank_bucket(rank_value: object) -> str:
    rank_num = pd.to_numeric(rank_value, errors="coerce")
    if pd.isna(rank_num):
        return "NO_RANK"
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


def confidence_band(sample_size: int) -> str:
    if sample_size >= 10000:
        return "VERY_HIGH"
    if sample_size >= 5000:
        return "HIGH"
    if sample_size >= 1000:
        return "MEDIUM"
    if sample_size >= 250:
        return "LOW"
    return "VERY_LOW"


def safe_prob(value: float) -> float:
    if pd.isna(value) or value <= 0:
        return 0.0
    return float(value)


def fair_odds(probability: float) -> float:
    probability = safe_prob(probability)
    if probability <= 0:
        return math.nan
    return 1.0 / probability


def build_probability_table(df: pd.DataFrame, group_cols: list[str], label_mode: str) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(
            runners=("race_key", "size"),
            wins=("won", "sum"),
            sample_size=("race_key", "nunique"),
        )
        .reset_index()
    )
    grouped["true_win_rate"] = (grouped["wins"] / grouped["runners"]).round(6)
    grouped["fair_odds"] = grouped["true_win_rate"].apply(fair_odds).round(4)
    grouped["confidence_band"] = grouped["sample_size"].astype(int).apply(confidence_band)

    if label_mode == "rank":
        grouped["score_band"] = ""
        grouped["rank_bucket"] = pd.Categorical(grouped["rank_bucket"], categories=RANK_BUCKET_ORDER, ordered=True)
        grouped = grouped.sort_values("rank_bucket").reset_index(drop=True)
    elif label_mode == "score":
        grouped["rank_bucket"] = ""
        grouped["score_band"] = pd.Categorical(grouped["score_band"], categories=SCORE_BAND_ORDER, ordered=True)
        grouped = grouped.sort_values("score_band").reset_index(drop=True)
    else:
        grouped["rank_bucket"] = pd.Categorical(grouped["rank_bucket"], categories=RANK_BUCKET_ORDER, ordered=True)
        grouped["score_band"] = pd.Categorical(grouped["score_band"], categories=SCORE_BAND_ORDER, ordered=True)
        grouped = grouped.sort_values(["rank_bucket", "score_band"]).reset_index(drop=True)

    keep = ["rank_bucket", "score_band", "runners", "wins", "true_win_rate", "fair_odds", "sample_size", "confidence_band"]
    return grouped[keep].copy()


def prepare_training() -> tuple[pd.DataFrame, float]:
    if not MARKET_PROXY.exists():
        raise FileNotFoundError(f"Missing market proxy file: {MARKET_PROXY}")
    if not HISTORICAL_REPLAY.exists():
        raise FileNotFoundError(f"Missing historical replay file: {HISTORICAL_REPLAY}")

    proxy = pd.read_csv(MARKET_PROXY, low_memory=False, usecols=["race_key", "horse_key", "runner_score", "runner_rank", "won", "rank_bucket", "score_band"])
    replay = pd.read_csv(HISTORICAL_REPLAY, low_memory=False, usecols=["race_key", "horse_key", "runner_score", "runner_rank", "won"])

    replay["race_key"] = replay["race_key"].astype(str).str.strip()
    replay["horse_key"] = replay["horse_key"].astype(str).str.strip()
    replay["runner_score"] = pd.to_numeric(replay["runner_score"], errors="coerce")
    replay["runner_rank"] = pd.to_numeric(replay["runner_rank"], errors="coerce")
    replay["won"] = pd.to_numeric(replay["won"], errors="coerce").fillna(0).astype(int)

    proxy["race_key"] = proxy["race_key"].astype(str).str.strip()
    proxy["horse_key"] = proxy["horse_key"].astype(str).str.strip()
    proxy["runner_score"] = pd.to_numeric(proxy["runner_score"], errors="coerce")
    proxy["runner_rank"] = pd.to_numeric(proxy["runner_rank"], errors="coerce")
    proxy["won"] = pd.to_numeric(proxy["won"], errors="coerce").fillna(0).astype(int)

    if len(proxy) != len(replay):
        raise RuntimeError(f"Training row mismatch: market_proxy={len(proxy)} replay={len(replay)}")

    train = proxy.copy()
    train["rank_bucket"] = train["rank_bucket"].fillna("").astype(str).replace({"": None})
    train["score_band"] = train["score_band"].fillna("").astype(str).replace({"": None})
    train["rank_bucket"] = train["rank_bucket"].where(train["rank_bucket"].notna(), train["runner_rank"].apply(rank_bucket))
    train["score_band"] = train["score_band"].where(train["score_band"].notna(), train["runner_score"].apply(score_band))

    temperature = float(pd.to_numeric(replay["runner_score"], errors="coerce").std())
    if pd.isna(temperature) or temperature <= 0:
        temperature = 15.0

    return train, temperature


def softmax_probabilities(scores: pd.Series, temperature: float) -> pd.Series:
    numeric_scores = pd.to_numeric(scores, errors="coerce").fillna(0.0)
    scaled = numeric_scores / max(temperature, 1.0)
    scaled = scaled - scaled.max()
    exp_values = np.exp(scaled)
    denom = exp_values.sum()
    if denom <= 0:
        return pd.Series(np.repeat(1.0 / max(len(scores), 1), len(scores)), index=scores.index)
    return pd.Series(exp_values / denom, index=scores.index)


def load_current_model(path: Path, score_col: str, rank_col: str) -> pd.DataFrame:
    usecols = ["meeting_date", "track", "race_no", "horse", "horse_key", score_col, rank_col]
    df = pd.read_csv(path, low_memory=False, usecols=usecols)
    df["meeting_date"] = df["meeting_date"].astype(str).str.slice(0, 10)
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df[score_col] = pd.to_numeric(df[score_col], errors="coerce")
    df[rank_col] = pd.to_numeric(df[rank_col], errors="coerce")
    df["race_key_empirical_v1"] = df["meeting_date"].astype(str) + "|" + df["track"].astype(str) + "|R" + df["race_no"].astype(str)
    df["horse_key_empirical_v1"] = df["horse_key"].fillna(df["horse"].map(canon_horse)).astype(str)
    return df


def prepare_current_model(path: Path, score_col: str, rank_col: str, model_label: str, temperature: float, rank_probs: pd.DataFrame, score_probs: pd.DataFrame, calibration: pd.DataFrame) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing current runner score file: {path}")

    df = load_current_model(path, score_col, rank_col)
    df = df.assign(
        rank_bucket_empirical_v1=df[rank_col].apply(rank_bucket),
        score_band_empirical_v1=df[score_col].apply(score_band),
        model_source_v1=model_label,
    )

    rank_map = rank_probs.rename(columns={
        "true_win_rate": "rank_true_win_rate_v1",
        "fair_odds": "rank_fair_odds_v1",
        "sample_size": "rank_sample_size_v1",
        "confidence_band": "rank_confidence_band_v1",
    })[["rank_bucket", "rank_true_win_rate_v1", "rank_fair_odds_v1", "rank_sample_size_v1", "rank_confidence_band_v1"]]

    score_map = score_probs.rename(columns={
        "true_win_rate": "score_true_win_rate_v1",
        "fair_odds": "score_fair_odds_v1",
        "sample_size": "score_sample_size_v1",
        "confidence_band": "score_confidence_band_v1",
    })[["score_band", "score_true_win_rate_v1", "score_fair_odds_v1", "score_sample_size_v1", "score_confidence_band_v1"]]

    calibration_map = calibration.rename(columns={
        "true_win_rate": "calibration_true_win_rate_v1",
        "fair_odds": "calibration_fair_odds_v1",
        "sample_size": "calibration_sample_size_v1",
        "confidence_band": "calibration_confidence_band_v1",
    })[["rank_bucket", "score_band", "calibration_true_win_rate_v1", "calibration_fair_odds_v1", "calibration_sample_size_v1", "calibration_confidence_band_v1"]]

    df = df.merge(rank_map, left_on="rank_bucket_empirical_v1", right_on="rank_bucket", how="left")
    df = df.drop(columns=["rank_bucket"])
    df = df.merge(score_map, left_on="score_band_empirical_v1", right_on="score_band", how="left")
    df = df.drop(columns=["score_band"])
    df = df.merge(calibration_map, left_on=["rank_bucket_empirical_v1", "score_band_empirical_v1"], right_on=["rank_bucket", "score_band"], how="left")
    df = df.drop(columns=["rank_bucket", "score_band"]).copy()

    softmax_series = df.groupby("race_key_empirical_v1")[score_col].transform(lambda values: softmax_probabilities(values, temperature))
    raw_blend_series = pd.concat(
        [df["rank_true_win_rate_v1"], df["score_true_win_rate_v1"], softmax_series],
        axis=1,
    ).mean(axis=1)
    norm_blend_series = raw_blend_series / raw_blend_series.groupby(df["race_key_empirical_v1"]).transform("sum")

    df = df.assign(
        within_race_softmax_prob_v1=softmax_series.fillna(0.0),
        blended_prob_raw_v1=raw_blend_series.fillna(0.0),
        blended_prob_norm_v1=norm_blend_series.fillna(0.0),
    )
    df["empirical_fair_odds_v1"] = df["blended_prob_norm_v1"].apply(fair_odds)

    keep = [
        "meeting_date",
        "track",
        "race_no",
        "race_key_empirical_v1",
        "horse",
        "horse_key_empirical_v1",
        "model_source_v1",
        score_col,
        rank_col,
        "rank_bucket_empirical_v1",
        "score_band_empirical_v1",
        "rank_true_win_rate_v1",
        "score_true_win_rate_v1",
        "calibration_true_win_rate_v1",
        "within_race_softmax_prob_v1",
        "blended_prob_raw_v1",
        "blended_prob_norm_v1",
        "empirical_fair_odds_v1",
        "rank_sample_size_v1",
        "score_sample_size_v1",
        "calibration_sample_size_v1",
        "rank_confidence_band_v1",
        "score_confidence_band_v1",
        "calibration_confidence_band_v1",
    ]
    out = df[[col for col in keep if col in df.columns]].copy()
    out = out.rename(columns={
        score_col: "runner_score_model_v1",
        rank_col: "runner_rank_model_v1",
    })
    return out


def main() -> None:
    train, temperature = prepare_training()

    rank_probs = build_probability_table(train, ["rank_bucket"], "rank")
    score_probs = build_probability_table(train, ["score_band"], "score")
    calibration = build_probability_table(train, ["rank_bucket", "score_band"], "calibration")

    rank_probs.to_csv(RANK_OUT, index=False)
    score_probs.to_csv(SCORE_OUT, index=False)
    calibration.to_csv(CALIBRATION_OUT, index=False)

    current_v5 = prepare_current_model(RUNNER_SCORE_V5, "runner_score_v5", "runner_rank_v5", "V5", temperature, rank_probs, score_probs, calibration)
    current_v6 = prepare_current_model(RUNNER_SCORE_V6, "runner_score_v6", "runner_rank_v6", "V6", temperature, rank_probs, score_probs, calibration)

    wide_keys = ["meeting_date", "track", "race_no", "race_key_empirical_v1", "horse", "horse_key_empirical_v1"]
    v5_wide = current_v5.drop(columns=["model_source_v1"]).rename(columns={
        "runner_score_model_v1": "runner_score_v5_empirical_v1",
        "runner_rank_model_v1": "runner_rank_v5_empirical_v1",
        "rank_bucket_empirical_v1": "rank_bucket_v5_empirical_v1",
        "score_band_empirical_v1": "score_band_v5_empirical_v1",
        "rank_true_win_rate_v1": "rank_prob_v5_empirical_v1",
        "score_true_win_rate_v1": "score_prob_v5_empirical_v1",
        "calibration_true_win_rate_v1": "calibration_prob_v5_empirical_v1",
        "within_race_softmax_prob_v1": "softmax_prob_v5_empirical_v1",
        "blended_prob_raw_v1": "blended_prob_raw_v5_empirical_v1",
        "blended_prob_norm_v1": "blended_prob_norm_v5_empirical_v1",
        "empirical_fair_odds_v1": "fair_odds_v5_empirical_v1",
        "rank_sample_size_v1": "rank_sample_size_v5_empirical_v1",
        "score_sample_size_v1": "score_sample_size_v5_empirical_v1",
        "calibration_sample_size_v1": "calibration_sample_size_v5_empirical_v1",
        "rank_confidence_band_v1": "rank_confidence_v5_empirical_v1",
        "score_confidence_band_v1": "score_confidence_v5_empirical_v1",
        "calibration_confidence_band_v1": "calibration_confidence_v5_empirical_v1",
    })

    v6_wide = current_v6.drop(columns=["model_source_v1"]).rename(columns={
        "runner_score_model_v1": "runner_score_v6_empirical_v1",
        "runner_rank_model_v1": "runner_rank_v6_empirical_v1",
        "rank_bucket_empirical_v1": "rank_bucket_v6_empirical_v1",
        "score_band_empirical_v1": "score_band_v6_empirical_v1",
        "rank_true_win_rate_v1": "rank_prob_v6_empirical_v1",
        "score_true_win_rate_v1": "score_prob_v6_empirical_v1",
        "calibration_true_win_rate_v1": "calibration_prob_v6_empirical_v1",
        "within_race_softmax_prob_v1": "softmax_prob_v6_empirical_v1",
        "blended_prob_raw_v1": "blended_prob_raw_v6_empirical_v1",
        "blended_prob_norm_v1": "blended_prob_norm_v6_empirical_v1",
        "empirical_fair_odds_v1": "fair_odds_v6_empirical_v1",
        "rank_sample_size_v1": "rank_sample_size_v6_empirical_v1",
        "score_sample_size_v1": "score_sample_size_v6_empirical_v1",
        "calibration_sample_size_v1": "calibration_sample_size_v6_empirical_v1",
        "rank_confidence_band_v1": "rank_confidence_v6_empirical_v1",
        "score_confidence_band_v1": "score_confidence_v6_empirical_v1",
        "calibration_confidence_band_v1": "calibration_confidence_v6_empirical_v1",
    })

    fair_price = v5_wide.merge(v6_wide, on=wide_keys, how="outer")
    fair_price["active_empirical_model_v1"] = np.where(
        fair_price["runner_score_v6_empirical_v1"].notna(),
        "V6",
        "V5",
    )
    fair_price["active_blended_prob_empirical_v1"] = np.where(
        fair_price["active_empirical_model_v1"].eq("V6"),
        fair_price["blended_prob_norm_v6_empirical_v1"],
        fair_price["blended_prob_norm_v5_empirical_v1"],
    )
    fair_price["active_fair_odds_empirical_v1"] = np.where(
        fair_price["active_empirical_model_v1"].eq("V6"),
        fair_price["fair_odds_v6_empirical_v1"],
        fair_price["fair_odds_v5_empirical_v1"],
    )
    fair_price["softmax_temperature_v1"] = round(float(temperature), 4)

    fair_price = fair_price.sort_values(["meeting_date", "track", "race_no", "active_fair_odds_empirical_v1", "horse"]).reset_index(drop=True)
    fair_price.to_csv(FAIR_PRICE_OUT, index=False)

    print("[EDGEIQ_PROBABILITY_MODEL_V1] COMPLETE")
    print(f"training_rows={len(train)}")
    print(f"training_races={train['race_key'].nunique()}")
    print(f"softmax_temperature_v1={round(float(temperature), 4)}")
    print(f"rank_rows={len(rank_probs)}")
    print(f"score_rows={len(score_probs)}")
    print(f"calibration_rows={len(calibration)}")
    print(f"fair_price_rows={len(fair_price)}")
    print(f"rank_out={RANK_OUT}")
    print(f"score_out={SCORE_OUT}")
    print(f"calibration_out={CALIBRATION_OUT}")
    print(f"fair_price_out={FAIR_PRICE_OUT}")


if __name__ == "__main__":
    main()
