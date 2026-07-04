import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v3_1.csv"
OUT = DATA / "edgeiq_class_strength_engine_v1.csv"
AUDIT = DATA / "edgeiq_class_strength_engine_v1_audit.csv"

print("=" * 90)
print("EDGEIQ CLASS STRENGTH ENGINE V1")
print("=" * 90)

df = pd.read_csv(SRC, low_memory=False)

df["performance_rating_v3"] = pd.to_numeric(df["performance_rating_v3"], errors="coerce")
df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
df["real_field_size"] = pd.to_numeric(df["real_field_size"], errors="coerce")

df = df[
    df["performance_rating_v3"].notna() &
    df["finish_position"].notna() &
    df["race_class_confidence_v3_1"].isin(["HIGH", "MEDIUM"]) &
    ~df["race_class_family_v3_1"].isin(["UNRESOLVED", "EXCLUDED_TRIAL_JUMPOUT"]) &
    df["race_class_clean_v3_1"].notna() &
    (df["race_class_clean_v3_1"].astype(str).str.strip() != "")
].copy()

def manual_order_score(cls):
    cls = str(cls).upper().strip()

    if cls == "GROUP 1":
        return 100
    if cls == "GROUP 2":
        return 94
    if cls == "GROUP 3":
        return 88
    if cls == "LISTED":
        return 82
    if cls in ["OPEN", "SET WEIGHTS", "SET WEIGHTS PENALTIES"]:
        return 76

    m = re.match(r"BM([0-9]{2,3})$", cls)
    if m:
        n = int(m.group(1))
        return max(20, min(78, n - 10))

    m = re.match(r"CLASS ([1-6])$", cls)
    if m:
        n = int(m.group(1))
        return 22 + (n * 6)

    if cls == "MAIDEN":
        return 12
    if cls in ["COUNTRY", "PROVINCIAL", "MIDWAY", "HIGHWAY"]:
        return 35
    if cls in ["JUMPS_RATING_BAND", "BM120"]:
        return 65

    return 30

rows = []

for cls, g in df.groupby("race_class_clean_v3_1", dropna=False):
    winners = g[g["finish_position"] == 1]
    top3 = g[g["finish_position"] <= 3]

    run_count = len(g)
    winner_count = len(winners)
    top3_count = len(top3)

    winner_avg = float(winners["performance_rating_v3"].mean()) if winner_count else np.nan
    winner_median = float(winners["performance_rating_v3"].median()) if winner_count else np.nan
    top3_avg = float(top3["performance_rating_v3"].mean()) if top3_count else np.nan
    top3_median = float(top3["performance_rating_v3"].median()) if top3_count else np.nan
    all_avg = float(g["performance_rating_v3"].mean()) if run_count else np.nan
    all_median = float(g["performance_rating_v3"].median()) if run_count else np.nan
    avg_field_size = float(g["real_field_size"].mean()) if g["real_field_size"].notna().any() else np.nan

    order_score = manual_order_score(cls)

    if run_count >= 200 and winner_count >= 20:
        confidence = "HIGH"
    elif run_count >= 80 and winner_count >= 8:
        confidence = "MEDIUM"
    elif run_count >= 30:
        confidence = "LOW"
    else:
        confidence = "VERY_LOW"

    rows.append({
        "race_class": cls,
        "run_count": run_count,
        "winner_count": winner_count,
        "top3_count": top3_count,
        "winner_avg_v3": round(winner_avg, 2) if pd.notna(winner_avg) else "",
        "winner_median_v3": round(winner_median, 2) if pd.notna(winner_median) else "",
        "top3_avg_v3": round(top3_avg, 2) if pd.notna(top3_avg) else "",
        "top3_median_v3": round(top3_median, 2) if pd.notna(top3_median) else "",
        "all_avg_v3": round(all_avg, 2) if pd.notna(all_avg) else "",
        "all_median_v3": round(all_median, 2) if pd.notna(all_median) else "",
        "avg_field_size": round(avg_field_size, 2) if pd.notna(avg_field_size) else "",
        "class_order_score_raw": order_score,
        "strength_confidence": confidence,
    })

out = pd.DataFrame(rows)

min_score = out["class_order_score_raw"].min()
max_score = out["class_order_score_raw"].max()

out["class_strength_score_v1"] = (
    (out["class_order_score_raw"] - min_score) / (max_score - min_score)
).round(4)

out = out.sort_values(
    ["class_strength_score_v1", "run_count"],
    ascending=[False, False]
).reset_index(drop=True)

out["class_strength_rank_v1"] = range(1, len(out) + 1)
out["built_at"] = datetime.now().isoformat(timespec="seconds")

out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rows_used", "value": len(df)},
    {"metric": "class_strength_rows", "value": len(out)},
    {"metric": "high_confidence_classes", "value": int((out["strength_confidence"] == "HIGH").sum())},
    {"metric": "medium_confidence_classes", "value": int((out["strength_confidence"] == "MEDIUM").sum())},
    {"metric": "low_confidence_classes", "value": int((out["strength_confidence"] == "LOW").sum())},
    {"metric": "very_low_confidence_classes", "value": int((out["strength_confidence"] == "VERY_LOW").sum())},
])
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
