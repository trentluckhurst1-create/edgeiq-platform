from pathlib import Path
from datetime import datetime
import re
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TAB = DATA / "edgeiq_tab_market_v1.csv"
LIVE = DATA / "edgeiq_live_runner_board_v1.csv"

OUT = DATA / "edgeiq_tab_market_intelligence_v1.csv"
SUMMARY = DATA / "edgeiq_tab_market_intelligence_v1_summary.csv"

def norm(x):
    if pd.isna(x):
        return ""
    return re.sub(r"[^A-Z0-9]+", "", str(x).upper())

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(x)
    except Exception:
        return np.nan

def edge_pct(price, fair):
    price = num(price)
    fair = num(fair)
    if pd.isna(price) or pd.isna(fair) or fair <= 0:
        return np.nan
    return round(((price / fair) - 1) * 100, 1)

def action_from_edge(edge, scratched, move_state):
    if str(scratched).upper() == "TRUE":
        return "SCRATCHED"
    if pd.isna(edge):
        return "NO FAIR"
    if edge >= 18 and move_state in ["STRONGLY FIRMING", "FIRMING", "STABLE"]:
        return "EXECUTE"
    if edge >= 18:
        return "STRONG WATCH"
    if edge >= 10:
        return "WATCH"
    if edge >= 6:
        return "LEAN"
    return "PASS"

tab = pd.read_csv(TAB)
tab["horse_key"] = tab["horse"].apply(norm)
tab["track_key"] = tab["track"].apply(norm)
tab["race_no_key"] = tab["race_no"].astype(str)

live_cols = []
live = pd.DataFrame()

if LIVE.exists():
    live = pd.read_csv(LIVE)
    live["horse_key"] = live["horse"].apply(norm)
    if "track" in live.columns:
        live["track_key"] = live["track"].apply(norm)
    else:
        live["track_key"] = ""
    live["race_no_key"] = live["race_no"].astype(str) if "race_no" in live.columns else ""

    fair_candidates = [
        "fair_price",
        "edgeiq_fair_price",
        "model_fair_price",
        "rated_price",
        "edgeiq_price",
    ]

    fair_col = next((c for c in fair_candidates if c in live.columns), None)

    keep = ["horse_key", "track_key", "race_no_key"]
    if fair_col:
        keep.append(fair_col)

    if "edge_pct" in live.columns:
        keep.append("edge_pct")
    if "execution_action" in live.columns:
        keep.append("execution_action")
    if "confidence_score" in live.columns:
        keep.append("confidence_score")

    live_small = live[keep].drop_duplicates(subset=["horse_key", "track_key", "race_no_key"])
    live_cols = keep

    merged = tab.merge(
        live_small,
        on=["horse_key", "track_key", "race_no_key"],
        how="left",
        suffixes=("", "_edgeiq")
    )

    if fair_col:
        merged["edgeiq_fair_price"] = merged[fair_col].apply(num)
    else:
        merged["edgeiq_fair_price"] = np.nan
else:
    merged = tab.copy()
    merged["edgeiq_fair_price"] = np.nan

merged["tab_fixed_win_num"] = merged["tab_fixed_win"].apply(num)
merged["tab_edge_pct"] = merged.apply(
    lambda r: edge_pct(r["tab_fixed_win_num"], r["edgeiq_fair_price"]),
    axis=1
)

merged["tab_market_intelligence_action"] = merged.apply(
    lambda r: action_from_edge(
        r["tab_edge_pct"],
        r.get("tab_scratched", ""),
        r.get("tab_market_movement_state", "")
    ),
    axis=1
)

merged["market_agreement"] = merged.apply(
    lambda r: (
        "SCRATCHED" if str(r.get("tab_scratched", "")).upper() == "TRUE"
        else "AGREEING" if r.get("tab_market_movement_state") in ["STRONGLY FIRMING", "FIRMING"]
        else "DISAGREEING" if r.get("tab_market_movement_state") in ["DRIFTING", "STRONGLY DRIFTING"]
        else "NEUTRAL"
    ),
    axis=1
)

out_cols = [
    "scraped_at",
    "track",
    "race_no",
    "runner_no",
    "horse",
    "horse_key",
    "barrier",
    "jockey",
    "trainer",
    "tab_fixed_open_win",
    "tab_fixed_win",
    "tab_fixed_place",
    "tab_market_move_pct",
    "tab_market_movement_state",
    "tab_fixed_betting_status",
    "tab_scratched",
    "tab_early_speed_band",
    "tab_early_speed_rating",
    "tab_dfs_form_rating",
    "edgeiq_fair_price",
    "tab_edge_pct",
    "market_agreement",
    "tab_market_intelligence_action",
    "runner_form_url",
    "silk_url",
]

for c in out_cols:
    if c not in merged.columns:
        merged[c] = ""

out = merged[out_cols].copy()
out = out.sort_values(["track", "race_no", "runner_no"])
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "scraped_at": datetime.now().isoformat(timespec="seconds"),
    "rows": len(out),
    "tracks": out["track"].nunique(),
    "races": out[["track", "race_no"]].drop_duplicates().shape[0],
    "scratched": (out["tab_scratched"].astype(str).str.upper() == "TRUE").sum(),
    "with_edgeiq_fair": out["edgeiq_fair_price"].apply(num).notna().sum(),
    "execute": (out["tab_market_intelligence_action"] == "EXECUTE").sum(),
    "strong_watch": (out["tab_market_intelligence_action"] == "STRONG WATCH").sum(),
    "watch": (out["tab_market_intelligence_action"] == "WATCH").sum(),
    "lean": (out["tab_market_intelligence_action"] == "LEAN").sum(),
    "pass": (out["tab_market_intelligence_action"] == "PASS").sum(),
    "scratched_action": (out["tab_market_intelligence_action"] == "SCRATCHED").sum(),
    "no_fair": (out["tab_market_intelligence_action"] == "NO FAIR").sum(),
    "output": str(OUT),
}])
summary.to_csv(SUMMARY, index=False)

print("[tab_intel] wrote", OUT)
print(summary.to_string(index=False))
print(out.head(120).to_string(index=False))
