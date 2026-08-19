import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJ = DATA / "edgeiq_projection_v4_audit.csv"
TARGETS = DATA / "edgeiq_race_targets_v4.csv"
CORR = DATA / "edgeiq_manual_race_metadata_corrections_v1.csv"

OUT = DATA / "edgeiq_projection_v4_class_corrected_audit.csv"
AUDIT = DATA / "edgeiq_projection_v4_class_corrected_audit_summary.csv"

print("=" * 90)
print("EDGEIQ PROJECTION V4 CLASS CORRECTION AUDIT")
print("=" * 90)

proj = pd.read_csv(PROJ, low_memory=False)
targets = pd.read_csv(TARGETS, low_memory=False)
corr = pd.read_csv(CORR, low_memory=False)

def key_track(x):
    return str(x).upper().strip()

def key_race_no(x):
    return str(x).replace(".0", "").strip()

for df in [proj, corr]:
    df["_track_key"] = df["track"].map(key_track)
    df["_race_no_key"] = df["race_no"].map(key_race_no)
    df["_race_date_key"] = df["race_date"].astype(str).str.strip()

corr_small = corr[[
    "_race_date_key",
    "_track_key",
    "_race_no_key",
    "race_name_corrected",
    "race_class_corrected",
    "race_type_corrected",
    "correction_reason",
]]

merged = proj.merge(
    corr_small,
    on=["_race_date_key", "_track_key", "_race_no_key"],
    how="left"
)

merged["race_class_original"] = merged["race_class_clean"]
merged["race_class_v4_corrected"] = merged["race_class_corrected"].fillna(merged["race_class_clean"])
merged["race_type_v4_corrected"] = merged["race_type_corrected"].fillna("FLAT_OR_UNKNOWN")
merged["metadata_correction_applied"] = merged["race_class_corrected"].notna()

class_targets = targets[targets["ladder_level"] == "CLASS"].copy()
class_targets = class_targets[[
    "race_class_clean",
    "competitive_target_v4",
    "race_standard_target_v4",
    "winning_target_v4",
    "confidence",
    "target_quality_flag",
]]
class_targets = class_targets.rename(columns={
    "race_class_clean": "race_class_v4_corrected",
    "competitive_target_v4": "competitive_target_v4_corrected",
    "race_standard_target_v4": "race_standard_target_v4_corrected",
    "winning_target_v4": "winning_target_v4_corrected",
    "confidence": "target_confidence_v4_corrected",
    "target_quality_flag": "target_quality_flag_v4_corrected",
})

merged = merged.merge(
    class_targets,
    on="race_class_v4_corrected",
    how="left"
)

# Fallbacks for race classes not present in ladder.
# HURDLE and STEEPLECHASE need separate jumps ladder later, so use BM120 as temporary jumps proxy.
bm120 = class_targets[class_targets["race_class_v4_corrected"] == "BM120"]
if not bm120.empty:
    for c in [
        "competitive_target_v4_corrected",
        "race_standard_target_v4_corrected",
        "winning_target_v4_corrected",
        "target_confidence_v4_corrected",
        "target_quality_flag_v4_corrected",
    ]:
        mask = merged["race_class_v4_corrected"].isin(["HURDLE", "STEEPLECHASE"]) & merged[c].isna()
        merged.loc[mask, c] = bm120.iloc[0][c]
    merged.loc[
        merged["race_class_v4_corrected"].isin(["HURDLE", "STEEPLECHASE"]),
        "target_quality_flag_v4_corrected"
    ] = "JUMPS_PROXY_BM120_PENDING_DEDICATED_LADDER"

merged["projected_rating_v3"] = pd.to_numeric(merged["projected_rating_v3"], errors="coerce")

def classify(row):
    p = row["projected_rating_v3"]
    c = pd.to_numeric(row["competitive_target_v4_corrected"], errors="coerce")
    r = pd.to_numeric(row["race_standard_target_v4_corrected"], errors="coerce")
    w = pd.to_numeric(row["winning_target_v4_corrected"], errors="coerce")

    if pd.isna(p):
        return "NO_HISTORY"
    if pd.isna(c):
        return "NO_TARGET"
    if p >= w:
        return "WINNING_STANDARD"
    if p >= r:
        return "RACE_STANDARD"
    if p >= c:
        return "COMPETITIVE"
    return "NON_COMPETITIVE"

merged["v4_classification_corrected"] = merged.apply(classify, axis=1)

drop_cols = [c for c in merged.columns if c.startswith("_")]
merged = merged.drop(columns=drop_cols)
merged["built_at"] = datetime.now().isoformat(timespec="seconds")
merged.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rows_loaded", "value": len(proj)},
    {"metric": "metadata_corrections_applied_rows", "value": int(merged["metadata_correction_applied"].sum())},
    {"metric": "corrected_class_count", "value": int(merged["race_class_v4_corrected"].nunique())},
    {"metric": "missing_corrected_competitive_target", "value": int(merged["competitive_target_v4_corrected"].isna().sum())},
    {"metric": "missing_corrected_race_standard_target", "value": int(merged["race_standard_target_v4_corrected"].isna().sum())},
    {"metric": "missing_corrected_winning_target", "value": int(merged["winning_target_v4_corrected"].isna().sum())},
])
audit.to_csv(AUDIT, index=False)

print(f"WROTE {OUT}")
print(f"WROTE {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
