from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"
BY_RACE = DATA / "edgeiq_runner_dna_weight_ladder_v1_by_race.csv"

SUMMARY = DATA / "edgeiq_runner_dna_v6_3_sp_roi_audit_v1_summary.csv"
FLIPS = DATA / "edgeiq_runner_dna_v6_3_sp_roi_audit_v1_flip_races.csv"
BUCKETS = DATA / "edgeiq_runner_dna_v6_3_sp_roi_audit_v1_sp_buckets.csv"

VERSION = "MEDIUM"

def num(x):
    try:
        s = str(x).replace("$", "").replace("%", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def sp_bucket(sp):
    if pd.isna(sp):
        return "NO_SP"
    if sp < 3:
        return "LT_3"
    if sp < 5:
        return "3_TO_5"
    if sp < 10:
        return "5_TO_10"
    if sp < 20:
        return "10_TO_20"
    return "20_PLUS"

hist = pd.read_csv(SRC, dtype=str).fillna("")
races = pd.read_csv(BY_RACE, dtype=str).fillna("")

built_at = datetime.now(timezone.utc).isoformat()

hist["sp_num"] = hist["sp_num_settled"].apply(num)
hist["profit_1u_num"] = hist["profit_1u"].apply(num)
hist["won_num"] = hist["won"].apply(num).fillna(0)
hist["finish_num"] = hist["finish_position"].apply(num)
hist["placed_num"] = np.where(hist["finish_num"].between(1,3), 1, 0)

sp_lookup = hist.set_index(["race_key", "horse"])[["sp_num","profit_1u_num","won_num","placed_num","finish_num"]].to_dict("index")

race_base = races[races["version"] == "BASE"].copy()
race_med = races[races["version"] == VERSION].copy()

rows = []

for label, source in [("BASE", race_base), ("MEDIUM", race_med)]:
    for _, r in source.iterrows():
        race_key = r["race_key"]
        horse = r["version_top"]

        info = sp_lookup.get((race_key, horse), {})

        sp = num(info.get("sp_num", ""))
        won = num(info.get("won_num", 0))
        placed = num(info.get("placed_num", 0))
        profit = num(info.get("profit_1u_num", ""))

        if pd.isna(profit):
            profit = (sp - 1.0) if won == 1 and not pd.isna(sp) else -1.0

        rows.append({
            "version": label,
            "race_key": race_key,
            "meeting_date": r.get("meeting_date", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "horse": horse,
            "sp": sp,
            "sp_bucket": sp_bucket(sp),
            "won": int(won) if not pd.isna(won) else 0,
            "placed": int(placed) if not pd.isna(placed) else 0,
            "profit_1u": profit,
            "built_at": built_at,
        })

detail = pd.DataFrame(rows)

summary_rows = []

for version, g in detail.groupby("version"):
    bets = len(g)
    wins = int(g["won"].sum())
    places = int(g["placed"].sum())
    profit = pd.to_numeric(g["profit_1u"], errors="coerce").sum()

    winners = g[g["won"] == 1]
    avg_winner_sp = pd.to_numeric(winners["sp"], errors="coerce").mean()

    summary_rows.append({
        "version": version,
        "races": bets,
        "wins": wins,
        "places": places,
        "win_pct": round(wins / bets * 100, 3) if bets else "",
        "place_pct": round(places / bets * 100, 3) if bets else "",
        "avg_winner_sp": round(avg_winner_sp, 3) if not pd.isna(avg_winner_sp) else "",
        "flat_bet_profit_1u": round(profit, 3),
        "roi_pct": round(profit / bets * 100, 3) if bets else "",
        "research_only": "YES",
        "built_at": built_at,
    })

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

flip_src = races[(races["version"] == VERSION) & (races["top_changed_vs_base"] == "True")].copy()

flip_rows = []

for _, r in flip_src.iterrows():
    race_key = r["race_key"]
    base_horse = r["base_top"]
    med_horse = r["version_top"]

    b = sp_lookup.get((race_key, base_horse), {})
    m = sp_lookup.get((race_key, med_horse), {})

    flip_rows.append({
        "race_key": race_key,
        "meeting_date": r.get("meeting_date", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "base_top": base_horse,
        "base_sp": b.get("sp_num", ""),
        "base_won": b.get("won_num", ""),
        "base_placed": b.get("placed_num", ""),
        "base_profit_1u": b.get("profit_1u_num", ""),
        "medium_top": med_horse,
        "medium_sp": m.get("sp_num", ""),
        "medium_won": m.get("won_num", ""),
        "medium_placed": m.get("placed_num", ""),
        "medium_profit_1u": m.get("profit_1u_num", ""),
        "profit_swing": (
            num(m.get("profit_1u_num", "")) - num(b.get("profit_1u_num", ""))
            if not pd.isna(num(m.get("profit_1u_num", ""))) and not pd.isna(num(b.get("profit_1u_num", "")))
            else ""
        ),
        "built_at": built_at,
    })

flips = pd.DataFrame(flip_rows)
flips.to_csv(FLIPS, index=False)

bucket_rows = []

for (version, bucket), g in detail.groupby(["version", "sp_bucket"]):
    bets = len(g)
    wins = int(g["won"].sum())
    places = int(g["placed"].sum())
    profit = pd.to_numeric(g["profit_1u"], errors="coerce").sum()

    bucket_rows.append({
        "version": version,
        "sp_bucket": bucket,
        "bets": bets,
        "wins": wins,
        "places": places,
        "win_pct": round(wins / bets * 100, 3) if bets else "",
        "place_pct": round(places / bets * 100, 3) if bets else "",
        "flat_bet_profit_1u": round(profit, 3),
        "roi_pct": round(profit / bets * 100, 3) if bets else "",
        "built_at": built_at,
    })

buckets = pd.DataFrame(bucket_rows)
buckets.to_csv(BUCKETS, index=False)

print("[RUNNER_DNA_V6_3_SP_ROI_AUDIT_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={SUMMARY}")
print(f"wrote={FLIPS}")
print(f"wrote={BUCKETS}")
