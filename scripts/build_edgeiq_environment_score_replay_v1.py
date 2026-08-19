from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_FILE = os.path.join(DATA, "edgeiq_environment_score_v1.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_environment_score_replay_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_environment_score_replay_v1_summary.csv")
OUT_BY_BAND = os.path.join(DATA, "edgeiq_environment_score_replay_v1_by_band.csv")
OUT_BY_TRUST = os.path.join(DATA, "edgeiq_environment_score_replay_v1_by_trust.csv")
OUT_BY_FIELD = os.path.join(DATA, "edgeiq_environment_score_replay_v1_by_field_size.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_environment_score_replay_v1_verdict.csv")


def num(x):
    return pd.to_numeric(x, errors="coerce")


def pct(x):
    if pd.isna(x):
        return np.nan
    return round(float(x) * 100.0, 2)


def choose_win_col(df):
    for c in ["won", "rank1_won", "is_winner", "winner"]:
        if c in df.columns:
            return c

    if "finish_position" in df.columns:
        return "finish_position"

    raise ValueError("No win/outcome column found. Expected won, rank1_won, is_winner, winner, or finish_position.")


def choose_place_col(df):
    for c in ["placed", "rank1_placed", "is_placed"]:
        if c in df.columns:
            return c

    if "finish_position" in df.columns:
        return "finish_position"

    return None


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
            "avg_environment_score": np.nan,
            "avg_score_share": np.nan,
            "avg_dominance": np.nan,
            "avg_edge_proxy_pct": np.nan,
        }

    return {
        "segment": segment,
        "signals": int(len(df)),
        "races": int(df["race_join_key_fixed"].nunique()) if "race_join_key_fixed" in df.columns else int(len(df)),
        "wins": int(df["won_num"].sum()),
        "places": int(df["placed_num"].sum()),
        "win_rate_pct": pct(df["won_num"].mean()),
        "place_rate_pct": pct(df["placed_num"].mean()) if "placed_num" in df.columns else np.nan,
        "avg_environment_score": round(float(df["environment_score_num"].mean()), 3),
        "avg_score_share": round(float(df["score_share_num"].mean()), 6) if df["score_share_num"].notna().any() else np.nan,
        "avg_dominance": round(float(df["dominance_num"].mean()), 3) if df["dominance_num"].notna().any() else np.nan,
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3) if df["edge_proxy_num"].notna().any() else np.nan,
    }


def group_report(df, col, prefix):
    rows = []
    for group, g in df.groupby(col, dropna=False):
        row = summarise(g, f"{prefix}_{group}")
        row["group"] = group
        rows.append(row)
    return pd.DataFrame(rows)


def add_lift(frame, base_wr):
    frame["lift_vs_base_points"] = frame["win_rate_pct"].apply(
        lambda x: round(float(x) - base_wr, 3) if pd.notna(x) and pd.notna(base_wr) else np.nan
    )
    return frame


def main():
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(IN_FILE)

    df = pd.read_csv(IN_FILE, low_memory=False)

    win_source = choose_win_col(df)

    if win_source == "finish_position":
        fp = num(df["finish_position"])
        df["won_num"] = (fp == 1).astype(int)
    else:
        df["won_num"] = num(df[win_source]).fillna(0).astype(int)

    place_source = choose_place_col(df)

    if place_source == "finish_position":
        fp = num(df["finish_position"])
        df["placed_num"] = ((fp >= 1) & (fp <= 3)).astype(int)
    elif place_source:
        df["placed_num"] = num(df[place_source]).fillna(0).astype(int)
    else:
        df["placed_num"] = np.nan

    df["environment_score_num"] = num(df["environment_score_v1"]).fillna(0)
    df["score_share_num"] = num(df.get("score_share_of_race"))
    df["dominance_num"] = num(df.get("dominance_score_v1"))
    df["edge_proxy_num"] = num(df.get("edge_proxy_pct"))

    base = summarise(df, "BASE_V4")
    base_wr = float(base["win_rate_pct"])

    summary_rows = [
        base,
        summarise(df[df["environment_score_num"] == 0], "ENV_SCORE_0"),
        summarise(df[df["environment_score_num"].between(1, 2)], "ENV_SCORE_1_2"),
        summarise(df[df["environment_score_num"].between(3, 4)], "ENV_SCORE_3_4"),
        summarise(df[df["environment_score_num"].between(5, 6)], "ENV_SCORE_5_6"),
        summarise(df[df["environment_score_num"] >= 7], "ENV_SCORE_7_PLUS"),
    ]

    summary = add_lift(pd.DataFrame(summary_rows), base_wr)

    by_band = add_lift(group_report(df, "environment_band_v1", "ENVIRONMENT_BAND"), base_wr)

    if "trust_profile_v1" in df.columns:
        by_trust = add_lift(group_report(df, "trust_profile_v1", "TRUST"), base_wr)
    else:
        by_trust = pd.DataFrame()

    if "field_size_bucket_v1" in df.columns:
        by_field = add_lift(group_report(df, "field_size_bucket_v1", "FIELD"), base_wr)
    else:
        by_field = pd.DataFrame()

    elite = by_band[by_band["group"].astype(str) == "ELITE"]
    positive = by_band[by_band["group"].astype(str) == "POSITIVE"]
    poor = by_band[by_band["group"].astype(str) == "POOR"]

    elite_lift = float(elite["lift_vs_base_points"].iloc[0]) if len(elite) else np.nan
    positive_lift = float(positive["lift_vs_base_points"].iloc[0]) if len(positive) else np.nan
    poor_lift = float(poor["lift_vs_base_points"].iloc[0]) if len(poor) else np.nan

    if pd.notna(elite_lift) and elite_lift >= 5.0:
        final = "ENVIRONMENT_SCORE_ADDS_STRONG_INFORMATION"
    elif pd.notna(positive_lift) and positive_lift >= 2.0:
        final = "ENVIRONMENT_SCORE_ADDS_MODEST_INFORMATION"
    else:
        final = "ENVIRONMENT_SCORE_NOT_PROVEN"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_FILE},
        {"metric": "signals", "value": len(df)},
        {"metric": "win_source", "value": win_source},
        {"metric": "place_source", "value": place_source if place_source else ""},
        {"metric": "base_win_rate_pct", "value": base_wr},
        {"metric": "elite_lift_points", "value": elite_lift},
        {"metric": "positive_lift_points", "value": positive_lift},
        {"metric": "poor_lift_points", "value": poor_lift},
        {"metric": "final_conclusion", "value": final},
    ])

    df.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_band.to_csv(OUT_BY_BAND, index=False)
    by_trust.to_csv(OUT_BY_TRUST, index=False)
    by_field.to_csv(OUT_BY_FIELD, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[ENVIRONMENT_SCORE_REPLAY_V1] COMPLETE")
    print(f"win_source={win_source}")
    print(f"place_source={place_source if place_source else ''}")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_BAND}")
    print(f"wrote={OUT_BY_TRUST}")
    print(f"wrote={OUT_BY_FIELD}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
