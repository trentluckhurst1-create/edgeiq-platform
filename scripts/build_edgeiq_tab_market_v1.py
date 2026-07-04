from pathlib import Path
from datetime import datetime
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_tab_vic_racecards_v1.csv"
OUT = DATA / "edgeiq_tab_market_v1.csv"
SUMMARY = DATA / "edgeiq_tab_market_v1_summary.csv"

def norm(x):
    if pd.isna(x):
        return ""
    return re.sub(r"[^A-Z0-9]+", "", str(x).upper())

def scratched_status(x):
    s = str(x or "").upper()
    return "TRUE" if "SCRATCH" in s else "FALSE"

def to_num(x):
    try:
        return float(x)
    except Exception:
        return None

def movement_pct(open_price, current_price):
    o = to_num(open_price)
    c = to_num(current_price)
    if not o or not c or o <= 0 or c <= 0:
        return None
    return round(((c - o) / o) * 100, 2)

def movement_state(pct):
    if pct is None:
        return "UNKNOWN"
    if pct <= -20:
        return "STRONGLY FIRMING"
    if pct <= -10:
        return "FIRMING"
    if pct >= 20:
        return "STRONGLY DRIFTING"
    if pct >= 10:
        return "DRIFTING"
    return "STABLE"

df = pd.read_csv(SRC)

df["horse_key"] = df["horse"].apply(norm)
df["track_key"] = df["meeting_name"].apply(norm)
df["tab_scratched"] = df["tab_fixed_betting_status"].apply(scratched_status)
df["tab_market_move_pct"] = df.apply(
    lambda r: movement_pct(r.get("tab_fixed_open_win"), r.get("tab_fixed_win")),
    axis=1
)
df["tab_market_movement_state"] = df["tab_market_move_pct"].apply(movement_state)

out = pd.DataFrame({
    "scraped_at": datetime.now().isoformat(timespec="seconds"),
    "source": "TAB",
    "meeting_date": df.get("meeting_date"),
    "track": df.get("meeting_name"),
    "track_key": df["track_key"],
    "race_no": df.get("race_no"),
    "runner_no": df.get("runner_no"),
    "horse": df.get("horse"),
    "horse_key": df["horse_key"],
    "barrier": df.get("barrier"),
    "jockey": df.get("jockey"),
    "trainer": df.get("trainer"),

    "tab_fixed_win": df.get("tab_fixed_win"),
    "tab_fixed_place": df.get("tab_fixed_place"),
    "tab_fixed_open_win": df.get("tab_fixed_open_win"),
    "tab_fixed_betting_status": df.get("tab_fixed_betting_status"),
    "tab_scratched": df["tab_scratched"],

    "tab_market_move_pct": df["tab_market_move_pct"],
    "tab_market_movement_state": df["tab_market_movement_state"],

    "tab_tote_win": df.get("tab_tote_win"),
    "tab_tote_place": df.get("tab_tote_place"),
    "tab_early_speed_rating": df.get("early_speed_rating"),
    "tab_early_speed_band": df.get("early_speed_band"),
    "tab_dfs_form_rating": df.get("dfs_form_rating"),
    "runner_form_url": df.get("runner_form_url"),
    "silk_url": df.get("silk_url"),
})

out = out.sort_values(["track", "race_no", "runner_no"])
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "scraped_at": datetime.now().isoformat(timespec="seconds"),
    "rows": len(out),
    "tracks": out["track"].nunique(),
    "races": out[["track","race_no"]].drop_duplicates().shape[0],
    "scratched": (out["tab_scratched"] == "TRUE").sum(),
    "strongly_firming": (out["tab_market_movement_state"] == "STRONGLY FIRMING").sum(),
    "firming": (out["tab_market_movement_state"] == "FIRMING").sum(),
    "stable": (out["tab_market_movement_state"] == "STABLE").sum(),
    "drifting": (out["tab_market_movement_state"] == "DRIFTING").sum(),
    "strongly_drifting": (out["tab_market_movement_state"] == "STRONGLY DRIFTING").sum(),
    "unknown": (out["tab_market_movement_state"] == "UNKNOWN").sum(),
    "output": str(OUT),
}])
summary.to_csv(SUMMARY, index=False)

print("[tab_market] wrote", OUT)
print(summary.to_string(index=False))
print(out[[
    "track","race_no","runner_no","horse","tab_fixed_open_win","tab_fixed_win",
    "tab_market_move_pct","tab_market_movement_state","tab_fixed_betting_status"
]].head(120).to_string(index=False))
