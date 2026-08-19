from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_FILE = os.path.join(DATA, "edgeiq_environment_score_replay_v1.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_environment_score_stability_audit_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_environment_score_stability_audit_v1_summary.csv")
OUT_BY_YEAR = os.path.join(DATA, "edgeiq_environment_score_stability_audit_v1_by_year.csv")
OUT_BY_YEAR_SCORE = os.path.join(DATA, "edgeiq_environment_score_stability_audit_v1_by_year_score.csv")
OUT_BY_TRUST_SCORE = os.path.join(DATA, "edgeiq_environment_score_stability_audit_v1_by_trust_score.csv")
OUT_BY_FIELD_SCORE = os.path.join(DATA, "edgeiq_environment_score_stability_audit_v1_by_field_score.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_environment_score_stability_audit_v1_verdict.csv")


def num(x):
    return pd.to_numeric(x, errors="coerce")


def pct(x):
    if pd.isna(x):
        return np.nan
    return round(float(x) * 100.0, 2)


def score_bucket(x):
    try:
        v = float(x)
    except Exception:
        return "UNKNOWN"

    if v == 0:
        return "SCORE_0"
    if v <= 2:
        return "SCORE_1_2"
    if v <= 4:
        return "SCORE_3_4"
    if v <= 6:
        return "SCORE_5_6"
    return "SCORE_7_PLUS"


def score_bucket_rank(x):
    order = {
        "SCORE_0": 0,
        "SCORE_1_2": 1,
        "SCORE_3_4": 2,
        "SCORE_5_6": 3,
        "SCORE_7_PLUS": 4,
    }
    return order.get(str(x), -1)


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
        "place_rate_pct": pct(df["placed_num"].mean()),
        "avg_environment_score": round(float(df["environment_score_num"].mean()), 3),
        "avg_score_share": round(float(df["score_share_num"].mean()), 6) if df["score_share_num"].notna().any() else np.nan,
        "avg_dominance": round(float(df["dominance_num"].mean()), 3) if df["dominance_num"].notna().any() else np.nan,
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3) if df["edge_proxy_num"].notna().any() else np.nan,
    }


def group_report(df, cols, prefix):
    rows = []

    for keys, g in df.groupby(cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        row = summarise(g, prefix + "__" + "__".join([str(k) for k in keys]))

        for c, k in zip(cols, keys):
            row[c] = k

        rows.append(row)

    return pd.DataFrame(rows)


def add_base_lift(frame, base_wr):
    if len(frame):
        frame["lift_vs_base_points"] = frame["win_rate_pct"].apply(
            lambda x: round(float(x) - base_wr, 3)
            if pd.notna(x) and pd.notna(base_wr)
            else np.nan
        )
    return frame


def main():
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(IN_FILE)

    df = pd.read_csv(IN_FILE, low_memory=False)

    if "won_num" not in df.columns:
        if "won" in df.columns:
            df["won_num"] = num(df["won"]).fillna(0).astype(int)
        elif "finish_position" in df.columns:
            df["won_num"] = (num(df["finish_position"]) == 1).astype(int)
        else:
            raise ValueError("No won_num, won, or finish_position column found")

    if "placed_num" not in df.columns:
        if "placed" in df.columns:
            df["placed_num"] = num(df["placed"]).fillna(0).astype(int)
        elif "finish_position" in df.columns:
            fp = num(df["finish_position"])
            df["placed_num"] = ((fp >= 1) & (fp <= 3)).astype(int)
        else:
            df["placed_num"] = 0

    df["environment_score_num"] = num(df["environment_score_v1"]).fillna(0)
    df["environment_score_bucket_v1"] = df["environment_score_num"].map(score_bucket)
    df["environment_score_bucket_rank_v1"] = df["environment_score_bucket_v1"].map(score_bucket_rank)

    df["score_share_num"] = num(df.get("score_share_of_race"))
    df["dominance_num"] = num(df.get("dominance_score_v1"))
    df["edge_proxy_num"] = num(df.get("edge_proxy_pct"))

    if "meeting_date" in df.columns:
        df["year"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    elif "race_date" in df.columns:
        df["year"] = pd.to_datetime(df["race_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    else:
        df["year"] = "UNKNOWN"

    base = summarise(df, "BASE_V4")
    base_wr = float(base["win_rate_pct"])

    low_env = df[df["environment_score_bucket_v1"].isin(["SCORE_0", "SCORE_1_2"])].copy()
    mid_env = df[df["environment_score_bucket_v1"].isin(["SCORE_3_4"])].copy()
    high_env = df[df["environment_score_bucket_v1"].isin(["SCORE_5_6", "SCORE_7_PLUS"])].copy()

    summary = pd.DataFrame([
        base,
        summarise(low_env, "LOW_ENV_SCORE_0_TO_2"),
        summarise(mid_env, "MID_ENV_SCORE_3_TO_4"),
        summarise(high_env, "HIGH_ENV_SCORE_5_PLUS"),
        summarise(df[df["environment_band_v1"].astype(str) == "POOR"], "BAND_POOR"),
        summarise(df[df["environment_band_v1"].astype(str) == "NEGATIVE"], "BAND_NEGATIVE"),
        summarise(df[df["environment_band_v1"].astype(str) == "NEUTRAL"], "BAND_NEUTRAL"),
        summarise(df[df["environment_band_v1"].astype(str) == "POSITIVE"], "BAND_POSITIVE"),
        summarise(df[df["environment_band_v1"].astype(str) == "ELITE"], "BAND_ELITE"),
    ])

    summary = add_base_lift(summary, base_wr)

    by_year = add_base_lift(group_report(df, ["year"], "YEAR"), base_wr)
    by_year_score = add_base_lift(group_report(df, ["year", "environment_score_bucket_v1"], "YEAR_SCORE"), base_wr)
    by_trust_score = add_base_lift(group_report(df, ["trust_profile_v1", "environment_score_bucket_v1"], "TRUST_SCORE"), base_wr)
    by_field_score = add_base_lift(group_report(df, ["field_size_bucket_v1", "environment_score_bucket_v1"], "FIELD_SCORE"), base_wr)

    # Stability pass/fail:
    # For every year with enough samples, high env (score 3+) should beat low env (0-2).
    stability_rows = []

    for year, g in df.groupby("year", dropna=False):
        low = g[g["environment_score_bucket_v1"].isin(["SCORE_0", "SCORE_1_2"])]
        high = g[g["environment_score_bucket_v1"].isin(["SCORE_3_4", "SCORE_5_6", "SCORE_7_PLUS"])]

        low_row = summarise(low, f"YEAR_{year}_LOW_0_2")
        high_row = summarise(high, f"YEAR_{year}_HIGH_3_PLUS")

        low_wr = low_row["win_rate_pct"]
        high_wr = high_row["win_rate_pct"]

        lift = (
            round(float(high_wr) - float(low_wr), 3)
            if pd.notna(low_wr) and pd.notna(high_wr)
            else np.nan
        )

        stability_rows.append({
            "year": year,
            "low_signals": low_row["signals"],
            "low_win_rate_pct": low_wr,
            "high_signals": high_row["signals"],
            "high_win_rate_pct": high_wr,
            "high_minus_low_points": lift,
            "year_pass": bool(
                low_row["signals"] >= 100
                and high_row["signals"] >= 100
                and pd.notna(lift)
                and lift > 0
            ),
        })

    stability = pd.DataFrame(stability_rows)

    tested = stability[(stability["low_signals"] >= 100) & (stability["high_signals"] >= 100)].copy()
    years_tested = int(len(tested))
    years_passed = int(tested["year_pass"].sum()) if len(tested) else 0
    min_year_lift = round(float(tested["high_minus_low_points"].min()), 3) if len(tested) else np.nan
    avg_year_lift = round(float(tested["high_minus_low_points"].mean()), 3) if len(tested) else np.nan

    high_overall = summarise(high_env, "HIGH_ENV_SCORE_5_PLUS")
    low_overall = summarise(low_env, "LOW_ENV_SCORE_0_TO_2")

    overall_lift = (
        round(float(high_overall["win_rate_pct"]) - float(low_overall["win_rate_pct"]), 3)
        if pd.notna(high_overall["win_rate_pct"]) and pd.notna(low_overall["win_rate_pct"])
        else np.nan
    )

    if years_tested >= 3 and years_passed == years_tested and pd.notna(overall_lift) and overall_lift >= 5:
        final = "ENVIRONMENT_SCORE_STABILITY_PASS"
    elif years_tested >= 3 and years_passed >= years_tested - 1 and pd.notna(overall_lift) and overall_lift >= 3:
        final = "ENVIRONMENT_SCORE_STABILITY_MODERATE"
    else:
        final = "ENVIRONMENT_SCORE_STABILITY_NOT_PROVEN"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_FILE},
        {"metric": "signals", "value": len(df)},
        {"metric": "base_win_rate_pct", "value": base_wr},
        {"metric": "low_env_signals_0_2", "value": low_overall["signals"]},
        {"metric": "low_env_win_rate_pct", "value": low_overall["win_rate_pct"]},
        {"metric": "high_env_signals_5_plus", "value": high_overall["signals"]},
        {"metric": "high_env_win_rate_pct", "value": high_overall["win_rate_pct"]},
        {"metric": "high_minus_low_points", "value": overall_lift},
        {"metric": "years_tested", "value": years_tested},
        {"metric": "years_passed", "value": years_passed},
        {"metric": "min_year_lift_points", "value": min_year_lift},
        {"metric": "avg_year_lift_points", "value": avg_year_lift},
        {"metric": "final_conclusion", "value": final},
    ])

    df.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_year.to_csv(OUT_BY_YEAR, index=False)
    by_year_score.to_csv(OUT_BY_YEAR_SCORE, index=False)
    by_trust_score.to_csv(OUT_BY_TRUST_SCORE, index=False)
    by_field_score.to_csv(OUT_BY_FIELD_SCORE, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[ENVIRONMENT_SCORE_STABILITY_AUDIT_V1] COMPLETE")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_YEAR}")
    print(f"wrote={OUT_BY_YEAR_SCORE}")
    print(f"wrote={OUT_BY_TRUST_SCORE}")
    print(f"wrote={OUT_BY_FIELD_SCORE}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
