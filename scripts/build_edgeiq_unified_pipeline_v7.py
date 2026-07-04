import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNNER = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")
V8 = pd.read_csv(ROOT / "public/data/edgeiq_live_v8_candidate_display_feed_v1.csv")
REL = pd.read_csv(ROOT / "public/data/edgeiq_live_race_reliability_v1_feed.csv")

def norm(x):
    return str(x).upper().replace(" ", "")

# FORCE REL INTO RUNNER KEY SYSTEM (CRITICAL FIX)
REL["race_key"] = REL["track"].map(norm) + "_" + REL["race_no"].astype(str)

RUNNER["race_key"] = RUNNER["track"].map(norm) + "_" + RUNNER["race_no"].astype(str)
V8["race_key"] = V8["track"].map(norm) + "_" + V8["race_no"].astype(str)

def norm_horse(x):
    return str(x).upper().replace(" ", "")

RUNNER["horse_key"] = RUNNER["horse"].map(norm_horse)
V8["horse_key"] = V8["horse"].map(norm_horse)
REL["horse_key"] = REL["horse"].map(norm_horse)

# NOW SAFE FILTER
master = set(RUNNER["race_key"])

V8 = V8[V8["race_key"].isin(master)]
REL = REL[REL["race_key"].isin(master)]

print("[FINAL ALIGNMENT CHECK]")
print("RUNNER races:", RUNNER["race_key"].nunique())
print("V8 races:", V8["race_key"].nunique())
print("REL races:", REL["race_key"].nunique())

df = RUNNER.merge(V8, on=["race_key","horse_key"], how="left")
df = df.merge(REL, on=["race_key","horse_key"], how="left")

out = ROOT / "public/data/edgeiq_live_runner_board_FINAL_UNIFIED_v7.csv"
df.to_csv(out, index=False)

print("[DONE]")
print("rows:", len(df))
print("V8 matched:", df["v8_candidate_status"].notna().sum())
print("REL matched:", df["race_reliability_score_v1"].notna().sum())
