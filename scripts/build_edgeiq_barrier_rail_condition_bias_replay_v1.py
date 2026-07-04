from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from edgeiq_bias_common_v1 import (
    condition_group as common_condition_group,
    load_results_base,
    normalize_horse_key,
    normalize_track,
    safe_num,
    win_place_score,
    write_csv,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_RAIL = DATA / "edgeiq_historical_rail_backfill_v1.csv"
IN_RANK1 = DATA / "edgeiq_rank1_failure_audit_v1.csv"
IN_BIAS_RELEVANCE_DETAIL = DATA / "edgeiq_bias_factor_relevance_audit_v1.csv"
IN_BIAS_RELEVANCE_SUMMARY = DATA / "edgeiq_bias_factor_relevance_audit_summary_v1.csv"

OUT_MAIN = DATA / "edgeiq_barrier_rail_condition_bias_replay_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_barrier_rail_condition_bias_replay_v1_summary.csv"
OUT_BY_BUCKET = DATA / "edgeiq_barrier_rail_condition_bias_replay_by_bucket_v1.csv"
OUT_RANK1 = DATA / "edgeiq_barrier_rail_condition_bias_rank1_relevance_v1.csv"
OUT_JSON = DATA / "edgeiq_barrier_rail_condition_bias_replay_v1.json"

RAIL_BUCKETS = ["TRUE", "0_3M", "3_6M", "6_9M", "9_12M", "12M_PLUS", "UNKNOWN"]
BARRIER_BUCKETS = ["1_2", "3_4", "5_6", "7_8", "9_10", "11_12", "13_PLUS"]
CONDITION_BUCKETS = ["GOOD", "SOFT", "HEAVY", "UNKNOWN"]


def pct(numerator, denominator):
    if denominator in (0, None) or pd.isna(denominator):
        return np.nan
    return round(float(numerator) / float(denominator) * 100.0, 2)


def normalize_barrier_bucket(value: str) -> str:
    text = "" if pd.isna(value) else str(value).strip().upper().replace("-", "_")
    if text == "13+":
        return "13_PLUS"
    if text in {"1_2", "3_4", "5_6", "7_8", "9_10", "11_12", "13_PLUS"}:
        return text
    return "UNKNOWN"


def replay_condition_group(value) -> str:
    group = common_condition_group(value)
    if group in {"GOOD", "SOFT", "HEAVY"}:
        return group
    return "UNKNOWN"


def barrier_rail_condition_band(lift_pts, starts) -> str:
    if pd.isna(lift_pts):
        return "UNKNOWN"
    if float(starts) >= 80 and float(lift_pts) >= 4.0:
        return "STRONG_POSITIVE"
    if float(starts) >= 50 and float(lift_pts) >= 2.0:
        return "POSITIVE"
    if float(starts) >= 80 and float(lift_pts) <= -4.0:
        return "STRONG_NEGATIVE"
    if float(starts) >= 50 and float(lift_pts) <= -2.0:
        return "NEGATIVE"
    return "NEUTRAL"


def load_rail_sidecar() -> pd.DataFrame:
    df = pd.read_csv(IN_RAIL, low_memory=False)
    out = pd.DataFrame()
    out["meeting_date"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["track_norm"] = df["normalized_track"].fillna(df["track"].map(normalize_track)).astype(str)
    out["race_no"] = safe_num(df["race_no"]).astype("Int64")
    out["rail_position"] = df["rail_position"].fillna("").astype(str)
    out["rail_bucket"] = df["rail_bucket"].fillna("UNKNOWN").astype(str).str.upper()
    out["track_condition_graphql"] = df["track_condition_graphql"].fillna("").astype(str)
    out["weather_graphql"] = df["weather_graphql"].fillna("").astype(str)
    out["penetrometer_graphql"] = df["penetrometer_graphql"].fillna("").astype(str)
    out["source_status"] = df["source_status"].fillna("UNKNOWN").astype(str)
    out = out.drop_duplicates(subset=["meeting_date", "track_norm", "race_no"], keep="first")
    return out


def load_replay_base() -> pd.DataFrame:
    results = load_results_base().copy()
    results["barrier_bucket_replay_v1"] = results["barrier_bucket_v1"].map(normalize_barrier_bucket)
    rail = load_rail_sidecar()
    merged = results.merge(
        rail,
        on=["meeting_date", "track_norm", "race_no"],
        how="left",
    )
    merged["rail_bucket"] = merged["rail_bucket"].fillna("UNKNOWN").astype(str).str.upper()
    merged.loc[~merged["rail_bucket"].isin(RAIL_BUCKETS), "rail_bucket"] = "UNKNOWN"
    merged["track_condition_effective_v1"] = merged["track_condition_graphql"]
    missing_condition = merged["track_condition_effective_v1"].fillna("").astype(str).str.strip().eq("")
    merged.loc[missing_condition, "track_condition_effective_v1"] = merged.loc[missing_condition, "track_condition_raw"]
    merged["condition_group_replay_v1"] = merged["track_condition_effective_v1"].map(replay_condition_group)
    merged.loc[~merged["condition_group_replay_v1"].isin(CONDITION_BUCKETS), "condition_group_replay_v1"] = "UNKNOWN"
    merged["track_display_v1"] = merged["track_raw"]
    merged["race_key_replay_v1"] = merged["race_key_norm"]
    merged = merged[merged["barrier_bucket_replay_v1"].isin(BARRIER_BUCKETS)].copy()
    return merged


def build_grouped_table(base: pd.DataFrame) -> pd.DataFrame:
    statewide = (
        base.groupby("barrier_bucket_replay_v1", dropna=False)
        .agg(
            statewide_barrier_starts=("won", "size"),
            statewide_barrier_wins=("won", "sum"),
            statewide_barrier_places=("placed", "sum"),
        )
        .reset_index()
    )
    statewide["statewide_barrier_win_pct"] = (
        statewide["statewide_barrier_wins"] / statewide["statewide_barrier_starts"] * 100.0
    ).round(2)
    statewide["statewide_barrier_place_pct"] = (
        statewide["statewide_barrier_places"] / statewide["statewide_barrier_starts"] * 100.0
    ).round(2)

    grouped = (
        base.groupby(
            [
                "track_norm",
                "distance_band_v1",
                "rail_bucket",
                "condition_group_replay_v1",
                "barrier_bucket_replay_v1",
            ],
            dropna=False,
        )
        .agg(
            track=("track_display_v1", lambda s: s.mode().iat[0] if not s.mode().empty else s.iloc[0]),
            starts=("won", "size"),
            races=("race_key_replay_v1", "nunique"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_field_size_v1=("field_size_v1", "mean"),
            sample_rail_position_v1=("rail_position", lambda s: s.dropna().iloc[0] if not s.dropna().empty else ""),
        )
        .reset_index()
    )
    grouped = grouped.merge(statewide, on="barrier_bucket_replay_v1", how="left")
    grouped["win_pct"] = np.where(grouped["starts"] > 0, grouped["wins"] / grouped["starts"] * 100.0, np.nan).round(2)
    grouped["place_pct"] = np.where(grouped["starts"] > 0, grouped["places"] / grouped["starts"] * 100.0, np.nan).round(2)
    grouped["barrier_rail_condition_lift_pts"] = (
        grouped["win_pct"] - grouped["statewide_barrier_win_pct"]
    ).round(2)
    grouped["barrier_rail_condition_score_v1"] = grouped.apply(
        lambda row: win_place_score(
            row["win_pct"],
            row["place_pct"],
            row["statewide_barrier_win_pct"],
            row["statewide_barrier_place_pct"],
        ),
        axis=1,
    )
    grouped["barrier_rail_condition_band_v1"] = grouped.apply(
        lambda row: barrier_rail_condition_band(row["barrier_rail_condition_lift_pts"], row["starts"]),
        axis=1,
    )
    for threshold in [50, 80, 100, 300]:
        grouped[f"sample_ge_{threshold}_v1"] = grouped["starts"] >= threshold

    grouped = grouped.rename(
        columns={
            "distance_band_v1": "distance_bucket",
            "condition_group_replay_v1": "condition_group",
            "barrier_bucket_replay_v1": "barrier_bucket",
        }
    )
    return grouped.sort_values(
        ["barrier_rail_condition_score_v1", "starts"],
        ascending=[False, False],
    ).reset_index(drop=True)


def build_row_level(base: pd.DataFrame, grouped: pd.DataFrame) -> pd.DataFrame:
    merge_cols = [
        "track_norm",
        "distance_bucket",
        "rail_bucket",
        "condition_group",
        "barrier_bucket",
        "statewide_barrier_win_pct",
        "statewide_barrier_place_pct",
        "barrier_rail_condition_lift_pts",
        "barrier_rail_condition_score_v1",
        "barrier_rail_condition_band_v1",
        "starts",
        "wins",
        "places",
        "win_pct",
        "place_pct",
        "races",
    ]
    out = base.copy()
    out["distance_bucket"] = out["distance_band_v1"]
    out["condition_group"] = out["condition_group_replay_v1"]
    out["barrier_bucket"] = out["barrier_bucket_replay_v1"]
    out = out.merge(
        grouped[merge_cols].rename(
            columns={
                "starts": "bucket_starts_v1",
                "wins": "bucket_wins_v1",
                "places": "bucket_places_v1",
                "win_pct": "bucket_win_pct_v1",
                "place_pct": "bucket_place_pct_v1",
                "races": "bucket_races_v1",
            }
        ),
        on=["track_norm", "distance_bucket", "rail_bucket", "condition_group", "barrier_bucket"],
        how="left",
    )
    out["barrier_num"] = out["barrier_num"].round(0).astype("Int64")
    return out[
        [
            "meeting_date",
            "track_raw",
            "track_norm",
            "race_no",
            "race_key_replay_v1",
            "horse",
            "horse_key",
            "horse_key_norm",
            "barrier_num",
            "barrier_bucket",
            "distance_m",
            "distance_bucket",
            "rail_position",
            "rail_bucket",
            "track_condition_effective_v1",
            "condition_group",
            "weather_graphql",
            "penetrometer_graphql",
            "finish_position_num",
            "won",
            "placed",
            "statewide_barrier_win_pct",
            "statewide_barrier_place_pct",
            "barrier_rail_condition_lift_pts",
            "barrier_rail_condition_score_v1",
            "barrier_rail_condition_band_v1",
            "bucket_starts_v1",
            "bucket_wins_v1",
            "bucket_places_v1",
            "bucket_win_pct_v1",
            "bucket_place_pct_v1",
            "bucket_races_v1",
            "source_url",
        ]
    ].rename(columns={"track_raw": "track"})


def load_rank1_failure_base() -> pd.DataFrame:
    if IN_BIAS_RELEVANCE_DETAIL.exists():
        df = pd.read_csv(IN_BIAS_RELEVANCE_DETAIL, low_memory=False)
        out = pd.DataFrame()
        out["meeting_date"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        out["track"] = df.get("rank1_track", "").fillna("").astype(str)
        out["track_norm"] = df["track_norm"].fillna(df.get("rank1_track", "").map(normalize_track)).astype(str)
        out["race_no"] = safe_num(df["race_no_num"]).astype("Int64")
        out["race_key"] = df.get("race_key_norm", "").fillna("").astype(str)
        out["rank1_horse"] = df.get("rank1_horse", "").fillna("").astype(str)
        out["rank1_horse_key"] = df.get("rank1_horse_key_norm", "").fillna("").astype(str)
        out["rank1_horse_key_norm"] = df["rank1_horse_key_norm"].fillna(df.get("rank1_horse", "").map(normalize_horse_key)).astype(str)
        out["rank1_horse_join_norm"] = out["rank1_horse"].map(normalize_horse_key)
        out["winner_horse"] = df.get("winner_horse", "").fillna("").astype(str)
        out["winner_horse_key"] = df.get("winner_horse_key_norm", "").fillna("").astype(str)
        out["winner_horse_key_norm"] = df["winner_horse_key_norm"].fillna(df.get("winner_horse", "").map(normalize_horse_key)).astype(str)
        out["winner_horse_join_norm"] = out["winner_horse"].map(normalize_horse_key)
        if "rank1_won" in df.columns:
            out["rank1_won"] = df["rank1_won"].astype(str).str.upper().isin(["TRUE", "1"]).astype(int)
        else:
            out["rank1_won"] = safe_num(df.get("rank1_won_num", 0)).fillna(0).astype(int)
        out = out[out["meeting_date"].notna() & out["race_no"].notna()].copy()
        out = out.drop_duplicates(subset=["meeting_date", "track_norm", "race_no"], keep="first")
        return out

    df = pd.read_csv(IN_RANK1, low_memory=False)
    out = pd.DataFrame()
    out["meeting_date"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["track"] = df["track"].fillna("").astype(str)
    out["track_norm"] = df["track"].map(normalize_track)
    out["race_no"] = safe_num(df["race_no"]).astype("Int64")
    out["race_key"] = df["race_key"].fillna("").astype(str)
    out["rank1_horse"] = df["rank1_horse"].fillna("").astype(str)
    out["rank1_horse_key"] = df["rank1_horse_key"].fillna("").astype(str)
    out["rank1_horse_key_norm"] = df["rank1_horse_key"].fillna(df["rank1_horse"]).map(normalize_horse_key)
    out["rank1_horse_join_norm"] = out["rank1_horse"].map(normalize_horse_key)
    out["winner_horse"] = df["winner_horse"].fillna("").astype(str)
    out["winner_horse_key"] = df["winner_horse_key"].fillna("").astype(str)
    out["winner_horse_key_norm"] = df["winner_horse_key"].fillna(df["winner_horse"]).map(normalize_horse_key)
    out["winner_horse_join_norm"] = out["winner_horse"].map(normalize_horse_key)
    out["rank1_won"] = safe_num(df["rank1_won"]).fillna(0).astype(int)
    out = out[out["meeting_date"].notna() & out["race_no"].notna()].copy()
    out = out.drop_duplicates(subset=["meeting_date", "track_norm", "race_no"], keep="first")
    return out


def build_rank1_relevance(row_level: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rank1_base = load_rank1_failure_base()
    score_side = row_level[
        [
            "meeting_date",
            "track",
            "track_norm",
            "race_no",
            "horse",
            "horse_key",
            "horse_key_norm",
            "barrier_num",
            "barrier_bucket",
            "rail_bucket",
            "condition_group",
            "distance_bucket",
            "barrier_rail_condition_score_v1",
            "barrier_rail_condition_band_v1",
            "barrier_rail_condition_lift_pts",
        ]
    ].drop_duplicates(
        subset=["meeting_date", "track_norm", "race_no", "horse_key_norm"],
        keep="first",
    )
    score_side["horse_name_norm"] = score_side["horse"].map(normalize_horse_key)

    rank1_side = score_side.rename(
        columns={
            "horse": "rank1_horse_source",
            "horse_key": "rank1_horse_key_source",
            "horse_key_norm": "rank1_horse_key_source_norm",
            "horse_name_norm": "rank1_horse_join_norm",
            "barrier_num": "rank1_barrier_num",
            "barrier_bucket": "rank1_barrier_bucket",
            "rail_bucket": "rank1_rail_bucket",
            "condition_group": "rank1_condition_group",
            "distance_bucket": "rank1_distance_bucket",
            "barrier_rail_condition_score_v1": "rank1_barrier_rail_condition_score_v1",
            "barrier_rail_condition_band_v1": "rank1_barrier_rail_condition_band_v1",
            "barrier_rail_condition_lift_pts": "rank1_barrier_rail_condition_lift_pts",
        }
    )
    winner_side = score_side.rename(
        columns={
            "horse": "winner_horse_source",
            "horse_key": "winner_horse_key_source",
            "horse_key_norm": "winner_horse_key_source_norm",
            "horse_name_norm": "winner_horse_join_norm",
            "barrier_num": "winner_barrier_num",
            "barrier_bucket": "winner_barrier_bucket",
            "rail_bucket": "winner_rail_bucket",
            "condition_group": "winner_condition_group",
            "distance_bucket": "winner_distance_bucket",
            "barrier_rail_condition_score_v1": "winner_barrier_rail_condition_score_v1",
            "barrier_rail_condition_band_v1": "winner_barrier_rail_condition_band_v1",
            "barrier_rail_condition_lift_pts": "winner_barrier_rail_condition_lift_pts",
        }
    )

    detail = rank1_base.merge(
        rank1_side,
        on=["meeting_date", "track_norm", "race_no", "rank1_horse_join_norm"],
        how="left",
    ).merge(
        winner_side,
        on=["meeting_date", "track_norm", "race_no", "winner_horse_join_norm"],
        how="left",
    )
    detail["rank1_loss_flag_v1"] = detail["rank1_won"] != 1
    detail["winner_better_barrier_rail_condition_flag_v1"] = (
        safe_num(detail["winner_barrier_rail_condition_score_v1"])
        > safe_num(detail["rank1_barrier_rail_condition_score_v1"])
    )
    losses = detail[detail["rank1_loss_flag_v1"]].copy()

    barrier_only_reference = 54.01
    if IN_BIAS_RELEVANCE_SUMMARY.exists():
        try:
            reference_df = pd.read_csv(IN_BIAS_RELEVANCE_SUMMARY)
            match = reference_df.loc[
                reference_df["metric"].astype(str).eq("losses_winner_better_barrier_bias_pct"),
                "value",
            ]
            if not match.empty:
                barrier_only_reference = float(match.iloc[0])
        except Exception:
            pass

    losses_pct = pct(
        int(losses["winner_better_barrier_rail_condition_flag_v1"].fillna(False).sum()),
        len(losses),
    )
    verdict = (
        "BARRIER_RAIL_CONDITION_ADDS_VALUE"
        if not pd.isna(losses_pct) and losses_pct > barrier_only_reference
        else "NO_CLEAR_IMPROVEMENT_OVER_BARRIER_ONLY"
    )
    meta = {
        "races_audited": int(len(detail)),
        "rank1_losses": int(len(losses)),
        "losses_winner_better_barrier_rail_condition_pct": losses_pct,
        "barrier_only_reference_pct": barrier_only_reference,
        "verdict": verdict,
    }
    return detail, meta


def build_json_payload(summary_df: pd.DataFrame, grouped: pd.DataFrame, rank1_meta: dict) -> dict:
    positive = grouped[grouped["starts"] >= 50].sort_values(
        ["barrier_rail_condition_lift_pts", "starts"],
        ascending=[False, False],
    ).head(25)
    negative = grouped[grouped["starts"] >= 50].sort_values(
        ["barrier_rail_condition_lift_pts", "starts"],
        ascending=[True, False],
    ).head(25)
    return {
        "status": "COMPLETE",
        "summary_metrics": {row["metric"]: row["value"] for row in summary_df.to_dict("records")},
        "rank1_relevance": rank1_meta,
        "top_positive_buckets": positive.to_dict("records"),
        "top_negative_buckets": negative.to_dict("records"),
    }


def main() -> None:
    base = load_replay_base()
    grouped = build_grouped_table(base)
    row_level = build_row_level(base, grouped)
    rank1_detail, rank1_meta = build_rank1_relevance(row_level)

    positive = grouped[grouped["starts"] >= 50].sort_values(
        ["barrier_rail_condition_lift_pts", "starts"],
        ascending=[False, False],
    )
    negative = grouped[grouped["starts"] >= 50].sort_values(
        ["barrier_rail_condition_lift_pts", "starts"],
        ascending=[True, False],
    )

    summary_rows = [
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "rows", "value": int(len(row_level))},
        {"metric": "races", "value": int(row_level["race_key_replay_v1"].nunique())},
        {"metric": "grouped_buckets", "value": int(len(grouped))},
        {"metric": "rail_known_pct", "value": round(float((row_level["rail_bucket"] != "UNKNOWN").mean()) * 100.0, 2)},
        {"metric": "condition_known_pct", "value": round(float((row_level["condition_group"] != "UNKNOWN").mean()) * 100.0, 2)},
        {"metric": "strong_positive_bucket_count", "value": int((grouped["barrier_rail_condition_band_v1"] == "STRONG_POSITIVE").sum())},
        {"metric": "positive_bucket_count", "value": int((grouped["barrier_rail_condition_band_v1"] == "POSITIVE").sum())},
        {"metric": "negative_bucket_count", "value": int((grouped["barrier_rail_condition_band_v1"] == "NEGATIVE").sum())},
        {"metric": "strong_negative_bucket_count", "value": int((grouped["barrier_rail_condition_band_v1"] == "STRONG_NEGATIVE").sum())},
        {"metric": "top_positive_bucket", "value": positive.head(1).apply(lambda r: f"{r['track']} | {r['distance_bucket']} | {r['rail_bucket']} | {r['condition_group']} | {r['barrier_bucket']}", axis=1).iloc[0] if not positive.empty else ""},
        {"metric": "top_negative_bucket", "value": negative.head(1).apply(lambda r: f"{r['track']} | {r['distance_bucket']} | {r['rail_bucket']} | {r['condition_group']} | {r['barrier_bucket']}", axis=1).iloc[0] if not negative.empty else ""},
        {"metric": "races_audited", "value": rank1_meta["races_audited"]},
        {"metric": "rank1_losses", "value": rank1_meta["rank1_losses"]},
        {"metric": "losses_winner_better_barrier_rail_condition_pct", "value": rank1_meta["losses_winner_better_barrier_rail_condition_pct"]},
        {"metric": "barrier_only_reference_pct", "value": rank1_meta["barrier_only_reference_pct"]},
        {"metric": "verdict", "value": rank1_meta["verdict"]},
    ]
    summary_df = pd.DataFrame(summary_rows)

    write_csv(row_level, OUT_MAIN.name)
    write_csv(grouped, OUT_BY_BUCKET.name)
    write_csv(summary_df, OUT_SUMMARY.name)
    write_csv(rank1_detail, OUT_RANK1.name)
    write_json(build_json_payload(summary_df, grouped, rank1_meta), OUT_JSON.name)

    print("[BARRIER_RAIL_CONDITION_BIAS_REPLAY_V1] COMPLETE")
    print(f"rows={len(row_level)}")
    print(f"races={row_level['race_key_replay_v1'].nunique()}")
    print(f"grouped_buckets={len(grouped)}")
    print(f"races_audited={rank1_meta['races_audited']}")
    print(f"rank1_losses={rank1_meta['rank1_losses']}")
    print(f"losses_winner_better_barrier_rail_condition_pct={rank1_meta['losses_winner_better_barrier_rail_condition_pct']}")
    print(f"barrier_only_reference_pct={rank1_meta['barrier_only_reference_pct']}")
    print(f"verdict={rank1_meta['verdict']}")
    print(f"wrote={OUT_MAIN}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_BUCKET}")
    print(f"wrote={OUT_RANK1}")
    print(f"wrote={OUT_JSON}")


if __name__ == "__main__":
    main()

