from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

REQUESTED_REPLAY_MASTER_PATH = DATA_DIR / "edgeiq_historical_replay_master_v1.csv"
FALLBACK_REPLAY_PATH = DATA_DIR / "edgeiq_historical_replay_v1.csv"

REQUESTED_DOMINANCE_PATH = DATA_DIR / "edgeiq_dominance_engine_v1.csv"
FALLBACK_HISTORICAL_DOMINANCE_PATH = DATA_DIR / "edgeiq_historical_dominance_replay_v1.csv"

RANK_PROBS_PATH = DATA_DIR / "edgeiq_probability_model_v1_rank_probs.csv"
SCORE_PROBS_PATH = DATA_DIR / "edgeiq_probability_model_v1_score_probs.csv"
FAIR_PRICE_EMPIRICAL_PATH = DATA_DIR / "edgeiq_fair_price_empirical_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_real_vs_fake_overlay_replay_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_real_vs_fake_overlay_replay_v1_summary.csv"
BY_DOMINANCE_PATH = DATA_DIR / "edgeiq_real_vs_fake_overlay_replay_v1_by_dominance.csv"
BY_SCORE_SHARE_PATH = DATA_DIR / "edgeiq_real_vs_fake_overlay_replay_v1_by_score_share.csv"

RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]
DOMINANCE_BAND_ORDER = ["ELITE", "STRONG", "POSITIVE", "NEUTRAL", "WEAK", "POOR", "UNKNOWN"]
SCORE_SHARE_BAND_ORDER = ["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
OVERLAY_BAND_ORDER = ["50+", "30-50", "20-30", "15-20", "10-15", "5-10", "0-5", "UNDERLAY"]

OUTPUT_COLUMNS = [
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
    "overlay_truth_v1",
    "dominance_score_v1",
    "dominance_band_v1",
    "score_share_of_race",
    "score_share_band_v1",
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


def normalize_horse(value: object) -> str:
    text = fix_mojibake(clean_text(value))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.upper().strip()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("&", " AND ")
    return re.sub(r"[^A-Z0-9]+", "", text)


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_race_key(df: pd.DataFrame, track_col: str = "track", race_col: str = "race_no", date_col: str = "meeting_date") -> pd.Series:
    race_no = to_num(df[race_col]).fillna(-1).astype(int).astype(str)
    return df[date_col].astype(str).str[:10] + "|" + df[track_col].map(normalize_track) + "|" + race_no


def build_runner_key(
    df: pd.DataFrame,
    horse_series: pd.Series,
    track_col: str = "track",
    race_col: str = "race_no",
    date_col: str = "meeting_date",
) -> pd.Series:
    return build_race_key(df, track_col=track_col, race_col=race_col, date_col=date_col) + "|" + horse_series.map(normalize_horse)


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


def score_share_band_from_quantiles(value: object, q25: float, q50: float, q75: float) -> str:
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


def monotonic_pass(values: list[float]) -> bool:
    filtered = [value for value in values if pd.notna(value)]
    if len(filtered) <= 1:
        return True
    return all(filtered[idx] >= filtered[idx + 1] for idx in range(len(filtered) - 1))


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def cohen_d(real_values: pd.Series, fake_values: pd.Series) -> float:
    real_values = pd.to_numeric(real_values, errors="coerce").dropna()
    fake_values = pd.to_numeric(fake_values, errors="coerce").dropna()
    if real_values.empty or fake_values.empty:
        return math.nan

    real_mean = float(real_values.mean())
    fake_mean = float(fake_values.mean())
    raw_difference = real_mean - fake_mean

    real_sd = float(real_values.std(ddof=1)) if len(real_values) > 1 else math.nan
    fake_sd = float(fake_values.std(ddof=1)) if len(fake_values) > 1 else math.nan

    pooled_num = 0.0
    pooled_den = 0
    if len(real_values) > 1 and not pd.isna(real_sd):
        pooled_num += (len(real_values) - 1) * (real_sd ** 2)
        pooled_den += len(real_values) - 1
    if len(fake_values) > 1 and not pd.isna(fake_sd):
        pooled_num += (len(fake_values) - 1) * (fake_sd ** 2)
        pooled_den += len(fake_values) - 1

    pooled_sd = math.sqrt(pooled_num / pooled_den) if pooled_den > 0 else math.nan
    if pd.isna(pooled_sd) or pooled_sd == 0:
        combined = pd.concat([real_values, fake_values], ignore_index=True)
        fallback_sd = float(combined.std(ddof=1)) if len(combined) > 1 else math.nan
        if pd.isna(fallback_sd) or fallback_sd == 0:
            return math.nan
        return raw_difference / fallback_sd
    return raw_difference / pooled_sd


def group_summary(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(
            overlay_runners=("runner_key_v1", "size"),
            overlay_races=("race_key_v1", "nunique"),
            real_overlay_wins=("won", "sum"),
            fake_overlay_losses=("won", lambda values: int((1 - values).sum())),
            places=("placed", "sum"),
            avg_runner_rank=("runner_rank", "mean"),
            avg_runner_score=("runner_score", "mean"),
            avg_dominance_score=("dominance_score_v1", "mean"),
            avg_score_share=("score_share_of_race", "mean"),
            avg_edge_proxy_pct=("edge_proxy_pct", "mean"),
        )
        .reset_index()
    )
    grouped["real_overlay_win_rate"] = grouped.apply(lambda row: safe_rate(row["real_overlay_wins"], row["overlay_runners"]), axis=1)
    grouped["place_rate"] = grouped.apply(lambda row: safe_rate(row["places"], row["overlay_runners"]), axis=1)
    return grouped


def summarize_feature_effects(overlay_df: pd.DataFrame) -> pd.DataFrame:
    real_df = overlay_df[overlay_df["overlay_truth_v1"] == "REAL_OVERLAY"].copy()
    fake_df = overlay_df[overlay_df["overlay_truth_v1"] == "FAKE_OVERLAY"].copy()
    rows = []
    feature_specs = [
        ("dominance_score_v1", "DOMINANCE"),
        ("score_share_of_race", "SCORE_SHARE"),
        ("runner_rank", "RANK"),
        ("runner_score", "RUNNER_SCORE"),
        ("edge_proxy_pct", "OVERLAY_SIZE"),
    ]
    for feature_name, feature_family in feature_specs:
        real_values = pd.to_numeric(real_df[feature_name], errors="coerce").dropna()
        fake_values = pd.to_numeric(fake_df[feature_name], errors="coerce").dropna()
        winner_mean = float(real_values.mean()) if not real_values.empty else math.nan
        loser_mean = float(fake_values.mean()) if not fake_values.empty else math.nan
        difference = winner_mean - loser_mean if not (pd.isna(winner_mean) or pd.isna(loser_mean)) else math.nan
        effect_size = cohen_d(real_values, fake_values)
        rows.append(
            {
                "feature_name": feature_name,
                "feature_family": feature_family,
                "winner_mean": winner_mean,
                "loser_mean": loser_mean,
                "difference": difference,
                "effect_size": effect_size,
                "abs_effect_size": abs(effect_size) if not pd.isna(effect_size) else math.nan,
            }
        )
    out = pd.DataFrame(rows)
    out = out.sort_values(["abs_effect_size", "feature_name"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    out["importance_rank"] = range(1, len(out) + 1)
    return out


def main() -> None:
    replay_path = REQUESTED_REPLAY_MASTER_PATH if REQUESTED_REPLAY_MASTER_PATH.exists() else FALLBACK_REPLAY_PATH
    dominance_path = REQUESTED_DOMINANCE_PATH if REQUESTED_REPLAY_MASTER_PATH.exists() and REQUESTED_DOMINANCE_PATH.exists() else FALLBACK_HISTORICAL_DOMINANCE_PATH

    replay = pd.read_csv(replay_path, low_memory=False)
    dominance = pd.read_csv(dominance_path, low_memory=False)
    rank_probs = pd.read_csv(RANK_PROBS_PATH, low_memory=False)
    score_probs = pd.read_csv(SCORE_PROBS_PATH, low_memory=False)

    fair_price_scope = "NOT_READ"
    if FAIR_PRICE_EMPIRICAL_PATH.exists():
        fair_sample = pd.read_csv(FAIR_PRICE_EMPIRICAL_PATH, usecols=["meeting_date"], low_memory=False)
        fair_dates = fair_sample["meeting_date"].astype(str).str[:10].nunique()
        fair_rows = len(fair_sample)
        fair_price_scope = f"LIVE_REFERENCE_ONLY rows={fair_rows} unique_dates={fair_dates}"

    replay = replay.copy()
    replay["meeting_date"] = replay["meeting_date"].astype(str).str[:10]
    replay["track"] = replay["track"].fillna("").astype(str).map(clean_text)
    replay["horse"] = replay["horse"].fillna("").astype(str).map(clean_text)
    replay["horse_key"] = replay.get("horse_key", replay["horse"]).fillna("").astype(str)
    replay["race_no"] = to_num(replay["race_no"]).astype("Int64")
    replay["runner_score"] = to_num(replay.get("runner_score", replay.get("runner_score_hist_v1", pd.Series(dtype=float))))
    replay["runner_rank"] = to_num(replay.get("runner_rank", replay.get("runner_rank_hist_v1", pd.Series(dtype=float))))
    replay["finish_position"] = to_num(replay["finish_position"])
    replay["won"] = to_num(replay["won"]).fillna(0).astype(int)
    replay["placed"] = replay["finish_position"].le(3).fillna(False).astype(int)
    replay["race_key_v1"] = build_race_key(replay)
    replay["runner_key_v1"] = build_runner_key(
        replay,
        replay["horse_key"].where(replay["horse_key"].astype(str).str.strip().ne(""), replay["horse"]),
    )
    replay["field_size"] = replay.groupby("race_key_v1")["horse"].transform("size")
    replay["rank_bucket"] = replay["runner_rank"].map(rank_bucket)
    replay["score_band"] = replay["runner_score"].map(score_band)

    dominance = dominance.copy()
    dominance["meeting_date"] = dominance["meeting_date"].astype(str).str[:10]
    dominance["track"] = dominance["track"].fillna("").astype(str).map(clean_text)
    dominance["horse"] = dominance["horse"].fillna("").astype(str).map(clean_text)
    dominance["horse_key"] = dominance.get("horse_key", dominance["horse"]).fillna("").astype(str)
    dominance["race_no"] = to_num(dominance["race_no"]).astype("Int64")
    dominance["runner_key_v1"] = build_runner_key(
        dominance,
        dominance["horse_key"].where(dominance["horse_key"].astype(str).str.strip().ne(""), dominance["horse"]),
    )

    numeric_cols = [
        "dominance_score_v1",
        "score_share_of_race",
        "finish_position",
        "won",
        "placed",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
    ]
    for col in numeric_cols:
        if col in dominance.columns:
            dominance[col] = to_num(dominance[col])

    if "dominance_band_v1" not in dominance.columns:
        dominance["dominance_band_v1"] = "UNKNOWN"
    dominance["dominance_band_v1"] = dominance["dominance_band_v1"].fillna("").astype(str).map(clean_text).str.upper()
    dominance["dominance_band_v1"] = dominance["dominance_band_v1"].where(dominance["dominance_band_v1"].ne(""), "UNKNOWN")

    dominance_keep = [
        "runner_key_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "score_share_of_race",
    ]
    replay = replay.merge(dominance[dominance_keep].drop_duplicates("runner_key_v1", keep="first"), on="runner_key_v1", how="left")

    q25 = float(replay["score_share_of_race"].dropna().quantile(0.25)) if replay["score_share_of_race"].notna().any() else 0.115
    q50 = float(replay["score_share_of_race"].dropna().quantile(0.50)) if replay["score_share_of_race"].notna().any() else 0.18
    q75 = float(replay["score_share_of_race"].dropna().quantile(0.75)) if replay["score_share_of_race"].notna().any() else 0.24
    replay["score_share_band_v1"] = replay["score_share_of_race"].map(lambda value: score_share_band_from_quantiles(value, q25, q50, q75))
    replay["score_share_band_v1"] = replay["score_share_band_v1"].fillna("UNKNOWN").astype(str)

    rank_map = rank_probs[["rank_bucket", "true_win_rate"]].copy().rename(columns={"true_win_rate": "historical_rank_prob"})
    score_map = score_probs[["score_band", "true_win_rate"]].copy().rename(columns={"true_win_rate": "historical_score_band_prob"})
    replay = replay.merge(rank_map, on="rank_bucket", how="left")
    replay = replay.merge(score_map, on="score_band", how="left")

    temperature = float(replay["runner_score"].std())
    if pd.isna(temperature) or temperature <= 0:
        temperature = 15.0

    replay["race_softmax_prob"] = replay.groupby("race_key_v1")["runner_score"].transform(lambda values: softmax_probabilities(values, temperature))
    replay["empirical_probability_raw"] = pd.concat(
        [replay["historical_rank_prob"], replay["historical_score_band_prob"], replay["race_softmax_prob"]],
        axis=1,
    ).mean(axis=1)
    replay["empirical_probability"] = replay["empirical_probability_raw"] / replay.groupby("race_key_v1")["empirical_probability_raw"].transform("sum")
    replay["empirical_probability"] = replay["empirical_probability"].fillna(0.0)
    replay["empirical_fair_odds"] = replay["empirical_probability"].map(fair_odds)
    replay["market_proxy_probability"] = np.where(replay["field_size"].gt(0), 1.0 / replay["field_size"], np.nan)
    replay["market_proxy_fair_odds"] = replay["field_size"].astype(float)
    replay["edge_proxy_pct"] = ((replay["market_proxy_fair_odds"] / replay["empirical_fair_odds"]) - 1.0) * 100.0
    replay["overlay_band"] = replay["edge_proxy_pct"].map(overlay_band)
    replay["positive_overlay_flag"] = replay["edge_proxy_pct"].gt(0).fillna(False)

    overlay_df = replay[replay["positive_overlay_flag"]].copy()
    overlay_df["overlay_truth_v1"] = np.where(overlay_df["won"].eq(1), "REAL_OVERLAY", "FAKE_OVERLAY")

    overlay_df[OUTPUT_COLUMNS].to_csv(OUTPUT_PATH, index=False)

    by_dominance = group_summary(overlay_df, ["dominance_band_v1"])
    by_dominance["dominance_band_v1"] = pd.Categorical(by_dominance["dominance_band_v1"], categories=DOMINANCE_BAND_ORDER, ordered=True)
    by_dominance["sample_ge_500"] = by_dominance["overlay_runners"].ge(500)
    by_dominance = by_dominance.sort_values("dominance_band_v1").reset_index(drop=True)
    by_dominance.to_csv(BY_DOMINANCE_PATH, index=False)

    by_score_share = group_summary(overlay_df, ["score_share_band_v1"])
    by_score_share["score_share_band_v1"] = pd.Categorical(by_score_share["score_share_band_v1"], categories=SCORE_SHARE_BAND_ORDER, ordered=True)
    by_score_share["sample_ge_500"] = by_score_share["overlay_runners"].ge(500)
    by_score_share = by_score_share.sort_values("score_share_band_v1").reset_index(drop=True)
    by_score_share.to_csv(BY_SCORE_SHARE_PATH, index=False)

    by_rank = group_summary(overlay_df, ["rank_bucket"])
    by_rank["rank_bucket"] = pd.Categorical(by_rank["rank_bucket"], categories=RANK_BUCKET_ORDER, ordered=True)
    by_rank = by_rank.sort_values("rank_bucket").reset_index(drop=True)

    by_combo = group_summary(overlay_df, ["dominance_band_v1", "score_share_band_v1"])
    by_combo = by_combo[by_combo["overlay_runners"] >= 300].copy()
    if not by_combo.empty:
        by_combo = by_combo.sort_values(["real_overlay_win_rate", "overlay_runners"], ascending=[False, False], kind="mergesort")
        best_combo = by_combo.iloc[0]
        best_combo_label = f"{best_combo['dominance_band_v1']}|{best_combo['score_share_band_v1']}"
        best_combo_rate = float(best_combo["real_overlay_win_rate"])
        best_combo_sample = int(best_combo["overlay_runners"])
    else:
        best_combo_label = "NONE"
        best_combo_rate = math.nan
        best_combo_sample = 0

    best_dom_500 = by_dominance[by_dominance["overlay_runners"] >= 500].copy()
    if not best_dom_500.empty:
        best_dom_500 = best_dom_500.sort_values(["real_overlay_win_rate", "overlay_runners"], ascending=[False, False], kind="mergesort")
        best_dom_label = str(best_dom_500.iloc[0]["dominance_band_v1"])
        best_dom_rate = float(best_dom_500.iloc[0]["real_overlay_win_rate"])
        best_dom_sample = int(best_dom_500.iloc[0]["overlay_runners"])
    else:
        best_dom_label = "NONE"
        best_dom_rate = math.nan
        best_dom_sample = 0

    best_share_500 = by_score_share[by_score_share["overlay_runners"] >= 500].copy()
    if not best_share_500.empty:
        best_share_500 = best_share_500.sort_values(["real_overlay_win_rate", "overlay_runners"], ascending=[False, False], kind="mergesort")
        best_share_label = str(best_share_500.iloc[0]["score_share_band_v1"])
        best_share_rate = float(best_share_500.iloc[0]["real_overlay_win_rate"])
        best_share_sample = int(best_share_500.iloc[0]["overlay_runners"])
    else:
        best_share_label = "NONE"
        best_share_rate = math.nan
        best_share_sample = 0

    feature_df = summarize_feature_effects(overlay_df)

    def feature_effect(name: str) -> float:
        row = feature_df.loc[feature_df["feature_name"] == name, "abs_effect_size"]
        return float(row.iloc[0]) if not row.empty and pd.notna(row.iloc[0]) else math.nan

    dominance_effect = feature_effect("dominance_score_v1")
    score_share_effect = feature_effect("score_share_of_race")
    overlay_effect = feature_effect("edge_proxy_pct")

    if pd.isna(dominance_effect) or pd.isna(score_share_effect) or pd.isna(overlay_effect):
        final_conclusion = "HYBRID"
    elif dominance_effect > score_share_effect * 1.1 and dominance_effect > overlay_effect * 1.25:
        final_conclusion = "DOMINANCE_DRIVEN"
    elif score_share_effect > dominance_effect * 1.1 and score_share_effect > overlay_effect * 1.25:
        final_conclusion = "SCORE_SHARE_DRIVEN"
    elif overlay_effect > max(dominance_effect, score_share_effect) * 1.1:
        final_conclusion = "OVERLAY_SIZE_DRIVEN"
    else:
        final_conclusion = "HYBRID"

    summary_rows: list[dict[str, object]] = [
        {"section": "INPUTS", "metric": "replay_source", "value": replay_path.name, "notes": "requested master path preferred, fallback used if missing"},
        {"section": "INPUTS", "metric": "dominance_source", "value": dominance_path.name, "notes": "historical-only source used for dominance features"},
        {"section": "INPUTS", "metric": "fair_price_empirical_scope", "value": fair_price_scope, "notes": "live fair-price file is not used for historical reconstruction"},
        {"section": "OVERVIEW", "metric": "historical_rows", "value": int(len(replay)), "notes": "full historical runner universe"},
        {"section": "OVERVIEW", "metric": "historical_races", "value": int(replay["race_key_v1"].nunique()), "notes": "full historical race universe"},
        {"section": "OVERVIEW", "metric": "positive_overlay_rows", "value": int(len(overlay_df)), "notes": "edge_proxy_pct > 0"},
        {"section": "OVERVIEW", "metric": "positive_overlay_races", "value": int(overlay_df["race_key_v1"].nunique()), "notes": "historical races containing at least one positive overlay"},
        {"section": "OVERVIEW", "metric": "real_overlay_rows", "value": int((overlay_df["overlay_truth_v1"] == 'REAL_OVERLAY').sum()), "notes": "positive overlay winners"},
        {"section": "OVERVIEW", "metric": "fake_overlay_rows", "value": int((overlay_df["overlay_truth_v1"] == 'FAKE_OVERLAY').sum()), "notes": "positive overlay losers"},
        {"section": "OVERVIEW", "metric": "positive_overlay_win_rate", "value": round(float(overlay_df["won"].mean()), 6), "notes": "real overlay share inside positive overlays"},
        {"section": "QUESTION_1", "metric": "real_overlay_win_rate_by_dominance_band", "value": "SEE_BY_DOMINANCE_FILE", "notes": "public/data/edgeiq_real_vs_fake_overlay_replay_v1_by_dominance.csv"},
        {"section": "QUESTION_2", "metric": "real_overlay_win_rate_by_score_share_band", "value": "SEE_BY_SCORE_SHARE_FILE", "notes": "public/data/edgeiq_real_vs_fake_overlay_replay_v1_by_score_share.csv"},
        {"section": "QUESTION_3", "metric": "real_overlay_win_rate_by_rank_bucket", "value": "SEE_SUMMARY_ROWS_BELOW", "notes": "rank-bucket rows appended below"},
        {"section": "QUESTION_4", "metric": "strongest_dominance_bucket_ge_500", "value": best_dom_label, "notes": f"win_rate={round(best_dom_rate, 6) if pd.notna(best_dom_rate) else 'NA'} sample={best_dom_sample}"},
        {"section": "QUESTION_5", "metric": "strongest_score_share_bucket_ge_500", "value": best_share_label, "notes": f"win_rate={round(best_share_rate, 6) if pd.notna(best_share_rate) else 'NA'} sample={best_share_sample}"},
        {"section": "QUESTION_6", "metric": "strongest_dominance_score_share_combo_ge_300", "value": best_combo_label, "notes": f"win_rate={round(best_combo_rate, 6) if pd.notna(best_combo_rate) else 'NA'} sample={best_combo_sample}"},
        {"section": "MONOTONICITY", "metric": "dominance_band", "value": "PASS" if monotonic_pass(by_dominance["real_overlay_win_rate"].tolist()) else "FAIL", "notes": "expected ELITE -> POOR descending"},
        {"section": "MONOTONICITY", "metric": "score_share_band", "value": "PASS" if monotonic_pass(by_score_share["real_overlay_win_rate"].tolist()) else "FAIL", "notes": "expected VERY_HIGH -> LOW descending"},
        {"section": "MONOTONICITY", "metric": "rank_bucket", "value": "PASS" if monotonic_pass(by_rank["real_overlay_win_rate"].tolist()) else "FAIL", "notes": "expected RANK_1 -> RANK_11_PLUS descending"},
        {"section": "MONOTONICITY", "metric": "overlay_band", "value": "PASS" if monotonic_pass(group_summary(overlay_df, ['overlay_band']).sort_values('overlay_band', key=lambda s: pd.Categorical(s, categories=OVERLAY_BAND_ORDER, ordered=True))['real_overlay_win_rate'].tolist()) else "FAIL", "notes": "included for overlay-size comparison"},
        {"section": "EFFECT_SIZES", "metric": "dominance_score_v1", "value": round(float(feature_df.loc[feature_df['feature_name'] == 'dominance_score_v1', 'effect_size'].iloc[0]), 6), "notes": "REAL_OVERLAY vs FAKE_OVERLAY"},
        {"section": "EFFECT_SIZES", "metric": "score_share_of_race", "value": round(float(feature_df.loc[feature_df['feature_name'] == 'score_share_of_race', 'effect_size'].iloc[0]), 6), "notes": "REAL_OVERLAY vs FAKE_OVERLAY"},
        {"section": "EFFECT_SIZES", "metric": "runner_rank", "value": round(float(feature_df.loc[feature_df['feature_name'] == 'runner_rank', 'effect_size'].iloc[0]), 6), "notes": "REAL_OVERLAY vs FAKE_OVERLAY"},
        {"section": "EFFECT_SIZES", "metric": "runner_score", "value": round(float(feature_df.loc[feature_df['feature_name'] == 'runner_score', 'effect_size'].iloc[0]), 6), "notes": "REAL_OVERLAY vs FAKE_OVERLAY"},
        {"section": "EFFECT_SIZES", "metric": "edge_proxy_pct", "value": round(float(feature_df.loc[feature_df['feature_name'] == 'edge_proxy_pct', 'effect_size'].iloc[0]), 6), "notes": "overlay-size reference"},
        {"section": "CONCLUSION", "metric": "final_conclusion", "value": final_conclusion, "notes": "based on predictive strength of dominance, score share, and overlay size"},
    ]

    for row in feature_df.itertuples(index=False):
        summary_rows.append(
            {
                "section": "FEATURE_RANKING",
                "metric": f"rank_{int(row.importance_rank)}",
                "value": row.feature_name,
                "notes": f"abs_effect_size={round(row.abs_effect_size, 6) if pd.notna(row.abs_effect_size) else 'NA'} family={row.feature_family}",
            }
        )

    for row in by_rank.itertuples(index=False):
        summary_rows.append(
            {
                "section": "BY_RANK",
                "metric": str(row.rank_bucket),
                "value": round(float(row.real_overlay_win_rate), 6) if pd.notna(row.real_overlay_win_rate) else "NA",
                "notes": f"runners={int(row.overlay_runners)} wins={int(row.real_overlay_wins)}",
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    print("[EDGEIQ_REAL_VS_FAKE_OVERLAY_REPLAY_V1] COMPLETE")
    print(summary_df.to_string(index=False))
    print("\nBy Dominance")
    print(by_dominance.to_string(index=False))
    print("\nBy Score Share")
    print(by_score_share.to_string(index=False))


if __name__ == "__main__":
    main()
