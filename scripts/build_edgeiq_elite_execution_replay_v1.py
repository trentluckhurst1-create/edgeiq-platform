from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

EXECUTION_REPLAY_PATH = DATA / "historical_execution_governance_replay_v1.csv"
TRUST_PROFILE_ENGINE_PATH = DATA / "edgeiq_trust_profile_engine_v1.csv"
RANK_GAP_ENGINE_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
HISTORICAL_DOMINANCE_REPLAY_PATH = DATA / "edgeiq_historical_dominance_replay_v1.csv"

RACE_OUT = DATA / "edgeiq_elite_execution_replay_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_elite_execution_replay_v1_summary.csv"
BY_RULE_OUT = DATA / "edgeiq_elite_execution_replay_v1_by_rule.csv"

MIN_RACES = 300
RULE_ORDER = ["A", "B", "C", "D", "E", "F", "G"]


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


def first_valid_text(values: pd.Series, default: str = "") -> str:
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


def dominance_certainty_band(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number >= 80:
        return "VERY_HIGH"
    if number >= 65:
        return "HIGH"
    if number >= 50:
        return "MEDIUM"
    return "LOW"


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def load_execution_race_level() -> pd.DataFrame:
    if not EXECUTION_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing historical execution governance replay file: {EXECUTION_REPLAY_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "trust_index_v1",
        "trust_band_v1",
        "trust_profile_score_v1",
        "trust_profile_v1",
        "race_execution_class_v1",
        "join_key_v1",
    ]
    df = pd.read_csv(EXECUTION_REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "horse", "trust_band_v1", "trust_profile_v1", "race_execution_class_v1", "join_key_v1"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "trust_index_v1", "trust_profile_score_v1"]:
        df[col] = to_num(df[col])

    if df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)

    race_df = (
        df.groupby("join_key_v1", dropna=False)
        .agg(
            meeting_date=("meeting_date", lambda s: first_valid_text(s)),
            track=("track", lambda s: first_valid_text(s)),
            race_no=("race_no", first_valid_numeric),
            trust_index_v1=("trust_index_v1", first_valid_numeric),
            trust_band_v1=("trust_band_v1", lambda s: first_valid_text(s, "UNKNOWN")),
            trust_profile_score_v1=("trust_profile_score_v1", first_valid_numeric),
            trust_profile_v1=("trust_profile_v1", lambda s: first_valid_text(s, "UNKNOWN")),
            race_execution_class_v1=("race_execution_class_v1", lambda s: first_valid_text(s, "UNKNOWN")),
        )
        .reset_index()
    )
    race_df["race_no"] = to_num(race_df["race_no"])
    return race_df.copy()


def load_rank_gap_race_level() -> pd.DataFrame:
    if not RANK_GAP_ENGINE_PATH.exists():
        raise FileNotFoundError(f"Missing rank gap engine file: {RANK_GAP_ENGINE_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "join_key_v1",
        "field_size",
        "top_horse",
        "top_score",
        "second_score",
        "third_score",
        "gap_1_2",
        "gap_1_3",
        "score_share_total",
        "top_pick_won",
        "winner_rank",
        "gap_1_2_band",
        "gap_1_3_band",
        "score_share_band",
        "winner_top3_flag_v1",
        "winner_top5_flag_v1",
    ]
    df = pd.read_csv(RANK_GAP_ENGINE_PATH, low_memory=False, usecols=usecols)
    for col in [
        "meeting_date",
        "track",
        "race_key",
        "join_key_v1",
        "top_horse",
        "gap_1_2_band",
        "gap_1_3_band",
        "score_share_band",
    ]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in [
        "race_no",
        "field_size",
        "top_score",
        "second_score",
        "third_score",
        "gap_1_2",
        "gap_1_3",
        "score_share_total",
        "top_pick_won",
        "winner_rank",
        "winner_top3_flag_v1",
        "winner_top5_flag_v1",
    ]:
        df[col] = to_num(df[col])

    if df["join_key_v1"].eq("").all():
        df["join_key_v1"] = build_join_key(df)

    return df.copy()


def load_dominance_race_level() -> pd.DataFrame:
    if not HISTORICAL_DOMINANCE_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing historical dominance replay file: {HISTORICAL_DOMINANCE_REPLAY_PATH}")

    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "runner_rank_hist_v1",
        "runner_score_hist_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "dominance_rank_v1",
    ]
    df = pd.read_csv(HISTORICAL_DOMINANCE_REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "race_key", "horse", "dominance_band_v1"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_rank_hist_v1", "runner_score_hist_v1", "dominance_score_v1", "dominance_rank_v1"]:
        df[col] = to_num(df[col])

    df["join_key_v1"] = build_join_key(df)
    df = df.sort_values(
        ["join_key_v1", "runner_rank_hist_v1", "runner_score_hist_v1", "horse"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)

    top_df = (
        df.groupby("join_key_v1", dropna=False)
        .agg(
            dominance_top_horse_v1=("horse", lambda s: first_valid_text(s)),
            dominance_score_v1=("dominance_score_v1", first_valid_numeric),
            dominance_band_v1=("dominance_band_v1", lambda s: first_valid_text(s, "UNKNOWN")),
        )
        .reset_index()
    )
    top_df["dominance_certainty_v1"] = top_df["dominance_score_v1"].apply(dominance_certainty_band)
    return top_df.copy()


def load_trust_profile_catalog() -> pd.DataFrame:
    if not TRUST_PROFILE_ENGINE_PATH.exists():
        return pd.DataFrame(columns=["trust_profile_v1"])
    df = pd.read_csv(TRUST_PROFILE_ENGINE_PATH, low_memory=False, usecols=["trust_profile_v1"])
    df["trust_profile_v1"] = df["trust_profile_v1"].fillna("").astype(str).map(clean_text)
    return df.drop_duplicates().reset_index(drop=True)


def build_race_frame() -> pd.DataFrame:
    execution_df = load_execution_race_level()
    gap_df = load_rank_gap_race_level()
    dominance_df = load_dominance_race_level()
    _catalog_df = load_trust_profile_catalog()

    race_df = execution_df.merge(gap_df, on="join_key_v1", how="inner", suffixes=("_exec", "_gap"))
    race_df = race_df.merge(dominance_df, on="join_key_v1", how="left")

    race_df["meeting_date"] = race_df["meeting_date_exec"].where(race_df["meeting_date_exec"].ne(""), race_df["meeting_date_gap"])
    race_df["track"] = race_df["track_exec"].where(race_df["track_exec"].ne(""), race_df["track_gap"])
    race_df["race_no"] = race_df["race_no_exec"].where(race_df["race_no_exec"].notna(), race_df["race_no_gap"])

    race_df["winner_top1_flag_v1"] = to_num(race_df["top_pick_won"]).fillna(0).astype(int)
    race_df["winner_top3_flag_v1"] = to_num(race_df["winner_top3_flag_v1"]).fillna(0).astype(int)
    race_df["winner_top5_flag_v1"] = to_num(race_df["winner_top5_flag_v1"]).fillna(0).astype(int)
    race_df["winner_rank"] = to_num(race_df["winner_rank"])

    race_df["rule_set_a_v1"] = race_df["race_execution_class_v1"].eq("FULL_EXECUTION")
    race_df["rule_set_b_v1"] = race_df["rule_set_a_v1"] & race_df["trust_profile_v1"].isin(["ELITE", "STRONG"])
    race_df["rule_set_c_v1"] = race_df["rule_set_b_v1"] & race_df["dominance_certainty_v1"].isin(["VERY_HIGH", "HIGH"])
    race_df["rule_set_d_v1"] = race_df["rule_set_c_v1"] & race_df["gap_1_2_band"].eq("TEN_PLUS")
    race_df["rule_set_e_v1"] = race_df["rule_set_c_v1"] & race_df["gap_1_3_band"].eq("FIFTEEN_PLUS")
    race_df["rule_set_f_v1"] = race_df["rule_set_c_v1"] & race_df["score_share_band"].eq("VERY_HIGH")
    race_df["rule_set_g_v1"] = race_df["rule_set_c_v1"] & race_df["gap_1_2_band"].eq("TEN_PLUS") & race_df["gap_1_3_band"].eq("FIFTEEN_PLUS")

    race_df = race_df[[
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "join_key_v1",
        "field_size",
        "top_horse",
        "top_score",
        "second_score",
        "third_score",
        "gap_1_2",
        "gap_1_3",
        "score_share_total",
        "score_share_band",
        "winner_rank",
        "winner_top1_flag_v1",
        "winner_top3_flag_v1",
        "winner_top5_flag_v1",
        "trust_index_v1",
        "trust_band_v1",
        "trust_profile_score_v1",
        "trust_profile_v1",
        "race_execution_class_v1",
        "gap_1_2_band",
        "gap_1_3_band",
        "dominance_top_horse_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "dominance_certainty_v1",
        "rule_set_a_v1",
        "rule_set_b_v1",
        "rule_set_c_v1",
        "rule_set_d_v1",
        "rule_set_e_v1",
        "rule_set_f_v1",
        "rule_set_g_v1",
    ]].copy()

    race_df = race_df.sort_values(["meeting_date", "track", "race_no"]).reset_index(drop=True)
    return race_df


def summarise_rules(race_df: pd.DataFrame) -> pd.DataFrame:
    total_races = int(len(race_df))
    baseline_top1 = float(race_df["winner_top1_flag_v1"].mean())
    baseline_top3 = float(race_df["winner_top3_flag_v1"].mean())
    baseline_top5 = float(race_df["winner_top5_flag_v1"].mean())
    baseline_avg_rank = float(race_df["winner_rank"].mean())

    rule_meta = {
        "A": "FULL_EXECUTION only",
        "B": "FULL_EXECUTION and trust_profile in ELITE/STRONG",
        "C": "Rule B and dominance_certainty in VERY_HIGH/HIGH",
        "D": "Rule C and gap_1_2_band = TEN_PLUS",
        "E": "Rule C and gap_1_3_band = FIFTEEN_PLUS",
        "F": "Rule C and score_share_band = VERY_HIGH",
        "G": "Rule C and gap_1_2_band = TEN_PLUS and gap_1_3_band = FIFTEEN_PLUS",
    }

    rows: list[dict[str, object]] = []
    for rule_name in RULE_ORDER:
        flag_col = f"rule_set_{rule_name.lower()}_v1"
        subset = race_df[race_df[flag_col]].copy()
        races = int(len(subset))
        top1 = float(subset["winner_top1_flag_v1"].mean()) if races else math.nan
        top3 = float(subset["winner_top3_flag_v1"].mean()) if races else math.nan
        top5 = float(subset["winner_top5_flag_v1"].mean()) if races else math.nan
        avg_rank = float(subset["winner_rank"].mean()) if races else math.nan
        rank1 = float(subset["winner_rank"].eq(1).mean()) if races else math.nan
        rank2 = float(subset["winner_rank"].eq(2).mean()) if races else math.nan
        rank3 = float(subset["winner_rank"].eq(3).mean()) if races else math.nan

        rows.append(
            {
                "rule_set_v1": rule_name,
                "rule_description_v1": rule_meta[rule_name],
                "races": races,
                "race_retention_pct": safe_div(races, total_races),
                "winner_top1_rate": top1,
                "winner_top3_rate": top3,
                "winner_top5_rate": top5,
                "avg_winner_rank": avg_rank,
                "rank1_win_rate": rank1,
                "rank2_win_rate": rank2,
                "rank3_win_rate": rank3,
                "eligible_min_300_races_v1": races >= MIN_RACES,
                "improvement_vs_baseline_top1": top1 - baseline_top1 if pd.notna(top1) else math.nan,
                "improvement_vs_baseline_top3": top3 - baseline_top3 if pd.notna(top3) else math.nan,
                "improvement_vs_baseline_top5": top5 - baseline_top5 if pd.notna(top5) else math.nan,
                "improvement_vs_baseline_avg_rank": baseline_avg_rank - avg_rank if pd.notna(avg_rank) else math.nan,
            }
        )

    by_rule_df = pd.DataFrame(rows)
    by_rule_df["sort_eligible_v1"] = (~by_rule_df["eligible_min_300_races_v1"]).astype(int)
    by_rule_df = by_rule_df.sort_values(
        ["sort_eligible_v1", "winner_top1_rate", "avg_winner_rank", "race_retention_pct", "rule_set_v1"],
        ascending=[True, False, True, False, True],
    ).reset_index(drop=True)
    by_rule_df["ranked_order_v1"] = range(1, len(by_rule_df) + 1)

    eligible_df = by_rule_df[by_rule_df["eligible_min_300_races_v1"]].copy()
    by_rule_df["eligible_rank_v1"] = math.nan
    if not eligible_df.empty:
        eligible_df = eligible_df.sort_values(
            ["winner_top1_rate", "avg_winner_rank", "race_retention_pct", "rule_set_v1"],
            ascending=[False, True, False, True],
        ).reset_index(drop=True)
        eligible_df["eligible_rank_v1"] = range(1, len(eligible_df) + 1)
        by_rule_df = by_rule_df.drop(columns=["eligible_rank_v1"]).merge(
            eligible_df[["rule_set_v1", "eligible_rank_v1"]],
            on="rule_set_v1",
            how="left",
        )

    by_rule_df = by_rule_df.drop(columns=["sort_eligible_v1"])
    return by_rule_df


def build_summary(race_df: pd.DataFrame, by_rule_df: pd.DataFrame) -> pd.DataFrame:
    baseline_top1 = float(race_df["winner_top1_flag_v1"].mean())
    baseline_top3 = float(race_df["winner_top3_flag_v1"].mean())
    baseline_top5 = float(race_df["winner_top5_flag_v1"].mean())
    baseline_avg_rank = float(race_df["winner_rank"].mean())

    eligible_df = by_rule_df[by_rule_df["eligible_min_300_races_v1"]].copy()
    best_row = eligible_df.sort_values(
        ["winner_top1_rate", "avg_winner_rank", "race_retention_pct", "rule_set_v1"],
        ascending=[False, True, False, True],
    ).iloc[0] if not eligible_df.empty else None

    summary_rows: list[dict[str, object]] = [
        {"metric": "baseline_races", "value": int(len(race_df))},
        {"metric": "baseline_winner_top1_rate", "value": baseline_top1},
        {"metric": "baseline_winner_top3_rate", "value": baseline_top3},
        {"metric": "baseline_winner_top5_rate", "value": baseline_top5},
        {"metric": "baseline_avg_winner_rank", "value": baseline_avg_rank},
        {"metric": "minimum_races_required", "value": MIN_RACES},
        {"metric": "eligible_ruleset_count", "value": int(len(eligible_df))},
    ]

    if best_row is not None:
        summary_rows.extend(
            [
                {"metric": "best_ruleset_v1", "value": str(best_row["rule_set_v1"])},
                {"metric": "best_ruleset_description_v1", "value": str(best_row["rule_description_v1"])},
                {"metric": "best_ruleset_races", "value": int(best_row["races"])},
                {"metric": "best_ruleset_race_retention_pct", "value": float(best_row["race_retention_pct"])},
                {"metric": "best_ruleset_winner_top1_rate", "value": float(best_row["winner_top1_rate"])},
                {"metric": "best_ruleset_winner_top3_rate", "value": float(best_row["winner_top3_rate"])},
                {"metric": "best_ruleset_winner_top5_rate", "value": float(best_row["winner_top5_rate"])},
                {"metric": "best_ruleset_avg_winner_rank", "value": float(best_row["avg_winner_rank"])},
            ]
        )

    return pd.DataFrame(summary_rows)


def main() -> None:
    race_df = build_race_frame()
    by_rule_df = summarise_rules(race_df)
    summary_df = build_summary(race_df, by_rule_df)

    race_df.to_csv(RACE_OUT, index=False)
    by_rule_df.to_csv(BY_RULE_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)

    print("[EDGEIQ_ELITE_EXECUTION_REPLAY_V1] COMPLETE")
    print(f"race_out={RACE_OUT}")
    print(f"summary_out={SUMMARY_OUT}")
    print(f"by_rule_out={BY_RULE_OUT}")
    print(f"historical_races={len(race_df)}")
    print(f"eligible_rules={int(by_rule_df['eligible_min_300_races_v1'].sum())}")


if __name__ == "__main__":
    main()
