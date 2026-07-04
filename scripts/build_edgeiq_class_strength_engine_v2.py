import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v3_1.csv"

OUT = DATA / "edgeiq_class_strength_engine_v2.csv"
AUDIT = DATA / "edgeiq_class_strength_engine_v2_audit.csv"

print("=" * 90)
print("EDGEIQ CLASS STRENGTH ENGINE V2 — DATA DRIVEN")
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

    if run_count >= 200 and winner_count >= 20 and top3_count >= 50:
        confidence = "HIGH"
    elif run_count >= 80 and winner_count >= 8 and top3_count >= 25:
        confidence = "MEDIUM"
    elif run_count >= 30 and top3_count >= 10:
        confidence = "LOW"
    else:
        confidence = "VERY_LOW"

    # Data-only score. No manual class ladder.
    # Winner and top-3 carry most of the signal; all-run average helps race depth.
    if pd.notna(winner_avg) and pd.notna(top3_avg) and pd.notna(all_avg):
        raw_score = (0.40 * winner_avg) + (0.40 * top3_avg) + (0.20 * all_avg)
        method = "WINNER_TOP3_FIELD_BLEND"
    elif pd.notna(top3_avg) and pd.notna(all_avg):
        raw_score = (0.70 * top3_avg) + (0.30 * all_avg)
        method = "TOP3_FIELD_BLEND"
    elif pd.notna(all_avg):
        raw_score = all_avg
        method = "FIELD_AVG_ONLY"
    else:
        raw_score = np.nan
        method = "NO_SCORE"

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
        "raw_strength_score_v2": round(raw_score, 4) if pd.notna(raw_score) else "",
        "strength_method_v2": method,
        "strength_confidence_v2": confidence,
    })

out = pd.DataFrame(rows)

score_num = pd.to_numeric(out["raw_strength_score_v2"], errors="coerce")
valid = score_num.notna()

min_score = score_num[valid].min()
max_score = score_num[valid].max()

out["class_strength_score_v2"] = np.where(
    valid & (max_score > min_score),
    ((score_num - min_score) / (max_score - min_score)).round(4),
    np.nan
)

out = out.sort_values(
    ["class_strength_score_v2", "run_count"],
    ascending=[False, False]
).reset_index(drop=True)

out["class_strength_rank_v2"] = range(1, len(out) + 1)
out["built_at"] = datetime.now().isoformat(timespec="seconds")

out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rows_used", "value": len(df)},
    {"metric": "class_strength_rows", "value": len(out)},
    {"metric": "high_confidence_classes", "value": int((out["strength_confidence_v2"] == "HIGH").sum())},
    {"metric": "medium_confidence_classes", "value": int((out["strength_confidence_v2"] == "MEDIUM").sum())},
    {"metric": "low_confidence_classes", "value": int((out["strength_confidence_v2"] == "LOW").sum())},
    {"metric": "very_low_confidence_classes", "value": int((out["strength_confidence_v2"] == "VERY_LOW").sum())},
    {"metric": "min_raw_strength_score", "value": round(float(min_score), 4) if pd.notna(min_score) else ""},
    {"metric": "max_raw_strength_score", "value": round(float(max_score), 4) if pd.notna(max_score) else ""},
])
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
