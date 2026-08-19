from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

REPLAY = DATA / "edgeiq_historical_replay_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUT = DATA / "edgeiq_historical_pace_advantage_replay_v1.csv"
SUMMARY = DATA / "edgeiq_historical_pace_advantage_replay_v1_summary.csv"
RANK_BUCKETS = DATA / "edgeiq_historical_pace_advantage_replay_v1_rank_buckets.csv"


RANK_BUCKET_ORDER = ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]
STYLE_ORDER = ["LEADER", "ON_PACE", "MIDFIELD", "BACKMARKER"]
PACE_BAND_ORDER = ["VERY_FAST", "FAST", "NEUTRAL", "SLOW", "VERY_SLOW", "UNKNOWN"]

PACE_MATRIX = {
    "VERY_SLOW": {"LEADER": 4, "ON_PACE": 2, "MIDFIELD": -2, "BACKMARKER": -4},
    "SLOW": {"LEADER": 2, "ON_PACE": 2, "MIDFIELD": 0, "BACKMARKER": -2},
    "NEUTRAL": {"LEADER": 0, "ON_PACE": 0, "MIDFIELD": 0, "BACKMARKER": 0},
    "FAST": {"LEADER": -2, "ON_PACE": -2, "MIDFIELD": 2, "BACKMARKER": 4},
    "VERY_FAST": {"LEADER": -4, "ON_PACE": -2, "MIDFIELD": 2, "BACKMARKER": 4},
}


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


def parse_inrun_position(value: object) -> float:
    nums = re.findall(r"\d+", upper_text(value))
    if not nums:
        return math.nan
    return float(nums[0])


def classify_position(pos: float, field_size: float) -> str:
    if pd.isna(pos) or pd.isna(field_size) or field_size <= 0:
        return "UNKNOWN"
    ratio = pos / max(1.0, field_size)
    if pos <= 1.5 or ratio <= 0.16:
        return "LEADER"
    if ratio <= 0.38:
        return "ON_PACE"
    if ratio <= 0.68:
        return "MIDFIELD"
    return "BACKMARKER"


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def choose_style_snapshot(counts: dict[str, int]) -> tuple[str, int, float, float, float, float]:
    total = sum(int(counts.get(style, 0)) for style in STYLE_ORDER)
    if total <= 0:
        return "UNKNOWN", 0, 0.0, 0.0, 0.0, 0.0

    probs = {style: float(counts.get(style, 0)) / total for style in STYLE_ORDER}
    best_style = max(probs, key=probs.get)
    return (
        best_style,
        total,
        round(probs["LEADER"], 4),
        round(probs["ON_PACE"], 4),
        round(probs["MIDFIELD"], 4),
        round(probs["BACKMARKER"], 4),
    )


def style_confidence(style_starts_before: int) -> str:
    if style_starts_before >= 6:
        return "HIGH"
    if style_starts_before >= 4:
        return "MEDIUM"
    if style_starts_before >= 2:
        return "LOW"
    if style_starts_before >= 1:
        return "VERY_LOW"
    return "INSUFFICIENT"


def pace_confidence_scale(style_starts_before: int) -> float:
    if style_starts_before < 2:
        return 0.0
    if style_starts_before < 4:
        return 0.5
    if style_starts_before < 6:
        return 0.75
    return 1.0


def pace_pressure_band(score: float, known_count: int) -> str:
    if known_count <= 0 or pd.isna(score):
        return "UNKNOWN"
    if score >= 2.25:
        return "VERY_FAST"
    if score >= 1.85:
        return "FAST"
    if score >= 1.35:
        return "NEUTRAL"
    if score >= 0.90:
        return "SLOW"
    return "VERY_SLOW"


def weighted_adjustment(raw_score: int, scale: float) -> int:
    return int(round(raw_score * scale))


def pace_advantage_band(score: int) -> str:
    if score >= 4:
        return "STRONG_ADVANTAGE"
    if score >= 1:
        return "MILD_ADVANTAGE"
    if score <= -4:
        return "STRONG_DISADVANTAGE"
    if score <= -1:
        return "MILD_DISADVANTAGE"
    return "NEUTRAL"


def pace_advantage_reason(pace_band: str, tactical_style: str, style_used: bool, pace_score: int) -> str:
    if pace_band == "UNKNOWN":
        return "insufficient race-level tactical history; no pace adjustment applied"
    if not style_used or tactical_style == "UNKNOWN":
        return "insufficient horse tactical history; no pace adjustment applied"
    if pace_score > 0:
        return f"{tactical_style} profile favoured by projected {pace_band} tempo"
    if pace_score < 0:
        return f"{tactical_style} profile disadvantaged by projected {pace_band} tempo"
    return f"projected {pace_band} tempo gives no material pace edge"


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


def build_rank_bucket_table(df: pd.DataFrame, rank_col: str, model_name: str) -> pd.DataFrame:
    work = df.copy()
    work["rank_bucket"] = work[rank_col].apply(rank_bucket)
    grouped = (
        work.groupby("rank_bucket", as_index=False)
        .agg(runners=("horse_key", "count"), wins=("won", "sum"))
    )
    grouped["rank_bucket"] = pd.Categorical(grouped["rank_bucket"], categories=RANK_BUCKET_ORDER, ordered=True)
    grouped = grouped.sort_values("rank_bucket").reset_index(drop=True)
    grouped["win_rate"] = (grouped["wins"] / grouped["runners"]).round(6)
    grouped["model"] = model_name
    return grouped[["model", "rank_bucket", "runners", "wins", "win_rate"]]


def monotonicity_pass(rank_bucket_df: pd.DataFrame) -> bool:
    rates = {
        str(row.rank_bucket): float(row.win_rate)
        for row in rank_bucket_df.itertuples(index=False)
    }
    return all(rates.get(RANK_BUCKET_ORDER[i], -1.0) > rates.get(RANK_BUCKET_ORDER[i + 1], -1.0) for i in range(len(RANK_BUCKET_ORDER) - 1))


def winner_metrics(df: pd.DataFrame, rank_col: str) -> dict[str, float]:
    winners = df[df["won"].eq(1)].copy()
    if winners.empty:
        return {
            "winner_top1_rate": 0.0,
            "winner_top3_rate": 0.0,
            "winner_top5_rate": 0.0,
            "winner_top10_rate": 0.0,
            "avg_winner_rank": 0.0,
        }

    ranks = pd.to_numeric(winners[rank_col], errors="coerce")
    return {
        "winner_top1_rate": round(float(ranks.le(1).mean()), 4),
        "winner_top3_rate": round(float(ranks.le(3).mean()), 4),
        "winner_top5_rate": round(float(ranks.le(5).mean()), 4),
        "winner_top10_rate": round(float(ranks.le(10).mean()), 4),
        "avg_winner_rank": round(float(ranks.mean()), 3),
    }


def load_replay() -> pd.DataFrame:
    if not REPLAY.exists():
        raise FileNotFoundError(f"Missing historical replay file: {REPLAY}")

    replay = pd.read_csv(REPLAY, low_memory=False)
    replay["meeting_date"] = replay["meeting_date"].astype(str).str.slice(0, 10)
    replay["track_norm"] = replay["track_norm"].fillna(replay["track"].map(norm_track))
    replay["race_no"] = pd.to_numeric(replay["race_no"], errors="coerce").astype("Int64")
    replay["runner_score"] = pd.to_numeric(replay["runner_score"], errors="coerce")
    replay["runner_rank"] = pd.to_numeric(replay["runner_rank"], errors="coerce")
    replay["won"] = pd.to_numeric(replay["won"], errors="coerce").fillna(0).astype(int)
    replay["finish_position"] = pd.to_numeric(replay["finish_position"], errors="coerce")
    replay["horse_key"] = replay["horse_key"].fillna(replay["horse"].map(canon_horse))
    replay["race_key"] = replay["race_key"].where(
        replay["race_key"].fillna("").astype(str).str.strip().ne(""),
        replay["meeting_date"].astype(str)
        + "|"
        + replay["track_norm"].astype(str)
        + "|R"
        + replay["race_no"].astype(str),
    )
    replay = replay.sort_values(["meeting_date", "track_norm", "race_no", "horse_key"]).reset_index(drop=True)
    return replay


def load_results_styles() -> dict[str, pd.DataFrame]:
    if not RESULTS.exists():
        raise FileNotFoundError(f"Missing results warehouse file: {RESULTS}")

    results = pd.read_csv(RESULTS, low_memory=False)
    results["meeting_date"] = results["meeting_date"].astype(str).str.slice(0, 10)
    results["track_norm"] = results["track"].map(norm_track)
    results["race_no"] = pd.to_numeric(results["race_no"], errors="coerce").astype("Int64")
    results["horse_key"] = results["horseKey"].fillna(results["horseName"]).map(canon_horse)
    results["finish_num"] = pd.to_numeric(results["finishPosition"], errors="coerce")
    results["inrun_pos"] = results["inRun"].apply(parse_inrun_position)

    field_sizes = (
        results[results["finish_num"].notna()]
        .groupby(["meeting_date", "track_norm", "race_no"], as_index=False)
        .agg(field_size=("horse_key", "count"))
    )
    all_field_sizes = (
        results.groupby(["meeting_date", "track_norm", "race_no"], as_index=False)
        .agg(all_field_size=("horse_key", "count"))
    )
    field_sizes = all_field_sizes.merge(field_sizes, on=["meeting_date", "track_norm", "race_no"], how="left")
    field_sizes["field_size"] = field_sizes["field_size"].fillna(field_sizes["all_field_size"])

    results = results.merge(field_sizes[["meeting_date", "track_norm", "race_no", "field_size"]], on=["meeting_date", "track_norm", "race_no"], how="left")
    results["style_observed"] = [
        classify_position(pos, field_size)
        for pos, field_size in zip(results["inrun_pos"], results["field_size"])
    ]

    results = results[["meeting_date", "horse_key", "style_observed"]].copy()
    return {date: group for date, group in results.groupby("meeting_date", sort=True)}


def main() -> None:
    replay = load_replay()
    results_by_date = load_results_styles()

    style_history: defaultdict[str, dict[str, int]] = defaultdict(lambda: {style: 0 for style in STYLE_ORDER})
    replay_parts: list[pd.DataFrame] = []

    for meeting_date, day in replay.groupby("meeting_date", sort=True):
        work = day.copy()

        snapshots = [choose_style_snapshot(style_history[horse_key]) for horse_key in work["horse_key"]]
        work["tactical_style_pre_race_v1"] = [item[0] for item in snapshots]
        work["style_starts_before_v1"] = [item[1] for item in snapshots]
        work["leader_pct_pre_race_v1"] = [item[2] for item in snapshots]
        work["on_pace_pct_pre_race_v1"] = [item[3] for item in snapshots]
        work["midfield_pct_pre_race_v1"] = [item[4] for item in snapshots]
        work["backmarker_pct_pre_race_v1"] = [item[5] for item in snapshots]
        work["tactical_style_confidence_v1"] = work["style_starts_before_v1"].apply(style_confidence)
        work["pace_confidence_scale_v1"] = work["style_starts_before_v1"].apply(pace_confidence_scale)
        work["style_used_for_pace_v1"] = work["pace_confidence_scale_v1"].gt(0)

        race_parts: list[pd.DataFrame] = []
        for race_key, race_group in work.groupby("race_key", sort=False):
            eligible = race_group[race_group["style_used_for_pace_v1"]].copy()
            leaders_count = int(eligible["tactical_style_pre_race_v1"].eq("LEADER").sum())
            on_pace_count = int(eligible["tactical_style_pre_race_v1"].eq("ON_PACE").sum())
            midfield_count = int(eligible["tactical_style_pre_race_v1"].eq("MIDFIELD").sum())
            backmarker_count = int(eligible["tactical_style_pre_race_v1"].eq("BACKMARKER").sum())
            unknown_count = int(len(race_group) - len(eligible))
            field_size = int(len(race_group))
            known_style_count = leaders_count + on_pace_count + midfield_count + backmarker_count

            pace_score = math.nan
            if field_size > 0:
                pace_score = (
                    (leaders_count * 3.0)
                    + (on_pace_count * 2.0)
                    + (midfield_count * 1.0)
                    - (backmarker_count * 0.5)
                ) / field_size
            pace_band = pace_pressure_band(pace_score, known_style_count)
            pace_shape_note = (
                f"leaders={leaders_count} | on_pace={on_pace_count} | midfield={midfield_count} | "
                f"backmarker={backmarker_count} | unknown={unknown_count}"
            )

            race_out = race_group.copy()
            race_out["field_size_v1"] = field_size
            race_out["leaders_count_v1"] = leaders_count
            race_out["on_pace_count_v1"] = on_pace_count
            race_out["midfield_count_v1"] = midfield_count
            race_out["backmarker_count_v1"] = backmarker_count
            race_out["unknown_count_v1"] = unknown_count
            race_out["known_style_count_v1"] = known_style_count
            race_out["pace_pressure_score_v1"] = round(float(pace_score), 3) if pd.notna(pace_score) else np.nan
            race_out["pace_pressure_band_v1"] = pace_band
            race_out["pace_shape_note_v1"] = pace_shape_note

            raw_scores = []
            final_scores = []
            final_bands = []
            final_reasons = []
            for row in race_out.itertuples(index=False):
                style = row.tactical_style_pre_race_v1
                scale = float(row.pace_confidence_scale_v1)
                used = bool(row.style_used_for_pace_v1)
                raw_score = PACE_MATRIX.get(pace_band, {}).get(style, 0) if used else 0
                final_score = weighted_adjustment(raw_score, scale)
                raw_scores.append(raw_score)
                final_scores.append(final_score)
                final_bands.append(pace_advantage_band(final_score))
                final_reasons.append(pace_advantage_reason(pace_band, style, used, final_score))

            race_out["pace_advantage_raw_score_v1"] = raw_scores
            race_out["pace_advantage_score_v1"] = final_scores
            race_out["pace_advantage_band_v1"] = final_bands
            race_out["pace_advantage_reason_v1"] = final_reasons
            race_parts.append(race_out)

        day_out = pd.concat(race_parts, ignore_index=True)
        day_out["runner_score_pace_v1"] = (
            day_out["runner_score"].fillna(0.0) + day_out["pace_advantage_score_v1"].fillna(0.0)
        ).clip(0, 100).round(3)

        day_out = day_out.sort_values(
            ["race_key", "runner_score_pace_v1", "pace_advantage_score_v1", "runner_score", "horse_key"],
            ascending=[True, False, False, False, True],
        ).reset_index(drop=True)

        day_out["runner_order_pace_v1"] = day_out.groupby("race_key").cumcount() + 1
        day_out["runner_rank_pace_v1"] = (
            day_out.groupby("race_key")["runner_score_pace_v1"]
            .rank(method="min", ascending=False)
            .astype(int)
        )
        day_out["runner_rank_delta_v1"] = day_out["runner_rank"] - day_out["runner_rank_pace_v1"]

        top_scores = day_out.groupby("race_key")["runner_score_pace_v1"].transform("max")
        tied_top_counts = day_out.groupby("race_key")["runner_score_pace_v1"].transform(lambda values: int(values.eq(values.max()).sum()))
        all_identical = day_out.groupby("race_key")["runner_score_pace_v1"].transform(lambda values: int(values.nunique(dropna=False) <= 1))
        day_out["top_score_tied_in_pace_race_v1"] = tied_top_counts.gt(1).astype(int)
        day_out["tied_top_score_count_pace_v1"] = tied_top_counts.astype(int)
        day_out["all_scores_identical_pace_race_v1"] = all_identical.astype(int)
        day_out["top_runner_score_pace_v1"] = top_scores.round(3)

        replay_parts.append(day_out)

        results_for_date = results_by_date.get(meeting_date)
        if results_for_date is not None:
            for row in results_for_date.itertuples(index=False):
                if row.style_observed in STYLE_ORDER:
                    style_history[row.horse_key][row.style_observed] += 1

    out = pd.concat(replay_parts, ignore_index=True)

    base_rank_buckets = build_rank_bucket_table(out, "runner_rank", "BASELINE_REPLAY_V1")
    pace_rank_buckets = build_rank_bucket_table(out, "runner_rank_pace_v1", "REPLAY_PLUS_PACE_V1")
    rank_bucket_compare = pd.concat([base_rank_buckets, pace_rank_buckets], ignore_index=True)
    rank_bucket_compare.to_csv(RANK_BUCKETS, index=False)

    base_metrics = winner_metrics(out, "runner_rank")
    pace_metrics = winner_metrics(out, "runner_rank_pace_v1")
    base_monotonic = monotonicity_pass(base_rank_buckets)
    pace_monotonic = monotonicity_pass(pace_rank_buckets)

    winner_rows = out[out["won"].eq(1)].copy()
    unique_winner_races = int(winner_rows["race_key"].nunique())
    dead_heat_races = int(winner_rows.groupby("race_key").size().gt(1).sum())
    pace_race_bands = out.groupby("race_key")["pace_pressure_band_v1"].first()

    summary_rows: list[dict[str, object]] = [
        {"metric": "replay_rows", "value": int(len(out))},
        {"metric": "replay_races", "value": int(out["race_key"].nunique())},
        {"metric": "winner_rows", "value": int(len(winner_rows))},
        {"metric": "unique_winner_races", "value": unique_winner_races},
        {"metric": "dead_heat_races", "value": dead_heat_races},
        {"metric": "style_rows_with_any_history", "value": int(out["style_starts_before_v1"].gt(0).sum())},
        {"metric": "style_history_coverage_any", "value": round(float(out["style_starts_before_v1"].gt(0).mean()), 4)},
        {"metric": "style_rows_used_for_pace", "value": int(out["style_used_for_pace_v1"].sum())},
        {"metric": "style_history_coverage_used_for_pace", "value": round(float(out["style_used_for_pace_v1"].mean()), 4)},
        {"metric": "races_with_unknown_pace_band", "value": int(pace_race_bands.eq("UNKNOWN").sum())},
        {"metric": "races_with_tied_top_score_pace_v1", "value": int(out.groupby("race_key")["runner_score_pace_v1"].apply(lambda values: int(values.eq(values.max()).sum())).gt(1).sum())},
        {"metric": "races_with_all_identical_scores_pace_v1", "value": int(out.groupby("race_key")["runner_score_pace_v1"].nunique(dropna=False).le(1).sum())},
    ]

    for band in PACE_BAND_ORDER:
        summary_rows.append({"metric": f"pace_band_races::{band}", "value": int(pace_race_bands.eq(band).sum())})

    for metric_name, base_value in base_metrics.items():
        pace_value = pace_metrics[metric_name]
        if metric_name == "avg_winner_rank":
            delta = round(pace_value - base_value, 3)
            improved = pace_value < base_value
        else:
            delta = round(pace_value - base_value, 4)
            improved = pace_value > base_value

        summary_rows.append({"metric": f"baseline::{metric_name}", "value": base_value})
        summary_rows.append({"metric": f"pace::{metric_name}", "value": pace_value})
        summary_rows.append({"metric": f"delta_vs_baseline::{metric_name}", "value": delta})
        summary_rows.append({"metric": f"improved_vs_baseline::{metric_name}", "value": improved})

    improved_metric_count = int(sum(
        1
        for metric_name, base_value in base_metrics.items()
        if (pace_metrics[metric_name] < base_value if metric_name == "avg_winner_rank" else pace_metrics[metric_name] > base_value)
    ))

    summary_rows.extend([
        {"metric": "baseline::rank_monotonicity_pass", "value": base_monotonic},
        {"metric": "pace::rank_monotonicity_pass", "value": pace_monotonic},
        {"metric": "improved_metric_count", "value": improved_metric_count},
        {"metric": "pace_overlay_net_improved", "value": improved_metric_count >= 3 and pace_monotonic},
    ])

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(SUMMARY, index=False)

    base_columns = list(replay.columns)
    extra_columns = [
        "tactical_style_pre_race_v1",
        "style_starts_before_v1",
        "leader_pct_pre_race_v1",
        "on_pace_pct_pre_race_v1",
        "midfield_pct_pre_race_v1",
        "backmarker_pct_pre_race_v1",
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
        "runner_order_pace_v1",
        "runner_rank_pace_v1",
        "runner_rank_delta_v1",
        "top_runner_score_pace_v1",
        "top_score_tied_in_pace_race_v1",
        "tied_top_score_count_pace_v1",
        "all_scores_identical_pace_race_v1",
    ]
    keep = [column for column in base_columns + extra_columns if column in out.columns]
    out = out[keep].copy()
    out.to_csv(OUT, index=False)

    print("[EDGEIQ_HISTORICAL_PACE_ADVANTAGE_REPLAY_V1] COMPLETE")
    print(f"replay_rows={len(out)}")
    print(f"replay_races={out['race_key'].nunique()}")
    print(f"style_history_coverage_used_for_pace={round(float(out['style_used_for_pace_v1'].mean()), 4)}")
    print(f"baseline_top1={base_metrics['winner_top1_rate']}")
    print(f"pace_top1={pace_metrics['winner_top1_rate']}")
    print(f"baseline_top3={base_metrics['winner_top3_rate']}")
    print(f"pace_top3={pace_metrics['winner_top3_rate']}")
    print(f"baseline_top5={base_metrics['winner_top5_rate']}")
    print(f"pace_top5={pace_metrics['winner_top5_rate']}")
    print(f"baseline_top10={base_metrics['winner_top10_rate']}")
    print(f"pace_top10={pace_metrics['winner_top10_rate']}")
    print(f"baseline_avg_winner_rank={base_metrics['avg_winner_rank']}")
    print(f"pace_avg_winner_rank={pace_metrics['avg_winner_rank']}")
    print(f"baseline_rank_monotonicity_pass={base_monotonic}")
    print(f"pace_rank_monotonicity_pass={pace_monotonic}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")
    print(f"rank_buckets={RANK_BUCKETS}")


if __name__ == "__main__":
    main()
