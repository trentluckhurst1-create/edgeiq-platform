from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASELINE = DATA / "edgeiq_historical_replay_v1.csv"
BROAD_PACE = DATA / "edgeiq_historical_pace_advantage_replay_v1.csv"

OUT = DATA / "edgeiq_historical_pace_trust_replay_v1.csv"
SUMMARY = DATA / "edgeiq_historical_pace_trust_replay_v1_summary.csv"
RANK_BUCKETS = DATA / "edgeiq_historical_pace_trust_replay_v1_rank_buckets.csv"

RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]
TRUST_MULTIPLIER = {
    "HIGH_TRUST": 1.00,
    "MEDIUM_TRUST": 0.50,
    "LOW_TRUST": 0.25,
    "IGNORE": 0.00,
}


def trust_decision(pace_band: str, leaders_count: int, on_pace_count: int) -> tuple[int, str, str]:
    forward_count = int(leaders_count) + int(on_pace_count)
    pace_band = str(pace_band).upper().strip()

    if pace_band == "SLOW":
        if forward_count >= 3:
            return 100, "HIGH_TRUST", "SLOW pace with at least 3 forward runners; trust leader/on-pace pace signal"
        if forward_count >= 2:
            return 50, "MEDIUM_TRUST", "SLOW pace with 2 forward runners; use pace signal cautiously"
        return 0, "IGNORE", "SLOW pace but not enough forward pressure clarity"

    if pace_band == "VERY_SLOW":
        if forward_count >= 3:
            return 25, "LOW_TRUST", "VERY_SLOW pace can matter with 3+ forward runners, but trust stays low"
        return 0, "IGNORE", "VERY_SLOW pace generally ignored without enough forward runners"

    if pace_band in {"FAST", "VERY_FAST"}:
        if forward_count >= 4:
            return 25, "LOW_TRUST", "FAST pace with 4+ forward runners; collapse risk exists but trust remains low"
        return 0, "IGNORE", "FAST pace lacks enough forward-runner density for trusted adjustment"

    if pace_band == "NEUTRAL":
        return 0, "IGNORE", "NEUTRAL pace is always ignored for selective trust"

    return 0, "IGNORE", "No selective pace trust condition met"


def rank_bucket(rank_value: object) -> str:
    if pd.isna(rank_value):
        return "NO_RANK"
    rank_int = int(rank_value)
    if rank_int == 1:
        return "RANK_1"
    if rank_int == 2:
        return "RANK_2"
    if rank_int == 3:
        return "RANK_3"
    if rank_int <= 5:
        return "RANK_4_5"
    if rank_int <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def winner_metrics(df: pd.DataFrame, rank_col: str) -> dict[str, float]:
    winners = df[df["won"].eq(1)].copy()
    ranks = pd.to_numeric(winners[rank_col], errors="coerce")
    return {
        "winner_top1_rate": round(float(ranks.le(1).mean()), 4),
        "winner_top3_rate": round(float(ranks.le(3).mean()), 4),
        "winner_top5_rate": round(float(ranks.le(5).mean()), 4),
        "winner_top10_rate": round(float(ranks.le(10).mean()), 4),
        "avg_winner_rank": round(float(ranks.mean()), 3),
    }


def build_rank_bucket_table(df: pd.DataFrame, rank_col: str, model: str) -> pd.DataFrame:
    work = df.copy()
    work["rank_bucket"] = work[rank_col].apply(rank_bucket)
    grouped = (
        work.groupby("rank_bucket", as_index=False)
        .agg(runners=("horse_key", "count"), wins=("won", "sum"))
    )
    grouped["rank_bucket"] = pd.Categorical(grouped["rank_bucket"], categories=RANK_BUCKET_ORDER, ordered=True)
    grouped = grouped.sort_values("rank_bucket").reset_index(drop=True)
    grouped["win_rate"] = (grouped["wins"] / grouped["runners"]).round(6)
    grouped["model"] = model
    return grouped[["model", "rank_bucket", "runners", "wins", "win_rate"]]


def monotonicity_pass(rank_bucket_df: pd.DataFrame) -> bool:
    rates = {str(row.rank_bucket): float(row.win_rate) for row in rank_bucket_df.itertuples(index=False)}
    return all(rates.get(RANK_BUCKET_ORDER[i], -1.0) > rates.get(RANK_BUCKET_ORDER[i + 1], -1.0) for i in range(len(RANK_BUCKET_ORDER) - 1))


def main() -> None:
    if not BASELINE.exists():
        raise FileNotFoundError(f"Missing baseline historical replay: {BASELINE}")
    if not BROAD_PACE.exists():
        raise FileNotFoundError(f"Missing broad pace historical replay: {BROAD_PACE}")

    baseline = pd.read_csv(BASELINE, low_memory=False)
    broad = pd.read_csv(BROAD_PACE, low_memory=False)

    baseline["race_key"] = baseline["race_key"].astype(str).str.strip()
    baseline["horse_key"] = baseline["horse_key"].astype(str).str.strip()
    baseline["runner_score"] = pd.to_numeric(baseline["runner_score"], errors="coerce")
    baseline["runner_rank"] = pd.to_numeric(baseline["runner_rank"], errors="coerce")
    baseline["finish_position"] = pd.to_numeric(baseline["finish_position"], errors="coerce")
    baseline["won"] = pd.to_numeric(baseline["won"], errors="coerce").fillna(0).astype(int)

    broad["race_key"] = broad["race_key"].astype(str).str.strip()
    broad["horse_key"] = broad["horse_key"].astype(str).str.strip()
    broad["runner_rank_pace_v1"] = pd.to_numeric(broad["runner_rank_pace_v1"], errors="coerce")
    broad["runner_score_pace_v1"] = pd.to_numeric(broad["runner_score_pace_v1"], errors="coerce")
    broad["pace_advantage_score_v1"] = pd.to_numeric(broad["pace_advantage_score_v1"], errors="coerce").fillna(0.0)

    merge_cols = [
        "race_key",
        "horse_key",
        "tactical_style_pre_race_v1",
        "style_starts_before_v1",
        "tactical_style_confidence_v1",
        "pace_confidence_scale_v1",
        "style_used_for_pace_v1",
        "field_size_v1",
        "leaders_count_v1",
        "on_pace_count_v1",
        "midfield_count_v1",
        "backmarker_count_v1",
        "unknown_count_v1",
        "known_style_count_v1",
        "pace_pressure_score_v1",
        "pace_pressure_band_v1",
        "pace_shape_note_v1",
        "pace_advantage_raw_score_v1",
        "pace_advantage_score_v1",
        "pace_advantage_band_v1",
        "pace_advantage_reason_v1",
        "runner_score_pace_v1",
        "runner_rank_pace_v1",
        "runner_rank_delta_v1",
    ]

    merged = baseline.merge(
        broad[[col for col in merge_cols if col in broad.columns]],
        on=["race_key", "horse_key"],
        how="left",
    )
    if merged.empty:
        raise RuntimeError("No rows matched between historical baseline replay and broad pace replay.")

    decisions = [
        trust_decision(band, leaders, on_pace)
        for band, leaders, on_pace in zip(
            merged["pace_pressure_band_v1"],
            merged["leaders_count_v1"],
            merged["on_pace_count_v1"],
        )
    ]
    merged["pace_trust_score_v1"] = [item[0] for item in decisions]
    merged["pace_trust_band_v1"] = [item[1] for item in decisions]
    merged["pace_trust_reason_v1"] = [item[2] for item in decisions]
    merged["trust_multiplier_v1"] = merged["pace_trust_band_v1"].map(TRUST_MULTIPLIER).fillna(0.0)
    merged["pace_adjustment_trusted_v1"] = (
        merged["pace_advantage_score_v1"].fillna(0.0) * merged["trust_multiplier_v1"]
    ).round(3)

    merged["runner_score_pace_trust_v1"] = np.clip(
        merged["runner_score"].fillna(0.0) + merged["pace_adjustment_trusted_v1"].fillna(0.0),
        0,
        100,
    ).round(3)

    merged = merged.sort_values(
        ["race_key", "runner_score_pace_trust_v1", "pace_adjustment_trusted_v1", "runner_score", "horse_key"],
        ascending=[True, False, False, False, True],
    ).reset_index(drop=True)
    merged["runner_order_pace_trust_v1"] = merged.groupby("race_key").cumcount() + 1
    merged["runner_rank_pace_trust_v1"] = (
        merged.groupby("race_key")["runner_score_pace_trust_v1"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    merged["runner_rank_delta_pace_trust_v1"] = merged["runner_rank"] - merged["runner_rank_pace_trust_v1"]

    top_scores = merged.groupby("race_key")["runner_score_pace_trust_v1"].transform("max")
    tied_top_counts = merged.groupby("race_key")["runner_score_pace_trust_v1"].transform(lambda values: int(values.eq(values.max()).sum()))
    all_identical = merged.groupby("race_key")["runner_score_pace_trust_v1"].transform(lambda values: int(values.nunique(dropna=False) <= 1))
    merged["top_score_tied_in_pace_trust_race_v1"] = tied_top_counts.gt(1).astype(int)
    merged["tied_top_score_count_pace_trust_v1"] = tied_top_counts.astype(int)
    merged["all_scores_identical_pace_trust_race_v1"] = all_identical.astype(int)
    merged["top_runner_score_pace_trust_v1"] = top_scores.round(3)

    base_rank_buckets = build_rank_bucket_table(merged, "runner_rank", "BASELINE_REPLAY_V1")
    broad_rank_buckets = build_rank_bucket_table(merged, "runner_rank_pace_v1", "BROAD_PACE_REPLAY_V1")
    trust_rank_buckets = build_rank_bucket_table(merged, "runner_rank_pace_trust_v1", "SELECTIVE_PACE_TRUST_REPLAY_V1")
    rank_bucket_compare = pd.concat([base_rank_buckets, broad_rank_buckets, trust_rank_buckets], ignore_index=True)
    rank_bucket_compare.to_csv(RANK_BUCKETS, index=False)

    baseline_metrics = winner_metrics(merged, "runner_rank")
    broad_metrics = winner_metrics(merged, "runner_rank_pace_v1")
    trust_metrics = winner_metrics(merged, "runner_rank_pace_trust_v1")

    baseline_monotonic = monotonicity_pass(base_rank_buckets)
    broad_monotonic = monotonicity_pass(broad_rank_buckets)
    trust_monotonic = monotonicity_pass(trust_rank_buckets)

    winner_rows = merged[merged["won"].eq(1)].copy()
    unique_winner_races = int(winner_rows["race_key"].nunique())
    dead_heat_races = int(winner_rows.groupby("race_key").size().gt(1).sum())

    trust_improved_vs_baseline = 0
    trust_improved_vs_broad = 0
    summary_rows = [
        {"metric": "replay_rows", "value": int(len(merged))},
        {"metric": "replay_races", "value": int(merged["race_key"].nunique())},
        {"metric": "winner_rows", "value": int(len(winner_rows))},
        {"metric": "unique_winner_races", "value": unique_winner_races},
        {"metric": "dead_heat_races", "value": dead_heat_races},
        {"metric": "trusted_rows", "value": int(merged["pace_trust_band_v1"].ne("IGNORE").sum())},
        {"metric": "trusted_row_coverage", "value": round(float(merged["pace_trust_band_v1"].ne("IGNORE").mean()), 4)},
        {"metric": "trusted_races", "value": int(merged.groupby("race_key")["pace_trust_band_v1"].first().ne("IGNORE").sum())},
        {"metric": "races_tied_top_score_selective", "value": int(merged.groupby("race_key")["runner_score_pace_trust_v1"].apply(lambda values: int(values.eq(values.max()).sum())).gt(1).sum())},
        {"metric": "races_all_identical_scores_selective", "value": int(merged.groupby("race_key")["runner_score_pace_trust_v1"].nunique(dropna=False).le(1).sum())},
    ]

    for band in ["HIGH_TRUST", "MEDIUM_TRUST", "LOW_TRUST", "IGNORE"]:
        summary_rows.append({"metric": f"trust_band::{band}", "value": int(merged["pace_trust_band_v1"].eq(band).sum())})

    for metric, baseline_value in baseline_metrics.items():
        trust_value = trust_metrics[metric]
        broad_value = broad_metrics[metric]
        delta_vs_baseline = round(trust_value - baseline_value, 4) if metric != "avg_winner_rank" else round(trust_value - baseline_value, 3)
        delta_vs_broad = round(trust_value - broad_value, 4) if metric != "avg_winner_rank" else round(trust_value - broad_value, 3)
        improved_baseline = trust_value > baseline_value if metric != "avg_winner_rank" else trust_value < baseline_value
        improved_broad = trust_value > broad_value if metric != "avg_winner_rank" else trust_value < broad_value
        trust_improved_vs_baseline += int(improved_baseline)
        trust_improved_vs_broad += int(improved_broad)

        summary_rows.extend([
            {"metric": f"baseline::{metric}", "value": baseline_value},
            {"metric": f"broad_pace::{metric}", "value": broad_value},
            {"metric": f"selective_trust::{metric}", "value": trust_value},
            {"metric": f"delta_vs_baseline::{metric}", "value": delta_vs_baseline},
            {"metric": f"delta_vs_broad_pace::{metric}", "value": delta_vs_broad},
            {"metric": f"improved_vs_baseline::{metric}", "value": improved_baseline},
            {"metric": f"improved_vs_broad_pace::{metric}", "value": improved_broad},
        ])

    summary_rows.extend([
        {"metric": "baseline::rank_monotonicity_pass", "value": baseline_monotonic},
        {"metric": "broad_pace::rank_monotonicity_pass", "value": broad_monotonic},
        {"metric": "selective_trust::rank_monotonicity_pass", "value": trust_monotonic},
        {"metric": "improved_metric_count_vs_baseline", "value": trust_improved_vs_baseline},
        {"metric": "improved_metric_count_vs_broad_pace", "value": trust_improved_vs_broad},
        {"metric": "selective_trust_improved_vs_baseline", "value": trust_improved_vs_baseline >= 3 and trust_monotonic},
        {"metric": "selective_trust_improved_vs_broad_pace", "value": trust_improved_vs_broad >= 3 and trust_monotonic},
    ])

    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    base_columns = list(baseline.columns)
    extra_columns = [
        "tactical_style_pre_race_v1",
        "style_starts_before_v1",
        "tactical_style_confidence_v1",
        "pace_confidence_scale_v1",
        "style_used_for_pace_v1",
        "field_size_v1",
        "leaders_count_v1",
        "on_pace_count_v1",
        "midfield_count_v1",
        "backmarker_count_v1",
        "unknown_count_v1",
        "known_style_count_v1",
        "pace_pressure_score_v1",
        "pace_pressure_band_v1",
        "pace_shape_note_v1",
        "pace_advantage_raw_score_v1",
        "pace_advantage_score_v1",
        "pace_advantage_band_v1",
        "pace_advantage_reason_v1",
        "runner_score_pace_v1",
        "runner_rank_pace_v1",
        "runner_rank_delta_v1",
        "pace_trust_score_v1",
        "pace_trust_band_v1",
        "pace_trust_reason_v1",
        "trust_multiplier_v1",
        "pace_adjustment_trusted_v1",
        "runner_score_pace_trust_v1",
        "runner_order_pace_trust_v1",
        "runner_rank_pace_trust_v1",
        "runner_rank_delta_pace_trust_v1",
        "top_runner_score_pace_trust_v1",
        "top_score_tied_in_pace_trust_race_v1",
        "tied_top_score_count_pace_trust_v1",
        "all_scores_identical_pace_trust_race_v1",
    ]
    keep = [column for column in base_columns + extra_columns if column in merged.columns]
    merged[keep].to_csv(OUT, index=False)

    print("[EDGEIQ_HISTORICAL_PACE_TRUST_REPLAY_V1] COMPLETE")
    print(f"replay_rows={len(merged)}")
    print(f"replay_races={merged['race_key'].nunique()}")
    print(f"trusted_row_coverage={round(float(merged['pace_trust_band_v1'].ne('IGNORE').mean()), 4)}")
    print(f"baseline_top1={baseline_metrics['winner_top1_rate']}")
    print(f"broad_top1={broad_metrics['winner_top1_rate']}")
    print(f"selective_top1={trust_metrics['winner_top1_rate']}")
    print(f"baseline_top3={baseline_metrics['winner_top3_rate']}")
    print(f"broad_top3={broad_metrics['winner_top3_rate']}")
    print(f"selective_top3={trust_metrics['winner_top3_rate']}")
    print(f"baseline_top5={baseline_metrics['winner_top5_rate']}")
    print(f"broad_top5={broad_metrics['winner_top5_rate']}")
    print(f"selective_top5={trust_metrics['winner_top5_rate']}")
    print(f"baseline_top10={baseline_metrics['winner_top10_rate']}")
    print(f"broad_top10={broad_metrics['winner_top10_rate']}")
    print(f"selective_top10={trust_metrics['winner_top10_rate']}")
    print(f"baseline_avg_winner_rank={baseline_metrics['avg_winner_rank']}")
    print(f"broad_avg_winner_rank={broad_metrics['avg_winner_rank']}")
    print(f"selective_avg_winner_rank={trust_metrics['avg_winner_rank']}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")
    print(f"rank_buckets={RANK_BUCKETS}")


if __name__ == "__main__":
    main()
