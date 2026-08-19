from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math

import pandas as pd

from audit_edgeiq_v6_1_overconfidence_archetypes_v1 import build_clean_detail, round_num, safe_pct


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT_REPLAY = DATA / "edgeiq_v6_1_segment_guardrail_replay_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_v6_1_segment_guardrail_replay_v1_summary.csv"


TARGET_SEGMENTS = [
    {
        "segment_id_v1": "SEG_DIST2000_GOOD_PROB1015",
        "segment_label_v1": "DIST_2000_PLUS + GOOD + PROB_10_15",
        "match": {
            "distance_bucket_v1": "DIST_2000_PLUS",
            "condition_group_v1": "GOOD",
            "probability_bucket_v1": "10_15",
        },
    },
    {
        "segment_id_v1": "SEG_ELITE_1600_1999_GOOD",
        "segment_label_v1": "ELITE + DIST_1600_1999 + GOOD",
        "match": {
            "projection_band_V6_1_RESEARCH": "ELITE",
            "distance_bucket_v1": "DIST_1600_1999",
            "condition_group_v1": "GOOD",
        },
    },
    {
        "segment_id_v1": "SEG_BM_GOOD_RANK3",
        "segment_label_v1": "BM + GOOD + PRICE_RANK_3",
        "match": {
            "class_bucket_v1": "BM",
            "condition_group_v1": "GOOD",
            "price_rank_bucket_v1": "RANK_3",
        },
    },
    {
        "segment_id_v1": "SEG_GOOD_PROB1520",
        "segment_label_v1": "GOOD + PROBABILITY_15_20",
        "match": {
            "condition_group_v1": "GOOD",
            "probability_bucket_v1": "15_20",
        },
    },
]

REDUCTION_SCENARIOS = [
    {"guardrail_name_v1": "NO_CHANGE", "reduction_pct_v1": 0.00},
    {"guardrail_name_v1": "REDUCE_10", "reduction_pct_v1": 0.10},
    {"guardrail_name_v1": "REDUCE_15", "reduction_pct_v1": 0.15},
    {"guardrail_name_v1": "REDUCE_20", "reduction_pct_v1": 0.20},
]


def fair_from_probability(probability: float | None) -> float | None:
    if probability is None or not math.isfinite(probability) or probability <= 0:
        return None
    return 1.0 / probability


def build_segment_flag(detail: pd.DataFrame, segment_def: dict[str, object]) -> pd.Series:
    mask = pd.Series(True, index=detail.index)
    for column, expected_value in segment_def["match"].items():
        mask = mask & detail[column].astype(str).eq(str(expected_value))
    return mask


def prepare_base_detail() -> pd.DataFrame:
    detail, metrics = build_clean_detail()
    detail = detail.copy()
    detail["base_probability_v1"] = pd.to_numeric(detail["V6_1_RESEARCH_probability"], errors="coerce")
    detail["base_probability_sum_race_v1"] = detail.groupby("backtest_race_key", dropna=False)["base_probability_v1"].transform("sum")
    detail["base_probability_norm_v1"] = detail["base_probability_v1"] / detail["base_probability_sum_race_v1"]
    detail["base_probability_norm_v1"] = detail["base_probability_norm_v1"].fillna(0.0)
    detail["base_fair_price_norm_v1"] = detail["base_probability_norm_v1"].map(fair_from_probability)
    detail["base_rank_v1"] = (
        detail.sort_values(["backtest_race_key", "base_probability_norm_v1", "horse_key"], ascending=[True, False, True])
        .groupby("backtest_race_key", dropna=False)
        .cumcount()
        + 1
    )
    detail["source_metrics_clean_rows_v1"] = metrics["clean_rows_v1"]
    detail["source_metrics_clean_races_v1"] = metrics["clean_races_v1"]
    detail["source_metrics_duplicate_backtest_rows_excluded_v1"] = metrics["duplicate_backtest_rows_excluded_v1"]
    detail["source_metrics_duplicate_backtest_races_excluded_v1"] = metrics["duplicate_backtest_races_excluded_v1"]
    return detail


def summarize_scenario(
    scenario_df: pd.DataFrame,
    segment_id: str,
    segment_label: str,
    reduction_name: str,
    reduction_pct: float,
    target_mask: pd.Series,
    baseline_lookup: dict[tuple[str, str], dict[str, object]],
) -> dict[str, object]:
    rows = int(len(scenario_df))
    races = int(scenario_df["backtest_race_key"].nunique())
    targeted_rows = int(target_mask.sum())
    targeted_races = int(scenario_df.loc[target_mask, "backtest_race_key"].nunique()) if targeted_rows > 0 else 0

    expected_total_wins = float(pd.to_numeric(scenario_df["adjusted_probability_v1"], errors="coerce").fillna(0.0).sum())
    actual_total_wins = float(pd.to_numeric(scenario_df["won"], errors="coerce").fillna(0.0).sum())
    overall_expected_vs_actual_delta = expected_total_wins - actual_total_wins

    brier_series = (scenario_df["adjusted_probability_v1"] - scenario_df["won"].astype(float)) ** 2
    brier_score = float(brier_series.mean()) if len(brier_series) else None

    rank1 = scenario_df[scenario_df["adjusted_rank_v1"].eq(1)].copy()
    rank1_rows = int(len(rank1))
    rank1_wins = int(rank1["won"].sum()) if rank1_rows else 0
    rank1_places = int(rank1["placed"].sum()) if rank1_rows else 0
    rank1_expected_win_pct = safe_pct(float(rank1["adjusted_probability_v1"].sum()), rank1_rows)
    rank1_actual_win_pct = safe_pct(rank1_wins, rank1_rows)
    rank1_actual_place_pct = safe_pct(rank1_places, rank1_rows)
    rank1_calibration_delta_pct = None
    if rank1_expected_win_pct is not None and rank1_actual_win_pct is not None:
        rank1_calibration_delta_pct = rank1_expected_win_pct - rank1_actual_win_pct

    rank1_sp_valid = rank1["sp_valid_v1"].eq("YES")
    rank1_sp_count = int(rank1_sp_valid.sum())
    rank1_roi_pct = None
    rank1_net_units = None
    if rank1_sp_count > 0:
        rank1_profits = rank1.loc[rank1_sp_valid].apply(
            lambda row: (float(row["sp"]) - 1.0) if int(row["won"]) == 1 else -1.0,
            axis=1,
        )
        rank1_net_units = float(rank1_profits.sum())
        rank1_roi_pct = safe_pct(rank1_net_units, rank1_sp_count)

    targeted = scenario_df.loc[target_mask].copy()
    target_expected_before = float(pd.to_numeric(targeted["base_probability_norm_v1"], errors="coerce").fillna(0.0).sum())
    target_expected_after = float(pd.to_numeric(targeted["adjusted_probability_v1"], errors="coerce").fillna(0.0).sum())
    target_actual_wins = float(pd.to_numeric(targeted["won"], errors="coerce").fillna(0.0).sum())
    target_expected_win_pct_before = safe_pct(target_expected_before, targeted_rows)
    target_expected_win_pct_after = safe_pct(target_expected_after, targeted_rows)
    target_actual_win_pct = safe_pct(target_actual_wins, targeted_rows)
    target_calibration_delta_before = None
    target_calibration_delta_after = None
    if target_expected_win_pct_before is not None and target_actual_win_pct is not None:
        target_calibration_delta_before = target_expected_win_pct_before - target_actual_win_pct
    if target_expected_win_pct_after is not None and target_actual_win_pct is not None:
        target_calibration_delta_after = target_expected_win_pct_after - target_actual_win_pct

    top_pick_changes = int((scenario_df["base_rank_v1"].eq(1) & scenario_df["adjusted_rank_v1"].ne(1)).sum())
    top_pick_changes_to_winner = int(
        (
            scenario_df["adjusted_rank_v1"].eq(1)
            & scenario_df["base_rank_v1"].ne(1)
            & scenario_df["won"].eq(1)
        ).sum()
    )
    top_pick_changes_from_winner = int(
        (
            scenario_df["base_rank_v1"].eq(1)
            & scenario_df["adjusted_rank_v1"].ne(1)
            & scenario_df["won"].eq(1)
        ).sum()
    )

    result = {
        "row_type_v1": "SCENARIO",
        "segment_id_v1": segment_id,
        "segment_label_v1": segment_label,
        "guardrail_name_v1": reduction_name,
        "reduction_pct_v1": round_num(reduction_pct * 100.0, 3),
        "scenario_id_v1": f"{segment_id}|{reduction_name}",
        "rows_v1": rows,
        "races_v1": races,
        "targeted_rows_v1": targeted_rows,
        "targeted_races_v1": targeted_races,
        "expected_total_wins_v1": round_num(expected_total_wins, 3),
        "actual_total_wins_v1": round_num(actual_total_wins, 3),
        "overall_expected_vs_actual_delta_v1": round_num(overall_expected_vs_actual_delta, 3),
        "brier_score_v1": round_num(brier_score, 6),
        "rank1_rows_v1": rank1_rows,
        "rank1_expected_win_pct_v1": round_num(rank1_expected_win_pct, 3),
        "rank1_actual_win_pct_v1": round_num(rank1_actual_win_pct, 3),
        "rank1_place_pct_v1": round_num(rank1_actual_place_pct, 3),
        "rank1_calibration_delta_pct_v1": round_num(rank1_calibration_delta_pct, 3),
        "rank1_roi_pct_v1": round_num(rank1_roi_pct, 3),
        "rank1_net_units_v1": round_num(rank1_net_units, 3),
        "top_pick_changes_v1": top_pick_changes,
        "top_pick_changes_to_winner_v1": top_pick_changes_to_winner,
        "top_pick_changes_from_winner_v1": top_pick_changes_from_winner,
        "target_expected_wins_before_v1": round_num(target_expected_before, 3),
        "target_expected_wins_after_v1": round_num(target_expected_after, 3),
        "target_actual_wins_v1": round_num(target_actual_wins, 3),
        "target_expected_win_pct_before_v1": round_num(target_expected_win_pct_before, 3),
        "target_expected_win_pct_after_v1": round_num(target_expected_win_pct_after, 3),
        "target_actual_win_pct_v1": round_num(target_actual_win_pct, 3),
        "target_calibration_delta_before_v1": round_num(target_calibration_delta_before, 3),
        "target_calibration_delta_after_v1": round_num(target_calibration_delta_after, 3),
        "target_abs_calibration_improvement_v1": round_num(
            (abs(target_calibration_delta_before) - abs(target_calibration_delta_after))
            if target_calibration_delta_before is not None and target_calibration_delta_after is not None
            else None,
            3,
        ),
        "source_metrics_clean_rows_v1": int(scenario_df["source_metrics_clean_rows_v1"].iloc[0]),
        "source_metrics_clean_races_v1": int(scenario_df["source_metrics_clean_races_v1"].iloc[0]),
        "source_metrics_duplicate_backtest_rows_excluded_v1": int(scenario_df["source_metrics_duplicate_backtest_rows_excluded_v1"].iloc[0]),
        "source_metrics_duplicate_backtest_races_excluded_v1": int(scenario_df["source_metrics_duplicate_backtest_races_excluded_v1"].iloc[0]),
        "built_at_v1": datetime.now(timezone.utc).isoformat(),
    }

    baseline = baseline_lookup.get((segment_id, "NO_CHANGE"))
    if baseline is None:
        result["brier_delta_vs_baseline_v1"] = None
        result["rank1_win_delta_vs_baseline_v1"] = None
        result["rank1_place_delta_vs_baseline_v1"] = None
        result["rank1_roi_delta_vs_baseline_v1"] = None
        result["recommendation_v1"] = "NO_CHANGE"
    else:
        result["brier_delta_vs_baseline_v1"] = round_num(
            (baseline["brier_score_v1"] - result["brier_score_v1"])
            if baseline["brier_score_v1"] is not None and result["brier_score_v1"] is not None
            else None,
            6,
        )
        result["rank1_win_delta_vs_baseline_v1"] = round_num(
            (result["rank1_actual_win_pct_v1"] - baseline["rank1_actual_win_pct_v1"])
            if baseline["rank1_actual_win_pct_v1"] is not None and result["rank1_actual_win_pct_v1"] is not None
            else None,
            3,
        )
        result["rank1_place_delta_vs_baseline_v1"] = round_num(
            (result["rank1_place_pct_v1"] - baseline["rank1_place_pct_v1"])
            if baseline["rank1_place_pct_v1"] is not None and result["rank1_place_pct_v1"] is not None
            else None,
            3,
        )
        result["rank1_roi_delta_vs_baseline_v1"] = round_num(
            (result["rank1_roi_pct_v1"] - baseline["rank1_roi_pct_v1"])
            if baseline["rank1_roi_pct_v1"] is not None and result["rank1_roi_pct_v1"] is not None
            else None,
            3,
        )

        if reduction_name == "NO_CHANGE":
            result["recommendation_v1"] = "NO_CHANGE"
        else:
            cal_improve = result["target_abs_calibration_improvement_v1"]
            brier_delta = result["brier_delta_vs_baseline_v1"]
            rank1_win_delta = result["rank1_win_delta_vs_baseline_v1"]
            rank1_place_delta = result["rank1_place_delta_vs_baseline_v1"]
            if (
                cal_improve is not None
                and cal_improve >= 1.0
                and (brier_delta is not None and brier_delta >= 0)
                and (rank1_win_delta is not None and rank1_win_delta >= 0)
                and (rank1_place_delta is not None and rank1_place_delta >= 0)
            ):
                result["recommendation_v1"] = "PROMOTION_CANDIDATE"
            elif (
                cal_improve is not None
                and cal_improve > 0
                and (brier_delta is None or brier_delta >= -0.0005)
                and (rank1_win_delta is None or rank1_win_delta >= -0.5)
                and (rank1_place_delta is None or rank1_place_delta >= -0.5)
            ):
                result["recommendation_v1"] = "RESEARCH_ONLY"
            else:
                result["recommendation_v1"] = "DO_NOT_USE"

    return result


def run_scenario(base_detail: pd.DataFrame, segment_def: dict[str, object], reduction_name: str, reduction_pct: float) -> tuple[pd.DataFrame, dict[str, object]]:
    scenario_df = base_detail.copy()
    target_mask = build_segment_flag(scenario_df, segment_def)
    scenario_df["segment_id_v1"] = segment_def["segment_id_v1"]
    scenario_df["segment_label_v1"] = segment_def["segment_label_v1"]
    scenario_df["guardrail_name_v1"] = reduction_name
    scenario_df["reduction_pct_v1"] = round_num(reduction_pct * 100.0, 3)
    scenario_df["target_segment_flag_v1"] = target_mask.map(lambda value: "YES" if value else "NO")

    scenario_df["adjustment_multiplier_v1"] = 1.0
    scenario_df.loc[target_mask, "adjustment_multiplier_v1"] = 1.0 - reduction_pct
    scenario_df["adjusted_probability_pre_renorm_v1"] = scenario_df["base_probability_norm_v1"] * scenario_df["adjustment_multiplier_v1"]
    race_sums = scenario_df.groupby("backtest_race_key", dropna=False)["adjusted_probability_pre_renorm_v1"].transform("sum")
    scenario_df["adjusted_probability_v1"] = scenario_df["adjusted_probability_pre_renorm_v1"] / race_sums
    scenario_df["adjusted_probability_v1"] = scenario_df["adjusted_probability_v1"].fillna(0.0)
    scenario_df["adjusted_fair_price_v1"] = scenario_df["adjusted_probability_v1"].map(fair_from_probability)

    scenario_df = scenario_df.sort_values(
        ["backtest_race_key", "adjusted_probability_v1", "horse_key"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    scenario_df["adjusted_rank_v1"] = scenario_df.groupby("backtest_race_key", dropna=False).cumcount() + 1

    baseline_stub = {}
    summary = summarize_scenario(
        scenario_df=scenario_df,
        segment_id=segment_def["segment_id_v1"],
        segment_label=segment_def["segment_label_v1"],
        reduction_name=reduction_name,
        reduction_pct=reduction_pct,
        target_mask=scenario_df["target_segment_flag_v1"].eq("YES"),
        baseline_lookup=baseline_stub,
    )
    return scenario_df, summary


def build_replay_and_summary() -> tuple[pd.DataFrame, pd.DataFrame]:
    base_detail = prepare_base_detail()

    replay_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []
    baseline_lookup: dict[tuple[str, str], dict[str, object]] = {}

    for segment_def in TARGET_SEGMENTS:
        for scenario in REDUCTION_SCENARIOS:
            scenario_df = base_detail.copy()
            target_mask = build_segment_flag(scenario_df, segment_def)
            scenario_df["segment_id_v1"] = segment_def["segment_id_v1"]
            scenario_df["segment_label_v1"] = segment_def["segment_label_v1"]
            scenario_df["guardrail_name_v1"] = scenario["guardrail_name_v1"]
            scenario_df["reduction_pct_v1"] = round_num(scenario["reduction_pct_v1"] * 100.0, 3)
            scenario_df["scenario_id_v1"] = f"{segment_def['segment_id_v1']}|{scenario['guardrail_name_v1']}"
            scenario_df["target_segment_flag_v1"] = target_mask.map(lambda value: "YES" if value else "NO")
            scenario_df["adjustment_multiplier_v1"] = 1.0
            scenario_df.loc[target_mask, "adjustment_multiplier_v1"] = 1.0 - scenario["reduction_pct_v1"]
            scenario_df["adjusted_probability_pre_renorm_v1"] = scenario_df["base_probability_norm_v1"] * scenario_df["adjustment_multiplier_v1"]
            race_sums = scenario_df.groupby("backtest_race_key", dropna=False)["adjusted_probability_pre_renorm_v1"].transform("sum")
            scenario_df["adjusted_probability_v1"] = scenario_df["adjusted_probability_pre_renorm_v1"] / race_sums
            scenario_df["adjusted_probability_v1"] = scenario_df["adjusted_probability_v1"].fillna(0.0)
            scenario_df["adjusted_fair_price_v1"] = scenario_df["adjusted_probability_v1"].map(fair_from_probability)
            scenario_df = scenario_df.sort_values(
                ["backtest_race_key", "adjusted_probability_v1", "horse_key"],
                ascending=[True, False, True],
            ).reset_index(drop=True)
            scenario_df["adjusted_rank_v1"] = scenario_df.groupby("backtest_race_key", dropna=False).cumcount() + 1

            target_mask_sorted = scenario_df["target_segment_flag_v1"].eq("YES")
            summary = summarize_scenario(
                scenario_df=scenario_df,
                segment_id=segment_def["segment_id_v1"],
                segment_label=segment_def["segment_label_v1"],
                reduction_name=scenario["guardrail_name_v1"],
                reduction_pct=scenario["reduction_pct_v1"],
                target_mask=target_mask_sorted,
                baseline_lookup=baseline_lookup,
            )
            summary_rows.append(summary)
            if scenario["guardrail_name_v1"] == "NO_CHANGE":
                baseline_lookup[(segment_def["segment_id_v1"], "NO_CHANGE")] = summary

            replay_frames.append(
                scenario_df[
                    [
                        "segment_id_v1",
                        "segment_label_v1",
                        "guardrail_name_v1",
                        "reduction_pct_v1",
                        "scenario_id_v1",
                        "race_key",
                        "backtest_race_key",
                        "meeting_date",
                        "track",
                        "race_no",
                        "horse",
                        "horse_key",
                        "won",
                        "placed",
                        "finish_position",
                        "sp",
                        "projection_band_V6_1_RESEARCH",
                        "class_bucket_v1",
                        "distance_bucket_v1",
                        "condition_group_v1",
                        "starts_bucket_v1",
                        "field_size_bucket_v1",
                        "probability_bucket_v1",
                        "price_rank_bucket_v1",
                        "target_segment_flag_v1",
                        "base_probability_norm_v1",
                        "base_fair_price_norm_v1",
                        "base_rank_v1",
                        "adjustment_multiplier_v1",
                        "adjusted_probability_pre_renorm_v1",
                        "adjusted_probability_v1",
                        "adjusted_fair_price_v1",
                        "adjusted_rank_v1",
                        "built_at_v1",
                    ]
                ].copy()
            )

    summary_df = pd.DataFrame(summary_rows)

    final_rows: list[dict[str, object]] = []
    for segment_def in TARGET_SEGMENTS:
        segment_rows = summary_df[summary_df["segment_id_v1"].eq(segment_def["segment_id_v1"])].copy()
        adjusted_rows = segment_rows[segment_rows["guardrail_name_v1"].ne("NO_CHANGE")].copy()
        if adjusted_rows.empty:
            continue
        best = adjusted_rows.sort_values(
            ["recommendation_v1", "target_abs_calibration_improvement_v1", "brier_delta_vs_baseline_v1", "rank1_win_delta_vs_baseline_v1"],
            ascending=[True, False, False, False],
        ).iloc[0].to_dict()
        final_rows.append(
            {
                "row_type_v1": "SEGMENT_RECOMMENDATION",
                "segment_id_v1": segment_def["segment_id_v1"],
                "segment_label_v1": segment_def["segment_label_v1"],
                "guardrail_name_v1": best["guardrail_name_v1"],
                "reduction_pct_v1": best["reduction_pct_v1"],
                "scenario_id_v1": best["scenario_id_v1"],
                "recommendation_v1": best["recommendation_v1"],
                "rows_v1": best["rows_v1"],
                "races_v1": best["races_v1"],
                "targeted_rows_v1": best["targeted_rows_v1"],
                "targeted_races_v1": best["targeted_races_v1"],
                "brier_score_v1": best["brier_score_v1"],
                "rank1_actual_win_pct_v1": best["rank1_actual_win_pct_v1"],
                "rank1_place_pct_v1": best["rank1_place_pct_v1"],
                "rank1_roi_pct_v1": best["rank1_roi_pct_v1"],
                "target_calibration_delta_before_v1": best["target_calibration_delta_before_v1"],
                "target_calibration_delta_after_v1": best["target_calibration_delta_after_v1"],
                "target_abs_calibration_improvement_v1": best["target_abs_calibration_improvement_v1"],
                "brier_delta_vs_baseline_v1": best["brier_delta_vs_baseline_v1"],
                "rank1_win_delta_vs_baseline_v1": best["rank1_win_delta_vs_baseline_v1"],
                "rank1_place_delta_vs_baseline_v1": best["rank1_place_delta_vs_baseline_v1"],
                "rank1_roi_delta_vs_baseline_v1": best["rank1_roi_delta_vs_baseline_v1"],
                "notes_v1": "best adjusted scenario for target segment under deterministic replay rules",
                "built_at_v1": datetime.now(timezone.utc).isoformat(),
            }
        )

    if final_rows:
        summary_df = pd.concat([summary_df, pd.DataFrame(final_rows)], ignore_index=True, sort=False)

    replay_df = pd.concat(replay_frames, ignore_index=True)
    return replay_df, summary_df


def main() -> None:
    replay_df, summary_df = build_replay_and_summary()
    replay_df.to_csv(OUT_REPLAY, index=False)
    summary_df.to_csv(OUT_SUMMARY, index=False)

    scenario_rows = summary_df[summary_df["row_type_v1"].eq("SCENARIO")].copy()
    segment_best = summary_df[summary_df["row_type_v1"].eq("SEGMENT_RECOMMENDATION")].copy()

    print("[EDGEIQ_V6_1_SEGMENT_GUARDRAIL_REPLAY_V1] COMPLETE")
    print(
        scenario_rows[
            [
                "segment_id_v1",
                "guardrail_name_v1",
                "targeted_rows_v1",
                "target_calibration_delta_before_v1",
                "target_calibration_delta_after_v1",
                "target_abs_calibration_improvement_v1",
                "brier_score_v1",
                "rank1_actual_win_pct_v1",
                "rank1_place_pct_v1",
                "rank1_roi_pct_v1",
                "recommendation_v1",
            ]
        ].to_string(index=False)
    )
    if not segment_best.empty:
        print(segment_best.to_string(index=False))
    print(f"wrote={OUT_REPLAY}")
    print(f"wrote={OUT_SUMMARY}")


if __name__ == "__main__":
    main()
