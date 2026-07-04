import os
import re
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

SECTIONAL_SRC = os.path.join(DATA, "racingcom_sectional_warehouse_v2.csv")
PROFILE_SRC = os.path.join(DATA, "edgeiq_sectional_profiles_v2.csv")
RACE_STRENGTH_SRC = os.path.join(DATA, "edgeiq_race_strength_v1.csv")

OUT = os.path.join(DATA, "edgeiq_sectional_strength_engine_v1.csv")
RUN_OUT = os.path.join(DATA, "edgeiq_sectional_strength_runs_v1.csv")
AUDIT = os.path.join(DATA, "edgeiq_sectional_strength_engine_v1_audit.csv")

print("=" * 100)
print("EDGEIQ SECTIONAL STRENGTH ENGINE V1")
print("=" * 100)
print(f"SECTIONAL_SRC:     {SECTIONAL_SRC}")
print(f"PROFILE_SRC:       {PROFILE_SRC}")
print(f"RACE_STRENGTH_SRC: {RACE_STRENGTH_SRC}")

for p in [SECTIONAL_SRC, PROFILE_SRC, RACE_STRENGTH_SRC]:
    if not os.path.exists(p):
        raise FileNotFoundError(f"Missing required input: {p}")

def clean_key(x):
    x = str(x).upper().strip()
    x = re.sub(r"\([^)]*\)", "", x)
    x = x.replace("'", "")
    x = x.replace("’", "")
    x = re.sub(r"[^A-Z0-9]+", "", x)
    return x

def clean_track(x):
    x = str(x).upper().strip()
    x = x.replace("THE VALLEY", "MOONEE VALLEY")
    x = re.sub(r"\s+", " ", x)
    return x

def num(x):
    s = str(x).strip().replace("$", "").replace(",", "")
    if s == "":
        return np.nan
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else np.nan

def find_col(cols, options):
    lower = {c.lower(): c for c in cols}
    for opt in options:
        if opt.lower() in lower:
            return lower[opt.lower()]
    return None

sec = pd.read_csv(SECTIONAL_SRC, dtype=str).fillna("")
profiles = pd.read_csv(PROFILE_SRC, dtype=str).fillna("")
strength = pd.read_csv(RACE_STRENGTH_SRC, dtype=str).fillna("")

sec_horse_col = find_col(sec.columns, ["horse_key", "horseKey", "horse", "horseName"])
sec_date_col = find_col(sec.columns, ["meeting_date", "race_date", "date"])
sec_track_col = find_col(sec.columns, ["track", "venue", "meeting_name"])
sec_race_col = find_col(sec.columns, ["race_no", "raceNo", "race_number"])
sec_peak_col = find_col(sec.columns, ["peak_speed", "avg_peak_speed", "top_speed"])
sec_late_col = find_col(sec.columns, ["late_speed", "avg_late_speed"])
sec_speed_col = find_col(sec.columns, ["speed", "avg_speed", "overall_speed"])

missing = []
if sec_horse_col is None: missing.append("sectional horse/horse_key")
if sec_date_col is None: missing.append("sectional meeting_date")
if sec_track_col is None: missing.append("sectional track")
if sec_race_col is None: missing.append("sectional race_no")
if missing:
    raise ValueError(f"Sectional warehouse missing required columns: {missing}")

sec["horse_key"] = sec[sec_horse_col].apply(clean_key)
sec["meeting_date"] = pd.to_datetime(sec[sec_date_col], errors="coerce").dt.strftime("%Y-%m-%d")
sec["track_clean"] = sec[sec_track_col].apply(clean_track)
sec["race_no_num"] = sec[sec_race_col].apply(num)

sec["peak_speed_raw"] = sec[sec_peak_col].apply(num) if sec_peak_col else np.nan
sec["late_speed_raw"] = sec[sec_late_col].apply(num) if sec_late_col else np.nan
sec["sustained_speed_raw"] = sec[sec_speed_col].apply(num) if sec_speed_col else np.nan

sec = sec[
    (sec["horse_key"] != "") &
    (sec["meeting_date"].notna()) &
    (sec["track_clean"] != "") &
    (sec["race_no_num"].notna())
].copy()

sec["race_key"] = (
    sec["meeting_date"] + "|" +
    sec["track_clean"] + "|R" +
    sec["race_no_num"].astype(int).astype(str)
)

strength["race_key_clean"] = strength["race_key"].astype(str).str.upper().str.strip() if "race_key" in strength.columns else ""

if "field_strength_score" not in strength.columns:
    raise ValueError("Race strength file missing field_strength_score.")

strength["field_strength_score"] = strength["field_strength_score"].apply(num)
strength["field_strength_percentile"] = strength["field_strength_percentile"].apply(num) if "field_strength_percentile" in strength.columns else np.nan

strength_keep = [
    "race_key_clean",
    "field_strength_score",
    "field_strength_percentile",
]

if "race_strength_band" in strength.columns:
    strength_keep.append("race_strength_band")

strength = strength[strength_keep].drop_duplicates("race_key_clean")

sec["race_key_clean"] = sec["race_key"].astype(str).str.upper().str.strip()

runs = sec.merge(strength, on="race_key_clean", how="left")

matched = runs["field_strength_score"].notna()
population_strength_mean = runs.loc[matched, "field_strength_score"].mean()

if pd.isna(population_strength_mean):
    raise RuntimeError("No sectional runs matched race strength. Check race_key join.")

runs["strength_adjustment_factor"] = np.where(
    runs["field_strength_score"].notna(),
    1.0 + ((runs["field_strength_score"] - population_strength_mean) / 100.0),
    1.0
)

runs["strength_adjustment_factor"] = runs["strength_adjustment_factor"].clip(0.80, 1.25)

runs["strength_adjusted_peak_speed_run"] = runs["peak_speed_raw"] * runs["strength_adjustment_factor"]
runs["strength_adjusted_late_speed_run"] = runs["late_speed_raw"] * runs["strength_adjustment_factor"]
runs["strength_adjusted_sustained_speed_run"] = runs["sustained_speed_raw"] * runs["strength_adjustment_factor"]

profile_key_col = find_col(profiles.columns, ["horse_key", "horseKey"])
if profile_key_col is None:
    raise ValueError("Sectional profiles missing horse_key.")

profiles["horse_key"] = profiles[profile_key_col].apply(clean_key)

for c in ["runs_with_sectionals", "avg_peak_speed", "avg_late_speed", "avg_speed"]:
    if c in profiles.columns:
        profiles[c] = profiles[c].apply(num)

agg = runs.groupby("horse_key", as_index=False).agg(
    runs_with_strength=("field_strength_score", lambda s: int(s.notna().sum())),
    sectional_runs_seen=("race_key", "count"),
    avg_race_strength=("field_strength_score", "mean"),
    avg_race_strength_percentile=("field_strength_percentile", "mean"),
    strength_adjusted_peak_speed=("strength_adjusted_peak_speed_run", "mean"),
    strength_adjusted_late_speed=("strength_adjusted_late_speed_run", "mean"),
    strength_adjusted_sustained_speed=("strength_adjusted_sustained_speed_run", "mean"),
)

out = profiles.merge(agg, on="horse_key", how="left")

for c in [
    "runs_with_strength",
    "sectional_runs_seen",
    "avg_race_strength",
    "avg_race_strength_percentile",
    "strength_adjusted_peak_speed",
    "strength_adjusted_late_speed",
    "strength_adjusted_sustained_speed",
]:
    if c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")

out["runs_with_strength"] = out["runs_with_strength"].fillna(0).astype(int)
out["sectional_runs_seen"] = out["sectional_runs_seen"].fillna(0).astype(int)

# Fallback to raw profile numbers when no race-strength join exists.
if "avg_peak_speed" in out.columns:
    out["strength_adjusted_peak_speed"] = out["strength_adjusted_peak_speed"].fillna(out["avg_peak_speed"])
if "avg_late_speed" in out.columns:
    out["strength_adjusted_late_speed"] = out["strength_adjusted_late_speed"].fillna(out["avg_late_speed"])
if "avg_speed" in out.columns:
    out["strength_adjusted_sustained_speed"] = out["strength_adjusted_sustained_speed"].fillna(out["avg_speed"])

out["avg_race_strength"] = out["avg_race_strength"].fillna(population_strength_mean)
out["avg_race_strength_percentile"] = out["avg_race_strength_percentile"].fillna(50)

out["sectional_strength_score"] = (
    out["strength_adjusted_peak_speed"].fillna(0) * 0.40 +
    out["strength_adjusted_late_speed"].fillna(0) * 0.35 +
    out["strength_adjusted_sustained_speed"].fillna(0) * 0.25
).round(3)

valid_score = out["sectional_strength_score"].notna() & (out["sectional_strength_score"] > 0)
out["sectional_strength_percentile"] = np.nan

if valid_score.any():
    out.loc[valid_score, "sectional_strength_percentile"] = (
        out.loc[valid_score, "sectional_strength_score"].rank(pct=True) * 100
    ).round(2)

def band(row):
    p = row["sectional_strength_percentile"]
    runs = row["runs_with_strength"]
    if pd.isna(p):
        return "UNKNOWN"
    if runs < 2:
        return "LOW_EVIDENCE"
    if p >= 97:
        return "ELITE"
    if p >= 90:
        return "VERY_STRONG"
    if p >= 75:
        return "STRONG"
    if p >= 45:
        return "SOLID"
    if p >= 25:
        return "WEAK"
    return "VERY_WEAK"

out["sectional_strength_band"] = out.apply(band, axis=1)

def confidence(row):
    runs = int(row["runs_with_strength"])
    if runs >= 8:
        return "HIGH"
    if runs >= 4:
        return "MEDIUM"
    if runs >= 2:
        return "LOW"
    if runs == 1:
        return "VERY_LOW"
    return "NO_STRENGTH_MATCH"

out["sectional_strength_confidence"] = out.apply(confidence, axis=1)

preferred = [
    "horse_key",
    "runs_with_sectionals",
    "runs_with_strength",
    "sectional_runs_seen",
    "avg_race_strength",
    "avg_race_strength_percentile",
    "avg_peak_speed",
    "avg_late_speed",
    "avg_speed",
    "strength_adjusted_peak_speed",
    "strength_adjusted_late_speed",
    "strength_adjusted_sustained_speed",
    "sectional_strength_score",
    "sectional_strength_percentile",
    "sectional_strength_band",
    "sectional_strength_confidence",
    "sectional_archetype",
    "profile_depth_status",
]

extra = [c for c in out.columns if c not in preferred]
out = out[[c for c in preferred if c in out.columns] + extra]

run_cols = [
    "race_key",
    "meeting_date",
    "track_clean",
    "race_no_num",
    "horse_key",
    "peak_speed_raw",
    "late_speed_raw",
    "sustained_speed_raw",
    "field_strength_score",
    "field_strength_percentile",
    "strength_adjustment_factor",
    "strength_adjusted_peak_speed_run",
    "strength_adjusted_late_speed_run",
    "strength_adjusted_sustained_speed_run",
]

runs[run_cols].to_csv(RUN_OUT, index=False)
out.to_csv(OUT, index=False)

audit = pd.DataFrame([{
    "sectional_rows": len(sec),
    "sectional_runs_output": len(runs),
    "sectional_runs_matched_strength": int(matched.sum()),
    "sectional_strength_match_rate_pct": round(float(matched.mean() * 100), 2),
    "profiles_output": len(out),
    "horses_with_strength_runs": int((out["runs_with_strength"] > 0).sum()),
    "population_strength_mean": round(float(population_strength_mean), 3),
    "elite": int((out["sectional_strength_band"] == "ELITE").sum()),
    "very_strong": int((out["sectional_strength_band"] == "VERY_STRONG").sum()),
    "strong": int((out["sectional_strength_band"] == "STRONG").sum()),
    "solid": int((out["sectional_strength_band"] == "SOLID").sum()),
    "weak": int((out["sectional_strength_band"] == "WEAK").sum()),
    "very_weak": int((out["sectional_strength_band"] == "VERY_WEAK").sum()),
    "low_evidence": int((out["sectional_strength_band"] == "LOW_EVIDENCE").sum()),
    "unknown": int((out["sectional_strength_band"] == "UNKNOWN").sum()),
}])

audit.to_csv(AUDIT, index=False)

print("")
print("DONE")
print(f"WROTE: {OUT}")
print(f"WROTE: {RUN_OUT}")
print(f"WROTE: {AUDIT}")
print("")
print(audit.to_string(index=False))
print("")
print("SECTIONAL STRENGTH DISTRIBUTION")
print(out["sectional_strength_band"].value_counts(dropna=False).to_string())
print("")
print("TOP SECTIONAL STRENGTH HORSES")
print(out.sort_values("sectional_strength_score", ascending=False).head(40)[[
    "horse_key",
    "runs_with_sectionals",
    "runs_with_strength",
    "avg_race_strength",
    "strength_adjusted_peak_speed",
    "strength_adjusted_late_speed",
    "strength_adjusted_sustained_speed",
    "sectional_strength_score",
    "sectional_strength_percentile",
    "sectional_strength_band",
    "sectional_strength_confidence",
]].to_string(index=False))
