from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

import build_edgeiq_execution_v4_replay_sweep_v1 as v4_sweep


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RULES_PATH = DATA / "edgeiq_execution_v4_replay_sweep_v1.csv"
RANK_PROBS_PATH = DATA / "edgeiq_probability_model_v1_rank_probs.csv"
SCORE_PROBS_PATH = DATA / "edgeiq_probability_model_v1_score_probs.csv"
REAL_FAKE_OVERLAY_PATH = DATA / "edgeiq_real_vs_fake_overlay_replay_v1.csv"

AUDIT_OUT = DATA / "edgeiq_market_disagreement_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_market_disagreement_audit_v1_summary.csv"

WINNING_RULE_ID = "SHARE_VERY_HIGH|DOM_ELITE|RANK_LE_1|EDGE_GE_0|TRUST_ELITE_STRONG_ONLY"
EDGE_BUCKETS = ["0-10", "10-20", "20-30", "30-50", "50-100", "100+"]
QUINTILE_LABELS = ["Q1_LOWEST", "Q2", "Q3", "Q4", "Q5_HIGHEST"]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def pick_rule_row() -> pd.Series:
    rules_df = pd.read_csv(RULES_PATH, low_memory=False)
    rules_df["rule_id"] = rules_df["rule_id"].fillna("").astype(str).map(clean_text)
    exact = rules_df[rules_df["rule_id"].eq(WINNING_RULE_ID)].copy()
    if not exact.empty:
        return exact.iloc[0]

    fallback = rules_df[
        rules_df["score_share_min"].fillna("").astype(str).eq("VERY_HIGH")
        & rules_df["dominance_min"].fillna("").astype(str).eq("ELITE")
        & pd.to_numeric(rules_df["rank_max"], errors="coerce").eq(1)
        & rules_df["trust_profile_filter"].fillna("").astype(str).eq("ELITE_STRONG_ONLY")
    ].copy()
    if fallback.empty:
        raise ValueError(f"Winning rule not found in {RULES_PATH}")

    fallback["edge_min_num_v1"] = pd.to_numeric(fallback["edge_min"], errors="coerce")
    fallback = fallback.sort_values(["win_rate", "edge_min_num_v1"], ascending=[False, True]).reset_index(drop=True)
    return fallback.iloc[0]


def load_probability_maps() -> tuple[dict[str, float], dict[str, float]]:
    rank_df = pd.read_csv(RANK_PROBS_PATH, low_memory=False, usecols=["rank_bucket", "true_win_rate"])
    rank_df["rank_bucket"] = rank_df["rank_bucket"].fillna("").astype(str).map(clean_text)
    rank_df["true_win_rate"] = pd.to_numeric(rank_df["true_win_rate"], errors="coerce")
    rank_map = dict(zip(rank_df["rank_bucket"], rank_df["true_win_rate"]))

    score_df = pd.read_csv(SCORE_PROBS_PATH, low_memory=False, usecols=["score_band", "true_win_rate"])
    score_df["score_band"] = score_df["score_band"].fillna("").astype(str).map(clean_text)
    score_df["true_win_rate"] = pd.to_numeric(score_df["true_win_rate"], errors="coerce")
    score_map = dict(zip(score_df["score_band"], score_df["true_win_rate"]))

    return rank_map, score_map


def load_overlay_base() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "field_size",
        "runner_score",
        "runner_rank",
        "rank_bucket",
        "score_band",
        "finish_position",
        "won",
        "placed",
        "historical_rank_prob",
        "historical_score_band_prob",
        "race_softmax_prob",
        "empirical_probability",
        "empirical_fair_odds",
        "edge_proxy_pct",
        "overlay_band",
        "positive_overlay_flag",
        "dominance_score_v1",
        "dominance_band_v1",
        "score_share_of_race",
        "score_share_band_v1",
    ]
    df = pd.read_csv(REAL_FAKE_OVERLAY_PATH, low_memory=False, usecols=usecols)

    for col in [
        "meeting_date",
        "track",
        "horse",
        "rank_bucket",
        "score_band",
        "overlay_band",
        "dominance_band_v1",
        "score_share_band_v1",
    ]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)

    for col in [
        "race_no",
        "field_size",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
        "placed",
        "historical_rank_prob",
        "historical_score_band_prob",
        "race_softmax_prob",
        "empirical_probability",
        "empirical_fair_odds",
        "edge_proxy_pct",
        "dominance_score_v1",
        "score_share_of_race",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["positive_overlay_flag"] = df["edge_proxy_pct"].gt(0)
    df = df[df["positive_overlay_flag"]].copy()
    df["join_key_v1"] = v4_sweep.build_join_key(df)
    return df.copy()


def build_v4_universe(rule_row: pd.Series) -> pd.DataFrame:
    rank_map, score_map = load_probability_maps()
    overlay_df = load_overlay_base()
    trust_profiles = v4_sweep.reconstruct_historical_trust_profiles()

    overlay_df = overlay_df.merge(
        trust_profiles[
            [
                "join_key_v1",
                "trust_profile_v1",
                "trust_band_v1",
                "field_size_bucket",
                "gap_1_2_band",
                "gap_1_3_band",
                "dominance_certainty_band",
            ]
        ],
        on="join_key_v1",
        how="left",
    )

    overlay_df["trust_profile_v1"] = overlay_df["trust_profile_v1"].fillna("UNKNOWN")
    overlay_df["trust_band_v1"] = overlay_df["trust_band_v1"].fillna("UNKNOWN")
    overlay_df["field_size_bucket"] = overlay_df["field_size_bucket"].fillna("UNKNOWN")
    overlay_df["gap_1_2_band"] = overlay_df["gap_1_2_band"].fillna("UNKNOWN")
    overlay_df["gap_1_3_band"] = overlay_df["gap_1_3_band"].fillna("UNKNOWN")
    overlay_df["dominance_certainty_band"] = overlay_df["dominance_certainty_band"].fillna("UNKNOWN")

    overlay_df["rank_probability_v1"] = overlay_df["rank_bucket"].map(rank_map).fillna(overlay_df["historical_rank_prob"])
    overlay_df["score_probability_v1"] = overlay_df["score_band"].map(score_map).fillna(overlay_df["historical_score_band_prob"])
    overlay_df["blended_probability_v1"] = overlay_df["empirical_probability"]
    overlay_df["blended_fair_odds_v1"] = overlay_df["empirical_fair_odds"]

    filtered = overlay_df[
        overlay_df["score_share_band_v1"].isin(v4_sweep.SCORE_SHARE_RULES[clean_text(rule_row["score_share_min"]).upper()])
        & overlay_df["dominance_band_v1"].isin(v4_sweep.DOMINANCE_RULES[clean_text(rule_row["dominance_min"]).upper()])
        & overlay_df["runner_rank"].le(int(pd.to_numeric(rule_row["rank_max"], errors="coerce")))
        & overlay_df["edge_proxy_pct"].ge(float(pd.to_numeric(rule_row["edge_min"], errors="coerce")))
        & overlay_df["trust_profile_v1"].isin(v4_sweep.TRUST_PROFILE_RULES[clean_text(rule_row["trust_profile_filter"]).upper()])
    ].copy()

    filtered["year"] = filtered["meeting_date"].astype(str).str[:4]
    return filtered.reset_index(drop=True)


def edge_bucket(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "UNKNOWN"
    if number < 10:
        return "0-10"
    if number < 20:
        return "10-20"
    if number < 30:
        return "20-30"
    if number < 50:
        return "30-50"
    if number < 100:
        return "50-100"
    return "100+"


def quantile_bucket(series: pd.Series, prefix: str) -> tuple[pd.Series, list[str]]:
    non_null = pd.to_numeric(series, errors="coerce")
    valid = non_null.dropna()
    if valid.empty:
        return pd.Series(["UNKNOWN"] * len(series), index=series.index), ["UNKNOWN"]

    quantile_count = min(5, valid.nunique())
    if quantile_count <= 1:
        labels = [f"{prefix}_Q1"]
        return pd.Series(labels[0], index=series.index), labels

    labels = QUINTILE_LABELS[:quantile_count]
    bucketed = pd.qcut(valid, q=quantile_count, labels=labels, duplicates="drop")
    result = pd.Series("UNKNOWN", index=series.index, dtype=object)
    result.loc[bucketed.index] = bucketed.astype(str)
    return result, labels


def summarize_bucket(df: pd.DataFrame, bucket_col: str, ordered_labels: list[str]) -> pd.DataFrame:
    grouped = (
        df.groupby(bucket_col, dropna=False)
        .agg(
            signals=("horse", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_edge_proxy_pct=("edge_proxy_pct", "mean"),
            avg_score_share=("score_share_of_race", "mean"),
            avg_dominance_score=("dominance_score_v1", "mean"),
        )
        .reset_index()
    )
    grouped[bucket_col] = grouped[bucket_col].fillna("UNKNOWN").astype(str).map(clean_text)
    grouped["win_rate"] = grouped.apply(lambda row: safe_div(row["wins"], row["signals"]), axis=1)
    grouped["place_rate"] = grouped.apply(lambda row: safe_div(row["places"], row["signals"]), axis=1)

    present = set(grouped[bucket_col].tolist())
    for label in ordered_labels:
        if label not in present:
            grouped = pd.concat(
                [
                    grouped,
                    pd.DataFrame(
                        [
                            {
                                bucket_col: label,
                                "signals": 0,
                                "wins": 0,
                                "places": 0,
                                "avg_edge_proxy_pct": math.nan,
                                "avg_score_share": math.nan,
                                "avg_dominance_score": math.nan,
                                "win_rate": math.nan,
                                "place_rate": math.nan,
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )

    grouped[bucket_col] = pd.Categorical(grouped[bucket_col], categories=ordered_labels, ordered=True)
    grouped = grouped.sort_values(bucket_col).reset_index(drop=True)
    return grouped.copy()


def monotonic_increasing(values: list[float]) -> bool:
    cleaned = [value for value in values if pd.notna(value)]
    if len(cleaned) <= 1:
        return True
    return all(b >= a for a, b in zip(cleaned, cleaned[1:]))


def feature_correlation(df: pd.DataFrame, feature_col: str) -> tuple[float, float]:
    feature = pd.to_numeric(df[feature_col], errors="coerce")
    target = pd.to_numeric(df["won"], errors="coerce")
    valid = pd.DataFrame({"feature": feature, "target": target}).dropna()
    if valid.empty or valid["feature"].nunique() <= 1 or valid["target"].nunique() <= 1:
        return math.nan, math.nan
    corr = float(valid["feature"].corr(valid["target"]))
    return corr, abs(corr)


def build_summary(v4_df: pd.DataFrame) -> pd.DataFrame:
    v4_df["edge_bucket_v1"] = v4_df["edge_proxy_pct"].map(edge_bucket)
    v4_df["score_share_quintile_v1"], score_labels = quantile_bucket(v4_df["score_share_of_race"], "SHARE")
    v4_df["dominance_quintile_v1"], dom_labels = quantile_bucket(v4_df["dominance_score_v1"], "DOM")

    by_edge = summarize_bucket(v4_df, "edge_bucket_v1", EDGE_BUCKETS)
    by_share = summarize_bucket(v4_df, "score_share_quintile_v1", score_labels)
    by_dom = summarize_bucket(v4_df, "dominance_quintile_v1", dom_labels)

    corr_rows = []
    for feature in [
        "edge_proxy_pct",
        "score_share_of_race",
        "dominance_score_v1",
        "runner_score",
        "score_probability_v1",
        "blended_probability_v1",
    ]:
        corr, effect = feature_correlation(v4_df, feature)
        corr_rows.append({"feature_name": feature, "correlation_with_winning": corr, "effect_size_abs_corr": effect})
    corr_df = pd.DataFrame(corr_rows).sort_values(["effect_size_abs_corr", "feature_name"], ascending=[False, True]).reset_index(drop=True)
    corr_df["predictive_rank_v1"] = range(1, len(corr_df) + 1)

    edge_corr = corr_df.loc[corr_df["feature_name"].eq("edge_proxy_pct"), "effect_size_abs_corr"].iloc[0]
    share_corr = corr_df.loc[corr_df["feature_name"].eq("score_share_of_race"), "effect_size_abs_corr"].iloc[0]
    dom_corr = corr_df.loc[corr_df["feature_name"].eq("dominance_score_v1"), "effect_size_abs_corr"].iloc[0]

    overlay_monotonic = monotonic_increasing(by_edge["win_rate"].tolist())
    share_monotonic = monotonic_increasing(by_share["win_rate"].tolist())
    dom_monotonic = monotonic_increasing(by_dom["win_rate"].tolist())

    edge_low = float(by_edge.loc[by_edge["edge_bucket_v1"].eq("0-10"), "win_rate"].iloc[0]) if "0-10" in set(by_edge["edge_bucket_v1"].astype(str)) else math.nan
    edge_high = float(by_edge.loc[by_edge["edge_bucket_v1"].eq("100+"), "win_rate"].iloc[0]) if "100+" in set(by_edge["edge_bucket_v1"].astype(str)) else math.nan
    overlay_increase = pd.notna(edge_low) and pd.notna(edge_high) and edge_high > edge_low

    if share_corr > edge_corr and dom_corr > edge_corr and (share_monotonic or dom_monotonic):
        conclusion = "HORSE_QUALITY_DRIVEN"
    elif edge_corr > share_corr and edge_corr > dom_corr and overlay_monotonic:
        conclusion = "OVERLAY_DRIVEN"
    else:
        conclusion = "HYBRID"

    summary_rows: list[dict[str, object]] = [
        {
            "section": "OVERVIEW",
            "bucket": "",
            "metric": "winning_rule_id",
            "value": WINNING_RULE_ID,
            "signals": int(len(v4_df)),
            "wins": int(v4_df["won"].sum()),
            "places": int(v4_df["placed"].sum()),
            "win_rate": safe_div(v4_df["won"].sum(), len(v4_df)),
            "place_rate": safe_div(v4_df["placed"].sum(), len(v4_df)),
            "notes": "Selected V4 historical universe",
        },
        {
            "section": "QUESTION",
            "bucket": "",
            "metric": "does_win_rate_increase_with_overlay_size",
            "value": "YES" if overlay_increase else "NO",
            "signals": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": math.nan,
            "place_rate": math.nan,
            "notes": f"low_edge_win_rate={edge_low:.4f} high_edge_win_rate={edge_high:.4f}" if pd.notna(edge_low) and pd.notna(edge_high) else "Edge comparison unavailable",
        },
        {
            "section": "QUESTION",
            "bucket": "",
            "metric": "does_score_share_beat_overlay_size",
            "value": "YES" if share_corr > edge_corr else "NO",
            "signals": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": math.nan,
            "place_rate": math.nan,
            "notes": f"score_share_abs_corr={share_corr:.4f} edge_abs_corr={edge_corr:.4f}",
        },
        {
            "section": "QUESTION",
            "bucket": "",
            "metric": "does_dominance_beat_overlay_size",
            "value": "YES" if dom_corr > edge_corr else "NO",
            "signals": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": math.nan,
            "place_rate": math.nan,
            "notes": f"dominance_abs_corr={dom_corr:.4f} edge_abs_corr={edge_corr:.4f}",
        },
        {
            "section": "QUESTION",
            "bucket": "",
            "metric": "is_overlay_monotonic",
            "value": "YES" if overlay_monotonic else "NO",
            "signals": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": math.nan,
            "place_rate": math.nan,
            "notes": "edge_proxy buckets ascending",
        },
        {
            "section": "QUESTION",
            "bucket": "",
            "metric": "is_score_share_monotonic",
            "value": "YES" if share_monotonic else "NO",
            "signals": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": math.nan,
            "place_rate": math.nan,
            "notes": "Within-V4 score-share quintiles ascending",
        },
        {
            "section": "QUESTION",
            "bucket": "",
            "metric": "is_dominance_monotonic",
            "value": "YES" if dom_monotonic else "NO",
            "signals": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": math.nan,
            "place_rate": math.nan,
            "notes": "Within-V4 dominance quintiles ascending",
        },
        {
            "section": "QUESTION",
            "bucket": "",
            "metric": "final_conclusion",
            "value": conclusion,
            "signals": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": math.nan,
            "place_rate": math.nan,
            "notes": "Inside V4 selected universe",
        },
    ]

    for _, row in by_edge.iterrows():
        summary_rows.append(
            {
                "section": "EDGE_BUCKET",
                "bucket": str(row["edge_bucket_v1"]),
                "metric": "",
                "value": "",
                "signals": int(row["signals"]),
                "wins": int(row["wins"]),
                "places": int(row["places"]),
                "win_rate": row["win_rate"],
                "place_rate": row["place_rate"],
                "notes": f"avg_edge={row['avg_edge_proxy_pct']:.4f}" if pd.notna(row["avg_edge_proxy_pct"]) else "",
            }
        )

    for _, row in by_share.iterrows():
        summary_rows.append(
            {
                "section": "SCORE_SHARE_BUCKET",
                "bucket": str(row["score_share_quintile_v1"]),
                "metric": "",
                "value": "",
                "signals": int(row["signals"]),
                "wins": int(row["wins"]),
                "places": int(row["places"]),
                "win_rate": row["win_rate"],
                "place_rate": row["place_rate"],
                "notes": f"avg_score_share={row['avg_score_share']:.6f}" if pd.notna(row["avg_score_share"]) else "",
            }
        )

    for _, row in by_dom.iterrows():
        summary_rows.append(
            {
                "section": "DOMINANCE_BUCKET",
                "bucket": str(row["dominance_quintile_v1"]),
                "metric": "",
                "value": "",
                "signals": int(row["signals"]),
                "wins": int(row["wins"]),
                "places": int(row["places"]),
                "win_rate": row["win_rate"],
                "place_rate": row["place_rate"],
                "notes": f"avg_dominance={row['avg_dominance_score']:.4f}" if pd.notna(row["avg_dominance_score"]) else "",
            }
        )

    for _, row in corr_df.iterrows():
        summary_rows.append(
            {
                "section": "FEATURE_CORRELATION",
                "bucket": str(int(row["predictive_rank_v1"])),
                "metric": row["feature_name"],
                "value": row["effect_size_abs_corr"],
                "signals": math.nan,
                "wins": math.nan,
                "places": math.nan,
                "win_rate": math.nan,
                "place_rate": math.nan,
                "notes": f"corr={row['correlation_with_winning']:.6f}" if pd.notna(row["correlation_with_winning"]) else "corr=NA",
            }
        )

    return v4_df, pd.DataFrame(summary_rows)


def main() -> None:
    rule_row = pick_rule_row()
    v4_df = build_v4_universe(rule_row)
    v4_df, summary_df = build_summary(v4_df)

    v4_df.to_csv(AUDIT_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)

    print(f"Wrote {AUDIT_OUT}")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
