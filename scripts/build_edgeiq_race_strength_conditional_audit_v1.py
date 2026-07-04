from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_FILE = os.path.join(DATA, "edgeiq_race_strength_independence_audit_v1.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_race_strength_conditional_audit_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_race_strength_conditional_audit_v1_summary.csv")
OUT_BY_BAND = os.path.join(DATA, "edgeiq_race_strength_conditional_audit_v1_by_band.csv")
OUT_CONDITIONAL = os.path.join(DATA, "edgeiq_race_strength_conditional_audit_v1_conditional.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_race_strength_conditional_audit_v1_verdict.csv")


STRENGTH_ORDER = {
    "VERY_WEAK": 1,
    "WEAK": 2,
    "SOLID": 3,
    "STRONG": 4,
    "VERY_STRONG": 5,
    "ELITE": 6,
}


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


def summarize(df, segment):
    if len(df) == 0:
        return {
            "segment": segment,
            "signals": 0,
            "races": 0,
            "win_rate_pct": np.nan,
            "place_rate_pct": np.nan,
            "avg_share": np.nan,
            "avg_dominance": np.nan,
            "avg_field_size": np.nan,
            "avg_edge_proxy_pct": np.nan,
        }

    return {
        "segment": segment,
        "signals": int(len(df)),
        "races": int(df["race_join_key"].nunique()) if "race_join_key" in df.columns else int(len(df)),
        "win_rate_pct": pct(df["won_num"].mean()),
        "place_rate_pct": pct(df["placed_num"].mean()),
        "avg_share": round(float(df["score_share_num"].mean()), 6),
        "avg_dominance": round(float(df["dominance_num"].mean()), 3),
        "avg_field_size": round(float(df["field_size_num"].mean()), 3),
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3),
    }


def strength_group(band):
    band = str(band).strip().upper()
    if band == "UNMATCHED":
        return "UNMATCHED"
    if band in {"VERY_WEAK", "WEAK"}:
        return "LOW_DEPTH"
    if band in {"SOLID"}:
        return "MID_DEPTH"
    if band in {"STRONG", "VERY_STRONG", "ELITE"}:
        return "HIGH_DEPTH"
    return "UNKNOWN"


def main():
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(IN_FILE)

    df = pd.read_csv(IN_FILE, low_memory=False)

    df["accepted_signal_bool"] = df["accepted_signal_v4"].map(to_bool)
    df["won_num"] = num(df["won"]).fillna(0)
    df["placed_num"] = num(df["placed"]).fillna(0)
    df["score_share_num"] = num(df["score_share_of_race"])
    df["dominance_num"] = num(df["dominance_score_v1"])
    df["field_size_num"] = num(df["field_size"])
    df["edge_proxy_num"] = num(df["edge_proxy_pct"])

    df["race_strength_band"] = df["race_strength_band"].fillna("UNMATCHED")
    df["race_strength_order"] = df["race_strength_band"].map(STRENGTH_ORDER).fillna(0).astype(int)
    df["competitive_depth_group_v1"] = df["race_strength_band"].map(strength_group)

    v4 = df[df["accepted_signal_bool"]].copy()

    segments = []

    segments.append(summarize(v4, "BASE_V4"))

    for group in ["UNMATCHED", "LOW_DEPTH", "MID_DEPTH", "HIGH_DEPTH"]:
        segments.append(
            summarize(
                v4[v4["competitive_depth_group_v1"] == group],
                f"BASE_V4_DEPTH_{group}",
            )
        )

    very_high_share = v4[v4["score_share_band_v1"].astype(str).str.upper() == "VERY_HIGH"].copy()
    elite_dom = v4[v4["dominance_band_v1"].astype(str).str.upper() == "ELITE"].copy()
    elite_trust = v4[v4["trust_profile_v1"].astype(str).str.upper() == "ELITE"].copy()
    strong_trust = v4[v4["trust_profile_v1"].astype(str).str.upper() == "STRONG"].copy()
    le7 = v4[v4["field_size_bucket_v1"].astype(str).str.upper() == "LE_7"].copy()
    eight_to_ten = v4[v4["field_size_bucket_v1"].astype(str).str.upper() == "8_10"].copy()
    eleven_to_thirteen = v4[v4["field_size_bucket_v1"].astype(str).str.upper() == "11_13"].copy()

    condition_sets = [
        ("ALL_V4", v4),
        ("VERY_HIGH_SHARE_ONLY", very_high_share),
        ("ELITE_DOMINANCE_ONLY", elite_dom),
        ("ELITE_TRUST_ONLY", elite_trust),
        ("STRONG_TRUST_ONLY", strong_trust),
        ("FIELD_LE_7_ONLY", le7),
        ("FIELD_8_10_ONLY", eight_to_ten),
        ("FIELD_11_13_ONLY", eleven_to_thirteen),
    ]

    conditional_rows = []

    for condition_name, condition_df in condition_sets:
        base = summarize(condition_df, condition_name)
        base_wr = base["win_rate_pct"]

        for group in ["LOW_DEPTH", "MID_DEPTH", "HIGH_DEPTH", "UNMATCHED"]:
            g = condition_df[condition_df["competitive_depth_group_v1"] == group]
            row = summarize(g, f"{condition_name}__{group}")
            row["condition"] = condition_name
            row["depth_group"] = group
            row["condition_base_win_rate_pct"] = base_wr
            row["lift_vs_condition_base_points"] = (
                round(float(row["win_rate_pct"]) - float(base_wr), 3)
                if pd.notna(row["win_rate_pct"]) and pd.notna(base_wr)
                else np.nan
            )
            conditional_rows.append(row)

    by_band_rows = []
    for band, g in v4.groupby("race_strength_band", dropna=False):
        row = summarize(g, f"V4_BAND_{band}")
        row["race_strength_band"] = band
        row["race_strength_order"] = STRENGTH_ORDER.get(str(band), 0)
        row["competitive_depth_group_v1"] = strength_group(band)
        by_band_rows.append(row)

    by_band = pd.DataFrame(by_band_rows).sort_values(
        ["race_strength_order", "race_strength_band"]
    )

    summary = pd.DataFrame(segments)
    conditional = pd.DataFrame(conditional_rows)

    all_v4_low = conditional[
        (conditional["condition"] == "ALL_V4") &
        (conditional["depth_group"] == "LOW_DEPTH")
    ]

    all_v4_high = conditional[
        (conditional["condition"] == "ALL_V4") &
        (conditional["depth_group"] == "HIGH_DEPTH")
    ]

    vh_low = conditional[
        (conditional["condition"] == "VERY_HIGH_SHARE_ONLY") &
        (conditional["depth_group"] == "LOW_DEPTH")
    ]

    vh_high = conditional[
        (conditional["condition"] == "VERY_HIGH_SHARE_ONLY") &
        (conditional["depth_group"] == "HIGH_DEPTH")
    ]

    elite_dom_low = conditional[
        (conditional["condition"] == "ELITE_DOMINANCE_ONLY") &
        (conditional["depth_group"] == "LOW_DEPTH")
    ]

    elite_dom_high = conditional[
        (conditional["condition"] == "ELITE_DOMINANCE_ONLY") &
        (conditional["depth_group"] == "HIGH_DEPTH")
    ]

    def one_value(frame, col):
        if len(frame) == 0:
            return np.nan
        return frame[col].iloc[0]

    all_gap = (
        round(float(one_value(all_v4_low, "win_rate_pct")) - float(one_value(all_v4_high, "win_rate_pct")), 3)
        if pd.notna(one_value(all_v4_low, "win_rate_pct")) and pd.notna(one_value(all_v4_high, "win_rate_pct"))
        else np.nan
    )

    share_control_gap = (
        round(float(one_value(vh_low, "win_rate_pct")) - float(one_value(vh_high, "win_rate_pct")), 3)
        if pd.notna(one_value(vh_low, "win_rate_pct")) and pd.notna(one_value(vh_high, "win_rate_pct"))
        else np.nan
    )

    dom_control_gap = (
        round(float(one_value(elite_dom_low, "win_rate_pct")) - float(one_value(elite_dom_high, "win_rate_pct")), 3)
        if pd.notna(one_value(elite_dom_low, "win_rate_pct")) and pd.notna(one_value(elite_dom_high, "win_rate_pct"))
        else np.nan
    )

    if pd.notna(share_control_gap) and share_control_gap >= 1.0:
        final = "DEPTH_ADDS_INDEPENDENT_INFORMATION_AFTER_SHARE_CONTROL"
    elif pd.notna(dom_control_gap) and dom_control_gap >= 1.0:
        final = "DEPTH_ADDS_INDEPENDENT_INFORMATION_AFTER_DOMINANCE_CONTROL"
    elif pd.notna(all_gap) and all_gap >= 1.0:
        final = "DEPTH_EFFECT_MOSTLY_EXPLAINED_BY_SHARE_DOMINANCE"
    else:
        final = "DEPTH_NOT_ACTIONABLE"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_FILE},
        {"metric": "base_v4_signals", "value": len(v4)},
        {"metric": "all_v4_low_depth_minus_high_depth_win_points", "value": all_gap},
        {"metric": "very_high_share_low_depth_minus_high_depth_win_points", "value": share_control_gap},
        {"metric": "elite_dominance_low_depth_minus_high_depth_win_points", "value": dom_control_gap},
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
        "race_strength_band",
        "competitive_depth_group_v1",
        "field_strength_score",
        "field_strength_percentile",
    ]
    detail_cols = [c for c in detail_cols if c in v4.columns]

    v4[detail_cols].to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_band.to_csv(OUT_BY_BAND, index=False)
    conditional.to_csv(OUT_CONDITIONAL, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[RACE_STRENGTH_CONDITIONAL_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_BAND}")
    print(f"wrote={OUT_CONDITIONAL}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
