import re
import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v3_1.csv"

OUT = DATA / "edgeiq_class_ladder_v1.csv"
AUDIT = DATA / "edgeiq_class_ladder_v1_audit.csv"

print("=" * 90)
print("EDGEIQ CLASS LADDER V1")
print("=" * 90)

df = pd.read_csv(SRC, low_memory=False)

df = df[
    df["race_class_confidence_v3_1"].isin(["HIGH", "MEDIUM"]) &
    df["race_class_clean_v3_1"].notna() &
    (df["race_class_clean_v3_1"].astype(str).str.strip() != "") &
    ~df["race_class_family_v3_1"].isin(["UNRESOLVED", "EXCLUDED_TRIAL_JUMPOUT"])
].copy()

def class_ladder_score(cls):
    cls = str(cls).upper().strip()

    # Black type
    if cls == "GROUP 1":
        return 100, "BLACKTYPE_GROUP_1"
    if cls == "GROUP 2":
        return 95, "BLACKTYPE_GROUP_2"
    if cls == "GROUP 3":
        return 90, "BLACKTYPE_GROUP_3"
    if cls == "LISTED":
        return 85, "BLACKTYPE_LISTED"

    # Open / set weights
    if cls in ["OPEN", "SET WEIGHTS", "SET WEIGHTS PENALTIES"]:
        return 80, "OPEN_SET_WEIGHTS"

    # Benchmark ladder
    m = re.match(r"BM([0-9]{2,3})$", cls)
    if m:
        n = int(m.group(1))

        if n >= 120:
            return 77, "JUMPS_HIGHWEIGHT_BM120_REVIEW"
        if n >= 100:
            return 76, "BM100_PLUS"
        if n >= 90:
            return 73, "BM90_PLUS"
        if n >= 84:
            return 70, "BM84"
        if n >= 78:
            return 66, "BM78"
        if n >= 74:
            return 63, "BM74"
        if n >= 72:
            return 61, "BM72"
        if n >= 70:
            return 60, "BM70"
        if n >= 68:
            return 58, "BM68"
        if n >= 66:
            return 56, "BM66"
        if n >= 64:
            return 54, "BM64"
        if n >= 62:
            return 52, "BM62"
        if n >= 60:
            return 50, "BM60"
        if n >= 58:
            return 48, "BM58"
        if n >= 56:
            return 46, "BM56"
        if n >= 54:
            return 44, "BM54"
        if n >= 52:
            return 42, "BM52"
        if n >= 50:
            return 40, "BM50"

        return 35, "LOW_BM_REVIEW"

    # Class ladder
    m = re.match(r"CLASS ([1-6])$", cls)
    if m:
        n = int(m.group(1))
        return {
            6: (44, "CLASS_6"),
            5: (42, "CLASS_5"),
            4: (40, "CLASS_4"),
            3: (37, "CLASS_3"),
            2: (34, "CLASS_2"),
            1: (30, "CLASS_1"),
        }.get(n, (34, "CLASS_UNKNOWN_REVIEW"))

    # Other useful classifications
    if cls == "MAIDEN":
        return 20, "MAIDEN"

    if cls == "HIGHWAY":
        return 45, "HIGHWAY_RESTRICTED"
    if cls == "MIDWAY":
        return 43, "MIDWAY_RESTRICTED"
    if cls == "PROVINCIAL":
        return 42, "PROVINCIAL_RESTRICTED"
    if cls == "COUNTRY":
        return 40, "COUNTRY_RESTRICTED"

    if cls == "JUMPS_RATING_BAND":
        return 65, "JUMPS_RATING_BAND_REVIEW"
    if cls in ["HURDLE", "STEEPLECHASE"]:
        return 65, "JUMPS_REVIEW"

    return 30, "UNKNOWN_LADDER_REVIEW"

rows = []

for cls, g in df.groupby("race_class_clean_v3_1", dropna=False):
    score, reason = class_ladder_score(cls)

    winner_count = int((pd.to_numeric(g["finish_position"], errors="coerce") == 1).sum())
    run_count = len(g)

    if run_count >= 200 and winner_count >= 20:
        sample_confidence = "HIGH"
    elif run_count >= 80 and winner_count >= 8:
        sample_confidence = "MEDIUM"
    elif run_count >= 30:
        sample_confidence = "LOW"
    else:
        sample_confidence = "VERY_LOW"

    rows.append({
        "race_class": cls,
        "class_ladder_score_v1": score,
        "class_ladder_reason_v1": reason,
        "run_count": run_count,
        "winner_count": winner_count,
        "sample_confidence_v1": sample_confidence,
    })

out = pd.DataFrame(rows)

min_score = out["class_ladder_score_v1"].min()
max_score = out["class_ladder_score_v1"].max()

out["class_ladder_norm_v1"] = (
    (out["class_ladder_score_v1"] - min_score) / (max_score - min_score)
).round(4)

out = out.sort_values(
    ["class_ladder_score_v1", "run_count"],
    ascending=[False, False]
).reset_index(drop=True)

out["class_ladder_rank_v1"] = range(1, len(out) + 1)
out["built_at"] = datetime.now().isoformat(timespec="seconds")

out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "source_rows_used", "value": len(df)},
    {"metric": "class_ladder_rows", "value": len(out)},
    {"metric": "high_sample_classes", "value": int((out["sample_confidence_v1"] == "HIGH").sum())},
    {"metric": "medium_sample_classes", "value": int((out["sample_confidence_v1"] == "MEDIUM").sum())},
    {"metric": "low_sample_classes", "value": int((out["sample_confidence_v1"] == "LOW").sum())},
    {"metric": "very_low_sample_classes", "value": int((out["sample_confidence_v1"] == "VERY_LOW").sum())},
])
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
