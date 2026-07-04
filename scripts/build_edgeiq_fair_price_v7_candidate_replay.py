from pathlib import Path
import numpy as np
import pandas as pd
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASELINE_REPLAY = DATA / "edgeiq_fair_price_replay_v1.csv"
TJ_RUNNER = DATA / "edgeiq_trainer_jockey_factor_runner_v1.csv"

OUT_MAIN = DATA / "edgeiq_fair_price_v7_candidate_replay.csv"
OUT_SUMMARY = DATA / "edgeiq_fair_price_v7_candidate_replay_summary.csv"
OUT_BY_THRESHOLD = DATA / "edgeiq_fair_price_v7_candidate_replay_by_overlay_threshold.csv"
OUT_TOP1_CHANGES = DATA / "edgeiq_fair_price_v7_candidate_replay_top1_changes.csv"

TJ_ADJUSTMENT_PCT = {
    "POOR": -1.0,
    "NEGATIVE": -0.5,
    "NEUTRAL": 0.0,
    "LOW_SAMPLE": 0.0,
    "UNKNOWN": 0.0,
    "POSITIVE": 0.5,
    "ELITE": 1.0,
}

TJ_ACTIVE_VERDICTS = {"COMPLETE", "TRAINER_JOCKEY_ONLY"}
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


def build_tj_verdict(df):
    trainer_present = df["trainer_factor_band_v1"].fillna("").astype(str).str.strip() != ""
    jockey_present = df["jockey_factor_band_v1"].fillna("").astype(str).str.strip() != ""
    combo_present = df["combo_factor_band_v1"].fillna("").astype(str).str.strip() != ""

    verdict = np.where(
        trainer_present & jockey_present & combo_present,
        "COMPLETE",
        np.where(
            trainer_present & jockey_present,
            "TRAINER_JOCKEY_ONLY",
            np.where(trainer_present | jockey_present, "PARTIAL", "UNMATCHED"),
        ),
    )
    return pd.Series(verdict, index=df.index)


def threshold_rows(df, baseline_prefix, candidate_prefix):
    rows = []
    for threshold in OVERLAY_THRESHOLDS:
        for prefix, label in [(baseline_prefix, "V6_BASELINE_PROXY"), (candidate_prefix, "V7_TJ_CANDIDATE")]:
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
    for path in [BASELINE_REPLAY, TJ_RUNNER]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")

    baseline = pd.read_csv(BASELINE_REPLAY, low_memory=False)
    tj = pd.read_csv(TJ_RUNNER, low_memory=False)

    baseline["horse_name_key"] = baseline["horse"].map(clean_text)
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

    replay = baseline.merge(
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

    replay["trainer_factor_band_v1"] = replay["trainer_factor_band_v1"].fillna("").astype(str).str.upper()
    replay["jockey_factor_band_v1"] = replay["jockey_factor_band_v1"].fillna("").astype(str).str.upper()
    replay["combo_factor_band_v1"] = replay["combo_factor_band_v1"].fillna("").astype(str).str.upper()
    replay["trainer_jockey_blend_band_v1"] = (
        replay["trainer_jockey_blend_band_v1"].fillna("UNKNOWN").astype(str).str.upper()
    )
    replay["tj_factor_verdict_v1"] = build_tj_verdict(replay)
    replay["tj_adjustment_active_v1"] = replay["tj_factor_verdict_v1"].isin(TJ_ACTIVE_VERDICTS)

    replay["v6_baseline_prob_v1"] = replay["fair_prob_replay_v1"]
    replay["v6_baseline_fair_price_v1"] = replay["fair_price_replay_v1"]
    replay["tj_adjustment_pct_v1"] = np.where(
        replay["tj_adjustment_active_v1"],
        replay["trainer_jockey_blend_band_v1"].map(TJ_ADJUSTMENT_PCT).fillna(0.0),
        0.0,
    )
    replay["tj_probability_multiplier_v1"] = 1.0 + (replay["tj_adjustment_pct_v1"] / 100.0)
    replay["v7_candidate_raw_prob_v1"] = replay["v6_baseline_prob_v1"] * replay["tj_probability_multiplier_v1"]
    replay["v7_candidate_prob_v1"] = (
        replay["v7_candidate_raw_prob_v1"]
        / replay.groupby("race_key")["v7_candidate_raw_prob_v1"].transform("sum")
    )
    replay["v7_candidate_fair_price_v1"] = 1.0 / replay["v7_candidate_prob_v1"]
    replay["v7_candidate_prob_delta_v1"] = (
        replay["v7_candidate_prob_v1"] - replay["v6_baseline_prob_v1"]
    ).round(6)
    replay["v7_candidate_fair_price_delta_v1"] = (
        replay["v7_candidate_fair_price_v1"] - replay["v6_baseline_fair_price_v1"]
    ).round(4)

    replay = replay.sort_values(
        ["race_key", "v6_baseline_prob_v1", "horse_name_key"],
        ascending=[True, False, True],
    ).copy()
    replay["v6_baseline_rank_v1"] = replay.groupby("race_key").cumcount() + 1

    replay = replay.sort_values(
        ["race_key", "v7_candidate_prob_v1", "horse_name_key"],
        ascending=[True, False, True],
    ).copy()
    replay["v7_candidate_rank_v1"] = replay.groupby("race_key").cumcount() + 1
    replay["rank_changed_flag_v1"] = replay["v6_baseline_rank_v1"] != replay["v7_candidate_rank_v1"]

    replay["market_proxy_probability_v1"] = np.where(
        replay["field_size"].gt(0), 1.0 / replay["field_size"], np.nan
    )
    replay["market_proxy_fair_odds_v1"] = replay["field_size"]

    replay["v6_baseline_overlay_pct_v1"] = (
        (replay["market_proxy_fair_odds_v1"] / replay["v6_baseline_fair_price_v1"]) - 1.0
    ) * 100.0
    replay["v7_candidate_overlay_pct_v1"] = (
        (replay["market_proxy_fair_odds_v1"] / replay["v7_candidate_fair_price_v1"]) - 1.0
    ) * 100.0
    replay["v6_baseline_positive_overlay_flag_v1"] = replay["v6_baseline_overlay_pct_v1"] > 0
    replay["v7_candidate_positive_overlay_flag_v1"] = replay["v7_candidate_overlay_pct_v1"] > 0

    replay["v6_baseline_overlay_truth_v1"] = [
        overlay_truth(flag, won)
        for flag, won in zip(replay["v6_baseline_positive_overlay_flag_v1"], replay["won"])
    ]
    replay["v7_candidate_overlay_truth_v1"] = [
        overlay_truth(flag, won)
        for flag, won in zip(replay["v7_candidate_positive_overlay_flag_v1"], replay["won"])
    ]
    replay["overlay_added_by_v7_v1"] = (
        ~replay["v6_baseline_positive_overlay_flag_v1"]
        & replay["v7_candidate_positive_overlay_flag_v1"]
    )
    replay["overlay_removed_by_v7_v1"] = (
        replay["v6_baseline_positive_overlay_flag_v1"]
        & ~replay["v7_candidate_positive_overlay_flag_v1"]
    )

    winners = replay[replay["won"] == 1].copy()
    v6_top1 = replay[replay["v6_baseline_rank_v1"] == 1].copy()
    v7_top1 = replay[replay["v7_candidate_rank_v1"] == 1].copy()

    top1_compare = v6_top1[
        ["race_key", "horse", "won", "trainer_jockey_blend_band_v1", "v6_baseline_prob_v1"]
    ].rename(
        columns={
            "horse": "v6_top1_horse_v1",
            "won": "v6_top1_won_v1",
            "trainer_jockey_blend_band_v1": "v6_top1_tj_band_v1",
            "v6_baseline_prob_v1": "v6_top1_prob_v1",
        }
    ).merge(
        v7_top1[
            ["race_key", "horse", "won", "trainer_jockey_blend_band_v1", "v7_candidate_prob_v1"]
        ].rename(
            columns={
                "horse": "v7_top1_horse_v1",
                "won": "v7_top1_won_v1",
                "trainer_jockey_blend_band_v1": "v7_top1_tj_band_v1",
                "v7_candidate_prob_v1": "v7_top1_prob_v1",
            }
        ),
        on="race_key",
        how="inner",
    )
    top1_compare["top1_changed_race_v1"] = top1_compare["v6_top1_horse_v1"] != top1_compare["v7_top1_horse_v1"]

    v6_overlay = replay["v6_baseline_positive_overlay_flag_v1"]
    v7_overlay = replay["v7_candidate_positive_overlay_flag_v1"]

    v6_overlay_rows = int(v6_overlay.sum())
    v7_overlay_rows = int(v7_overlay.sum())
    v6_overlay_wins = int(replay.loc[v6_overlay, "won"].sum())
    v7_overlay_wins = int(replay.loc[v7_overlay, "won"].sum())
    v6_false_positives = int((v6_overlay & replay["won"].eq(0)).sum())
    v7_false_positives = int((v7_overlay & replay["won"].eq(0)).sum())

    v6_top1_win_pct = pct(int(v6_top1["won"].sum()), len(v6_top1))
    v7_top1_win_pct = pct(int(v7_top1["won"].sum()), len(v7_top1))
    v6_top3_capture = pct(int((winners["v6_baseline_rank_v1"] <= 3).sum()), len(winners))
    v7_top3_capture = pct(int((winners["v7_candidate_rank_v1"] <= 3).sum()), len(winners))
    v6_top5_capture = pct(int((winners["v6_baseline_rank_v1"] <= 5).sum()), len(winners))
    v7_top5_capture = pct(int((winners["v7_candidate_rank_v1"] <= 5).sum()), len(winners))

    top1_delta = round(v7_top1_win_pct - v6_top1_win_pct, 2)
    top3_delta = round(v7_top3_capture - v6_top3_capture, 2)
    top5_delta = round(v7_top5_capture - v6_top5_capture, 2)
    overlay_quality_delta = round(
        pct(v7_overlay_wins, v7_overlay_rows) - pct(v6_overlay_wins, v6_overlay_rows),
        2,
    )
    false_positive_rate_delta = round(
        pct(v7_false_positives, v7_overlay_rows) - pct(v6_false_positives, v6_overlay_rows),
        2,
    )

    if (
        top1_delta >= 0
        and top3_delta >= 0
        and top5_delta >= 0
        and overlay_quality_delta > 0
        and false_positive_rate_delta <= 0
    ):
        verdict = "V7_CANDIDATE_PASSES_REPLAY_GATE"
        promotion_candidate = "YES"
    elif (
        top1_delta >= 0
        and top3_delta >= 0
        and top5_delta >= 0
        and overlay_quality_delta >= 0
    ):
        verdict = "V7_CANDIDATE_NEUTRAL_SAFE"
        promotion_candidate = "MAYBE"
    else:
        verdict = "V7_CANDIDATE_FAILS_REPLAY_GATE"
        promotion_candidate = "NO"

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "audit_name", "value": "FAIR_PRICE_V7_CANDIDATE_REPLAY"},
        {"metric": "baseline_definition", "value": "edgeiq_fair_price_replay_v1.csv used as historical V6-baseline proxy because no historical fair_price_v6 replay artifact exists in repo."},
        {"metric": "rows", "value": int(len(replay))},
        {"metric": "races", "value": int(replay['race_key'].nunique())},
        {"metric": "tj_rows_matched", "value": int(replay['trainer_jockey_blend_band_v1'].notna().sum())},
        {"metric": "tj_match_pct", "value": pct(int(replay['trainer_jockey_blend_band_v1'].notna().sum()), len(replay))},
        {"metric": "tj_active_complete_rows", "value": int((replay['tj_factor_verdict_v1'] == 'COMPLETE').sum())},
        {"metric": "tj_active_trainer_jockey_only_rows", "value": int((replay['tj_factor_verdict_v1'] == 'TRAINER_JOCKEY_ONLY').sum())},
        {"metric": "v6_top1_win_pct", "value": v6_top1_win_pct},
        {"metric": "v7_top1_win_pct", "value": v7_top1_win_pct},
        {"metric": "top1_win_pct_delta_pts", "value": top1_delta},
        {"metric": "v6_winner_top3_capture_pct", "value": v6_top3_capture},
        {"metric": "v7_winner_top3_capture_pct", "value": v7_top3_capture},
        {"metric": "winner_top3_capture_delta_pts", "value": top3_delta},
        {"metric": "v6_winner_top5_capture_pct", "value": v6_top5_capture},
        {"metric": "v7_winner_top5_capture_pct", "value": v7_top5_capture},
        {"metric": "winner_top5_capture_delta_pts", "value": top5_delta},
        {"metric": "v6_positive_overlay_rows", "value": v6_overlay_rows},
        {"metric": "v7_positive_overlay_rows", "value": v7_overlay_rows},
        {"metric": "v6_overlay_quality_win_pct", "value": pct(v6_overlay_wins, v6_overlay_rows)},
        {"metric": "v7_overlay_quality_win_pct", "value": pct(v7_overlay_wins, v7_overlay_rows)},
        {"metric": "overlay_quality_delta_pts", "value": overlay_quality_delta},
        {"metric": "v6_false_positive_rows", "value": v6_false_positives},
        {"metric": "v7_false_positive_rows", "value": v7_false_positives},
        {"metric": "v6_false_positive_rate_pct", "value": pct(v6_false_positives, v6_overlay_rows)},
        {"metric": "v7_false_positive_rate_pct", "value": pct(v7_false_positives, v7_overlay_rows)},
        {"metric": "false_positive_rate_delta_pts", "value": false_positive_rate_delta},
        {"metric": "overlay_rows_added_by_v7", "value": int(replay["overlay_added_by_v7_v1"].sum())},
        {"metric": "overlay_rows_removed_by_v7", "value": int(replay["overlay_removed_by_v7_v1"].sum())},
        {"metric": "added_overlay_rows_win_pct", "value": pct(int(replay.loc[replay["overlay_added_by_v7_v1"], "won"].sum()), int(replay["overlay_added_by_v7_v1"].sum()))},
        {"metric": "removed_overlay_rows_win_pct", "value": pct(int(replay.loc[replay["overlay_removed_by_v7_v1"], "won"].sum()), int(replay["overlay_removed_by_v7_v1"].sum()))},
        {"metric": "rank_changed_rows", "value": int(replay["rank_changed_flag_v1"].sum())},
        {"metric": "top1_changed_races", "value": int(top1_compare["top1_changed_race_v1"].sum())},
        {"metric": "changed_top1_races_new_top1_won", "value": int(top1_compare.loc[top1_compare["top1_changed_race_v1"], "v7_top1_won_v1"].sum())},
        {"metric": "changed_top1_races_old_top1_won", "value": int(top1_compare.loc[top1_compare["top1_changed_race_v1"], "v6_top1_won_v1"].sum())},
        {"metric": "verdict", "value": verdict},
        {"metric": "promote_later_candidate", "value": promotion_candidate},
        {"metric": "important_note", "value": "Replay only. No live changes, no action change, no stake change, no execution change."},
    ]

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
        "field_size",
        "trainer",
        "jockey",
        "trainer_factor_band_v1",
        "jockey_factor_band_v1",
        "combo_factor_band_v1",
        "trainer_jockey_blend_score_v1",
        "trainer_jockey_blend_band_v1",
        "tj_factor_verdict_v1",
        "tj_adjustment_active_v1",
        "tj_adjustment_pct_v1",
        "v6_baseline_prob_v1",
        "v6_baseline_fair_price_v1",
        "v6_baseline_rank_v1",
        "v7_candidate_prob_v1",
        "v7_candidate_fair_price_v1",
        "v7_candidate_rank_v1",
        "v7_candidate_prob_delta_v1",
        "v7_candidate_fair_price_delta_v1",
        "rank_changed_flag_v1",
        "market_proxy_fair_odds_v1",
        "v6_baseline_overlay_pct_v1",
        "v6_baseline_positive_overlay_flag_v1",
        "v6_baseline_overlay_truth_v1",
        "v7_candidate_overlay_pct_v1",
        "v7_candidate_positive_overlay_flag_v1",
        "v7_candidate_overlay_truth_v1",
        "overlay_added_by_v7_v1",
        "overlay_removed_by_v7_v1",
    ]

    replay[detail_columns].to_csv(OUT_MAIN, index=False)
    pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY, index=False)
    threshold_rows(replay, "v6_baseline", "v7_candidate").to_csv(OUT_BY_THRESHOLD, index=False)
    top1_compare[top1_compare["top1_changed_race_v1"]].to_csv(OUT_TOP1_CHANGES, index=False)

    print("[FAIR_PRICE_V7_CANDIDATE_REPLAY] COMPLETE")
    print(f"rows={len(replay)}")
    print(f"races={int(replay['race_key'].nunique())}")
    print(f"v6_top1_win_pct={v6_top1_win_pct}")
    print(f"v7_top1_win_pct={v7_top1_win_pct}")
    print(f"v6_overlay_quality_win_pct={pct(v6_overlay_wins, v6_overlay_rows)}")
    print(f"v7_overlay_quality_win_pct={pct(v7_overlay_wins, v7_overlay_rows)}")
    print(f"v6_false_positive_rate_pct={pct(v6_false_positives, v6_overlay_rows)}")
    print(f"v7_false_positive_rate_pct={pct(v7_false_positives, v7_overlay_rows)}")
    print(f"top1_changed_races={int(top1_compare['top1_changed_race_v1'].sum())}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT_MAIN}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_THRESHOLD}")
    print(f"wrote={OUT_TOP1_CHANGES}")


if __name__ == "__main__":
    main()
