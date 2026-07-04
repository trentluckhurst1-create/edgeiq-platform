from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_V4 = os.path.join(DATA, "edgeiq_v4_rejected_winner_audit_v1.csv")
IN_DNA = os.path.join(DATA, "edgeiq_tactical_dna_v2.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_pace_advantage_replay_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_pace_advantage_replay_v1_summary.csv")
OUT_BY_BAND = os.path.join(DATA, "edgeiq_pace_advantage_replay_v1_by_band.csv")
OUT_BY_TRUST = os.path.join(DATA, "edgeiq_pace_advantage_replay_v1_by_trust.csv")
OUT_AUDIT = os.path.join(DATA, "edgeiq_pace_advantage_replay_v1_audit.csv")


MATRIX = {
    "LEADER": {
        "CRAWL": 25,
        "MODERATE": 10,
        "FAST": -5,
        "HIGH_PRESSURE": -20,
        "PRESSURE_COLLAPSE": -40,
    },
    "ON_PACE": {
        "CRAWL": 15,
        "MODERATE": 10,
        "FAST": 0,
        "HIGH_PRESSURE": -10,
        "PRESSURE_COLLAPSE": -25,
    },
    "MIDFIELD": {
        "CRAWL": -5,
        "MODERATE": 0,
        "FAST": 10,
        "HIGH_PRESSURE": 15,
        "PRESSURE_COLLAPSE": 20,
    },
    "BACKMARKER": {
        "CRAWL": -20,
        "MODERATE": -10,
        "FAST": 15,
        "HIGH_PRESSURE": 25,
        "PRESSURE_COLLAPSE": 40,
    },
    "UNKNOWN": {
        "CRAWL": 0,
        "MODERATE": 0,
        "FAST": 0,
        "HIGH_PRESSURE": 0,
        "PRESSURE_COLLAPSE": 0,
    },
}


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


def role_from_bucket(x):
    s = safe_str(x).upper()

    if "LEADER" in s:
        return "LEADER"
    if "ON" in s and "PACE" in s:
        return "ON_PACE"
    if "MID" in s:
        return "MIDFIELD"
    if "BACK" in s:
        return "BACKMARKER"

    return "UNKNOWN"


def density_shape(density, leaders):
    try:
        d = float(density)
    except Exception:
        d = 0.0

    try:
        l = int(leaders)
    except Exception:
        l = 0

    if d >= 0.80 or l >= 5:
        return "PRESSURE_COLLAPSE"
    if d >= 0.60 or l >= 4:
        return "HIGH_PRESSURE"
    if d >= 0.40:
        return "FAST"
    if d >= 0.20:
        return "MODERATE"
    return "CRAWL"


def adv_band(score):
    try:
        s = float(score)
    except Exception:
        return "UNKNOWN"

    if s >= 20:
        return "ELITE"
    if s >= 10:
        return "POSITIVE"
    if s <= -20:
        return "POOR"
    if s <= -10:
        return "NEGATIVE"
    return "NEUTRAL"


def pct(x):
    if pd.isna(x):
        return np.nan
    return round(float(x) * 100.0, 2)


def summarize(df, label):
    if len(df) == 0:
        return {
            "segment": label,
            "signals": 0,
            "races": 0,
            "win_rate_pct": np.nan,
            "place_rate_pct": np.nan,
            "avg_pace_score": np.nan,
            "avg_score_share": np.nan,
            "avg_dominance": np.nan,
            "avg_edge_proxy_pct": np.nan,
        }

    return {
        "segment": label,
        "signals": int(len(df)),
        "races": int(df["race_key"].nunique()) if "race_key" in df.columns else int(df["join_key_v1"].nunique()),
        "win_rate_pct": pct(df["won_num"].mean()),
        "place_rate_pct": pct(df["placed_num"].mean()),
        "avg_pace_score": round(float(df["pace_advantage_score_v1"].mean()), 3),
        "avg_score_share": round(float(df["score_share_num"].mean()), 6),
        "avg_dominance": round(float(df["dominance_num"].mean()), 3),
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3),
    }


def main():
    if not os.path.exists(IN_V4):
        raise FileNotFoundError(IN_V4)

    if not os.path.exists(IN_DNA):
        raise FileNotFoundError(IN_DNA)

    v4 = pd.read_csv(IN_V4, low_memory=False)
    dna = pd.read_csv(IN_DNA, low_memory=False)

    v4["horse_key_join"] = v4["horse"].map(norm_key)
    dna["horse_key_join"] = dna["horse_key"].map(norm_key)

    dna_role_col = "tactical_speed_bucket_v2" if "tactical_speed_bucket_v2" in dna.columns else "tactical_speed_bucket"

    dna_keep = [
        "horse_key_join",
        dna_role_col,
        "leader_pct_v2",
        "on_pace_pct_v2",
        "midfield_pct_v2",
        "backmarker_pct_v2",
        "dna_confidence_v2",
        "dna_source",
    ]
    dna_keep = [c for c in dna_keep if c in dna.columns]

    dna2 = dna[dna_keep].drop_duplicates("horse_key_join").copy()
    dna2["pace_role_v1"] = dna2[dna_role_col].map(role_from_bucket)

    df = v4.merge(dna2, on="horse_key_join", how="left")
    df["pace_role_v1"] = df["pace_role_v1"].fillna("UNKNOWN")

    df["leader_flag_v1"] = (df["pace_role_v1"] == "LEADER").astype(int)
    df["on_pace_flag_v1"] = (df["pace_role_v1"] == "ON_PACE").astype(int)
    df["midfield_flag_v1"] = (df["pace_role_v1"] == "MIDFIELD").astype(int)
    df["backmarker_flag_v1"] = (df["pace_role_v1"] == "BACKMARKER").astype(int)
    df["unknown_pace_flag_v1"] = (df["pace_role_v1"] == "UNKNOWN").astype(int)

    race_key_col = "race_key" if "race_key" in df.columns else "join_key_v1"

    race_rows = []
    for race_key, g in df.groupby(race_key_col, dropna=False):
        field_size = len(g)
        leaders = int(g["leader_flag_v1"].sum())
        on_pace = int(g["on_pace_flag_v1"].sum())
        midfield = int(g["midfield_flag_v1"].sum())
        backmarkers = int(g["backmarker_flag_v1"].sum())
        unknown = int(g["unknown_pace_flag_v1"].sum())

        early = leaders + on_pace
        density = round(early / field_size, 4) if field_size else 0
        known_ratio = round((field_size - unknown) / field_size, 4) if field_size else 0
        pressure_score = leaders * 4 + on_pace * 2 + midfield

        race_rows.append({
            race_key_col: race_key,
            "pace_field_size_v1": field_size,
            "leaders_v1": leaders,
            "on_pace_v1": on_pace,
            "midfield_v1": midfield,
            "backmarkers_v1": backmarkers,
            "unknown_pace_v1": unknown,
            "early_speed_count_v1": early,
            "early_speed_density_v1": density,
            "known_pace_ratio_v1": known_ratio,
            "pressure_score_v1": pressure_score,
            "race_shape_density_v1": density_shape(density, leaders),
        })

    race = pd.DataFrame(race_rows)

    df = df.merge(race, on=race_key_col, how="left")

    df["pace_advantage_score_v1"] = df.apply(
        lambda r: MATRIX.get(r["pace_role_v1"], MATRIX["UNKNOWN"]).get(r["race_shape_density_v1"], 0),
        axis=1,
    )
    df["pace_advantage_band_v1"] = df["pace_advantage_score_v1"].map(adv_band)

    df["accepted_signal_bool"] = df["accepted_signal_v4"].map(to_bool)
    df["won_num"] = num(df["won"]).fillna(0)
    df["placed_num"] = num(df["placed"]).fillna(0)
    df["score_share_num"] = num(df["score_share_of_race"])
    df["dominance_num"] = num(df["dominance_score_v1"])
    df["edge_proxy_num"] = num(df["edge_proxy_pct"])

    v4_sig = df[df["accepted_signal_bool"]].copy()

    summary_rows = [
        summarize(v4_sig, "BASE_V4"),
        summarize(v4_sig[v4_sig["pace_advantage_band_v1"] == "ELITE"], "BASE_V4_PLUS_ELITE_PACE"),
        summarize(v4_sig[v4_sig["pace_advantage_band_v1"].isin(["ELITE", "POSITIVE"])], "BASE_V4_PLUS_POSITIVE_OR_ELITE_PACE"),
        summarize(v4_sig[~v4_sig["pace_advantage_band_v1"].isin(["NEGATIVE", "POOR"])], "BASE_V4_REMOVE_NEGATIVE_POOR_PACE"),
        summarize(v4_sig[v4_sig["pace_advantage_band_v1"] == "POOR"], "BASE_V4_POOR_PACE_ONLY"),
        summarize(v4_sig[v4_sig["pace_advantage_band_v1"] == "NEGATIVE"], "BASE_V4_NEGATIVE_PACE_ONLY"),
    ]

    summary = pd.DataFrame(summary_rows)

    base_wr = float(summary.loc[summary["segment"] == "BASE_V4", "win_rate_pct"].iloc[0])

    summary["lift_vs_base_points"] = summary["win_rate_pct"].apply(
        lambda x: round(float(x) - base_wr, 3) if pd.notna(x) else np.nan
    )

    by_band_rows = []
    for b, g in v4_sig.groupby("pace_advantage_band_v1", dropna=False):
        row = summarize(g, f"PACE_BAND_{b}")
        row["pace_advantage_band_v1"] = b
        row["lift_vs_base_points"] = (
            round(float(row["win_rate_pct"]) - base_wr, 3)
            if pd.notna(row["win_rate_pct"])
            else np.nan
        )
        by_band_rows.append(row)

    by_band = pd.DataFrame(by_band_rows)

    by_trust_rows = []
    for keys, g in v4_sig.groupby(["trust_profile_v1", "pace_advantage_band_v1"], dropna=False):
        trust, pace_band = keys
        row = summarize(g, f"{trust}__{pace_band}")
        row["trust_profile_v1"] = trust
        row["pace_advantage_band_v1"] = pace_band
        by_trust_rows.append(row)

    by_trust = pd.DataFrame(by_trust_rows)

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
    ]
    detail_cols = [c for c in detail_cols if c in df.columns]

    df[detail_cols].to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_band.to_csv(OUT_BY_BAND, index=False)
    by_trust.to_csv(OUT_BY_TRUST, index=False)

    best_lift = summary["lift_vs_base_points"].max()

    if pd.notna(best_lift) and best_lift >= 1.0:
        conclusion = "PACE_ADVANTAGE_ADDS_INFORMATION"
    elif pd.notna(best_lift) and best_lift <= -1.0:
        conclusion = "PACE_ADVANTAGE_CURRENT_SCALE_HURTS"
    else:
        conclusion = "PACE_ADVANTAGE_NOT_PROVEN_YET"

    audit = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "v4_rows_loaded", "value": len(v4)},
        {"metric": "dna_rows_loaded", "value": len(dna)},
        {"metric": "merged_rows", "value": len(df)},
        {"metric": "base_v4_signals", "value": len(v4_sig)},
        {"metric": "known_pace_v4_signals", "value": int((v4_sig["pace_role_v1"] != "UNKNOWN").sum())},
        {"metric": "known_pace_v4_pct", "value": round(float((v4_sig["pace_role_v1"] != "UNKNOWN").mean()) * 100.0, 2) if len(v4_sig) else 0},
        {"metric": "best_lift_points", "value": best_lift},
        {"metric": "final_conclusion", "value": conclusion},
    ])

    audit.to_csv(OUT_AUDIT, index=False)

    print("[PACE_ADVANTAGE_REPLAY_V1] COMPLETE")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_BAND}")
    print(f"wrote={OUT_BY_TRUST}")
    print(f"wrote={OUT_AUDIT}")


if __name__ == "__main__":
    main()
