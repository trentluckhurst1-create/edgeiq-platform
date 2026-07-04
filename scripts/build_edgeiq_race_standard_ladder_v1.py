import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v3.csv"
OUT = DATA / "edgeiq_race_standard_ladder_v1.csv"
AUDIT = DATA / "edgeiq_race_standard_ladder_v1_audit.csv"

print("=" * 90)
print("EDGEIQ RACE STANDARD LADDER V1")
print("=" * 90)

if not SRC.exists():
    raise FileNotFoundError(SRC)

df = pd.read_csv(SRC, low_memory=False)

required = [
    "race_class_clean",
    "distance",
    "condition_recovered",
    "finish_position",
    "performance_rating_v3",
    "recovery_confidence",
]

missing = [c for c in required if c not in df.columns]
if missing:
    print("AVAILABLE COLUMNS:")
    print(list(df.columns))
    raise ValueError(f"Missing required columns: {missing}")

df = df[df["recovery_confidence"].astype(str).str.upper().isin(["HIGH", "MEDIUM"])].copy()

df["performance_rating_v3"] = pd.to_numeric(df["performance_rating_v3"], errors="coerce")
df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
df["distance"] = pd.to_numeric(df["distance"], errors="coerce")

df = df[
    df["performance_rating_v3"].notna() &
    df["finish_position"].notna() &
    df["distance"].notna()
].copy()

def distance_band(d):
    if d < 1000:
        return "800-999"
    if d < 1200:
        return "1000-1199"
    if d < 1400:
        return "1200-1399"
    if d < 1600:
        return "1400-1599"
    if d < 1800:
        return "1600-1799"
    if d < 2000:
        return "1800-1999"
    if d < 2200:
        return "2000-2199"
    if d < 2400:
        return "2200-2399"
    if d < 2800:
        return "2400-2799"
    return "2800+"

def condition_group(x):
    t = str(x).upper().strip()
    if "FIRM" in t:
        return "FIRM"
    if "GOOD" in t:
        return "GOOD"
    if "SOFT" in t:
        return "SOFT"
    if "HEAVY" in t:
        return "HEAVY"
    if "SYN" in t:
        return "SYNTHETIC"
    return "UNKNOWN"

df["distance_band"] = df["distance"].apply(distance_band)
df["condition_group"] = df["condition_recovered"].apply(condition_group)
df["race_class_clean"] = df["race_class_clean"].astype(str).str.upper().str.strip()

def median_for_pos(g, pos):
    s = g.loc[g["finish_position"] == pos, "performance_rating_v3"]
    if len(s) == 0:
        return np.nan
    return round(float(s.median()), 2)

def avg_for_pos(g, pos):
    s = g.loc[g["finish_position"] == pos, "performance_rating_v3"]
    if len(s) == 0:
        return np.nan
    return round(float(s.mean()), 2)

def count_for_pos(g, pos):
    return int((g["finish_position"] == pos).sum())

def build_ladder(group_cols, level_name):
    rows = []
    for keys, g in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        row = {
            "ladder_level": level_name,
            "run_count": len(g),
            "winner_count": count_for_pos(g, 1),
            "top3_count": int((g["finish_position"] <= 3).sum()),
            "top5_count": int((g["finish_position"] <= 5).sum()),
            "all_run_median": round(float(g["performance_rating_v3"].median()), 2),
            "all_run_avg": round(float(g["performance_rating_v3"].mean()), 2),
            "winner_median": median_for_pos(g, 1),
            "second_median": median_for_pos(g, 2),
            "third_median": median_for_pos(g, 3),
            "fourth_median": median_for_pos(g, 4),
            "fifth_median": median_for_pos(g, 5),
            "winner_avg": avg_for_pos(g, 1),
            "second_avg": avg_for_pos(g, 2),
            "third_avg": avg_for_pos(g, 3),
            "fourth_avg": avg_for_pos(g, 4),
            "fifth_avg": avg_for_pos(g, 5),
        }

        for col, val in zip(group_cols, keys):
            row[col] = val

        if row["winner_count"] >= 20 and row["top3_count"] >= 50:
            row["confidence"] = "HIGH"
        elif row["winner_count"] >= 8 and row["top3_count"] >= 20:
            row["confidence"] = "MEDIUM"
        elif row["run_count"] >= 30:
            row["confidence"] = "LOW"
        else:
            row["confidence"] = "VERY_LOW"

        row["race_standard_median"] = row["third_median"]
        row["competitive_standard_median"] = row["fifth_median"]
        row["winning_standard_median"] = row["winner_median"]

        rows.append(row)

    return rows

rows = []
rows += build_ladder(["race_class_clean"], "CLASS")
rows += build_ladder(["distance_band"], "DISTANCE")
rows += build_ladder(["condition_group"], "CONDITION")
rows += build_ladder(["race_class_clean", "distance_band"], "CLASS_DISTANCE")
rows += build_ladder(["race_class_clean", "condition_group"], "CLASS_CONDITION")
rows += build_ladder(["race_class_clean", "distance_band", "condition_group"], "CLASS_DISTANCE_CONDITION")

out = pd.DataFrame(rows)

preferred_cols = [
    "ladder_level",
    "race_class_clean",
    "distance_band",
    "condition_group",
    "run_count",
    "winner_count",
    "top3_count",
    "top5_count",
    "all_run_median",
    "winner_median",
    "second_median",
    "third_median",
    "fourth_median",
    "fifth_median",
    "race_standard_median",
    "competitive_standard_median",
    "winning_standard_median",
    "confidence",
]

for c in preferred_cols:
    if c not in out.columns:
        out[c] = ""

out = out[preferred_cols + [c for c in out.columns if c not in preferred_cols]]
out["built_at"] = datetime.now().isoformat(timespec="seconds")

out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rows_loaded", "value": len(pd.read_csv(SRC, low_memory=False))},
    {"metric": "rows_used", "value": len(df)},
    {"metric": "ladder_rows_written", "value": len(out)},
    {"metric": "class_rows", "value": int((out["ladder_level"] == "CLASS").sum())},
    {"metric": "distance_rows", "value": int((out["ladder_level"] == "DISTANCE").sum())},
    {"metric": "condition_rows", "value": int((out["ladder_level"] == "CONDITION").sum())},
    {"metric": "class_distance_rows", "value": int((out["ladder_level"] == "CLASS_DISTANCE").sum())},
    {"metric": "class_condition_rows", "value": int((out["ladder_level"] == "CLASS_CONDITION").sum())},
    {"metric": "class_distance_condition_rows", "value": int((out["ladder_level"] == "CLASS_DISTANCE_CONDITION").sum())},
    {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
])

audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
