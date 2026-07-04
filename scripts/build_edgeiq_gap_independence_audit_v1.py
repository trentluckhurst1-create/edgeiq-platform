from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

import build_edgeiq_execution_v4_replay_sweep_v1 as v4_sweep


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST_REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
GAP_ENGINE_PATH = DATA / "edgeiq_rank_gap_engine_v1.csv"
DOMINANCE_REFERENCE_PATH = DATA / "edgeiq_dominance_engine_v1.csv"
RULES_PATH = DATA / "edgeiq_execution_v4_replay_sweep_v1.csv"

AUDIT_OUT = DATA / "edgeiq_gap_independence_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_gap_independence_audit_v1_summary.csv"
MARGINAL_LIFT_OUT = DATA / "edgeiq_gap_independence_audit_v1_marginal_lift.csv"

WINNING_RULE_ID = "SHARE_VERY_HIGH|DOM_ELITE|RANK_LE_1|EDGE_GE_0|TRUST_ELITE_STRONG_ONLY"
GAP12_ORDER = ["ZERO_TO_2", "TWO_TO_5", "FIVE_TO_10", "TEN_PLUS", "UNKNOWN"]
GAP13_ORDER = ["ZERO_TO_5", "FIVE_TO_10", "TEN_TO_15", "FIFTEEN_PLUS", "UNKNOWN"]
MIN_GAP_SAMPLE = 300


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def pick_winning_rule() -> pd.Series:
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


def load_historical_replay_lookup() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "runner_score",
        "runner_rank",
        "finish_position",
        "won",
    ]
    df = pd.read_csv(HIST_REPLAY_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "horse"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
    for col in ["race_no", "runner_score", "runner_rank", "finish_position", "won"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["placed"] = df["finish_position"].le(3).fillna(False).astype(int)
    df["join_key_v1"] = v4_sweep.build_join_key(df)
    df["runner_key_v1"] = v4_sweep.build_runner_key(df)
    df["runner_rank"] = df["runner_rank"].fillna(999).astype(int)
    df["won"] = df["won"].fillna(0).astype(int)
    return df[
        [
            "runner_key_v1",
            "join_key_v1",
            "runner_score",
            "runner_rank",
            "finish_position",
            "won",
            "placed",
        ]
    ].copy()


def load_gap_context() -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "field_size",
        "winner_rank",
        "trust_band_v1",
        "gap_1_2_band",
        "gap_1_3_band",
    ]
    df = pd.read_csv(GAP_ENGINE_PATH, low_memory=False, usecols=usecols)
    for col in ["meeting_date", "track", "trust_band_v1", "gap_1_2_band", "gap_1_3_band"]:
        df[col] = df[col].fillna("").astype(str).map(clean_text)
        df[col] = df[col].replace("", "UNKNOWN")
    for col in ["race_no", "field_size", "winner_rank"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["join_key_v1"] = v4_sweep.build_join_key(df)
    df["winner_top3_v1"] = df["winner_rank"].le(3).fillna(False).astype(int)
    return df[
        [
            "join_key_v1",
            "field_size",
            "winner_rank",
            "winner_top3_v1",
            "trust_band_v1",
            "gap_1_2_band",
            "gap_1_3_band",
        ]
    ].drop_duplicates(subset=["join_key_v1"]).copy()


def load_dominance_reference() -> list[str]:
    if not DOMINANCE_REFERENCE_PATH.exists():
        return []
    try:
        ref = pd.read_csv(DOMINANCE_REFERENCE_PATH, low_memory=False, usecols=["dominance_band_v1"])
    except ValueError:
        return []
    values = [
        clean_text(value).upper()
        for value in ref["dominance_band_v1"].dropna().tolist()
        if clean_text(value) != ""
    ]
    return sorted(set(values))


def build_base_universe() -> pd.DataFrame:
    base_df = v4_sweep.enrich_overlay_universe()
    replay_lookup = load_historical_replay_lookup()
    gap_lookup = load_gap_context()
    load_dominance_reference()

    base_df = base_df.merge(
        replay_lookup,
        on="runner_key_v1",
        how="left",
        suffixes=("", "_hist"),
    )
    for col in ["runner_score", "runner_rank", "finish_position", "won", "placed"]:
        hist_col = f"{col}_hist"
        if hist_col in base_df.columns:
            base_df[col] = base_df[col].where(base_df[col].notna(), base_df[hist_col])

    base_df = base_df.merge(gap_lookup, on="join_key_v1", how="left", suffixes=("", "_gap"))
    base_df["winner_rank_v1"] = pd.to_numeric(base_df["winner_rank"], errors="coerce")
    base_df["winner_top3_v1"] = pd.to_numeric(base_df["winner_top3_v1"], errors="coerce").fillna(0).astype(int)
    base_df["gap_1_2_band"] = base_df["gap_1_2_band_gap"].fillna(base_df["gap_1_2_band"]).fillna("UNKNOWN")
    base_df["gap_1_3_band"] = base_df["gap_1_3_band_gap"].fillna(base_df["gap_1_3_band"]).fillna("UNKNOWN")
    base_df["trust_band_v1"] = base_df["trust_band_v1_gap"].fillna(base_df["trust_band_v1"]).fillna("UNKNOWN")
    base_df["field_size"] = pd.to_numeric(base_df["field_size"], errors="coerce").where(
        pd.to_numeric(base_df["field_size"], errors="coerce").notna(),
        pd.to_numeric(base_df["field_size_gap"], errors="coerce"),
    )

    base_df["runner_rank"] = pd.to_numeric(base_df["runner_rank"], errors="coerce").fillna(999).astype(int)
    base_df["runner_score"] = pd.to_numeric(base_df["runner_score"], errors="coerce")
    base_df["won"] = pd.to_numeric(base_df["won"], errors="coerce").fillna(0).astype(int)
    base_df["placed"] = pd.to_numeric(base_df["placed"], errors="coerce").fillna(0).astype(int)
    base_df["edge_proxy_pct"] = pd.to_numeric(base_df["edge_proxy_pct"], errors="coerce")
    base_df["dominance_score_v1"] = pd.to_numeric(base_df["dominance_score_v1"], errors="coerce")
    base_df["score_share_of_race"] = pd.to_numeric(base_df["score_share_of_race"], errors="coerce")

    base_df["base_rank1_trust_v1"] = base_df["runner_rank"].eq(1) & base_df["trust_profile_v1"].isin(["ELITE", "STRONG"])
    base_df["share_only_v1"] = base_df["base_rank1_trust_v1"] & base_df["score_share_band_v1"].eq("VERY_HIGH")
    base_df["dom_only_v1"] = base_df["base_rank1_trust_v1"] & base_df["dominance_band_v1"].eq("ELITE")
    base_df["base_v4_v1"] = base_df["share_only_v1"] & base_df["dom_only_v1"]
    return base_df.copy()


def summarize_gap(df: pd.DataFrame, subset_name: str, gap_col: str, order: list[str]) -> pd.DataFrame:
    grouped = (
        df.groupby(gap_col, dropna=False)
        .agg(
            signals=("runner_key_v1", "size"),
            races=("join_key_v1", "nunique"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_edge_proxy_pct=("edge_proxy_pct", "mean"),
            avg_score_share=("score_share_of_race", "mean"),
            avg_dominance_score=("dominance_score_v1", "mean"),
        )
        .reset_index()
    )
    grouped[gap_col] = grouped[gap_col].fillna("UNKNOWN").astype(str).map(clean_text)
    grouped["win_rate"] = grouped.apply(lambda row: safe_div(row["wins"], row["signals"]), axis=1)
    grouped["place_rate"] = grouped.apply(lambda row: safe_div(row["places"], row["signals"]), axis=1)
    grouped["subset_name_v1"] = subset_name
    grouped["gap_dimension_v1"] = gap_col
    grouped["eligible_ge_300_v1"] = grouped["signals"].ge(MIN_GAP_SAMPLE)

    present = set(grouped[gap_col].tolist())
    missing_rows = []
    for label in order:
        if label not in present:
            missing_rows.append(
                {
                    gap_col: label,
                    "signals": 0,
                    "races": 0,
                    "wins": 0,
                    "places": 0,
                    "avg_edge_proxy_pct": math.nan,
                    "avg_score_share": math.nan,
                    "avg_dominance_score": math.nan,
                    "win_rate": math.nan,
                    "place_rate": math.nan,
                    "subset_name_v1": subset_name,
                    "gap_dimension_v1": gap_col,
                    "eligible_ge_300_v1": False,
                }
            )
    if missing_rows:
        grouped = pd.concat([grouped, pd.DataFrame(missing_rows)], ignore_index=True)

    grouped[gap_col] = pd.Categorical(grouped[gap_col], categories=order, ordered=True)
    grouped = grouped.sort_values(gap_col).reset_index(drop=True)
    return grouped.copy()


def select_best_gap_band(df: pd.DataFrame, gap_col: str) -> str:
    grouped = summarize_gap(df, "BASE_V4", gap_col, GAP12_ORDER if gap_col == "gap_1_2_band" else GAP13_ORDER)
    eligible = grouped[grouped["eligible_ge_300_v1"] & grouped["win_rate"].notna()].copy()
    if eligible.empty:
        eligible = grouped[grouped["signals"].gt(0) & grouped["win_rate"].notna()].copy()
    if eligible.empty:
        return "UNKNOWN"
    eligible = eligible.sort_values(["win_rate", "signals"], ascending=[False, False]).reset_index(drop=True)
    return str(eligible.iloc[0][gap_col])


def model_metrics(df: pd.DataFrame, model_id: str, selected_gap12: str, selected_gap13: str) -> dict[str, object]:
    race_level = df.sort_values(["join_key_v1", "runner_rank", "runner_score"], ascending=[True, True, False]).drop_duplicates("join_key_v1")
    return {
        "model_id": model_id,
        "selected_gap12_band_v1": selected_gap12,
        "selected_gap13_band_v1": selected_gap13,
        "signals": int(len(df)),
        "races": int(race_level["join_key_v1"].nunique()),
        "wins": int(df["won"].sum()),
        "places": int(df["placed"].sum()),
        "win_rate": safe_div(df["won"].sum(), len(df)),
        "place_rate": safe_div(df["placed"].sum(), len(df)),
        "winner_top3": float(race_level["winner_top3_v1"].mean()) if not race_level.empty else math.nan,
        "avg_winner_rank": float(race_level["winner_rank_v1"].mean()) if not race_level.empty else math.nan,
    }


def build_additive_models(v4_df: pd.DataFrame, gap12_band: str, gap13_band: str) -> pd.DataFrame:
    base_df = v4_df.copy()
    gap12_df = v4_df[v4_df["gap_1_2_band"].eq(gap12_band)].copy()
    gap13_df = v4_df[v4_df["gap_1_3_band"].eq(gap13_band)].copy()
    both_df = v4_df[v4_df["gap_1_2_band"].eq(gap12_band) & v4_df["gap_1_3_band"].eq(gap13_band)].copy()

    rows = [
        model_metrics(base_df, "BASE_V4", gap12_band, gap13_band),
        model_metrics(gap12_df, "BASE_V4_PLUS_GAP12", gap12_band, gap13_band),
        model_metrics(gap13_df, "BASE_V4_PLUS_GAP13", gap12_band, gap13_band),
        model_metrics(both_df, "BASE_V4_PLUS_BOTH_GAPS", gap12_band, gap13_band),
    ]
    table = pd.DataFrame(rows)
    base_win_rate = float(table.loc[table["model_id"].eq("BASE_V4"), "win_rate"].iloc[0])
    base_place_rate = float(table.loc[table["model_id"].eq("BASE_V4"), "place_rate"].iloc[0])
    base_top3 = float(table.loc[table["model_id"].eq("BASE_V4"), "winner_top3"].iloc[0])
    base_avg_rank = float(table.loc[table["model_id"].eq("BASE_V4"), "avg_winner_rank"].iloc[0])

    table["marginal_lift_win_rate"] = table["win_rate"] - base_win_rate
    table["marginal_lift_win_rate_points"] = table["marginal_lift_win_rate"] * 100.0
    table["marginal_lift_place_rate"] = table["place_rate"] - base_place_rate
    table["marginal_lift_winner_top3"] = table["winner_top3"] - base_top3
    table["marginal_lift_avg_winner_rank"] = base_avg_rank - table["avg_winner_rank"]
    return table.copy()


def build_summary(
    base_df: pd.DataFrame,
    share_df: pd.DataFrame,
    dom_df: pd.DataFrame,
    v4_df: pd.DataFrame,
    additive_df: pd.DataFrame,
    gap12_v4: pd.DataFrame,
    gap13_v4: pd.DataFrame,
    gap12_share: pd.DataFrame,
    gap13_share: pd.DataFrame,
    gap12_dom: pd.DataFrame,
    gap13_dom: pd.DataFrame,
) -> pd.DataFrame:
    best_gap12 = str(additive_df.iloc[0]["selected_gap12_band_v1"])
    best_gap13 = str(additive_df.iloc[0]["selected_gap13_band_v1"])

    gap12_lift_points = float(additive_df.loc[additive_df["model_id"].eq("BASE_V4_PLUS_GAP12"), "marginal_lift_win_rate_points"].iloc[0])
    gap13_lift_points = float(additive_df.loc[additive_df["model_id"].eq("BASE_V4_PLUS_GAP13"), "marginal_lift_win_rate_points"].iloc[0])
    both_lift_points = float(additive_df.loc[additive_df["model_id"].eq("BASE_V4_PLUS_BOTH_GAPS"), "marginal_lift_win_rate_points"].iloc[0])

    max_lift = max(gap12_lift_points, gap13_lift_points, both_lift_points)
    conclusion = "GAP_ADDS_NEW_INFORMATION" if max_lift >= 1.0 else "GAP_ALREADY_CAPTURED"

    overlay_summary_rows = [
        {
            "section": "OVERVIEW",
            "subset_name_v1": "BASE_RANK1_TRUST",
            "gap_dimension_v1": "",
            "gap_band_v1": "",
            "signals": int(len(base_df)),
            "races": int(base_df["join_key_v1"].nunique()),
            "wins": int(base_df["won"].sum()),
            "places": int(base_df["placed"].sum()),
            "win_rate": safe_div(base_df["won"].sum(), len(base_df)),
            "place_rate": safe_div(base_df["placed"].sum(), len(base_df)),
            "notes": "Positive overlay + rank1 + trust profile ELITE/STRONG",
        },
        {
            "section": "OVERVIEW",
            "subset_name_v1": "VERY_HIGH_SCORE_SHARE",
            "gap_dimension_v1": "",
            "gap_band_v1": "",
            "signals": int(len(share_df)),
            "races": int(share_df["join_key_v1"].nunique()),
            "wins": int(share_df["won"].sum()),
            "places": int(share_df["placed"].sum()),
            "win_rate": safe_div(share_df["won"].sum(), len(share_df)),
            "place_rate": safe_div(share_df["placed"].sum(), len(share_df)),
            "notes": "Base rank1-trust universe plus VERY_HIGH score share",
        },
        {
            "section": "OVERVIEW",
            "subset_name_v1": "ELITE_DOMINANCE",
            "gap_dimension_v1": "",
            "gap_band_v1": "",
            "signals": int(len(dom_df)),
            "races": int(dom_df["join_key_v1"].nunique()),
            "wins": int(dom_df["won"].sum()),
            "places": int(dom_df["placed"].sum()),
            "win_rate": safe_div(dom_df["won"].sum(), len(dom_df)),
            "place_rate": safe_div(dom_df["placed"].sum(), len(dom_df)),
            "notes": "Base rank1-trust universe plus ELITE dominance",
        },
        {
            "section": "OVERVIEW",
            "subset_name_v1": "BASE_V4",
            "gap_dimension_v1": "",
            "gap_band_v1": "",
            "signals": int(len(v4_df)),
            "races": int(v4_df["join_key_v1"].nunique()),
            "wins": int(v4_df["won"].sum()),
            "places": int(v4_df["placed"].sum()),
            "win_rate": safe_div(v4_df["won"].sum(), len(v4_df)),
            "place_rate": safe_div(v4_df["placed"].sum(), len(v4_df)),
            "notes": "Winning V4 rule universe",
        },
    ]

    gap_tables = [
        gap12_v4.assign(section="GAP_BAND", gap_band_v1=gap12_v4["gap_1_2_band"].astype(str)),
        gap13_v4.assign(section="GAP_BAND", gap_band_v1=gap13_v4["gap_1_3_band"].astype(str)),
        gap12_share.assign(section="GAP_BAND", gap_band_v1=gap12_share["gap_1_2_band"].astype(str)),
        gap13_share.assign(section="GAP_BAND", gap_band_v1=gap13_share["gap_1_3_band"].astype(str)),
        gap12_dom.assign(section="GAP_BAND", gap_band_v1=gap12_dom["gap_1_2_band"].astype(str)),
        gap13_dom.assign(section="GAP_BAND", gap_band_v1=gap13_dom["gap_1_3_band"].astype(str)),
    ]

    gap_rows = []
    for table in gap_tables:
        for _, row in table.iterrows():
            gap_rows.append(
                {
                    "section": row["section"],
                    "subset_name_v1": row["subset_name_v1"],
                    "gap_dimension_v1": row["gap_dimension_v1"],
                    "gap_band_v1": row["gap_band_v1"],
                    "signals": int(row["signals"]),
                    "races": int(row["races"]),
                    "wins": int(row["wins"]),
                    "places": int(row["places"]),
                    "win_rate": row["win_rate"],
                    "place_rate": row["place_rate"],
                    "notes": f"eligible_ge_300={row['eligible_ge_300_v1']}",
                }
            )

    answer_rows = [
        {
            "section": "ANSWERS",
            "subset_name_v1": "",
            "gap_dimension_v1": "",
            "gap_band_v1": "best_gap12_band_v1",
            "signals": math.nan,
            "races": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": gap12_lift_points,
            "place_rate": math.nan,
            "notes": best_gap12,
        },
        {
            "section": "ANSWERS",
            "subset_name_v1": "",
            "gap_dimension_v1": "",
            "gap_band_v1": "best_gap13_band_v1",
            "signals": math.nan,
            "races": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": gap13_lift_points,
            "place_rate": math.nan,
            "notes": best_gap13,
        },
        {
            "section": "ANSWERS",
            "subset_name_v1": "",
            "gap_dimension_v1": "",
            "gap_band_v1": "gap12_marginal_lift_points",
            "signals": math.nan,
            "races": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": gap12_lift_points,
            "place_rate": math.nan,
            "notes": "BASE_V4_PLUS_GAP12 minus BASE_V4",
        },
        {
            "section": "ANSWERS",
            "subset_name_v1": "",
            "gap_dimension_v1": "",
            "gap_band_v1": "gap13_marginal_lift_points",
            "signals": math.nan,
            "races": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": gap13_lift_points,
            "place_rate": math.nan,
            "notes": "BASE_V4_PLUS_GAP13 minus BASE_V4",
        },
        {
            "section": "ANSWERS",
            "subset_name_v1": "",
            "gap_dimension_v1": "",
            "gap_band_v1": "both_gaps_marginal_lift_points",
            "signals": math.nan,
            "races": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": both_lift_points,
            "place_rate": math.nan,
            "notes": "BASE_V4_PLUS_BOTH_GAPS minus BASE_V4",
        },
        {
            "section": "ANSWERS",
            "subset_name_v1": "",
            "gap_dimension_v1": "",
            "gap_band_v1": "final_conclusion",
            "signals": math.nan,
            "races": math.nan,
            "wins": math.nan,
            "places": math.nan,
            "win_rate": max_lift,
            "place_rate": math.nan,
            "notes": conclusion,
        },
    ]

    return pd.DataFrame(overlay_summary_rows + gap_rows + answer_rows)


def main() -> None:
    rule_row = pick_winning_rule()
    base_universe_df = build_base_universe()

    base_rank1_trust_df = base_universe_df[base_universe_df["base_rank1_trust_v1"]].copy()
    share_only_df = base_universe_df[base_universe_df["share_only_v1"]].copy()
    dom_only_df = base_universe_df[base_universe_df["dom_only_v1"]].copy()
    v4_df = base_universe_df[base_universe_df["base_v4_v1"]].copy()

    gap12_v4 = summarize_gap(v4_df, "BASE_V4", "gap_1_2_band", GAP12_ORDER)
    gap13_v4 = summarize_gap(v4_df, "BASE_V4", "gap_1_3_band", GAP13_ORDER)
    gap12_share = summarize_gap(share_only_df, "VERY_HIGH_SCORE_SHARE", "gap_1_2_band", GAP12_ORDER)
    gap13_share = summarize_gap(share_only_df, "VERY_HIGH_SCORE_SHARE", "gap_1_3_band", GAP13_ORDER)
    gap12_dom = summarize_gap(dom_only_df, "ELITE_DOMINANCE", "gap_1_2_band", GAP12_ORDER)
    gap13_dom = summarize_gap(dom_only_df, "ELITE_DOMINANCE", "gap_1_3_band", GAP13_ORDER)

    best_gap12 = select_best_gap_band(v4_df, "gap_1_2_band")
    best_gap13 = select_best_gap_band(v4_df, "gap_1_3_band")
    additive_df = build_additive_models(v4_df, best_gap12, best_gap13)

    audit_df = base_universe_df.copy()
    audit_df["winning_rule_id_v1"] = clean_text(rule_row["rule_id"])
    audit_df["selected_gap12_band_v1"] = best_gap12
    audit_df["selected_gap13_band_v1"] = best_gap13
    audit_df["base_v4_plus_gap12_v1"] = audit_df["base_v4_v1"] & audit_df["gap_1_2_band"].eq(best_gap12)
    audit_df["base_v4_plus_gap13_v1"] = audit_df["base_v4_v1"] & audit_df["gap_1_3_band"].eq(best_gap13)
    audit_df["base_v4_plus_both_gaps_v1"] = audit_df["base_v4_v1"] & audit_df["gap_1_2_band"].eq(best_gap12) & audit_df["gap_1_3_band"].eq(best_gap13)

    summary_df = build_summary(
        base_df=base_rank1_trust_df,
        share_df=share_only_df,
        dom_df=dom_only_df,
        v4_df=v4_df,
        additive_df=additive_df,
        gap12_v4=gap12_v4,
        gap13_v4=gap13_v4,
        gap12_share=gap12_share,
        gap13_share=gap13_share,
        gap12_dom=gap12_dom,
        gap13_dom=gap13_dom,
    )

    audit_df.to_csv(AUDIT_OUT, index=False)
    summary_df.to_csv(SUMMARY_OUT, index=False)
    additive_df.to_csv(MARGINAL_LIFT_OUT, index=False)

    print(f"Wrote {AUDIT_OUT}")
    print(f"Wrote {SUMMARY_OUT}")
    print(f"Wrote {MARGINAL_LIFT_OUT}")


if __name__ == "__main__":
    main()
