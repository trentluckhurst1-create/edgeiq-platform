from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
HIST_RUNNER_SCORES_PATH = DATA / "edgeiq_historical_runner_scores_v1.csv"
HIST_TRUST_REPLAY_PATH = DATA / "edgeiq_trust_band_replay_v1.csv"
HIST_GAP_ENGINE_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
TRUST_PROFILE_SUMMARY_PATH = DATA / "edgeiq_trust_profile_engine_v1_summary.csv"

REPLAY_OUT = DATA / "historical_execution_governance_replay_v1.csv"
SUMMARY_OUT = DATA / "historical_execution_governance_replay_v1_summary.csv"

PRIOR_RACES = 300.0
PROFILE_ORDER = ["ELITE", "STRONG", "STANDARD", "CHAOTIC"]
EXECUTION_ORDER = ["FULL_EXECUTION", "REDUCED_EXECUTION", "WATCH_ONLY", "NO_BET"]
EXECUTION_SORT = {name: idx for idx, name in enumerate(EXECUTION_ORDER, start=1)}
FEATURE_WEIGHTS = {
    "trust_band_v1": 0.35,
    "gap_1_3_band": 0.25,
    "dominance_certainty_band": 0.20,
    "field_size_bucket": 0.10,
    "gap_1_2_band": 0.10,
}
PROFILE_BASE_PERMISSION = {
    "ELITE": "FULL_EXECUTION",
    "STRONG": "FULL_EXECUTION",
    "STANDARD": "REDUCED_EXECUTION",
    "CHAOTIC": "WATCH_ONLY",
}
PROFILE_REASON = {
    "ELITE": "ELITE_RACE",
    "STRONG": "STRONG_RACE",
    "STANDARD": "STANDARD_RISK_REDUCTION",
    "CHAOTIC": "CHAOTIC_RACE",
}


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


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


def build_join_key(df: pd.DataFrame, track_col: str = "track") -> pd.Series:
    race_no = to_num(df["race_no"]).fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df[track_col].map(normalize_track) + "|" + race_no


def build_runner_key(df: pd.DataFrame, track_col: str = "track", horse_key_col: str = "horse_key", horse_col: str = "horse") -> pd.Series:
    horse_component = [normalize_horse_key(horse_key, horse) for horse_key, horse in zip(df[horse_key_col], df[horse_col])]
    return build_join_key(df, track_col=track_col) + "|" + pd.Series(horse_component, index=df.index)


def field_size_bucket(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number <= 7:
        return "LE_7"
    if number <= 10:
        return "8_10"
    if number <= 13:
        return "11_13"
    return "14_PLUS"


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def first_valid_text(values: pd.Series, default: str = "UNKNOWN") -> str:
    clean = values.fillna("").astype(str).map(clean_text)
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def first_valid_numeric(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return math.nan
    return float(clean.iloc[0])


def build_smoothed_score_map(df: pd.DataFrame, category_col: str, outcome_col: str = "top_pick_won") -> pd.DataFrame:
    grouped = (
        df.groupby(category_col, dropna=False)
        .agg(
            races=("join_key_v1", "size"),
            wins=(outcome_col, "sum"),
        )
        .reset_index()
    )
    grouped[category_col] = grouped[category_col].fillna("UNKNOWN").astype(str)
    overall_rate = float(df[outcome_col].mean())
    grouped["raw_top1_rate_v1"] = grouped["wins"] / grouped["races"]
    grouped["smoothed_top1_rate_v1"] = (grouped["wins"] + PRIOR_RACES * overall_rate) / (grouped["races"] + PRIOR_RACES)
    min_rate = float(grouped["smoothed_top1_rate_v1"].min())
    max_rate = float(grouped["smoothed_top1_rate_v1"].max())
    if math.isclose(min_rate, max_rate):
        grouped["feature_score_v1"] = 50.0
    else:
        grouped["feature_score_v1"] = 100.0 * (grouped["smoothed_top1_rate_v1"] - min_rate) / (max_rate - min_rate)
    grouped["feature_score_v1"] = grouped["feature_score_v1"].round(3)
    return grouped


def profile_from_score(value: float, q25: float, q50: float, q75: float) -> str:
    if pd.isna(value):
        return "CHAOTIC"
    if value >= q75:
        return "ELITE"
    if value >= q50:
        return "STRONG"
    if value >= q25:
        return "STANDARD"
    return "CHAOTIC"


def downgrade_permission(permission: str) -> str:
    current_rank = EXECUTION_SORT.get(permission, len(EXECUTION_ORDER)) - 1
    next_rank = min(current_rank + 1, len(EXECUTION_ORDER) - 1)
    return EXECUTION_ORDER[next_rank]


def load_profile_quantiles() -> tuple[float, float, float]:
    if not TRUST_PROFILE_SUMMARY_PATH.exists():
        raise FileNotFoundError(f"Missing trust profile summary file: {TRUST_PROFILE_SUMMARY_PATH}")
    df = pd.read_csv(TRUST_PROFILE_SUMMARY_PATH, low_memory=False)
    if df.empty:
        raise ValueError("Trust profile summary file is empty.")
    return (
        float(to_num(df["learned_q25_v1"]).dropna().iloc[0]),
        float(to_num(df["learned_q50_v1"]).dropna().iloc[0]),
        float(to_num(df["learned_q75_v1"]).dropna().iloc[0]),
    )


def load_historical_replay() -> pd.DataFrame:
    if not HIST_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing historical replay file: {HIST_REPLAY_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
    ]
    df = pd.read_csv(HIST_REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "horse", "horse_key"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_score", "runner_rank", "finish_position", "won"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    df["runner_join_key_v1"] = build_runner_key(df)
    df = df.rename(
        columns={
            "runner_score": "replay_runner_score_v1",
            "runner_rank": "replay_runner_rank_v1",
        }
    )
    return df.copy()


def load_historical_runner_scores() -> pd.DataFrame:
    if not HIST_RUNNER_SCORES_PATH.exists():
        raise FileNotFoundError(f"Missing historical runner score file: {HIST_RUNNER_SCORES_PATH}")

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
    df = pd.read_csv(HIST_RUNNER_SCORES_PATH, low_memory=False, usecols=usecols)
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


def load_historical_trust_race() -> pd.DataFrame:
    if not HIST_TRUST_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing historical trust replay file: {HIST_TRUST_REPLAY_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "join_key_v1",
        "trust_index_v1",
        "trust_band_v1",
        "dominance_certainty_band",
    ]
    df = pd.read_csv(HIST_TRUST_REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "join_key_v1", "trust_band_v1", "dominance_certainty_band"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "trust_index_v1"]:
        df[col] = to_num(df[col])

    if df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)

    race_df = (
        df.groupby("join_key_v1", dropna=False)
        .agg(
            trust_index_v1=("trust_index_v1", first_valid_numeric),
            trust_band_v1_hist=("trust_band_v1", lambda s: first_valid_text(s, "UNKNOWN")),
            dominance_certainty_band=("dominance_certainty_band", lambda s: first_valid_text(s, "UNKNOWN")),
        )
        .reset_index()
    )
    return race_df.copy()


def load_historical_gap_race() -> pd.DataFrame:
    if not HIST_GAP_ENGINE_PATH.exists():
        raise FileNotFoundError(f"Missing historical gap engine file: {HIST_GAP_ENGINE_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "join_key_v1",
        "field_size",
        "top_pick_won",
        "winner_rank",
        "trust_band_v1",
        "gap_1_2_band",
        "gap_1_3_band",
    ]
    df = pd.read_csv(HIST_GAP_ENGINE_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "join_key_v1", "trust_band_v1", "gap_1_2_band", "gap_1_3_band"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "field_size", "top_pick_won", "winner_rank"]:
        df[col] = to_num(df[col])

    if df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)

    df["field_size_bucket"] = df["field_size"].apply(field_size_bucket)
    return df.copy()


def build_historical_trust_profiles() -> pd.DataFrame:
    gap_df = load_historical_gap_race()
    trust_race_df = load_historical_trust_race()

    race_df = gap_df.merge(trust_race_df, on="join_key_v1", how="left")
    race_df["dominance_certainty_band"] = race_df["dominance_certainty_band"].fillna("UNKNOWN")
    race_df["trust_band_v1"] = race_df["trust_band_v1"].replace("", pd.NA)
    race_df["trust_band_v1"] = race_df["trust_band_v1"].fillna(race_df["trust_band_v1_hist"]).fillna("UNKNOWN")

    feature_maps: dict[str, dict[str, float]] = {}
    for feature_name in FEATURE_WEIGHTS:
        feature_map_df = build_smoothed_score_map(race_df, feature_name)
        feature_maps[feature_name] = dict(zip(feature_map_df[feature_name], feature_map_df["feature_score_v1"]))

    for feature_name, mapping in feature_maps.items():
        race_df[f"{feature_name}_score_v1"] = race_df[feature_name].map(mapping).fillna(50.0)

    race_df["trust_profile_score_v1"] = (
        FEATURE_WEIGHTS["trust_band_v1"] * race_df["trust_band_v1_score_v1"]
        + FEATURE_WEIGHTS["gap_1_3_band"] * race_df["gap_1_3_band_score_v1"]
        + FEATURE_WEIGHTS["dominance_certainty_band"] * race_df["dominance_certainty_band_score_v1"]
        + FEATURE_WEIGHTS["field_size_bucket"] * race_df["field_size_bucket_score_v1"]
        + FEATURE_WEIGHTS["gap_1_2_band"] * race_df["gap_1_2_band_score_v1"]
    ).round(3)

    q25, q50, q75 = load_profile_quantiles()
    race_df["trust_profile_v1"] = race_df["trust_profile_score_v1"].apply(lambda value: profile_from_score(value, q25, q50, q75))

    out_cols = [
        "join_key_v1",
        "field_size",
        "field_size_bucket",
        "trust_index_v1",
        "trust_band_v1",
        "gap_1_2_band",
        "gap_1_3_band",
        "dominance_certainty_band",
        "trust_profile_score_v1",
        "trust_profile_v1",
    ]
    return race_df[out_cols].drop_duplicates(subset=["join_key_v1"]).copy()


def determine_execution(row: pd.Series) -> tuple[str, str]:
    trust_profile = clean_text(row.get("trust_profile_v1", "")).upper()
    runner_rank = pd.to_numeric(pd.Series([row.get("runner_rank_hist_v1")]), errors="coerce").iloc[0]
    trust_index = pd.to_numeric(pd.Series([row.get("trust_index_v1")]), errors="coerce").iloc[0]

    permission = PROFILE_BASE_PERMISSION.get(trust_profile, "NO_BET")
    reasons: list[str] = [PROFILE_REASON.get(trust_profile, "UNKNOWN_PROFILE")]

    if not pd.isna(runner_rank) and runner_rank > 5:
        permission = downgrade_permission(permission)
        reasons.append("DEEP_RANK")

    if not pd.isna(trust_index) and trust_index < 25:
        permission = "NO_BET"
        reasons.append("LOW_TRUST_INDEX")

    if trust_profile == "CHAOTIC" and not pd.isna(runner_rank) and runner_rank > 3:
        permission = "NO_BET"
        if "CHAOTIC_RACE" not in reasons:
            reasons.append("CHAOTIC_RACE")

    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)

    return permission, "|".join(deduped)


def build_execution_replay() -> pd.DataFrame:
    replay_df = load_historical_replay()
    scores_df = load_historical_runner_scores()
    trust_profile_df = build_historical_trust_profiles()

    runner_df = replay_df.merge(scores_df, on="runner_join_key_v1", how="left")
    runner_df = runner_df.merge(trust_profile_df, on="join_key_v1", how="left")

    runner_df["governance_band_hist_v1"] = runner_df["governance_band_hist_v1"].fillna("UNKNOWN")
    runner_df["runner_score_hist_v1"] = to_num(runner_df["runner_score_hist_v1"]).fillna(to_num(runner_df["replay_runner_score_v1"]))
    runner_df["runner_rank_hist_v1"] = to_num(runner_df["runner_rank_hist_v1"]).fillna(to_num(runner_df["replay_runner_rank_v1"]))
    runner_df["trust_index_v1"] = to_num(runner_df["trust_index_v1"])
    runner_df["trust_band_v1"] = runner_df["trust_band_v1"].fillna("UNKNOWN")
    runner_df["trust_profile_v1"] = runner_df["trust_profile_v1"].fillna("UNKNOWN")
    runner_df["trust_profile_score_v1"] = to_num(runner_df["trust_profile_score_v1"])

    execution_cols = runner_df.apply(determine_execution, axis=1, result_type="expand")
    runner_df["execution_permission_v1"] = execution_cols[0]
    runner_df["execution_reason_v1"] = execution_cols[1]
    runner_df["execution_permission_sort_v1"] = runner_df["execution_permission_v1"].map(EXECUTION_SORT).fillna(999)

    sorted_df = runner_df.sort_values(
        ["join_key_v1", "runner_rank_hist_v1", "runner_score_hist_v1", "horse"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)
    race_execution_df = (
        sorted_df.groupby("join_key_v1", sort=False)
        .agg(
            race_execution_class_v1=("execution_permission_v1", lambda s: first_valid_text(s, "NO_BET")),
            top_ranked_horse_v1=("horse", lambda s: first_valid_text(s, "")),
        )
        .reset_index()
    )

    runner_df = runner_df.merge(race_execution_df, on="join_key_v1", how="left")
    runner_df = runner_df.sort_values(
        ["join_key_v1", "runner_rank_hist_v1", "runner_score_hist_v1", "horse"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)

    out_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "replay_runner_score_v1",
        "replay_runner_rank_v1",
        "finish_position",
        "won",
        "governance_band_hist_v1",
        "trust_index_v1",
        "trust_band_v1",
        "trust_profile_score_v1",
        "trust_profile_v1",
        "execution_permission_v1",
        "execution_reason_v1",
        "race_execution_class_v1",
        "top_ranked_horse_v1",
        "join_key_v1",
        "runner_join_key_v1",
    ]
    return runner_df[out_cols].copy()


def build_summary(execution_df: pd.DataFrame) -> pd.DataFrame:
    total_races = int(execution_df["join_key_v1"].nunique())
    winners_df = execution_df[execution_df["won"].eq(1)].copy()
    total_winner_rows = int(len(winners_df))

    baseline_top1 = float(winners_df["replay_runner_rank_v1"].eq(1).mean()) if total_winner_rows else math.nan
    baseline_top3 = float(winners_df["replay_runner_rank_v1"].le(3).mean()) if total_winner_rows else math.nan
    baseline_top5 = float(winners_df["replay_runner_rank_v1"].le(5).mean()) if total_winner_rows else math.nan
    baseline_avg_rank = float(winners_df["replay_runner_rank_v1"].mean()) if total_winner_rows else math.nan

    race_class_df = execution_df[["join_key_v1", "race_execution_class_v1"]].drop_duplicates().copy()

    rows: list[dict[str, object]] = [
        {
            "execution_class_v1": "ALL_BASELINE",
            "races": total_races,
            "winner_rows": total_winner_rows,
            "winner_top1_rate": baseline_top1,
            "winner_top3_rate": baseline_top3,
            "winner_top5_rate": baseline_top5,
            "avg_winner_rank": baseline_avg_rank,
            "race_retention_pct": 1.0,
            "winner_retention_pct": 1.0,
            "improvement_vs_baseline_top1": 0.0,
            "improvement_vs_baseline_top3": 0.0,
            "improvement_vs_baseline_top5": 0.0,
            "improvement_vs_baseline_avg_rank": 0.0,
            "sort_order_v1": 0,
        }
    ]

    for sort_order, execution_class in enumerate(EXECUTION_ORDER, start=1):
        subset_races = race_class_df[race_class_df["race_execution_class_v1"].eq(execution_class)]["join_key_v1"]
        race_count = int(len(subset_races))
        subset_winners = winners_df[winners_df["join_key_v1"].isin(subset_races)].copy()
        winner_rows = int(len(subset_winners))

        top1 = float(subset_winners["replay_runner_rank_v1"].eq(1).mean()) if winner_rows else math.nan
        top3 = float(subset_winners["replay_runner_rank_v1"].le(3).mean()) if winner_rows else math.nan
        top5 = float(subset_winners["replay_runner_rank_v1"].le(5).mean()) if winner_rows else math.nan
        avg_rank = float(subset_winners["replay_runner_rank_v1"].mean()) if winner_rows else math.nan

        rows.append(
            {
                "execution_class_v1": execution_class,
                "races": race_count,
                "winner_rows": winner_rows,
                "winner_top1_rate": top1,
                "winner_top3_rate": top3,
                "winner_top5_rate": top5,
                "avg_winner_rank": avg_rank,
                "race_retention_pct": safe_div(race_count, total_races),
                "winner_retention_pct": safe_div(winner_rows, total_winner_rows),
                "improvement_vs_baseline_top1": top1 - baseline_top1 if pd.notna(top1) and pd.notna(baseline_top1) else math.nan,
                "improvement_vs_baseline_top3": top3 - baseline_top3 if pd.notna(top3) and pd.notna(baseline_top3) else math.nan,
                "improvement_vs_baseline_top5": top5 - baseline_top5 if pd.notna(top5) and pd.notna(baseline_top5) else math.nan,
                "improvement_vs_baseline_avg_rank": baseline_avg_rank - avg_rank if pd.notna(avg_rank) and pd.notna(baseline_avg_rank) else math.nan,
                "sort_order_v1": sort_order,
            }
        )

    summary_df = pd.DataFrame(rows).sort_values(["sort_order_v1", "execution_class_v1"]).drop(columns=["sort_order_v1"])
    return summary_df.copy()


def main() -> None:
    execution_df = build_execution_replay()
    summary_df = build_summary(execution_df)

    execution_df.to_csv(REPLAY_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)

    print("[HISTORICAL_EXECUTION_GOVERNANCE_REPLAY_V1] COMPLETE")
    print(f"replay_out={REPLAY_OUT}")
    print(f"summary_out={SUMMARY_OUT}")
    print(f"rows={len(execution_df)}")
    print(f"races={execution_df['join_key_v1'].nunique()}")
    print(f"baseline_top1={float(summary_df.loc[summary_df['execution_class_v1'].eq('ALL_BASELINE'), 'winner_top1_rate'].iloc[0]):.6f}")


if __name__ == "__main__":
    main()
