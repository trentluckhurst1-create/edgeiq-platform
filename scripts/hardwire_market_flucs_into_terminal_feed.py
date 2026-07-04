from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
FLUCS = DATA / "edgeiq_market_fluctuations_v1.csv"

def clean(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def key(v):
    return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())

def race_no_key(v):
    s = clean(v)
    try:
        return str(int(float(s)))
    except Exception:
        m = re.search(r"\d+", s)
        return str(int(m.group(0))) if m else key(s)

live = pd.read_csv(LIVE, dtype=str).fillna("")
flucs = pd.read_csv(FLUCS, dtype=str).fillna("")

lookup = {}
for _, r in flucs.iterrows():
    k = (key(r.get("track")), race_no_key(r.get("race_no")), key(r.get("horse")))
    ladder = clean(r.get("fluc_ladder"))
    if ladder:
        lookup[k] = ladder

matched = 0
for idx, r in live.iterrows():
    k = (key(r.get("track")), race_no_key(r.get("race_no")), key(r.get("horse")))
    ladder = lookup.get(k, "")
    if ladder:
        live.at[idx, "flucs"] = ladder
        live.at[idx, "last10"] = ladder
        live.at[idx, "last_10"] = ladder
        matched += 1

live.to_csv(LIVE, index=False)

print("=" * 80)
print("EDGEIQ TERMINAL FLUC HARDWIRE")
print("=" * 80)
print("live rows:", len(live))
print("fluc rows:", len(flucs))
print("matched:", matched)
print(live[(live["track"].str.upper() == "CAULFIELD") & (live["race_no"].astype(str) == "1")][["horse","flucs"]].to_string(index=False))
