import pandas as pd
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNNER = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")
V8 = pd.read_csv(ROOT / "public/data/edgeiq_live_v8_candidate_display_feed_v1.csv")
REL = pd.read_csv(ROOT / "public/data/edgeiq_live_race_reliability_v1_feed.csv")

def norm(x):
    if pd.isna(x):
        return ""
    return str(x).upper().replace(" ", "")

RUNNER["race_key"] = RUNNER["track"].map(norm) + "_" + RUNNER["race_no"].astype(str)
V8["race_key"] = V8["track"].map(norm) + "_" + V8["race_no"].astype(str)
REL["race_key"] = REL["track"].map(norm) + "_" + REL["race_no"].astype(str)

RUNNER["horse_key"] = RUNNER["horse"].map(norm)
V8["horse_key"] = V8["horse"].map(norm)
REL["horse_key"] = REL["horse"].map(norm)

master = set(RUNNER["race_key"])

V8 = V8[V8["race_key"].isin(master)]
REL = REL[REL["race_key"].isin(master)]

print("[FILTER] RUNNER races:", RUNNER["race_key"].nunique())
print("[FILTER] V8 races:", V8["race_key"].nunique())
print("[FILTER] REL races:", REL["race_key"].nunique())

df = RUNNER.merge(V8, on=["race_key","horse_key"], how="left")
df = df.merge(REL, on=["race_key","horse_key"], how="left")

out = ROOT / "public/data/edgeiq_live_runner_board_UNIFIED_FIXED_v4.csv"
df.to_csv(out, index=False)

print("[UNIFIED PIPELINE V4 COMPLETE]")
print("rows:", len(df))
print("V8 matched:", df["v8_candidate_status"].notna().sum())
print("REL matched:", df["race_reliability_score_v1"].notna().sum())
