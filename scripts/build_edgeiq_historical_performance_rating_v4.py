import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v3_1.csv"
OUT = DATA / "edgeiq_historical_performance_rating_v4.csv"
AUDIT = DATA / "edgeiq_historical_performance_rating_v4_audit.csv"

print("=" * 90)
print("EDGEIQ HISTORICAL PERFORMANCE RATING V4")
print("=" * 90)

df = pd.read_csv(SRC, low_memory=False)

required = [
    "performance_rating_v3",
    "finish_position",
    "real_field_size",
    "race_class_clean_v3_1",
    "race_class_family_v3_1",
    "race_class_confidence_v3_1",
]

missing = [c for c in required if c not in df.columns]
if missing:
    print("AVAILABLE COLUMNS:")
    print(list(df.columns))
    raise ValueError(f"Missing required columns: {missing}")

df["performance_rating_v3"] = pd.to_numeric(df["performance_rating_v3"], errors="coerce")
df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
df["distance"] = pd.to_numeric(df["distance"], errors="coerce")
df["real_field_size"] = pd.to_numeric(df["real_field_size"], errors="coerce")

def class_bonus(row):
    cls = str(row.get("race_class_clean_v3_1", "")).upper().strip()
    fam = str(row.get("race_class_family_v3_1", "")).upper().strip()

    if cls == "GROUP 1":
        return 12.0, "GROUP_1_BONUS"
    if cls == "GROUP 2":
        return 10.0, "GROUP_2_BONUS"
    if cls == "GROUP 3":
        return 8.0, "GROUP_3_BONUS"
    if cls == "LISTED":
        return 6.0, "LISTED_BONUS"

    if cls in ["OPEN", "SET WEIGHTS", "SET WEIGHTS PENALTIES"]:
        return 5.0, "OPEN_SET_WEIGHTS_BONUS"

    m = re.match(r"BM([0-9]{2,3})$", cls)
    if m:
        n = int(m.group(1))
        if n >= 100:
            return 4.0, "BM100_PLUS_BONUS"
        if n >= 90:
            return 3.5, "BM90_PLUS_BONUS"
        if n >= 84:
            return 3.0, "BM84_PLUS_BONUS"
        if n >= 78:
            return 2.0, "BM78_PLUS_BONUS"
        if n >= 70:
            return 1.0, "BM70_PLUS_BONUS"
        if n >= 64:
            return 0.0, "BM64_BASE"
        if n >= 58:
            return -1.0, "BM58_MINUS"
        if n >= 50:
            return -2.0, "BM50_56_MINUS"
        return -3.0, "LOW_BM_MINUS"

    m = re.match(r"CLASS ([1-6])$", cls)
    if m:
        n = int(m.group(1))
        return {
            1: (-5.0, "CLASS_1_MINUS"),
            2: (-4.0, "CLASS_2_MINUS"),
            3: (-3.0, "CLASS_3_MINUS"),
            4: (-2.0, "CLASS_4_MINUS"),
            5: (-1.5, "CLASS_5_MINUS"),
            6: (-1.0, "CLASS_6_MINUS"),
        }.get(n, (-4.0, "CLASS_UNKNOWN_MINUS"))

    if cls == "MAIDEN":
        return -8.0, "MAIDEN_MINUS"

    if cls in ["COUNTRY", "PROVINCIAL", "MIDWAY", "HIGHWAY"]:
        return -1.5, "REGIONAL_RESTRICTED_MINUS"

    if cls == "JUMPS_RATING_BAND" or fam == "JUMPS_OR_HIGHWEIGHT":
        return 0.0, "JUMPS_HELD_NEUTRAL_RESEARCH"

    return 0.0, "NO_CLASS_BONUS"

bonus = df.apply(class_bonus, axis=1)
df["class_strength_bonus_v4"] = [x[0] for x in bonus]
df["class_strength_reason_v4"] = [x[1] for x in bonus]

df["finish_quality_multiplier_v4"] = np.select(
    [
        df["finish_position"].eq(1),
        df["finish_position"].eq(2),
        df["finish_position"].eq(3),
        df["finish_position"].between(4, 5),
        df["finish_position"].between(6, 8),
    ],
    [
        1.00,
        0.85,
        0.70,
        0.50,
        0.30,
    ],
    default=0.15,
)

df["performance_rating_base_v4"] = df["performance_rating_v3"]

df["performance_rating_v4"] = (
    df["performance_rating_base_v4"] +
    (df["class_strength_bonus_v4"] * df["finish_quality_multiplier_v4"])
)

df["performance_rating_v4"] = df["performance_rating_v4"].clip(lower=0, upper=120).round(2)

df["rating_v4_status"] = np.select(
    [
        df["race_class_confidence_v3_1"].isin(["HIGH", "MEDIUM"]),
        df["race_class_family_v3_1"].eq("UNRESOLVED"),
        df["race_class_family_v3_1"].eq("EXCLUDED_TRIAL_JUMPOUT"),
    ],
    [
        "CLASS_ADJUSTED",
        "UNRESOLVED_CLASS_BASE_ONLY",
        "EXCLUDED_TRIAL_JUMPOUT_BASE_ONLY",
    ],
    default="BASE_ONLY",
)

df["built_at_v4"] = datetime.now().isoformat(timespec="seconds")
df.to_csv(OUT, index=False)

key_classes = [
    "GROUP 1","GROUP 2","GROUP 3","LISTED",
    "BM84","BM78","BM70","BM64","BM58","BM56",
    "CLASS 1","CLASS 2","CLASS 3","MAIDEN"
]

rows = []
for cls in key_classes:
    g = df[df["race_class_clean_v3_1"].astype(str).str.upper().str.strip() == cls]
    winners = g[g["finish_position"] == 1]

    rows.append({
        "race_class": cls,
        "runs": len(g),
        "winners": len(winners),
        "v3_winner_avg": round(float(winners["performance_rating_v3"].mean()), 2) if len(winners) else "",
        "v4_winner_avg": round(float(winners["performance_rating_v4"].mean()), 2) if len(winners) else "",
        "v3_all_avg": round(float(g["performance_rating_v3"].mean()), 2) if len(g) else "",
        "v4_all_avg": round(float(g["performance_rating_v4"].mean()), 2) if len(g) else "",
    })

audit = pd.DataFrame(rows)
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
