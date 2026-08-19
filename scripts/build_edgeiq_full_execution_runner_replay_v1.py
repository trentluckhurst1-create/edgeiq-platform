from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

EXECUTION_REPLAY_PATH = DATA / "historical_execution_governance_replay_v1.csv"
HISTORICAL_RUNNER_SCORES_PATH = DATA / "edgeiq_historical_runner_scores_v1.csv"
TRUST_PROFILE_SUMMARY_PATH = DATA / "edgeiq_trust_profile_engine_v1_summary.csv"

RUNNER_OUT = DATA / "edgeiq_full_execution_runner_replay_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_full_execution_runner_replay_v1_summary.csv"
BY_RANK_OUT = DATA / "edgeiq_full_execution_runner_replay_v1_by_rank.csv"
BY_SCORE_OUT = DATA / "edgeiq_full_execution_runner_replay_v1_by_score_band.csv"

MIN_SAMPLE = 300
RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]
SCORE_BAND_ORDER = ["<40", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+"]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def normalize_horse_key(value: object, fallback: object = "") -> str:
    raw = clean_text(value)
    if raw == "":
        raw = clean_text(fallback)
    return re.sub(r"[^A-Z0-9]+", "", raw.upper())


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_join_key(df: pd.DataFrame, track_col: str = "track") -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df[track_col].map(normalize_track) + "|" + race_no


def build_runner_key(df: pd.DataFrame, track_col: str = "track", horse_key_col: str = "horse_key", horse_col: str = "horse") -> pd.Series:
    horse_component = [normalize_horse_key(horse_key, horse) for horse_key, horse in zip(df[horse_key_col], df[horse_col])]
    return build_join_key(df, track_col=track_col) + "|" + pd.Series(horse_component, index=df.index)


def rank_bucket(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number <= 1:
        return "RANK_1"
    if number <= 2:
        return "RANK_2"
    if number <= 3:
        return "RANK_3"
    if number <= 5:
        return "RANK_4_5"
    if number <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def score_band(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number < 40:
        return "<40"
    if number < 45:
        return "40-44"
    if number < 50:
        return "45-49"
    if number < 55:
        return "50-54"
    if number < 60:
        return "55-59"
    if number < 65:
        return "60-64"
    if number < 70:
        return "65-69"
    if number < 75:
        return "70-74"
    if number < 80:
        return "75-79"
    return "80+"


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def first_valid_text(values: pd.Series, default: str = "") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def load_execution_replay() -> pd.DataFrame:
    if not EXECUTION_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing execution replay file: {EXECUTION_REPLAY_PATH}")

    df = pd.read_csv(EXECUTION_REPLAY_PATH, low_memory=False)
    text_cols = [
        "meeting_date",
        "track",
        "horse",
        "horse_key",
        "governance_band_hist_v1",
        "trust_band_v1",
        "trust_profile_v1",
        "execution_permission_v1",
        "execution_reason_v1",
        "race_execution_class_v1",
        "top_ranked_horse_v1",
        "join_key_v1",
        "runner_join_key_v1",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).map(clean_text)

    numeric_cols = [
        "race_no",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "replay_runner_score_v1",
        "replay_runner_rank_v1",
        "finish_position",
        "won",
        "trust_index_v1",
        "trust_profile_score_v1",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_num(df[col])

    if "join_key_v1" not in df.columns or df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)
    if "runner_join_key_v1" not in df.columns or df["runner_join_key_v1"].eq("").all():
        df["runner_join_key_v1"] = build_runner_key(df)

    return df.copy()


def load_historical_runner_scores() -> pd.DataFrame:
    if not HISTORICAL_RUNNER_SCORES_PATH.exists():
        raise FileNotFoundError(f"Missing historical runner scores file: {HISTORICAL_RUNNER_SCORES_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "governance_band_hist_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
    ]
    df = pd.read_csv(HISTORICAL_RUNNER_SCORES_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "horse", "horse_key", "governance_band_hist_v1"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_score_hist_v1", "runner_rank_hist_v1"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    return df[[
        "runner_join_key_v1",
        "governance_band_hist_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
    ]].copy()


def load_trust_profile_summary() -> dict[str, object]:
    if not TRUST_PROFILE_SUMMARY_PATH.exists():
        raise FileNotFoundError(f"Missing trust profile summary file: {TRUST_PROFILE_SUMMARY_PATH}")

    df = pd.read_csv(TRUST_PROFILE_SUMMARY_PATH, low_memory=False)
    if df.empty:
        return {
            "strongest_profile": "",
            "exclude_profile": "",
            "learned_q25_v1": math.nan,
            "learned_q50_v1": math.nan,
            "learned_q75_v1": math.nan,
        }

    strongest = df[df.get("strongest_historical_profile_flag_v1", False).astype(bool)]
    exclude = df[df.get("exclude_from_betting_flag_v1", False).astype(bool)]

    return {
        "strongest_profile": first_valid_text(strongest["trust_profile_v1"], "") if "trust_profile_v1" in strongest.columns else "",
        "exclude_profile": first_valid_text(exclude["trust_profile_v1"], "") if "trust_profile_v1" in exclude.columns else "",
        "learned_q25_v1": float(to_num(df["learned_q25_v1"]).dropna().iloc[0]) if "learned_q25_v1" in df.columns and not to_num(df["learned_q25_v1"]).dropna().empty else math.nan,
        "learned_q50_v1": float(to_num(df["learned_q50_v1"]).dropna().iloc[0]) if "learned_q50_v1" in df.columns and not to_num(df["learned_q50_v1"]).dropna().empty else math.nan,
        "learned_q75_v1": float(to_num(df["learned_q75_v1"]).dropna().iloc[0]) if "learned_q75_v1" in df.columns and not to_num(df["learned_q75_v1"]).dropna().empty else math.nan,
    }


def prepare_full_execution_runner_frame() -> pd.DataFrame:
    execution_df = load_execution_replay()
    score_df = load_historical_runner_scores()

    merged = execution_df.merge(score_df, on="runner_join_key_v1", how="left", suffixes=("", "_source"))
    merged["runner_score_hist_v1"] = to_num(merged["runner_score_hist_v1"]).fillna(to_num(merged["runner_score_hist_v1_source"]))
    merged["runner_rank_hist_v1"] = to_num(merged["runner_rank_hist_v1"]).fillna(to_num(merged["runner_rank_hist_v1_source"]))
    merged["governance_band_hist_v1"] = merged["governance_band_hist_v1"].replace("", pd.NA)
    merged["governance_band_hist_v1"] = merged["governance_band_hist_v1"].fillna(merged["governance_band_hist_v1_source"]).fillna("UNKNOWN")

    full_df = merged[merged["race_execution_class_v1"].eq("FULL_EXECUTION")].copy()
    full_df["placed"] = to_num(full_df["finish_position"]).le(3).astype(int)
    full_df["rank_bucket_v1"] = full_df["runner_rank_hist_v1"].apply(rank_bucket)
    full_df["score_band_v1"] = full_df["runner_score_hist_v1"].apply(score_band)
    full_df["avg_finish_v1"] = to_num(full_df["finish_position"])
    full_df = full_df.sort_values(
        ["join_key_v1", "runner_rank_hist_v1", "runner_score_hist_v1", "horse"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)
    return full_df.copy()


def summarise_bucket(df: pd.DataFrame, group_col: str, group_order: list[str]) -> pd.DataFrame:
    winners_total = int(df["won"].sum())
    grouped = (
        df.groupby(group_col, dropna=False)
        .agg(
            runners=("horse", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_finish=("avg_finish_v1", "mean"),
            avg_score=("runner_score_hist_v1", "mean"),
            avg_rank=("runner_rank_hist_v1", "mean"),
        )
        .reset_index()
    )
    grouped["win_rate"] = grouped["wins"] / grouped["runners"]
    grouped["place_rate"] = grouped["places"] / grouped["runners"]
    grouped["winner_capture"] = grouped["wins"].apply(lambda value: safe_div(value, winners_total))
    grouped["eligible_min_sample_v1"] = grouped["runners"].ge(MIN_SAMPLE)
    grouped["group_sort_v1"] = grouped[group_col].map({name: idx for idx, name in enumerate(group_order, start=1)}).fillna(999)
    grouped = grouped.sort_values(["win_rate", "runners", "group_sort_v1"], ascending=[False, False, True]).reset_index(drop=True)
    grouped["ranked_order_v1"] = range(1, len(grouped) + 1)
    grouped = grouped[[
        group_col,
        "runners",
        "wins",
        "win_rate",
        "places",
        "place_rate",
        "avg_finish",
        "avg_score",
        "avg_rank",
        "winner_capture",
        "eligible_min_sample_v1",
        "ranked_order_v1",
        "group_sort_v1",
    ]].copy()
    return grouped


def summarise_combo(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["rank_bucket_v1", "score_band_v1"], dropna=False)
        .agg(
            runners=("horse", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_finish=("avg_finish_v1", "mean"),
        )
        .reset_index()
    )
    grouped["win_rate"] = grouped["wins"] / grouped["runners"]
    grouped["place_rate"] = grouped["places"] / grouped["runners"]
    grouped["eligible_min_sample_v1"] = grouped["runners"].ge(MIN_SAMPLE)
    grouped["combo_label_v1"] = grouped["rank_bucket_v1"] + " | " + grouped["score_band_v1"]
    return grouped


def build_summary(full_df: pd.DataFrame, by_rank_df: pd.DataFrame, by_score_df: pd.DataFrame, combo_df: pd.DataFrame, trust_summary: dict[str, object]) -> pd.DataFrame:
    winner_df = full_df[full_df["won"].eq(1)].copy()
    summary_rows: list[dict[str, object]] = []

    def add(metric: str, value: object) -> None:
        summary_rows.append({"metric": metric, "value": value})

    add("full_execution_runner_rows", int(len(full_df)))
    add("full_execution_races", int(full_df["join_key_v1"].nunique()))
    add("full_execution_winner_rows", int(len(winner_df)))

    rank_lookup = by_rank_df.set_index("rank_bucket_v1") if not by_rank_df.empty else pd.DataFrame()
    for bucket, metric_name in [
        ("RANK_1", "rank1_win_rate"),
        ("RANK_2", "rank2_win_rate"),
        ("RANK_3", "rank3_win_rate"),
        ("RANK_4_5", "rank4_5_win_rate"),
    ]:
        value = rank_lookup.at[bucket, "win_rate"] if bucket in rank_lookup.index else math.nan
        add(metric_name, value)

    add("top3_capture", float(winner_df["runner_rank_hist_v1"].le(3).mean()) if not winner_df.empty else math.nan)
    add("top5_capture", float(winner_df["runner_rank_hist_v1"].le(5).mean()) if not winner_df.empty else math.nan)
    add("avg_winner_rank", float(winner_df["runner_rank_hist_v1"].mean()) if not winner_df.empty else math.nan)
    add("min_sample_required", MIN_SAMPLE)

    eligible_rank = by_rank_df[by_rank_df["eligible_min_sample_v1"]].copy()
    if not eligible_rank.empty:
        best_rank = eligible_rank.sort_values(["win_rate", "runners"], ascending=[False, False]).iloc[0]
        add("best_rank_bucket", best_rank["rank_bucket_v1"])
        add("best_rank_bucket_runners", int(best_rank["runners"]))
        add("best_rank_bucket_wins", int(best_rank["wins"]))
        add("best_rank_bucket_win_rate", float(best_rank["win_rate"]))
    else:
        add("best_rank_bucket", "")
        add("best_rank_bucket_runners", math.nan)
        add("best_rank_bucket_wins", math.nan)
        add("best_rank_bucket_win_rate", math.nan)

    eligible_score = by_score_df[by_score_df["eligible_min_sample_v1"]].copy()
    if not eligible_score.empty:
        best_score = eligible_score.sort_values(["win_rate", "runners"], ascending=[False, False]).iloc[0]
        add("best_score_bucket", best_score["score_band_v1"])
        add("best_score_bucket_runners", int(best_score["runners"]))
        add("best_score_bucket_wins", int(best_score["wins"]))
        add("best_score_bucket_win_rate", float(best_score["win_rate"]))
    else:
        add("best_score_bucket", "")
        add("best_score_bucket_runners", math.nan)
        add("best_score_bucket_wins", math.nan)
        add("best_score_bucket_win_rate", math.nan)

    eligible_combo = combo_df[combo_df["eligible_min_sample_v1"]].copy()
    if not eligible_combo.empty:
        best_combo = eligible_combo.sort_values(["win_rate", "runners"], ascending=[False, False]).iloc[0]
        add("best_rank_score_combo", str(best_combo["combo_label_v1"]))
        add("best_rank_score_combo_runners", int(best_combo["runners"]))
        add("best_rank_score_combo_wins", int(best_combo["wins"]))
        add("best_rank_score_combo_win_rate", float(best_combo["win_rate"]))
        add("best_rank_score_combo_place_rate", float(best_combo["place_rate"]))
        add("best_rank_score_combo_avg_finish", float(best_combo["avg_finish"]))
    else:
        add("best_rank_score_combo", "")
        add("best_rank_score_combo_runners", math.nan)
        add("best_rank_score_combo_wins", math.nan)
        add("best_rank_score_combo_win_rate", math.nan)
        add("best_rank_score_combo_place_rate", math.nan)
        add("best_rank_score_combo_avg_finish", math.nan)

    add("strongest_trust_profile_v1", trust_summary.get("strongest_profile", ""))
    add("exclude_trust_profile_v1", trust_summary.get("exclude_profile", ""))
    add("trust_profile_q25_v1", trust_summary.get("learned_q25_v1", math.nan))
    add("trust_profile_q50_v1", trust_summary.get("learned_q50_v1", math.nan))
    add("trust_profile_q75_v1", trust_summary.get("learned_q75_v1", math.nan))

    return pd.DataFrame(summary_rows)


def main() -> None:
    trust_summary = load_trust_profile_summary()
    full_df = prepare_full_execution_runner_frame()

    by_rank_df = summarise_bucket(full_df, "rank_bucket_v1", RANK_BUCKET_ORDER)
    by_score_df = summarise_bucket(full_df, "score_band_v1", SCORE_BAND_ORDER)
    combo_df = summarise_combo(full_df)
    summary_df = build_summary(full_df, by_rank_df, by_score_df, combo_df, trust_summary)

    runner_out = full_df[[
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "rank_bucket_v1",
        "score_band_v1",
        "finish_position",
        "won",
        "placed",
        "governance_band_hist_v1",
        "trust_index_v1",
        "trust_band_v1",
        "trust_profile_score_v1",
        "trust_profile_v1",
        "execution_permission_v1",
        "execution_reason_v1",
        "race_execution_class_v1",
        "join_key_v1",
        "runner_join_key_v1",
    ]].copy()

    runner_out.to_csv(RUNNER_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    by_rank_df.to_csv(BY_RANK_OUT, index=False)
    by_score_df.to_csv(BY_SCORE_OUT, index=False)

    winner_df = full_df[full_df["won"].eq(1)].copy()
    print("[EDGEIQ_FULL_EXECUTION_RUNNER_REPLAY_V1] COMPLETE")
    print(f"runner_out={RUNNER_OUT}")
    print(f"summary_out={SUMMARY_OUT}")
    print(f"by_rank_out={BY_RANK_OUT}")
    print(f"by_score_out={BY_SCORE_OUT}")
    print(f"full_execution_races={full_df['join_key_v1'].nunique()}")
    print(f"full_execution_runners={len(full_df)}")
    print(f"winner_rows={len(winner_df)}")


if __name__ == "__main__":
    main()
