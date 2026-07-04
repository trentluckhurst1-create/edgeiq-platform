from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST = DATA / "edgeiq_historical_replay_settled_v1.csv"
BY_RACE = DATA / "edgeiq_runner_dna_weight_ladder_v1_by_race.csv"

OUT = DATA / "edgeiq_runner_dna_v6_3_top_selection_sp_coverage_audit_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_3_top_selection_sp_coverage_audit_v1_summary.csv"

built_at = datetime.now(timezone.utc).isoformat()

def num(x):
    try:
        s = str(x).replace("$","").replace("%","").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def truthy(x):
    return str(x).strip().lower() in ["true","yes","1","y"]

hist = pd.read_csv(HIST, dtype=str).fillna("")
races = pd.read_csv(BY_RACE, dtype=str).fillna("")

hist["sp_valid_bool"] = hist["sp_valid"].apply(truthy)
hist["sp_num"] = hist["sp_num_settled"].apply(num)
hist["won_num"] = hist["won"].apply(num).fillna(0)
hist["finish_num"] = hist["finish_position"].apply(num)
hist["placed_num"] = np.where(hist["finish_num"].between(1,3), 1, 0)

lookup = hist.set_index(["race_key","horse"])[["sp_valid_bool","sp_num","won_num","placed_num","finish_num"]].to_dict("index")

rows = []
for _, r in races.iterrows():
    info = lookup.get((r["race_key"], r["version_top"]), {})
    sp_valid = bool(info.get("sp_valid_bool", False))
    sp = info.get("sp_num", np.nan)
    won = int(info.get("won_num", 0)) if not pd.isna(info.get("won_num", np.nan)) else 0
    placed = int(info.get("placed_num", 0)) if not pd.isna(info.get("placed_num", np.nan)) else 0

    profit = np.nan
    if sp_valid and not pd.isna(sp):
        profit = (sp - 1.0) if won == 1 else -1.0

    rows.append({
        "version": r["version"],
        "race_key": r["race_key"],
        "track": r.get("track",""),
        "race_no": r.get("race_no",""),
        "version_top": r["version_top"],
        "sp_valid": "YES" if sp_valid else "NO",
        "sp": sp,
        "won": won,
        "placed": placed,
        "profit_1u": profit,
        "top_changed_vs_base": r.get("top_changed_vs_base",""),
        "built_at": built_at,
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary_rows = []
for version, g in out.groupby("version"):
    total_races = len(g)
    valid = g[g["sp_valid"] == "YES"].copy()
    missing = g[g["sp_valid"] != "YES"].copy()

    for segment_name, seg in [
        ("ALL_TOP_SELECTIONS", g),
        ("SP_VALID_ONLY", valid),
        ("NO_SP_ONLY", missing),
    ]:
        n = len(seg)
        wins = int(seg["won"].sum()) if n else 0
        places = int(seg["placed"].sum()) if n else 0
        valid_bets = int((seg["sp_valid"] == "YES").sum()) if n else 0
        profit = pd.to_numeric(seg["profit_1u"], errors="coerce").sum() if valid_bets else np.nan

        summary_rows.append({
            "version": version,
            "segment": segment_name,
            "rows": n,
            "sp_valid_rows": valid_bets,
            "sp_valid_pct_of_version": round(valid_bets / total_races * 100, 3) if total_races else "",
            "wins": wins,
            "places": places,
            "win_pct": round(wins / n * 100, 3) if n else "",
            "place_pct": round(places / n * 100, 3) if n else "",
            "profit_1u_valid_only": round(profit, 3) if not pd.isna(profit) else "",
            "roi_pct_valid_only": round(profit / valid_bets * 100, 3) if valid_bets else "",
            "research_only": "YES",
            "built_at": built_at,
        })

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

print("[TOP_SELECTION_SP_COVERAGE_AUDIT_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
