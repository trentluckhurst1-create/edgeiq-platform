from __future__ import annotations

import math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_PATH = DATA / "edgeiq_historical_dominance_v2_replay.csv"
ENGINE_OUT = DATA / "edgeiq_certainty_engine_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_certainty_engine_v1_summary.csv"
RULES_OUT = DATA / "edgeiq_certainty_engine_v1_rules.csv"
BEST_CONDITIONS_OUT = DATA / "edgeiq_certainty_engine_v1_best_conditions.csv"

MIN_RULE_RACES = 300


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


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


def gap_1_2_bucket(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number < 2:
        return "0_2"
    if number < 5:
        return "2_5"
    if number < 10:
        return "5_10"
    return "10_PLUS"


def gap_1_3_bucket(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number < 5:
        return "0_5"
    if number < 10:
        return "5_10"
    if number < 15:
        return "10_15"
    return "15_PLUS"


def load_replay() -> pd.DataFrame:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, low_memory=False)
    df["meeting_date"] = df["meeting_date"].astype(str).str[:10]
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")

    numeric_cols = [
        "field_size_v1",
        "runner_score_hist_v1",
        "runner_rank_hist_v1",
        "model_a_runner_only_rank_v1",
        "dominance_score_v1",
        "dominance_strength_ratio",
        "dominance_gap_rank2_pct",
        "dominance_gap_rank3_pct",
        "dominance_certainty_score_v1",
        "finish_position",
        "won",
        "placed",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = to_num(df[col])

    df["horse"] = df["horse"].fillna("")
    df["track"] = df["track"].fillna("")
    df["governance_band_hist_v1"] = df.get("governance_band_hist_v1", "UNKNOWN")
    df["governance_band_hist_v1"] = df["governance_band_hist_v1"].fillna("UNKNOWN").astype(str)
    df["dominance_certainty_v1"] = df.get("dominance_certainty_v1", "UNKNOWN")
    df["dominance_certainty_v1"] = df["dominance_certainty_v1"].fillna("UNKNOWN").astype(str)

    return df.copy()


def resolve_rank_col(df: pd.DataFrame) -> str:
    preferred = [
        "model_a_runner_only_rank_v1",
        "runner_rank_hist_v1",
    ]
    for col in preferred:
        if col in df.columns:
            return col
    rank_candidates = [col for col in df.columns if col.endswith("_rank_v1")]
    if rank_candidates:
        return sorted(rank_candidates)[0]
    raise KeyError("No ranking column found in replay input.")


def resolve_score_col(df: pd.DataFrame) -> str:
    preferred = [
        "runner_score_hist_v1",
        "model_a_runner_only_score_v1",
        "dominance_score_v1",
    ]
    for col in preferred:
        if col in df.columns:
            return col
    raise KeyError("No score column found in replay input.")


def first_valid(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return math.nan
    return float(clean.iloc[0])


def first_text(values: pd.Series, default: str = "UNKNOWN") -> str:
    clean = values.fillna("").astype(str).str.strip()
    clean = clean[clean.ne("")]
    if clean.empty:
        return default
    return str(clean.iloc[0])


def build_race_engine(df: pd.DataFrame, rank_col: str, score_col: str) -> pd.DataFrame:
    ranked = df.copy()
    ranked = ranked.sort_values(
        ["race_key", rank_col, score_col, "horse"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)

    race_rows: list[dict[str, object]] = []
    for race_key, group in ranked.groupby("race_key", sort=False):
        group = group.copy().sort_values([rank_col, score_col, "horse"], ascending=[True, False, True])
        top_row = group.iloc[0]
        top_three = group.head(3)
        scores = top_three[score_col].tolist()
        top_score = float(scores[0]) if len(scores) >= 1 and pd.notna(scores[0]) else math.nan
        second_score = float(scores[1]) if len(scores) >= 2 and pd.notna(scores[1]) else math.nan
        third_score = float(scores[2]) if len(scores) >= 3 and pd.notna(scores[2]) else math.nan
        score_gap_1_2 = top_score - second_score if pd.notna(top_score) and pd.notna(second_score) else math.nan
        score_gap_1_3 = top_score - third_score if pd.notna(top_score) and pd.notna(third_score) else math.nan

        winner_rows = group[group["won"].eq(1)].copy()
        winner_rank = first_valid(winner_rows[rank_col])
        top_pick_won = int(bool((group[rank_col].eq(1) & group["won"].eq(1)).any()))

        race_rows.append(
            {
                "meeting_date": str(top_row["meeting_date"]),
                "track": str(top_row["track"]),
                "race_no": int(top_row["race_no"]) if pd.notna(top_row["race_no"]) else math.nan,
                "race_key": race_key,
                "field_size": int(round(first_valid(group["field_size_v1"]))) if pd.notna(first_valid(group["field_size_v1"])) else int(len(group)),
                "top_pick_horse": str(top_row["horse"]),
                "top_pick_governance_band": str(top_row["governance_band_hist_v1"]),
                "dominance_certainty_band": str(top_row["dominance_certainty_v1"]),
                "dominance_certainty_score": first_valid(pd.Series([top_row.get("dominance_certainty_score_v1")], dtype=float)),
                "top_score": top_score,
                "second_score": second_score,
                "third_score": third_score,
                "score_gap_1_2": score_gap_1_2,
                "score_gap_1_3": score_gap_1_3,
                "winner_rank": winner_rank,
                "top_pick_won": top_pick_won,
            }
        )

    race_df = pd.DataFrame(race_rows)
    race_df["field_size_bucket"] = race_df["field_size"].apply(field_size_bucket)
    race_df["gap_1_2_bucket"] = race_df["score_gap_1_2"].apply(gap_1_2_bucket)
    race_df["gap_1_3_bucket"] = race_df["score_gap_1_3"].apply(gap_1_3_bucket)
    return race_df


def summarise_group(df: pd.DataFrame, group_cols: list[str], section: str) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(
            races=("race_key", "size"),
            top_pick_wins=("top_pick_won", "sum"),
            top_pick_win_rate=("top_pick_won", "mean"),
            avg_winner_rank=("winner_rank", "mean"),
        )
        .reset_index()
    )
    grouped.insert(0, "section", section)
    return grouped


def add_rule_name(df: pd.DataFrame, cols: list[str], rule_type: str) -> pd.DataFrame:
    out = df.copy()
    out["rule_type"] = rule_type
    out["rule_name"] = out[cols].astype(str).agg(" | ".join, axis=1)
    return out


def build_rules(race_df: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [
        "field_size_bucket",
        "gap_1_2_bucket",
        "gap_1_3_bucket",
        "dominance_certainty_band",
        "top_pick_governance_band",
    ]

    targeted_groups: list[tuple[str, list[str]]] = []
    for col in feature_cols:
        targeted_groups.append((f"SINGLE::{col}", [col]))
    for combo in combinations(feature_cols, 2):
        targeted_groups.append((f"PAIR::{'+'.join(combo)}", list(combo)))
    targeted_groups.extend(
        [
            (
                "TRIPLE::field_size_bucket+gap_1_2_bucket+dominance_certainty_band",
                ["field_size_bucket", "gap_1_2_bucket", "dominance_certainty_band"],
            ),
            (
                "TRIPLE::field_size_bucket+gap_1_3_bucket+dominance_certainty_band",
                ["field_size_bucket", "gap_1_3_bucket", "dominance_certainty_band"],
            ),
            (
                "TRIPLE::gap_1_2_bucket+dominance_certainty_band+top_pick_governance_band",
                ["gap_1_2_bucket", "dominance_certainty_band", "top_pick_governance_band"],
            ),
            (
                "TRIPLE::gap_1_3_bucket+dominance_certainty_band+top_pick_governance_band",
                ["gap_1_3_bucket", "dominance_certainty_band", "top_pick_governance_band"],
            ),
        ]
    )

    rule_frames: list[pd.DataFrame] = []
    for rule_type, cols in targeted_groups:
        grouped = (
            race_df.groupby(cols, dropna=False)
            .agg(
                races=("race_key", "size"),
                top_pick_wins=("top_pick_won", "sum"),
                top_pick_win_rate=("top_pick_won", "mean"),
                avg_winner_rank=("winner_rank", "mean"),
            )
            .reset_index()
        )
        grouped = add_rule_name(grouped, cols, rule_type)
        for col in feature_cols:
            if col not in grouped.columns:
                grouped[col] = ""
        grouped["meets_min_300_races"] = grouped["races"].ge(MIN_RULE_RACES)
        grouped = grouped[
            [
                "rule_type",
                "rule_name",
                "field_size_bucket",
                "gap_1_2_bucket",
                "gap_1_3_bucket",
                "dominance_certainty_band",
                "top_pick_governance_band",
                "races",
                "top_pick_wins",
                "top_pick_win_rate",
                "avg_winner_rank",
                "meets_min_300_races",
            ]
        ]
        rule_frames.append(grouped)

    rules_df = pd.concat(rule_frames, ignore_index=True)
    rules_df = rules_df.sort_values(
        ["top_pick_win_rate", "races", "avg_winner_rank", "rule_type", "rule_name"],
        ascending=[False, False, True, True, True],
    ).reset_index(drop=True)
    return rules_df


def build_summary(race_df: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    overall = pd.DataFrame(
        [
            {
                "section": "OVERALL",
                "bucket_type": "ALL_RACES",
                "bucket_value": "ALL",
                "races": int(len(race_df)),
                "top_pick_wins": int(race_df["top_pick_won"].sum()),
                "top_pick_win_rate": float(race_df["top_pick_won"].mean()),
                "avg_winner_rank": float(race_df["winner_rank"].mean()),
            }
        ]
    )
    frames.append(overall)

    section_map = {
        "field_size_bucket": "BY_FIELD_SIZE_BUCKET",
        "gap_1_2_bucket": "BY_GAP_1_2_BUCKET",
        "gap_1_3_bucket": "BY_GAP_1_3_BUCKET",
        "dominance_certainty_band": "BY_DOMINANCE_CERTAINTY_BAND",
        "top_pick_governance_band": "BY_TOP_PICK_GOVERNANCE_BAND",
    }

    for col, section in section_map.items():
        grouped = summarise_group(race_df, [col], section)
        grouped = grouped.rename(columns={col: "bucket_value"})
        grouped.insert(1, "bucket_type", col)
        frames.append(grouped)

    summary_df = pd.concat(frames, ignore_index=True)
    summary_df = summary_df[
        [
            "section",
            "bucket_type",
            "bucket_value",
            "races",
            "top_pick_wins",
            "top_pick_win_rate",
            "avg_winner_rank",
        ]
    ]
    return summary_df


def main() -> None:
    replay_df = load_replay()
    rank_col = resolve_rank_col(replay_df)
    score_col = resolve_score_col(replay_df)

    race_df = build_race_engine(replay_df, rank_col=rank_col, score_col=score_col)
    summary_df = build_summary(race_df)
    rules_df = build_rules(race_df)
    best_conditions_df = rules_df[rules_df["meets_min_300_races"]].copy()
    best_conditions_df = best_conditions_df.sort_values(
        ["top_pick_win_rate", "races", "avg_winner_rank", "rule_type", "rule_name"],
        ascending=[False, False, True, True, True],
    ).reset_index(drop=True)

    race_df.to_csv(ENGINE_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    rules_df.to_csv(RULES_OUT, index=False)
    best_conditions_df.to_csv(BEST_CONDITIONS_OUT, index=False)

    best_row = best_conditions_df.iloc[0] if not best_conditions_df.empty else None

    print("[EDGEIQ_CERTAINTY_ENGINE_V1] COMPLETE")
    print(f"races={len(race_df)}")
    print(f"overall_top_pick_win_rate={float(race_df['top_pick_won'].mean()):.6f}")
    print(f"rank_col={rank_col}")
    print(f"score_col={score_col}")
    print(f"best_conditions_count={len(best_conditions_df)}")
    if best_row is not None:
        print(f"best_rule={best_row['rule_name']}")
        print(f"best_rule_type={best_row['rule_type']}")
        print(f"best_rule_races={int(best_row['races'])}")
        print(f"best_rule_top_pick_win_rate={float(best_row['top_pick_win_rate']):.6f}")
        print(f"best_rule_avg_winner_rank={float(best_row['avg_winner_rank']):.6f}")
    print(f"engine_out={ENGINE_OUT}")
    print(f"summary_out={SUMMARY_OUT}")
    print(f"rules_out={RULES_OUT}")
    print(f"best_conditions_out={BEST_CONDITIONS_OUT}")


if __name__ == "__main__":
    main()
