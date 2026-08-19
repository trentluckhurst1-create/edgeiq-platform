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
    x = str(x).upper()
    x = re.sub(r"\(.*?\)", "", x)
    x = re.sub(r"[^A-Z0-9 ]", "", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x

def make_key(df):
    df["horse_key"] = df["horse"].apply(norm)
    df["race_key"] = (
        df["track"].astype(str).str.upper().str.replace(" ", "")
        + "_"
        + df["race_no"].astype(str)
    )
    return df


RUNNER = make_key(RUNNER)
V8 = make_key(V8)
REL = make_key(REL)

print("[DEBUG] RUNNER sample keys:", RUNNER[["race_key","horse_key"]].head(3).to_string(index=False))
print("[DEBUG] V8 sample keys:", V8[["race_key","horse_key"]].head(3).to_string(index=False))


df = RUNNER.merge(V8, on=["race_key","horse_key"], how="left")
df = df.merge(REL, on=["race_key","horse_key"], how="left")

out = ROOT / "public/data/edgeiq_live_runner_board_UNIFIED_FIXED_v3.csv"
df.to_csv(out, index=False)

print("[FIXED UNIFIED PIPELINE V3 COMPLETE]")
print("rows:", len(df))
print("V8 matched:", df["v8_candidate_status"].notna().sum())
print("REL matched:", df["race_reliability_score_v1"].notna().sum())
