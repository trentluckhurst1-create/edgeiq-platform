from pathlib import Path
import numpy as np
import pandas as pd
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FAIR_REPLAY = DATA / "edgeiq_fair_price_replay_v1.csv"
TJ_RUNNER = DATA / "edgeiq_trainer_jockey_factor_runner_v1.csv"

OUT_DETAIL = DATA / "edgeiq_tj_pricing_impact_replay_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_tj_pricing_impact_replay_v1_summary.csv"
OUT_BY_BAND = DATA / "edgeiq_tj_pricing_impact_replay_v1_by_tj_band.csv"
OUT_BY_THRESHOLD = DATA / "edgeiq_tj_pricing_impact_replay_v1_by_overlay_threshold.csv"

ADJUSTMENTS = {
    "POOR": -1.0,
    "NEGATIVE": -0.5,
    "NEUTRAL": 0.0,
    "LOW_SAMPLE": 0.0,
    "UNKNOWN": 0.0,
    "POSITIVE": 0.5,
    "ELITE": 1.0,
}

THRESHOLDS = [0, 5, 10, 20, 30, 50]


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


def overlay_truth(positive_flag, won_flag):
    if not positive_flag:
        return "NOT_OVERLAY"
    if won_flag == 1:
        return "REAL_OVERLAY"
    return "FAKE_OVERLAY"


def rows_by_threshold(df, prefix):
    rows = []
    for threshold in THRESHOLDS:
        mask = df[f"{prefix}_overlay_pct_v1"] > threshold
        runners = int(mask.sum())
        wins = int(df.loc[mask, "won"].sum()) if runners else 0
        false_positives = int((mask & df["won"].eq(0)).sum()) if runners else 0
        rows.append(
            {
                "pricing_view_v1": prefix.upper(),
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
    return rows


def main():
    for path in [FAIR_REPLAY, TJ_RUNNER]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")

    fair = pd.read_csv(FAIR_REPLAY, low_memory=False)
    tj = pd.read_csv(TJ_RUNNER, low_memory=False)

    fair["horse_name_key"] = fair["horse"].map(clean_text)
    tj["horse_name_key"] = tj["horse"].map(clean_text)

    tj_small = tj[
        [
            "meeting_date",
            "track",
            "race_no",
            "horse_name_key",
            "field_size",
            "trainer",
            "jockey",
            "trainer_factor_band_v1",
            "jockey_factor_band_v1",
            "combo_factor_band_v1",
            "trainer_jockey_blend_score_v1",
            "trainer_jockey_blend_band_v1",
        ]
    ].copy()

    replay = fair.merge(
        tj_small,
        on=["meeting_date", "track", "race_no", "horse_name_key"],
        how="left",
    )

    replay["runner_rank"] = num(replay["runner_rank"])
    replay["runner_score"] = num(replay["runner_score"])
    replay["finish_position"] = num(replay["finish_position"])
    replay["won"] = num(replay["won"]).fillna(0).astype(int)
    replay["fair_prob_replay_v1"] = num(replay["fair_prob_replay_v1"])
    replay["fair_price_replay_v1"] = num(replay["fair_price_replay_v1"])
    replay["field_size"] = num(replay["field_size"])
    replay["trainer_jockey_blend_score_v1"] = num(replay["trainer_jockey_blend_score_v1"])

    replay["trainer_jockey_blend_band_v1"] = (
        replay["trainer_jockey_blend_band_v1"].fillna("UNKNOWN").astype(str).str.upper()
    )
    replay["tj_probability_adjustment_pct_v1"] = (
        replay["trainer_jockey_blend_band_v1"].map(ADJUSTMENTS).fillna(0.0)
    )
    replay["tj_probability_multiplier_v1"] = 1.0 + (
        replay["tj_probability_adjustment_pct_v1"] / 100.0
    )
    replay["tj_adjustment_reason_v1"] = (
        "TJ_BLEND_BAND:" + replay["trainer_jockey_blend_band_v1"]
        + " => "
        + replay["tj_probability_adjustment_pct_v1"].map(lambda v: f"{v:+.1f}%")
    )

    replay["baseline_prob_v1"] = replay["fair_prob_replay_v1"]
    replay["baseline_fair_price_v1"] = replay["fair_price_replay_v1"]
    replay["tj_adjusted_raw_prob_v1"] = (
        replay["baseline_prob_v1"] * replay["tj_probability_multiplier_v1"]
    )
    replay["tj_adjusted_prob_v1"] = (
        replay["tj_adjusted_raw_prob_v1"]
        / replay.groupby("race_key")["tj_adjusted_raw_prob_v1"].transform("sum")
    )
    replay["tj_adjusted_fair_price_v1"] = 1.0 / replay["tj_adjusted_prob_v1"]
    replay["tj_fair_price_delta_v1"] = (
        replay["tj_adjusted_fair_price_v1"] - replay["baseline_fair_price_v1"]
    ).round(4)
    replay["tj_prob_delta_v1"] = (
        replay["tj_adjusted_prob_v1"] - replay["baseline_prob_v1"]
    ).round(6)

    replay = replay.sort_values(
        ["race_key", "baseline_prob_v1", "horse_name_key"],
        ascending=[True, False, True],
    ).copy()
    replay["baseline_price_rank_v1"] = replay.groupby("race_key").cumcount() + 1

    replay = replay.sort_values(
        ["race_key", "tj_adjusted_prob_v1", "horse_name_key"],
        ascending=[True, False, True],
    ).copy()
    replay["tj_adjusted_price_rank_v1"] = replay.groupby("race_key").cumcount() + 1
    replay["price_rank_changed_flag_v1"] = (
        replay["baseline_price_rank_v1"] != replay["tj_adjusted_price_rank_v1"]
    )

    replay["market_proxy_probability_v1"] = np.where(
        replay["field_size"].gt(0), 1.0 / replay["field_size"], np.nan
    )
    replay["market_proxy_fair_odds_v1"] = replay["field_size"]

    replay["baseline_overlay_pct_v1"] = (
        (replay["market_proxy_fair_odds_v1"] / replay["baseline_fair_price_v1"]) - 1.0
    ) * 100.0
    replay["tj_adjusted_overlay_pct_v1"] = (
        (replay["market_proxy_fair_odds_v1"] / replay["tj_adjusted_fair_price_v1"]) - 1.0
    ) * 100.0

    replay["baseline_positive_overlay_flag_v1"] = replay["baseline_overlay_pct_v1"] > 0
    replay["tj_adjusted_positive_overlay_flag_v1"] = replay["tj_adjusted_overlay_pct_v1"] > 0

    replay["baseline_overlay_truth_v1"] = [
        overlay_truth(pos, won)
        for pos, won in zip(
            replay["baseline_positive_overlay_flag_v1"],
            replay["won"],
        )
    ]
    replay["tj_adjusted_overlay_truth_v1"] = [
        overlay_truth(pos, won)
        for pos, won in zip(
            replay["tj_adjusted_positive_overlay_flag_v1"],
            replay["won"],
        )
    ]

    replay["overlay_added_by_tj_v1"] = (
        ~replay["baseline_positive_overlay_flag_v1"]
        & replay["tj_adjusted_positive_overlay_flag_v1"]
    )
    replay["overlay_removed_by_tj_v1"] = (
        replay["baseline_positive_overlay_flag_v1"]
        & ~replay["tj_adjusted_positive_overlay_flag_v1"]
    )

    races = int(replay["race_key"].nunique())
    matched_rows = int(replay["trainer_jockey_blend_band_v1"].notna().sum())

    baseline_top1 = replay[replay["baseline_price_rank_v1"] == 1].copy()
    adjusted_top1 = replay[replay["tj_adjusted_price_rank_v1"] == 1].copy()
    winners = replay[replay["won"] == 1].copy()

    top1_compare = baseline_top1[
        ["race_key", "horse", "won", "trainer_jockey_blend_band_v1", "baseline_prob_v1"]
    ].rename(
        columns={
            "horse": "baseline_top1_horse_v1",
            "won": "baseline_top1_won_v1",
            "trainer_jockey_blend_band_v1": "baseline_top1_tj_band_v1",
            "baseline_prob_v1": "baseline_top1_prob_v1",
        }
    ).merge(
        adjusted_top1[
            ["race_key", "horse", "won", "trainer_jockey_blend_band_v1", "tj_adjusted_prob_v1"]
        ].rename(
            columns={
                "horse": "tj_adjusted_top1_horse_v1",
                "won": "tj_adjusted_top1_won_v1",
                "trainer_jockey_blend_band_v1": "tj_adjusted_top1_tj_band_v1",
                "tj_adjusted_prob_v1": "tj_adjusted_top1_prob_v1",
            }
        ),
        on="race_key",
        how="inner",
    )
    top1_compare["top1_changed_race_v1"] = (
        top1_compare["baseline_top1_horse_v1"] != top1_compare["tj_adjusted_top1_horse_v1"]
    )

    baseline_overlay_mask = replay["baseline_positive_overlay_flag_v1"]
    adjusted_overlay_mask = replay["tj_adjusted_positive_overlay_flag_v1"]

    baseline_overlay_rows = int(baseline_overlay_mask.sum())
    adjusted_overlay_rows = int(adjusted_overlay_mask.sum())
    baseline_overlay_wins = int(replay.loc[baseline_overlay_mask, "won"].sum())
    adjusted_overlay_wins = int(replay.loc[adjusted_overlay_mask, "won"].sum())
    baseline_false_positives = int((baseline_overlay_mask & replay["won"].eq(0)).sum())
    adjusted_false_positives = int((adjusted_overlay_mask & replay["won"].eq(0)).sum())

    baseline_top1_win_pct = pct(int(baseline_top1["won"].sum()), len(baseline_top1))
    adjusted_top1_win_pct = pct(int(adjusted_top1["won"].sum()), len(adjusted_top1))
    baseline_top3_capture = pct(int((winners["baseline_price_rank_v1"] <= 3).sum()), len(winners))
    adjusted_top3_capture = pct(int((winners["tj_adjusted_price_rank_v1"] <= 3).sum()), len(winners))
    baseline_top5_capture = pct(int((winners["baseline_price_rank_v1"] <= 5).sum()), len(winners))
    adjusted_top5_capture = pct(int((winners["tj_adjusted_price_rank_v1"] <= 5).sum()), len(winners))

    top1_delta = round(adjusted_top1_win_pct - baseline_top1_win_pct, 2)
    top3_delta = round(adjusted_top3_capture - baseline_top3_capture, 2)
    top5_delta = round(adjusted_top5_capture - baseline_top5_capture, 2)
    overlay_win_delta = round(
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
        and overlay_win_delta > 0
        and false_positive_rate_delta < 0
    ):
        verdict = "TJ_SMALL_CONTROLLED_IMPROVEMENT"
        fair_price_v7_candidate = "YES"
    elif (
        top1_delta >= 0
        and overlay_win_delta >= 0
        and false_positive_rate_delta <= 0
    ):
        verdict = "TJ_NEUTRAL_SAFE_CANDIDATE"
        fair_price_v7_candidate = "MAYBE"
    else:
        verdict = "TJ_NOT_READY_FOR_FAIR_PRICE_V7"
        fair_price_v7_candidate = "NO"

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "audit_name", "value": "TJ_PRICING_IMPACT_REPLAY_V1"},
        {"metric": "rows", "value": int(len(replay))},
        {"metric": "races", "value": races},
        {"metric": "tj_rows_matched", "value": matched_rows},
        {"metric": "tj_match_pct", "value": pct(matched_rows, len(replay))},
        {"metric": "baseline_top1_win_pct", "value": baseline_top1_win_pct},
        {"metric": "tj_adjusted_top1_win_pct", "value": adjusted_top1_win_pct},
        {"metric": "top1_win_pct_delta_pts", "value": top1_delta},
        {"metric": "baseline_winner_top3_capture_pct", "value": baseline_top3_capture},
        {"metric": "tj_adjusted_winner_top3_capture_pct", "value": adjusted_top3_capture},
        {"metric": "winner_top3_capture_delta_pts", "value": top3_delta},
        {"metric": "baseline_winner_top5_capture_pct", "value": baseline_top5_capture},
        {"metric": "tj_adjusted_winner_top5_capture_pct", "value": adjusted_top5_capture},
        {"metric": "winner_top5_capture_delta_pts", "value": top5_delta},
        {"metric": "baseline_positive_overlay_rows", "value": baseline_overlay_rows},
        {"metric": "tj_adjusted_positive_overlay_rows", "value": adjusted_overlay_rows},
        {
            "metric": "baseline_overlay_quality_win_pct",
            "value": pct(baseline_overlay_wins, baseline_overlay_rows),
        },
        {
            "metric": "tj_adjusted_overlay_quality_win_pct",
            "value": pct(adjusted_overlay_wins, adjusted_overlay_rows),
        },
        {"metric": "overlay_quality_win_pct_delta_pts", "value": overlay_win_delta},
        {"metric": "baseline_false_positive_rows", "value": baseline_false_positives},
        {"metric": "tj_adjusted_false_positive_rows", "value": adjusted_false_positives},
        {
            "metric": "baseline_false_positive_rate_pct",
            "value": pct(baseline_false_positives, baseline_overlay_rows),
        },
        {
            "metric": "tj_adjusted_false_positive_rate_pct",
            "value": pct(adjusted_false_positives, adjusted_overlay_rows),
        },
        {"metric": "false_positive_rate_delta_pts", "value": false_positive_rate_delta},
        {
            "metric": "overlay_rows_added_by_tj",
            "value": int(replay["overlay_added_by_tj_v1"].sum()),
        },
        {
            "metric": "overlay_rows_removed_by_tj",
            "value": int(replay["overlay_removed_by_tj_v1"].sum()),
        },
        {
            "metric": "added_overlay_rows_win_pct",
            "value": pct(
                int(replay.loc[replay["overlay_added_by_tj_v1"], "won"].sum()),
                int(replay["overlay_added_by_tj_v1"].sum()),
            ),
        },
        {
            "metric": "removed_overlay_rows_win_pct",
            "value": pct(
                int(replay.loc[replay["overlay_removed_by_tj_v1"], "won"].sum()),
                int(replay["overlay_removed_by_tj_v1"].sum()),
            ),
        },
        {
            "metric": "price_rank_changed_rows",
            "value": int(replay["price_rank_changed_flag_v1"].sum()),
        },
        {
            "metric": "top1_changed_races",
            "value": int(top1_compare["top1_changed_race_v1"].sum()),
        },
        {
            "metric": "changed_top1_races_new_top1_won",
            "value": int(
                top1_compare.loc[top1_compare["top1_changed_race_v1"], "tj_adjusted_top1_won_v1"].sum()
            ),
        },
        {
            "metric": "changed_top1_races_old_top1_won",
            "value": int(
                top1_compare.loc[top1_compare["top1_changed_race_v1"], "baseline_top1_won_v1"].sum()
            ),
        },
        {"metric": "verdict", "value": verdict},
        {"metric": "fair_price_v7_controlled_candidate", "value": fair_price_v7_candidate},
        {
            "metric": "important_note",
            "value": "Replay only. No live pricing change, no execution change, no staking change.",
        },
    ]

    by_band_rows = []
    for band, group in replay.groupby("trainer_jockey_blend_band_v1", dropna=False):
        band_name = "UNKNOWN" if pd.isna(band) else str(band)
        base_pos = group["baseline_positive_overlay_flag_v1"]
        adj_pos = group["tj_adjusted_positive_overlay_flag_v1"]
        by_band_rows.append(
            {
                "trainer_jockey_blend_band_v1": band_name,
                "adjustment_pct_v1": ADJUSTMENTS.get(band_name, 0.0),
                "runners": int(len(group)),
                "wins": int(group["won"].sum()),
                "win_pct": pct(int(group["won"].sum()), len(group)),
                "avg_baseline_fair_price_v1": round(float(group["baseline_fair_price_v1"].mean()), 3),
                "avg_tj_adjusted_fair_price_v1": round(float(group["tj_adjusted_fair_price_v1"].mean()), 3),
                "avg_price_delta_v1": round(float(group["tj_fair_price_delta_v1"].mean()), 4),
                "baseline_positive_overlay_rows": int(base_pos.sum()),
                "tj_adjusted_positive_overlay_rows": int(adj_pos.sum()),
                "baseline_overlay_win_pct": pct(int(group.loc[base_pos, "won"].sum()), int(base_pos.sum())),
                "tj_adjusted_overlay_win_pct": pct(int(group.loc[adj_pos, "won"].sum()), int(adj_pos.sum())),
                "baseline_false_positive_rate_pct": pct(
                    int((base_pos & group["won"].eq(0)).sum()), int(base_pos.sum())
                ),
                "tj_adjusted_false_positive_rate_pct": pct(
                    int((adj_pos & group["won"].eq(0)).sum()), int(adj_pos.sum())
                ),
            }
        )

    threshold_rows = rows_by_threshold(replay, "baseline")
    threshold_rows.extend(rows_by_threshold(replay, "tj_adjusted"))
    threshold_df = pd.DataFrame(threshold_rows)

    detail_cols = [
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
        "field_size",
        "trainer",
        "jockey",
        "trainer_factor_band_v1",
        "jockey_factor_band_v1",
        "combo_factor_band_v1",
        "trainer_jockey_blend_score_v1",
        "trainer_jockey_blend_band_v1",
        "tj_probability_adjustment_pct_v1",
        "tj_probability_multiplier_v1",
        "tj_adjustment_reason_v1",
        "baseline_prob_v1",
        "baseline_fair_price_v1",
        "baseline_price_rank_v1",
        "tj_adjusted_prob_v1",
        "tj_adjusted_fair_price_v1",
        "tj_adjusted_price_rank_v1",
        "tj_prob_delta_v1",
        "tj_fair_price_delta_v1",
        "price_rank_changed_flag_v1",
        "market_proxy_probability_v1",
        "market_proxy_fair_odds_v1",
        "baseline_overlay_pct_v1",
        "baseline_positive_overlay_flag_v1",
        "baseline_overlay_truth_v1",
        "tj_adjusted_overlay_pct_v1",
        "tj_adjusted_positive_overlay_flag_v1",
        "tj_adjusted_overlay_truth_v1",
        "overlay_added_by_tj_v1",
        "overlay_removed_by_tj_v1",
    ]

    replay[detail_cols].to_csv(OUT_DETAIL, index=False)
    pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY, index=False)
    pd.DataFrame(by_band_rows).sort_values(
        ["adjustment_pct_v1", "runners"], ascending=[False, False]
    ).to_csv(OUT_BY_BAND, index=False)
    threshold_df.to_csv(OUT_BY_THRESHOLD, index=False)

    print("[TJ_PRICING_IMPACT_REPLAY_V1] COMPLETE")
    print(f"rows={len(replay)}")
    print(f"races={races}")
    print(f"baseline_top1_win_pct={baseline_top1_win_pct}")
    print(f"tj_adjusted_top1_win_pct={adjusted_top1_win_pct}")
    print(f"baseline_overlay_quality_win_pct={pct(baseline_overlay_wins, baseline_overlay_rows)}")
    print(f"tj_adjusted_overlay_quality_win_pct={pct(adjusted_overlay_wins, adjusted_overlay_rows)}")
    print(f"baseline_false_positive_rate_pct={pct(baseline_false_positives, baseline_overlay_rows)}")
    print(f"tj_adjusted_false_positive_rate_pct={pct(adjusted_false_positives, adjusted_overlay_rows)}")
    print(f"top1_changed_races={int(top1_compare['top1_changed_race_v1'].sum())}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_BAND}")
    print(f"wrote={OUT_BY_THRESHOLD}")


if __name__ == "__main__":
    main()
