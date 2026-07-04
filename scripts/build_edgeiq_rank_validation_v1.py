import re
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RANKED = DATA / "edgeiq_execution_confidence_v1.csv"
TAB = DATA / "edgeiq_tab_vic_racecards_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUT = DATA / "edgeiq_rank_validation_v1_runner_rows.csv"
SUMMARY = DATA / "edgeiq_rank_validation_v1_summary.csv"
BY_RANK = DATA / "edgeiq_rank_validation_v1_by_rank.csv"
BY_TOP_BUCKET = DATA / "edgeiq_rank_validation_v1_by_top_bucket.csv"
BY_CONF = DATA / "edgeiq_rank_validation_v1_by_confidence.csv"
BY_GOV = DATA / "edgeiq_rank_validation_v1_by_governance.csv"

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def norm_track(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = s.replace("BET365 ", "")
    s = s.replace("LADBROKES ", "")
    s = s.replace("SPORTSBET ", "")
    s = s.replace("SPORTSBET-", "")
    s = s.replace("APIAM ", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def pos_num(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    if s in ["", "NAN", "NONE", "SCR", "SCRATCHED"]:
        return np.nan
    m = re.search(r"\d+", s)
    return float(m.group(0)) if m else np.nan

def rank_bucket(rank):
    if pd.isna(rank):
        return "NO_RANK"
    r = int(rank)
    if r <= 5:
        return f"RANK_{r}"
    if r <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"

def top_bucket(rank):
    if pd.isna(rank):
        return "NO_RANK"
    r = int(rank)
    if r == 1:
        return "TOP_1"
    if r <= 2:
        return "TOP_2"
    if r <= 3:
        return "TOP_3"
    if r <= 5:
        return "TOP_5"
    if r <= 10:
        return "TOP_10"
    return "OUTSIDE_TOP_10"

def metrics(df, col):
    if len(df) == 0 or col not in df.columns:
        return pd.DataFrame(columns=[
            col, "runners", "races", "wins", "places", "top4",
            "avg_finish", "median_finish", "avg_score", "avg_strength",
            "win_rate", "place_rate", "top4_rate"
        ])

    g = df.groupby(col, dropna=False).agg(
        runners=("horse", "count"),
        races=("race_key", "nunique"),
        wins=("won", "sum"),
        places=("placed", "sum"),
        top4=("top4", "sum"),
        avg_finish=("finish_position", "mean"),
        median_finish=("finish_position", "median"),
        avg_score=("runner_score_v3_1", "mean"),
        avg_strength=("strength_adjusted_rating_v4", "mean"),
    ).reset_index()

    g["win_rate"] = (g["wins"] / g["runners"]).round(4)
    g["place_rate"] = (g["places"] / g["runners"]).round(4)
    g["top4_rate"] = (g["top4"] / g["runners"]).round(4)
    g["avg_finish"] = g["avg_finish"].round(2)
    g["median_finish"] = g["median_finish"].round(2)
    g["avg_score"] = g["avg_score"].round(2)
    g["avg_strength"] = g["avg_strength"].round(2)

    return g

def main():
    for f in [RANKED, TAB, RESULTS]:
        if not f.exists():
            raise FileNotFoundError(f"Missing required file: {f}")

    ranked = pd.read_csv(RANKED).copy()
    tab = pd.read_csv(TAB).copy()
    res = pd.read_csv(RESULTS).copy()

    # Remove old merge indicator columns if they exist from previous pipeline joins.
    for df in [ranked, tab, res]:
        for c in ["_merge", "merge_status", "rank_validation_merge"]:
            if c in df.columns:
                df.drop(columns=[c], inplace=True)

    ranked["runner_rank_v7_2"] = pd.to_numeric(ranked.get("runner_rank_v7_2"), errors="coerce")
    ranked["runner_score_v3_1"] = pd.to_numeric(ranked.get("runner_score_v3_1"), errors="coerce")
    ranked["strength_adjusted_rating_v4"] = pd.to_numeric(ranked.get("strength_adjusted_rating_v4"), errors="coerce")

    ranked["join_track"] = ranked["track"].map(norm_track)
    ranked["join_race_no"] = pd.to_numeric(ranked["race_no"], errors="coerce").astype("Int64")
    ranked["join_horse"] = ranked["horse"].map(canon)

    tab["join_track"] = tab["meeting_name"].map(norm_track)
    tab["join_race_no"] = pd.to_numeric(tab["race_no"], errors="coerce").astype("Int64")
    tab["join_horse"] = tab["horse"].map(canon)

    date_map = tab[["meeting_date", "join_track", "join_race_no", "join_horse"]].drop_duplicates(
        ["join_track", "join_race_no", "join_horse"],
        keep="last"
    )

    ranked = ranked.merge(
        date_map,
        on=["join_track", "join_race_no", "join_horse"],
        how="left",
        suffixes=("", "_tab")
    )

    ranked["event_date"] = ranked["meeting_date"].astype(str).str.slice(0, 10)

    date_col = "meeting_date" if "meeting_date" in res.columns else "race_date"
    horse_col = "horseName" if "horseName" in res.columns else "horse"
    finish_col = "finishPosition" if "finishPosition" in res.columns else "finish_position"

    res["join_date"] = res[date_col].astype(str).str.slice(0, 10)
    res["join_track"] = res["track"].map(norm_track)
    res["join_race_no"] = pd.to_numeric(res["race_no"], errors="coerce").astype("Int64")
    res["join_horse"] = res[horse_col].map(canon)
    res["finish_position"] = res[finish_col].apply(pos_num)

    res_keep = res[[
        "join_date",
        "join_track",
        "join_race_no",
        "join_horse",
        "finish_position",
    ]].drop_duplicates(
        ["join_date", "join_track", "join_race_no", "join_horse"],
        keep="last"
    )

    out = ranked.merge(
        res_keep,
        left_on=["event_date", "join_track", "join_race_no", "join_horse"],
        right_on=["join_date", "join_track", "join_race_no", "join_horse"],
        how="left",
        indicator="rank_validation_merge"
    )

    out["result_match_status_v1"] = np.where(
        out["rank_validation_merge"].eq("both") & out["finish_position"].notna(),
        "MATCHED",
        "PENDING"
    )

    out["race_key"] = (
        out["event_date"].astype(str) + "|" +
        out["track"].astype(str) + "|" +
        out["race_no"].astype(str)
    )

    out["won"] = np.where(out["finish_position"].eq(1), 1, 0)
    out["placed"] = np.where(out["finish_position"].le(3), 1, 0)
    out["top4"] = np.where(out["finish_position"].le(4), 1, 0)

    out.loc[out["result_match_status_v1"].ne("MATCHED"), ["won", "placed", "top4"]] = 0

    out["rank_bucket_v1"] = out["runner_rank_v7_2"].apply(rank_bucket)
    out["top_bucket_v1"] = out["runner_rank_v7_2"].apply(top_bucket)

    out.to_csv(OUT, index=False)

    matched = out[out["result_match_status_v1"].eq("MATCHED")].copy()

    by_rank = metrics(matched, "rank_bucket_v1")
    if len(by_rank):
        order = {
            "RANK_1": 1,
            "RANK_2": 2,
            "RANK_3": 3,
            "RANK_4": 4,
            "RANK_5": 5,
            "RANK_6_10": 6,
            "RANK_11_PLUS": 11,
            "NO_RANK": 99,
        }
        by_rank["_order"] = by_rank["rank_bucket_v1"].map(order).fillna(99)
        by_rank = by_rank.sort_values("_order").drop(columns=["_order"])
    by_rank.to_csv(BY_RANK, index=False)

    by_top = metrics(matched, "top_bucket_v1")
    if len(by_top):
        order = {
            "TOP_1": 1,
            "TOP_2": 2,
            "TOP_3": 3,
            "TOP_5": 5,
            "TOP_10": 10,
            "OUTSIDE_TOP_10": 11,
            "NO_RANK": 99,
        }
        by_top["_order"] = by_top["top_bucket_v1"].map(order).fillna(99)
        by_top = by_top.sort_values("_order").drop(columns=["_order"])
    by_top.to_csv(BY_TOP_BUCKET, index=False)

    metrics(matched, "execution_confidence_band_v1").to_csv(BY_CONF, index=False)
    metrics(matched, "governance_band_v7_2").to_csv(BY_GOV, index=False)

    races_total = out["race_key"].nunique()
    races_matched = matched["race_key"].nunique()
    rank1 = matched[matched["runner_rank_v7_2"].eq(1)]
    top3 = matched[matched["runner_rank_v7_2"].le(3)]

    summary = pd.DataFrame([
        {"metric": "ranked_rows", "value": len(out)},
        {"metric": "matched_rows", "value": len(matched)},
        {"metric": "pending_rows", "value": int((out["result_match_status_v1"] == "PENDING").sum())},
        {"metric": "races_total", "value": races_total},
        {"metric": "races_matched", "value": races_matched},
        {"metric": "rank1_runners", "value": len(rank1)},
        {"metric": "rank1_wins", "value": int(rank1["won"].sum()) if len(rank1) else 0},
        {"metric": "rank1_places", "value": int(rank1["placed"].sum()) if len(rank1) else 0},
        {"metric": "rank1_win_rate", "value": round(rank1["won"].mean(), 4) if len(rank1) else 0},
        {"metric": "rank1_place_rate", "value": round(rank1["placed"].mean(), 4) if len(rank1) else 0},
        {"metric": "top3_runners", "value": len(top3)},
        {"metric": "top3_wins", "value": int(top3["won"].sum()) if len(top3) else 0},
        {"metric": "top3_places", "value": int(top3["placed"].sum()) if len(top3) else 0},
        {"metric": "top3_win_rate", "value": round(top3["won"].mean(), 4) if len(top3) else 0},
        {"metric": "top3_place_rate", "value": round(top3["placed"].mean(), 4) if len(top3) else 0},
    ])

    summary.to_csv(SUMMARY, index=False)

    print("[RANK_VALIDATION_V1] COMPLETE")
    print(f"ranked_rows={len(out)}")
    print(f"matched_rows={len(matched)}")
    print(f"pending_rows={(out['result_match_status_v1'] == 'PENDING').sum()}")
    print(f"races_matched={races_matched}")
    print(f"rank1_win_rate={summary.loc[summary['metric'].eq('rank1_win_rate'), 'value'].iloc[0]}")
    print(f"rank1_place_rate={summary.loc[summary['metric'].eq('rank1_place_rate'), 'value'].iloc[0]}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
