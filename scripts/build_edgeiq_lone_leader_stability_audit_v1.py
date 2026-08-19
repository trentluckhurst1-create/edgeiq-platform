from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_FILE = os.path.join(DATA, "edgeiq_lone_leader_independence_audit_v1.csv")

OUT_SUMMARY = os.path.join(DATA, "edgeiq_lone_leader_stability_audit_v1_summary.csv")
OUT_BY_YEAR = os.path.join(DATA, "edgeiq_lone_leader_stability_audit_v1_by_year.csv")
OUT_BY_TRUST = os.path.join(DATA, "edgeiq_lone_leader_stability_audit_v1_by_trust.csv")
OUT_BY_FIELD = os.path.join(DATA, "edgeiq_lone_leader_stability_audit_v1_by_field_size.csv")
OUT_BY_TRACK = os.path.join(DATA, "edgeiq_lone_leader_stability_audit_v1_by_track.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_lone_leader_stability_audit_v1_verdict.csv")


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


def summarise(df, label):
    if len(df) == 0:
        return {
            "segment": label,
            "signals": 0,
            "wins": 0,
            "places": 0,
            "win_rate_pct": np.nan,
            "place_rate_pct": np.nan,
            "avg_score_share": np.nan,
            "avg_dominance": np.nan,
            "avg_edge_proxy_pct": np.nan,
            "avg_field_size": np.nan,
        }

    return {
        "segment": label,
        "signals": int(len(df)),
        "wins": int(df["won_num"].sum()),
        "places": int(df["placed_num"].sum()),
        "win_rate_pct": pct(df["won_num"].mean()),
        "place_rate_pct": pct(df["placed_num"].mean()),
        "avg_score_share": round(float(df["score_share_num"].mean()), 6),
        "avg_dominance": round(float(df["dominance_num"].mean()), 3),
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3),
        "avg_field_size": round(float(df["field_size_num"].mean()), 3),
    }


def compare(df, group_col, prefix):
    rows = []

    for group, g in df.groupby(group_col, dropna=False):
        lone = g[g["lone_leader_bool"]].copy()
        other = g[~g["lone_leader_bool"]].copy()

        lone_row = summarise(lone, f"{prefix}_{group}__LONE_LEADER")
        other_row = summarise(other, f"{prefix}_{group}__OTHER_V4")

        lone_wr = lone_row["win_rate_pct"]
        other_wr = other_row["win_rate_pct"]

        lift = (
            round(float(lone_wr) - float(other_wr), 3)
            if pd.notna(lone_wr) and pd.notna(other_wr)
            else np.nan
        )

        lone_row["group"] = group
        lone_row["other_v4_win_rate_pct"] = other_wr
        lone_row["lift_vs_other_points"] = lift

        other_row["group"] = group
        other_row["other_v4_win_rate_pct"] = other_wr
        other_row["lift_vs_other_points"] = 0

        rows.append(lone_row)
        rows.append(other_row)

    return pd.DataFrame(rows)


def main():
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(IN_FILE)

    df = pd.read_csv(IN_FILE, low_memory=False)

    df["accepted_signal_bool"] = df["accepted_signal_v4"].map(to_bool)
    df["lone_leader_bool"] = df["lone_leader_crawl_v1"].map(to_bool)

    df["won_num"] = num(df["won"]).fillna(0)
    df["placed_num"] = num(df["placed"]).fillna(0)
    df["score_share_num"] = num(df["score_share_of_race"])
    df["dominance_num"] = num(df["dominance_score_v1"])
    df["edge_proxy_num"] = num(df["edge_proxy_pct"])
    df["field_size_num"] = num(df["field_size"])

    df["year"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year.astype("Int64").astype(str)

    v4 = df[df["accepted_signal_bool"]].copy()

    base = summarise(v4, "BASE_V4")
    lone = summarise(v4[v4["lone_leader_bool"]], "BASE_V4_LONE_LEADER")
    other = summarise(v4[~v4["lone_leader_bool"]], "BASE_V4_OTHER")

    summary = pd.DataFrame([base, lone, other])

    by_year = compare(v4, "year", "YEAR")
    by_trust = compare(v4, "trust_profile_v1", "TRUST")
    by_field = compare(v4, "field_size_bucket_v1", "FIELD")

    track_counts = (
        v4[v4["lone_leader_bool"]]
        .groupby("track", dropna=False)
        .size()
        .reset_index(name="lone_leader_signals")
        .sort_values("lone_leader_signals", ascending=False)
    )

    top_tracks = track_counts[track_counts["lone_leader_signals"] >= 3]["track"].tolist()
    by_track = compare(v4[v4["track"].isin(top_tracks)], "track", "TRACK") if top_tracks else pd.DataFrame()

    year_lone = by_year[by_year["segment"].astype(str).str.contains("LONE_LEADER", na=False)].copy()
    year_lone_valid = year_lone[year_lone["signals"] >= 10].copy()

    years_positive = int((year_lone_valid["lift_vs_other_points"] > 0).sum()) if len(year_lone_valid) else 0
    years_tested = int(len(year_lone_valid))
    min_year_lift = round(float(year_lone_valid["lift_vs_other_points"].min()), 3) if len(year_lone_valid) else np.nan
    avg_year_lift = round(float(year_lone_valid["lift_vs_other_points"].mean()), 3) if len(year_lone_valid) else np.nan

    if years_tested >= 3 and years_positive == years_tested and min_year_lift >= 1.0:
        final = "STABILITY_PASS"
    elif years_tested >= 3 and years_positive >= years_tested - 1:
        final = "STABILITY_MODERATE"
    else:
        final = "STABILITY_NOT_PROVEN"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_FILE},
        {"metric": "base_v4_signals", "value": len(v4)},
        {"metric": "lone_leader_signals", "value": int(v4["lone_leader_bool"].sum())},
        {"metric": "years_tested_min_10_signals", "value": years_tested},
        {"metric": "years_positive", "value": years_positive},
        {"metric": "min_year_lift_points", "value": min_year_lift},
        {"metric": "avg_year_lift_points", "value": avg_year_lift},
        {"metric": "final_conclusion", "value": final},
    ])

    summary.to_csv(OUT_SUMMARY, index=False)
    by_year.to_csv(OUT_BY_YEAR, index=False)
    by_trust.to_csv(OUT_BY_TRUST, index=False)
    by_field.to_csv(OUT_BY_FIELD, index=False)
    by_track.to_csv(OUT_BY_TRACK, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[LONE_LEADER_STABILITY_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_YEAR}")
    print(f"wrote={OUT_BY_TRUST}")
    print(f"wrote={OUT_BY_FIELD}")
    print(f"wrote={OUT_BY_TRACK}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
