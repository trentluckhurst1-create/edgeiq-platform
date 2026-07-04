import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_official_runs_master_v1.csv"
OUT = DATA / "edgeiq_historical_performance_rating_v2.csv"
AUDIT = DATA / "edgeiq_historical_performance_rating_v2_audit.csv"

print("=" * 90)
print("EDGEIQ HISTORICAL PERFORMANCE RATING V2 — CALIBRATED")
print("=" * 90)

df = pd.read_csv(SRC, low_memory=False)

def bool_true(s):
    return s.astype(str).str.strip().str.upper().eq("TRUE")

def parse_finish(v):
    if pd.isna(v):
        return np.nan
    t = str(v).strip().upper()
    if not t:
        return np.nan
    m = re.search(r"(\d+)", t)
    if not m:
        return np.nan
    n = int(m.group(1))
    return float(n) if 1 <= n <= 30 else np.nan

def parse_of_field(v):
    if pd.isna(v):
        return np.nan
    t = str(v).strip().upper()
    m = re.search(r"OF\s+(\d+)", t)
    if not m:
        return np.nan
    n = int(m.group(1))
    return float(n) if 1 <= n <= 30 else np.nan

def parse_margin(v, finish):
    if pd.isna(v) or str(v).strip() == "":
        return 0.0 if finish == 1 else np.nan
    t = str(v).strip().upper()
    m = re.search(r"(\d+(?:\.\d+)?)", t)
    if finish == 1:
        return 0.0
    if not m:
        return np.nan
    x = float(m.group(1))
    return x if 0 <= x <= 150 else np.nan

rows_loaded = len(df)

df = df[
    bool_true(df["official_run_flag"]) &
    (~bool_true(df["trial_flag"])) &
    (~bool_true(df["jumpout_flag"]))
].copy()

rows_after_flags = len(df)

df["finish_position"] = df["finish_pos"].apply(parse_finish)
df["field_from_finish_text"] = df["finish_pos"].apply(parse_of_field)
df["margin_numeric"] = [
    parse_margin(m, f) for m, f in zip(df["margin"], df["finish_position"])
]
df["distance_numeric"] = pd.to_numeric(df["distance"], errors="coerce")

df["horse_clean"] = df["horse"].astype(str).str.strip()
df["track_clean"] = df["track"].astype(str).str.strip().str.upper()
df["race_date_clean"] = df["race_date"].astype(str).str.strip()
df["race_no_clean"] = df["race_no"].astype(str).str.strip()
df["race_class_clean"] = df["race_class"].astype(str).str.strip().str.upper()
df["condition_recovered"] = df["track_condition"].astype(str).str.strip().str.upper()

group_cols = [
    "race_date_clean",
    "track_clean",
    "distance_numeric",
    "race_class_clean",
    "condition_recovered",
]

df["field_size_group_est"] = df.groupby(group_cols, dropna=False)["horse_clean"].transform("count")
df["field_size"] = df["field_from_finish_text"].fillna(df["field_size_group_est"])
df["field_size"] = pd.to_numeric(df["field_size"], errors="coerce").fillna(df["finish_position"])
df["field_size"] = df[["field_size", "finish_position"]].max(axis=1)
df["field_size"] = df["field_size"].clip(lower=1, upper=20)

rows_valid_finish = int(df["finish_position"].notna().sum())
rows_valid_margin = int(df["margin_numeric"].notna().sum())
rows_valid_distance = int(df["distance_numeric"].notna().sum())

df = df[
    df["horse_clean"].ne("") &
    df["finish_position"].notna() &
    df["margin_numeric"].notna() &
    df["distance_numeric"].notna()
].copy()

rows_written = len(df)

finish = df["finish_position"].astype(float)
margin = df["margin_numeric"].astype(float).clip(lower=0)
field = df["field_size"].astype(float).clip(lower=1, upper=20)

# V2 CALIBRATION
# Goal:
# - preserve finish-position ordering
# - reduce winner ceiling saturation
# - reduce floor saturation
# - remain class-independent
# Does NOT use class, SP, price, market, benchmark, grade, or overlay.

base = 68.0

position_score = np.maximum(0, (field - finish) / np.maximum(field - 1, 1)) * 13.0

winner_bonus = np.where(finish == 1, 8.5, 0.0)
placing_bonus = np.where((finish > 1) & (finish <= 3), 4.0, 0.0)
top_half_bonus = np.where(finish <= np.ceil(field / 2), 1.5, 0.0)

close_margin_bonus = np.select(
    [
        margin <= 0.5,
        margin <= 1.0,
        margin <= 2.0,
        margin <= 3.0,
    ],
    [
        3.5,
        2.5,
        1.5,
        0.75,
    ],
    default=0.0,
)

# Softer than V1.
margin_penalty = np.minimum(38.0, margin * 2.6)

rating = (
    base
    + position_score
    + winner_bonus
    + placing_bonus
    + top_half_bonus
    + close_margin_bonus
    - margin_penalty
)

# V2 uses wider natural scale with softer floor/ceiling.
df["performance_rating_v2"] = np.round(np.clip(rating, 25, 108), 2)

df["performance_band_v2"] = np.select(
    [
        df["performance_rating_v2"] >= 100,
        df["performance_rating_v2"] >= 94,
        df["performance_rating_v2"] >= 87,
        df["performance_rating_v2"] >= 78,
        df["performance_rating_v2"] >= 68,
        df["performance_rating_v2"] >= 55,
    ],
    ["ELITE", "STRONG", "SOLID", "COMPETITIVE", "OK", "WEAK"],
    default="POOR",
)

df["performance_reason_v2"] = np.select(
    [
        finish == 1,
        margin <= 0.5,
        margin <= 1.5,
        margin <= 3.0,
        margin >= 10.0,
    ],
    [
        "winner performance",
        "very close finish",
        "close-up performance",
        "competitive performance",
        "well beaten",
    ],
    default="standard run",
)

out = pd.DataFrame({
    "built_at": datetime.now().isoformat(timespec="seconds"),
    "horse": df["horse_clean"],
    "track": df["track_clean"],
    "race_date": df["race_date_clean"],
    "race_no": df["race_no_clean"],
    "distance": df["distance_numeric"].astype(int),
    "condition_recovered": df["condition_recovered"],
    "race_class_clean": df["race_class_clean"],
    "finish_pos_raw": df["finish_pos"],
    "finish_position": df["finish_position"].astype(int),
    "field_size": df["field_size"].round(0).astype(int),
    "margin_raw": df["margin"],
    "margin": df["margin_numeric"].round(2),
    "performance_rating_v2": df["performance_rating_v2"],
    "performance_band_v2": df["performance_band_v2"],
    "performance_reason_v2": df["performance_reason_v2"],
})

out = out.sort_values(
    ["race_date", "track", "distance", "race_no", "finish_position", "horse"],
    kind="stable"
)

audit = pd.DataFrame([
    {"metric": "rows_loaded", "value": rows_loaded},
    {"metric": "rows_after_official_trial_jumpout_filters", "value": rows_after_flags},
    {"metric": "rows_valid_finish_after_filters", "value": rows_valid_finish},
    {"metric": "rows_valid_margin_after_filters", "value": rows_valid_margin},
    {"metric": "rows_valid_distance_after_filters", "value": rows_valid_distance},
    {"metric": "rows_written", "value": rows_written},
    {"metric": "rows_lost_after_flag_filter", "value": rows_after_flags - rows_written},
    {"metric": "ratings_ge_105", "value": int((out["performance_rating_v2"] >= 105).sum())},
    {"metric": "ratings_le_20", "value": int((out["performance_rating_v2"] <= 20).sum())},
    {"metric": "ratings_le_30", "value": int((out["performance_rating_v2"] <= 30).sum())},
])

out.to_csv(OUT, index=False)
audit.to_csv(AUDIT, index=False)

print(f"rows_loaded: {rows_loaded:,}")
print(f"rows_after_official_trial_jumpout_filters: {rows_after_flags:,}")
print(f"rows_written: {rows_written:,}")
print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print("")
print("BAND COUNTS")
print(out["performance_band_v2"].value_counts(dropna=False).to_string())
print("")
print("RATING SUMMARY")
print(out["performance_rating_v2"].describe().to_string())
print("")
print("CEILING/FLOOR")
print("ratings_ge_105:", int((out["performance_rating_v2"] >= 105).sum()))
print("ratings_le_20:", int((out["performance_rating_v2"] <= 20).sum()))
print("ratings_le_30:", int((out["performance_rating_v2"] <= 30).sum()))
print("=" * 90)
