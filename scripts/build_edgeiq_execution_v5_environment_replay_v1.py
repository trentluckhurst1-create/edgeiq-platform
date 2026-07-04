from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_FILE = os.path.join(DATA, "edgeiq_environment_score_replay_v1.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_execution_v5_environment_replay_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_execution_v5_environment_replay_v1_summary.csv")
OUT_BY_YEAR = os.path.join(DATA, "edgeiq_execution_v5_environment_replay_v1_by_year.csv")
OUT_BY_TRUST = os.path.join(DATA, "edgeiq_execution_v5_environment_replay_v1_by_trust.csv")
OUT_BY_FIELD = os.path.join(DATA, "edgeiq_execution_v5_environment_replay_v1_by_field_size.csv")
OUT_BY_SCORE = os.path.join(DATA, "edgeiq_execution_v5_environment_replay_v1_by_score_bucket.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_execution_v5_environment_replay_v1_verdict.csv")


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


def choose_wins(df):
    if "won_num" in df.columns:
        return num(df["won_num"]).fillna(0).astype(int), "won_num"

    if "won" in df.columns:
        return num(df["won"]).fillna(0).astype(int), "won"

    if "rank1_won" in df.columns:
        return num(df["rank1_won"]).fillna(0).astype(int), "rank1_won"

    if "finish_position" in df.columns:
        return (num(df["finish_position"]) == 1).astype(int), "finish_position"

    raise ValueError("No win column found")


def choose_places(df):
    if "placed_num" in df.columns:
        return num(df["placed_num"]).fillna(0).astype(int), "placed_num"

    if "placed" in df.columns:
        return num(df["placed"]).fillna(0).astype(int), "placed"

    if "rank1_placed" in df.columns:
        return num(df["rank1_placed"]).fillna(0).astype(int), "rank1_placed"

    if "finish_position" in df.columns:
        fp = num(df["finish_position"])
        return ((fp >= 1) & (fp <= 3)).astype(int), "finish_position"

    return pd.Series([0] * len(df), index=df.index), "none"


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
            "avg_runner_score": np.nan,
            "avg_field_size": np.nan,
        }

    return {
        "segment": segment,
        "signals": int(len(df)),
        "races": int(df["race_join_key_fixed"].nunique()) if "race_join_key_fixed" in df.columns else int(len(df)),
        "wins": int(df["won_final"].sum()),
        "places": int(df["placed_final"].sum()),
        "win_rate_pct": pct(df["won_final"].mean()),
        "place_rate_pct": pct(df["placed_final"].mean()),
        "avg_environment_score": round(float(df["environment_score_num"].mean()), 3),
        "avg_score_share": round(float(df["score_share_num"].mean()), 6) if df["score_share_num"].notna().any() else np.nan,
        "avg_dominance": round(float(df["dominance_num"].mean()), 3) if df["dominance_num"].notna().any() else np.nan,
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3) if df["edge_proxy_num"].notna().any() else np.nan,
        "avg_runner_score": round(float(df["runner_score_num"].mean()), 3) if df["runner_score_num"].notna().any() else np.nan,
        "avg_field_size": round(float(df["field_size_num"].mean()), 3) if df["field_size_num"].notna().any() else np.nan,
    }


def add_lift(frame, base_wr):
    frame["lift_vs_base_points"] = frame["win_rate_pct"].apply(
        lambda x: round(float(x) - float(base_wr), 3)
        if pd.notna(x) and pd.notna(base_wr)
        else np.nan
    )
    return frame


def group_report(df, cols, prefix, base_wr):
    rows = []

    for keys, g in df.groupby(cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        label = prefix + "__" + "__".join([str(k) for k in keys])
        row = summarise(g, label)

        for c, k in zip(cols, keys):
            row[c] = k

        rows.append(row)

    return add_lift(pd.DataFrame(rows), base_wr)


def main():
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(IN_FILE)

    df = pd.read_csv(IN_FILE, low_memory=False)

    wins, win_source = choose_wins(df)
    places, place_source = choose_places(df)

    df["won_final"] = wins
    df["placed_final"] = places

    df["environment_score_num"] = num(df["environment_score_v1"]).fillna(0)
    df["environment_score_bucket_v1"] = df["environment_score_num"].map(score_bucket)

    df["score_share_num"] = num(df.get("score_share_of_race"))
    df["dominance_num"] = num(df.get("dominance_score_v1"))
    df["edge_proxy_num"] = num(df.get("edge_proxy_pct"))
    df["runner_score_num"] = num(df.get("runner_score"))
    df["field_size_num"] = num(df.get("field_size"))

    if "meeting_date" in df.columns:
        df["year"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    elif "race_date" in df.columns:
        df["year"] = pd.to_datetime(df["race_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    else:
        df["year"] = "UNKNOWN"

    base_row = summarise(df, "BASE_V4")
    base_wr = float(base_row["win_rate_pct"])

    env_ge_3 = df[df["environment_score_num"] >= 3].copy()
    env_ge_5 = df[df["environment_score_num"] >= 5].copy()
    env_ge_7 = df[df["environment_score_num"] >= 7].copy()
    env_band_elite = df[df["environment_band_v1"].astype(str).str.upper() == "ELITE"].copy()
    env_band_positive_plus = df[
        df["environment_band_v1"].astype(str).str.upper().isin(["POSITIVE", "ELITE"])
    ].copy()

    env_low_0_2 = df[df["environment_score_num"] <= 2].copy()
    env_mid_3_4 = df[df["environment_score_num"].between(3, 4)].copy()
    env_high_5_plus = df[df["environment_score_num"] >= 5].copy()

    summary = pd.DataFrame([
        base_row,
        summarise(env_low_0_2, "V5_REJECT_LOW_ENV_0_2"),
        summarise(env_mid_3_4, "V5_QUALIFY_ENV_3_4"),
        summarise(env_high_5_plus, "V5_QUALIFY_ENV_5_PLUS"),
        summarise(env_ge_3, "V5_ENV_SCORE_GE_3"),
        summarise(env_ge_5, "V5_ENV_SCORE_GE_5"),
        summarise(env_ge_7, "V5_ENV_SCORE_GE_7"),
        summarise(env_band_positive_plus, "V5_ENV_BAND_POSITIVE_PLUS"),
        summarise(env_band_elite, "V5_ENV_BAND_ELITE"),
    ])

    summary = add_lift(summary, base_wr)

    by_score = group_report(df, ["environment_score_bucket_v1"], "SCORE_BUCKET", base_wr)
    by_year = group_report(df, ["year", "environment_score_bucket_v1"], "YEAR_SCORE", base_wr)
    by_trust = group_report(df, ["trust_profile_v1", "environment_score_bucket_v1"], "TRUST_SCORE", base_wr)
    by_field = group_report(df, ["field_size_bucket_v1", "environment_score_bucket_v1"], "FIELD_SCORE", base_wr)

    # Stability of the proposed V5 execution cut:
    # V5_ENV_SCORE_GE_3 should beat low env 0-2 every tested year.
    stability_rows = []

    for year, g in df.groupby("year", dropna=False):
        low = g[g["environment_score_num"] <= 2]
        high = g[g["environment_score_num"] >= 3]

        low_row = summarise(low, f"YEAR_{year}_LOW_0_2")
        high_row = summarise(high, f"YEAR_{year}_GE_3")

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
            "ge3_signals": high_row["signals"],
            "ge3_win_rate_pct": high_wr,
            "ge3_minus_low_points": lift,
            "year_pass": bool(
                low_row["signals"] >= 100
                and high_row["signals"] >= 100
                and pd.notna(lift)
                and lift > 0
            ),
        })

    stability = pd.DataFrame(stability_rows)

    years_tested_df = stability[
        (stability["low_signals"] >= 100) &
        (stability["ge3_signals"] >= 100)
    ].copy()

    years_tested = int(len(years_tested_df))
    years_passed = int(years_tested_df["year_pass"].sum()) if years_tested else 0
    min_year_lift = (
        round(float(years_tested_df["ge3_minus_low_points"].min()), 3)
        if years_tested
        else np.nan
    )
    avg_year_lift = (
        round(float(years_tested_df["ge3_minus_low_points"].mean()), 3)
        if years_tested
        else np.nan
    )

    ge3_row = summary[summary["segment"] == "V5_ENV_SCORE_GE_3"].iloc[0]
    ge5_row = summary[summary["segment"] == "V5_ENV_SCORE_GE_5"].iloc[0]
    low_row = summary[summary["segment"] == "V5_REJECT_LOW_ENV_0_2"].iloc[0]

    ge3_lift = ge3_row["lift_vs_base_points"]
    ge5_lift = ge5_row["lift_vs_base_points"]
    low_lift = low_row["lift_vs_base_points"]

    ge3_signals = int(ge3_row["signals"])
    ge5_signals = int(ge5_row["signals"])

    if (
        pd.notna(ge3_lift)
        and pd.notna(ge5_lift)
        and ge3_signals >= 1000
        and ge3_lift >= 3.0
        and ge5_signals >= 250
        and ge5_lift >= ge3_lift
        and years_tested >= 3
        and years_passed == years_tested
    ):
        final = "V5_ENVIRONMENT_LAYER_READY"
    elif (
        pd.notna(ge3_lift)
        and ge3_signals >= 1000
        and ge3_lift >= 2.0
        and years_tested >= 3
        and years_passed >= years_tested - 1
    ):
        final = "V5_ENVIRONMENT_LAYER_READY_WITH_CAUTION"
    else:
        final = "V5_ENVIRONMENT_LAYER_NOT_READY"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_FILE},
        {"metric": "signals", "value": len(df)},
        {"metric": "win_source", "value": win_source},
        {"metric": "place_source", "value": place_source},
        {"metric": "base_win_rate_pct", "value": base_wr},
        {"metric": "low_env_0_2_win_rate_pct", "value": low_row["win_rate_pct"]},
        {"metric": "low_env_0_2_lift_points", "value": low_lift},
        {"metric": "env_ge_3_signals", "value": ge3_signals},
        {"metric": "env_ge_3_win_rate_pct", "value": ge3_row["win_rate_pct"]},
        {"metric": "env_ge_3_lift_points", "value": ge3_lift},
        {"metric": "env_ge_5_signals", "value": ge5_signals},
        {"metric": "env_ge_5_win_rate_pct", "value": ge5_row["win_rate_pct"]},
        {"metric": "env_ge_5_lift_points", "value": ge5_lift},
        {"metric": "years_tested", "value": years_tested},
        {"metric": "years_passed", "value": years_passed},
        {"metric": "min_year_ge3_minus_low_points", "value": min_year_lift},
        {"metric": "avg_year_ge3_minus_low_points", "value": avg_year_lift},
        {"metric": "final_conclusion", "value": final},
    ])

    df.to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    stability.to_csv(OUT_BY_YEAR, index=False)
    by_trust.to_csv(OUT_BY_TRUST, index=False)
    by_field.to_csv(OUT_BY_FIELD, index=False)
    by_score.to_csv(OUT_BY_SCORE, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[EXECUTION_V5_ENVIRONMENT_REPLAY_V1] COMPLETE")
    print(f"win_source={win_source}")
    print(f"place_source={place_source}")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_YEAR}")
    print(f"wrote={OUT_BY_TRUST}")
    print(f"wrote={OUT_BY_FIELD}")
    print(f"wrote={OUT_BY_SCORE}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
