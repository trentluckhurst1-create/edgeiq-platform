from pathlib import Path
import numpy as np
import pandas as pd
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASELINE_REPLAY = DATA / "edgeiq_fair_price_replay_v1.csv"
BARRIER_RAIL_CONDITION = DATA / "edgeiq_barrier_rail_condition_bias_replay_v1.csv"

OUT_MAIN = DATA / "edgeiq_barrier_rail_condition_pricing_impact_replay_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_barrier_rail_condition_pricing_impact_replay_v1_summary.csv"
OUT_BY_BAND = DATA / "edgeiq_barrier_rail_condition_pricing_impact_replay_by_band_v1.csv"
OUT_BY_THRESHOLD = DATA / "edgeiq_barrier_rail_condition_pricing_impact_replay_by_overlay_threshold_v1.csv"

ADJUSTMENT_PCT = {
    "STRONG_POSITIVE": 1.0,
    "POSITIVE": 0.5,
    "NEUTRAL": 0.0,
    "NEGATIVE": -0.5,
    "STRONG_NEGATIVE": -1.0,
    "UNKNOWN": 0.0,
}

OVERLAY_THRESHOLDS = [0, 5, 10, 20, 30, 50]


def clean_text(value):
    if pd.isna(value):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def num(series):
    return pd.to_numeric(series, errors="coerce")


def pct(numerator, denominator):
    if denominator == 0:
        return np.nan
    return round(float(numerator) / float(denominator) * 100.0, 2)


def overlay_truth(is_overlay, won):
    if not is_overlay:
        return "NOT_OVERLAY"
    return "REAL_OVERLAY" if int(won) == 1 else "FAKE_OVERLAY"


def threshold_rows(df, baseline_prefix, candidate_prefix):
    rows = []
    for threshold in OVERLAY_THRESHOLDS:
        for prefix, label in [
            (baseline_prefix, "BASELINE_FAIR_PRICE_PROXY"),
            (candidate_prefix, "BARRIER_RAIL_CONDITION_CANDIDATE"),
        ]:
            mask = df[f"{prefix}_overlay_pct_v1"] > threshold
            runners = int(mask.sum())
            wins = int(df.loc[mask, "won"].sum()) if runners else 0
            false_positives = int((mask & df["won"].eq(0)).sum()) if runners else 0
            rows.append(
                {
                    "pricing_view_v1": label,
                    "overlay_threshold_gt_v1": threshold,
                    "runners": runners,
                    "wins": wins,
                    "win_pct": pct(wins, runners),
                    "false_positives": false_positives,
                    "false_positive_rate_pct": pct(false_positives, runners),
                    "avg_overlay_pct": round(float(df.loc[mask, f"{prefix}_overlay_pct_v1"].mean()), 2)
                    if runners
                    else np.nan,
                }
            )
    return pd.DataFrame(rows)


def main():
    for path in [BASELINE_REPLAY, BARRIER_RAIL_CONDITION]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")

    baseline = pd.read_csv(BASELINE_REPLAY, low_memory=False)
    brc = pd.read_csv(BARRIER_RAIL_CONDITION, low_memory=False)

    baseline["horse_name_key"] = baseline["horse"].map(clean_text)
    brc["horse_name_key"] = brc["horse"].map(clean_text)

    brc_small = brc[
        [
            "meeting_date",
            "track",
            "race_no",
            "horse_name_key",
            "barrier_num",
            "barrier_bucket",
            "rail_bucket",
            "condition_group",
            "barrier_rail_condition_lift_pts",
            "barrier_rail_condition_score_v1",
            "barrier_rail_condition_band_v1",
        ]
    ].copy()

    replay = baseline.merge(
        brc_small,
        on=["meeting_date", "track", "race_no", "horse_name_key"],
        how="left",
    )

    replay["runner_rank"] = num(replay["runner_rank"])
    replay["runner_score"] = num(replay["runner_score"])
    replay["finish_position"] = num(replay["finish_position"])
    replay["won"] = num(replay["won"]).fillna(0).astype(int)
    replay["fair_prob_replay_v1"] = num(replay["fair_prob_replay_v1"])
    replay["fair_price_replay_v1"] = num(replay["fair_price_replay_v1"])
    replay["barrier_rail_condition_score_v1"] = num(replay["barrier_rail_condition_score_v1"]).fillna(0.0)
    replay["barrier_rail_condition_lift_pts"] = num(replay["barrier_rail_condition_lift_pts"]).fillna(0.0)
    replay["barrier_rail_condition_band_v1"] = (
        replay["barrier_rail_condition_band_v1"].fillna("UNKNOWN").astype(str).str.upper()
    )

    replay["barrier_rail_condition_adjustment_pct_v1"] = (
        replay["barrier_rail_condition_band_v1"].map(ADJUSTMENT_PCT).fillna(0.0)
    )
    replay["barrier_rail_condition_probability_multiplier_v1"] = (
        1.0 + (replay["barrier_rail_condition_adjustment_pct_v1"] / 100.0)
    )
    replay["barrier_rail_condition_adjustment_reason_v1"] = (
        "BRC_BAND:"
        + replay["barrier_rail_condition_band_v1"]
        + " => "
        + replay["barrier_rail_condition_adjustment_pct_v1"].map(lambda value: f"{value:+.1f}%")
    )

    replay["baseline_prob_v1"] = replay["fair_prob_replay_v1"]
    replay["baseline_fair_price_v1"] = replay["fair_price_replay_v1"]
    replay["brc_adjusted_raw_prob_v1"] = (
        replay["baseline_prob_v1"] * replay["barrier_rail_condition_probability_multiplier_v1"]
    )
    replay["brc_adjusted_prob_v1"] = (
        replay["brc_adjusted_raw_prob_v1"]
        / replay.groupby("race_key")["brc_adjusted_raw_prob_v1"].transform("sum")
    )
    replay["brc_adjusted_fair_price_v1"] = 1.0 / replay["brc_adjusted_prob_v1"]
    replay["brc_fair_price_delta_v1"] = (
        replay["brc_adjusted_fair_price_v1"] - replay["baseline_fair_price_v1"]
    ).round(4)
    replay["brc_prob_delta_v1"] = (
        replay["brc_adjusted_prob_v1"] - replay["baseline_prob_v1"]
    ).round(6)

    replay = replay.sort_values(
        ["race_key", "baseline_prob_v1", "horse_name_key"],
        ascending=[True, False, True],
    ).copy()
    replay["baseline_price_rank_v1"] = replay.groupby("race_key").cumcount() + 1

    replay = replay.sort_values(
        ["race_key", "brc_adjusted_prob_v1", "horse_name_key"],
        ascending=[True, False, True],
    ).copy()
    replay["brc_adjusted_price_rank_v1"] = replay.groupby("race_key").cumcount() + 1
    replay["price_rank_changed_flag_v1"] = (
        replay["baseline_price_rank_v1"] != replay["brc_adjusted_price_rank_v1"]
    )

    replay["field_size_proxy_v1"] = replay.groupby("race_key")["horse_name_key"].transform("count")
    replay["market_proxy_probability_v1"] = np.where(
        replay["field_size_proxy_v1"].gt(0), 1.0 / replay["field_size_proxy_v1"], np.nan
    )
    replay["market_proxy_fair_odds_v1"] = replay["field_size_proxy_v1"]

    replay["baseline_overlay_pct_v1"] = (
        (replay["market_proxy_fair_odds_v1"] / replay["baseline_fair_price_v1"]) - 1.0
    ) * 100.0
    replay["brc_adjusted_overlay_pct_v1"] = (
        (replay["market_proxy_fair_odds_v1"] / replay["brc_adjusted_fair_price_v1"]) - 1.0
    ) * 100.0

    replay["baseline_positive_overlay_flag_v1"] = replay["baseline_overlay_pct_v1"] > 0
    replay["brc_adjusted_positive_overlay_flag_v1"] = replay["brc_adjusted_overlay_pct_v1"] > 0

    replay["baseline_overlay_truth_v1"] = [
        overlay_truth(flag, won)
        for flag, won in zip(replay["baseline_positive_overlay_flag_v1"], replay["won"])
    ]
    replay["brc_adjusted_overlay_truth_v1"] = [
        overlay_truth(flag, won)
        for flag, won in zip(replay["brc_adjusted_positive_overlay_flag_v1"], replay["won"])
    ]

    replay["overlay_added_by_brc_v1"] = (
        ~replay["baseline_positive_overlay_flag_v1"]
        & replay["brc_adjusted_positive_overlay_flag_v1"]
    )
    replay["overlay_removed_by_brc_v1"] = (
        replay["baseline_positive_overlay_flag_v1"]
        & ~replay["brc_adjusted_positive_overlay_flag_v1"]
    )

    winners = replay[replay["won"] == 1].copy()
    baseline_top1 = replay[replay["baseline_price_rank_v1"] == 1].copy()
    adjusted_top1 = replay[replay["brc_adjusted_price_rank_v1"] == 1].copy()

    top1_compare = baseline_top1[
        ["race_key", "horse", "won", "barrier_rail_condition_band_v1", "baseline_prob_v1"]
    ].rename(
        columns={
            "horse": "baseline_top1_horse_v1",
            "won": "baseline_top1_won_v1",
            "barrier_rail_condition_band_v1": "baseline_top1_brc_band_v1",
            "baseline_prob_v1": "baseline_top1_prob_v1",
        }
    ).merge(
        adjusted_top1[
            ["race_key", "horse", "won", "barrier_rail_condition_band_v1", "brc_adjusted_prob_v1"]
        ].rename(
            columns={
                "horse": "brc_adjusted_top1_horse_v1",
                "won": "brc_adjusted_top1_won_v1",
                "barrier_rail_condition_band_v1": "brc_adjusted_top1_brc_band_v1",
                "brc_adjusted_prob_v1": "brc_adjusted_top1_prob_v1",
            }
        ),
        on="race_key",
        how="inner",
    )
    top1_compare["top1_changed_race_v1"] = (
        top1_compare["baseline_top1_horse_v1"] != top1_compare["brc_adjusted_top1_horse_v1"]
    )

    baseline_overlay_mask = replay["baseline_positive_overlay_flag_v1"]
    adjusted_overlay_mask = replay["brc_adjusted_positive_overlay_flag_v1"]

    baseline_overlay_rows = int(baseline_overlay_mask.sum())
    adjusted_overlay_rows = int(adjusted_overlay_mask.sum())
    baseline_overlay_wins = int(replay.loc[baseline_overlay_mask, "won"].sum())
    adjusted_overlay_wins = int(replay.loc[adjusted_overlay_mask, "won"].sum())
    baseline_false_positives = int((baseline_overlay_mask & replay["won"].eq(0)).sum())
    adjusted_false_positives = int((adjusted_overlay_mask & replay["won"].eq(0)).sum())

    baseline_top1_win_pct = pct(int(baseline_top1["won"].sum()), len(baseline_top1))
    adjusted_top1_win_pct = pct(int(adjusted_top1["won"].sum()), len(adjusted_top1))
    baseline_top3_capture = pct(int((winners["baseline_price_rank_v1"] <= 3).sum()), len(winners))
    adjusted_top3_capture = pct(int((winners["brc_adjusted_price_rank_v1"] <= 3).sum()), len(winners))
    baseline_top5_capture = pct(int((winners["baseline_price_rank_v1"] <= 5).sum()), len(winners))
    adjusted_top5_capture = pct(int((winners["brc_adjusted_price_rank_v1"] <= 5).sum()), len(winners))

    top1_delta = round(adjusted_top1_win_pct - baseline_top1_win_pct, 2)
    top3_delta = round(adjusted_top3_capture - baseline_top3_capture, 2)
    top5_delta = round(adjusted_top5_capture - baseline_top5_capture, 2)
    overlay_quality_delta = round(
        pct(adjusted_overlay_wins, adjusted_overlay_rows)
        - pct(baseline_overlay_wins, baseline_overlay_rows),
        2,
    )
    false_positive_rate_delta = round(
        pct(adjusted_false_positives, adjusted_overlay_rows)
        - pct(baseline_false_positives, baseline_overlay_rows),
        2,
    )

    if (
        top1_delta >= 0
        and top3_delta >= 0
        and top5_delta >= 0
        and overlay_quality_delta > 0
        and false_positive_rate_delta <= 0
    ):
        verdict = "BARRIER_RAIL_CONDITION_V8_CANDIDATE_PASSES_REPLAY_GATE"
        v8_candidate = "YES"
    elif (
        top1_delta >= 0
        and top3_delta >= 0
        and top5_delta >= 0
        and overlay_quality_delta >= 0
    ):
        verdict = "BARRIER_RAIL_CONDITION_NEUTRAL_SAFE_CANDIDATE"
        v8_candidate = "MAYBE"
    else:
        verdict = "BARRIER_RAIL_CONDITION_NOT_READY_FOR_V8"
        v8_candidate = "NO"

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {
            "metric": "baseline_definition",
            "value": "edgeiq_fair_price_replay_v1.csv used as the historical fair-price baseline proxy.",
        },
        {"metric": "rows", "value": int(len(replay))},
        {"metric": "races", "value": int(replay["race_key"].nunique())},
        {"metric": "barrier_rail_condition_rows_matched", "value": int(replay["barrier_rail_condition_band_v1"].notna().sum())},
        {"metric": "barrier_rail_condition_match_pct", "value": pct(int(replay["barrier_rail_condition_band_v1"].notna().sum()), len(replay))},
        {"metric": "baseline_top1_win_pct", "value": baseline_top1_win_pct},
        {"metric": "brc_adjusted_top1_win_pct", "value": adjusted_top1_win_pct},
        {"metric": "top1_win_pct_delta_pts", "value": top1_delta},
        {"metric": "baseline_winner_top3_capture_pct", "value": baseline_top3_capture},
        {"metric": "brc_adjusted_winner_top3_capture_pct", "value": adjusted_top3_capture},
        {"metric": "winner_top3_capture_delta_pts", "value": top3_delta},
        {"metric": "baseline_winner_top5_capture_pct", "value": baseline_top5_capture},
        {"metric": "brc_adjusted_winner_top5_capture_pct", "value": adjusted_top5_capture},
        {"metric": "winner_top5_capture_delta_pts", "value": top5_delta},
        {"metric": "baseline_positive_overlay_rows", "value": baseline_overlay_rows},
        {"metric": "brc_adjusted_positive_overlay_rows", "value": adjusted_overlay_rows},
        {"metric": "baseline_overlay_quality_win_pct", "value": pct(baseline_overlay_wins, baseline_overlay_rows)},
        {"metric": "brc_adjusted_overlay_quality_win_pct", "value": pct(adjusted_overlay_wins, adjusted_overlay_rows)},
        {"metric": "overlay_quality_delta_pts", "value": overlay_quality_delta},
        {"metric": "baseline_false_positive_rows", "value": baseline_false_positives},
        {"metric": "brc_adjusted_false_positive_rows", "value": adjusted_false_positives},
        {"metric": "baseline_false_positive_rate_pct", "value": pct(baseline_false_positives, baseline_overlay_rows)},
        {"metric": "brc_adjusted_false_positive_rate_pct", "value": pct(adjusted_false_positives, adjusted_overlay_rows)},
        {"metric": "false_positive_rate_delta_pts", "value": false_positive_rate_delta},
        {"metric": "overlay_rows_added_by_brc", "value": int(replay["overlay_added_by_brc_v1"].sum())},
        {"metric": "overlay_rows_removed_by_brc", "value": int(replay["overlay_removed_by_brc_v1"].sum())},
        {
            "metric": "added_overlay_rows_win_pct",
            "value": pct(
                int(replay.loc[replay["overlay_added_by_brc_v1"], "won"].sum()),
                int(replay["overlay_added_by_brc_v1"].sum()),
            ),
        },
        {
            "metric": "removed_overlay_rows_win_pct",
            "value": pct(
                int(replay.loc[replay["overlay_removed_by_brc_v1"], "won"].sum()),
                int(replay["overlay_removed_by_brc_v1"].sum()),
            ),
        },
        {"metric": "price_rank_changed_rows", "value": int(replay["price_rank_changed_flag_v1"].sum())},
        {"metric": "top1_changed_races", "value": int(top1_compare["top1_changed_race_v1"].sum())},
        {"metric": "verdict", "value": verdict},
        {"metric": "fair_price_v8_candidate", "value": v8_candidate},
        {
            "metric": "important_note",
            "value": "Replay only. No live pricing change, no execution change, no staking change.",
        },
    ]

    by_band_rows = []
    for band, group in replay.groupby("barrier_rail_condition_band_v1", dropna=False):
        band_name = "UNKNOWN" if pd.isna(band) else str(band)
        baseline_pos = group["baseline_positive_overlay_flag_v1"]
        adjusted_pos = group["brc_adjusted_positive_overlay_flag_v1"]
        by_band_rows.append(
            {
                "barrier_rail_condition_band_v1": band_name,
                "adjustment_pct_v1": ADJUSTMENT_PCT.get(band_name, 0.0),
                "runners": int(len(group)),
                "wins": int(group["won"].sum()),
                "win_pct": pct(int(group["won"].sum()), len(group)),
                "avg_baseline_fair_price_v1": round(float(group["baseline_fair_price_v1"].mean()), 3),
                "avg_brc_adjusted_fair_price_v1": round(float(group["brc_adjusted_fair_price_v1"].mean()), 3),
                "avg_price_delta_v1": round(float(group["brc_fair_price_delta_v1"].mean()), 4),
                "baseline_positive_overlay_rows": int(baseline_pos.sum()),
                "brc_adjusted_positive_overlay_rows": int(adjusted_pos.sum()),
                "baseline_overlay_win_pct": pct(int(group.loc[baseline_pos, "won"].sum()), int(baseline_pos.sum())),
                "brc_adjusted_overlay_win_pct": pct(int(group.loc[adjusted_pos, "won"].sum()), int(adjusted_pos.sum())),
                "baseline_false_positive_rate_pct": pct(
                    int((baseline_pos & group["won"].eq(0)).sum()),
                    int(baseline_pos.sum()),
                ),
                "brc_adjusted_false_positive_rate_pct": pct(
                    int((adjusted_pos & group["won"].eq(0)).sum()),
                    int(adjusted_pos.sum()),
                ),
            }
        )

    detail_columns = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_name_key",
        "runner_rank",
        "runner_score",
        "finish_position",
        "won",
        "barrier_num",
        "barrier_bucket",
        "rail_bucket",
        "condition_group",
        "barrier_rail_condition_lift_pts",
        "barrier_rail_condition_score_v1",
        "barrier_rail_condition_band_v1",
        "barrier_rail_condition_adjustment_pct_v1",
        "baseline_prob_v1",
        "baseline_fair_price_v1",
        "baseline_price_rank_v1",
        "brc_adjusted_prob_v1",
        "brc_adjusted_fair_price_v1",
        "brc_adjusted_price_rank_v1",
        "brc_prob_delta_v1",
        "brc_fair_price_delta_v1",
        "price_rank_changed_flag_v1",
        "market_proxy_fair_odds_v1",
        "baseline_overlay_pct_v1",
        "baseline_positive_overlay_flag_v1",
        "baseline_overlay_truth_v1",
        "brc_adjusted_overlay_pct_v1",
        "brc_adjusted_positive_overlay_flag_v1",
        "brc_adjusted_overlay_truth_v1",
        "overlay_added_by_brc_v1",
        "overlay_removed_by_brc_v1",
    ]

    replay[detail_columns].to_csv(OUT_MAIN, index=False)
    pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY, index=False)
    pd.DataFrame(by_band_rows).sort_values(["adjustment_pct_v1", "runners"], ascending=[False, False]).to_csv(
        OUT_BY_BAND,
        index=False,
    )
    threshold_rows(replay, "baseline", "brc_adjusted").to_csv(OUT_BY_THRESHOLD, index=False)

    print("[BARRIER_RAIL_CONDITION_PRICING_IMPACT_REPLAY_V1] COMPLETE")
    print(f"rows={len(replay)}")
    print(f"races={int(replay['race_key'].nunique())}")
    print(f"baseline_top1_win_pct={baseline_top1_win_pct}")
    print(f"brc_adjusted_top1_win_pct={adjusted_top1_win_pct}")
    print(f"baseline_overlay_quality_win_pct={pct(baseline_overlay_wins, baseline_overlay_rows)}")
    print(f"brc_adjusted_overlay_quality_win_pct={pct(adjusted_overlay_wins, adjusted_overlay_rows)}")
    print(f"baseline_false_positive_rate_pct={pct(baseline_false_positives, baseline_overlay_rows)}")
    print(f"brc_adjusted_false_positive_rate_pct={pct(adjusted_false_positives, adjusted_overlay_rows)}")
    print(f"top1_changed_races={int(top1_compare['top1_changed_race_v1'].sum())}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT_MAIN}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_BAND}")
    print(f"wrote={OUT_BY_THRESHOLD}")


if __name__ == "__main__":
    main()
