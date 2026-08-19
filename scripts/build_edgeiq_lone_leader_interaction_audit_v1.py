from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_FILE = os.path.join(DATA, "edgeiq_lone_leader_market_audit_v1.csv")

OUT = os.path.join(DATA, "edgeiq_lone_leader_interaction_audit_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_lone_leader_interaction_audit_v1_summary.csv")
OUT_TOP = os.path.join(DATA, "edgeiq_lone_leader_interaction_audit_v1_top_pockets.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_lone_leader_interaction_audit_v1_verdict.csv")


def safe_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


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
    valid = df[df["sp_valid_bool"]].copy()

    wins_all = int(df["won_num"].sum()) if len(df) else 0
    strike_all = pct(df["won_num"].mean()) if len(df) else np.nan

    if len(valid):
        wins = float(valid["won_num"].sum())
        bets = float(len(valid))
        profit = float(valid["profit_1u"].sum())
        expected = float(valid["expected_win_prob_sp"].sum())

        roi = round((profit / bets) * 100.0, 2) if bets else np.nan
        ae = round(wins / expected, 3) if expected > 0 else np.nan
        avg_sp = round(float(valid["sp_num_v1"].mean()), 3)
        med_sp = round(float(valid["sp_num_v1"].median()), 3)
    else:
        profit = np.nan
        roi = np.nan
        ae = np.nan
        avg_sp = np.nan
        med_sp = np.nan

    return {
        "segment": segment,
        "signals": int(len(df)),
        "wins_all": wins_all,
        "strike_all_pct": strike_all,
        "priced_signals": int(len(valid)),
        "avg_sp": avg_sp,
        "median_sp": med_sp,
        "profit_1u": round(profit, 3) if pd.notna(profit) else np.nan,
        "roi_pct": roi,
        "ae_ratio": ae,
        "avg_score_share": round(float(df["score_share_num"].mean()), 6) if len(df) else np.nan,
        "avg_dominance": round(float(df["dominance_num"].mean()), 3) if len(df) else np.nan,
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3) if len(df) else np.nan,
        "avg_field_size": round(float(df["field_size_num"].mean()), 3) if len(df) else np.nan,
    }


def group_report(df, cols, label):
    rows = []

    for keys, g in df.groupby(cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        segment = label + "__" + "__".join([safe_str(k) for k in keys])
        row = summarise(g, segment)

        for c, k in zip(cols, keys):
            row[c] = k

        rows.append(row)

    return pd.DataFrame(rows)


def main():
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(IN_FILE)

    df = pd.read_csv(IN_FILE, low_memory=False)

    df["lone_leader_bool"] = df["lone_leader_crawl_v1"].map(to_bool)
    df["won_num"] = num(df["won"]).fillna(0)
    df["placed_num"] = num(df["placed"]).fillna(0)
    df["sp_num_v1"] = num(df["sp_num_v1"])
    df["sp_valid_bool"] = df["sp_valid_v1"].map(to_bool) & df["sp_num_v1"].notna() & (df["sp_num_v1"] > 1)

    df["score_share_num"] = num(df["score_share_of_race"])
    df["dominance_num"] = num(df["dominance_score_v1"])
    df["edge_proxy_num"] = num(df["edge_proxy_pct"])
    df["field_size_num"] = num(df["field_size"])

    df["profit_1u"] = np.where(
        df["sp_valid_bool"],
        np.where(df["won_num"] == 1, df["sp_num_v1"] - 1.0, -1.0),
        np.nan,
    )
    df["expected_win_prob_sp"] = np.where(df["sp_valid_bool"], 1.0 / df["sp_num_v1"], np.nan)

    df["year"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year.astype("Int64").astype(str)

    lone = df[df["lone_leader_bool"]].copy()
    other = df[~df["lone_leader_bool"]].copy()

    base_summary = pd.DataFrame([
        summarise(df, "BASE_V4"),
        summarise(lone, "LONE_LEADER_ALL"),
        summarise(other, "OTHER_V4_ALL"),
    ])

    reports = []

    for cols, label in [
        (["year"], "YEAR"),
        (["trust_profile_v1"], "TRUST"),
        (["field_size_bucket_v1"], "FIELD"),
        (["trust_profile_v1", "field_size_bucket_v1"], "TRUST_FIELD"),
        (["year", "trust_profile_v1"], "YEAR_TRUST"),
        (["year", "field_size_bucket_v1"], "YEAR_FIELD"),
        (["track"], "TRACK"),
    ]:
        rep = group_report(lone, cols, label)
        rep["report_type"] = label
        reports.append(rep)

    all_report = pd.concat(reports, ignore_index=True) if reports else pd.DataFrame()

    top = all_report[
        (all_report["signals"] >= 10) &
        (all_report["priced_signals"] >= 5)
    ].copy()

    top["quality_score_v1"] = (
        top["strike_all_pct"].fillna(0) * 0.45
        + top["roi_pct"].fillna(0) * 0.25
        + top["ae_ratio"].fillna(0) * 20.0
        + np.minimum(top["signals"].fillna(0), 50) * 0.20
    ).round(3)

    top = top.sort_values(
        ["quality_score_v1", "strike_all_pct", "signals"],
        ascending=[False, False, False],
    )

    best = top.iloc[0] if len(top) else None

    if best is not None:
        best_segment = best["segment"]
        best_signals = int(best["signals"])
        best_strike = best["strike_all_pct"]
        best_roi = best["roi_pct"]
        best_ae = best["ae_ratio"]

        if best_signals >= 20 and pd.notna(best_strike) and best_strike >= 35:
            final = "LONE_LEADER_INTERACTION_POCKET_FOUND"
        elif best_signals >= 10 and pd.notna(best_strike) and best_strike >= 30:
            final = "LONE_LEADER_INTERACTION_POCKET_MODEST"
        else:
            final = "NO_CLEAR_INTERACTION_POCKET"
    else:
        best_segment = ""
        best_signals = 0
        best_strike = np.nan
        best_roi = np.nan
        best_ae = np.nan
        final = "NO_CLEAR_INTERACTION_POCKET"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_FILE},
        {"metric": "lone_leader_rows", "value": len(lone)},
        {"metric": "lone_leader_priced_rows", "value": int(lone["sp_valid_bool"].sum())},
        {"metric": "best_segment", "value": best_segment},
        {"metric": "best_segment_signals", "value": best_signals},
        {"metric": "best_segment_strike_pct", "value": best_strike},
        {"metric": "best_segment_roi_pct", "value": best_roi},
        {"metric": "best_segment_ae_ratio", "value": best_ae},
        {"metric": "final_conclusion", "value": final},
    ])

    df.to_csv(OUT, index=False)
    base_summary.to_csv(OUT_SUMMARY, index=False)
    top.to_csv(OUT_TOP, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[LONE_LEADER_INTERACTION_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_TOP}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
