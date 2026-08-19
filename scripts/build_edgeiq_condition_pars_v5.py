import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v5.csv"
OUT = DATA / "edgeiq_condition_pars_v5.csv"
AUDIT = DATA / "edgeiq_condition_pars_v5_audit.csv"

print("=" * 90)
print("EDGEIQ CONDITION PARS V5")
print("=" * 90)

df = pd.read_csv(SRC, low_memory=False)

df["performance_rating_v5"] = pd.to_numeric(df["performance_rating_v5"], errors="coerce")
df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")

def clean_condition(row):
    cond = str(row.get("condition_recovered", "")).upper().strip()
    token = str(row.get("condition_token_recovered", "")).upper().strip()

    blob = f"{cond} {token}"

    if "FIRM" in blob:
        return "FIRM"
    if "GOOD" in blob:
        return "GOOD"
    if "SOFT" in blob:
        return "SOFT"
    if "HEAVY" in blob:
        return "HEAVY"
    if "SYNTH" in blob or "POLY" in blob:
        return "SYNTHETIC"
    return "UNKNOWN"

df["condition_group_v5"] = df.apply(clean_condition, axis=1)

df = df[
    df["performance_rating_v5"].notna() &
    df["finish_position"].notna() &
    df["race_class_confidence_v3_1"].isin(["HIGH","MEDIUM"]) &
    ~df["race_class_family_v3_1"].isin(["UNRESOLVED","EXCLUDED_TRIAL_JUMPOUT"])
].copy()

rows = []

for cond, g in df.groupby("condition_group_v5", dropna=False):
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
        "condition_group_v5": cond,
        "run_count": run_count,
        "winner_count": winner_count,
        "top3_count": top3_count,
        "winner_median_v5": round(float(winner_median), 2) if pd.notna(winner_median) else "",
        "top3_median_v5": round(float(top3_median), 2) if pd.notna(top3_median) else "",
        "all_runs_median_v5": round(float(all_median), 2) if pd.notna(all_median) else "",
        "condition_par_rating_v5": round(float(par), 2) if pd.notna(par) else "",
        "condition_par_method_v5": method,
        "condition_par_confidence_v5": confidence,
        "built_at": datetime.now().isoformat(timespec="seconds"),
    })

out = pd.DataFrame(rows)

order = {
    "FIRM": 1,
    "GOOD": 2,
    "SOFT": 3,
    "HEAVY": 4,
    "SYNTHETIC": 5,
    "UNKNOWN": 6,
}

out["sort_order"] = out["condition_group_v5"].map(order).fillna(99)
out = out.sort_values("sort_order").drop(columns=["sort_order"])
out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rows_used", "value": len(df)},
    {"metric": "condition_par_rows", "value": len(out)},
    {"metric": "high_confidence_pars", "value": int((out["condition_par_confidence_v5"] == "HIGH").sum())},
    {"metric": "medium_confidence_pars", "value": int((out["condition_par_confidence_v5"] == "MEDIUM").sum())},
    {"metric": "low_confidence_pars", "value": int((out["condition_par_confidence_v5"] == "LOW").sum())},
    {"metric": "very_low_confidence_pars", "value": int((out["condition_par_confidence_v5"] == "VERY_LOW").sum())},
])
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
