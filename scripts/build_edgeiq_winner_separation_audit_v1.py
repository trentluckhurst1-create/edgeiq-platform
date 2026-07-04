from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
HIST_SCORES_PATH = DATA / "edgeiq_historical_runner_scores_v1.csv"

AUDIT_OUT = DATA / "edgeiq_winner_separation_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_winner_separation_audit_v1_summary.csv"
FEATURES_OUT = DATA / "edgeiq_winner_vs_contender_features_v1.csv"

FIELD_SIZE_ORDER = list(range(1, 41))
RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS", "UNKNOWN"]
PERCENTILE_BUCKET_ORDER = [
    "00_09", "10_19", "20_29", "30_39", "40_49", "50_59", "60_69", "70_79", "80_89", "90_100", "UNKNOWN"
]
GAP_BUCKET_ORDER = [
    "LT_NEG10", "NEG10_TO_NEG5", "NEG5_TO_NEG2", "NEG2_TO_0", "ZERO_TO_2", "TWO_TO_5", "FIVE_TO_10", "TEN_PLUS", "UNKNOWN"
]
FINISH_GROUP_ORDER = ["WINNERS", "SECONDS", "THIRDS", "OTHERS"]
GOVERNANCE_ORDER = [
    "PROVEN",
    "LIMITED_DATA_3_4_STARTS",
    "LIMITED_DATA_2_STARTS",
    "LIMITED_DATA_1_START",
    "IMPORT_UNKNOWN",
    "FIRST_STARTER_OR_UNKNOWN",
    "UNKNOWN",
]


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


def norm_track(value: object) -> str:
    text = upper_text(value)
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM "]:
        text = text.replace(prefix, "")
    return re.sub(r"\s+", " ", text).strip()


def to_float(value: object) -> float:
    if value is None or pd.isna(value):
        return math.nan
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else math.nan
    text = str(value).replace("$", "").replace(",", "").strip()
    if text == "":
        return math.nan
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return math.nan
    try:
        number = float(match.group(0))
    except ValueError:
        return math.nan
    return number if math.isfinite(number) else math.nan


def to_int(value: object) -> float:
    number = to_float(value)
    if pd.isna(number):
        return math.nan
    return int(number)


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator is None or pd.isna(denominator) or float(denominator) == 0.0:
        return math.nan
    return float(numerator) / float(denominator)


def rank_bucket(rank_value: object) -> str:
    rank_num = to_int(rank_value)
    if pd.isna(rank_num):
        return "UNKNOWN"
    if rank_num == 1:
        return "RANK_1"
    if rank_num == 2:
        return "RANK_2"
    if rank_num == 3:
        return "RANK_3"
    if rank_num <= 5:
        return "RANK_4_5"
    if rank_num <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def percentile_bucket(value: object) -> str:
    number = to_float(value)
    if pd.isna(number):
        return "UNKNOWN"
    pct = max(0.0, min(1.0, number)) * 100.0
    if pct >= 90.0:
        return "90_100"
    floor = int(pct // 10) * 10
    ceiling = floor + 9
    return f"{floor:02d}_{ceiling:02d}"


def gap_bucket(value: object) -> str:
    number = to_float(value)
    if pd.isna(number):
        return "UNKNOWN"
    if number < -10:
        return "LT_NEG10"
    if number < -5:
        return "NEG10_TO_NEG5"
    if number < -2:
        return "NEG5_TO_NEG2"
    if number < 0:
        return "NEG2_TO_0"
    if number < 2:
        return "ZERO_TO_2"
    if number < 5:
        return "TWO_TO_5"
    if number < 10:
        return "FIVE_TO_10"
    return "TEN_PLUS"


def finish_group(value: object) -> str:
    pos = to_int(value)
    if pd.isna(pos):
        return "OTHERS"
    if pos == 1:
        return "WINNERS"
    if pos == 2:
        return "SECONDS"
    if pos == 3:
        return "THIRDS"
    return "OTHERS"


def pooled_standardized_gap(winners: pd.Series, others: pd.Series) -> float:
    winners_clean = pd.to_numeric(winners, errors="coerce").dropna()
    others_clean = pd.to_numeric(others, errors="coerce").dropna()
    if len(winners_clean) < 2 or len(others_clean) < 2:
        return math.nan
    winner_mean = float(winners_clean.mean())
    other_mean = float(others_clean.mean())
    winner_var = float(winners_clean.var(ddof=0))
    other_var = float(others_clean.var(ddof=0))
    pooled = math.sqrt((winner_var + other_var) / 2.0)
    if pooled <= 0:
        return math.nan
    return (winner_mean - other_mean) / pooled


def load_replay() -> pd.DataFrame:
    if not REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing replay file: {REPLAY_PATH}")
    df = pd.read_csv(REPLAY_PATH, low_memory=False)
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["runner_score"] = pd.to_numeric(df["runner_score"], errors="coerce")
    df["runner_rank"] = pd.to_numeric(df["runner_rank"], errors="coerce")
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0).astype(int)
    df["join_track_v1"] = df["track_norm"].fillna(df["track"]).map(norm_track)
    df["join_horse_v1"] = df["horse_key"].fillna(df["horse"].map(canon_horse)).astype(str)
    df["governance_band_v1"] = df["projection_status_v6"].fillna("UNKNOWN").replace({"": "UNKNOWN"}).astype(str)
    return df


def load_hist_scores() -> pd.DataFrame:
    if not HIST_SCORES_PATH.exists():
        raise FileNotFoundError(f"Missing historical runner score file: {HIST_SCORES_PATH}")
    df = pd.read_csv(HIST_SCORES_PATH, low_memory=False)
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["join_track_v1"] = df["track"].map(norm_track)
    df["join_horse_v1"] = df["horse_key"].fillna(df["horse"].map(canon_horse)).astype(str)
    df["field_size_hist_v1"] = pd.to_numeric(df.get("field_size"), errors="coerce")
    df["governance_band_hist_v1"] = df.get("governance_band_hist_v1", pd.Series("UNKNOWN", index=df.index)).fillna("UNKNOWN").astype(str)
    df["runner_score_hist_v1"] = pd.to_numeric(df.get("runner_score_hist_v1"), errors="coerce")
    df["runner_rank_hist_v1"] = pd.to_numeric(df.get("runner_rank_hist_v1"), errors="coerce")
    keep = [
        "meeting_date",
        "race_no",
        "join_track_v1",
        "join_horse_v1",
        "field_size_hist_v1",
        "governance_band_hist_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
    ]
    df = df[keep].drop_duplicates(subset=["meeting_date", "race_no", "join_track_v1", "join_horse_v1"], keep="last")
    return df


def build_runner_features(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for race_key, race in df.groupby("race_key", sort=False):
        race = race.copy()
        race = race.sort_values(["runner_score", "runner_rank", "horse"], ascending=[False, True, True]).reset_index(drop=True)

        scores = pd.to_numeric(race["runner_score"], errors="coerce")
        top_scores = scores.tolist()
        top1_score = top_scores[0] if len(top_scores) >= 1 else math.nan
        top2_score = top_scores[1] if len(top_scores) >= 2 else math.nan
        top3_score = top_scores[2] if len(top_scores) >= 3 else math.nan
        total_score = float(scores.sum()) if len(scores) else math.nan
        avg_score = float(scores.mean()) if len(scores) else math.nan
        min_score = float(scores.min()) if len(scores) else math.nan
        max_score = float(scores.max()) if len(scores) else math.nan
        score_range = max_score - min_score if not (pd.isna(max_score) or pd.isna(min_score)) else math.nan
        field_size = int(len(race))

        for row in race.itertuples(index=False):
            score = to_float(getattr(row, "runner_score"))
            if pd.isna(score_range) or score_range <= 0:
                score_pct = 0.5
            else:
                score_pct = (score - min_score) / score_range

            rows.append(
                {
                    "meeting_date": row.meeting_date,
                    "track": row.track,
                    "race_no": row.race_no,
                    "race_key": row.race_key,
                    "horse": row.horse,
                    "horse_key": row.horse_key,
                    "runner_score": score,
                    "runner_rank": to_int(getattr(row, "runner_rank")),
                    "finish_position": to_int(getattr(row, "finish_position")),
                    "won": int(getattr(row, "won")),
                    "placed": int(getattr(row, "finish_position") <= 3),
                    "finish_group_v1": finish_group(getattr(row, "finish_position")),
                    "governance_band_v1": getattr(row, "governance_band_v1"),
                    "field_size_v1": field_size,
                    "score_minus_race_avg": score - avg_score if not pd.isna(score) and not pd.isna(avg_score) else math.nan,
                    "score_minus_rank2": score - top2_score if not pd.isna(score) and not pd.isna(top2_score) else math.nan,
                    "score_minus_rank3": score - top3_score if not pd.isna(score) and not pd.isna(top3_score) else math.nan,
                    "score_percentile": score_pct,
                    "score_percentile_bucket_v1": percentile_bucket(score_pct),
                    "score_share_of_total_race_score": score / total_score if not pd.isna(score) and not pd.isna(total_score) and total_score != 0 else math.nan,
                    "score_minus_rank2_bucket_v1": gap_bucket(score - top2_score if not pd.isna(score) and not pd.isna(top2_score) else math.nan),
                    "rank_bucket_v1": rank_bucket(getattr(row, "runner_rank")),
                    "runner_score_hist_v1": to_float(getattr(row, "runner_score_hist_v1")),
                    "runner_rank_hist_v1": to_float(getattr(row, "runner_rank_hist_v1")),
                    "legacy_match_found_v1": int(not pd.isna(getattr(row, "runner_score_hist_v1")) or not pd.isna(getattr(row, "runner_rank_hist_v1"))),
                }
            )

    features = pd.DataFrame(rows)
    return features


def build_race_audit(df: pd.DataFrame, features_df: pd.DataFrame) -> pd.DataFrame:
    feature_lookup = features_df.set_index(["race_key", "horse_key"])
    rows: list[dict[str, object]] = []

    for race_key, race in df.groupby("race_key", sort=False):
        race = race.copy()
        race_sorted = race.sort_values(["runner_score", "runner_rank", "horse"], ascending=[False, True, True]).reset_index(drop=True)
        top_ranked = race_sorted.iloc[0] if len(race_sorted) >= 1 else None
        second_ranked = race_sorted.iloc[1] if len(race_sorted) >= 2 else None
        third_ranked = race_sorted.iloc[2] if len(race_sorted) >= 3 else None

        winners = race[race["finish_position"].eq(1)].copy()
        winners = winners.sort_values(["runner_rank", "runner_score", "horse"], ascending=[True, False, True]).reset_index(drop=True)
        if winners.empty:
            continue
        winner = winners.iloc[0]
        feature_key = (winner["race_key"], winner["horse_key"])
        winner_feature = feature_lookup.loc[feature_key] if feature_key in feature_lookup.index else None

        top_score = to_float(top_ranked["runner_score"]) if top_ranked is not None else math.nan
        second_score = to_float(second_ranked["runner_score"]) if second_ranked is not None else math.nan
        third_score = to_float(third_ranked["runner_score"]) if third_ranked is not None else math.nan
        winner_score = to_float(winner["runner_score"])
        winner_rank = to_int(winner["runner_rank"])
        winner_percentile = float(winner_feature["score_percentile"]) if winner_feature is not None else math.nan
        field_size = int(len(race))

        rows.append(
            {
                "meeting_date": winner["meeting_date"],
                "track": winner["track"],
                "race_no": winner["race_no"],
                "race_key": winner["race_key"],
                "winner_horse": winner["horse"],
                "winner_score": winner_score,
                "second_score": second_score,
                "third_score": third_score,
                "top_ranked_horse": top_ranked["horse"] if top_ranked is not None else "",
                "top_ranked_score": top_score,
                "score_gap_winner_to_second": winner_score - second_score if not pd.isna(winner_score) and not pd.isna(second_score) else math.nan,
                "score_gap_winner_to_top_ranked": winner_score - top_score if not pd.isna(winner_score) and not pd.isna(top_score) else math.nan,
                "score_gap_top_ranked_to_second": top_score - second_score if not pd.isna(top_score) and not pd.isna(second_score) else math.nan,
                "winner_rank": winner_rank,
                "winner_rank_bucket_v1": rank_bucket(winner_rank),
                "winner_governance": winner["governance_band_v1"],
                "winner_field_size": field_size,
                "winner_percentile_within_race": winner_percentile,
                "winner_percentile_bucket_v1": percentile_bucket(winner_percentile),
                "score_gap_bucket_v1": gap_bucket(top_score - second_score if not pd.isna(top_score) and not pd.isna(second_score) else math.nan),
                "winner_rank1_flag_v1": int(winner_rank == 1),
                "winner_top3_flag_v1": int(not pd.isna(winner_rank) and winner_rank <= 3),
                "winner_top5_flag_v1": int(not pd.isna(winner_rank) and winner_rank <= 5),
                "winner_count_in_race_v1": int(len(winners)),
                "dead_heat_winner_flag_v1": int(len(winners) > 1),
            }
        )

    return pd.DataFrame(rows)


def build_runner_rate_table(features_df: pd.DataFrame, group_col: str, section: str, sort_order: list[str] | None = None) -> pd.DataFrame:
    grouped = (
        features_df.groupby(group_col, dropna=False)
        .agg(
            runners=("horse", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_finish=("finish_position", "mean"),
            avg_rank=("runner_rank", "mean"),
            avg_score=("runner_score", "mean"),
        )
        .reset_index()
        .rename(columns={group_col: "bucket"})
    )
    grouped["section"] = section
    grouped["win_rate"] = grouped["wins"] / grouped["runners"]
    grouped["place_rate"] = grouped["places"] / grouped["runners"]
    grouped["races"] = np.nan
    grouped["avg_winner_rank"] = np.nan
    grouped["winner_rank1_rate"] = np.nan
    grouped["avg_winner_percentile"] = np.nan
    grouped["feature_name"] = ""
    grouped["winner_mean"] = np.nan
    grouped["second_mean"] = np.nan
    grouped["third_mean"] = np.nan
    grouped["others_mean"] = np.nan
    grouped["winner_minus_others"] = np.nan
    grouped["standardized_gap_v1"] = np.nan
    grouped["metric"] = ""
    grouped["value"] = np.nan

    if sort_order is not None:
        grouped["sort_order"] = grouped["bucket"].map({value: idx for idx, value in enumerate(sort_order, start=1)}).fillna(999)
        grouped = grouped.sort_values(["sort_order", "bucket"]).drop(columns=["sort_order"])
    else:
        grouped = grouped.sort_values(["bucket"])
    return grouped


def build_race_table(audit_df: pd.DataFrame, group_col: str, section: str, sort_order: list[str] | None = None) -> pd.DataFrame:
    grouped = (
        audit_df.groupby(group_col, dropna=False)
        .agg(
            races=("race_key", "size"),
            avg_winner_rank=("winner_rank", "mean"),
            winner_rank1_rate=("winner_rank1_flag_v1", "mean"),
            winner_top3_rate=("winner_top3_flag_v1", "mean"),
            winner_top5_rate=("winner_top5_flag_v1", "mean"),
            avg_winner_percentile=("winner_percentile_within_race", "mean"),
            avg_winner_score=("winner_score", "mean"),
            avg_gap_top_to_second=("score_gap_top_ranked_to_second", "mean"),
        )
        .reset_index()
        .rename(columns={group_col: "bucket"})
    )
    grouped["section"] = section
    grouped["runners"] = np.nan
    grouped["wins"] = np.nan
    grouped["places"] = np.nan
    grouped["win_rate"] = np.nan
    grouped["place_rate"] = np.nan
    grouped["avg_finish"] = np.nan
    grouped["avg_rank"] = np.nan
    grouped["avg_score"] = np.nan
    grouped["feature_name"] = ""
    grouped["winner_mean"] = np.nan
    grouped["second_mean"] = np.nan
    grouped["third_mean"] = np.nan
    grouped["others_mean"] = np.nan
    grouped["winner_minus_others"] = np.nan
    grouped["standardized_gap_v1"] = np.nan
    grouped["metric"] = ""
    grouped["value"] = np.nan

    if sort_order is not None:
        grouped["sort_order"] = grouped["bucket"].map({value: idx for idx, value in enumerate(sort_order, start=1)}).fillna(999)
        grouped = grouped.sort_values(["sort_order", "bucket"]).drop(columns=["sort_order"])
    else:
        grouped = grouped.sort_values(["bucket"])
    return grouped


def build_feature_separation_table(features_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    winners = features_df[features_df["finish_group_v1"] == "WINNERS"].copy()
    seconds = features_df[features_df["finish_group_v1"] == "SECONDS"].copy()
    thirds = features_df[features_df["finish_group_v1"] == "THIRDS"].copy()
    others = features_df[features_df["finish_group_v1"] == "OTHERS"].copy()

    feature_columns = [
        "score_minus_race_avg",
        "score_minus_rank2",
        "score_minus_rank3",
        "score_percentile",
        "score_share_of_total_race_score",
    ]

    for feature_name in feature_columns:
        winner_series = pd.to_numeric(winners[feature_name], errors="coerce")
        second_series = pd.to_numeric(seconds[feature_name], errors="coerce")
        third_series = pd.to_numeric(thirds[feature_name], errors="coerce")
        other_series = pd.to_numeric(others[feature_name], errors="coerce")
        winner_mean = float(winner_series.mean()) if len(winner_series.dropna()) else math.nan
        second_mean = float(second_series.mean()) if len(second_series.dropna()) else math.nan
        third_mean = float(third_series.mean()) if len(third_series.dropna()) else math.nan
        other_mean = float(other_series.mean()) if len(other_series.dropna()) else math.nan
        rows.append(
            {
                "section": "FEATURE_SEPARATION_RANKING",
                "bucket": "",
                "runners": np.nan,
                "wins": np.nan,
                "places": np.nan,
                "win_rate": np.nan,
                "place_rate": np.nan,
                "avg_finish": np.nan,
                "avg_rank": np.nan,
                "avg_score": np.nan,
                "races": np.nan,
                "avg_winner_rank": np.nan,
                "winner_rank1_rate": np.nan,
                "winner_top3_rate": np.nan,
                "winner_top5_rate": np.nan,
                "avg_winner_percentile": np.nan,
                "avg_winner_score": np.nan,
                "avg_gap_top_to_second": np.nan,
                "feature_name": feature_name,
                "winner_mean": winner_mean,
                "second_mean": second_mean,
                "third_mean": third_mean,
                "others_mean": other_mean,
                "winner_minus_others": winner_mean - other_mean if not pd.isna(winner_mean) and not pd.isna(other_mean) else math.nan,
                "standardized_gap_v1": pooled_standardized_gap(winner_series, other_series),
                "metric": "",
                "value": np.nan,
            }
        )

    out = pd.DataFrame(rows)
    out = out.sort_values(["standardized_gap_v1", "winner_minus_others"], ascending=[False, False])
    return out


def build_overall_metrics(replay_df: pd.DataFrame, audit_df: pd.DataFrame, features_df: pd.DataFrame) -> pd.DataFrame:
    legacy_match_rate = safe_rate(features_df["legacy_match_found_v1"].sum(), len(features_df))
    dead_heat_races = int(audit_df["dead_heat_winner_flag_v1"].sum())
    best_feature_row = build_feature_separation_table(features_df).head(1)
    best_feature_name = best_feature_row.iloc[0]["feature_name"] if not best_feature_row.empty else ""
    best_feature_gap = float(best_feature_row.iloc[0]["standardized_gap_v1"]) if not best_feature_row.empty else math.nan

    rows = [
        {"section": "OVERALL_METRICS", "metric": "races", "value": int(audit_df["race_key"].nunique())},
        {"section": "OVERALL_METRICS", "metric": "runner_rows", "value": int(len(features_df))},
        {"section": "OVERALL_METRICS", "metric": "dead_heat_races", "value": dead_heat_races},
        {"section": "OVERALL_METRICS", "metric": "rank1_winner_rate", "value": float(audit_df["winner_rank1_flag_v1"].mean())},
        {"section": "OVERALL_METRICS", "metric": "top3_winner_rate", "value": float(audit_df["winner_top3_flag_v1"].mean())},
        {"section": "OVERALL_METRICS", "metric": "top5_winner_rate", "value": float(audit_df["winner_top5_flag_v1"].mean())},
        {"section": "OVERALL_METRICS", "metric": "avg_winner_rank", "value": float(audit_df["winner_rank"].mean())},
        {"section": "OVERALL_METRICS", "metric": "avg_winner_percentile", "value": float(audit_df["winner_percentile_within_race"].mean())},
        {"section": "OVERALL_METRICS", "metric": "avg_gap_top_ranked_to_second", "value": float(audit_df["score_gap_top_ranked_to_second"].mean())},
        {"section": "OVERALL_METRICS", "metric": "legacy_hist_score_match_rate", "value": legacy_match_rate},
        {"section": "OVERALL_METRICS", "metric": "best_separation_feature_v1", "value": best_feature_name},
        {"section": "OVERALL_METRICS", "metric": "best_separation_standardized_gap_v1", "value": best_feature_gap},
    ]
    out = pd.DataFrame(rows)
    for col in [
        "bucket", "runners", "wins", "places", "win_rate", "place_rate", "avg_finish", "avg_rank", "avg_score", "races",
        "avg_winner_rank", "winner_rank1_rate", "winner_top3_rate", "winner_top5_rate", "avg_winner_percentile", "avg_winner_score",
        "avg_gap_top_to_second", "feature_name", "winner_mean", "second_mean", "third_mean", "others_mean", "winner_minus_others", "standardized_gap_v1"
    ]:
        out[col] = np.nan if col != "bucket" and col != "feature_name" else ""
    return out


def main() -> None:
    replay = load_replay()
    hist_scores = load_hist_scores()

    merged = replay.merge(
        hist_scores,
        on=["meeting_date", "race_no", "join_track_v1", "join_horse_v1"],
        how="left",
    )

    merged["governance_band_v1"] = np.where(
        merged["governance_band_v1"].fillna("") != "",
        merged["governance_band_v1"],
        merged["governance_band_hist_v1"].fillna("UNKNOWN"),
    )

    features = build_runner_features(merged)
    features.to_csv(FEATURES_OUT, index=False)

    audit = build_race_audit(merged, features)
    audit.to_csv(AUDIT_OUT, index=False)

    runner_by_field_size = build_runner_rate_table(features, "field_size_v1", "RUNNER_WIN_RATE_BY_FIELD_SIZE")
    runner_by_score_pct = build_runner_rate_table(features, "score_percentile_bucket_v1", "RUNNER_WIN_RATE_BY_SCORE_PERCENTILE", PERCENTILE_BUCKET_ORDER)
    runner_by_gap = build_runner_rate_table(features, "score_minus_rank2_bucket_v1", "RUNNER_WIN_RATE_BY_SCORE_GAP_BUCKET", GAP_BUCKET_ORDER)
    runner_by_gov = build_runner_rate_table(features, "governance_band_v1", "RUNNER_WIN_RATE_BY_GOVERNANCE", GOVERNANCE_ORDER)
    runner_by_rank = build_runner_rate_table(features, "rank_bucket_v1", "RUNNER_WIN_RATE_BY_RANK", RANK_BUCKET_ORDER)

    race_by_field_size = build_race_table(audit, "winner_field_size", "RACE_WINNER_PATTERN_BY_FIELD_SIZE")
    race_by_pct = build_race_table(audit, "winner_percentile_bucket_v1", "RACE_WINNER_PATTERN_BY_PERCENTILE", PERCENTILE_BUCKET_ORDER)
    race_by_gap = build_race_table(audit, "score_gap_bucket_v1", "RACE_WINNER_PATTERN_BY_SCORE_GAP", GAP_BUCKET_ORDER)
    race_by_gov = build_race_table(audit, "winner_governance", "RACE_WINNER_PATTERN_BY_GOVERNANCE", GOVERNANCE_ORDER)
    race_by_rank = build_race_table(audit, "winner_rank_bucket_v1", "RACE_WINNER_PATTERN_BY_RANK", RANK_BUCKET_ORDER)

    feature_separation = build_feature_separation_table(features)
    overall_metrics = build_overall_metrics(merged, audit, features)

    summary = pd.concat(
        [
            overall_metrics,
            feature_separation,
            runner_by_field_size,
            runner_by_score_pct,
            runner_by_gap,
            runner_by_gov,
            runner_by_rank,
            race_by_field_size,
            race_by_pct,
            race_by_gap,
            race_by_gov,
            race_by_rank,
        ],
        ignore_index=True,
        sort=False,
    )
    summary.to_csv(SUMMARY_OUT, index=False)

    print("[EDGEIQ_WINNER_SEPARATION_AUDIT_V1] COMPLETE")
    print(f"race_rows={len(audit)}")
    print(f"runner_rows={len(features)}")
    print(f"dead_heat_races={int(audit['dead_heat_winner_flag_v1'].sum())}")
    print(f"rank1_winner_rate={float(audit['winner_rank1_flag_v1'].mean()):.6f}")
    print(f"avg_winner_rank={float(audit['winner_rank'].mean()):.6f}")
    print(f"audit_out={AUDIT_OUT}")
    print(f"summary_out={SUMMARY_OUT}")
    print(f"features_out={FEATURES_OUT}")


if __name__ == "__main__":
    main()
