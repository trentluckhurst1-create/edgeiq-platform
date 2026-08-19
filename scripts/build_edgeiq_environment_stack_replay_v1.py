from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_FILE = os.path.join(DATA, "edgeiq_race_reliability_independence_audit_v1.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_environment_stack_replay_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_environment_stack_replay_v1_summary.csv")
OUT_BY_TRUST = os.path.join(DATA, "edgeiq_environment_stack_replay_v1_by_trust.csv")
OUT_TOP = os.path.join(DATA, "edgeiq_environment_stack_replay_v1_top_segments.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_environment_stack_replay_v1_verdict.csv")


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
            "avg_pace_score": np.nan,
            "lone_leader_count": 0,
            "elite_pace_count": 0,
            "elite_reliability_count": 0,
        }

    return {
        "segment": segment,
        "signals": int(len(df)),
        "races": int(df["race_join_key_fixed"].nunique()) if "race_join_key_fixed" in df.columns else int(len(df)),
        "wins": int(df["won_num"].sum()),
        "places": int(df["placed_num"].sum()),
        "win_rate_pct": pct(df["won_num"].mean()),
        "place_rate_pct": pct(df["placed_num"].mean()),
        "avg_score_share": round(float(df["score_share_num"].mean()), 6),
        "avg_dominance": round(float(df["dominance_num"].mean()), 3),
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3),
        "avg_field_size": round(float(df["field_size_num"].mean()), 3),
        "avg_pace_score": round(float(df["pace_advantage_score_num"].mean()), 3)
        if df["pace_advantage_score_num"].notna().any()
        else np.nan,
        "lone_leader_count": int(df["lone_leader_bool"].sum()),
        "elite_pace_count": int(df["elite_pace_bool"].sum()),
        "elite_reliability_count": int(df["elite_reliability_bool"].sum()),
    }


def add_segment(rows, df, name, base_wr):
    row = summarise(df, name)
    row["lift_vs_base_points"] = (
        round(float(row["win_rate_pct"]) - float(base_wr), 3)
        if pd.notna(row["win_rate_pct"]) and pd.notna(base_wr)
        else np.nan
    )
    rows.append(row)


def main():
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(IN_FILE)

    df = pd.read_csv(IN_FILE, low_memory=False)

    df["won_num"] = num(df["won"]).fillna(0)
    df["placed_num"] = num(df["placed"]).fillna(0)
    df["score_share_num"] = num(df.get("score_share_of_race"))
    df["dominance_num"] = num(df.get("dominance_score_v1"))
    df["edge_proxy_num"] = num(df.get("edge_proxy_pct"))
    df["field_size_num"] = num(df.get("field_size"))
    df["pace_advantage_score_num"] = num(df.get("pace_advantage_score_v1"))

    df["lone_leader_bool"] = df["lone_leader_bool"].map(to_bool)
    df["elite_pace_bool"] = df["pace_advantage_band_v1"].astype(str).str.upper().eq("ELITE")
    df["positive_pace_bool"] = df["pace_advantage_band_v1"].astype(str).str.upper().isin(["ELITE", "POSITIVE"])
    df["poor_negative_pace_bool"] = df["pace_advantage_band_v1"].astype(str).str.upper().isin(["POOR", "NEGATIVE"])

    df["elite_reliability_bool"] = df["race_reliability_band_v1"].astype(str).str.upper().eq("ELITE")
    df["positive_plus_reliability_bool"] = df["race_reliability_band_v1"].astype(str).str.upper().isin(["ELITE", "POSITIVE"])
    df["poor_negative_reliability_bool"] = df["race_reliability_band_v1"].astype(str).str.upper().isin(["POOR", "NEGATIVE"])

    df["low_depth_strength_bool"] = df["race_strength_band"].astype(str).str.upper().isin(["VERY_WEAK", "WEAK"])
    df["high_depth_strength_bool"] = df["race_strength_band"].astype(str).str.upper().isin(["STRONG", "VERY_STRONG", "ELITE"])

    df["environment_stack_count_v1"] = (
        df["lone_leader_bool"].astype(int)
        + df["elite_pace_bool"].astype(int)
        + df["elite_reliability_bool"].astype(int)
        + df["low_depth_strength_bool"].astype(int)
    )

    df["environment_stack_label_v1"] = df["environment_stack_count_v1"].map({
        0: "STACK_0",
        1: "STACK_1",
        2: "STACK_2",
        3: "STACK_3",
        4: "STACK_4",
    }).fillna("STACK_UNKNOWN")

    base = df.copy()
    base_wr = float(base["won_num"].mean() * 100.0) if len(base) else np.nan

    summary_rows = []

    add_segment(summary_rows, base, "BASE_V4", base_wr)
    add_segment(summary_rows, base[base["elite_reliability_bool"]], "ELITE_RELIABILITY", base_wr)
    add_segment(summary_rows, base[base["elite_pace_bool"]], "ELITE_PACE", base_wr)
    add_segment(summary_rows, base[base["lone_leader_bool"]], "LONE_LEADER", base_wr)
    add_segment(summary_rows, base[base["low_depth_strength_bool"]], "LOW_DEPTH_STRENGTH", base_wr)
    add_segment(summary_rows, base[base["high_depth_strength_bool"]], "HIGH_DEPTH_STRENGTH", base_wr)

    add_segment(
        summary_rows,
        base[base["lone_leader_bool"] & base["elite_pace_bool"]],
        "LONE_LEADER_PLUS_ELITE_PACE",
        base_wr,
    )

    add_segment(
        summary_rows,
        base[base["lone_leader_bool"] & base["elite_reliability_bool"]],
        "LONE_LEADER_PLUS_ELITE_RELIABILITY",
        base_wr,
    )

    add_segment(
        summary_rows,
        base[base["elite_pace_bool"] & base["elite_reliability_bool"]],
        "ELITE_PACE_PLUS_ELITE_RELIABILITY",
        base_wr,
    )

    add_segment(
        summary_rows,
        base[
            base["lone_leader_bool"]
            & base["elite_pace_bool"]
            & base["elite_reliability_bool"]
        ],
        "TRIPLE_LONE_ELITE_PACE_ELITE_RELIABILITY",
        base_wr,
    )

    for stack_label, g in base.groupby("environment_stack_label_v1", dropna=False):
        add_segment(summary_rows, g, f"ENVIRONMENT_{stack_label}", base_wr)

    summary = pd.DataFrame(summary_rows)

    by_trust_rows = []

    for trust, tg in base.groupby("trust_profile_v1", dropna=False):
        add_segment(by_trust_rows, tg, f"TRUST_{trust}_BASE", base_wr)
        add_segment(by_trust_rows, tg[tg["elite_reliability_bool"]], f"TRUST_{trust}_ELITE_RELIABILITY", base_wr)
        add_segment(by_trust_rows, tg[tg["elite_pace_bool"]], f"TRUST_{trust}_ELITE_PACE", base_wr)
        add_segment(by_trust_rows, tg[tg["lone_leader_bool"]], f"TRUST_{trust}_LONE_LEADER", base_wr)
        add_segment(
            by_trust_rows,
            tg[tg["lone_leader_bool"] & tg["elite_pace_bool"]],
            f"TRUST_{trust}_LONE_PLUS_ELITE_PACE",
            base_wr,
        )
        add_segment(
            by_trust_rows,
            tg[tg["lone_leader_bool"] & tg["elite_reliability_bool"]],
            f"TRUST_{trust}_LONE_PLUS_ELITE_RELIABILITY",
            base_wr,
        )
        add_segment(
            by_trust_rows,
            tg[
                tg["lone_leader_bool"]
                & tg["elite_pace_bool"]
                & tg["elite_reliability_bool"]
            ],
            f"TRUST_{trust}_TRIPLE_STACK",
            base_wr,
        )

    by_trust = pd.DataFrame(by_trust_rows)

    top_frames = []

    for frame_name, frame in [
        ("summary", summary),
        ("by_trust", by_trust),
    ]:
        f = frame.copy()
        f["source_table"] = frame_name
        top_frames.append(f)

    top = pd.concat(top_frames, ignore_index=True)
    top = top[
        (top["signals"] >= 30)
        & (top["lift_vs_base_points"].notna())
    ].copy()

    top["quality_score_v1"] = (
        top["win_rate_pct"].fillna(0) * 0.50
        + top["place_rate_pct"].fillna(0) * 0.15
        + top["lift_vs_base_points"].fillna(0) * 2.50
        + np.minimum(top["signals"].fillna(0), 500) * 0.015
    ).round(3)

    top = top.sort_values(
        ["quality_score_v1", "win_rate_pct", "signals"],
        ascending=[False, False, False],
    )

    best = top.iloc[0] if len(top) else None

    if best is not None:
        best_segment = best["segment"]
        best_signals = int(best["signals"])
        best_win = best["win_rate_pct"]
        best_lift = best["lift_vs_base_points"]
    else:
        best_segment = ""
        best_signals = 0
        best_win = np.nan
        best_lift = np.nan

    triple = summary[summary["segment"] == "TRIPLE_LONE_ELITE_PACE_ELITE_RELIABILITY"]
    triple_signals = int(triple["signals"].iloc[0]) if len(triple) else 0
    triple_win = triple["win_rate_pct"].iloc[0] if len(triple) else np.nan
    triple_lift = triple["lift_vs_base_points"].iloc[0] if len(triple) else np.nan

    stack3 = summary[summary["segment"].isin(["ENVIRONMENT_STACK_3", "ENVIRONMENT_STACK_4"])]
    stack3_signals = int(stack3["signals"].sum()) if len(stack3) else 0
    stack3_wins = int(stack3["wins"].sum()) if len(stack3) else 0
    stack3_win = round((stack3_wins / stack3_signals) * 100.0, 2) if stack3_signals else np.nan
    stack3_lift = round(stack3_win - base_wr, 3) if pd.notna(stack3_win) and pd.notna(base_wr) else np.nan

    if pd.notna(best_lift) and best_lift >= 5.0 and best_signals >= 100:
        final = "ENVIRONMENT_STACK_ADDS_STRONG_INFORMATION"
    elif pd.notna(best_lift) and best_lift >= 3.0 and best_signals >= 30:
        final = "ENVIRONMENT_STACK_ADDS_MODEST_INFORMATION"
    else:
        final = "ENVIRONMENT_STACK_NOT_PROVEN_AS_HARD_FILTER"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_FILE},
        {"metric": "base_signals", "value": len(base)},
        {"metric": "base_win_rate_pct", "value": round(base_wr, 2) if pd.notna(base_wr) else np.nan},
        {"metric": "best_segment_min30", "value": best_segment},
        {"metric": "best_segment_signals", "value": best_signals},
        {"metric": "best_segment_win_rate_pct", "value": best_win},
        {"metric": "best_segment_lift_points", "value": best_lift},
        {"metric": "triple_stack_signals", "value": triple_signals},
        {"metric": "triple_stack_win_rate_pct", "value": triple_win},
        {"metric": "triple_stack_lift_points", "value": triple_lift},
        {"metric": "stack3_plus_signals", "value": stack3_signals},
        {"metric": "stack3_plus_win_rate_pct", "value": stack3_win},
        {"metric": "stack3_plus_lift_points", "value": stack3_lift},
        {"metric": "final_conclusion", "value": final},
    ])

    detail_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "race_join_key_fixed",
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
        "won",
        "placed",
        "finish_position",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "pace_advantage_band_v1",
        "pace_advantage_score_v1",
        "pace_role_v1",
        "race_shape_density_v1",
        "lone_leader_bool",
        "race_strength_band",
        "environment_stack_count_v1",
        "environment_stack_label_v1",
    ]

    detail_cols = [c for c in detail_cols if c in base.columns]

    base[detail_cols].to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_trust.to_csv(OUT_BY_TRUST, index=False)
    top.to_csv(OUT_TOP, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[ENVIRONMENT_STACK_REPLAY_V1] COMPLETE")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_TRUST}")
    print(f"wrote={OUT_TOP}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
