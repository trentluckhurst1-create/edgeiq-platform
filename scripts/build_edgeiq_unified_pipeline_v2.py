import pandas as pd
import re
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TAB = pd.read_csv(ROOT / "public/data/tab_full_field_v2.csv")
RUNNER = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")
V8 = pd.read_csv(ROOT / "public/data/edgeiq_live_v8_candidate_display_feed_v1.csv")
REL = pd.read_csv(ROOT / "public/data/edgeiq_live_race_reliability_v1_feed.csv")

def clean(x):
    if pd.isna(x):
        return ""
    x = str(x).upper()
    x = x.replace("’","'").replace("?","'")
    x = re.sub(r"\(.*?\)", "", x)
    x = re.sub(r"[^A-Z0-9 ]", "", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x

def hid(x):
    return hashlib.md5(x.encode("utf-8")).hexdigest()

def add_keys(df):
    df["horse_clean"] = df["horse"].apply(clean)
    df["horse_id"] = df["horse_clean"].apply(hid)
    df["race_key"] = df["track"].astype(str) + "_" + df["race_no"].astype(str)
    return df


# APPLY ENTITY SYSTEM TO ALL TABLES
TAB = add_keys(TAB)
RUNNER = add_keys(RUNNER)
V8 = add_keys(V8)
REL = add_keys(REL)


# BASE MERGE
df = RUNNER.merge(
    TAB,
    on=["race_key","horse_id"],
    how="left"
)


# V8 MERGE (NOW FIXED)
df = df.merge(
    V8[[
        "race_key","horse_id",
        "v8_candidate_price_display",
        "v8_candidate_status",
        "confidence_score"
    ]],
    on=["race_key","horse_id"],
    how="left"
)


# RELIABILITY MERGE (NOW FIXED)
df = df.merge(
    REL[[
        "race_key","horse_id",
        "race_reliability_band_v1",
        "race_reliability_score_v1"
    ]],
    on=["race_key","horse_id"],
    how="left"
)


OUT = ROOT / "public/data/edgeiq_live_runner_board_UNIFIED_v2.csv"
df.to_csv(OUT, index=False)

print("[UNIFIED PIPELINE V2 COMPLETE]")
print("rows:", len(df))
print("TAB matched:", df["tab_fixed_win"].notna().sum())
print("V8 enriched:", df["v8_candidate_status"].notna().sum())
print("REL enriched:", df["race_reliability_band_v1"].notna().sum())
