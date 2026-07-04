import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LADDER = DATA / "edgeiq_race_standard_ladder_v1.csv"
OUT = DATA / "edgeiq_race_targets_v4.csv"
AUDIT = DATA / "edgeiq_race_targets_v4_audit.csv"

print("=" * 90)
print("EDGEIQ RACE TARGETS V4")
print("=" * 90)

if not LADDER.exists():
    raise FileNotFoundError(LADDER)

df = pd.read_csv(LADDER, low_memory=False)

required = [
    "ladder_level",
    "race_class_clean",
    "distance_band",
    "condition_group",
    "run_count",
    "winner_count",
    "winner_median",
    "third_median",
    "fifth_median",
    "confidence",
]

missing = [c for c in required if c not in df.columns]
if missing:
    print("AVAILABLE COLUMNS:")
    print(list(df.columns))
    raise ValueError(f"Missing columns: {missing}")

for c in ["run_count", "winner_count", "winner_median", "third_median", "fifth_median"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# V4 meaning:
# competitive_target = typical 5th-place standard
# race_standard_target = typical 3rd-place standard
# winning_target = typical winner standard
df["competitive_target_v4"] = df["fifth_median"]
df["race_standard_target_v4"] = df["third_median"]
df["winning_target_v4"] = df["winner_median"]

# Prefer rows with enough actual depth.
df["target_quality_flag"] = np.select(
    [
        df["winning_target_v4"].notna() & df["race_standard_target_v4"].notna() & df["competitive_target_v4"].notna(),
        df["winning_target_v4"].notna() & df["race_standard_target_v4"].notna(),
        df["winning_target_v4"].notna(),
    ],
    [
        "FULL_LADDER",
        "WIN_RACE_STANDARD_ONLY",
        "WIN_ONLY",
    ],
    default="INSUFFICIENT_LADDER",
)

df["target_method_v4"] = np.select(
    [
        df["ladder_level"].eq("CLASS_DISTANCE_CONDITION"),
        df["ladder_level"].eq("CLASS_DISTANCE"),
        df["ladder_level"].eq("CLASS_CONDITION"),
        df["ladder_level"].eq("CLASS"),
        df["ladder_level"].eq("DISTANCE"),
        df["ladder_level"].eq("CONDITION"),
    ],
    [
        "CLASS_DISTANCE_CONDITION_LADDER",
        "CLASS_DISTANCE_LADDER",
        "CLASS_CONDITION_LADDER",
        "CLASS_LADDER",
        "DISTANCE_LADDER",
        "CONDITION_LADDER",
    ],
    default="UNKNOWN_LADDER",
)

out = df[[
    "ladder_level",
    "race_class_clean",
    "distance_band",
    "condition_group",
    "run_count",
    "winner_count",
    "all_run_median",
    "winner_median",
    "second_median",
    "third_median",
    "fourth_median",
    "fifth_median",
    "competitive_target_v4",
    "race_standard_target_v4",
    "winning_target_v4",
    "confidence",
    "target_quality_flag",
    "target_method_v4",
]].copy()

out["built_at"] = datetime.now().isoformat(timespec="seconds")
out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "ladder_rows_loaded", "value": len(df)},
    {"metric": "target_rows_written", "value": len(out)},
    {"metric": "full_ladder_rows", "value": int(out["target_quality_flag"].eq("FULL_LADDER").sum())},
    {"metric": "win_race_standard_only_rows", "value": int(out["target_quality_flag"].eq("WIN_RACE_STANDARD_ONLY").sum())},
    {"metric": "win_only_rows", "value": int(out["target_quality_flag"].eq("WIN_ONLY").sum())},
    {"metric": "insufficient_ladder_rows", "value": int(out["target_quality_flag"].eq("INSUFFICIENT_LADDER").sum())},
    {"metric": "high_confidence_rows", "value": int(out["confidence"].astype(str).str.upper().eq("HIGH").sum())},
    {"metric": "medium_confidence_rows", "value": int(out["confidence"].astype(str).str.upper().eq("MEDIUM").sum())},
    {"metric": "low_confidence_rows", "value": int(out["confidence"].astype(str).str.upper().eq("LOW").sum())},
    {"metric": "very_low_confidence_rows", "value": int(out["confidence"].astype(str).str.upper().eq("VERY_LOW").sum())},
    {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
])

audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
