import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

RATING = DATA / "edgeiq_historical_performance_rating_v3.csv"
CLEAN = DATA / "edgeiq_historical_class_clean_v2.csv"

OUT = DATA / "edgeiq_historical_performance_rating_v3_2.csv"
AUDIT = DATA / "edgeiq_historical_performance_rating_v3_2_audit.csv"
MISS = DATA / "edgeiq_historical_performance_rating_v3_2_misses.csv"

print("=" * 90)
print("EDGEIQ HISTORICAL PERFORMANCE RATING V3.2 — RACE LEVEL CLASS JOIN")
print("=" * 90)

rating = pd.read_csv(RATING, low_memory=False)
clean = pd.read_csv(CLEAN, low_memory=False)

def norm_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x).upper().strip())

def dist_round(x):
    v = pd.to_numeric(x, errors="coerce")
    if pd.isna(v):
        return ""
    return str(int(round(float(v) / 25.0) * 25))

def date_key(x):
    if pd.isna(x):
        return ""
    return str(x).strip()[:10]

def valid_class(x):
    x = norm_text(x)
    if x in ["", "UNKNOWN", "TRIAL_OR_JUMPOUT", "HANDICAP_UNRESOLVED"]:
        return False
    return True

for df in [rating, clean]:
    df["_race_date_key"] = df["race_date"].map(date_key)
    df["_track_key"] = df["track"].map(norm_text)
    df["_distance_round25_key"] = df["distance"].map(dist_round)
    df["_source_file_key"] = df["source_file"].map(norm_text) if "source_file" in df.columns else ""

clean["_class_is_valid"] = clean["race_class_model_v2"].apply(valid_class)

# Keep valid clean classes first. If no valid class exists for a race context, fallback can still carry UNKNOWN.
clean_valid = clean[clean["_class_is_valid"]].copy()
clean_all = clean.copy()

join_cols = ["_race_date_key", "_track_key", "_distance_round25_key"]

clean_race_valid = (
    clean_valid
    .sort_values(["class_model_confidence_v2", "race_class_model_v2"], ascending=[True, True])
    .drop_duplicates(join_cols, keep="first")
)

clean_race_all = (
    clean_all
    .sort_values(["class_model_confidence_v2", "race_class_model_v2"], ascending=[True, True])
    .drop_duplicates(join_cols, keep="first")
)

keep_cols = join_cols + [
    "race_class_model_v2",
    "class_model_family_v2",
    "class_model_confidence_v2",
    "race_type_recovered",
    "age_restriction_recovered",
    "sex_restriction_recovered",
    "condition_token_recovered",
    "class_recovery_status",
    "class_recovery_reason",
    "race_name",
    "race_class_raw",
]

valid_keep = clean_race_valid[keep_cols].copy()
all_keep = clean_race_all[keep_cols].copy()

valid_keep = valid_keep.add_suffix("_valid")
all_keep = all_keep.add_suffix("_all")

for c in join_cols:
    valid_keep = valid_keep.rename(columns={c + "_valid": c})
    all_keep = all_keep.rename(columns={c + "_all": c})

merged = rating.merge(valid_keep, on=join_cols, how="left")
merged = merged.merge(all_keep, on=join_cols, how="left")

fields = [
    "race_class_model_v2",
    "class_model_family_v2",
    "class_model_confidence_v2",
    "race_type_recovered",
    "age_restriction_recovered",
    "sex_restriction_recovered",
    "condition_token_recovered",
    "class_recovery_status",
    "class_recovery_reason",
    "race_name",
    "race_class_raw",
]

for f in fields:
    merged[f] = merged[f"{f}_valid"].where(
        merged[f"{f}_valid"].notna(),
        merged[f"{f}_all"]
    )

merged["clean_class_join_status_v3_2"] = np.select(
    [
        merged["race_class_model_v2_valid"].notna(),
        merged["race_class_model_v2_all"].notna(),
    ],
    [
        "JOINED_VALID_CLASS_RACE_LEVEL",
        "JOINED_NON_VALID_CLASS_RACE_LEVEL",
    ],
    default="NOT_JOINED"
)

merged["race_class_clean_v3_2"] = merged["race_class_model_v2"]
merged["race_class_family_v3_2"] = merged["class_model_family_v2"]
merged["race_class_confidence_v3_2"] = merged["class_model_confidence_v2"]

drop_cols = [c for c in merged.columns if c.endswith("_valid") or c.endswith("_all") or c.startswith("_")]
merged = merged.drop(columns=drop_cols)

merged["built_at_v3_2"] = datetime.now().isoformat(timespec="seconds")
merged.to_csv(OUT, index=False)

miss = merged[merged["clean_class_join_status_v3_2"].eq("NOT_JOINED")].copy()
miss.to_csv(MISS, index=False)

audit = pd.DataFrame([
    {"metric": "rating_rows_loaded", "value": len(rating)},
    {"metric": "rows_written", "value": len(merged)},
    {"metric": "joined_valid_class", "value": int(merged["clean_class_join_status_v3_2"].eq("JOINED_VALID_CLASS_RACE_LEVEL").sum())},
    {"metric": "joined_non_valid_class", "value": int(merged["clean_class_join_status_v3_2"].eq("JOINED_NON_VALID_CLASS_RACE_LEVEL").sum())},
    {"metric": "not_joined", "value": int(merged["clean_class_join_status_v3_2"].eq("NOT_JOINED").sum())},
    {"metric": "usable_clean_class_rows", "value": int(merged["race_class_confidence_v3_2"].isin(["HIGH","MEDIUM"]).sum())},
    {"metric": "unresolved_clean_class_rows", "value": int(merged["race_class_family_v3_2"].eq("UNRESOLVED").sum())},
    {"metric": "excluded_trial_jumpout_rows", "value": int(merged["race_class_family_v3_2"].eq("EXCLUDED_TRIAL_JUMPOUT").sum())},
])

audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(f"wrote: {MISS}")
print(audit.to_string(index=False))
print("=" * 90)
