from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

DATA = Path(r".\public\data")
SRC = DATA / "edgeiq_current_field_projection_v5_2.csv"
BACKUP = DATA / "edgeiq_current_field_projection_v5_2_PRE_TARGET_SCALE_REPAIR.csv"
AUDIT = DATA / "edgeiq_target_scale_repair_v5_2_audit.csv"

df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)
df.to_csv(BACKUP, index=False)

for col in [
    "projected_rating_v5_2",
    "race_target_rating_v5_2",
    "projection_gap_v5_2",
    "starts_found_v5_2",
]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

matched = df[
    df["history_match_status_v5_2"].astype(str).eq("MATCHED_HISTORY")
    & df["projected_rating_v5_2"].notna()
    & df["race_target_rating_v5_2"].notna()
].copy()

if matched.empty:
    raise SystemExit("No matched projected rows available for target scale repair")

matched["target_minus_projected"] = matched["race_target_rating_v5_2"] - matched["projected_rating_v5_2"]

offset_mean = float(matched["target_minus_projected"].mean())
offset_median = float(matched["target_minus_projected"].median())

# Use median to avoid one or two extreme ratings distorting the scale.
scale_offset = offset_median

df["race_target_rating_raw_v5_2"] = df["race_target_rating_v5_2"]

mask_target = df["race_target_rating_v5_2"].notna()
df.loc[mask_target, "race_target_rating_v5_2"] = (
    df.loc[mask_target, "race_target_rating_v5_2"] - scale_offset
)

df["target_scale_offset_v5_2"] = round(scale_offset, 2)
df["target_scale_repair_method_v5_2"] = "MEDIAN_TARGET_MINUS_PROJECTED_OFFSET"
df["target_formula_v5_2"] = (
    "raw_target - median(raw_target - projected_rating) across matched current runners"
)

df["projection_gap_v5_2"] = np.where(
    df["projected_rating_v5_2"].notna() & df["race_target_rating_v5_2"].notna(),
    df["projected_rating_v5_2"] - df["race_target_rating_v5_2"],
    np.nan,
)

def band(v):
    if pd.isna(v):
        return "NO_PROJECTION"
    v = float(v)
    if v >= 8:
        return "ELITE"
    if v >= 4:
        return "STRONG"
    if v >= 1:
        return "POSITIVE"
    if v >= -1:
        return "NEUTRAL"
    if v >= -4:
        return "NEGATIVE"
    return "POOR"

df["projection_band_v5_2"] = df["projection_gap_v5_2"].map(band)

df["is_no_history_for_pricing_v5_2"] = np.where(
    df["history_match_status_v5_2"].astype(str).eq("NO_HISTORY"),
    "TRUE",
    "FALSE",
)

df["target_notes_v5_2"] = (
    df.get("target_notes_v5_2", "").astype(str)
    + " | TARGET_SCALE_REPAIRED offset="
    + str(round(scale_offset, 2))
)

for col in [
    "projected_rating_v5_2",
    "race_target_rating_v5_2",
    "race_target_rating_raw_v5_2",
    "projection_gap_v5_2",
]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

df.to_csv(SRC, index=False)

matched_after = df[
    df["history_match_status_v5_2"].astype(str).eq("MATCHED_HISTORY")
    & df["projected_rating_v5_2"].notna()
    & df["race_target_rating_v5_2"].notna()
].copy()

audit = pd.DataFrame([
    {"metric": "rows", "value": len(df)},
    {"metric": "matched_rows", "value": len(matched)},
    {"metric": "offset_mean", "value": round(offset_mean, 4)},
    {"metric": "offset_median_used", "value": round(scale_offset, 4)},
    {"metric": "avg_gap_before", "value": round(float(matched["projected_rating_v5_2"].mean() - matched["race_target_rating_v5_2"].mean()), 4)},
    {"metric": "avg_gap_after", "value": round(float(matched_after["projection_gap_v5_2"].mean()), 4)},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat(timespec="seconds")},
])

audit.to_csv(AUDIT, index=False)

print("WROTE:", SRC)
print("BACKUP:", BACKUP)
print("AUDIT:", AUDIT)
print(audit.to_string(index=False))
