import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v5.csv"
OUT = DATA / "edgeiq_class_pars_v5.csv"
AUDIT = DATA / "edgeiq_class_pars_v5_audit.csv"

print("=" * 90)
print("EDGEIQ CLASS PARS V5")
print("=" * 90)

df = pd.read_csv(SRC, low_memory=False)

df["performance_rating_v5"] = pd.to_numeric(df["performance_rating_v5"], errors="coerce")
df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")

df = df[
    df["performance_rating_v5"].notna() &
    df["finish_position"].notna() &
    df["race_class_confidence_v3_1"].isin(["HIGH","MEDIUM"]) &
    ~df["race_class_family_v3_1"].isin(["UNRESOLVED","EXCLUDED_TRIAL_JUMPOUT"]) &
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

    winner_median = winners["performance_rating_v5"].median() if winner_count else np.nan
    top3_median = top3["performance_rating_v5"].median() if top3_count else np.nan
    all_median = g["performance_rating_v5"].median() if run_count else np.nan

    if winner_count >= 20 and top3_count >= 50:
        par = (0.60 * winner_median) + (0.40 * top3_median)
        method = "WINNER_TOP3_BLEND"
        confidence = "HIGH"
    elif top3_count >= 30:
        par = top3_median
        method = "TOP3_MEDIAN"
        confidence = "MEDIUM"
    elif run_count >= 50:
        par = all_median
        method = "ALL_MEDIAN_LOW_WIN_SAMPLE"
        confidence = "LOW"
    else:
        par = all_median
        method = "LOW_SAMPLE_RESEARCH_ONLY"
        confidence = "VERY_LOW"

    rows.append({
        "race_class_clean_v5": cls,
        "run_count": run_count,
        "winner_count": winner_count,
        "top3_count": top3_count,
        "winner_median_v5": round(float(winner_median), 2) if pd.notna(winner_median) else "",
        "top3_median_v5": round(float(top3_median), 2) if pd.notna(top3_median) else "",
        "all_runs_median_v5": round(float(all_median), 2) if pd.notna(all_median) else "",
        "class_par_rating_v5": round(float(par), 2) if pd.notna(par) else "",
        "class_par_method_v5": method,
        "class_par_confidence_v5": confidence,
        "built_at": datetime.now().isoformat(timespec="seconds"),
    })

out = pd.DataFrame(rows).sort_values("class_par_rating_v5", ascending=False)
out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rows_used", "value": len(df)},
    {"metric": "class_par_rows", "value": len(out)},
    {"metric": "high_confidence_pars", "value": int((out["class_par_confidence_v5"] == "HIGH").sum())},
    {"metric": "medium_confidence_pars", "value": int((out["class_par_confidence_v5"] == "MEDIUM").sum())},
    {"metric": "low_confidence_pars", "value": int((out["class_par_confidence_v5"] == "LOW").sum())},
    {"metric": "very_low_confidence_pars", "value": int((out["class_par_confidence_v5"] == "VERY_LOW").sum())},
])
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
