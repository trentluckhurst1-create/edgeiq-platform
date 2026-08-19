from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

import build_edgeiq_execution_v4_replay_sweep_v1 as v4_sweep


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
RULES_PATH = DATA / "edgeiq_execution_v4_replay_sweep_v1.csv"

AUDIT_OUT = DATA / "edgeiq_v4_rejected_winner_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_v4_rejected_winner_audit_v1_summary.csv"

WINNING_RULE_ID = "SHARE_VERY_HIGH|DOM_ELITE|RANK_LE_1|EDGE_GE_0|TRUST_ELITE_STRONG_ONLY"
FIELD_SIZE_ORDER = ["LE_7", "8_10", "11_13", "14_PLUS"]
TRUST_ORDER = ["ELITE", "STRONG", "STANDARD", "CHAOTIC"]
REASON_ORDER = [
    "CHAOTIC_TRUST",
    "STANDARD_TRUST",
    "NOT_RANK_1",
    "NOT_ELITE_DOMINANCE",
    "NOT_VERY_HIGH_SCORE_SHARE",
    "NO_POSITIVE_OVERLAY",
]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def pick_winning_rule() -> pd.Series:
    rules_df = pd.read_csv(RULES_PATH, low_memory=False)
    rules_df["rule_id"] = rules_df["rule_id"].fillna("").astype(str).map(clean_text)

    exact = rules_df[rules_df["rule_id"].eq(WINNING_RULE_ID)].copy()
    if not exact.empty:
        return exact.iloc[0]

    fallback = rules_df[
        rules_df["score_share_min"].fillna("").astype(str).eq("VERY_HIGH")
        & rules_df["dominance_min"].fillna("").astype(str).eq("ELITE")
        & pd.to_numeric(rules_df["rank_max"], errors="coerce").eq(1)
        & rules_df["trust_profile_filter"].fillna("").astype(str).eq("ELITE_STRONG_ONLY")
    ].copy()
    if fallback.empty:
        raise ValueError(f"Winning rule not found in {RULES_PATH}")

    fallback["edge_min_num_v1"] = pd.to_numeric(fallback["edge_min"], errors="coerce")
    fallback = fallback.sort_values(["win_rate", "edge_min_num_v1"], ascending=[False, True]).reset_index(drop=True)
    return fallback.iloc[0]


def score_share_band(value: object, q25: float, q50: float, q75: float) -> str:
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


def load_historical_replay() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
        "race_key",
    ]
    df = pd.read_csv(HIST_REPLAY_PATH, low_memory=False, usecols=usecols)

    for col in ["meeting_date", "track", "horse", "race_key"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)

    for col in ["race_no", "runner_score", "runner_rank", "finish_position", "won"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["placed"] = df["finish_position"].le(3).fillna(False).astype(int)
    df["join_key_v1"] = v4_sweep.build_join_key(df)
    df["runner_key_v1"] = v4_sweep.build_runner_key(df)
    df["runner_rank"] = df["runner_rank"].fillna(999).astype(int)
    df["won"] = df["won"].fillna(0).astype(int)
    return df.copy()


def load_historical_dominance_full() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "field_size_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "score_share_of_race",
    ]
    df = pd.read_csv(v4_sweep.HIST_DOMINANCE_PATH, low_memory=False, usecols=usecols)

    for col in ["meeting_date", "track", "horse", "dominance_band_v1"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)

    for col in ["race_no", "field_size_v1", "dominance_score_v1", "score_share_of_race"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["join_key_v1"] = v4_sweep.build_join_key(df)
    df["runner_key_v1"] = v4_sweep.build_runner_key(df)

    q25 = float(df["score_share_of_race"].quantile(0.25))
    q50 = float(df["score_share_of_race"].quantile(0.50))
    q75 = float(df["score_share_of_race"].quantile(0.75))
    df["score_share_band_v1_hist"] = df["score_share_of_race"].map(lambda value: score_share_band(value, q25, q50, q75))
    return df.copy()


def first_true_reason(row: pd.Series) -> str:
    for reason in REASON_ORDER:
        if bool(row.get(reason, False)):
            return reason
    return "NONE"


def build_enriched_universe(rule_row: pd.Series) -> pd.DataFrame:
    replay_df = load_historical_replay()
    dom_df = load_historical_dominance_full()
    trust_profiles = v4_sweep.reconstruct_historical_trust_profiles()
    positive_overlay_df = v4_sweep.load_positive_overlay_base()

    positive_overlay_lookup = positive_overlay_df[
        [
            "runner_key_v1",
            "edge_proxy_pct",
            "positive_overlay_flag",
            "score_share_band_v1",
        ]
    ].copy()
    positive_overlay_lookup = positive_overlay_lookup.rename(
        columns={
            "score_share_band_v1": "score_share_band_v1_overlay",
        }
    )

    full_df = replay_df.merge(
        dom_df[
            [
                "runner_key_v1",
                "field_size_v1",
                "dominance_score_v1",
                "dominance_band_v1",
                "score_share_of_race",
                "score_share_band_v1_hist",
            ]
        ],
        on="runner_key_v1",
        how="left",
    )
    full_df = full_df.merge(
        trust_profiles[
            [
                "join_key_v1",
                "field_size_bucket",
                "trust_band_v1",
                "gap_1_2_band",
                "gap_1_3_band",
                "dominance_certainty_band",
                "trust_profile_v1",
            ]
        ],
        on="join_key_v1",
        how="left",
    )
    full_df = full_df.merge(positive_overlay_lookup, on="runner_key_v1", how="left")

    full_df["field_size"] = full_df["field_size_v1"]
    full_df["field_size_bucket_v1"] = full_df["field_size_bucket"].fillna("").astype(str).map(clean_text)
    full_df["trust_profile_v1"] = full_df["trust_profile_v1"].fillna("").astype(str).map(clean_text).replace("", "UNKNOWN")
    full_df["trust_band_v1"] = full_df["trust_band_v1"].fillna("").astype(str).map(clean_text).replace("", "UNKNOWN")
    full_df["dominance_band_v1"] = full_df["dominance_band_v1"].fillna("").astype(str).map(clean_text).replace("", "UNKNOWN")
    full_df["dominance_certainty_band"] = full_df["dominance_certainty_band"].fillna("").astype(str).map(clean_text).replace("", "UNKNOWN")
    full_df["gap_1_2_band"] = full_df["gap_1_2_band"].fillna("").astype(str).map(clean_text).replace("", "UNKNOWN")
    full_df["gap_1_3_band"] = full_df["gap_1_3_band"].fillna("").astype(str).map(clean_text).replace("", "UNKNOWN")
    full_df["score_share_band_v1"] = (
        full_df["score_share_band_v1_overlay"].fillna("").astype(str).map(clean_text)
    )
    full_df["score_share_band_v1"] = full_df["score_share_band_v1"].where(
        full_df["score_share_band_v1"].ne(""),
        full_df["score_share_band_v1_hist"].fillna("").astype(str).map(clean_text),
    )
    full_df["score_share_band_v1"] = full_df["score_share_band_v1"].replace("", "UNKNOWN")

    full_df["edge_proxy_pct"] = pd.to_numeric(full_df["edge_proxy_pct"], errors="coerce")
    full_df["positive_overlay_flag"] = full_df["positive_overlay_flag"].fillna(False).astype(bool)
    full_df["field_size"] = pd.to_numeric(full_df["field_size"], errors="coerce")
    full_df["dominance_score_v1"] = pd.to_numeric(full_df["dominance_score_v1"], errors="coerce")
    full_df["score_share_of_race"] = pd.to_numeric(full_df["score_share_of_race"], errors="coerce")

    score_share_min = clean_text(rule_row["score_share_min"]).upper()
    dominance_min = clean_text(rule_row["dominance_min"]).upper()
    rank_max = int(pd.to_numeric(rule_row["rank_max"], errors="coerce"))
    edge_min = float(pd.to_numeric(rule_row["edge_min"], errors="coerce"))
    trust_profile_filter = clean_text(rule_row["trust_profile_filter"]).upper()

    full_df["accepted_signal_v4"] = (
        full_df["score_share_band_v1"].isin(v4_sweep.SCORE_SHARE_RULES[score_share_min])
        & full_df["dominance_band_v1"].isin(v4_sweep.DOMINANCE_RULES[dominance_min])
        & full_df["runner_rank"].le(rank_max)
        & full_df["edge_proxy_pct"].ge(edge_min).fillna(False)
        & full_df["trust_profile_v1"].isin(v4_sweep.TRUST_PROFILE_RULES[trust_profile_filter])
    )

    full_df["CHAOTIC_TRUST"] = full_df["trust_profile_v1"].eq("CHAOTIC")
    full_df["STANDARD_TRUST"] = full_df["trust_profile_v1"].eq("STANDARD")
    full_df["NOT_RANK_1"] = full_df["runner_rank"].ne(1)
    full_df["NOT_ELITE_DOMINANCE"] = full_df["dominance_band_v1"].ne("ELITE")
    full_df["NOT_VERY_HIGH_SCORE_SHARE"] = full_df["score_share_band_v1"].ne("VERY_HIGH")
    full_df["NO_POSITIVE_OVERLAY"] = ~full_df["positive_overlay_flag"]

    full_df["primary_rejection_reason_v1"] = full_df.apply(first_true_reason, axis=1)

    race_signal_lookup = (
        full_df.groupby("join_key_v1", dropna=False)["accepted_signal_v4"]
        .max()
        .rename("race_has_v4_signal_v1")
        .reset_index()
    )
    full_df = full_df.merge(race_signal_lookup, on="join_key_v1", how="left")
    full_df["race_has_v4_signal_v1"] = full_df["race_has_v4_signal_v1"].fillna(False).astype(bool)
    full_df["race_universe_v1"] = full_df["race_has_v4_signal_v1"].map({True: "ACCEPTED_BY_V4", False: "REJECTED_BY_V4"})

    keep_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "join_key_v1",
        "race_key",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
        "placed",
        "field_size",
        "field_size_bucket_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "dominance_certainty_band",
        "score_share_of_race",
        "score_share_band_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "gap_1_2_band",
        "gap_1_3_band",
        "edge_proxy_pct",
        "positive_overlay_flag",
        "accepted_signal_v4",
        "race_has_v4_signal_v1",
        "race_universe_v1",
        "CHAOTIC_TRUST",
        "STANDARD_TRUST",
        "NOT_RANK_1",
        "NOT_ELITE_DOMINANCE",
        "NOT_VERY_HIGH_SCORE_SHARE",
        "NO_POSITIVE_OVERLAY",
        "primary_rejection_reason_v1",
    ]
    return full_df[keep_cols].copy()


def winner_universe_table(winner_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total_winner_rows = len(winner_df)

    for universe_name in ["ACCEPTED_BY_V4", "REJECTED_BY_V4"]:
        subset = winner_df[winner_df["race_universe_v1"].eq(universe_name)].copy()
        rows.append(
            {
                "section": "WINNER_RETENTION",
                "universe": universe_name,
                "reason": "",
                "subgroup_type": "",
                "subgroup_value": "",
                "races": int(subset["join_key_v1"].nunique()),
                "winner_rows": int(len(subset)),
                "winner_retention_pct": safe_div(len(subset), total_winner_rows),
                "winner_top1_rate": float(subset["runner_rank"].eq(1).mean()) if not subset.empty else math.nan,
                "winner_top3_rate": float(subset["runner_rank"].le(3).mean()) if not subset.empty else math.nan,
                "winner_top5_rate": float(subset["runner_rank"].le(5).mean()) if not subset.empty else math.nan,
                "avg_winner_rank": float(subset["runner_rank"].mean()) if not subset.empty else math.nan,
                "avg_dominance_score": float(subset["dominance_score_v1"].mean()) if not subset.empty else math.nan,
                "avg_score_share": float(subset["score_share_of_race"].mean()) if not subset.empty else math.nan,
                "avg_field_size": float(subset["field_size"].mean()) if not subset.empty else math.nan,
                "direct_winner_signal_pct": float(subset["accepted_signal_v4"].mean()) if not subset.empty else math.nan,
                "count": math.nan,
                "pct": math.nan,
                "notes": "",
            }
        )
    return pd.DataFrame(rows)


def reason_table(df: pd.DataFrame, section_name: str) -> pd.DataFrame:
    total_rows = len(df)
    rows = []
    for reason in REASON_ORDER:
        count = int(df[reason].sum())
        rows.append(
            {
                "section": section_name,
                "universe": "",
                "reason": reason,
                "subgroup_type": "",
                "subgroup_value": "",
                "races": math.nan,
                "winner_rows": math.nan,
                "winner_retention_pct": math.nan,
                "winner_top1_rate": math.nan,
                "winner_top3_rate": math.nan,
                "winner_top5_rate": math.nan,
                "avg_winner_rank": math.nan,
                "avg_dominance_score": math.nan,
                "avg_score_share": math.nan,
                "avg_field_size": math.nan,
                "direct_winner_signal_pct": math.nan,
                "count": count,
                "pct": safe_div(count, total_rows),
                "notes": f"population_rows={total_rows}",
            }
        )
    return pd.DataFrame(rows)


def rejected_subgroup_table(rejected_winners: pd.DataFrame) -> pd.DataFrame:
    subgroup_frames = []
    for subgroup_type, col_name in [
        ("PRIMARY_REASON", "primary_rejection_reason_v1"),
        ("TRUST_PROFILE", "trust_profile_v1"),
        ("FIELD_SIZE_BUCKET", "field_size_bucket_v1"),
    ]:
        grouped = (
            rejected_winners.groupby(col_name, dropna=False)
            .agg(
                races=("join_key_v1", "nunique"),
                winner_rows=("horse", "size"),
                winner_top1_rate=("runner_rank", lambda s: float(pd.Series(s).eq(1).mean())),
                winner_top3_rate=("runner_rank", lambda s: float(pd.Series(s).le(3).mean())),
                winner_top5_rate=("runner_rank", lambda s: float(pd.Series(s).le(5).mean())),
                avg_winner_rank=("runner_rank", "mean"),
                avg_dominance_score=("dominance_score_v1", "mean"),
                avg_score_share=("score_share_of_race", "mean"),
                avg_field_size=("field_size", "mean"),
            )
            .reset_index()
        )
        grouped["section"] = "REJECTED_SUBGROUPS"
        grouped["universe"] = ""
        grouped["reason"] = ""
        grouped["subgroup_type"] = subgroup_type
        grouped["subgroup_value"] = grouped[col_name].fillna("UNKNOWN").astype(str).map(clean_text)
        grouped["winner_retention_pct"] = math.nan
        grouped["direct_winner_signal_pct"] = math.nan
        grouped["count"] = math.nan
        grouped["pct"] = math.nan
        grouped["notes"] = ""
        subgroup_frames.append(
            grouped[
                [
                    "section",
                    "universe",
                    "reason",
                    "subgroup_type",
                    "subgroup_value",
                    "races",
                    "winner_rows",
                    "winner_retention_pct",
                    "winner_top1_rate",
                    "winner_top3_rate",
                    "winner_top5_rate",
                    "avg_winner_rank",
                    "avg_dominance_score",
                    "avg_score_share",
                    "avg_field_size",
                    "direct_winner_signal_pct",
                    "count",
                    "pct",
                    "notes",
                ]
            ]
        )

    return pd.concat(subgroup_frames, ignore_index=True)


def best_and_worst_rejected_subgroups(subgroup_df: pd.DataFrame) -> tuple[pd.Series | None, pd.Series | None]:
    eligible = subgroup_df[subgroup_df["races"].ge(300)].copy()
    if eligible.empty:
        return None, None

    best = eligible.sort_values(["winner_top1_rate", "avg_winner_rank", "races"], ascending=[False, True, False]).iloc[0]
    worst = eligible.sort_values(["winner_top1_rate", "avg_winner_rank", "races"], ascending=[True, False, False]).iloc[0]
    return best, worst


def build_summary(
    universe_df: pd.DataFrame,
    winner_table: pd.DataFrame,
    winner_reason_df: pd.DataFrame,
    losing_reason_df: pd.DataFrame,
    subgroup_df: pd.DataFrame,
) -> pd.DataFrame:
    winner_df = universe_df[universe_df["won"].eq(1)].copy()
    accepted_row = winner_table[winner_table["universe"].eq("ACCEPTED_BY_V4")].iloc[0]
    rejected_row = winner_table[winner_table["universe"].eq("REJECTED_BY_V4")].iloc[0]

    best_rejected, worst_rejected = best_and_worst_rejected_subgroups(subgroup_df)

    max_winner_reason = winner_reason_df.sort_values(["count", "reason"], ascending=[False, True]).iloc[0]
    max_loser_reason = losing_reason_df.sort_values(["count", "reason"], ascending=[False, True]).iloc[0]

    overall_top1 = float(winner_df["runner_rank"].eq(1).mean()) if not winner_df.empty else math.nan
    accepted_top1 = float(accepted_row["winner_top1_rate"])
    rejected_top1 = float(rejected_row["winner_top1_rate"])
    accepted_top5 = float(accepted_row["winner_top5_rate"])
    rejected_top5 = float(rejected_row["winner_top5_rate"])
    accepted_retention = float(accepted_row["winner_retention_pct"])

    rejected_materially_weaker = (
        accepted_top1 - rejected_top1 >= 0.07
        and accepted_top5 - rejected_top5 >= 0.05
        and float(accepted_row["avg_dominance_score"]) - float(rejected_row["avg_dominance_score"]) >= 4.0
        and float(accepted_row["avg_score_share"]) - float(rejected_row["avg_score_share"]) >= 0.02
        and float(rejected_row["avg_winner_rank"]) - float(accepted_row["avg_winner_rank"]) >= 0.5
    )

    if rejected_materially_weaker and 0.35 <= accepted_retention <= 0.65 and accepted_top1 - rejected_top1 >= 0.07:
        verdict = "WELL_CALIBRATED"
    elif accepted_retention < 0.35:
        verdict = "OVER_FILTERING"
    elif accepted_retention > 0.70 or accepted_top1 - rejected_top1 < 0.04:
        verdict = "UNDER_FILTERING"
    elif rejected_materially_weaker:
        verdict = "WELL_CALIBRATED"
    else:
        verdict = "OVER_FILTERING"

    accepted_signal_winner_pct = float(winner_df["accepted_signal_v4"].mean()) if not winner_df.empty else math.nan

    summary_rows = [
        {
            "section": "SUMMARY",
            "universe": "",
            "reason": "",
            "subgroup_type": "",
            "subgroup_value": "",
            "races": int(universe_df["join_key_v1"].nunique()),
            "winner_rows": int(len(winner_df)),
            "winner_retention_pct": math.nan,
            "winner_top1_rate": overall_top1,
            "winner_top3_rate": float(winner_df["runner_rank"].le(3).mean()) if not winner_df.empty else math.nan,
            "winner_top5_rate": float(winner_df["runner_rank"].le(5).mean()) if not winner_df.empty else math.nan,
            "avg_winner_rank": float(winner_df["runner_rank"].mean()) if not winner_df.empty else math.nan,
            "avg_dominance_score": math.nan,
            "avg_score_share": math.nan,
            "avg_field_size": math.nan,
            "direct_winner_signal_pct": accepted_signal_winner_pct,
            "count": math.nan,
            "pct": math.nan,
            "notes": "Overall historical winner baseline",
        },
        {
            "section": "ANSWERS",
            "universe": "",
            "reason": "",
            "subgroup_type": "",
            "subgroup_value": "WINNERS_RETAINED_BY_ACCEPTED_RACE_UNIVERSE",
            "races": math.nan,
            "winner_rows": math.nan,
            "winner_retention_pct": accepted_retention,
            "winner_top1_rate": math.nan,
            "winner_top3_rate": math.nan,
            "winner_top5_rate": math.nan,
            "avg_winner_rank": math.nan,
            "avg_dominance_score": math.nan,
            "avg_score_share": math.nan,
            "avg_field_size": math.nan,
            "direct_winner_signal_pct": math.nan,
            "count": math.nan,
            "pct": math.nan,
            "notes": "Percentage of winner rows in races where V4 produced at least one signal",
        },
        {
            "section": "ANSWERS",
            "universe": "",
            "reason": "",
            "subgroup_type": "",
            "subgroup_value": "WINNERS_REJECTED_BY_RACE_UNIVERSE",
            "races": math.nan,
            "winner_rows": math.nan,
            "winner_retention_pct": float(rejected_row["winner_retention_pct"]),
            "winner_top1_rate": math.nan,
            "winner_top3_rate": math.nan,
            "winner_top5_rate": math.nan,
            "avg_winner_rank": math.nan,
            "avg_dominance_score": math.nan,
            "avg_score_share": math.nan,
            "avg_field_size": math.nan,
            "direct_winner_signal_pct": math.nan,
            "count": math.nan,
            "pct": math.nan,
            "notes": "Percentage of winner rows in races where V4 produced no signals",
        },
        {
            "section": "ANSWERS",
            "universe": "",
            "reason": "",
            "subgroup_type": "",
            "subgroup_value": "WINNERS_DIRECTLY_PASSING_V4_RULE",
            "races": math.nan,
            "winner_rows": math.nan,
            "winner_retention_pct": accepted_signal_winner_pct,
            "winner_top1_rate": math.nan,
            "winner_top3_rate": math.nan,
            "winner_top5_rate": math.nan,
            "avg_winner_rank": math.nan,
            "avg_dominance_score": math.nan,
            "avg_score_share": math.nan,
            "avg_field_size": math.nan,
            "direct_winner_signal_pct": math.nan,
            "count": math.nan,
            "pct": math.nan,
            "notes": "Percentage of winner rows that themselves satisfied the exact V4 signal rule",
        },
        {
            "section": "ANSWERS",
            "universe": "",
            "reason": max_winner_reason["reason"],
            "subgroup_type": "",
            "subgroup_value": "TOP_REJECTION_REASON_FOR_WINNERS",
            "races": math.nan,
            "winner_rows": math.nan,
            "winner_retention_pct": math.nan,
            "winner_top1_rate": math.nan,
            "winner_top3_rate": math.nan,
            "winner_top5_rate": math.nan,
            "avg_winner_rank": math.nan,
            "avg_dominance_score": math.nan,
            "avg_score_share": math.nan,
            "avg_field_size": math.nan,
            "direct_winner_signal_pct": math.nan,
            "count": int(max_winner_reason["count"]),
            "pct": float(max_winner_reason["pct"]),
            "notes": "Rejected winner rows; multiple reasons allowed",
        },
        {
            "section": "ANSWERS",
            "universe": "",
            "reason": max_loser_reason["reason"],
            "subgroup_type": "",
            "subgroup_value": "TOP_REJECTION_REASON_FOR_LOSING_RUNNERS",
            "races": math.nan,
            "winner_rows": math.nan,
            "winner_retention_pct": math.nan,
            "winner_top1_rate": math.nan,
            "winner_top3_rate": math.nan,
            "winner_top5_rate": math.nan,
            "avg_winner_rank": math.nan,
            "avg_dominance_score": math.nan,
            "avg_score_share": math.nan,
            "avg_field_size": math.nan,
            "direct_winner_signal_pct": math.nan,
            "count": int(max_loser_reason["count"]),
            "pct": float(max_loser_reason["pct"]),
            "notes": "Rejected losing runners; multiple reasons allowed",
        },
        {
            "section": "ANSWERS",
            "universe": "",
            "reason": "",
            "subgroup_type": "",
            "subgroup_value": "REJECTED_WINNERS_MATERIALLY_WEAKER",
            "races": math.nan,
            "winner_rows": math.nan,
            "winner_retention_pct": math.nan,
            "winner_top1_rate": math.nan,
            "winner_top3_rate": math.nan,
            "winner_top5_rate": math.nan,
            "avg_winner_rank": math.nan,
            "avg_dominance_score": math.nan,
            "avg_score_share": math.nan,
            "avg_field_size": math.nan,
            "direct_winner_signal_pct": math.nan,
            "count": math.nan,
            "pct": math.nan,
            "notes": "YES" if rejected_materially_weaker else "NO",
        },
        {
            "section": "ANSWERS",
            "universe": "",
            "reason": "",
            "subgroup_type": best_rejected["subgroup_type"] if best_rejected is not None else "",
            "subgroup_value": best_rejected["subgroup_value"] if best_rejected is not None else "NONE",
            "races": int(best_rejected["races"]) if best_rejected is not None else math.nan,
            "winner_rows": int(best_rejected["winner_rows"]) if best_rejected is not None else math.nan,
            "winner_retention_pct": math.nan,
            "winner_top1_rate": float(best_rejected["winner_top1_rate"]) if best_rejected is not None else math.nan,
            "winner_top3_rate": float(best_rejected["winner_top3_rate"]) if best_rejected is not None else math.nan,
            "winner_top5_rate": float(best_rejected["winner_top5_rate"]) if best_rejected is not None else math.nan,
            "avg_winner_rank": float(best_rejected["avg_winner_rank"]) if best_rejected is not None else math.nan,
            "avg_dominance_score": float(best_rejected["avg_dominance_score"]) if best_rejected is not None else math.nan,
            "avg_score_share": float(best_rejected["avg_score_share"]) if best_rejected is not None else math.nan,
            "avg_field_size": float(best_rejected["avg_field_size"]) if best_rejected is not None else math.nan,
            "direct_winner_signal_pct": math.nan,
            "count": math.nan,
            "pct": math.nan,
            "notes": "Best rejected subgroup with >=300 races by winner_top1_rate",
        },
        {
            "section": "ANSWERS",
            "universe": "",
            "reason": "",
            "subgroup_type": worst_rejected["subgroup_type"] if worst_rejected is not None else "",
            "subgroup_value": worst_rejected["subgroup_value"] if worst_rejected is not None else "NONE",
            "races": int(worst_rejected["races"]) if worst_rejected is not None else math.nan,
            "winner_rows": int(worst_rejected["winner_rows"]) if worst_rejected is not None else math.nan,
            "winner_retention_pct": math.nan,
            "winner_top1_rate": float(worst_rejected["winner_top1_rate"]) if worst_rejected is not None else math.nan,
            "winner_top3_rate": float(worst_rejected["winner_top3_rate"]) if worst_rejected is not None else math.nan,
            "winner_top5_rate": float(worst_rejected["winner_top5_rate"]) if worst_rejected is not None else math.nan,
            "avg_winner_rank": float(worst_rejected["avg_winner_rank"]) if worst_rejected is not None else math.nan,
            "avg_dominance_score": float(worst_rejected["avg_dominance_score"]) if worst_rejected is not None else math.nan,
            "avg_score_share": float(worst_rejected["avg_score_share"]) if worst_rejected is not None else math.nan,
            "avg_field_size": float(worst_rejected["avg_field_size"]) if worst_rejected is not None else math.nan,
            "direct_winner_signal_pct": math.nan,
            "count": math.nan,
            "pct": math.nan,
            "notes": "Worst rejected subgroup with >=300 races by winner_top1_rate",
        },
        {
            "section": "FINAL_VERDICT",
            "universe": "",
            "reason": "",
            "subgroup_type": "",
            "subgroup_value": verdict,
            "races": math.nan,
            "winner_rows": math.nan,
            "winner_retention_pct": accepted_retention,
            "winner_top1_rate": accepted_top1,
            "winner_top3_rate": rejected_top1,
            "winner_top5_rate": math.nan,
            "avg_winner_rank": math.nan,
            "avg_dominance_score": math.nan,
            "avg_score_share": math.nan,
            "avg_field_size": math.nan,
            "direct_winner_signal_pct": accepted_signal_winner_pct,
            "count": math.nan,
            "pct": math.nan,
            "notes": f"accepted_top1={accepted_top1:.4f} rejected_top1={rejected_top1:.4f} accepted_retention={accepted_retention:.4f}",
        },
    ]
    return pd.DataFrame(summary_rows)


def main() -> None:
    rule_row = pick_winning_rule()
    universe_df = build_enriched_universe(rule_row)
    winner_df = universe_df[universe_df["won"].eq(1)].copy()

    winner_table = winner_universe_table(winner_df)
    rejected_winners = winner_df[winner_df["race_universe_v1"].eq("REJECTED_BY_V4")].copy()
    rejected_losing_runners = universe_df[
        universe_df["race_universe_v1"].eq("REJECTED_BY_V4") & universe_df["won"].eq(0)
    ].copy()

    winner_reason_df = reason_table(rejected_winners, "REJECTION_REASON_WINNERS")
    losing_reason_df = reason_table(rejected_losing_runners, "REJECTION_REASON_LOSERS")
    subgroup_df = rejected_subgroup_table(rejected_winners)
    summary_df = pd.concat(
        [
            winner_table,
            winner_reason_df,
            losing_reason_df,
            subgroup_df,
            build_summary(universe_df, winner_table, winner_reason_df, losing_reason_df, subgroup_df),
        ],
        ignore_index=True,
    )

    universe_df.to_csv(AUDIT_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)

    print(f"Wrote {AUDIT_OUT}")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
