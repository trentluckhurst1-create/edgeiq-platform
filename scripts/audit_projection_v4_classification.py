import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJ = DATA / "edgeiq_runner_projection_v3.csv"
TARGETS = DATA / "edgeiq_race_targets_v4.csv"

OUT = DATA / "edgeiq_projection_v4_audit.csv"

proj = pd.read_csv(PROJ, low_memory=False)
targets = pd.read_csv(TARGETS, low_memory=False)

targets = targets[
    (targets["ladder_level"] == "CLASS")
].copy()

targets = targets[[
    "race_class_clean",
    "competitive_target_v4",
    "race_standard_target_v4",
    "winning_target_v4"
]]

proj["race_class_clean"] = (
    proj["race_class_clean"]
    .astype(str)
    .str.upper()
    .str.strip()
)

merged = proj.merge(
    targets,
    on="race_class_clean",
    how="left"
)

merged["projected_rating_v3"] = pd.to_numeric(
    merged["projected_rating_v3"],
    errors="coerce"
)

def classify(row):

    p = row["projected_rating_v3"]
    c = pd.to_numeric(row["competitive_target_v4"], errors="coerce")
    r = pd.to_numeric(row["race_standard_target_v4"], errors="coerce")
    w = pd.to_numeric(row["winning_target_v4"], errors="coerce")

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

merged["v4_classification"] = merged.apply(classify, axis=1)

merged.to_csv(OUT, index=False)

print("WROTE", OUT)
print(
    merged["v4_classification"]
    .value_counts(dropna=False)
)
