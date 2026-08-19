from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_V4 = os.path.join(DATA, "edgeiq_v4_rejected_winner_audit_v1.csv")
IN_RELIABILITY = os.path.join(DATA, "edgeiq_race_reliability_v1.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_race_reliability_replay_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_race_reliability_replay_v1_summary.csv")
OUT_BY_BAND = os.path.join(DATA, "edgeiq_race_reliability_replay_v1_by_band.csv")
OUT_BY_TRUST = os.path.join(DATA, "edgeiq_race_reliability_replay_v1_by_trust.csv")
OUT_BY_FIELD = os.path.join(DATA, "edgeiq_race_reliability_replay_v1_by_field_size.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_race_reliability_replay_v1_verdict.csv")


def safe_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def clean_track(x):
    return (
        safe_str(x)
        .upper()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace(".", "")
        .replace("'", "")
        .replace("’", "")
    )


def clean_race_no(x):
    s = safe_str(x).upper().replace("R", "")
    try:
        return str(int(float(s)))
    except Exception:
        return s


def make_join_key(df, date_col="meeting_date", track_col="track", race_col="race_no"):
    return (
        df[date_col].astype(str).str.strip()
        + "|"
        + df[track_col].map(clean_track)
        + "|"
        + df[race_col].map(clean_race_no)
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
    if len(df) == 0:
        return {
            "segment": segment,
            "signals": 0,
            "races": 0,
            "wins": 0,
            "places": 0,
            "win_rate_pct": np.nan,
            "place_rate_pct": np.nan,
            "avg_score_share": np.nan,
            "avg_dominance": np.nan,
            "avg_edge_proxy_pct": np.nan,
            "avg_field_size": np.nan,
            "avg_race_reliability_score": np.nan,
        }

    return {
        "segment": segment,
        "signals": int(len(df)),
        "races": int(df["race_join_key"].nunique()),
        "wins": int(df["won_num"].sum()),
        "places": int(df["placed_num"].sum()),
        "win_rate_pct": pct(df["won_num"].mean()),
        "place_rate_pct": pct(df["placed_num"].mean()),
        "avg_score_share": round(float(df["score_share_num"].mean()), 6),
        "avg_dominance": round(float(df["dominance_num"].mean()), 3),
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3),
        "avg_field_size": round(float(df["field_size_num"].mean()), 3),
        "avg_race_reliability_score": round(float(df["race_reliability_score_num"].mean()), 3)
        if df["race_reliability_score_num"].notna().any()
        else np.nan,
    }


def compare_group(df, group_col, prefix):
    rows = []

    for group, g in df.groupby(group_col, dropna=False):
        row = summarise(g, f"{prefix}_{group}")
        row["group"] = group
        rows.append(row)

    return pd.DataFrame(rows)


def main():
    if not os.path.exists(IN_V4):
        raise FileNotFoundError(IN_V4)

    if not os.path.exists(IN_RELIABILITY):
        raise FileNotFoundError(IN_RELIABILITY)

    v4 = pd.read_csv(IN_V4, low_memory=False)
    rr = pd.read_csv(IN_RELIABILITY, low_memory=False)

    v4["race_join_key"] = make_join_key(v4)

    if "meeting_date" in rr.columns:
        rr_date_col = "meeting_date"
    elif "race_date" in rr.columns:
        rr_date_col = "race_date"
    else:
        raise ValueError("Race Reliability file missing meeting_date/race_date column")

    rr["race_join_key"] = make_join_key(rr, date_col=rr_date_col)

    band_col = None
    for c in [
        "race_reliability_band_v1",
        "environment_band_v2",
        "environment_band_v1",
        "race_environment_band_v1",
    ]:
        if c in rr.columns:
            band_col = c
            break

    if band_col is None:
        raise ValueError("Race Reliability file missing race_reliability_band_v1/environment band column")

    score_col = None
    for c in [
        "race_reliability_score_v1",
        "environment_score_v2",
        "environment_score_v1",
        "race_environment_score_v1",
    ]:
        if c in rr.columns:
            score_col = c
            break

    rr_keep = ["race_join_key", band_col]
    if score_col:
        rr_keep.append(score_col)

    extra_cols = [
        "race_reliability_reason_v1",
        "race_reliability_hint_v1",
        "race_reliability_label_v1",
        "environment_reason_v2",
        "environment_hint_v2",
    ]

    rr_keep += [c for c in extra_cols if c in rr.columns]
    rr2 = rr[rr_keep].drop_duplicates("race_join_key").copy()

    rr2 = rr2.rename(columns={
        band_col: "race_reliability_band_v1",
        score_col: "race_reliability_score_v1" if score_col else score_col,
    })

    merged = v4.merge(rr2, on="race_join_key", how="left")

    merged["accepted_signal_bool"] = merged["accepted_signal_v4"].map(to_bool)
    merged["won_num"] = num(merged["won"]).fillna(0)
    merged["placed_num"] = num(merged["placed"]).fillna(0)

    merged["score_share_num"] = num(merged.get("score_share_of_race"))
    merged["dominance_num"] = num(merged.get("dominance_score_v1"))
    merged["edge_proxy_num"] = num(merged.get("edge_proxy_pct"))
    merged["field_size_num"] = num(merged.get("field_size"))
    merged["race_reliability_score_num"] = num(merged.get("race_reliability_score_v1"))

    merged["race_reliability_band_v1"] = merged["race_reliability_band_v1"].fillna("UNMATCHED")

    v4_signals = merged[merged["accepted_signal_bool"]].copy()

    base = summarise(v4_signals, "BASE_V4")
    matched = summarise(
        v4_signals[v4_signals["race_reliability_band_v1"] != "UNMATCHED"],
        "BASE_V4_MATCHED_RACE_RELIABILITY",
    )

    positive_plus = summarise(
        v4_signals[v4_signals["race_reliability_band_v1"].isin(["POSITIVE", "ELITE"])],
        "BASE_V4_POSITIVE_PLUS_RELIABILITY",
    )

    elite_only = summarise(
        v4_signals[v4_signals["race_reliability_band_v1"] == "ELITE"],
        "BASE_V4_ELITE_RELIABILITY_ONLY",
    )

    poor_negative_removed = summarise(
        v4_signals[~v4_signals["race_reliability_band_v1"].isin(["POOR", "NEGATIVE"])],
        "BASE_V4_REMOVE_POOR_NEGATIVE_RELIABILITY",
    )

    poor_negative_only = summarise(
        v4_signals[v4_signals["race_reliability_band_v1"].isin(["POOR", "NEGATIVE"])],
        "BASE_V4_POOR_NEGATIVE_RELIABILITY_ONLY",
    )

    summary = pd.DataFrame([
        base,
        matched,
        positive_plus,
        elite_only,
        poor_negative_removed,
        poor_negative_only,
    ])

    base_wr = float(base["win_rate_pct"]) if pd.notna(base["win_rate_pct"]) else np.nan

    summary["lift_vs_base_points"] = summary["win_rate_pct"].apply(
        lambda x: round(float(x) - base_wr, 3)
        if pd.notna(x) and pd.notna(base_wr)
        else np.nan
    )

    by_band = compare_group(v4_signals, "race_reliability_band_v1", "RELIABILITY_BAND")
    by_band["lift_vs_base_points"] = by_band["win_rate_pct"].apply(
        lambda x: round(float(x) - base_wr, 3)
        if pd.notna(x) and pd.notna(base_wr)
        else np.nan
    )

    by_trust = compare_group(v4_signals, "trust_profile_v1", "TRUST")
    by_field = compare_group(v4_signals, "field_size_bucket_v1", "FIELD")

    matched_rate = (
        round(float((v4_signals["race_reliability_band_v1"] != "UNMATCHED").mean()) * 100.0, 2)
        if len(v4_signals)
        else 0
    )

    elite_row = summary[summary["segment"] == "BASE_V4_ELITE_RELIABILITY_ONLY"]
    pos_row = summary[summary["segment"] == "BASE_V4_POSITIVE_PLUS_RELIABILITY"]

    elite_lift = float(elite_row["lift_vs_base_points"].iloc[0]) if len(elite_row) else np.nan
    pos_lift = float(pos_row["lift_vs_base_points"].iloc[0]) if len(pos_row) else np.nan

    if pd.notna(elite_lift) and elite_lift >= 2.0:
        final = "RACE_RELIABILITY_ADDS_STRONG_INFORMATION"
    elif pd.notna(pos_lift) and pos_lift >= 1.0:
        final = "RACE_RELIABILITY_ADDS_MODEST_INFORMATION"
    elif matched_rate < 70:
        final = "RACE_RELIABILITY_REPLAY_INSUFFICIENT_MATCH_COVERAGE"
    else:
        final = "RACE_RELIABILITY_NOT_PROVEN_AS_FILTER"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "v4_rows_loaded", "value": len(v4)},
        {"metric": "race_reliability_rows_loaded", "value": len(rr)},
        {"metric": "v4_accepted_signals", "value": len(v4_signals)},
        {"metric": "matched_v4_signals", "value": int((v4_signals["race_reliability_band_v1"] != "UNMATCHED").sum())},
        {"metric": "unmatched_v4_signals", "value": int((v4_signals["race_reliability_band_v1"] == "UNMATCHED").sum())},
        {"metric": "match_rate_pct", "value": matched_rate},
        {"metric": "base_v4_win_rate_pct", "value": base["win_rate_pct"]},
        {"metric": "positive_plus_lift_points", "value": pos_lift},
        {"metric": "elite_lift_points", "value": elite_lift},
        {"metric": "final_conclusion", "value": final},
    ])

    detail_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "race_join_key",
        "runner_rank",
        "runner_score",
        "score_share_of_race",
        "score_share_band_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "field_size",
        "field_size_bucket_v1",
        "edge_proxy_pct",
        "accepted_signal_v4",
        "won",
        "placed",
        "finish_position",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "race_reliability_reason_v1",
        "race_reliability_hint_v1",
        "race_reliability_label_v1",
        "environment_reason_v2",
        "environment_hint_v2",
    ]

    detail_cols = [c for c in detail_cols if c in merged.columns]

    merged[detail_cols].to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_band.to_csv(OUT_BY_BAND, index=False)
    by_trust.to_csv(OUT_BY_TRUST, index=False)
    by_field.to_csv(OUT_BY_FIELD, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[RACE_RELIABILITY_REPLAY_V1] COMPLETE")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_BAND}")
    print(f"wrote={OUT_BY_TRUST}")
    print(f"wrote={OUT_BY_FIELD}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
