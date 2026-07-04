import re
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V6 = DATA / "edgeiq_strength_adjusted_ratings_v6.csv"
TAB = DATA / "edgeiq_tab_vic_racecards_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUT = DATA / "edgeiq_winner_rank_audit_v2.csv"
SUMMARY = DATA / "edgeiq_winner_rank_audit_v2_summary.csv"
BUCKETS = DATA / "edgeiq_winner_rank_audit_v2_rank_buckets.csv"

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def norm_track(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    for p in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM "]:
        s = s.replace(p, "")
    return re.sub(r"\s+", " ", s).strip()

def pos_num(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    if s in ["", "NAN", "NONE", "SCR", "SCRATCHED"]:
        return np.nan
    m = re.search(r"\d+", s)
    return float(m.group(0)) if m else np.nan

def rank_bucket(r):
    if pd.isna(r): return "NO_RANK"
    r = int(r)
    if r == 1: return "RANK_1"
    if r == 2: return "RANK_2"
    if r == 3: return "RANK_3"
    if r <= 5: return "RANK_4_5"
    if r <= 10: return "RANK_6_10"
    return "RANK_11_PLUS"

def main():
    v6 = pd.read_csv(V6)
    tab = pd.read_csv(TAB)
    res = pd.read_csv(RESULTS)

    v6["join_track"] = v6["track"].map(norm_track)
    v6["join_race_no"] = pd.to_numeric(v6["race_no"], errors="coerce").astype("Int64")
    v6["join_horse"] = v6["horse"].map(canon)
    v6["strength_adjusted_rating_v6"] = pd.to_numeric(v6["strength_adjusted_rating_v6"], errors="coerce")

    tab["join_track"] = tab["meeting_name"].map(norm_track)
    tab["join_race_no"] = pd.to_numeric(tab["race_no"], errors="coerce").astype("Int64")
    tab["join_horse"] = tab["horse"].map(canon)

    date_map = tab[["meeting_date","join_track","join_race_no","join_horse"]].drop_duplicates(
        ["join_track","join_race_no","join_horse"], keep="last"
    )

    ranked = v6.merge(date_map, on=["join_track","join_race_no","join_horse"], how="left")
    ranked["event_date"] = ranked["meeting_date"].astype(str).str.slice(0,10)
    ranked["race_key_v2"] = ranked["event_date"].astype(str) + "|" + ranked["join_track"].astype(str) + "|" + ranked["join_race_no"].astype(str)

    ranked = ranked.sort_values(["race_key_v2","strength_adjusted_rating_v6"], ascending=[True, False])
    ranked["v6_rank"] = ranked.groupby("race_key_v2").cumcount() + 1

    horse_col = "horseName" if "horseName" in res.columns else "horse"
    finish_col = "finishPosition" if "finishPosition" in res.columns else "finish_position"

    res["join_date"] = res["meeting_date"].astype(str).str.slice(0,10)
    res["join_track"] = res["track"].map(norm_track)
    res["join_race_no"] = pd.to_numeric(res["race_no"], errors="coerce").astype("Int64")
    res["join_horse"] = res[horse_col].map(canon)
    res["finish_position"] = res[finish_col].apply(pos_num)

    res_keep = res[["join_date","join_track","join_race_no","join_horse","finish_position"]].drop_duplicates(
        ["join_date","join_track","join_race_no","join_horse"], keep="last"
    )

    joined = ranked.merge(
        res_keep,
        left_on=["event_date","join_track","join_race_no","join_horse"],
        right_on=["join_date","join_track","join_race_no","join_horse"],
        how="left"
    )

    matched = joined[joined["finish_position"].notna()].copy()
    winners = matched[matched["finish_position"].eq(1)].copy()
    tops = matched.sort_values(["race_key_v2","v6_rank"]).groupby("race_key_v2").head(1).copy()

    w = winners.rename(columns={
        "horse":"winner",
        "v6_rank":"winner_v6_rank",
        "strength_adjusted_rating_v6":"winner_v6_rating",
        "governance_band_v7_2":"winner_governance",
    })

    t = tops[["race_key_v2","horse","v6_rank","strength_adjusted_rating_v6","finish_position"]].rename(columns={
        "horse":"top_v6_runner",
        "v6_rank":"top_v6_rank",
        "strength_adjusted_rating_v6":"top_v6_rating",
        "finish_position":"top_v6_finish",
    })

    out = w.merge(t, on="race_key_v2", how="left")
    out["winner_top1"] = out["winner_v6_rank"].eq(1).astype(int)
    out["winner_top3"] = out["winner_v6_rank"].le(3).astype(int)
    out["winner_top5"] = out["winner_v6_rank"].le(5).astype(int)
    out["winner_top10"] = out["winner_v6_rank"].le(10).astype(int)
    out["score_gap_top_minus_winner"] = (out["top_v6_rating"] - out["winner_v6_rating"]).round(3)
    out["winner_rank_bucket"] = out["winner_v6_rank"].apply(rank_bucket)

    keep = [
        "event_date","track","race_no","winner","winner_v6_rank","winner_v6_rating","winner_governance",
        "top_v6_runner","top_v6_finish","top_v6_rating","score_gap_top_minus_winner",
        "winner_top1","winner_top3","winner_top5","winner_top10"
    ]
    out[[c for c in keep if c in out.columns]].sort_values(["event_date","track","race_no"]).to_csv(OUT, index=False)

    buckets = out.groupby("winner_rank_bucket").agg(
        races=("race_key_v2","count"),
        avg_winner_rank=("winner_v6_rank","mean"),
        avg_winner_rating=("winner_v6_rating","mean"),
        avg_top_rating=("top_v6_rating","mean"),
        avg_score_gap=("score_gap_top_minus_winner","mean"),
    ).reset_index()
    for c in ["avg_winner_rank","avg_winner_rating","avg_top_rating","avg_score_gap"]:
        buckets[c] = buckets[c].round(3)
    buckets.to_csv(BUCKETS, index=False)

    total = len(out)
    summary = pd.DataFrame([
        {"metric":"races_audited","value":total},
        {"metric":"winner_rank1_count","value":int(out["winner_top1"].sum())},
        {"metric":"winner_top3_count","value":int(out["winner_top3"].sum())},
        {"metric":"winner_top5_count","value":int(out["winner_top5"].sum())},
        {"metric":"winner_top10_count","value":int(out["winner_top10"].sum())},
        {"metric":"winner_rank1_rate","value":round(out["winner_top1"].mean(),4) if total else 0},
        {"metric":"winner_top3_rate","value":round(out["winner_top3"].mean(),4) if total else 0},
        {"metric":"winner_top5_rate","value":round(out["winner_top5"].mean(),4) if total else 0},
        {"metric":"winner_top10_rate","value":round(out["winner_top10"].mean(),4) if total else 0},
        {"metric":"avg_winner_rank","value":round(out["winner_v6_rank"].mean(),3) if total else 0},
        {"metric":"avg_score_gap_top_minus_winner","value":round(out["score_gap_top_minus_winner"].mean(),3) if total else 0},
        {"metric":"old_v1_rank1_rate","value":0.0},
        {"metric":"old_v1_top3_rate","value":0.1176},
        {"metric":"old_v1_top5_rate","value":0.1765},
        {"metric":"old_v1_top10_rate","value":0.7059},
    ])
    summary.to_csv(SUMMARY, index=False)

    print("[WINNER_RANK_AUDIT_V2] COMPLETE")
    print(f"races_audited={total}")
    print(f"rank1={summary.loc[summary.metric.eq('winner_rank1_rate'),'value'].iloc[0]}")
    print(f"top3={summary.loc[summary.metric.eq('winner_top3_rate'),'value'].iloc[0]}")
    print(f"top5={summary.loc[summary.metric.eq('winner_top5_rate'),'value'].iloc[0]}")
    print(f"top10={summary.loc[summary.metric.eq('winner_top10_rate'),'value'].iloc[0]}")
    print(f"wrote={OUT}")

if __name__ == "__main__":
    main()
