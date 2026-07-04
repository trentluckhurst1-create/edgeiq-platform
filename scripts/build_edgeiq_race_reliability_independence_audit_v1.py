from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_RELIABILITY_REPLAY = os.path.join(DATA, "edgeiq_race_reliability_replay_v1.csv")
IN_PACE = os.path.join(DATA, "edgeiq_pace_advantage_replay_v1.csv")
IN_RACE_STRENGTH = os.path.join(DATA, "edgeiq_race_strength_independence_audit_v1.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_race_reliability_independence_audit_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_race_reliability_independence_audit_v1_summary.csv")
OUT_FIELD_PACE = os.path.join(DATA, "edgeiq_race_reliability_independence_audit_v1_field_pace.csv")
OUT_FIELD_LONE = os.path.join(DATA, "edgeiq_race_reliability_independence_audit_v1_field_lone_leader.csv")
OUT_FIELD_STRENGTH = os.path.join(DATA, "edgeiq_race_reliability_independence_audit_v1_field_race_strength.csv")
OUT_FIELD_TRUST = os.path.join(DATA, "edgeiq_race_reliability_independence_audit_v1_field_trust.csv")
OUT_WITHIN_FIELD = os.path.join(DATA, "edgeiq_race_reliability_independence_audit_v1_within_field.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_race_reliability_independence_audit_v1_verdict.csv")


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
        .replace("SPORTSBET", "")
        .replace("LADBROKES", "")
        .replace("BET365", "")
        .replace("TABPARK", "")
        .replace("PICKLEBETPARK", "")
        .replace("APIAM", "")
    )


def clean_race_no(x):
    s = safe_str(x).upper().replace("R", "")
    try:
        return str(int(float(s)))
    except Exception:
        return s


def clean_horse(x):
    return (
        safe_str(x)
        .upper()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace(".", "")
        .replace("'", "")
        .replace("’", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
    )


def get_date_col(df):
    for c in ["meeting_date", "race_date", "date"]:
        if c in df.columns:
            return c
    return None


def make_runner_join_key(df):
    date_col = get_date_col(df)
    if date_col is None:
        raise ValueError("Missing date column")

    required = ["track", "race_no", "horse"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for runner join: {missing}")

    return (
        df[date_col].astype(str).str.strip()
        + "|"
        + df["track"].map(clean_track)
        + "|"
        + df["race_no"].map(clean_race_no)
        + "|"
        + df["horse"].map(clean_horse)
    )


def make_race_join_key(df):
    date_col = get_date_col(df)
    if date_col is None:
        raise ValueError("Missing date column")

    required = ["track", "race_no"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for race join: {missing}")

    return (
        df[date_col].astype(str).str.strip()
        + "|"
        + df["track"].map(clean_track)
        + "|"
        + df["race_no"].map(clean_race_no)
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
            "avg_pace_score": np.nan,
            "lone_leader_count": 0,
        }

    return {
        "segment": segment,
        "signals": int(len(df)),
        "races": int(df["race_join_key_fixed"].nunique()),
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
    }


def group_report(df, group_cols, prefix):
    rows = []

    for keys, g in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        label = prefix + "__" + "__".join([safe_str(k) for k in keys])
        row = summarise(g, label)

        for c, k in zip(group_cols, keys):
            row[c] = k

        rows.append(row)

    return pd.DataFrame(rows)


def add_lift(frame, base_wr):
    if len(frame):
        frame["lift_vs_base_points"] = frame["win_rate_pct"].apply(
            lambda x: round(float(x) - base_wr, 3)
            if pd.notna(x)
            else np.nan
        )
    return frame


def main():
    if not os.path.exists(IN_RELIABILITY_REPLAY):
        raise FileNotFoundError(IN_RELIABILITY_REPLAY)

    rr = pd.read_csv(IN_RELIABILITY_REPLAY, low_memory=False)

    rr["runner_join_key_fixed"] = make_runner_join_key(rr)
    rr["race_join_key_fixed"] = make_race_join_key(rr)

    rr["accepted_signal_bool"] = rr["accepted_signal_v4"].map(to_bool)
    rr["won_num"] = num(rr["won"]).fillna(0)
    rr["placed_num"] = num(rr["placed"]).fillna(0)
    rr["score_share_num"] = num(rr.get("score_share_of_race"))
    rr["dominance_num"] = num(rr.get("dominance_score_v1"))
    rr["edge_proxy_num"] = num(rr.get("edge_proxy_pct"))
    rr["field_size_num"] = num(rr.get("field_size"))

    base = rr[rr["accepted_signal_bool"]].copy()

    base["pace_advantage_band_v1"] = "UNMATCHED"
    base["pace_advantage_score_v1"] = np.nan
    base["race_shape_density_v1"] = "UNMATCHED"
    base["pace_role_v1"] = "UNMATCHED"
    base["early_speed_density_v1"] = np.nan
    base["known_pace_ratio_v1"] = np.nan

    if os.path.exists(IN_PACE):
        pace = pd.read_csv(IN_PACE, low_memory=False)
        pace["runner_join_key_fixed"] = make_runner_join_key(pace)

        pace_keep = [
            "runner_join_key_fixed",
            "pace_advantage_band_v1",
            "pace_advantage_score_v1",
            "race_shape_density_v1",
            "pace_role_v1",
            "early_speed_density_v1",
            "known_pace_ratio_v1",
            "leaders_v1",
            "on_pace_v1",
            "midfield_v1",
            "backmarkers_v1",
            "unknown_pace_v1",
        ]
        pace_keep = [c for c in pace_keep if c in pace.columns]

        pace2 = pace[pace_keep].drop_duplicates("runner_join_key_fixed").copy()

        base = base.drop(
            columns=[
                "pace_advantage_band_v1",
                "pace_advantage_score_v1",
                "race_shape_density_v1",
                "pace_role_v1",
                "early_speed_density_v1",
                "known_pace_ratio_v1",
            ],
            errors="ignore",
        )

        base = base.merge(
            pace2,
            on="runner_join_key_fixed",
            how="left",
        )

    base["pace_advantage_band_v1"] = base["pace_advantage_band_v1"].fillna("UNMATCHED")
    base["pace_advantage_score_num"] = num(base.get("pace_advantage_score_v1"))
    base["race_shape_density_v1"] = base["race_shape_density_v1"].fillna("UNMATCHED")
    base["pace_role_v1"] = base["pace_role_v1"].fillna("UNMATCHED")

    base["lone_leader_bool"] = (
        (base["pace_role_v1"].astype(str).str.upper() == "LEADER") &
        (base["race_shape_density_v1"].astype(str).str.upper() == "CRAWL")
    )

    base["race_strength_band"] = "UNMATCHED"
    base["field_strength_score"] = np.nan
    base["field_strength_percentile"] = np.nan

    if os.path.exists(IN_RACE_STRENGTH):
        rs = pd.read_csv(IN_RACE_STRENGTH, low_memory=False)
        rs["runner_join_key_fixed"] = make_runner_join_key(rs)

        rs_keep = [
            "runner_join_key_fixed",
            "race_strength_band",
            "field_strength_score",
            "field_strength_percentile",
        ]
        rs_keep = [c for c in rs_keep if c in rs.columns]

        rs2 = rs[rs_keep].drop_duplicates("runner_join_key_fixed").copy()

        base = base.drop(
            columns=["race_strength_band", "field_strength_score", "field_strength_percentile"],
            errors="ignore",
        )

        base = base.merge(
            rs2,
            on="runner_join_key_fixed",
            how="left",
        )

    base["race_strength_band"] = base["race_strength_band"].fillna("UNMATCHED")

    summary = pd.DataFrame([
        summarise(base, "BASE_V4"),
        summarise(base[base["race_reliability_band_v1"] == "ELITE"], "RELIABILITY_ELITE"),
        summarise(base[base["race_reliability_band_v1"] == "POSITIVE"], "RELIABILITY_POSITIVE"),
        summarise(base[base["race_reliability_band_v1"] == "NEUTRAL"], "RELIABILITY_NEUTRAL"),
        summarise(base[base["race_reliability_band_v1"] == "NEGATIVE"], "RELIABILITY_NEGATIVE"),
    ])

    base_wr = float(summary.loc[summary["segment"] == "BASE_V4", "win_rate_pct"].iloc[0])

    field_pace = group_report(
        base,
        ["field_size_bucket_v1", "pace_advantage_band_v1"],
        "FIELD_PACE",
    )

    field_lone = group_report(
        base,
        ["field_size_bucket_v1", "lone_leader_bool"],
        "FIELD_LONE",
    )

    field_strength = group_report(
        base,
        ["field_size_bucket_v1", "race_strength_band"],
        "FIELD_STRENGTH",
    )

    field_trust = group_report(
        base,
        ["field_size_bucket_v1", "trust_profile_v1"],
        "FIELD_TRUST",
    )

    summary = add_lift(summary, base_wr)
    field_pace = add_lift(field_pace, base_wr)
    field_lone = add_lift(field_lone, base_wr)
    field_strength = add_lift(field_strength, base_wr)
    field_trust = add_lift(field_trust, base_wr)

    independence_rows = []

    for bucket, g in base.groupby("field_size_bucket_v1", dropna=False):
        bucket_base = summarise(g, f"FIELD_{bucket}_BASE")
        bucket_wr = bucket_base["win_rate_pct"]

        tests = [
            ("ELITE_PACE", g[g["pace_advantage_band_v1"] == "ELITE"]),
            ("POSITIVE_PLUS_PACE", g[g["pace_advantage_band_v1"].isin(["ELITE", "POSITIVE"])]),
            ("POOR_NEGATIVE_PACE", g[g["pace_advantage_band_v1"].isin(["POOR", "NEGATIVE"])]),
            ("LONE_LEADER", g[g["lone_leader_bool"]]),
            ("NON_LONE", g[~g["lone_leader_bool"]]),
            ("LOW_DEPTH_STRENGTH", g[g["race_strength_band"].isin(["VERY_WEAK", "WEAK"])]),
            ("HIGH_DEPTH_STRENGTH", g[g["race_strength_band"].isin(["STRONG", "VERY_STRONG", "ELITE"])]),
            ("ELITE_TRUST", g[g["trust_profile_v1"].astype(str).str.upper() == "ELITE"]),
            ("STRONG_TRUST", g[g["trust_profile_v1"].astype(str).str.upper() == "STRONG"]),
        ]

        for label, subset in tests:
            row = summarise(subset, f"FIELD_{bucket}_{label}")
            row["field_size_bucket_v1"] = bucket
            row["test"] = label
            row["field_bucket_base_win_rate_pct"] = bucket_wr
            row["lift_vs_field_bucket_points"] = (
                round(float(row["win_rate_pct"]) - float(bucket_wr), 3)
                if pd.notna(row["win_rate_pct"]) and pd.notna(bucket_wr)
                else np.nan
            )
            independence_rows.append(row)

    within_field = pd.DataFrame(independence_rows)

    valid_ind = within_field[
        (within_field["signals"] >= 25) &
        (within_field["lift_vs_field_bucket_points"].notna())
    ].copy()

    best_lift = valid_ind["lift_vs_field_bucket_points"].max() if len(valid_ind) else np.nan
    best_segment = (
        valid_ind.sort_values("lift_vs_field_bucket_points", ascending=False)["segment"].iloc[0]
        if len(valid_ind)
        else ""
    )

    elite_rows = summary[summary["segment"] == "RELIABILITY_ELITE"]
    elite_lift = (
        float(elite_rows["lift_vs_base_points"].iloc[0])
        if len(elite_rows)
        else np.nan
    )

    pace_match_pct = round(float((base["pace_advantage_band_v1"] != "UNMATCHED").mean()) * 100.0, 2) if len(base) else 0
    strength_match_pct = round(float((base["race_strength_band"] != "UNMATCHED").mean()) * 100.0, 2) if len(base) else 0

    if pace_match_pct < 50:
        final = "PACE_JOIN_STILL_INSUFFICIENT"
    elif pd.notna(best_lift) and best_lift >= 3.0:
        final = "ENVIRONMENT_FACTORS_ADD_INFORMATION_WITHIN_FIELD_SIZE"
    elif pd.notna(best_lift) and best_lift >= 1.0:
        final = "ENVIRONMENT_FACTORS_ADD_MODEST_INFORMATION_WITHIN_FIELD_SIZE"
    elif pd.notna(elite_lift) and elite_lift >= 2.0:
        final = "RACE_RELIABILITY_IS_MAINLY_FIELD_SIZE_DRIVEN"
    else:
        final = "RACE_RELIABILITY_INDEPENDENCE_NOT_PROVEN"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "base_signals", "value": len(base)},
        {"metric": "input_reliability_replay", "value": IN_RELIABILITY_REPLAY},
        {"metric": "input_pace_used", "value": os.path.exists(IN_PACE)},
        {"metric": "input_race_strength_used", "value": os.path.exists(IN_RACE_STRENGTH)},
        {"metric": "pace_match_pct", "value": pace_match_pct},
        {"metric": "race_strength_match_pct", "value": strength_match_pct},
        {"metric": "base_v4_win_rate_pct", "value": base_wr},
        {"metric": "elite_reliability_lift_vs_base_points", "value": elite_lift},
        {"metric": "best_within_field_segment", "value": best_segment},
        {"metric": "best_within_field_lift_points", "value": best_lift},
        {"metric": "final_conclusion", "value": final},
    ])

    detail_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "runner_join_key_fixed",
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
        "field_strength_score",
        "field_strength_percentile",
    ]
    detail_cols = [c for c in detail_cols if c in base.columns]

    base[detail_cols].to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    field_pace.to_csv(OUT_FIELD_PACE, index=False)
    field_lone.to_csv(OUT_FIELD_LONE, index=False)
    field_strength.to_csv(OUT_FIELD_STRENGTH, index=False)
    field_trust.to_csv(OUT_FIELD_TRUST, index=False)
    within_field.to_csv(OUT_WITHIN_FIELD, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[RACE_RELIABILITY_INDEPENDENCE_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_FIELD_PACE}")
    print(f"wrote={OUT_FIELD_LONE}")
    print(f"wrote={OUT_FIELD_STRENGTH}")
    print(f"wrote={OUT_FIELD_TRUST}")
    print(f"wrote={OUT_WITHIN_FIELD}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
