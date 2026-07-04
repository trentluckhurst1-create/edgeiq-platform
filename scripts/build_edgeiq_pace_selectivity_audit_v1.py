from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_historical_pace_advantage_replay_v1.csv"
OUT_BY_BAND = DATA / "edgeiq_pace_selectivity_audit_v1_by_band.csv"
OUT_BY_ADJUSTMENT = DATA / "edgeiq_pace_selectivity_audit_v1_by_adjustment.csv"
OUT_SUMMARY = DATA / "edgeiq_pace_selectivity_audit_v1_summary.csv"

PACE_BAND_ORDER = ["VERY_FAST", "FAST", "NEUTRAL", "SLOW", "VERY_SLOW", "UNKNOWN"]
FOCUS_BANDS = ["VERY_FAST", "FAST", "VERY_SLOW", "SLOW", "NEUTRAL"]
FOCUS_ADJUSTMENTS = [8, 4, 0, -4, -8]
TACTICAL_STYLE_ORDER = ["LEADER", "ON_PACE", "MIDFIELD", "BACKMARKER", "UNKNOWN"]


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def round_or_zero(value: float, digits: int = 4) -> float:
    if pd.isna(value):
        return 0.0
    return round(float(value), digits)


def format_adjustment(value: int) -> str:
    return f"{value:+d}"


def load_input() -> pd.DataFrame:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT}")

    df = pd.read_csv(INPUT, low_memory=False)
    df["pace_pressure_band_v1"] = df["pace_pressure_band_v1"].fillna("UNKNOWN").astype(str).str.upper().str.strip()
    df["tactical_style_pre_race_v1"] = df["tactical_style_pre_race_v1"].fillna("UNKNOWN").astype(str).str.upper().str.strip()
    df["runner_rank"] = pd.to_numeric(df["runner_rank"], errors="coerce")
    df["runner_rank_pace_v1"] = pd.to_numeric(df["runner_rank_pace_v1"], errors="coerce")
    df["runner_rank_delta_v1"] = pd.to_numeric(df.get("runner_rank_delta_v1"), errors="coerce")
    df["pace_advantage_score_v1"] = pd.to_numeric(df["pace_advantage_score_v1"], errors="coerce").fillna(0).astype(int)
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0).astype(int)
    df["place"] = df["finish_position"].le(3).fillna(False).astype(int)

    missing_delta = df["runner_rank_delta_v1"].isna()
    if missing_delta.any():
        df.loc[missing_delta, "runner_rank_delta_v1"] = (
            df.loc[missing_delta, "runner_rank"] - df.loc[missing_delta, "runner_rank_pace_v1"]
        )

    df["rank_improved_flag"] = df["runner_rank_delta_v1"].gt(0).astype(int)
    df["rank_worsened_flag"] = df["runner_rank_delta_v1"].lt(0).astype(int)
    df["rank_unchanged_flag"] = df["runner_rank_delta_v1"].eq(0).astype(int)
    df["winner_rank_improved_flag"] = ((df["won"].eq(1)) & df["runner_rank_delta_v1"].gt(0)).astype(int)
    df["winner_rank_worsened_flag"] = ((df["won"].eq(1)) & df["runner_rank_delta_v1"].lt(0)).astype(int)
    df["winner_rank_unchanged_flag"] = ((df["won"].eq(1)) & df["runner_rank_delta_v1"].eq(0)).astype(int)
    return df


def build_group_table(df: pd.DataFrame, group_col: str, values: list[object] | None = None) -> pd.DataFrame:
    grouped = (
        df.groupby(group_col, dropna=False)
        .agg(
            runners=(group_col, "size"),
            wins=("won", "sum"),
            places=("place", "sum"),
            avg_finish=("finish_position", "mean"),
            rank_improved_count=("rank_improved_flag", "sum"),
            rank_worsened_count=("rank_worsened_flag", "sum"),
            rank_unchanged_count=("rank_unchanged_flag", "sum"),
            winner_rank_improved=("winner_rank_improved_flag", "sum"),
            winner_rank_worsened=("winner_rank_worsened_flag", "sum"),
            winner_rank_unchanged=("winner_rank_unchanged_flag", "sum"),
            avg_rank_delta_all=("runner_rank_delta_v1", "mean"),
        )
        .reset_index()
    )

    winner_rank_delta = (
        df[df["won"].eq(1)]
        .groupby(group_col, dropna=False)["runner_rank_delta_v1"]
        .mean()
        .reset_index(name="avg_rank_delta_winners")
    )
    grouped = grouped.merge(winner_rank_delta, on=group_col, how="left")

    if values is not None:
        scaffold = pd.DataFrame({group_col: values})
        grouped = scaffold.merge(grouped, on=group_col, how="left")

    numeric_cols = [
        "runners",
        "wins",
        "places",
        "rank_improved_count",
        "rank_worsened_count",
        "rank_unchanged_count",
        "winner_rank_improved",
        "winner_rank_worsened",
        "winner_rank_unchanged",
    ]
    for col in numeric_cols:
        grouped[col] = pd.to_numeric(grouped[col], errors="coerce").fillna(0).astype(int)

    grouped["win_rate"] = grouped.apply(lambda row: safe_rate(row["wins"], row["runners"]), axis=1)
    grouped["place_rate"] = grouped.apply(lambda row: safe_rate(row["places"], row["runners"]), axis=1)
    grouped["rank_improved_rate"] = grouped.apply(lambda row: safe_rate(row["rank_improved_count"], row["runners"]), axis=1)
    grouped["rank_worsened_rate"] = grouped.apply(lambda row: safe_rate(row["rank_worsened_count"], row["runners"]), axis=1)
    grouped["winner_rank_improved_rate"] = grouped.apply(lambda row: safe_rate(row["winner_rank_improved"], row["wins"]), axis=1)
    grouped["winner_rank_worsened_rate"] = grouped.apply(lambda row: safe_rate(row["winner_rank_worsened"], row["wins"]), axis=1)
    grouped["net_rank_improvement"] = grouped["rank_improved_count"] - grouped["rank_worsened_count"]
    grouped["net_winner_rank_improvement"] = grouped["winner_rank_improved"] - grouped["winner_rank_worsened"]

    for col in [
        "avg_finish",
        "avg_rank_delta_all",
        "avg_rank_delta_winners",
        "win_rate",
        "place_rate",
        "rank_improved_rate",
        "rank_worsened_rate",
        "winner_rank_improved_rate",
        "winner_rank_worsened_rate",
    ]:
        grouped[col] = pd.to_numeric(grouped[col], errors="coerce")

    grouped["avg_finish"] = grouped["avg_finish"].round(3)
    grouped["avg_rank_delta_all"] = grouped["avg_rank_delta_all"].round(3)
    grouped["avg_rank_delta_winners"] = grouped["avg_rank_delta_winners"].round(3)
    for col in [
        "win_rate",
        "place_rate",
        "rank_improved_rate",
        "rank_worsened_rate",
        "winner_rank_improved_rate",
        "winner_rank_worsened_rate",
    ]:
        grouped[col] = grouped[col].round(4)

    return grouped


def append_focus_summary(summary_rows: list[dict[str, object]], table: pd.DataFrame, key_col: str, prefix: str) -> None:
    for row in table.itertuples(index=False):
        group_key = getattr(row, key_col)
        summary_rows.extend([
            {"metric": f"{prefix}::{group_key}::runners", "value": int(row.runners)},
            {"metric": f"{prefix}::{group_key}::wins", "value": int(row.wins)},
            {"metric": f"{prefix}::{group_key}::win_rate", "value": round_or_zero(row.win_rate)},
            {"metric": f"{prefix}::{group_key}::winner_rank_improved", "value": int(row.winner_rank_improved)},
            {"metric": f"{prefix}::{group_key}::winner_rank_worsened", "value": int(row.winner_rank_worsened)},
            {"metric": f"{prefix}::{group_key}::winner_rank_improved_rate", "value": round_or_zero(row.winner_rank_improved_rate)},
            {"metric": f"{prefix}::{group_key}::avg_rank_delta_winners", "value": round_or_zero(row.avg_rank_delta_winners, 3)},
        ])


def best_row(table: pd.DataFrame, value_col: str) -> pd.Series | None:
    eligible = table[table["wins"].gt(0)].copy()
    if eligible.empty:
        return None
    return eligible.sort_values([value_col, "wins", "runners"], ascending=[False, False, False]).iloc[0]


def worst_row(table: pd.DataFrame, value_col: str) -> pd.Series | None:
    eligible = table[table["wins"].gt(0)].copy()
    if eligible.empty:
        return None
    return eligible.sort_values([value_col, "wins", "runners"], ascending=[True, False, False]).iloc[0]


def main() -> None:
    df = load_input()

    by_band = build_group_table(df, "pace_pressure_band_v1", PACE_BAND_ORDER)
    by_band.insert(0, "sort_order", by_band["pace_pressure_band_v1"].map({band: idx for idx, band in enumerate(PACE_BAND_ORDER, start=1)}).fillna(999).astype(int))
    by_band = by_band.rename(columns={"pace_pressure_band_v1": "pace_pressure_band"})
    by_band.to_csv(OUT_BY_BAND, index=False)

    observed_adjustments = sorted({int(value) for value in df["pace_advantage_score_v1"].dropna().astype(int).tolist()}, reverse=True)
    adjustment_values = []
    seen = set()
    for value in FOCUS_ADJUSTMENTS + observed_adjustments:
        if value not in seen:
            seen.add(value)
            adjustment_values.append(value)

    by_adjustment = build_group_table(df, "pace_advantage_score_v1", adjustment_values)
    by_adjustment.insert(0, "sort_order", range(1, len(by_adjustment) + 1))
    by_adjustment["pace_advantage_label"] = by_adjustment["pace_advantage_score_v1"].apply(format_adjustment)
    by_adjustment["focus_compare_flag"] = by_adjustment["pace_advantage_score_v1"].isin(FOCUS_ADJUSTMENTS)
    by_adjustment = by_adjustment.rename(columns={"pace_advantage_score_v1": "pace_advantage_score"})
    by_adjustment.to_csv(OUT_BY_ADJUSTMENT, index=False)

    by_style = build_group_table(df, "tactical_style_pre_race_v1", TACTICAL_STYLE_ORDER)

    focus_band_table = by_band[by_band["pace_pressure_band"].isin(FOCUS_BANDS)].copy()
    focus_adjustment_table = by_adjustment[by_adjustment["pace_advantage_score"].isin(FOCUS_ADJUSTMENTS)].copy()

    summary_rows: list[dict[str, object]] = [
        {"metric": "replay_rows", "value": int(len(df))},
        {"metric": "replay_races", "value": int(df["race_key"].nunique())},
        {"metric": "winner_rows", "value": int(df["won"].sum())},
        {"metric": "place_rows", "value": int(df["place"].sum())},
        {"metric": "overall_rank_improved_count", "value": int(df["rank_improved_flag"].sum())},
        {"metric": "overall_rank_worsened_count", "value": int(df["rank_worsened_flag"].sum())},
        {"metric": "overall_winner_rank_improved", "value": int(df["winner_rank_improved_flag"].sum())},
        {"metric": "overall_winner_rank_worsened", "value": int(df["winner_rank_worsened_flag"].sum())},
        {"metric": "overall_winner_rank_improved_rate", "value": round_or_zero(safe_rate(df["winner_rank_improved_flag"].sum(), df["won"].sum()))},
        {"metric": "overall_winner_rank_worsened_rate", "value": round_or_zero(safe_rate(df["winner_rank_worsened_flag"].sum(), df["won"].sum()))},
        {"metric": "observed_adjustment_values", "value": "|".join(format_adjustment(value) for value in observed_adjustments)},
        {"metric": "observed_adjustment_min", "value": int(min(observed_adjustments)) if observed_adjustments else 0},
        {"metric": "observed_adjustment_max", "value": int(max(observed_adjustments)) if observed_adjustments else 0},
    ]

    top_band = best_row(by_band, "winner_rank_improved_rate")
    low_band = worst_row(by_band, "winner_rank_improved_rate")
    top_adjustment = best_row(by_adjustment, "winner_rank_improved_rate")
    low_adjustment = worst_row(by_adjustment, "winner_rank_improved_rate")

    if top_band is not None:
        summary_rows.extend([
            {"metric": "best_band_by_winner_rank_improved_rate", "value": str(top_band["pace_pressure_band"])},
            {"metric": "best_band_winner_rank_improved_rate", "value": round_or_zero(top_band["winner_rank_improved_rate"])},
            {"metric": "best_band_net_winner_rank_improvement", "value": int(top_band["net_winner_rank_improvement"])},
        ])
    if low_band is not None:
        summary_rows.extend([
            {"metric": "worst_band_by_winner_rank_improved_rate", "value": str(low_band["pace_pressure_band"])},
            {"metric": "worst_band_winner_rank_improved_rate", "value": round_or_zero(low_band["winner_rank_improved_rate"])},
            {"metric": "worst_band_net_winner_rank_improvement", "value": int(low_band["net_winner_rank_improvement"])},
        ])
    if top_adjustment is not None:
        summary_rows.extend([
            {"metric": "best_adjustment_by_winner_rank_improved_rate", "value": format_adjustment(int(top_adjustment["pace_advantage_score"]))},
            {"metric": "best_adjustment_winner_rank_improved_rate", "value": round_or_zero(top_adjustment["winner_rank_improved_rate"])},
            {"metric": "best_adjustment_net_winner_rank_improvement", "value": int(top_adjustment["net_winner_rank_improvement"])},
        ])
    if low_adjustment is not None:
        summary_rows.extend([
            {"metric": "worst_adjustment_by_winner_rank_improved_rate", "value": format_adjustment(int(low_adjustment["pace_advantage_score"]))},
            {"metric": "worst_adjustment_winner_rank_improved_rate", "value": round_or_zero(low_adjustment["winner_rank_improved_rate"])},
            {"metric": "worst_adjustment_net_winner_rank_improvement", "value": int(low_adjustment["net_winner_rank_improvement"])},
        ])

    append_focus_summary(summary_rows, focus_band_table, "pace_pressure_band", "focus_band")
    append_focus_summary(summary_rows, focus_adjustment_table, "pace_advantage_score", "focus_adjustment")
    append_focus_summary(summary_rows, by_style, "tactical_style_pre_race_v1", "tactical_style")

    pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY, index=False)

    print("[EDGEIQ_PACE_SELECTIVITY_AUDIT_V1] COMPLETE")
    print(f"replay_rows={len(df)}")
    print(f"replay_races={df['race_key'].nunique()}")
    print(f"winner_rows={int(df['won'].sum())}")
    print(f"overall_winner_rank_improved={int(df['winner_rank_improved_flag'].sum())}")
    print(f"overall_winner_rank_worsened={int(df['winner_rank_worsened_flag'].sum())}")
    print(f"wrote_band={OUT_BY_BAND}")
    print(f"wrote_adjustment={OUT_BY_ADJUSTMENT}")
    print(f"wrote_summary={OUT_SUMMARY}")


if __name__ == "__main__":
    main()
