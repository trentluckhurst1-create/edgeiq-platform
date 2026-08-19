import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v3_1.csv"
LADDER = DATA / "edgeiq_class_ladder_v1.csv"

OUT = DATA / "edgeiq_historical_performance_rating_v5.csv"
AUDIT = DATA / "edgeiq_historical_performance_rating_v5_audit.csv"

print("=" * 90)
print("EDGEIQ HISTORICAL PERFORMANCE RATING V5")
print("=" * 90)

df = pd.read_csv(SRC, low_memory=False)
ladder = pd.read_csv(LADDER, low_memory=False)

df["performance_rating_v3"] = pd.to_numeric(df["performance_rating_v3"], errors="coerce")
df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
df["real_field_size"] = pd.to_numeric(df["real_field_size"], errors="coerce")

ladder["class_ladder_score_v1"] = pd.to_numeric(ladder["class_ladder_score_v1"], errors="coerce")

ladder_keep = ladder[[
    "race_class",
    "class_ladder_score_v1",
    "class_ladder_norm_v1",
    "class_ladder_rank_v1",
    "class_ladder_reason_v1",
    "sample_confidence_v1",
]].copy()

ladder_keep = ladder_keep.rename(columns={
    "race_class": "race_class_clean_v3_1"
})

df = df.merge(
    ladder_keep,
    on="race_class_clean_v3_1",
    how="left"
)

df["class_ladder_score_v1"] = pd.to_numeric(df["class_ladder_score_v1"], errors="coerce")

# Anchor BM64 as the neutral class point.
neutral_class_score = 54.0

# Class quality adjustment.
# Scale: every 10 ladder points = 2.5 rating points.
df["class_quality_adjustment_v5"] = (
    (df["class_ladder_score_v1"] - neutral_class_score) / 10.0 * 2.5
)

df["class_quality_adjustment_v5"] = df["class_quality_adjustment_v5"].fillna(0)

# Apply class quality most strongly to better performances.
df["finish_quality_multiplier_v5"] = np.select(
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

# Field competitiveness.
# Larger fields get a small positive adjustment for top-end runs.
df["field_size_adjustment_v5"] = np.select(
    [
        df["real_field_size"] >= 16,
        df["real_field_size"].between(13, 15),
        df["real_field_size"].between(10, 12),
        df["real_field_size"].between(7, 9),
        df["real_field_size"].between(1, 6),
    ],
    [
        1.25,
        0.80,
        0.40,
        0.00,
        -0.50,
    ],
    default=0.00,
)

df["field_size_adjustment_v5"] = df["field_size_adjustment_v5"] * df["finish_quality_multiplier_v5"]

df["performance_rating_base_v5"] = df["performance_rating_v3"]

df["performance_rating_v5"] = (
    df["performance_rating_base_v5"] +
    (df["class_quality_adjustment_v5"] * df["finish_quality_multiplier_v5"]) +
    df["field_size_adjustment_v5"]
)

df["performance_rating_v5"] = df["performance_rating_v5"].clip(lower=0, upper=120).round(2)

df["rating_v5_status"] = np.select(
    [
        df["class_ladder_score_v1"].notna() & df["race_class_confidence_v3_1"].isin(["HIGH","MEDIUM"]),
        df["race_class_family_v3_1"].eq("UNRESOLVED"),
        df["race_class_family_v3_1"].eq("EXCLUDED_TRIAL_JUMPOUT"),
    ],
    [
        "CLASS_LADDER_ADJUSTED",
        "UNRESOLVED_CLASS_BASE_ONLY",
        "EXCLUDED_TRIAL_JUMPOUT_BASE_ONLY",
    ],
    default="BASE_ONLY",
)

df["built_at_v5"] = datetime.now().isoformat(timespec="seconds")
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
        "v5_winner_avg": round(float(winners["performance_rating_v5"].mean()), 2) if len(winners) else "",
        "v3_all_avg": round(float(g["performance_rating_v3"].mean()), 2) if len(g) else "",
        "v5_all_avg": round(float(g["performance_rating_v5"].mean()), 2) if len(g) else "",
        "ladder_score": round(float(g["class_ladder_score_v1"].dropna().iloc[0]), 2) if len(g) and g["class_ladder_score_v1"].notna().any() else "",
    })

audit = pd.DataFrame(rows)
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
