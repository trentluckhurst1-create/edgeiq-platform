import pandas as pd
import re
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FULL = ROOT / "public/data/tab_full_field_v2.csv"
RUNNER = ROOT / "public/data/edgeiq_live_runner_board_v1.csv"

OUT = ROOT / "public/data/edgeiq_live_runner_board_v4.csv"
MAP_OUT = ROOT / "public/data/horse_entity_map_v1.csv"


# ----------------------------
# NORMALISATION (STRICT)
# ----------------------------
def clean_name(x):
    if pd.isna(x):
        return ""

    x = str(x).upper()

    # unify apostrophes / junk chars
    x = x.replace("’", "'").replace("?", "'")

    # remove SCR markers and parentheses content
    x = re.sub(r"\(.*?\)", "", x)

    # keep only letters/numbers/spaces
    x = re.sub(r"[^A-Z0-9 ]", "", x)

    # collapse whitespace
    x = re.sub(r"\s+", " ", x).strip()

    return x


# ----------------------------
# STABLE ID GENERATOR
# ----------------------------
def horse_id(name):
    return hashlib.md5(name.encode("utf-8")).hexdigest()


# ----------------------------
# LOAD
# ----------------------------
full = pd.read_csv(FULL)
runner = pd.read_csv(RUNNER)

# ----------------------------
# BUILD CANONICAL KEYS
# ----------------------------
full["horse_clean"] = full["horse"].apply(clean_name)
runner["horse_clean"] = runner["horse"].apply(clean_name)

full["horse_id"] = full["horse_clean"].apply(horse_id)
runner["horse_id"] = runner["horse_clean"].apply(horse_id)


# ----------------------------
# CREATE GLOBAL ENTITY MAP
# ----------------------------
entity_map = pd.concat([
    full[["horse","horse_clean","horse_id"]],
    runner[["horse","horse_clean","horse_id"]]
]).drop_duplicates()

entity_map.to_csv(MAP_OUT, index=False)


# ----------------------------
# RACE KEY (OPTIONAL FUTURE LOCK)
# ----------------------------
full["race_key"] = full["track"].astype(str) + "_" + full["race_no"].astype(str)
runner["race_key"] = runner["track"].astype(str) + "_" + runner["race_no"].astype(str)


# ----------------------------
# FINAL MERGE (ZERO AMBIGUITY)
# ----------------------------
merged = runner.merge(
    full,
    on=["race_key", "horse_id"],
    how="left",
    suffixes=("_runner", "_tab")
)


# ----------------------------
# OUTPUT
# ----------------------------
merged.to_csv(OUT, index=False)

print("[ENTITY CORE v1 COMPLETE]")
print("rows:", len(merged))
print("matched TAB fields:", merged["tab_fixed_win"].notna().sum())
print("unique horses:", merged["horse_id"].nunique())
print("entity map written:", MAP_OUT)
