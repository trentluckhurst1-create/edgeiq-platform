from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_SCORE_V6_PATH = DATA / "edgeiq_runner_score_v6.csv"
TRUST_INDEX_PATH = DATA / "edgeiq_trust_index_v1.csv"
RANK_GAP_ENGINE_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
TRUST_PROFILE_PATH = DATA / "edgeiq_trust_profile_engine_v1.csv"
OUT_PATH = DATA / "edgeiq_trust_profile_live_audit_v1.csv"

PROFILE_ORDER = ["ELITE", "STRONG", "STANDARD", "CHAOTIC"]
LIVE_GAP_1_2_MAP = {
    "0_2": "ZERO_TO_2",
    "2_5": "TWO_TO_5",
    "5_10": "FIVE_TO_10",
    "10_PLUS": "TEN_PLUS",
}
LIVE_GAP_1_3_MAP = {
    "0_5": "ZERO_TO_5",
    "5_10": "FIVE_TO_10",
    "10_15": "TEN_TO_15",
    "15_PLUS": "FIFTEEN_PLUS",
}


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_join_key(df: pd.DataFrame, track_col: str = "track") -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df[track_col].map(normalize_track) + "|" + race_no


def normalize_gap_1_2_live(value: object) -> str:
    text = clean_text(value).upper()
    return LIVE_GAP_1_2_MAP.get(text, text or "UNKNOWN")


def normalize_gap_1_3_live(value: object) -> str:
    text = clean_text(value).upper()
    return LIVE_GAP_1_3_MAP.get(text, text or "UNKNOWN")


def score_share_band(value: float, q25: float, q50: float, q75: float) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    if value < q25:
        return "LOW"
    if value < q50:
        return "MEDIUM"
    if value < q75:
        return "HIGH"
    return "VERY_HIGH"


def first_valid_text(values: pd.Series, default: str = "") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def nth_value_desc(values: pd.Series, index_zero_based: int) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna().sort_values(ascending=False).reset_index(drop=True)
    if len(clean) <= index_zero_based:
        return math.nan
    return float(clean.iloc[index_zero_based])


def load_rank_gap_quantiles() -> tuple[float, float, float]:
    if not RANK_GAP_ENGINE_PATH.exists():
        raise FileNotFoundError(f"Missing rank gap engine file: {RANK_GAP_ENGINE_PATH}")
    df = pd.read_csv(RANK_GAP_ENGINE_PATH, low_memory=False, usecols=["score_share_total"])
    score_share = to_num(df["score_share_total"]).dropna()
    if score_share.empty:
        raise ValueError("Historical rank gap engine has no score_share_total values.")
    return (
        float(score_share.quantile(0.25)),
        float(score_share.quantile(0.50)),
        float(score_share.quantile(0.75)),
    )


def load_runner_scores() -> pd.DataFrame:
    if not RUNNER_SCORE_V6_PATH.exists():
        raise FileNotFoundError(f"Missing runner score v6 file: {RUNNER_SCORE_V6_PATH}")
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "runner_score_v6",
        "runner_rank_v6",
    ]
    df = pd.read_csv(RUNNER_SCORE_V6_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "horse"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_score_v6", "runner_rank_v6"]:
        df[col] = to_num(df[col])
    df["join_key_v1"] = build_join_key(df)
    return df.copy()


def build_live_race_metrics(q25: float, q50: float, q75: float) -> pd.DataFrame:
    runner_df = load_runner_scores()
    race_df = (
        runner_df.groupby("join_key_v1", dropna=False)
        .agg(
            meeting_date=("meeting_date", lambda s: first_valid_text(s)),
            track=("track", lambda s: first_valid_text(s)),
            race_no=("race_no", "first"),
            top_horse_v6=("horse", lambda s: first_valid_text(s)),
            field_size_live=("horse", "size"),
            top_score_v6=("runner_score_v6", lambda s: nth_value_desc(s, 0)),
            second_score_v6=("runner_score_v6", lambda s: nth_value_desc(s, 1)),
            third_score_v6=("runner_score_v6", lambda s: nth_value_desc(s, 2)),
            total_race_score_v6=("runner_score_v6", "sum"),
        )
        .reset_index()
    )
    race_df["score_share_total_v6"] = race_df["top_score_v6"] / race_df["total_race_score_v6"]
    race_df["score_share_band"] = race_df["score_share_total_v6"].apply(lambda value: score_share_band(value, q25, q50, q75))
    return race_df.copy()


def load_trust_index() -> pd.DataFrame:
    if not TRUST_INDEX_PATH.exists():
        raise FileNotFoundError(f"Missing trust index file: {TRUST_INDEX_PATH}")
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "top_pick_horse",
        "field_size",
        "trust_band_v1",
        "gap_1_2_bucket",
        "gap_1_3_bucket",
        "trust_index_v1",
    ]
    df = pd.read_csv(TRUST_INDEX_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "race_key", "top_pick_horse", "trust_band_v1", "gap_1_2_bucket", "gap_1_3_bucket"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "field_size", "trust_index_v1"]:
        df[col] = to_num(df[col])
    df["join_key_v1"] = build_join_key(df)
    df["gap_1_2_band"] = df["gap_1_2_bucket"].apply(normalize_gap_1_2_live)
    df["gap_1_3_band"] = df["gap_1_3_bucket"].apply(normalize_gap_1_3_live)
    return df.copy()


def load_trust_profiles() -> pd.DataFrame:
    if not TRUST_PROFILE_PATH.exists():
        raise FileNotFoundError(f"Missing trust profile engine file: {TRUST_PROFILE_PATH}")
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "join_key_v1",
        "trust_profile_v1",
        "trust_profile_score_v1",
        "historical_top1_profile_v1",
        "historical_top3_profile_v1",
        "historical_top5_profile_v1",
        "historical_top10_profile_v1",
        "historical_avg_winner_rank_profile_v1",
    ]
    df = pd.read_csv(TRUST_PROFILE_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "trust_profile_v1"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in [
        "race_no",
        "trust_profile_score_v1",
        "historical_top1_profile_v1",
        "historical_top3_profile_v1",
        "historical_top5_profile_v1",
        "historical_top10_profile_v1",
        "historical_avg_winner_rank_profile_v1",
    ]:
        df[col] = to_num(df[col])
    if "join_key_v1" not in df.columns or df["join_key_v1"].isna().all():
        df["join_key_v1"] = build_join_key(df)
    return df.copy()


def race_label(row: pd.Series) -> str:
    return f"{row['track']} R{int(row['race_no'])}"


def main() -> None:
    q25, q50, q75 = load_rank_gap_quantiles()
    live_metrics_df = build_live_race_metrics(q25, q50, q75)
    trust_index_df = load_trust_index()
    trust_profile_df = load_trust_profiles()

    audit_df = trust_index_df.merge(trust_profile_df, on="join_key_v1", how="left", suffixes=("", "_profile"))
    audit_df = audit_df.merge(live_metrics_df[[
        "join_key_v1",
        "top_horse_v6",
        "field_size_live",
        "top_score_v6",
        "second_score_v6",
        "third_score_v6",
        "total_race_score_v6",
        "score_share_total_v6",
        "score_share_band",
    ]], on="join_key_v1", how="left")

    audit_df["meeting_date"] = audit_df["meeting_date"].fillna(audit_df.get("meeting_date_profile"))
    audit_df["track"] = audit_df["track"].fillna(audit_df.get("track_profile"))
    audit_df["race_no"] = audit_df["race_no"].fillna(audit_df.get("race_no_profile"))
    audit_df["trust_profile_v1"] = audit_df["trust_profile_v1"].fillna("UNKNOWN")
    audit_df["score_share_band"] = audit_df["score_share_band"].fillna("UNKNOWN")
    audit_df["profile_order_v1"] = audit_df["trust_profile_v1"].map({name: idx for idx, name in enumerate(PROFILE_ORDER, start=1)}).fillna(999)
    audit_df["race_label_v1"] = audit_df.apply(race_label, axis=1)

    audit_df = audit_df[[
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "join_key_v1",
        "top_pick_horse",
        "top_horse_v6",
        "trust_profile_v1",
        "trust_profile_score_v1",
        "trust_band_v1",
        "score_share_band",
        "gap_1_2_band",
        "gap_1_3_band",
        "field_size",
        "field_size_live",
        "trust_index_v1",
        "top_score_v6",
        "second_score_v6",
        "third_score_v6",
        "score_share_total_v6",
        "historical_top1_profile_v1",
        "historical_top3_profile_v1",
        "historical_top5_profile_v1",
        "historical_top10_profile_v1",
        "historical_avg_winner_rank_profile_v1",
        "profile_order_v1",
        "race_label_v1",
    ]].copy()

    audit_df = audit_df.sort_values(["profile_order_v1", "trust_profile_score_v1", "trust_index_v1", "track", "race_no"], ascending=[True, False, False, True, True]).reset_index(drop=True)
    audit_df.to_csv(OUT_PATH, index=False)

    profile_counts = (
        audit_df.groupby("trust_profile_v1", dropna=False)
        .agg(races=("join_key_v1", "size"))
        .reset_index()
    )
    profile_counts["profile_order_v1"] = profile_counts["trust_profile_v1"].map({name: idx for idx, name in enumerate(PROFILE_ORDER, start=1)}).fillna(999)
    profile_counts = profile_counts.sort_values(["profile_order_v1", "trust_profile_v1"]).drop(columns=["profile_order_v1"])

    best_race = audit_df.sort_values(["profile_order_v1", "trust_profile_score_v1", "trust_index_v1"], ascending=[True, False, False]).iloc[0]
    worst_race = audit_df.sort_values(["profile_order_v1", "trust_profile_score_v1", "trust_index_v1"], ascending=[False, True, True]).iloc[0]
    highest_trust_race = audit_df.sort_values(["trust_index_v1", "trust_profile_score_v1"], ascending=[False, False]).iloc[0]
    lowest_trust_race = audit_df.sort_values(["trust_index_v1", "trust_profile_score_v1"], ascending=[True, True]).iloc[0]

    print("[EDGEIQ_TRUST_PROFILE_LIVE_AUDIT_V1] COMPLETE")
    print(f"output={OUT_PATH}")
    print(f"live_races={len(audit_df)}")
    print("profile_counts_start")
    for row in profile_counts.itertuples(index=False):
        print(f"{row.trust_profile_v1},{int(row.races)}")
    print("profile_counts_end")
    print(f"best_race_on_card={best_race['race_label_v1']}|profile={best_race['trust_profile_v1']}|profile_score={float(best_race['trust_profile_score_v1']):.3f}|trust_index={float(best_race['trust_index_v1']):.3f}")
    print(f"worst_race_on_card={worst_race['race_label_v1']}|profile={worst_race['trust_profile_v1']}|profile_score={float(worst_race['trust_profile_score_v1']):.3f}|trust_index={float(worst_race['trust_index_v1']):.3f}")
    print(f"highest_trust_race={highest_trust_race['race_label_v1']}|profile={highest_trust_race['trust_profile_v1']}|profile_score={float(highest_trust_race['trust_profile_score_v1']):.3f}|trust_index={float(highest_trust_race['trust_index_v1']):.3f}")
    print(f"lowest_trust_race={lowest_trust_race['race_label_v1']}|profile={lowest_trust_race['trust_profile_v1']}|profile_score={float(lowest_trust_race['trust_profile_score_v1']):.3f}|trust_index={float(lowest_trust_race['trust_index_v1']):.3f}")


if __name__ == "__main__":
    main()
