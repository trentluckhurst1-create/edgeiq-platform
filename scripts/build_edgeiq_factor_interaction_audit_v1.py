from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_TJ_REPLAY = DATA / "edgeiq_tj_pricing_impact_replay_v1.csv"
IN_BRC_PRICING = DATA / "edgeiq_barrier_rail_condition_pricing_impact_replay_v1.csv"
IN_BRC_BIAS = DATA / "edgeiq_barrier_rail_condition_bias_replay_v1.csv"
IN_TJ_RUNNER = DATA / "edgeiq_trainer_jockey_factor_runner_v1.csv"
IN_FAIR = DATA / "edgeiq_fair_price_replay_v1.csv"

OUT_MAIN = DATA / "edgeiq_factor_interaction_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_factor_interaction_audit_v1_summary.csv"
OUT_BY_COMBO = DATA / "edgeiq_factor_interaction_audit_v1_by_combo.csv"
OUT_RANK1 = DATA / "edgeiq_factor_interaction_audit_v1_rank1_relevance.csv"
OUT_OVERLAY = DATA / "edgeiq_factor_interaction_audit_v1_overlay_quality.csv"
OUT_JSON = DATA / "edgeiq_factor_interaction_audit_v1.json"


def write_csv(df: pd.DataFrame, name: str) -> Path:
    path = DATA / name
    df.to_csv(path, index=False)
    return path


def write_json(payload: dict, name: str) -> Path:
    path = DATA / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def num(series):
    return pd.to_numeric(series, errors="coerce")


def pct(numerator, denominator):
    if denominator in (0, None) or pd.isna(denominator):
        return np.nan
    return round(float(numerator) / float(denominator) * 100.0, 2)


def compute_tj_verdict(trainer_band: pd.Series, jockey_band: pd.Series, combo_band: pd.Series) -> pd.Series:
    trainer_present = trainer_band.fillna("").astype(str).str.strip().ne("")
    jockey_present = jockey_band.fillna("").astype(str).str.strip().ne("")
    combo_present = combo_band.fillna("").astype(str).str.strip().ne("")
    verdict = np.where(
        trainer_present & jockey_present & combo_present,
        "COMPLETE",
        np.where(
            trainer_present & jockey_present,
            "TRAINER_JOCKEY_ONLY",
            np.where(trainer_present | jockey_present, "PARTIAL", "UNMATCHED"),
        ),
    )
    return pd.Series(verdict, index=trainer_band.index)


def tj_state_from_band_verdict(band: str, verdict: str) -> str:
    band_text = "" if pd.isna(band) else str(band).upper()
    verdict_text = "" if pd.isna(verdict) else str(verdict).upper()
    if verdict_text in {"PARTIAL", "UNMATCHED"}:
        return "TJ_NEUTRAL"
    if band_text in {"ELITE", "POSITIVE"}:
        return "TJ_POSITIVE"
    if band_text in {"NEGATIVE", "POOR"}:
        return "TJ_NEGATIVE"
    return "TJ_NEUTRAL"


def brc_state_from_band(band: str) -> str:
    band_text = "" if pd.isna(band) else str(band).upper()
    if band_text in {"STRONG_POSITIVE", "POSITIVE"}:
        return "BRC_POSITIVE"
    if band_text in {"STRONG_NEGATIVE", "NEGATIVE"}:
        return "BRC_NEGATIVE"
    return "BRC_NEUTRAL"


def tj_score_from_band_verdict(band: str, verdict: str) -> int:
    verdict_text = "" if pd.isna(verdict) else str(verdict).upper()
    if verdict_text in {"PARTIAL", "UNMATCHED"}:
        return 0
    band_text = "" if pd.isna(band) else str(band).upper()
    mapping = {
        "ELITE": 2,
        "POSITIVE": 1,
        "NEUTRAL": 0,
        "LOW_SAMPLE": 0,
        "UNKNOWN": 0,
        "NEGATIVE": -1,
        "POOR": -2,
    }
    return mapping.get(band_text, 0)


def brc_score_from_band(band: str) -> int:
    band_text = "" if pd.isna(band) else str(band).upper()
    mapping = {
        "STRONG_POSITIVE": 2,
        "POSITIVE": 1,
        "NEUTRAL": 0,
        "LOW_SAMPLE": 0,
        "UNKNOWN": 0,
        "NEGATIVE": -1,
        "STRONG_NEGATIVE": -2,
    }
    return mapping.get(band_text, 0)


def load_base() -> pd.DataFrame:
    fair = pd.read_csv(IN_FAIR, low_memory=False)
    tj_replay = pd.read_csv(IN_TJ_REPLAY, low_memory=False)
    brc_pricing = pd.read_csv(IN_BRC_PRICING, low_memory=False)
    tj_runner = pd.read_csv(IN_TJ_RUNNER, low_memory=False)
    brc_bias = pd.read_csv(IN_BRC_BIAS, low_memory=False)

    for frame in [fair, tj_replay, brc_pricing, tj_runner, brc_bias]:
        if "horse_name_key" not in frame.columns and "horse" in frame.columns:
            frame["horse_name_key"] = frame["horse"].map(clean_text)

    base = fair[
        [
            "meeting_date",
            "track",
            "race_no",
            "horse",
            "race_key",
            "runner_rank",
            "runner_score",
            "fair_prob_replay_v1",
            "fair_price_replay_v1",
            "won",
            "finish_position",
            "horse_name_key",
        ]
    ].copy()
    base["runner_rank"] = num(base["runner_rank"])
    base["runner_score"] = num(base["runner_score"])
    base["fair_prob_replay_v1"] = num(base["fair_prob_replay_v1"])
    base["fair_price_replay_v1"] = num(base["fair_price_replay_v1"])
    base["won"] = num(base["won"]).fillna(0).astype(int)
    base["finish_position"] = num(base["finish_position"])
    base["placed"] = ((base["finish_position"] >= 1) & (base["finish_position"] <= 3)).astype(int)

    tj_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse_name_key",
        "trainer",
        "jockey",
        "trainer_factor_band_v1",
        "jockey_factor_band_v1",
        "combo_factor_band_v1",
        "trainer_jockey_blend_score_v1",
        "trainer_jockey_blend_band_v1",
        "tj_probability_adjustment_pct_v1",
        "tj_adjusted_prob_v1",
        "tj_adjusted_fair_price_v1",
        "tj_adjusted_price_rank_v1",
        "tj_adjusted_overlay_pct_v1",
        "tj_adjusted_positive_overlay_flag_v1",
        "overlay_added_by_tj_v1",
        "overlay_removed_by_tj_v1",
    ]
    tj_small = tj_replay[tj_cols].copy()

    brc_cols = [
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
        "barrier_rail_condition_adjustment_pct_v1",
        "brc_adjusted_prob_v1",
        "brc_adjusted_fair_price_v1",
        "brc_adjusted_price_rank_v1",
        "brc_adjusted_overlay_pct_v1",
        "brc_adjusted_positive_overlay_flag_v1",
        "overlay_added_by_brc_v1",
        "overlay_removed_by_brc_v1",
    ]
    brc_small = brc_pricing[brc_cols].copy()

    runner_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse_name_key",
        "horse_key",
    ]
    runner_small = tj_runner[runner_cols].drop_duplicates(
        subset=["meeting_date", "track", "race_no", "horse_name_key"], keep="first"
    )

    bias_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse_name_key",
        "source_url",
    ]
    bias_small = brc_bias[bias_cols].drop_duplicates(
        subset=["meeting_date", "track", "race_no", "horse_name_key"], keep="first"
    )

    merged = base.merge(
        tj_small,
        on=["meeting_date", "track", "race_no", "horse_name_key"],
        how="left",
    ).merge(
        brc_small,
        on=["meeting_date", "track", "race_no", "horse_name_key"],
        how="left",
    ).merge(
        runner_small,
        on=["meeting_date", "track", "race_no", "horse_name_key"],
        how="left",
    ).merge(
        bias_small,
        on=["meeting_date", "track", "race_no", "horse_name_key"],
        how="left",
    )

    merged["trainer_jockey_blend_score_v1"] = num(merged["trainer_jockey_blend_score_v1"]).fillna(0.0)
    merged["barrier_rail_condition_score_v1"] = num(merged["barrier_rail_condition_score_v1"]).fillna(0.0)
    merged["trainer_jockey_blend_band_v1"] = merged["trainer_jockey_blend_band_v1"].fillna("UNKNOWN").astype(str).str.upper()
    merged["barrier_rail_condition_band_v1"] = merged["barrier_rail_condition_band_v1"].fillna("UNKNOWN").astype(str).str.upper()
    merged["trainer_factor_band_v1"] = merged["trainer_factor_band_v1"].fillna("").astype(str).str.upper()
    merged["jockey_factor_band_v1"] = merged["jockey_factor_band_v1"].fillna("").astype(str).str.upper()
    merged["combo_factor_band_v1"] = merged["combo_factor_band_v1"].fillna("").astype(str).str.upper()
    merged["tj_verdict_v1"] = compute_tj_verdict(
        merged["trainer_factor_band_v1"],
        merged["jockey_factor_band_v1"],
        merged["combo_factor_band_v1"],
    )
    merged["baseline_overlay_pct_v1"] = (
        (merged.groupby("race_key")["horse_name_key"].transform("count") / merged["fair_price_replay_v1"]) - 1.0
    ) * 100.0
    merged["baseline_positive_overlay_flag_v1"] = merged["baseline_overlay_pct_v1"] > 0
    return merged


def add_interaction_fields(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["tj_state_v1"] = [
        tj_state_from_band_verdict(band, verdict)
        for band, verdict in zip(out["trainer_jockey_blend_band_v1"], out["tj_verdict_v1"])
    ]
    out["brc_state_v1"] = out["barrier_rail_condition_band_v1"].map(brc_state_from_band)
    out["interaction_bucket_v1"] = out["tj_state_v1"] + " + " + out["brc_state_v1"]
    out["tj_score_v1"] = [
        tj_score_from_band_verdict(band, verdict)
        for band, verdict in zip(out["trainer_jockey_blend_band_v1"], out["tj_verdict_v1"])
    ]
    out["brc_score_v1"] = out["barrier_rail_condition_band_v1"].map(brc_score_from_band)
    out["interaction_score_v1"] = out["tj_score_v1"] + out["brc_score_v1"]
    out["tj_positive_flag_v1"] = out["tj_state_v1"].eq("TJ_POSITIVE")
    out["tj_negative_flag_v1"] = out["tj_state_v1"].eq("TJ_NEGATIVE")
    out["brc_positive_flag_v1"] = out["brc_state_v1"].eq("BRC_POSITIVE")
    out["brc_negative_flag_v1"] = out["brc_state_v1"].eq("BRC_NEGATIVE")
    out["interaction_positive_agreement_flag_v1"] = out["tj_positive_flag_v1"] & out["brc_positive_flag_v1"]
    out["interaction_negative_agreement_flag_v1"] = out["tj_negative_flag_v1"] & out["brc_negative_flag_v1"]
    out["interaction_score_ge_2_flag_v1"] = out["interaction_score_v1"] >= 2
    out["interaction_score_le_minus_2_flag_v1"] = out["interaction_score_v1"] <= -2
    return out


def aggregate_combo_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for combo, group in df.groupby("interaction_bucket_v1", dropna=False):
        overlay_mask = group["baseline_positive_overlay_flag_v1"]
        overlay_rows = int(overlay_mask.sum())
        overlay_wins = int(group.loc[overlay_mask, "won"].sum()) if overlay_rows else 0
        false_positives = int((overlay_mask & group["won"].eq(0)).sum()) if overlay_rows else 0
        rows.append(
            {
                "interaction_bucket_v1": combo,
                "runners": int(len(group)),
                "wins": int(group["won"].sum()),
                "places": int(group["placed"].sum()),
                "win_pct": pct(int(group["won"].sum()), len(group)),
                "place_pct": pct(int(group["placed"].sum()), len(group)),
                "avg_model_rank": round(float(group["runner_rank"].mean()), 3),
                "avg_fair_price": round(float(group["fair_price_replay_v1"].mean()), 3),
                "avg_interaction_score_v1": round(float(group["interaction_score_v1"].mean()), 3),
                "overlay_rows": overlay_rows,
                "overlay_win_pct": pct(overlay_wins, overlay_rows),
                "false_positive_pct": pct(false_positives, overlay_rows),
            }
        )
    combo_df = pd.DataFrame(rows).sort_values(["win_pct", "runners"], ascending=[False, False]).reset_index(drop=True)
    return combo_df


def derive_rank1_relevance(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    race_agg = (
        df.groupby("race_key", dropna=False)
        .agg(rank1_count=("runner_rank", lambda s: int((s == 1).sum())), winner_count=("won", "sum"))
        .reset_index()
    )
    eligible = race_agg[(race_agg["rank1_count"] == 1) & (race_agg["winner_count"] == 1)][["race_key"]]

    rank1 = df[df["runner_rank"] == 1].copy()
    winner = df[df["won"] == 1].copy()

    rank1_side = rank1[
        [
            "race_key",
            "meeting_date",
            "track",
            "race_no",
            "horse",
            "horse_key",
            "trainer_jockey_blend_score_v1",
            "trainer_jockey_blend_band_v1",
            "tj_verdict_v1",
            "barrier_rail_condition_score_v1",
            "barrier_rail_condition_band_v1",
            "interaction_bucket_v1",
            "interaction_score_v1",
            "tj_state_v1",
            "brc_state_v1",
        ]
    ].rename(
        columns={
            "horse": "rank1_horse",
            "horse_key": "rank1_horse_key",
            "trainer_jockey_blend_score_v1": "rank1_tj_score_continuous_v1",
            "trainer_jockey_blend_band_v1": "rank1_tj_band_v1",
            "tj_verdict_v1": "rank1_tj_verdict_v1",
            "barrier_rail_condition_score_v1": "rank1_brc_score_continuous_v1",
            "barrier_rail_condition_band_v1": "rank1_brc_band_v1",
            "interaction_bucket_v1": "rank1_interaction_bucket_v1",
            "interaction_score_v1": "rank1_interaction_score_v1",
            "tj_state_v1": "rank1_tj_state_v1",
            "brc_state_v1": "rank1_brc_state_v1",
        }
    )
    winner_side = winner[
        [
            "race_key",
            "horse",
            "horse_key",
            "trainer_jockey_blend_score_v1",
            "trainer_jockey_blend_band_v1",
            "tj_verdict_v1",
            "barrier_rail_condition_score_v1",
            "barrier_rail_condition_band_v1",
            "interaction_bucket_v1",
            "interaction_score_v1",
            "tj_state_v1",
            "brc_state_v1",
        ]
    ].rename(
        columns={
            "horse": "winner_horse",
            "horse_key": "winner_horse_key",
            "trainer_jockey_blend_score_v1": "winner_tj_score_continuous_v1",
            "trainer_jockey_blend_band_v1": "winner_tj_band_v1",
            "tj_verdict_v1": "winner_tj_verdict_v1",
            "barrier_rail_condition_score_v1": "winner_brc_score_continuous_v1",
            "barrier_rail_condition_band_v1": "winner_brc_band_v1",
            "interaction_bucket_v1": "winner_interaction_bucket_v1",
            "interaction_score_v1": "winner_interaction_score_v1",
            "tj_state_v1": "winner_tj_state_v1",
            "brc_state_v1": "winner_brc_state_v1",
        }
    )

    detail = eligible.merge(rank1_side, on="race_key", how="inner").merge(winner_side, on="race_key", how="inner")
    detail["rank1_won_v1"] = detail["rank1_horse"].fillna("").astype(str).str.upper() == detail["winner_horse"].fillna("").astype(str).str.upper()
    detail["rank1_loss_flag_v1"] = ~detail["rank1_won_v1"]
    losses = detail[detail["rank1_loss_flag_v1"]].copy()
    losses["winner_better_tj_flag_v1"] = losses["winner_tj_score_continuous_v1"] > losses["rank1_tj_score_continuous_v1"]
    losses["winner_better_brc_flag_v1"] = losses["winner_brc_score_continuous_v1"] > losses["rank1_brc_score_continuous_v1"]
    losses["winner_better_interaction_flag_v1"] = losses["winner_interaction_score_v1"] > losses["rank1_interaction_score_v1"]

    summary = {
        "races_audited": int(len(detail)),
        "rank1_losses": int(len(losses)),
        "winner_better_tj_pct": pct(int(losses["winner_better_tj_flag_v1"].sum()), len(losses)),
        "winner_better_brc_pct": pct(int(losses["winner_better_brc_flag_v1"].sum()), len(losses)),
        "winner_better_interaction_pct": pct(int(losses["winner_better_interaction_flag_v1"].sum()), len(losses)),
    }
    return detail, summary


def summarize_overlay_quality(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add_row(label: str, mask: pd.Series):
        runners = int(mask.sum())
        wins = int(df.loc[mask, "won"].sum()) if runners else 0
        false_positives = int((mask & df["won"].eq(0)).sum()) if runners else 0
        rows.append(
            {
                "overlay_view_v1": label,
                "overlay_rows": runners,
                "overlay_wins": wins,
                "overlay_win_pct": pct(wins, runners),
                "false_positives": false_positives,
                "false_positive_pct": pct(false_positives, runners),
            }
        )

    add_row("BASELINE_ALL", df["baseline_positive_overlay_flag_v1"])
    add_row("TJ_ADJUSTED_ALL", df["tj_adjusted_positive_overlay_flag_v1"])
    add_row("BRC_ADJUSTED_ALL", df["brc_adjusted_positive_overlay_flag_v1"])
    add_row(
        "TJ_POSITIVE_ANY_BASELINE_OVERLAYS",
        df["baseline_positive_overlay_flag_v1"] & df["tj_positive_flag_v1"],
    )
    add_row(
        "BRC_POSITIVE_ANY_BASELINE_OVERLAYS",
        df["baseline_positive_overlay_flag_v1"] & df["brc_positive_flag_v1"],
    )
    add_row(
        "TJ_POSITIVE_BRC_POSITIVE_BASELINE_OVERLAYS",
        df["baseline_positive_overlay_flag_v1"] & df["interaction_positive_agreement_flag_v1"],
    )
    add_row(
        "TJ_POSITIVE_BRC_NEGATIVE_BASELINE_OVERLAYS",
        df["baseline_positive_overlay_flag_v1"] & df["tj_positive_flag_v1"] & df["brc_negative_flag_v1"],
    )
    add_row(
        "TJ_NEGATIVE_BRC_POSITIVE_BASELINE_OVERLAYS",
        df["baseline_positive_overlay_flag_v1"] & df["tj_negative_flag_v1"] & df["brc_positive_flag_v1"],
    )
    add_row(
        "INTERACTION_SCORE_GE_2_BASELINE_OVERLAYS",
        df["baseline_positive_overlay_flag_v1"] & df["interaction_score_ge_2_flag_v1"],
    )
    add_row(
        "INTERACTION_SCORE_LE_MINUS_2_BASELINE_OVERLAYS",
        df["baseline_positive_overlay_flag_v1"] & df["interaction_score_le_minus_2_flag_v1"],
    )
    return pd.DataFrame(rows)


def build_summary(
    df: pd.DataFrame,
    combo_df: pd.DataFrame,
    rank1_summary: dict,
    overlay_df: pd.DataFrame,
) -> pd.DataFrame:
    def overlay_metric(label: str, metric: str):
        match = overlay_df.loc[overlay_df["overlay_view_v1"].eq(label), metric]
        if match.empty:
            return np.nan
        return match.iloc[0]

    interaction_positive_win = combo_df.loc[
        combo_df["interaction_bucket_v1"].eq("TJ_POSITIVE + BRC_POSITIVE"),
        "win_pct",
    ]
    interaction_negative_win = combo_df.loc[
        combo_df["interaction_bucket_v1"].eq("TJ_NEGATIVE + BRC_NEGATIVE"),
        "win_pct",
    ]
    interaction_positive_win = interaction_positive_win.iloc[0] if not interaction_positive_win.empty else np.nan
    interaction_negative_win = interaction_negative_win.iloc[0] if not interaction_negative_win.empty else np.nan

    tj_lift = (
        pct(int(df.loc[df["tj_positive_flag_v1"], "won"].sum()), int(df["tj_positive_flag_v1"].sum()))
        - pct(int(df.loc[df["tj_negative_flag_v1"], "won"].sum()), int(df["tj_negative_flag_v1"].sum()))
    )
    brc_lift = (
        pct(int(df.loc[df["brc_positive_flag_v1"], "won"].sum()), int(df["brc_positive_flag_v1"].sum()))
        - pct(int(df.loc[df["brc_negative_flag_v1"], "won"].sum()), int(df["brc_negative_flag_v1"].sum()))
    )
    interaction_lift = (
        pct(int(df.loc[df["interaction_score_ge_2_flag_v1"], "won"].sum()), int(df["interaction_score_ge_2_flag_v1"].sum()))
        - pct(int(df.loc[df["interaction_score_le_minus_2_flag_v1"], "won"].sum()), int(df["interaction_score_le_minus_2_flag_v1"].sum()))
    )

    baseline_overlay_win = overlay_metric("BASELINE_ALL", "overlay_win_pct")
    tj_overlay_win = overlay_metric("TJ_ADJUSTED_ALL", "overlay_win_pct")
    brc_overlay_win = overlay_metric("BRC_ADJUSTED_ALL", "overlay_win_pct")
    pospos_overlay_win = overlay_metric("TJ_POSITIVE_BRC_POSITIVE_BASELINE_OVERLAYS", "overlay_win_pct")
    baseline_fp = overlay_metric("BASELINE_ALL", "false_positive_pct")
    tj_fp = overlay_metric("TJ_ADJUSTED_ALL", "false_positive_pct")
    brc_fp = overlay_metric("BRC_ADJUSTED_ALL", "false_positive_pct")
    pospos_fp = overlay_metric("TJ_POSITIVE_BRC_POSITIVE_BASELINE_OVERLAYS", "false_positive_pct")

    adds_new_info = (
        not pd.isna(rank1_summary["winner_better_interaction_pct"])
        and rank1_summary["winner_better_interaction_pct"] >= rank1_summary["winner_better_tj_pct"] + 3.0
        and rank1_summary["winner_better_interaction_pct"] >= rank1_summary["winner_better_brc_pct"] + 3.0
    )
    pricing_improves = (
        not pd.isna(pospos_overlay_win)
        and pospos_overlay_win > max(baseline_overlay_win, tj_overlay_win, brc_overlay_win)
        and pospos_fp < min(baseline_fp, tj_fp, brc_fp)
    )

    if adds_new_info:
        verdict = "INTERACTION_ADDS_NEW_INFORMATION"
    elif pricing_improves:
        verdict = "INTERACTION_PRICING_CANDIDATE"
    elif (
        not pd.isna(rank1_summary["winner_better_interaction_pct"])
        and rank1_summary["winner_better_interaction_pct"] > max(
            rank1_summary["winner_better_tj_pct"],
            rank1_summary["winner_better_brc_pct"],
        )
    ):
        verdict = "INTERACTION_CONTEXT_ONLY"
    else:
        verdict = "NO_INTERACTION_EDGE"

    rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "rows", "value": int(len(df))},
        {"metric": "races", "value": int(df["race_key"].nunique())},
        {"metric": "interaction_combo_count", "value": int(combo_df["interaction_bucket_v1"].nunique())},
        {"metric": "winner_better_tj_pct", "value": rank1_summary["winner_better_tj_pct"]},
        {"metric": "winner_better_brc_pct", "value": rank1_summary["winner_better_brc_pct"]},
        {"metric": "winner_better_interaction_pct", "value": rank1_summary["winner_better_interaction_pct"]},
        {"metric": "tj_positive_vs_negative_win_lift_pts", "value": round(float(tj_lift), 2) if not pd.isna(tj_lift) else np.nan},
        {"metric": "brc_positive_vs_negative_win_lift_pts", "value": round(float(brc_lift), 2) if not pd.isna(brc_lift) else np.nan},
        {"metric": "interaction_score_extremes_win_lift_pts", "value": round(float(interaction_lift), 2) if not pd.isna(interaction_lift) else np.nan},
        {"metric": "tj_positive_brc_positive_win_pct", "value": interaction_positive_win},
        {"metric": "tj_negative_brc_negative_win_pct", "value": interaction_negative_win},
        {"metric": "baseline_overlay_win_pct", "value": baseline_overlay_win},
        {"metric": "tj_adjusted_overlay_win_pct", "value": tj_overlay_win},
        {"metric": "brc_adjusted_overlay_win_pct", "value": brc_overlay_win},
        {"metric": "interaction_pospos_overlay_win_pct", "value": pospos_overlay_win},
        {"metric": "baseline_false_positive_pct", "value": baseline_fp},
        {"metric": "tj_adjusted_false_positive_pct", "value": tj_fp},
        {"metric": "brc_adjusted_false_positive_pct", "value": brc_fp},
        {"metric": "interaction_pospos_false_positive_pct", "value": pospos_fp},
        {"metric": "is_interaction_score_better_than_tj_alone", "value": "YES" if interaction_lift > tj_lift else "NO"},
        {"metric": "is_interaction_score_better_than_brc_alone", "value": "YES" if interaction_lift > brc_lift else "NO"},
        {"metric": "is_worth_fair_price_v8_replay", "value": "YES" if verdict in {"INTERACTION_ADDS_NEW_INFORMATION", "INTERACTION_PRICING_CANDIDATE"} else "NO"},
        {"metric": "verdict", "value": verdict},
    ]
    return pd.DataFrame(rows)


def build_json_payload(summary_df: pd.DataFrame, combo_df: pd.DataFrame, overlay_df: pd.DataFrame) -> dict:
    return {
        "status": "COMPLETE",
        "summary_metrics": {row["metric"]: row["value"] for row in summary_df.to_dict("records")},
        "by_combo_top_win_pct": combo_df.sort_values(["win_pct", "runners"], ascending=[False, False]).head(10).to_dict("records"),
        "by_combo_top_overlay_quality": combo_df.sort_values(["overlay_win_pct", "overlay_rows"], ascending=[False, False]).head(10).to_dict("records"),
        "overlay_quality_rows": overlay_df.to_dict("records"),
    }


def main():
    for path in [IN_TJ_REPLAY, IN_BRC_PRICING, IN_BRC_BIAS, IN_TJ_RUNNER, IN_FAIR]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")

    base = add_interaction_fields(load_base())
    combo_df = aggregate_combo_table(base)
    rank1_detail, rank1_summary = derive_rank1_relevance(base)
    overlay_df = summarize_overlay_quality(base)
    summary_df = build_summary(base, combo_df, rank1_summary, overlay_df)

    write_csv(base, OUT_MAIN.name)
    write_csv(summary_df, OUT_SUMMARY.name)
    write_csv(combo_df, OUT_BY_COMBO.name)
    write_csv(rank1_detail, OUT_RANK1.name)
    write_csv(overlay_df, OUT_OVERLAY.name)
    write_json(build_json_payload(summary_df, combo_df, overlay_df), OUT_JSON.name)

    verdict = summary_df.loc[summary_df["metric"].eq("verdict"), "value"].iloc[0]
    print("[FACTOR_INTERACTION_AUDIT_V1] COMPLETE")
    print(f"rows={len(base)}")
    print(f"races={base['race_key'].nunique()}")
    print(f"winner_better_tj_pct={rank1_summary['winner_better_tj_pct']}")
    print(f"winner_better_brc_pct={rank1_summary['winner_better_brc_pct']}")
    print(f"winner_better_interaction_pct={rank1_summary['winner_better_interaction_pct']}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT_MAIN}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_COMBO}")
    print(f"wrote={OUT_RANK1}")
    print(f"wrote={OUT_OVERLAY}")
    print(f"wrote={OUT_JSON}")


if __name__ == "__main__":
    main()
