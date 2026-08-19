import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNNER = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")
V8 = pd.read_csv(ROOT / "public/data/edgeiq_live_v8_candidate_display_feed_v1.csv")
REL = pd.read_csv(ROOT / "public/data/edgeiq_live_race_reliability_v1_feed.csv")

def make_race_key(df):
    return (
        df["meeting_date"].astype(str) + "|" +
        df["track"].astype(str).str.upper() + "|" +
        df["race_no"].astype(str)
    )

def norm_horse(x):
    return str(x).upper().replace(" ", "")

# FORCE ALL TO SAME KEY SYSTEM
RUNNER["race_key"] = make_race_key(RUNNER)
V8["race_key"] = make_race_key(V8)
REL["race_key"] = make_race_key(REL)

RUNNER["horse_key"] = RUNNER["horse"].map(norm_horse)
V8["horse_key"] = V8["horse"].map(norm_horse)
REL["horse_key"] = REL["horse"].map(norm_horse)

master = set(RUNNER["race_key"])

V8 = V8[V8["race_key"].isin(master)]
REL = REL[REL["race_key"].isin(master)]

print("[UNIFIED KEYS FIXED]")
print("RUNNER races:", RUNNER["race_key"].nunique())
print("V8 races:", V8["race_key"].nunique())
print("REL races:", REL["race_key"].nunique())

df = RUNNER.merge(V8, on=["race_key","horse_key"], how="left")
df = df.merge(REL, on=["race_key","horse_key"], how="left")

out = ROOT / "public/data/edgeiq_live_runner_board_UNIFIED_FINAL_v5.csv"
df.to_csv(out, index=False)

print("[FINAL PIPELINE COMPLETE]")
print("rows:", len(df))
print("V8 matched:", df["v8_candidate_status"].notna().sum())
print("REL matched:", df["race_reliability_score_v1"].notna().sum())
