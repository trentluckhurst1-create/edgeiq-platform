from pathlib import Path
import numpy as np
import pandas as pd
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER = DATA / "edgeiq_trainer_jockey_factor_runner_v1.csv"
RANK1_FAILURE = DATA / "edgeiq_rank1_failure_audit_v1.csv"
PACE = DATA / "edgeiq_pace_advantage_replay_v1.csv"
RELIABILITY = DATA / "edgeiq_environment_v2_replay_audit.csv"

OUT_DETAIL = DATA / "edgeiq_trainer_jockey_factor_effect_on_rank1_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_trainer_jockey_factor_effect_on_rank1_v1_summary.csv"
OUT_FEATURES = DATA / "edgeiq_trainer_jockey_factor_effect_on_rank1_v1_feature_rankings.csv"


def num(series):
    return pd.to_numeric(series, errors="coerce")


def clean_text(value):
    if pd.isna(value):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def pct(numerator, denominator):
    if denominator == 0:
        return np.nan
    return round(float(numerator) / float(denominator) * 100.0, 2)


def win_pct(frame):
    if len(frame) == 0:
        return np.nan
    return round(float(frame["rank1_won"].mean()) * 100.0, 2)


def pick_unique_rank1_winner_races(runner):
    race_counts = (
        runner.groupby(["meeting_date", "track", "race_no"], dropna=False)
        .agg(
            rank1_count=("runner_rank_num", lambda s: int((s == 1).sum())),
            winner_count=("won_num", "sum"),
        )
        .reset_index()
    )
    return race_counts[
        (race_counts["rank1_count"] == 1) & (race_counts["winner_count"] == 1)
    ][["meeting_date", "track", "race_no"]]


def runner_sidecar(runner, eligible, selector_mask, prefix):
    cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "horse_name_key",
        "trainer",
        "jockey",
        "runner_rank",
        "runner_score",
        "score_share_of_race",
        "dominance_score_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "field_size",
        "field_size_bucket_v1",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "trainer_factor_band_v1",
        "trainer_factor_score_v1",
        "jockey_factor_band_v1",
        "jockey_factor_score_v1",
        "combo_factor_band_v1",
        "combo_factor_score_v1",
        "trainer_jockey_blend_score_v1",
        "trainer_jockey_blend_band_v1",
        "won_num",
        "finish_position",
    ]
    side = runner.loc[selector_mask, cols].merge(
        eligible,
        on=["meeting_date", "track", "race_no"],
        how="inner",
    )
    rename = {
        "horse": f"{prefix}_horse_runnerfile",
        "horse_key": f"{prefix}_horse_key_runnerfile",
        "horse_name_key": f"{prefix}_horse_name_key",
        "trainer": f"{prefix}_trainer",
        "jockey": f"{prefix}_jockey",
        "runner_rank": f"{prefix}_runner_rank_runnerfile",
        "runner_score": f"{prefix}_runner_score_runnerfile",
        "score_share_of_race": f"{prefix}_score_share_runnerfile",
        "dominance_score_v1": f"{prefix}_dominance_score_runnerfile",
        "trust_profile_v1": f"{prefix}_trust_profile_runnerfile",
        "trust_band_v1": f"{prefix}_trust_band_runnerfile",
        "field_size": f"{prefix}_field_size_runnerfile",
        "field_size_bucket_v1": f"{prefix}_field_size_bucket_runnerfile",
        "race_reliability_score_v1": f"{prefix}_race_reliability_score_runnerfile",
        "race_reliability_band_v1": f"{prefix}_race_reliability_band_runnerfile",
        "trainer_factor_band_v1": f"{prefix}_trainer_factor_band_v1",
        "trainer_factor_score_v1": f"{prefix}_trainer_factor_score_v1",
        "jockey_factor_band_v1": f"{prefix}_jockey_factor_band_v1",
        "jockey_factor_score_v1": f"{prefix}_jockey_factor_score_v1",
        "combo_factor_band_v1": f"{prefix}_combo_factor_band_v1",
        "combo_factor_score_v1": f"{prefix}_combo_factor_score_v1",
        "trainer_jockey_blend_score_v1": f"{prefix}_trainer_jockey_blend_score_v1",
        "trainer_jockey_blend_band_v1": f"{prefix}_trainer_jockey_blend_band_v1",
        "won_num": f"{prefix}_won_runnerfile",
        "finish_position": f"{prefix}_finish_position_runnerfile",
    }
    return side.rename(columns=rename)


def pace_sidecar(pace, detail, horse_col, prefix):
    base = detail[["meeting_date", "track", "race_no", horse_col]].copy()
    merged = base.merge(
        pace[
            [
                "meeting_date",
                "track",
                "race_no",
                "horse_name_key",
                "pace_advantage_score_v1",
                "pace_advantage_band_v1",
                "pace_role_v1",
            ]
        ],
        left_on=["meeting_date", "track", "race_no", horse_col],
        right_on=["meeting_date", "track", "race_no", "horse_name_key"],
        how="left",
    )
    return merged.rename(
        columns={
            "pace_advantage_score_v1": f"{prefix}_pace_advantage_score_v1",
            "pace_advantage_band_v1": f"{prefix}_pace_advantage_band_v1",
            "pace_role_v1": f"{prefix}_pace_role_v1",
        }
    )[
        [
            f"{prefix}_pace_advantage_score_v1",
            f"{prefix}_pace_advantage_band_v1",
            f"{prefix}_pace_role_v1",
        ]
    ]


def horse_to_horse_feature_rows(losses):
    rows = []
    features = [
        ("TJ_BLEND", "tj_superior_flag_v1"),
        ("PACE_ADVANTAGE", "pace_superior_flag_v1"),
        ("DOMINANCE", "dominance_superior_flag_v1"),
        ("SCORE_SHARE", "score_share_superior_flag_v1"),
    ]
    for feature_name, col in features:
        explained = int(losses[col].fillna(False).sum())
        rows.append(
            {
                "analysis_family": "HORSE_TO_HORSE_LOSS_EXPLANATION",
                "feature_name": feature_name,
                "sample_size": int(len(losses)),
                "positive_cases": explained,
                "positive_case_pct": pct(explained, len(losses)),
                "ranking_score_v1": pct(explained, len(losses)),
                "comparison_note": "Share of Rank1 losses where the eventual winner rated higher than Rank1 on this feature.",
            }
        )
    return rows


def context_lift_row(detail, feature_name, strong_mask, weak_mask):
    strong = detail.loc[strong_mask].copy()
    weak = detail.loc[weak_mask].copy()
    strong_win = win_pct(strong)
    weak_win = win_pct(weak)
    lift = np.nan if pd.isna(strong_win) or pd.isna(weak_win) else round(strong_win - weak_win, 2)
    return {
        "analysis_family": "RACE_CONTEXT_LIFT",
        "feature_name": feature_name,
        "sample_size": int(len(detail)),
        "strong_context_rows": int(len(strong)),
        "weak_context_rows": int(len(weak)),
        "strong_context_rank1_win_pct": strong_win,
        "weak_context_rank1_win_pct": weak_win,
        "lift_pts": lift,
        "ranking_score_v1": lift,
        "comparison_note": "Rank1 win-rate spread between stronger and weaker race contexts.",
    }


def residual_row(losses, feature_name, base_mask, flag_col):
    subset = losses.loc[base_mask].copy()
    explained = int(subset[flag_col].fillna(False).sum()) if len(subset) else 0
    return {
        "analysis_family": "TJ_RESIDUAL",
        "feature_name": feature_name,
        "sample_size": int(len(subset)),
        "positive_cases": explained,
        "positive_case_pct": pct(explained, len(subset)),
        "ranking_score_v1": pct(explained, len(subset)),
        "comparison_note": "Share of residual Rank1 losses still explained by superior TJ blend.",
    }


def build_summary(detail, losses):
    tj_pct = pct(int(losses["tj_superior_flag_v1"].sum()), len(losses))
    pace_pct = pct(int(losses["pace_superior_flag_v1"].sum()), len(losses))
    dom_pct = pct(int(losses["dominance_superior_flag_v1"].sum()), len(losses))
    share_pct = pct(int(losses["score_share_superior_flag_v1"].sum()), len(losses))

    strong_reliability = detail["race_reliability_band_v1"].isin(["POSITIVE", "ELITE"])
    weak_reliability = detail["race_reliability_band_v1"].isin(["POOR", "NEGATIVE"])
    strong_trust = detail["trust_profile_v1"].isin(["STRONG", "ELITE"])
    weak_trust = detail["trust_profile_v1"].isin(["CHAOTIC", "STANDARD"])
    strong_pace = detail["rank1_pace_advantage_band_v1"].isin(["POSITIVE", "ELITE"])
    weak_pace = detail["rank1_pace_advantage_band_v1"].isin(["POOR", "NEGATIVE"])

    reliability_lift = round(win_pct(detail.loc[strong_reliability]) - win_pct(detail.loc[weak_reliability]), 2)
    trust_lift = round(win_pct(detail.loc[strong_trust]) - win_pct(detail.loc[weak_trust]), 2)
    pace_lift = round(win_pct(detail.loc[strong_pace]) - win_pct(detail.loc[weak_pace]), 2)

    residual_no_dom_share_pace = losses["residual_no_dominance_score_share_pace_flag_v1"]
    residual_tj_pct = pct(
        int(losses.loc[residual_no_dom_share_pace, "tj_superior_flag_v1"].sum()),
        int(residual_no_dom_share_pace.sum()),
    )

    strong_context_mask = (
        losses["strong_reliability_context_flag_v1"]
        & losses["strong_trust_context_flag_v1"]
        & losses["strong_pace_context_flag_v1"]
    )
    strong_context_tj_pct = pct(
        int(losses.loc[strong_context_mask, "tj_superior_flag_v1"].sum()),
        int(strong_context_mask.sum()),
    )

    if (
        not pd.isna(tj_pct)
        and not pd.isna(residual_tj_pct)
        and not pd.isna(strong_context_tj_pct)
        and tj_pct >= 50.0
        and residual_tj_pct >= 50.0
        and strong_context_tj_pct >= 50.0
    ):
        verdict = "TJ_ADDS_NEW_INFORMATION"
        fair_price_candidate = "YES"
    elif not pd.isna(tj_pct) and tj_pct >= 45.0:
        verdict = "TJ_PARTIALLY_REDUNDANT_BUT_USEFUL"
        fair_price_candidate = "MAYBE"
    else:
        verdict = "TJ_DISPLAY_ONLY_FOR_NOW"
        fair_price_candidate = "NO"

    best_horse_factor = "TJ_BLEND"
    horse_factor_scores = {
        "TJ_BLEND": tj_pct if not pd.isna(tj_pct) else -999,
        "PACE_ADVANTAGE": pace_pct if not pd.isna(pace_pct) else -999,
        "DOMINANCE": dom_pct if not pd.isna(dom_pct) else -999,
        "SCORE_SHARE": share_pct if not pd.isna(share_pct) else -999,
    }
    best_horse_factor = max(horse_factor_scores, key=horse_factor_scores.get)

    best_context_factor = "RACE_RELIABILITY"
    context_scores = {
        "RACE_RELIABILITY": reliability_lift,
        "TRUST_PROFILE": trust_lift,
        "PACE_ADVANTAGE_CONTEXT": pace_lift,
    }
    best_context_factor = max(context_scores, key=context_scores.get)

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "audit_name", "value": "TRAINER_JOCKEY_FACTOR_EFFECT_ON_RANK1_V1"},
        {"metric": "races_audited", "value": int(len(detail))},
        {"metric": "rank1_wins", "value": int(detail["rank1_won"].sum())},
        {"metric": "rank1_losses", "value": int(len(losses))},
        {"metric": "rank1_win_pct", "value": win_pct(detail)},
        {"metric": "losses_winner_better_tj_blend_pct", "value": tj_pct},
        {"metric": "losses_winner_better_pace_advantage_pct", "value": pace_pct},
        {"metric": "losses_winner_better_dominance_pct", "value": dom_pct},
        {"metric": "losses_winner_better_score_share_pct", "value": share_pct},
        {
            "metric": "race_reliability_strong_rank1_win_pct",
            "value": win_pct(detail.loc[strong_reliability]),
        },
        {
            "metric": "race_reliability_weak_rank1_win_pct",
            "value": win_pct(detail.loc[weak_reliability]),
        },
        {"metric": "race_reliability_lift_pts", "value": reliability_lift},
        {
            "metric": "trust_profile_strong_rank1_win_pct",
            "value": win_pct(detail.loc[strong_trust]),
        },
        {
            "metric": "trust_profile_weak_rank1_win_pct",
            "value": win_pct(detail.loc[weak_trust]),
        },
        {"metric": "trust_profile_lift_pts", "value": trust_lift},
        {
            "metric": "pace_context_strong_rank1_win_pct",
            "value": win_pct(detail.loc[strong_pace]),
        },
        {
            "metric": "pace_context_weak_rank1_win_pct",
            "value": win_pct(detail.loc[weak_pace]),
        },
        {"metric": "pace_context_lift_pts", "value": pace_lift},
        {
            "metric": "residual_no_dominance_score_share_pace_losses",
            "value": int(residual_no_dom_share_pace.sum()),
        },
        {
            "metric": "tj_superior_pct_on_residual_no_dominance_score_share_pace_losses",
            "value": residual_tj_pct,
        },
        {
            "metric": "strong_context_losses",
            "value": int(strong_context_mask.sum()),
        },
        {
            "metric": "tj_superior_pct_on_strong_reliability_strong_trust_strong_pace_losses",
            "value": strong_context_tj_pct,
        },
        {
            "metric": "tj_only_loss_explanation_pct",
            "value": pct(int((losses["tj_superior_flag_v1"] & ~losses["pace_superior_flag_v1"]).sum()), len(losses)),
        },
        {
            "metric": "pace_only_loss_explanation_pct",
            "value": pct(int((~losses["tj_superior_flag_v1"] & losses["pace_superior_flag_v1"]).sum()), len(losses)),
        },
        {
            "metric": "best_horse_to_horse_explainer",
            "value": best_horse_factor,
        },
        {
            "metric": "best_race_context_factor",
            "value": best_context_factor,
        },
        {
            "metric": "dominance_score_share_structural_note",
            "value": "In this audit base Rank1 is already the model's top horse, so winner-superior dominance/score-share rarely or never appear as losing explanations.",
        },
        {"metric": "verdict", "value": verdict},
        {"metric": "future_fair_price_input_candidate", "value": fair_price_candidate},
    ]
    return pd.DataFrame(summary_rows)


def main():
    for required in [RUNNER, RANK1_FAILURE, PACE, RELIABILITY]:
        if not required.exists():
            raise FileNotFoundError(f"Missing input: {required}")

    runner = pd.read_csv(RUNNER, low_memory=False)
    rank1_failure = pd.read_csv(RANK1_FAILURE, low_memory=False)
    pace = pd.read_csv(PACE, low_memory=False)
    reliability = pd.read_csv(RELIABILITY, low_memory=False)

    runner["runner_rank_num"] = num(runner["runner_rank"])
    runner["won_num"] = num(runner["won"]).fillna(0).astype(int)
    runner["horse_name_key"] = runner["horse"].map(clean_text)
    pace["horse_name_key"] = pace["horse"].map(clean_text)

    eligible = pick_unique_rank1_winner_races(runner)

    detail = eligible.merge(
        rank1_failure,
        on=["meeting_date", "track", "race_no"],
        how="inner",
    )

    rank1_side = runner_sidecar(runner, eligible, runner["runner_rank_num"] == 1, "rank1")
    winner_side = runner_sidecar(runner, eligible, runner["won_num"] == 1, "winner")
    detail = detail.merge(rank1_side, on=["meeting_date", "track", "race_no"], how="left")
    detail = detail.merge(winner_side, on=["meeting_date", "track", "race_no"], how="left")

    reliability_cols = [
        "meeting_date",
        "track",
        "race_no",
        "environment_score_v2",
        "environment_band_v2",
        "environment_reason_v2",
    ]
    reliability_race = reliability[reliability_cols].drop_duplicates(
        subset=["meeting_date", "track", "race_no"]
    )
    detail = detail.merge(reliability_race, on=["meeting_date", "track", "race_no"], how="left")

    detail["rank1_name_key"] = detail["rank1_horse"].map(clean_text)
    detail["winner_name_key"] = detail["winner_horse"].map(clean_text)

    rank1_pace = pace_sidecar(pace, detail, "rank1_name_key", "rank1")
    winner_pace = pace_sidecar(pace, detail, "winner_name_key", "winner")
    detail = pd.concat([detail.reset_index(drop=True), rank1_pace, winner_pace], axis=1)

    detail["race_reliability_score_v1"] = num(detail["environment_score_v2"])
    detail["race_reliability_band_v1"] = (
        detail["environment_band_v2"].fillna("UNKNOWN").astype(str).str.upper()
    )
    detail["race_reliability_reason_v1"] = detail["environment_reason_v2"].fillna("")

    detail["rank1_won"] = num(detail["rank1_won"]).fillna(0).astype(int)
    detail["rank1_dominance_score_v1"] = num(detail["rank1_dominance_score_v1"])
    detail["winner_dominance_score_v1"] = num(detail["winner_dominance_score_v1"])
    detail["rank1_score_share_of_race"] = num(detail["rank1_score_share_of_race"])
    detail["winner_score_share_of_race"] = num(detail["winner_score_share_of_race"])
    detail["rank1_pace_advantage_score_v1"] = num(detail["rank1_pace_advantage_score_v1"])
    detail["winner_pace_advantage_score_v1"] = num(detail["winner_pace_advantage_score_v1"])
    detail["rank1_trainer_jockey_blend_score_v1"] = num(detail["rank1_trainer_jockey_blend_score_v1"])
    detail["winner_trainer_jockey_blend_score_v1"] = num(detail["winner_trainer_jockey_blend_score_v1"])

    detail["tj_blend_delta_v1"] = (
        detail["winner_trainer_jockey_blend_score_v1"]
        - detail["rank1_trainer_jockey_blend_score_v1"]
    ).round(3)
    detail["dominance_delta_v1"] = (
        detail["winner_dominance_score_v1"] - detail["rank1_dominance_score_v1"]
    ).round(3)
    detail["score_share_delta_v1"] = (
        detail["winner_score_share_of_race"] - detail["rank1_score_share_of_race"]
    ).round(6)
    detail["pace_advantage_delta_v1"] = (
        detail["winner_pace_advantage_score_v1"] - detail["rank1_pace_advantage_score_v1"]
    ).round(3)

    detail["tj_superior_flag_v1"] = detail["tj_blend_delta_v1"] > 0
    detail["dominance_superior_flag_v1"] = detail["dominance_delta_v1"] > 0
    detail["score_share_superior_flag_v1"] = detail["score_share_delta_v1"] > 0
    detail["pace_superior_flag_v1"] = detail["pace_advantage_delta_v1"] > 0

    detail["strong_reliability_context_flag_v1"] = detail["race_reliability_band_v1"].isin(
        ["POSITIVE", "ELITE"]
    )
    detail["weak_reliability_context_flag_v1"] = detail["race_reliability_band_v1"].isin(
        ["POOR", "NEGATIVE"]
    )
    detail["strong_trust_context_flag_v1"] = detail["trust_profile_v1"].isin(["STRONG", "ELITE"])
    detail["weak_trust_context_flag_v1"] = detail["trust_profile_v1"].isin(
        ["CHAOTIC", "STANDARD"]
    )
    detail["strong_pace_context_flag_v1"] = detail["rank1_pace_advantage_band_v1"].isin(
        ["POSITIVE", "ELITE"]
    )
    detail["weak_pace_context_flag_v1"] = detail["rank1_pace_advantage_band_v1"].isin(
        ["POOR", "NEGATIVE"]
    )
    detail["residual_no_dominance_score_share_pace_flag_v1"] = (
        ~detail["dominance_superior_flag_v1"]
        & ~detail["score_share_superior_flag_v1"]
        & ~detail["pace_superior_flag_v1"]
    )
    detail["tj_only_vs_pace_flag_v1"] = (
        detail["tj_superior_flag_v1"] & ~detail["pace_superior_flag_v1"]
    )

    losses = detail[detail["rank1_won"] == 0].copy()

    feature_rows = []
    feature_rows.extend(horse_to_horse_feature_rows(losses))
    feature_rows.append(
        context_lift_row(
            detail,
            "RACE_RELIABILITY",
            detail["strong_reliability_context_flag_v1"],
            detail["weak_reliability_context_flag_v1"],
        )
    )
    feature_rows.append(
        context_lift_row(
            detail,
            "TRUST_PROFILE",
            detail["strong_trust_context_flag_v1"],
            detail["weak_trust_context_flag_v1"],
        )
    )
    feature_rows.append(
        context_lift_row(
            detail,
            "PACE_ADVANTAGE_CONTEXT",
            detail["strong_pace_context_flag_v1"],
            detail["weak_pace_context_flag_v1"],
        )
    )
    feature_rows.append(
        residual_row(
            losses,
            "TJ_AFTER_NO_DOMINANCE_NO_SCORE_SHARE_NO_PACE",
            losses["residual_no_dominance_score_share_pace_flag_v1"],
            "tj_superior_flag_v1",
        )
    )
    feature_rows.append(
        residual_row(
            losses,
            "TJ_WITHIN_STRONG_RELIABILITY",
            losses["strong_reliability_context_flag_v1"],
            "tj_superior_flag_v1",
        )
    )
    feature_rows.append(
        residual_row(
            losses,
            "TJ_WITHIN_STRONG_TRUST",
            losses["strong_trust_context_flag_v1"],
            "tj_superior_flag_v1",
        )
    )
    feature_rows.append(
        residual_row(
            losses,
            "TJ_WITHIN_STRONG_RELIABILITY_TRUST_AND_PACE",
            losses["strong_reliability_context_flag_v1"]
            & losses["strong_trust_context_flag_v1"]
            & losses["strong_pace_context_flag_v1"],
            "tj_superior_flag_v1",
        )
    )

    feature_rankings = pd.DataFrame(feature_rows)
    feature_rankings["family_sort_v1"] = feature_rankings["analysis_family"].map(
        {
            "HORSE_TO_HORSE_LOSS_EXPLANATION": 1,
            "RACE_CONTEXT_LIFT": 2,
            "TJ_RESIDUAL": 3,
        }
    )
    feature_rankings = feature_rankings.sort_values(
        ["family_sort_v1", "ranking_score_v1"],
        ascending=[True, False],
        na_position="last",
    ).drop(columns=["family_sort_v1"])

    summary = build_summary(detail, losses)

    detail_columns = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "rank1_horse",
        "winner_horse",
        "rank1_won",
        "winner_rank",
        "field_size",
        "field_size_bucket_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "environment_score_v2",
        "environment_band_v2",
        "environment_reason_v2",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "race_reliability_reason_v1",
        "rank1_pace_advantage_score_v1",
        "rank1_pace_advantage_band_v1",
        "rank1_pace_role_v1",
        "winner_pace_advantage_score_v1",
        "winner_pace_advantage_band_v1",
        "winner_pace_role_v1",
        "rank1_dominance_score_v1",
        "winner_dominance_score_v1",
        "dominance_delta_v1",
        "dominance_superior_flag_v1",
        "rank1_score_share_of_race",
        "winner_score_share_of_race",
        "score_share_delta_v1",
        "score_share_superior_flag_v1",
        "rank1_trainer",
        "rank1_jockey",
        "rank1_trainer_factor_band_v1",
        "rank1_jockey_factor_band_v1",
        "rank1_combo_factor_band_v1",
        "rank1_trainer_jockey_blend_band_v1",
        "rank1_trainer_jockey_blend_score_v1",
        "winner_trainer",
        "winner_jockey",
        "winner_trainer_factor_band_v1",
        "winner_jockey_factor_band_v1",
        "winner_combo_factor_band_v1",
        "winner_trainer_jockey_blend_band_v1",
        "winner_trainer_jockey_blend_score_v1",
        "tj_blend_delta_v1",
        "tj_superior_flag_v1",
        "pace_advantage_delta_v1",
        "pace_superior_flag_v1",
        "strong_reliability_context_flag_v1",
        "weak_reliability_context_flag_v1",
        "strong_trust_context_flag_v1",
        "weak_trust_context_flag_v1",
        "strong_pace_context_flag_v1",
        "weak_pace_context_flag_v1",
        "residual_no_dominance_score_share_pace_flag_v1",
        "tj_only_vs_pace_flag_v1",
        "failure_reason_v1",
    ]
    detail = detail[detail_columns].copy()

    detail.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    feature_rankings.to_csv(OUT_FEATURES, index=False)

    print("[TRAINER_JOCKEY_FACTOR_EFFECT_ON_RANK1_V1] COMPLETE")
    print(f"races_audited={len(detail)}")
    print(f"rank1_wins={int(detail['rank1_won'].sum())}")
    print(f"rank1_losses={len(losses)}")
    print(
        "losses_winner_better_tj_blend_pct="
        f"{summary.loc[summary['metric'] == 'losses_winner_better_tj_blend_pct', 'value'].iloc[0]}"
    )
    print(
        "losses_winner_better_pace_advantage_pct="
        f"{summary.loc[summary['metric'] == 'losses_winner_better_pace_advantage_pct', 'value'].iloc[0]}"
    )
    print(
        "losses_winner_better_dominance_pct="
        f"{summary.loc[summary['metric'] == 'losses_winner_better_dominance_pct', 'value'].iloc[0]}"
    )
    print(
        "losses_winner_better_score_share_pct="
        f"{summary.loc[summary['metric'] == 'losses_winner_better_score_share_pct', 'value'].iloc[0]}"
    )
    print(
        "race_reliability_lift_pts="
        f"{summary.loc[summary['metric'] == 'race_reliability_lift_pts', 'value'].iloc[0]}"
    )
    print(
        "trust_profile_lift_pts="
        f"{summary.loc[summary['metric'] == 'trust_profile_lift_pts', 'value'].iloc[0]}"
    )
    print(
        "pace_context_lift_pts="
        f"{summary.loc[summary['metric'] == 'pace_context_lift_pts', 'value'].iloc[0]}"
    )
    print(
        "tj_residual_after_dom_score_share_pace_pct="
        f"{summary.loc[summary['metric'] == 'tj_superior_pct_on_residual_no_dominance_score_share_pace_losses', 'value'].iloc[0]}"
    )
    print(
        "tj_in_strong_reliability_trust_pace_pct="
        f"{summary.loc[summary['metric'] == 'tj_superior_pct_on_strong_reliability_strong_trust_strong_pace_losses', 'value'].iloc[0]}"
    )
    print(
        "verdict="
        f"{summary.loc[summary['metric'] == 'verdict', 'value'].iloc[0]}"
    )
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_FEATURES}")


if __name__ == "__main__":
    main()
