from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_V3 = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v3_environment.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v3_replay.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v3_replay_summary.csv")
OUT_BY_YEAR = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v3_replay_by_year.csv")
OUT_BY_FIELD = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v3_replay_by_field_size.csv")
OUT_BY_ENV = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v3_replay_by_environment_band.csv")
OUT_VERDICT = os.path.join(DATA, "edgeiq_strength_adjusted_ratings_v3_replay_verdict.csv")


def num(x):
    return pd.to_numeric(x, errors="coerce")


def pct(x):
    if pd.isna(x):
        return np.nan
    return round(float(x) * 100.0, 2)


def choose_win(df):
    if "won" in df.columns:
        return num(df["won"]).fillna(0).astype(int), "won"
    if "rank1_won" in df.columns:
        return num(df["rank1_won"]).fillna(0).astype(int), "rank1_won"
    if "finish_position" in df.columns:
        return (num(df["finish_position"]) == 1).astype(int), "finish_position"
    raise ValueError("No win column found")


def choose_place(df):
    if "placed" in df.columns:
        return num(df["placed"]).fillna(0).astype(int), "placed"
    if "rank1_placed" in df.columns:
        return num(df["rank1_placed"]).fillna(0).astype(int), "rank1_placed"
    if "finish_position" in df.columns:
        fp = num(df["finish_position"])
        return ((fp >= 1) & (fp <= 3)).astype(int), "finish_position"
    return pd.Series([0] * len(df), index=df.index), "none"


def rank_in_race(df, rating_col, out_col):
    df[out_col] = (
        df.groupby("race_key_for_replay")[rating_col]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    return df


def race_summary(df, label, rank_col):
    rank1 = df[df[rank_col] == 1].copy()
    top2 = df[df[rank_col] <= 2].copy()
    top3 = df[df[rank_col] <= 3].copy()

    races = int(df["race_key_for_replay"].nunique())

    if races == 0:
        return {
            "model": label,
            "races": 0,
            "rank1_wins": 0,
            "rank1_win_rate_pct": np.nan,
            "rank1_places": 0,
            "rank1_place_rate_pct": np.nan,
            "top2_winner_capture_pct": np.nan,
            "top3_winner_capture_pct": np.nan,
            "avg_rank1_rating": np.nan,
            "avg_rank1_env_score": np.nan,
        }

    top2_winner_races = int(top2.groupby("race_key_for_replay")["won_final"].max().sum())
    top3_winner_races = int(top3.groupby("race_key_for_replay")["won_final"].max().sum())

    return {
        "model": label,
        "races": races,
        "rank1_wins": int(rank1["won_final"].sum()),
        "rank1_win_rate_pct": pct(rank1["won_final"].mean()) if len(rank1) else np.nan,
        "rank1_places": int(rank1["placed_final"].sum()),
        "rank1_place_rate_pct": pct(rank1["placed_final"].mean()) if len(rank1) else np.nan,
        "top2_winner_capture_pct": round((top2_winner_races / races) * 100.0, 2),
        "top3_winner_capture_pct": round((top3_winner_races / races) * 100.0, 2),
        "avg_rank1_rating": round(float(rank1["rating_for_summary"].mean()), 3) if len(rank1) else np.nan,
        "avg_rank1_env_score": round(float(rank1["environment_score_num"].mean()), 3) if len(rank1) else np.nan,
    }


def compare_group(df, group_col):
    rows = []

    for group, g in df.groupby(group_col, dropna=False):
        v2 = race_summary(g.copy(), "V2_BASE_RUNNER_SCORE", "rank_v2")
        v3 = race_summary(g.copy(), "V3_ENVIRONMENT_ADJUSTED", "rank_v3")

        v2[group_col] = group
        v3[group_col] = group

        rows.append(v2)
        rows.append(v3)

    return pd.DataFrame(rows)


def main():
    if not os.path.exists(IN_V3):
        raise FileNotFoundError(IN_V3)

    df = pd.read_csv(IN_V3, low_memory=False)

    if "race_join_key_fixed" in df.columns:
        df["race_key_for_replay"] = df["race_join_key_fixed"].astype(str)
    elif "race_key" in df.columns:
        df["race_key_for_replay"] = df["race_key"].astype(str)
    else:
        df["race_key_for_replay"] = (
            df["meeting_date"].astype(str)
            + "|"
            + df["track"].astype(str)
            + "|"
            + df["race_no"].astype(str)
        )

    wins, win_source = choose_win(df)
    places, place_source = choose_place(df)

    df["won_final"] = wins
    df["placed_final"] = places

    if "base_rating_for_v3_environment" not in df.columns:
        raise ValueError("Missing base_rating_for_v3_environment column")

    if "strength_adjusted_rating_v3_environment" not in df.columns:
        raise ValueError("Missing strength_adjusted_rating_v3_environment column")

    df["rating_v2"] = num(df["base_rating_for_v3_environment"])
    df["rating_v3"] = num(df["strength_adjusted_rating_v3_environment"])

    df = df[df["rating_v2"].notna() & df["rating_v3"].notna()].copy()

    df["environment_score_num"] = num(df.get("environment_score_v1")).fillna(0)
    df["rating_for_summary"] = df["rating_v2"]

    if "meeting_date" in df.columns:
        df["year"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    elif "race_date" in df.columns:
        df["year"] = pd.to_datetime(df["race_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    else:
        df["year"] = "UNKNOWN"

    df = rank_in_race(df, "rating_v2", "rank_v2")
    df = rank_in_race(df, "rating_v3", "rank_v3")

    df["v3_promoted_rank1"] = (df["rank_v3"] == 1) & (df["rank_v2"] != 1)
    df["v3_demoted_from_rank1"] = (df["rank_v2"] == 1) & (df["rank_v3"] != 1)

    v2_summary = race_summary(df.copy(), "V2_BASE_RUNNER_SCORE", "rank_v2")
    df["rating_for_summary"] = df["rating_v3"]
    v3_summary = race_summary(df.copy(), "V3_ENVIRONMENT_ADJUSTED", "rank_v3")

    summary = pd.DataFrame([v2_summary, v3_summary])

    v2_rank1 = float(summary.loc[summary["model"] == "V2_BASE_RUNNER_SCORE", "rank1_win_rate_pct"].iloc[0])
    v3_rank1 = float(summary.loc[summary["model"] == "V3_ENVIRONMENT_ADJUSTED", "rank1_win_rate_pct"].iloc[0])

    v2_top2 = float(summary.loc[summary["model"] == "V2_BASE_RUNNER_SCORE", "top2_winner_capture_pct"].iloc[0])
    v3_top2 = float(summary.loc[summary["model"] == "V3_ENVIRONMENT_ADJUSTED", "top2_winner_capture_pct"].iloc[0])

    v2_top3 = float(summary.loc[summary["model"] == "V2_BASE_RUNNER_SCORE", "top3_winner_capture_pct"].iloc[0])
    v3_top3 = float(summary.loc[summary["model"] == "V3_ENVIRONMENT_ADJUSTED", "top3_winner_capture_pct"].iloc[0])

    summary["rank1_lift_vs_v2_points"] = summary["rank1_win_rate_pct"].apply(
        lambda x: round(float(x) - v2_rank1, 3) if pd.notna(x) else np.nan
    )
    summary["top2_lift_vs_v2_points"] = summary["top2_winner_capture_pct"].apply(
        lambda x: round(float(x) - v2_top2, 3) if pd.notna(x) else np.nan
    )
    summary["top3_lift_vs_v2_points"] = summary["top3_winner_capture_pct"].apply(
        lambda x: round(float(x) - v2_top3, 3) if pd.notna(x) else np.nan
    )

    by_year = compare_group(df, "year") if "year" in df.columns else pd.DataFrame()
    by_field = compare_group(df, "field_size_bucket_v1") if "field_size_bucket_v1" in df.columns else pd.DataFrame()
    by_env = compare_group(df, "environment_band_v1") if "environment_band_v1" in df.columns else pd.DataFrame()

    rank1_changes = (
        df.groupby("race_key_for_replay")
        .apply(
            lambda g: pd.Series({
                "v2_rank1_horse": g.loc[g["rank_v2"].idxmin(), "horse"],
                "v3_rank1_horse": g.loc[g["rank_v3"].idxmin(), "horse"],
                "v2_rank1_won": int(g.loc[g["rank_v2"].idxmin(), "won_final"]),
                "v3_rank1_won": int(g.loc[g["rank_v3"].idxmin(), "won_final"]),
                "changed_rank1": bool(g.loc[g["rank_v2"].idxmin(), "horse"] != g.loc[g["rank_v3"].idxmin(), "horse"]),
            })
        )
        .reset_index()
    )

    changed = rank1_changes[rank1_changes["changed_rank1"]].copy()
    changed_races = int(len(changed))
    total_races = int(df["race_key_for_replay"].nunique())
    changed_rate = round((changed_races / total_races) * 100.0, 2) if total_races else 0

    if (
        v3_rank1 > v2_rank1
        and v3_top2 >= v2_top2
        and v3_top3 >= v2_top3
    ):
        final = "V3_ENVIRONMENT_RATINGS_PROMOTION_PASS"
    elif v3_rank1 > v2_rank1:
        final = "V3_ENVIRONMENT_RATINGS_RANK1_ONLY_PASS"
    else:
        final = "V3_ENVIRONMENT_RATINGS_NOT_READY"

    verdict = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_V3},
        {"metric": "rows", "value": len(df)},
        {"metric": "races", "value": total_races},
        {"metric": "win_source", "value": win_source},
        {"metric": "place_source", "value": place_source},
        {"metric": "v2_rank1_win_rate_pct", "value": v2_rank1},
        {"metric": "v3_rank1_win_rate_pct", "value": v3_rank1},
        {"metric": "rank1_lift_points", "value": round(v3_rank1 - v2_rank1, 3)},
        {"metric": "v2_top2_capture_pct", "value": v2_top2},
        {"metric": "v3_top2_capture_pct", "value": v3_top2},
        {"metric": "top2_lift_points", "value": round(v3_top2 - v2_top2, 3)},
        {"metric": "v2_top3_capture_pct", "value": v2_top3},
        {"metric": "v3_top3_capture_pct", "value": v3_top3},
        {"metric": "top3_lift_points", "value": round(v3_top3 - v2_top3, 3)},
        {"metric": "changed_rank1_races", "value": changed_races},
        {"metric": "changed_rank1_rate_pct", "value": changed_rate},
        {"metric": "final_conclusion", "value": final},
    ])

    wanted = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "race_key_for_replay",
        "rating_v2",
        "rating_v3",
        "rank_v2",
        "rank_v3",
        "won_final",
        "placed_final",
        "environment_score_v1",
        "environment_band_v1",
        "environment_adjustment_v3",
        "strength_adjusted_reason_v3_environment",
        "score_share_of_race",
        "dominance_score_v1",
        "trust_profile_v1",
        "field_size_bucket_v1",
        "edge_proxy_pct",
        "finish_position",
    ]
    wanted = [c for c in wanted if c in df.columns]

    df[wanted].to_csv(OUT_DETAIL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_year.to_csv(OUT_BY_YEAR, index=False)
    by_field.to_csv(OUT_BY_FIELD, index=False)
    by_env.to_csv(OUT_BY_ENV, index=False)
    verdict.to_csv(OUT_VERDICT, index=False)

    print("[STRENGTH_ADJUSTED_RATINGS_V3_REPLAY] COMPLETE")
    print(f"win_source={win_source}")
    print(f"place_source={place_source}")
    print(f"wrote={OUT_DETAIL}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_YEAR}")
    print(f"wrote={OUT_BY_FIELD}")
    print(f"wrote={OUT_BY_ENV}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
