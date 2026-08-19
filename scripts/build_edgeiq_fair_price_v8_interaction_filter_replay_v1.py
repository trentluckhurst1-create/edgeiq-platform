from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_INTERACTION = DATA / "edgeiq_factor_interaction_audit_v1.csv"
IN_INTERACTION_BY_COMBO = DATA / "edgeiq_factor_interaction_audit_v1_by_combo.csv"
IN_TJ_REPLAY = DATA / "edgeiq_tj_pricing_impact_replay_v1.csv"
IN_BRC_REPLAY = DATA / "edgeiq_barrier_rail_condition_pricing_impact_replay_v1.csv"
IN_FAIR = DATA / "edgeiq_fair_price_replay_v1.csv"
IN_TJ_RUNNER = DATA / "edgeiq_trainer_jockey_factor_runner_v1.csv"
IN_BRC_BIAS = DATA / "edgeiq_barrier_rail_condition_bias_replay_v1.csv"

OUT_MAIN = DATA / "edgeiq_fair_price_v8_interaction_filter_replay_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_fair_price_v8_interaction_filter_replay_v1_summary.csv"
OUT_BY_RULE = DATA / "edgeiq_fair_price_v8_interaction_filter_replay_by_rule_v1.csv"
OUT_BY_THRESHOLD = DATA / "edgeiq_fair_price_v8_interaction_filter_replay_by_overlay_threshold_v1.csv"
OUT_ADDED_REMOVED = DATA / "edgeiq_fair_price_v8_interaction_filter_replay_added_removed_v1.csv"
OUT_JSON = DATA / "edgeiq_fair_price_v8_interaction_filter_replay_v1.json"

RULE_SETS = {
    "RULE_SET_A_TINY": {
        "TJ_POSITIVE + BRC_POSITIVE": 1.0,
        "TJ_POSITIVE + BRC_NEUTRAL": 0.25,
        "TJ_NEUTRAL + BRC_POSITIVE": 0.25,
        "TJ_POSITIVE + BRC_NEGATIVE": -0.25,
        "TJ_NEGATIVE + BRC_POSITIVE": -0.50,
        "TJ_NEGATIVE + BRC_NEUTRAL": -0.50,
        "TJ_NEUTRAL + BRC_NEGATIVE": -0.50,
        "TJ_NEGATIVE + BRC_NEGATIVE": -1.0,
    },
    "RULE_SET_B_SELECTIVE": {
        "TJ_POSITIVE + BRC_POSITIVE": 1.5,
        "TJ_POSITIVE + BRC_NEUTRAL": 0.50,
        "TJ_NEUTRAL + BRC_POSITIVE": 0.50,
        "TJ_POSITIVE + BRC_NEGATIVE": -0.25,
        "TJ_NEGATIVE + BRC_POSITIVE": -0.75,
        "TJ_NEGATIVE + BRC_NEUTRAL": -0.75,
        "TJ_NEUTRAL + BRC_NEGATIVE": -0.75,
        "TJ_NEGATIVE + BRC_NEGATIVE": -1.5,
    },
    "RULE_SET_C_FILTER_HEAVY": {
        "TJ_POSITIVE + BRC_POSITIVE": 2.0,
        "TJ_POSITIVE + BRC_NEUTRAL": 0.50,
        "TJ_NEUTRAL + BRC_POSITIVE": 0.50,
        "TJ_POSITIVE + BRC_NEGATIVE": -0.50,
        "TJ_NEGATIVE + BRC_POSITIVE": -1.0,
        "TJ_NEGATIVE + BRC_NEUTRAL": -1.0,
        "TJ_NEUTRAL + BRC_NEGATIVE": -1.0,
        "TJ_NEGATIVE + BRC_NEGATIVE": -2.0,
    },
}

OVERLAY_THRESHOLDS = [0, 5, 10, 20, 50]


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


def write_json(payload: dict, path: Path) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def pct(numerator, denominator):
    if denominator in (0, None) or pd.isna(denominator):
        return np.nan
    return round(float(numerator) / float(denominator) * 100.0, 2)


def overlay_truth(is_overlay, won):
    if not is_overlay:
        return "NOT_OVERLAY"
    return "REAL_OVERLAY" if int(won) == 1 else "FAKE_OVERLAY"


def add_baseline_price_ranks(base: pd.DataFrame) -> pd.DataFrame:
    ranked = base.sort_values(
        ["race_key", "fair_price_replay_v1", "horse_name_key"],
        ascending=[True, True, True],
    ).copy()
    ranked["baseline_price_rank_v1"] = ranked.groupby("race_key").cumcount() + 1
    return ranked.sort_index()


def load_base() -> pd.DataFrame:
    required = [
        IN_INTERACTION,
        IN_INTERACTION_BY_COMBO,
        IN_TJ_REPLAY,
        IN_BRC_REPLAY,
        IN_FAIR,
    ]
    optional = [IN_TJ_RUNNER, IN_BRC_BIAS]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")
    for path in optional:
        if not path.exists():
            print(f"[WARN] Optional input missing and not required for this replay: {path}")

    base = pd.read_csv(IN_INTERACTION, low_memory=False)
    base["runner_rank"] = pd.to_numeric(base["runner_rank"], errors="coerce")
    base["runner_score"] = pd.to_numeric(base["runner_score"], errors="coerce")
    base["fair_prob_replay_v1"] = pd.to_numeric(base["fair_prob_replay_v1"], errors="coerce")
    base["fair_price_replay_v1"] = pd.to_numeric(base["fair_price_replay_v1"], errors="coerce")
    base["won"] = pd.to_numeric(base["won"], errors="coerce").fillna(0).astype(int)
    base["placed"] = pd.to_numeric(base["placed"], errors="coerce").fillna(0).astype(int)
    base["tj_adjusted_prob_v1"] = pd.to_numeric(base["tj_adjusted_prob_v1"], errors="coerce")
    base["tj_adjusted_fair_price_v1"] = pd.to_numeric(base["tj_adjusted_fair_price_v1"], errors="coerce")
    base["tj_adjusted_price_rank_v1"] = pd.to_numeric(base["tj_adjusted_price_rank_v1"], errors="coerce")
    base["tj_adjusted_overlay_pct_v1"] = pd.to_numeric(base["tj_adjusted_overlay_pct_v1"], errors="coerce")
    base["brc_adjusted_prob_v1"] = pd.to_numeric(base["brc_adjusted_prob_v1"], errors="coerce")
    base["brc_adjusted_fair_price_v1"] = pd.to_numeric(base["brc_adjusted_fair_price_v1"], errors="coerce")
    base["brc_adjusted_price_rank_v1"] = pd.to_numeric(base["brc_adjusted_price_rank_v1"], errors="coerce")
    base["brc_adjusted_overlay_pct_v1"] = pd.to_numeric(base["brc_adjusted_overlay_pct_v1"], errors="coerce")
    base["baseline_overlay_pct_v1"] = pd.to_numeric(base["baseline_overlay_pct_v1"], errors="coerce")
    base["race_size_v1"] = base.groupby("race_key")["horse"].transform("count")
    base["market_proxy_fair_odds_v1"] = base["race_size_v1"]
    base = add_baseline_price_ranks(base)
    return base


def compute_reference_metrics(base: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    winners = base[base["won"] == 1].copy()
    baseline_top1 = base[base["baseline_price_rank_v1"] == 1].copy()
    tj_top1 = base[base["tj_adjusted_price_rank_v1"] == 1].copy()
    brc_top1 = base[base["brc_adjusted_price_rank_v1"] == 1].copy()

    refs = {
        "BASELINE": {
            "top1_win_pct": pct(int(baseline_top1["won"].sum()), len(baseline_top1)),
            "top3_capture_pct": pct(int((winners["baseline_price_rank_v1"] <= 3).sum()), len(winners)),
            "top5_capture_pct": pct(int((winners["baseline_price_rank_v1"] <= 5).sum()), len(winners)),
            "overlay_rows": int(base["baseline_positive_overlay_flag_v1"].sum()),
            "overlay_wins": int(base.loc[base["baseline_positive_overlay_flag_v1"], "won"].sum()),
            "false_positive_rows": int((base["baseline_positive_overlay_flag_v1"] & base["won"].eq(0)).sum()),
        },
        "TJ_ADJUSTED": {
            "top1_win_pct": pct(int(tj_top1["won"].sum()), len(tj_top1)),
            "top3_capture_pct": pct(int((winners["tj_adjusted_price_rank_v1"] <= 3).sum()), len(winners)),
            "top5_capture_pct": pct(int((winners["tj_adjusted_price_rank_v1"] <= 5).sum()), len(winners)),
            "overlay_rows": int(base["tj_adjusted_positive_overlay_flag_v1"].sum()),
            "overlay_wins": int(base.loc[base["tj_adjusted_positive_overlay_flag_v1"], "won"].sum()),
            "false_positive_rows": int((base["tj_adjusted_positive_overlay_flag_v1"] & base["won"].eq(0)).sum()),
        },
        "BRC_ADJUSTED": {
            "top1_win_pct": pct(int(brc_top1["won"].sum()), len(brc_top1)),
            "top3_capture_pct": pct(int((winners["brc_adjusted_price_rank_v1"] <= 3).sum()), len(winners)),
            "top5_capture_pct": pct(int((winners["brc_adjusted_price_rank_v1"] <= 5).sum()), len(winners)),
            "overlay_rows": int(base["brc_adjusted_positive_overlay_flag_v1"].sum()),
            "overlay_wins": int(base.loc[base["brc_adjusted_positive_overlay_flag_v1"], "won"].sum()),
            "false_positive_rows": int((base["brc_adjusted_positive_overlay_flag_v1"] & base["won"].eq(0)).sum()),
        },
    }
    for metrics in refs.values():
        metrics["overlay_win_pct"] = pct(metrics["overlay_wins"], metrics["overlay_rows"])
        metrics["false_positive_pct"] = pct(metrics["false_positive_rows"], metrics["overlay_rows"])

    reference_rows = []
    for label, metrics in refs.items():
        reference_rows.append(
            {
                "rule_set_v1": label,
                "top1_win_pct": metrics["top1_win_pct"],
                "top3_winner_capture_pct": metrics["top3_capture_pct"],
                "top5_winner_capture_pct": metrics["top5_capture_pct"],
                "overlay_rows": metrics["overlay_rows"],
                "overlay_wins": metrics["overlay_wins"],
                "overlay_win_pct": metrics["overlay_win_pct"],
                "false_positive_rows": metrics["false_positive_rows"],
                "false_positive_pct": metrics["false_positive_pct"],
            }
        )
    return refs, pd.DataFrame(reference_rows)


def threshold_table_for_flags(df: pd.DataFrame, view_name: str, overlay_pct_col: str) -> list[dict]:
    rows = []
    for threshold in OVERLAY_THRESHOLDS:
        mask = df[overlay_pct_col] > threshold
        runners = int(mask.sum())
        wins = int(df.loc[mask, "won"].sum()) if runners else 0
        false_positives = int((mask & df["won"].eq(0)).sum()) if runners else 0
        rows.append(
            {
                "pricing_view_v1": view_name,
                "overlay_threshold_gt_v1": threshold,
                "runners": runners,
                "wins": wins,
                "win_pct": pct(wins, runners),
                "false_positives": false_positives,
                "false_positive_rate_pct": pct(false_positives, runners),
                "avg_overlay_pct": round(float(df.loc[mask, overlay_pct_col].mean()), 2) if runners else np.nan,
            }
        )
    return rows


def run_rule_set(base: pd.DataFrame, rule_set_name: str, rule_map: dict[str, float]) -> tuple[pd.DataFrame, dict, dict, pd.DataFrame]:
    df = base.copy()
    df["rule_set_v1"] = rule_set_name
    df["interaction_adjustment_pct_v1"] = df["interaction_bucket_v1"].map(rule_map).fillna(0.0)
    df["interaction_probability_multiplier_v1"] = 1.0 + (df["interaction_adjustment_pct_v1"] / 100.0)
    df["v8_adjusted_raw_prob_v1"] = df["fair_prob_replay_v1"] * df["interaction_probability_multiplier_v1"]
    df["v8_adjusted_prob_v1"] = (
        df["v8_adjusted_raw_prob_v1"]
        / df.groupby("race_key")["v8_adjusted_raw_prob_v1"].transform("sum")
    )
    df["v8_adjusted_fair_price_v1"] = 1.0 / df["v8_adjusted_prob_v1"]
    df["v8_adjusted_prob_delta_v1"] = (df["v8_adjusted_prob_v1"] - df["fair_prob_replay_v1"]).round(6)
    df["v8_adjusted_fair_price_delta_v1"] = (df["v8_adjusted_fair_price_v1"] - df["fair_price_replay_v1"]).round(4)
    df["abs_price_delta_v1"] = df["v8_adjusted_fair_price_delta_v1"].abs()

    df = df.sort_values(
        ["race_key", "v8_adjusted_prob_v1", "horse_name_key"],
        ascending=[True, False, True],
    ).copy()
    df["v8_adjusted_price_rank_v1"] = df.groupby("race_key").cumcount() + 1
    df["v8_adjusted_overlay_pct_v1"] = (
        (df["market_proxy_fair_odds_v1"] / df["v8_adjusted_fair_price_v1"]) - 1.0
    ) * 100.0
    df["v8_adjusted_positive_overlay_flag_v1"] = df["v8_adjusted_overlay_pct_v1"] > 0
    df["v8_adjusted_overlay_truth_v1"] = [
        overlay_truth(flag, won)
        for flag, won in zip(df["v8_adjusted_positive_overlay_flag_v1"], df["won"])
    ]
    df["overlay_added_by_v8_v1"] = (
        ~df["baseline_positive_overlay_flag_v1"] & df["v8_adjusted_positive_overlay_flag_v1"]
    )
    df["overlay_removed_by_v8_v1"] = (
        df["baseline_positive_overlay_flag_v1"] & ~df["v8_adjusted_positive_overlay_flag_v1"]
    )

    winners = df[df["won"] == 1].copy()
    baseline_top1 = df[df["baseline_price_rank_v1"] == 1].copy()
    adjusted_top1 = df[df["v8_adjusted_price_rank_v1"] == 1].copy()
    top1_compare = baseline_top1[
        ["race_key", "horse", "won", "interaction_bucket_v1", "fair_price_replay_v1"]
    ].rename(
        columns={
            "horse": "baseline_top1_horse_v1",
            "won": "baseline_top1_won_v1",
            "interaction_bucket_v1": "baseline_top1_interaction_bucket_v1",
            "fair_price_replay_v1": "baseline_top1_fair_price_v1",
        }
    ).merge(
        adjusted_top1[
            ["race_key", "horse", "won", "interaction_bucket_v1", "v8_adjusted_fair_price_v1"]
        ].rename(
            columns={
                "horse": "v8_top1_horse_v1",
                "won": "v8_top1_won_v1",
                "interaction_bucket_v1": "v8_top1_interaction_bucket_v1",
                "v8_adjusted_fair_price_v1": "v8_top1_fair_price_v1",
            }
        ),
        on="race_key",
        how="inner",
    )
    top1_compare["top1_changed_race_v1"] = top1_compare["baseline_top1_horse_v1"] != top1_compare["v8_top1_horse_v1"]
    top1_compare["winner_to_loser_v1"] = (
        top1_compare["top1_changed_race_v1"]
        & top1_compare["baseline_top1_won_v1"].eq(1)
        & top1_compare["v8_top1_won_v1"].eq(0)
    )
    top1_compare["loser_to_winner_v1"] = (
        top1_compare["top1_changed_race_v1"]
        & top1_compare["baseline_top1_won_v1"].eq(0)
        & top1_compare["v8_top1_won_v1"].eq(1)
    )

    overlay_mask = df["v8_adjusted_positive_overlay_flag_v1"]
    overlay_rows = int(overlay_mask.sum())
    overlay_wins = int(df.loc[overlay_mask, "won"].sum())
    false_positive_rows = int((overlay_mask & df["won"].eq(0)).sum())
    added_rows = int(df["overlay_added_by_v8_v1"].sum())
    removed_rows = int(df["overlay_removed_by_v8_v1"].sum())
    added_win_pct = pct(int(df.loc[df["overlay_added_by_v8_v1"], "won"].sum()), added_rows)
    removed_win_pct = pct(int(df.loc[df["overlay_removed_by_v8_v1"], "won"].sum()), removed_rows)

    metrics = {
        "rule_set_v1": rule_set_name,
        "rows": int(len(df)),
        "races": int(df["race_key"].nunique()),
        "top1_win_pct": pct(int(adjusted_top1["won"].sum()), len(adjusted_top1)),
        "top3_winner_capture_pct": pct(int((winners["v8_adjusted_price_rank_v1"] <= 3).sum()), len(winners)),
        "top5_winner_capture_pct": pct(int((winners["v8_adjusted_price_rank_v1"] <= 5).sum()), len(winners)),
        "overlay_rows": overlay_rows,
        "overlay_wins": overlay_wins,
        "overlay_win_pct": pct(overlay_wins, overlay_rows),
        "false_positive_rows": false_positive_rows,
        "false_positive_pct": pct(false_positive_rows, overlay_rows),
        "top1_changed_races": int(top1_compare["top1_changed_race_v1"].sum()),
        "top1_changed_winner_to_loser": int(top1_compare["winner_to_loser_v1"].sum()),
        "top1_changed_loser_to_winner": int(top1_compare["loser_to_winner_v1"].sum()),
        "average_abs_price_delta": round(float(df["abs_price_delta_v1"].mean()), 4),
        "max_abs_price_delta": round(float(df["abs_price_delta_v1"].max()), 4),
    }

    added_removed = {
        "rule_set_v1": rule_set_name,
        "overlays_added": added_rows,
        "overlays_added_win_pct": added_win_pct,
        "overlays_removed": removed_rows,
        "overlays_removed_win_pct": removed_win_pct,
        "net_overlay_count_change": added_rows - removed_rows,
        "net_overlay_quality_delta": round(
            (0.0 if pd.isna(added_win_pct) else float(added_win_pct))
            - (0.0 if pd.isna(removed_win_pct) else float(removed_win_pct)),
            2,
        ),
    }

    threshold_df = pd.DataFrame(
        threshold_table_for_flags(df, rule_set_name, "v8_adjusted_overlay_pct_v1")
    )
    return df, metrics, added_removed, threshold_df


def add_rule_verdicts(by_rule: pd.DataFrame, refs: dict, added_removed_df: pd.DataFrame) -> pd.DataFrame:
    out = by_rule.merge(added_removed_df, on="rule_set_v1", how="left")
    baseline = refs["BASELINE"]

    out["crit_top1_safe_v1"] = out["top1_win_pct"] >= baseline["top1_win_pct"]
    out["crit_top3_safe_v1"] = out["top3_winner_capture_pct"] >= baseline["top3_capture_pct"]
    out["crit_top5_safe_v1"] = out["top5_winner_capture_pct"] >= baseline["top5_capture_pct"]
    out["overlay_improvement_pts_v1"] = (out["overlay_win_pct"] - baseline["overlay_win_pct"]).round(2)
    out["false_positive_delta_pts_v1"] = (out["false_positive_pct"] - baseline["false_positive_pct"]).round(2)
    out["crit_overlay_improves_v1"] = out["overlay_improvement_pts_v1"] >= 0.05
    out["crit_false_positive_reduces_v1"] = out["false_positive_delta_pts_v1"] < 0
    out["crit_added_removed_quality_v1"] = (
        (out["overlays_added_win_pct"] > out["overlays_removed_win_pct"])
        | (out["overlays_removed_win_pct"] <= 5.0)
    )
    out["crit_top1_change_safe_v1"] = (
        out["top1_changed_winner_to_loser"].eq(0) & out["top1_changed_races"].le(25)
    )

    verdicts = []
    for _, row in out.iterrows():
        safe_rank = bool(row["crit_top1_safe_v1"] and row["crit_top3_safe_v1"] and row["crit_top5_safe_v1"])
        strong_overlay = bool(
            row["crit_overlay_improves_v1"]
            and row["crit_false_positive_reduces_v1"]
            and row["crit_added_removed_quality_v1"]
            and row["crit_top1_change_safe_v1"]
        )
        neutral_overlay = bool(
            safe_rank
            and row["overlay_improvement_pts_v1"] >= 0.0
            and row["false_positive_delta_pts_v1"] <= 0.0
            and row["crit_top1_change_safe_v1"]
        )
        if safe_rank and strong_overlay:
            verdict = "V8_INTERACTION_REPLAY_PASS"
        elif safe_rank and neutral_overlay:
            verdict = "V8_INTERACTION_NEUTRAL_SAFE"
        elif (not safe_rank) or row["false_positive_delta_pts_v1"] > 0:
            verdict = "V8_INTERACTION_FAIL"
        else:
            verdict = "V8_INTERACTION_RESEARCH_ONLY"
        verdicts.append(verdict)
    out["verdict_v1"] = verdicts
    return out


def build_summary(refs: dict, by_rule: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    pass_rows = by_rule[by_rule["verdict_v1"].eq("V8_INTERACTION_REPLAY_PASS")].copy()
    if not pass_rows.empty:
        best = pass_rows.sort_values(
            ["overlay_improvement_pts_v1", "false_positive_delta_pts_v1", "top1_changed_races"],
            ascending=[False, True, True],
        ).iloc[0]
        final_recommendation = "Promote to V8 candidate sidecar."
    else:
        neutral_rows = by_rule[by_rule["verdict_v1"].eq("V8_INTERACTION_NEUTRAL_SAFE")].copy()
        if not neutral_rows.empty:
            best = neutral_rows.sort_values(
                ["overlay_improvement_pts_v1", "false_positive_delta_pts_v1", "top1_changed_races"],
                ascending=[False, True, True],
            ).iloc[0]
            final_recommendation = "Keep as research only."
        else:
            best = by_rule.sort_values(
                ["overlay_improvement_pts_v1", "false_positive_delta_pts_v1", "top1_changed_races"],
                ascending=[False, True, True],
            ).iloc[0]
            final_recommendation = "Reject interaction pricing and keep as display/filter context only."

    rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "baseline_overlay_win_pct", "value": refs["BASELINE"]["overlay_win_pct"]},
        {"metric": "tj_adjusted_overlay_win_pct", "value": refs["TJ_ADJUSTED"]["overlay_win_pct"]},
        {"metric": "brc_adjusted_overlay_win_pct", "value": refs["BRC_ADJUSTED"]["overlay_win_pct"]},
        {"metric": "baseline_false_positive_pct", "value": refs["BASELINE"]["false_positive_pct"]},
        {"metric": "tj_adjusted_false_positive_pct", "value": refs["TJ_ADJUSTED"]["false_positive_pct"]},
        {"metric": "brc_adjusted_false_positive_pct", "value": refs["BRC_ADJUSTED"]["false_positive_pct"]},
        {"metric": "best_rule_set", "value": best["rule_set_v1"]},
        {"metric": "best_v8_overlay_win_pct", "value": best["overlay_win_pct"]},
        {"metric": "best_v8_false_positive_pct", "value": best["false_positive_pct"]},
        {"metric": "best_rule_false_positive_delta_pts", "value": best["false_positive_delta_pts_v1"]},
        {"metric": "best_rule_top1_win_pct", "value": best["top1_win_pct"]},
        {"metric": "best_rule_top3_capture_pct", "value": best["top3_winner_capture_pct"]},
        {"metric": "best_rule_top5_capture_pct", "value": best["top5_winner_capture_pct"]},
        {"metric": "best_rule_top1_changed_races", "value": int(best["top1_changed_races"])},
        {"metric": "best_rule_top1_changed_winner_to_loser", "value": int(best["top1_changed_winner_to_loser"])},
        {"metric": "best_rule_top1_changed_loser_to_winner", "value": int(best["top1_changed_loser_to_winner"])},
        {"metric": "best_rule_overlays_added", "value": int(best["overlays_added"])},
        {"metric": "best_rule_overlays_added_win_pct", "value": best["overlays_added_win_pct"]},
        {"metric": "best_rule_overlays_removed", "value": int(best["overlays_removed"])},
        {"metric": "best_rule_overlays_removed_win_pct", "value": best["overlays_removed_win_pct"]},
        {"metric": "best_rule_net_overlay_quality_delta", "value": best["net_overlay_quality_delta"]},
        {"metric": "best_rule_verdict", "value": best["verdict_v1"]},
        {"metric": "final_recommendation", "value": final_recommendation},
    ]
    return pd.DataFrame(rows), best


def build_json_payload(summary_df: pd.DataFrame, by_rule: pd.DataFrame, added_removed: pd.DataFrame, threshold_df: pd.DataFrame) -> dict:
    return {
        "status": "COMPLETE",
        "summary_metrics": {row["metric"]: row["value"] for row in summary_df.to_dict("records")},
        "by_rule": by_rule.to_dict("records"),
        "added_removed": added_removed.to_dict("records"),
        "thresholds": threshold_df.to_dict("records"),
    }


def main():
    base = load_base()
    refs, _reference_rows = compute_reference_metrics(base)

    detail_frames = []
    by_rule_rows = []
    added_removed_rows = []
    threshold_frames = []

    threshold_frames.append(
        pd.DataFrame(threshold_table_for_flags(base, "BASELINE", "baseline_overlay_pct_v1"))
    )
    threshold_frames.append(
        pd.DataFrame(threshold_table_for_flags(base, "TJ_ADJUSTED", "tj_adjusted_overlay_pct_v1"))
    )
    threshold_frames.append(
        pd.DataFrame(threshold_table_for_flags(base, "BRC_ADJUSTED", "brc_adjusted_overlay_pct_v1"))
    )

    for rule_name, rule_map in RULE_SETS.items():
        detail, metrics, added_removed, thresholds = run_rule_set(base, rule_name, rule_map)
        detail_frames.append(detail)
        by_rule_rows.append(metrics)
        added_removed_rows.append(added_removed)
        threshold_frames.append(thresholds)

    detail_out = pd.concat(detail_frames, ignore_index=True)
    by_rule_df = pd.DataFrame(by_rule_rows)
    added_removed_df = pd.DataFrame(added_removed_rows)
    threshold_df = pd.concat(threshold_frames, ignore_index=True)
    by_rule_df = add_rule_verdicts(by_rule_df, refs, added_removed_df)
    summary_df, best_row = build_summary(refs, by_rule_df)

    write_csv(detail_out, OUT_MAIN)
    write_csv(summary_df, OUT_SUMMARY)
    write_csv(by_rule_df, OUT_BY_RULE)
    write_csv(threshold_df, OUT_BY_THRESHOLD)
    write_csv(added_removed_df, OUT_ADDED_REMOVED)
    write_json(build_json_payload(summary_df, by_rule_df, added_removed_df, threshold_df), OUT_JSON)

    print("[FAIR_PRICE_V8_INTERACTION_FILTER_REPLAY_V1] COMPLETE")
    print(f"best_rule_set={best_row['rule_set_v1']}")
    print(f"baseline_overlay_win_pct={refs['BASELINE']['overlay_win_pct']}")
    print(f"best_v8_overlay_win_pct={best_row['overlay_win_pct']}")
    print(f"false_positive_delta_pts={best_row['false_positive_delta_pts_v1']}")
    print(f"top1_win_pct={best_row['top1_win_pct']}")
    print(f"top3_capture_pct={best_row['top3_winner_capture_pct']}")
    print(f"top5_capture_pct={best_row['top5_winner_capture_pct']}")
    print(
        "overlays_added_removed_quality="
        f"{int(best_row['overlays_added'])}@{best_row['overlays_added_win_pct']} vs "
        f"{int(best_row['overlays_removed'])}@{best_row['overlays_removed_win_pct']}"
    )
    print(f"verdict={best_row['verdict_v1']}")
    print(f"wrote={OUT_MAIN}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_RULE}")
    print(f"wrote={OUT_BY_THRESHOLD}")
    print(f"wrote={OUT_ADDED_REMOVED}")
    print(f"wrote={OUT_JSON}")


if __name__ == "__main__":
    main()
