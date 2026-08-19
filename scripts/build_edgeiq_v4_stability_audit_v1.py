from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

import build_edgeiq_execution_v4_replay_sweep_v1 as v4_sweep


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RULES_PATH = DATA / "edgeiq_execution_v4_replay_sweep_v1.csv"

AUDIT_OUT = DATA / "edgeiq_v4_stability_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_v4_stability_audit_v1_summary.csv"
BY_YEAR_OUT = DATA / "edgeiq_v4_stability_audit_v1_by_year.csv"
BY_FIELD_SIZE_OUT = DATA / "edgeiq_v4_stability_audit_v1_by_field_size.csv"
BY_RANK_OUT = DATA / "edgeiq_v4_stability_audit_v1_by_rank.csv"
BY_TRUST_OUT = DATA / "edgeiq_v4_stability_audit_v1_by_trust.csv"

WINNING_RULE_ID = "SHARE_VERY_HIGH|DOM_ELITE|RANK_LE_1|EDGE_GE_0|TRUST_ELITE_STRONG_ONLY"
MIN_RACES = 300
YEAR_ORDER = ["2023", "2024", "2025", "2026"]
FIELD_SIZE_ORDER = ["LE_7", "8_10", "11_13", "14_PLUS"]
TRUST_ORDER = ["ELITE", "STRONG"]
RANK_ORDER = ["RANK_1", "RANK_2_PLUS"]


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


def build_rule_universe(rule_row: pd.Series) -> pd.DataFrame:
    base_df = v4_sweep.enrich_overlay_universe()

    score_share_min = clean_text(rule_row["score_share_min"]).upper()
    dominance_min = clean_text(rule_row["dominance_min"]).upper()
    rank_max = int(pd.to_numeric(rule_row["rank_max"], errors="coerce"))
    edge_min = float(pd.to_numeric(rule_row["edge_min"], errors="coerce"))
    trust_profile_filter = clean_text(rule_row["trust_profile_filter"]).upper()

    filtered = base_df[
        base_df["score_share_band_v1"].isin(v4_sweep.SCORE_SHARE_RULES[score_share_min])
        & base_df["dominance_band_v1"].isin(v4_sweep.DOMINANCE_RULES[dominance_min])
        & base_df["runner_rank"].le(rank_max)
        & base_df["edge_proxy_pct"].ge(edge_min)
        & base_df["trust_profile_v1"].isin(v4_sweep.TRUST_PROFILE_RULES[trust_profile_filter])
    ].copy()

    filtered["year"] = filtered["meeting_date"].astype(str).str[:4]
    filtered["field_size_bucket_v1"] = filtered["field_size_bucket"].fillna("").astype(str).map(clean_text).replace("", "UNKNOWN")
    filtered["trust_profile_v1"] = filtered["trust_profile_v1"].fillna("").astype(str).map(clean_text).replace("", "UNKNOWN")
    filtered["rank_group_v1"] = filtered["runner_rank"].map(lambda value: "RANK_1" if pd.notna(value) and int(value) == 1 else "RANK_2_PLUS")
    filtered["races_v1"] = 1

    keep_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "join_key_v1",
        "field_size",
        "field_size_bucket_v1",
        "year",
        "trust_profile_v1",
        "trust_band_v1",
        "gap_1_2_band",
        "gap_1_3_band",
        "dominance_certainty_band",
        "dominance_band_v1",
        "score_share_band_v1",
        "runner_rank",
        "rank_group_v1",
        "runner_score",
        "dominance_score_v1",
        "score_share_of_race",
        "edge_proxy_pct",
        "finish_position",
        "won",
        "placed",
    ]
    return filtered[keep_cols].copy()


def blank_row(label_col: str, label_value: str) -> dict[str, object]:
    return {
        label_col: label_value,
        "signals": 0,
        "races": 0,
        "wins": 0,
        "places": 0,
        "win_rate": math.nan,
        "place_rate": math.nan,
        "avg_finish": math.nan,
        "avg_rank": math.nan,
        "avg_score": math.nan,
        "avg_dominance_score": math.nan,
        "avg_score_share": math.nan,
        "sample_ge_300": False,
    }


def summarize_group(df: pd.DataFrame, group_col: str, ordered_labels: list[str] | None = None) -> pd.DataFrame:
    grouped = (
        df.groupby(group_col, dropna=False)
        .agg(
            signals=("horse", "size"),
            races=("join_key_v1", "nunique"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_finish=("finish_position", "mean"),
            avg_rank=("runner_rank", "mean"),
            avg_score=("runner_score", "mean"),
            avg_dominance_score=("dominance_score_v1", "mean"),
            avg_score_share=("score_share_of_race", "mean"),
        )
        .reset_index()
    )

    grouped[group_col] = grouped[group_col].fillna("UNKNOWN").astype(str).map(clean_text)
    grouped["win_rate"] = grouped.apply(lambda row: safe_div(row["wins"], row["signals"]), axis=1)
    grouped["place_rate"] = grouped.apply(lambda row: safe_div(row["places"], row["signals"]), axis=1)
    grouped["sample_ge_300"] = grouped["races"].ge(MIN_RACES)

    if ordered_labels is not None:
        present = set(grouped[group_col].tolist())
        missing_rows = [blank_row(group_col, label) for label in ordered_labels if label not in present]
        if missing_rows:
            grouped = pd.concat([grouped, pd.DataFrame(missing_rows)], ignore_index=True)
        grouped[group_col] = pd.Categorical(grouped[group_col], categories=ordered_labels, ordered=True)
        grouped = grouped.sort_values(group_col).reset_index(drop=True)

    return grouped.copy()


def eligible_extremes(df: pd.DataFrame, label_col: str) -> tuple[pd.Series | None, pd.Series | None]:
    eligible = df[df["races"].ge(MIN_RACES) & df["win_rate"].notna()].copy()
    if eligible.empty:
        return None, None
    best = eligible.sort_values(["win_rate", "races"], ascending=[False, False]).iloc[0]
    worst = eligible.sort_values(["win_rate", "races"], ascending=[True, False]).iloc[0]
    return best, worst


def build_stability_frame(by_year: pd.DataFrame, by_field: pd.DataFrame, by_trust: pd.DataFrame, by_rank: pd.DataFrame) -> pd.DataFrame:
    frames = [
        by_year.assign(subgroup_type="YEAR", subgroup_label=by_year["year"].astype(str)),
        by_field.assign(subgroup_type="FIELD_SIZE", subgroup_label=by_field["field_size_bucket_v1"].astype(str)),
        by_trust.assign(subgroup_type="TRUST_PROFILE", subgroup_label=by_trust["trust_profile_v1"].astype(str)),
        by_rank.assign(subgroup_type="RANK_GROUP", subgroup_label=by_rank["rank_group_v1"].astype(str)),
    ]
    stability = pd.concat(frames, ignore_index=True)
    stability = stability[stability["races"].ge(MIN_RACES) & stability["win_rate"].notna()].copy()
    return stability.reset_index(drop=True)


def stability_score_and_verdict(stability_df: pd.DataFrame) -> tuple[float, float, float, float, str]:
    if stability_df.empty:
        return math.nan, math.nan, math.nan, math.nan, "UNSTABLE"

    rates = stability_df["win_rate"].astype(float)
    lowest = float(rates.min())
    highest = float(rates.max())
    spread = highest - lowest
    mean_rate = float(rates.mean())
    cv = float(rates.std(ddof=0) / mean_rate) if mean_rate > 0 else math.nan

    spread_component = max(0.0, 1.0 - safe_div(spread, 0.15))
    cv_component = max(0.0, 1.0 - safe_div(cv, 0.30))
    stability_score = 100.0 * (0.6 * spread_component + 0.4 * cv_component)

    if stability_score >= 75.0 and spread <= 0.10 and cv <= 0.20:
        verdict = "ROBUST"
    elif stability_score >= 50.0 and spread <= 0.18 and cv <= 0.35:
        verdict = "MODERATELY_ROBUST"
    else:
        verdict = "UNSTABLE"

    return lowest, highest, spread, cv, verdict, stability_score


def build_summary(
    audit_df: pd.DataFrame,
    rule_row: pd.Series,
    by_year: pd.DataFrame,
    by_field: pd.DataFrame,
    by_trust: pd.DataFrame,
    by_rank: pd.DataFrame,
) -> pd.DataFrame:
    best_year, worst_year = eligible_extremes(by_year, "year")
    best_field, worst_field = eligible_extremes(by_field, "field_size_bucket_v1")
    stability_df = build_stability_frame(by_year, by_field, by_trust, by_rank)
    lowest, highest, spread, cv, verdict, stability_score = stability_score_and_verdict(stability_df)

    overall_win_rate = safe_div(audit_df["won"].sum(), len(audit_df))
    overall_place_rate = safe_div(audit_df["placed"].sum(), len(audit_df))

    if verdict == "ROBUST":
        main_answer = "REAL_EDGE"
    elif verdict == "MODERATELY_ROBUST":
        main_answer = "MOSTLY_REAL_EDGE"
    else:
        main_answer = "LUCKY_POCKET_RISK"

    summary_rows = [
        {"section": "OVERVIEW", "metric": "winning_rule_id", "value": clean_text(rule_row["rule_id"]), "notes": "Selected from V4 sweep results"},
        {"section": "OVERVIEW", "metric": "signals", "value": int(len(audit_df)), "notes": "Historical runner signals inside selected V4 rule"},
        {"section": "OVERVIEW", "metric": "races", "value": int(audit_df["join_key_v1"].nunique()), "notes": "Historical races represented"},
        {"section": "OVERVIEW", "metric": "wins", "value": int(audit_df["won"].sum()), "notes": "Historical wins inside rule"},
        {"section": "OVERVIEW", "metric": "places", "value": int(audit_df["placed"].sum()), "notes": "Historical places inside rule"},
        {"section": "OVERVIEW", "metric": "win_rate", "value": overall_win_rate, "notes": "Overall selected-rule win rate"},
        {"section": "OVERVIEW", "metric": "place_rate", "value": overall_place_rate, "notes": "Overall selected-rule place rate"},
        {"section": "QUESTION", "metric": "best_year", "value": best_year["year"] if best_year is not None else "NONE", "notes": f"win_rate={best_year['win_rate']:.4f} races={int(best_year['races'])}" if best_year is not None else "No eligible year"},
        {"section": "QUESTION", "metric": "worst_year", "value": worst_year["year"] if worst_year is not None else "NONE", "notes": f"win_rate={worst_year['win_rate']:.4f} races={int(worst_year['races'])}" if worst_year is not None else "No eligible year"},
        {"section": "QUESTION", "metric": "best_field_size", "value": str(best_field["field_size_bucket_v1"]) if best_field is not None else "NONE", "notes": f"win_rate={best_field['win_rate']:.4f} races={int(best_field['races'])}" if best_field is not None else "No eligible field-size bucket"},
        {"section": "QUESTION", "metric": "worst_field_size", "value": str(worst_field["field_size_bucket_v1"]) if worst_field is not None else "NONE", "notes": f"win_rate={worst_field['win_rate']:.4f} races={int(worst_field['races'])}" if worst_field is not None else "No eligible field-size bucket"},
        {"section": "STABILITY", "metric": "eligible_subgroups_ge_300", "value": int(len(stability_df)), "notes": "Across year, field size, trust profile, and rank group"},
        {"section": "STABILITY", "metric": "lowest_subgroup_win_rate", "value": lowest, "notes": "Minimum eligible subgroup win rate"},
        {"section": "STABILITY", "metric": "highest_subgroup_win_rate", "value": highest, "notes": "Maximum eligible subgroup win rate"},
        {"section": "STABILITY", "metric": "spread", "value": spread, "notes": "highest_subgroup_win_rate - lowest_subgroup_win_rate"},
        {"section": "STABILITY", "metric": "coefficient_of_variation", "value": cv, "notes": "Std/mean across eligible subgroup win rates"},
        {"section": "STABILITY", "metric": "stability_score_v1", "value": stability_score, "notes": "0-100 composite from spread and coefficient of variation"},
        {"section": "STABILITY", "metric": "final_verdict", "value": verdict, "notes": "ROBUST / MODERATELY_ROBUST / UNSTABLE"},
        {"section": "QUESTION", "metric": "did_v4_find_real_edge_or_lucky_pocket", "value": main_answer, "notes": "Interpretation from subgroup stability"},
    ]
    return pd.DataFrame(summary_rows)


def main() -> None:
    rule_row = pick_winning_rule()
    audit_df = build_rule_universe(rule_row)

    by_year = summarize_group(audit_df, "year", YEAR_ORDER)
    by_field = summarize_group(audit_df, "field_size_bucket_v1", FIELD_SIZE_ORDER)
    by_trust = summarize_group(audit_df, "trust_profile_v1", TRUST_ORDER)
    by_rank = summarize_group(audit_df, "rank_group_v1", RANK_ORDER)
    summary_df = build_summary(audit_df, rule_row, by_year, by_field, by_trust, by_rank)

    audit_df.to_csv(AUDIT_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    by_year.to_csv(BY_YEAR_OUT, index=False)
    by_field.to_csv(BY_FIELD_SIZE_OUT, index=False)
    by_rank.to_csv(BY_RANK_OUT, index=False)
    by_trust.to_csv(BY_TRUST_OUT, index=False)

    print(f"Wrote {AUDIT_OUT}")
    print(f"Wrote {SUMMARY_OUT}")
    print(f"Wrote {BY_YEAR_OUT}")
    print(f"Wrote {BY_FIELD_SIZE_OUT}")
    print(f"Wrote {BY_RANK_OUT}")
    print(f"Wrote {BY_TRUST_OUT}")


if __name__ == "__main__":
    main()
