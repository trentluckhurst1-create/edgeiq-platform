from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

V4_FILE = os.path.join(DATA, "edgeiq_v4_rejected_winner_audit_v1.csv")
RACE_STRENGTH_FILE = os.path.join(DATA, "edgeiq_race_strength_v1.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_race_strength_independence_audit_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_race_strength_independence_audit_v1_summary.csv")
OUT_BAND = os.path.join(DATA, "edgeiq_race_strength_independence_audit_v1_by_strength_band.csv")
OUT_MARGINAL = os.path.join(DATA, "edgeiq_race_strength_independence_audit_v1_marginal_lift.csv")
OUT_COVERAGE = os.path.join(DATA, "edgeiq_race_strength_independence_audit_v1_coverage.csv")


STRENGTH_ORDER = {
    "VERY_WEAK": 1,
    "WEAK": 2,
    "SOLID": 3,
    "STRONG": 4,
    "VERY_STRONG": 5,
    "ELITE": 6,
}


def clean_track(x):
    if pd.isna(x):
        return ""
    return (
        str(x)
        .upper()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace(".", "")
        .replace("'", "")
        .replace("’", "")
        .strip()
    )


def clean_race_no(x):
    if pd.isna(x):
        return ""
    s = str(x).upper().replace("R", "").strip()
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


def to_bool(s):
    if pd.isna(s):
        return False
    return str(s).strip().lower() in {"true", "1", "yes", "y"}


def num(s):
    return pd.to_numeric(s, errors="coerce")


def pct(x):
    if pd.isna(x):
        return np.nan
    return round(float(x) * 100.0, 2)


def summarise(df, label):
    out = {
        "segment": label,
        "signals": int(len(df)),
        "races": int(df["race_join_key"].nunique()) if len(df) else 0,
        "win_rate_pct": pct(df["won_num"].mean()) if len(df) else np.nan,
        "place_rate_pct": pct(df["placed_num"].mean()) if len(df) else np.nan,
        "avg_field_size": round(float(df["field_size_num"].mean()), 3) if len(df) else np.nan,
        "avg_score_share": round(float(df["score_share_num"].mean()), 6) if len(df) else np.nan,
        "avg_dominance": round(float(df["dominance_num"].mean()), 3) if len(df) else np.nan,
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3) if len(df) else np.nan,
        "avg_race_strength_score": round(float(df["field_strength_score_num"].mean()), 3) if len(df) else np.nan,
        "avg_race_strength_percentile": round(float(df["field_strength_percentile_num"].mean()), 3) if len(df) else np.nan,
        "matched_race_strength_pct": pct(df["race_strength_band"].notna().mean()) if len(df) else np.nan,
    }
    return out


def main():
    if not os.path.exists(V4_FILE):
        raise FileNotFoundError(V4_FILE)

    if not os.path.exists(RACE_STRENGTH_FILE):
        raise FileNotFoundError(RACE_STRENGTH_FILE)

    v4 = pd.read_csv(V4_FILE, low_memory=False)
    rs = pd.read_csv(RACE_STRENGTH_FILE, low_memory=False)

    v4["race_join_key"] = make_join_key(v4)
    rs["race_join_key"] = make_join_key(rs)

    keep_rs = [
        "race_join_key",
        "race_key",
        "distance",
        "raceClass",
        "trackCondition",
        "field_size",
        "rated_field_size",
        "rating_reliability",
        "winner_rating",
        "top3_avg_rating",
        "field_avg_rating",
        "field_rating_stddev",
        "field_strength_score",
        "field_strength_percentile",
        "race_strength_band",
    ]

    rs = rs[[c for c in keep_rs if c in rs.columns]].drop_duplicates("race_join_key")

    merged = v4.merge(
        rs,
        on="race_join_key",
        how="left",
        suffixes=("", "_race_strength"),
    )

    merged["accepted_signal_bool"] = merged["accepted_signal_v4"].map(to_bool)
    merged["positive_overlay_bool"] = merged["positive_overlay_flag"].map(to_bool)

    merged["won_num"] = num(merged["won"]).fillna(0)
    merged["placed_num"] = num(merged["placed"]).fillna(0)
    merged["field_size_num"] = num(merged["field_size"])
    merged["score_share_num"] = num(merged["score_share_of_race"])
    merged["dominance_num"] = num(merged["dominance_score_v1"])
    merged["edge_proxy_num"] = num(merged["edge_proxy_pct"])
    merged["field_strength_score_num"] = num(merged.get("field_strength_score"))
    merged["field_strength_percentile_num"] = num(merged.get("field_strength_percentile"))

    merged["race_strength_band"] = merged["race_strength_band"].fillna("UNMATCHED")
    merged["race_strength_order"] = merged["race_strength_band"].map(STRENGTH_ORDER).fillna(0).astype(int)

    base_v4 = merged[merged["accepted_signal_bool"]].copy()
    solid_plus = base_v4[base_v4["race_strength_order"] >= STRENGTH_ORDER["SOLID"]].copy()
    strong_plus = base_v4[base_v4["race_strength_order"] >= STRENGTH_ORDER["STRONG"]].copy()
    very_strong_plus = base_v4[base_v4["race_strength_order"] >= STRENGTH_ORDER["VERY_STRONG"]].copy()
    elite_only = base_v4[base_v4["race_strength_order"] >= STRENGTH_ORDER["ELITE"]].copy()
    weak_removed = base_v4[~base_v4["race_strength_band"].isin(["VERY_WEAK", "WEAK"])].copy()
    unmatched_removed = base_v4[base_v4["race_strength_band"] != "UNMATCHED"].copy()

    segments = [
        summarise(base_v4, "BASE_V4"),
        summarise(unmatched_removed, "BASE_V4_MATCHED_RACE_STRENGTH_ONLY"),
        summarise(solid_plus, "BASE_V4_PLUS_SOLID_PLUS"),
        summarise(strong_plus, "BASE_V4_PLUS_STRONG_PLUS"),
        summarise(very_strong_plus, "BASE_V4_PLUS_VERY_STRONG_PLUS"),
        summarise(elite_only, "BASE_V4_PLUS_ELITE_ONLY"),
        summarise(weak_removed, "BASE_V4_WEAK_REMOVED"),
    ]

    summary = pd.DataFrame(segments)

    base_wr = float(summary.loc[summary["segment"] == "BASE_V4", "win_rate_pct"].iloc[0])

    marginal_rows = []
    for _, r in summary.iterrows():
        if r["segment"] == "BASE_V4":
            continue

        lift = round(float(r["win_rate_pct"]) - base_wr, 3) if pd.notna(r["win_rate_pct"]) else np.nan

        if pd.isna(lift):
            conclusion = "NO_RESULT"
        elif lift >= 1.0:
            conclusion = "RACE_STRENGTH_ADDS_INFORMATION"
        elif lift <= -1.0:
            conclusion = "RACE_STRENGTH_HURTS_OR_OVERFILTERS"
        else:
            conclusion = "RACE_STRENGTH_NOT_MEANINGFUL_AS_FILTER"

        marginal_rows.append({
            "test": r["segment"],
            "base_win_rate_pct": base_wr,
            "test_win_rate_pct": r["win_rate_pct"],
            "marginal_lift_points": lift,
            "base_signals": int(summary.loc[summary["segment"] == "BASE_V4", "signals"].iloc[0]),
            "test_signals": int(r["signals"]),
            "signal_retention_pct": round((float(r["signals"]) / float(summary.loc[summary["segment"] == "BASE_V4", "signals"].iloc[0])) * 100.0, 2) if float(summary.loc[summary["segment"] == "BASE_V4", "signals"].iloc[0]) else np.nan,
            "conclusion": conclusion,
        })

    marginal = pd.DataFrame(marginal_rows)

    band_rows = []
    for band, g in base_v4.groupby("race_strength_band", dropna=False):
        band_rows.append(summarise(g, f"V4_BY_RACE_STRENGTH_{band}"))

    band = pd.DataFrame(band_rows)
    band["race_strength_band"] = band["segment"].str.replace("V4_BY_RACE_STRENGTH_", "", regex=False)
    band["race_strength_order"] = band["race_strength_band"].map(STRENGTH_ORDER).fillna(0).astype(int)
    band = band.sort_values(["race_strength_order", "race_strength_band"])

    coverage = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "v4_rows_loaded", "value": len(v4)},
        {"metric": "race_strength_rows_loaded", "value": len(rs)},
        {"metric": "merged_rows", "value": len(merged)},
        {"metric": "base_v4_signals", "value": len(base_v4)},
        {"metric": "base_v4_matched_race_strength", "value": int((base_v4["race_strength_band"] != "UNMATCHED").sum())},
        {"metric": "base_v4_unmatched_race_strength", "value": int((base_v4["race_strength_band"] == "UNMATCHED").sum())},
        {"metric": "base_v4_match_rate_pct", "value": pct((base_v4["race_strength_band"] != "UNMATCHED").mean()) if len(base_v4) else np.nan},
        {"metric": "best_marginal_lift_points", "value": marginal["marginal_lift_points"].max() if len(marginal) else np.nan},
        {"metric": "final_conclusion", "value": "CHECK_MARGINAL_LIFT"},
    ])

    best_lift = marginal["marginal_lift_points"].max() if len(marginal) else np.nan
    if pd.notna(best_lift):
        coverage.loc[coverage["metric"] == "final_conclusion", "value"] = (
            "RACE_STRENGTH_ADDS_INFORMATION" if best_lift >= 1.0 else "RACE_STRENGTH_NOT_PRIMARY_FILTER"
        )

    detail_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "race_join_key",
        "race_key",
        "runner_rank",
        "runner_score",
        "score_share_of_race",
        "score_share_band_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "dominance_certainty_band",
        "trust_profile_v1",
        "trust_band_v1",
        "field_size",
        "field_size_bucket_v1",
        "edge_proxy_pct",
        "positive_overlay_flag",
        "accepted_signal_v4",
        "won",
        "placed",
        "finish_position",
        "race_strength_band",
        "field_strength_score",
        "field_strength_percentile",
        "rating_reliability",
        "rated_field_size",
        "winner_rating",
        "top3_avg_rating",
        "field_avg_rating",
        "field_rating_stddev",
    ]

    detail_cols = [c for c in detail_cols if c in merged.columns]

    merged[detail_cols].to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    band.to_csv(OUT_BAND, index=False)
    marginal.to_csv(OUT_MARGINAL, index=False)
    coverage.to_csv(OUT_COVERAGE, index=False)

    print("[RACE_STRENGTH_INDEPENDENCE_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BAND}")
    print(f"wrote={OUT_MARGINAL}")
    print(f"wrote={OUT_COVERAGE}")


if __name__ == "__main__":
    main()
