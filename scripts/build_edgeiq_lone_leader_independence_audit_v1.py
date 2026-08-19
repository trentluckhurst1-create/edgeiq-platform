from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_FILE = os.path.join(DATA, "edgeiq_pace_advantage_replay_v1.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_lone_leader_independence_audit_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_lone_leader_independence_audit_v1_summary.csv")
OUT_BY_TRUST = os.path.join(DATA, "edgeiq_lone_leader_independence_audit_v1_by_trust.csv")
OUT_BY_FIELD = os.path.join(DATA, "edgeiq_lone_leader_independence_audit_v1_by_field_size.csv")
OUT_BY_SHARE = os.path.join(DATA, "edgeiq_lone_leader_independence_audit_v1_by_share_bucket.csv")
OUT_BY_DOM = os.path.join(DATA, "edgeiq_lone_leader_independence_audit_v1_by_dominance_bucket.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_lone_leader_independence_audit_v1_verdict.csv")


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


def share_micro_bucket(x):
    try:
        v = float(x)
    except Exception:
        return "UNKNOWN"

    if v >= 0.30:
        return "SHARE_30_PLUS"
    if v >= 0.25:
        return "SHARE_25_30"
    if v >= 0.20:
        return "SHARE_20_25"
    if v >= 0.15:
        return "SHARE_15_20"
    return "SHARE_LT_15"


def dominance_micro_bucket(x):
    try:
        v = float(x)
    except Exception:
        return "UNKNOWN"

    if v >= 98:
        return "DOM_98_PLUS"
    if v >= 96:
        return "DOM_96_98"
    if v >= 94:
        return "DOM_94_96"
    if v >= 92:
        return "DOM_92_94"
    return "DOM_LT_92"


def summarize(df, segment):
    if len(df) == 0:
        return {
            "segment": segment,
            "signals": 0,
            "races": 0,
            "win_rate_pct": np.nan,
            "place_rate_pct": np.nan,
            "avg_score_share": np.nan,
            "avg_dominance": np.nan,
            "avg_edge_proxy_pct": np.nan,
            "avg_field_size": np.nan,
            "avg_early_speed_density": np.nan,
        }

    race_col = "race_key" if "race_key" in df.columns else "join_key_v1"

    return {
        "segment": segment,
        "signals": int(len(df)),
        "races": int(df[race_col].nunique()),
        "win_rate_pct": pct(df["won_num"].mean()),
        "place_rate_pct": pct(df["placed_num"].mean()),
        "avg_score_share": round(float(df["score_share_num"].mean()), 6),
        "avg_dominance": round(float(df["dominance_num"].mean()), 3),
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3),
        "avg_field_size": round(float(df["field_size_num"].mean()), 3),
        "avg_early_speed_density": round(float(df["early_speed_density_num"].mean()), 4),
    }


def compare_group(df, group_col, output_segment_prefix):
    rows = []

    for group_name, g in df.groupby(group_col, dropna=False):
        lone = g[g["lone_leader_crawl_v1"]].copy()
        other = g[~g["lone_leader_crawl_v1"]].copy()

        lone_row = summarize(lone, f"{output_segment_prefix}_{group_name}__LONE_LEADER_CRAWL")
        other_row = summarize(other, f"{output_segment_prefix}_{group_name}__OTHER_V4")

        lone_wr = lone_row["win_rate_pct"]
        other_wr = other_row["win_rate_pct"]

        lift = (
            round(float(lone_wr) - float(other_wr), 3)
            if pd.notna(lone_wr) and pd.notna(other_wr)
            else np.nan
        )

        lone_row["group"] = group_name
        lone_row["comparison_base"] = "OTHER_V4_SAME_GROUP"
        lone_row["other_v4_win_rate_pct"] = other_wr
        lone_row["lift_vs_other_same_group_points"] = lift

        other_row["group"] = group_name
        other_row["comparison_base"] = "REFERENCE"
        other_row["other_v4_win_rate_pct"] = other_wr
        other_row["lift_vs_other_same_group_points"] = 0

        rows.append(lone_row)
        rows.append(other_row)

    return pd.DataFrame(rows)


def main():
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(IN_FILE)

    df = pd.read_csv(IN_FILE, low_memory=False)

    df["accepted_signal_bool"] = df["accepted_signal_v4"].map(to_bool)
    df["won_num"] = num(df["won"]).fillna(0)
    df["placed_num"] = num(df["placed"]).fillna(0)
    df["score_share_num"] = num(df["score_share_of_race"])
    df["dominance_num"] = num(df["dominance_score_v1"])
    df["edge_proxy_num"] = num(df["edge_proxy_pct"])
    df["field_size_num"] = num(df["field_size"])
    df["early_speed_density_num"] = num(df["early_speed_density_v1"])

    v4 = df[df["accepted_signal_bool"]].copy()

    v4["lone_leader_crawl_v1"] = (
        (v4["pace_role_v1"].astype(str).str.upper() == "LEADER") &
        (v4["race_shape_density_v1"].astype(str).str.upper() == "CRAWL")
    )

    v4["share_micro_bucket_v1"] = v4["score_share_num"].map(share_micro_bucket)
    v4["dominance_micro_bucket_v1"] = v4["dominance_num"].map(dominance_micro_bucket)

    base = summarize(v4, "BASE_V4")
    lone = summarize(v4[v4["lone_leader_crawl_v1"]], "BASE_V4_LONE_LEADER_CRAWL")
    other = summarize(v4[~v4["lone_leader_crawl_v1"]], "BASE_V4_OTHER_THAN_LONE_LEADER_CRAWL")

    base_wr = base["win_rate_pct"]
    other_wr = other["win_rate_pct"]
    lone_wr = lone["win_rate_pct"]

    summary = pd.DataFrame([base, lone, other])
    summary["lift_vs_base_points"] = summary["win_rate_pct"].apply(
        lambda x: round(float(x) - float(base_wr), 3) if pd.notna(x) else np.nan
    )
    summary["lift_vs_other_v4_points"] = summary["win_rate_pct"].apply(
        lambda x: round(float(x) - float(other_wr), 3) if pd.notna(x) else np.nan
    )

    by_trust = compare_group(v4, "trust_profile_v1", "TRUST")
    by_field = compare_group(v4, "field_size_bucket_v1", "FIELD")
    by_share = compare_group(v4, "share_micro_bucket_v1", "SHARE")
    by_dom = compare_group(v4, "dominance_micro_bucket_v1", "DOM")

    elite_trust_lone = by_trust[
        (by_trust["group"].astype(str) == "ELITE") &
        (by_trust["segment"].astype(str).str.contains("LONE_LEADER_CRAWL"))
    ]

    strong_trust_lone = by_trust[
        (by_trust["group"].astype(str) == "STRONG") &
        (by_trust["segment"].astype(str).str.contains("LONE_LEADER_CRAWL"))
    ]

    def get_first(frame, col):
        if len(frame) == 0:
            return np.nan
        return frame[col].iloc[0]

    lone_lift_vs_other = (
        round(float(lone_wr) - float(other_wr), 3)
        if pd.notna(lone_wr) and pd.notna(other_wr)
        else np.nan
    )

    elite_trust_lift = get_first(elite_trust_lone, "lift_vs_other_same_group_points")
    strong_trust_lift = get_first(strong_trust_lone, "lift_vs_other_same_group_points")

    if pd.notna(lone_lift_vs_other) and lone_lift_vs_other >= 3.0:
        final = "LONE_LEADER_ADVANTAGE_ADDS_INFORMATION"
    elif pd.notna(lone_lift_vs_other) and lone_lift_vs_other >= 1.0:
        final = "LONE_LEADER_ADVANTAGE_MODEST_INFORMATION"
    else:
        final = "LONE_LEADER_ADVANTAGE_NOT_PROVEN"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_FILE},
        {"metric": "base_v4_signals", "value": len(v4)},
        {"metric": "lone_leader_crawl_signals", "value": int(v4["lone_leader_crawl_v1"].sum())},
        {"metric": "lone_leader_crawl_win_rate_pct", "value": lone_wr},
        {"metric": "other_v4_win_rate_pct", "value": other_wr},
        {"metric": "lone_leader_lift_vs_other_v4_points", "value": lone_lift_vs_other},
        {"metric": "elite_trust_lone_leader_lift_points", "value": elite_trust_lift},
        {"metric": "strong_trust_lone_leader_lift_points", "value": strong_trust_lift},
        {"metric": "final_conclusion", "value": final},
    ])

    detail_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "race_key",
        "join_key_v1",
        "runner_rank",
        "runner_score",
        "score_share_of_race",
        "score_share_band_v1",
        "share_micro_bucket_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "dominance_micro_bucket_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "field_size",
        "field_size_bucket_v1",
        "edge_proxy_pct",
        "accepted_signal_v4",
        "won",
        "placed",
        "finish_position",
        "pace_role_v1",
        "race_shape_density_v1",
        "pace_advantage_score_v1",
        "pace_advantage_band_v1",
        "early_speed_density_v1",
        "known_pace_ratio_v1",
        "leaders_v1",
        "on_pace_v1",
        "midfield_v1",
        "backmarkers_v1",
        "unknown_pace_v1",
        "dna_confidence_v2",
        "dna_source",
        "lone_leader_crawl_v1",
    ]

    detail_cols = [c for c in detail_cols if c in v4.columns]

    v4[detail_cols].to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_trust.to_csv(OUT_BY_TRUST, index=False)
    by_field.to_csv(OUT_BY_FIELD, index=False)
    by_share.to_csv(OUT_BY_SHARE, index=False)
    by_dom.to_csv(OUT_BY_DOM, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[LONE_LEADER_INDEPENDENCE_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_TRUST}")
    print(f"wrote={OUT_BY_FIELD}")
    print(f"wrote={OUT_BY_SHARE}")
    print(f"wrote={OUT_BY_DOM}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
