import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

RATINGS = DATA / "edgeiq_historical_performance_rating_v5.csv"
CLASS_PARS = DATA / "edgeiq_class_pars_v5.csv"
DIST_PARS = DATA / "edgeiq_distance_pars_v5.csv"
COND_PARS = DATA / "edgeiq_condition_pars_v5.csv"

OUT = DATA / "edgeiq_race_rating_targets_v5.csv"
AUDIT = DATA / "edgeiq_race_rating_targets_v5_audit.csv"

print("=" * 90)
print("EDGEIQ RACE RATING TARGETS V5")
print("=" * 90)

ratings = pd.read_csv(RATINGS, low_memory=False)
class_pars = pd.read_csv(CLASS_PARS, low_memory=False)
dist_pars = pd.read_csv(DIST_PARS, low_memory=False)
cond_pars = pd.read_csv(COND_PARS, low_memory=False)

ratings["distance"] = pd.to_numeric(ratings["distance"], errors="coerce")
ratings["real_field_size"] = pd.to_numeric(ratings["real_field_size"], errors="coerce")

def distance_band(d):
    if pd.isna(d):
        return ""
    if d < 800:
        return "UNDER_800"
    if d <= 999:
        return "800-999"
    if d <= 1199:
        return "1000-1199"
    if d <= 1399:
        return "1200-1399"
    if d <= 1599:
        return "1400-1599"
    if d <= 1799:
        return "1600-1799"
    if d <= 1999:
        return "1800-1999"
    if d <= 2199:
        return "2000-2199"
    if d <= 2399:
        return "2200-2399"
    if d <= 2799:
        return "2400-2799"
    return "2800+"

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

ratings["distance_band_v5"] = ratings["distance"].apply(distance_band)
ratings["condition_group_v5"] = ratings.apply(clean_condition, axis=1)

class_keep = class_pars[[
    "race_class_clean_v5",
    "class_par_rating_v5",
    "class_par_confidence_v5",
]].rename(columns={
    "race_class_clean_v5": "race_class_clean_v3_1"
})

dist_keep = dist_pars[[
    "distance_band_v5",
    "distance_par_rating_v5",
    "distance_par_confidence_v5",
]]

cond_keep = cond_pars[[
    "condition_group_v5",
    "condition_par_rating_v5",
    "condition_par_confidence_v5",
]]

df = ratings.merge(class_keep, on="race_class_clean_v3_1", how="left")
df = df.merge(dist_keep, on="distance_band_v5", how="left")
df = df.merge(cond_keep, on="condition_group_v5", how="left")

for c in ["class_par_rating_v5","distance_par_rating_v5","condition_par_rating_v5"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Race-context grouping. Still best-effort because not all historical rows have a perfect race ID.
group_cols = [
    "race_date",
    "track",
    "distance",
    "race_class_clean_v3_1",
    "condition_group_v5",
    "real_field_size",
    "source_file",
]

race_rows = []

for keys, g in df.groupby(group_cols, dropna=False):
    race_date, track, distance, race_class, condition, field_size, source_file = keys

    class_par = g["class_par_rating_v5"].dropna().iloc[0] if g["class_par_rating_v5"].notna().any() else np.nan
    dist_par = g["distance_par_rating_v5"].dropna().iloc[0] if g["distance_par_rating_v5"].notna().any() else np.nan
    cond_par = g["condition_par_rating_v5"].dropna().iloc[0] if g["condition_par_rating_v5"].notna().any() else np.nan

    class_conf = g["class_par_confidence_v5"].dropna().iloc[0] if g["class_par_confidence_v5"].notna().any() else "MISSING"
    dist_conf = g["distance_par_confidence_v5"].dropna().iloc[0] if g["distance_par_confidence_v5"].notna().any() else "MISSING"
    cond_conf = g["condition_par_confidence_v5"].dropna().iloc[0] if g["condition_par_confidence_v5"].notna().any() else "MISSING"

    if pd.notna(class_par) and pd.notna(dist_par) and pd.notna(cond_par):
        target = (0.70 * class_par) + (0.15 * dist_par) + (0.15 * cond_par)
        status = "TARGET_BUILT"
    else:
        target = np.nan
        status = "NO_TARGET"

    conf_parts = [class_conf, dist_conf, cond_conf]

    if status == "NO_TARGET":
        target_conf = "NO_TARGET"
    elif "VERY_LOW" in conf_parts or "MISSING" in conf_parts:
        target_conf = "LOW"
    elif "LOW" in conf_parts:
        target_conf = "LOW"
    elif "MEDIUM" in conf_parts:
        target_conf = "MEDIUM"
    else:
        target_conf = "HIGH"

    race_rows.append({
        "race_date": race_date,
        "track": track,
        "distance": distance,
        "distance_band_v5": distance_band(distance),
        "race_class_clean_v5": race_class,
        "condition_group_v5": condition,
        "real_field_size": field_size,
        "source_file": source_file,
        "class_par_rating_v5": round(float(class_par), 2) if pd.notna(class_par) else "",
        "distance_par_rating_v5": round(float(dist_par), 2) if pd.notna(dist_par) else "",
        "condition_par_rating_v5": round(float(cond_par), 2) if pd.notna(cond_par) else "",
        "race_target_rating_v5": round(float(target), 2) if pd.notna(target) else "",
        "target_status_v5": status,
        "target_confidence_v5": target_conf,
        "class_par_confidence_v5": class_conf,
        "distance_par_confidence_v5": dist_conf,
        "condition_par_confidence_v5": cond_conf,
        "runner_rows_in_context": len(g),
        "built_at": datetime.now().isoformat(timespec="seconds"),
    })

out = pd.DataFrame(race_rows)
out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rating_rows_loaded", "value": len(ratings)},
    {"metric": "race_target_rows", "value": len(out)},
    {"metric": "target_built_rows", "value": int((out["target_status_v5"] == "TARGET_BUILT").sum())},
    {"metric": "no_target_rows", "value": int((out["target_status_v5"] == "NO_TARGET").sum())},
    {"metric": "high_confidence_targets", "value": int((out["target_confidence_v5"] == "HIGH").sum())},
    {"metric": "medium_confidence_targets", "value": int((out["target_confidence_v5"] == "MEDIUM").sum())},
    {"metric": "low_confidence_targets", "value": int((out["target_confidence_v5"] == "LOW").sum())},
])
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
