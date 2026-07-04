import pandas as pd
import re
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TAB = ROOT / "public/data/tab_full_field_v2.csv"
RUNNER = ROOT / "public/data/edgeiq_live_runner_board_v1.csv"
V8 = ROOT / "public/data/edgeiq_live_v8_candidate_display_feed_v1.csv"
REL = ROOT / "public/data/edgeiq_live_race_reliability_v1_feed.csv"

OUT = ROOT / "public/data/edgeiq_live_runner_board_UNIFIED_v1.csv"
ENTITY_MAP = ROOT / "public/data/horse_entity_map_v2.csv"


# ----------------------------
# NORMALISATION
# ----------------------------
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


def key(df):
    df["horse_clean"] = df["horse"].apply(clean)
    df["horse_id"] = df["horse_clean"].apply(hid)
    df["race_key"] = df["track"].astype(str) + "_" + df["race_no"].astype(str)
    return df


# ----------------------------
# LOAD ALL SOURCES
# ----------------------------
tab = pd.read_csv(TAB)
runner = pd.read_csv(RUNNER)
v8 = pd.read_csv(V8)
rel = pd.read_csv(REL)

tab = key(tab)
runner = key(runner)
v8 = key(v8)
rel = key(rel)


# ----------------------------
# ENTITY MAP (GLOBAL TRUTH)
# ----------------------------
entity_map = pd.concat([
    tab[["horse","horse_clean","horse_id"]],
    runner[["horse","horse_clean","horse_id"]]
]).drop_duplicates()

entity_map.to_csv(ENTITY_MAP, index=False)


# ----------------------------
# BASE MERGE (TAB + RUNNER)
# ----------------------------
df = runner.merge(
    tab,
    on=["race_key","horse_id"],
    how="left",
    suffixes=("_runner","_tab")
)


# ----------------------------
# V8 MERGE
# ----------------------------
df = df.merge(
    v8[["race_key","horse_id",
        "v8_candidate_price_display",
        "v8_candidate_status",
        "confidence_score"]],
    on=["race_key","horse_id"],
    how="left"
)


# ----------------------------
# RELIABILITY MERGE
# ----------------------------
df = df.merge(
    rel[["race_key","horse_id",
        "race_reliability_band_v1",
        "race_reliability_score_v1"]],
    on=["race_key","horse_id"],
    how="left"
)


# ----------------------------
# FINAL OUTPUT
# ----------------------------
df.to_csv(OUT, index=False)

print("[UNIFIED PIPELINE COMPLETE]")
print("rows:", len(df))
print("races:", df["race_key"].nunique())
print("matched TAB:", df["tab_fixed_win"].notna().sum())
print("v8 enriched:", df["v8_candidate_price_display"].notna().sum())
print("reliability enriched:", df["race_reliability_band_v1"].notna().sum())
