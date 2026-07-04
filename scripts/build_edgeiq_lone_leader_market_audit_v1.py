from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_LONE = os.path.join(DATA, "edgeiq_lone_leader_independence_audit_v1.csv")
IN_MARKET = os.path.join(DATA, "edgeiq_replay_market_proxy_v1.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_lone_leader_market_audit_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_lone_leader_market_audit_v1_summary.csv")
OUT_BY_YEAR = os.path.join(DATA, "edgeiq_lone_leader_market_audit_v1_by_year.csv")
OUT_BY_TRUST = os.path.join(DATA, "edgeiq_lone_leader_market_audit_v1_by_trust.csv")
OUT_BY_FIELD = os.path.join(DATA, "edgeiq_lone_leader_market_audit_v1_by_field_size.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_lone_leader_market_audit_v1_verdict.csv")


def safe_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def norm_key(x):
    return (
        safe_str(x)
        .upper()
        .replace(" ", "")
        .replace("'", "")
        .replace("’", "")
        .replace("-", "")
        .replace("_", "")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
    )


def to_bool(x):
    if pd.isna(x):
        return False
    return str(x).strip().lower() in {"true", "1", "yes", "y"}


def num(x):
    return pd.to_numeric(x, errors="coerce")


def pct(x):
    if pd.isna(x):
        return np.nan
    return round(float(x) * 100.0, 2)


def summarise(df, segment):
    valid = df[df["sp_valid_v1"]].copy()

    if len(df) == 0:
        return {
            "segment": segment,
            "signals": 0,
            "priced_signals": 0,
            "wins": 0,
            "strike_rate_pct": np.nan,
            "avg_sp": np.nan,
            "median_sp": np.nan,
            "profit_1u": np.nan,
            "roi_pct": np.nan,
            "expected_wins": np.nan,
            "ae_ratio": np.nan,
            "avg_score_share": np.nan,
            "avg_dominance": np.nan,
            "avg_edge_proxy_pct": np.nan,
        }

    if len(valid) == 0:
        return {
            "segment": segment,
            "signals": int(len(df)),
            "priced_signals": 0,
            "wins": int(df["won_num"].sum()),
            "strike_rate_pct": pct(df["won_num"].mean()),
            "avg_sp": np.nan,
            "median_sp": np.nan,
            "profit_1u": np.nan,
            "roi_pct": np.nan,
            "expected_wins": np.nan,
            "ae_ratio": np.nan,
            "avg_score_share": round(float(df["score_share_num"].mean()), 6),
            "avg_dominance": round(float(df["dominance_num"].mean()), 3),
            "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3),
        }

    wins = float(valid["won_num"].sum())
    bets = float(len(valid))
    profit = float(valid["profit_1u"].sum())
    expected = float(valid["expected_win_prob_sp"].sum())

    return {
        "segment": segment,
        "signals": int(len(df)),
        "priced_signals": int(len(valid)),
        "wins": int(wins),
        "strike_rate_pct": pct(valid["won_num"].mean()),
        "avg_sp": round(float(valid["sp_num_v1"].mean()), 3),
        "median_sp": round(float(valid["sp_num_v1"].median()), 3),
        "profit_1u": round(profit, 3),
        "roi_pct": round((profit / bets) * 100.0, 2) if bets else np.nan,
        "expected_wins": round(expected, 3),
        "ae_ratio": round(wins / expected, 3) if expected > 0 else np.nan,
        "avg_score_share": round(float(valid["score_share_num"].mean()), 6),
        "avg_dominance": round(float(valid["dominance_num"].mean()), 3),
        "avg_edge_proxy_pct": round(float(valid["edge_proxy_num"].mean()), 3),
    }


def compare(df, group_col, prefix):
    rows = []

    for group, g in df.groupby(group_col, dropna=False):
        lone = g[g["lone_leader_bool"]].copy()
        other = g[~g["lone_leader_bool"]].copy()

        lone_row = summarise(lone, f"{prefix}_{group}__LONE_LEADER")
        other_row = summarise(other, f"{prefix}_{group}__OTHER_V4")

        lone_row["group"] = group
        other_row["group"] = group

        other_roi = other_row["roi_pct"]
        lone_roi = lone_row["roi_pct"]

        lone_row["roi_lift_vs_other_points"] = (
            round(float(lone_roi) - float(other_roi), 3)
            if pd.notna(lone_roi) and pd.notna(other_roi)
            else np.nan
        )

        other_row["roi_lift_vs_other_points"] = 0

        rows.append(lone_row)
        rows.append(other_row)

    return pd.DataFrame(rows)


def main():
    if not os.path.exists(IN_LONE):
        raise FileNotFoundError(IN_LONE)

    if not os.path.exists(IN_MARKET):
        raise FileNotFoundError(IN_MARKET)

    lone = pd.read_csv(IN_LONE, low_memory=False)
    market = pd.read_csv(IN_MARKET, low_memory=False)

    lone["horse_key_join"] = lone["horse"].map(norm_key)
    market["horse_key_join"] = market["horse"].map(norm_key)

    lone["race_key_join"] = lone["race_key"].astype(str)
    market["race_key_join"] = market["race_key"].astype(str)

    market_keep = [
        "race_key_join",
        "horse_key_join",
        "sp",
        "sp_settled",
        "sp_num_settled",
        "biased_sp_valid",
        "rank_empirical_fair_odds_v1",
        "rank_biased_avg_sp_v1",
        "rank_implied_edge_vs_biased_sp_v1",
        "score_empirical_fair_odds_v1",
        "score_biased_avg_sp_v1",
        "score_implied_edge_vs_biased_sp_v1",
    ]
    market_keep = [c for c in market_keep if c in market.columns]

    market2 = market[market_keep].drop_duplicates(["race_key_join", "horse_key_join"]).copy()

    df = lone.merge(
        market2,
        on=["race_key_join", "horse_key_join"],
        how="left",
    )

    df["accepted_signal_bool"] = df["accepted_signal_v4"].map(to_bool)
    df["lone_leader_bool"] = df["lone_leader_crawl_v1"].map(to_bool)

    df["won_num"] = num(df["won"]).fillna(0)
    df["placed_num"] = num(df["placed"]).fillna(0)
    df["score_share_num"] = num(df["score_share_of_race"])
    df["dominance_num"] = num(df["dominance_score_v1"])
    df["edge_proxy_num"] = num(df["edge_proxy_pct"])

    df["sp_num_v1"] = num(df["sp_num_settled"])
    if "biased_sp_valid" in df.columns:
        df["sp_valid_v1"] = df["biased_sp_valid"].map(to_bool) & df["sp_num_v1"].notna() & (df["sp_num_v1"] > 1)
    else:
        df["sp_valid_v1"] = df["sp_num_v1"].notna() & (df["sp_num_v1"] > 1)

    df["expected_win_prob_sp"] = np.where(df["sp_valid_v1"], 1.0 / df["sp_num_v1"], np.nan)
    df["profit_1u"] = np.where(
        df["sp_valid_v1"],
        np.where(df["won_num"] == 1, df["sp_num_v1"] - 1.0, -1.0),
        np.nan,
    )

    df["year"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year.astype("Int64").astype(str)

    v4 = df[df["accepted_signal_bool"]].copy()

    base = summarise(v4, "BASE_V4")
    lone_row = summarise(v4[v4["lone_leader_bool"]], "BASE_V4_LONE_LEADER")
    other_row = summarise(v4[~v4["lone_leader_bool"]], "BASE_V4_OTHER")

    summary = pd.DataFrame([base, lone_row, other_row])

    base_roi = float(base["roi_pct"]) if pd.notna(base["roi_pct"]) else np.nan
    other_roi = float(other_row["roi_pct"]) if pd.notna(other_row["roi_pct"]) else np.nan

    summary["roi_lift_vs_base_points"] = summary["roi_pct"].apply(
        lambda x: round(float(x) - base_roi, 3)
        if pd.notna(x) and pd.notna(base_roi)
        else np.nan
    )

    summary["roi_lift_vs_other_points"] = summary["roi_pct"].apply(
        lambda x: round(float(x) - other_roi, 3)
        if pd.notna(x) and pd.notna(other_roi)
        else np.nan
    )

    by_year = compare(v4, "year", "YEAR")
    by_trust = compare(v4, "trust_profile_v1", "TRUST")
    by_field = compare(v4, "field_size_bucket_v1", "FIELD")

    lone_summary = summary[summary["segment"] == "BASE_V4_LONE_LEADER"].iloc[0]

    lone_roi = float(lone_summary["roi_pct"]) if pd.notna(lone_summary["roi_pct"]) else np.nan
    lone_ae = float(lone_summary["ae_ratio"]) if pd.notna(lone_summary["ae_ratio"]) else np.nan
    lone_avg_sp = float(lone_summary["avg_sp"]) if pd.notna(lone_summary["avg_sp"]) else np.nan
    lone_priced = int(lone_summary["priced_signals"])

    if lone_priced < 50:
        final = "MARKET_AUDIT_INSUFFICIENT_PRICED_SAMPLE"
    elif pd.notna(lone_roi) and pd.notna(lone_ae) and lone_roi >= 10 and lone_ae >= 1.10:
        final = "LONE_LEADER_MARKET_EDGE_CONFIRMED"
    elif pd.notna(lone_roi) and pd.notna(lone_ae) and lone_roi > 0 and lone_ae > 1.00:
        final = "LONE_LEADER_MARKET_EDGE_MODEST"
    elif pd.notna(lone_roi) and pd.notna(lone_ae):
        final = "LONE_LEADER_MARKET_EDGE_NOT_PROVEN"
    else:
        final = "LONE_LEADER_MARKET_AUDIT_FAILED"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "lone_leader_signals", "value": int(v4["lone_leader_bool"].sum())},
        {"metric": "lone_leader_priced_signals", "value": lone_priced},
        {"metric": "lone_leader_avg_sp", "value": lone_avg_sp},
        {"metric": "lone_leader_roi_pct", "value": lone_roi},
        {"metric": "lone_leader_ae_ratio", "value": lone_ae},
        {"metric": "other_v4_roi_pct", "value": other_roi},
        {"metric": "final_conclusion", "value": final},
    ])

    detail_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "race_key",
        "runner_rank",
        "runner_score",
        "score_share_of_race",
        "dominance_score_v1",
        "trust_profile_v1",
        "field_size",
        "field_size_bucket_v1",
        "edge_proxy_pct",
        "won",
        "placed",
        "finish_position",
        "lone_leader_crawl_v1",
        "pace_role_v1",
        "race_shape_density_v1",
        "early_speed_density_v1",
        "sp_num_v1",
        "sp_valid_v1",
        "profit_1u",
        "expected_win_prob_sp",
        "rank_empirical_fair_odds_v1",
        "rank_biased_avg_sp_v1",
        "rank_implied_edge_vs_biased_sp_v1",
        "score_empirical_fair_odds_v1",
        "score_biased_avg_sp_v1",
        "score_implied_edge_vs_biased_sp_v1",
    ]
    detail_cols = [c for c in detail_cols if c in v4.columns]

    v4[detail_cols].to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_year.to_csv(OUT_BY_YEAR, index=False)
    by_trust.to_csv(OUT_BY_TRUST, index=False)
    by_field.to_csv(OUT_BY_FIELD, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[LONE_LEADER_MARKET_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_YEAR}")
    print(f"wrote={OUT_BY_TRUST}")
    print(f"wrote={OUT_BY_FIELD}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
