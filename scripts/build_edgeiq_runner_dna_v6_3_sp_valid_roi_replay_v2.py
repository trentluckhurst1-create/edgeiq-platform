from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST = DATA / "edgeiq_historical_replay_settled_v1.csv"
BY_RACE = DATA / "edgeiq_runner_dna_weight_ladder_v1_by_race.csv"

OUT = DATA / "edgeiq_runner_dna_v6_3_sp_valid_roi_replay_v2.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_3_sp_valid_roi_replay_v2_summary.csv"
BUCKETS = DATA / "edgeiq_runner_dna_v6_3_sp_valid_roi_replay_v2_price_buckets.csv"

built_at = datetime.now(timezone.utc).isoformat()

hist = pd.read_csv(HIST, dtype=str).fillna("")
races = pd.read_csv(BY_RACE, dtype=str).fillna("")

def num(x):
    try:
        s = str(x).replace("$","").replace("%","").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def is_true(x):
    return str(x).strip().lower() in ["true","1","yes","y"]

def bucket(sp):
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

hist["sp_valid_bool"] = hist["sp_valid"].apply(is_true)
hist["sp_num"] = hist["sp_num_settled"].apply(num)
hist["won_num"] = hist["won"].apply(num).fillna(0)
hist["finish_num"] = hist["finish_position"].apply(num)
hist["placed_num"] = np.where(hist["finish_num"].between(1,3), 1, 0)

lookup = hist.set_index(["race_key","horse"])[
    ["sp_valid_bool","sp_num","won_num","placed_num","finish_num"]
].to_dict("index")

rows = []

for _, r in races.iterrows():
    version = r["version"]
    race_key = r["race_key"]
    horse = r["version_top"]

    info = lookup.get((race_key, horse), {})

    sp_valid = bool(info.get("sp_valid_bool", False))
    sp = info.get("sp_num", np.nan)
    won = int(info.get("won_num", 0)) if not pd.isna(info.get("won_num", np.nan)) else 0
    placed = int(info.get("placed_num", 0)) if not pd.isna(info.get("placed_num", np.nan)) else 0

    if sp_valid and not pd.isna(sp):
        profit = (sp - 1.0) if won == 1 else -1.0
    else:
        profit = np.nan

    rows.append({
        "version": version,
        "race_key": race_key,
        "meeting_date": r.get("meeting_date",""),
        "track": r.get("track",""),
        "race_no": r.get("race_no",""),
        "horse": horse,
        "sp_valid": "YES" if sp_valid else "NO",
        "sp": sp,
        "price_bucket": bucket(sp),
        "won": won,
        "placed": placed,
        "profit_1u": profit,
        "top_changed_vs_base": r.get("top_changed_vs_base",""),
        "built_at": built_at,
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary_rows = []

for version, g0 in out.groupby("version"):
    g = g0[g0["sp_valid"] == "YES"].copy()
    bets = len(g)
    wins = int(g["won"].sum()) if bets else 0
    places = int(g["placed"].sum()) if bets else 0
    profit = pd.to_numeric(g["profit_1u"], errors="coerce").sum() if bets else 0
    avg_sp = pd.to_numeric(g["sp"], errors="coerce").mean() if bets else np.nan

    summary_rows.append({
        "version": version,
        "valid_bets": bets,
        "wins": wins,
        "places": places,
        "win_pct": round(wins / bets * 100, 3) if bets else "",
        "place_pct": round(places / bets * 100, 3) if bets else "",
        "avg_sp": round(avg_sp, 3) if not pd.isna(avg_sp) else "",
        "profit_1u": round(profit, 3),
        "roi_pct": round(profit / bets * 100, 3) if bets else "",
        "pot_pct": round(profit / bets * 100, 3) if bets else "",
        "research_only": "YES",
        "built_at": built_at,
    })

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

bucket_rows = []
for (version, price_bucket), g in out[out["sp_valid"] == "YES"].groupby(["version","price_bucket"]):
    bets = len(g)
    wins = int(g["won"].sum())
    places = int(g["placed"].sum())
    profit = pd.to_numeric(g["profit_1u"], errors="coerce").sum()

    bucket_rows.append({
        "version": version,
        "price_bucket": price_bucket,
        "bets": bets,
        "wins": wins,
        "places": places,
        "win_pct": round(wins / bets * 100, 3) if bets else "",
        "place_pct": round(places / bets * 100, 3) if bets else "",
        "profit_1u": round(profit, 3),
        "roi_pct": round(profit / bets * 100, 3) if bets else "",
        "built_at": built_at,
    })

buckets = pd.DataFrame(bucket_rows)
buckets.to_csv(BUCKETS, index=False)

print("[SP_VALID_ROI_REPLAY_V2] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
print(f"wrote={BUCKETS}")
