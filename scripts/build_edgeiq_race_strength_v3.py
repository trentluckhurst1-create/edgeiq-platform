import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RESULTS = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"
TAB = DATA / "edgeiq_tab_vic_racecards_v1.csv"

HORSE_PROFILE_OUT = DATA / "edgeiq_horse_results_strength_profile_v3.csv"
LIVE_RACE_STRENGTH_OUT = DATA / "edgeiq_live_race_strength_v3.csv"
AUDIT = DATA / "edgeiq_race_strength_v3_audit.csv"

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def pos_num(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    if s in ["", "NAN", "NONE", "SCR", "SCRATCHED"]:
        return np.nan
    m = re.search(r"\d+", s)
    return float(m.group(0)) if m else np.nan

def field_size_from_group(g):
    return int(g["finish_num"].notna().sum())

def strength_band(score):
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 72:
        return "ELITE"
    if score >= 64:
        return "STRONG"
    if score >= 56:
        return "SOLID"
    if score >= 48:
        return "WEAK"
    return "VERY_WEAK"

def main():
    if not RESULTS.exists():
        raise FileNotFoundError(f"Missing {RESULTS}")
    if not TAB.exists():
        raise FileNotFoundError(f"Missing {TAB}")

    res = pd.read_csv(RESULTS)
    tab = pd.read_csv(TAB)

    horse_col = "horseName" if "horseName" in res.columns else "horse"
    finish_col = "finishPosition" if "finishPosition" in res.columns else "finish_position"

    res["horse_key"] = res[horse_col].map(canon)
    res["finish_num"] = res[finish_col].apply(pos_num)
    res["meeting_date"] = res["meeting_date"].astype(str).str.slice(0, 10)
    res["race_key"] = res["meeting_date"].astype(str) + "|" + res["track"].astype(str) + "|" + res["race_no"].astype(str)

    finished = res[res["finish_num"].notna()].copy()

    field_sizes = finished.groupby("race_key").apply(field_size_from_group).rename("field_size").reset_index()
    finished = finished.merge(field_sizes, on="race_key", how="left")

    finished["finish_pct"] = np.where(
        finished["field_size"] > 1,
        1.0 - ((finished["finish_num"] - 1.0) / (finished["field_size"] - 1.0)),
        0.5
    )

    finished["win"] = finished["finish_num"].eq(1).astype(int)
    finished["place"] = finished["finish_num"].le(3).astype(int)
    finished["top4"] = finished["finish_num"].le(4).astype(int)

    finished = finished.sort_values(["horse_key", "meeting_date"])

    recent = (
        finished.groupby("horse_key")
        .tail(5)
        .groupby("horse_key")
        .agg(
            recent_starts=("horse_key", "count"),
            recent_avg_finish_pct=("finish_pct", "mean"),
            recent_wins=("win", "sum"),
            recent_places=("place", "sum"),
        )
        .reset_index()
    )

    career = finished.groupby("horse_key").agg(
        horse=("horseName", "last") if "horseName" in finished.columns else (horse_col, "last"),
        starts=("horse_key", "count"),
        wins=("win", "sum"),
        places=("place", "sum"),
        top4s=("top4", "sum"),
        avg_finish_pct=("finish_pct", "mean"),
        best_finish_pct=("finish_pct", "max"),
        avg_field_size=("field_size", "mean"),
        last_start_date=("meeting_date", "max"),
    ).reset_index()

    profile = career.merge(recent, on="horse_key", how="left")

    profile["win_rate"] = profile["wins"] / profile["starts"]
    profile["place_rate"] = profile["places"] / profile["starts"]
    profile["top4_rate"] = profile["top4s"] / profile["starts"]

    # Results-proven horse strength score, not a price.
    profile["horse_results_strength_v3"] = (
        100.0 * (
            0.34 * profile["avg_finish_pct"].fillna(0) +
            0.26 * profile["recent_avg_finish_pct"].fillna(profile["avg_finish_pct"]).fillna(0) +
            0.16 * profile["place_rate"].fillna(0) +
            0.12 * profile["win_rate"].fillna(0) +
            0.08 * profile["top4_rate"].fillna(0) +
            0.04 * profile["best_finish_pct"].fillna(0)
        )
    )

    # Small reliability adjustment: many starts are more believable.
    profile["results_reliability_v3"] = np.select(
        [
            profile["starts"] >= 10,
            profile["starts"] >= 5,
            profile["starts"] >= 3,
            profile["starts"] >= 1,
        ],
        [
            "PROVEN_10_PLUS",
            "PROVEN_5_9",
            "LIMITED_3_4",
            "LIMITED_1_2",
        ],
        default="UNKNOWN"
    )

    profile["results_reliability_multiplier_v3"] = np.select(
        [
            profile["starts"] >= 10,
            profile["starts"] >= 5,
            profile["starts"] >= 3,
            profile["starts"] >= 1,
        ],
        [1.00, 0.96, 0.90, 0.82],
        default=0.75
    )

    profile["horse_results_strength_v3"] = (
        profile["horse_results_strength_v3"] * profile["results_reliability_multiplier_v3"]
    ).clip(0, 100).round(3)

    for c in [
        "avg_finish_pct", "recent_avg_finish_pct", "best_finish_pct",
        "win_rate", "place_rate", "top4_rate", "avg_field_size"
    ]:
        profile[c] = profile[c].round(4)

    profile.to_csv(HORSE_PROFILE_OUT, index=False)

    tab["horse_key"] = tab["horse"].map(canon)
    tab["meeting_date"] = tab["meeting_date"].astype(str).str.slice(0, 10)
    tab["race_key"] = tab["meeting_date"].astype(str) + "|" + tab["meeting_name"].astype(str) + "|" + tab["race_no"].astype(str)

    live = tab.merge(
        profile[[
            "horse_key",
            "starts",
            "wins",
            "places",
            "horse_results_strength_v3",
            "results_reliability_v3",
            "last_start_date",
        ]],
        on="horse_key",
        how="left"
    )

    live["horse_results_strength_v3"] = pd.to_numeric(live["horse_results_strength_v3"], errors="coerce")
    live["is_profiled_v3"] = live["horse_results_strength_v3"].notna().astype(int)

    rows = []

    for race_key, g in live.groupby("race_key"):
        vals = g["horse_results_strength_v3"].dropna().sort_values(ascending=False)
        total = len(g)
        profiled = int(g["is_profiled_v3"].sum())
        coverage = profiled / total if total else 0

        if len(vals):
            top1 = vals.iloc[0]
            top3 = vals.head(3).mean()
            top5 = vals.head(5).mean()
            avg = vals.mean()
        else:
            top1 = top3 = top5 = avg = np.nan

        score = (
            0.34 * (top3 if pd.notna(top3) else 35) +
            0.26 * (top5 if pd.notna(top5) else 35) +
            0.20 * (avg if pd.notna(avg) else 35) +
            0.12 * (top1 if pd.notna(top1) else 35) +
            0.08 * (coverage * 100)
        )

        first = g.iloc[0]

        rows.append({
            "meeting_date": first["meeting_date"],
            "track": first["meeting_name"],
            "race_no": first["race_no"],
            "race_key": race_key,
            "field_size_v3": total,
            "profiled_runners_v3": profiled,
            "profile_coverage_v3": round(coverage, 4),
            "top1_horse_results_strength_v3": round(top1, 3) if pd.notna(top1) else "",
            "top3_avg_horse_results_strength_v3": round(top3, 3) if pd.notna(top3) else "",
            "top5_avg_horse_results_strength_v3": round(top5, 3) if pd.notna(top5) else "",
            "field_avg_horse_results_strength_v3": round(avg, 3) if pd.notna(avg) else "",
            "live_race_strength_score_v3": round(score, 3),
            "live_race_strength_band_v3": strength_band(score),
        })

    race_strength = pd.DataFrame(rows).sort_values(["meeting_date", "track", "race_no"])
    race_strength.to_csv(LIVE_RACE_STRENGTH_OUT, index=False)

    audit = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "result_rows", "value": len(res)},
        {"metric": "finished_rows", "value": len(finished)},
        {"metric": "horse_profiles", "value": len(profile)},
        {"metric": "live_runner_rows", "value": len(live)},
        {"metric": "live_races", "value": len(race_strength)},
        {"metric": "avg_profile_coverage", "value": round(race_strength["profile_coverage_v3"].mean(), 4) if len(race_strength) else 0},
        {"metric": "elite_races", "value": int((race_strength["live_race_strength_band_v3"] == "ELITE").sum())},
        {"metric": "strong_races", "value": int((race_strength["live_race_strength_band_v3"] == "STRONG").sum())},
        {"metric": "solid_races", "value": int((race_strength["live_race_strength_band_v3"] == "SOLID").sum())},
        {"metric": "weak_races", "value": int((race_strength["live_race_strength_band_v3"] == "WEAK").sum())},
        {"metric": "very_weak_races", "value": int((race_strength["live_race_strength_band_v3"] == "VERY_WEAK").sum())},
    ])
    audit.to_csv(AUDIT, index=False)

    print("[RACE_STRENGTH_V3] COMPLETE")
    print(f"horse_profiles={len(profile)}")
    print(f"live_races={len(race_strength)}")
    print(f"avg_profile_coverage={round(race_strength['profile_coverage_v3'].mean(), 4) if len(race_strength) else 0}")
    print(f"wrote_profiles={HORSE_PROFILE_OUT}")
    print(f"wrote_live_race_strength={LIVE_RACE_STRENGTH_OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
