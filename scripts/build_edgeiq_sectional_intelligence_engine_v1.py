from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

IN_PATH = PUBLIC / "edgeiq_sectional_master_v1.csv"
OUT_PATH = PUBLIC / "edgeiq_sectional_intelligence_v1.csv"
DIAG_PATH = PUBLIC / "edgeiq_sectional_intelligence_diagnostics_v1.csv"

def norm_col(c):
    return re.sub(r"[^a-z0-9]", "", str(c).lower())

def find_col(df, candidates):
    cmap = {norm_col(c): c for c in df.columns}
    for cand in candidates:
        key = norm_col(cand)
        if key in cmap:
            return cmap[key]
    return None

def to_num(s):
    return pd.to_numeric(
        s.astype(str)
         .str.replace(",", "", regex=False)
         .str.replace("s", "", regex=False)
         .str.strip(),
        errors="coerce"
    )

def pct_rank_fast(series, ascending=True):
    return series.rank(pct=True, ascending=ascending) * 100

print("=" * 80)
print("EDGEIQ SECTIONAL INTELLIGENCE ENGINE V1")
print("=" * 80)

if not IN_PATH.exists():
    raise FileNotFoundError(f"Missing sectional master: {IN_PATH}")

df = pd.read_csv(IN_PATH, low_memory=False)

horse_col = find_col(df, ["horse", "runner", "horse_name"])
date_col = find_col(df, ["race_date", "date", "run_date"])
track_col = find_col(df, ["track", "venue"])
race_col = find_col(df, ["race_no", "race_number", "race"])
source_col = find_col(df, ["sectional_source", "source", "data_source"])
dist_col = find_col(df, ["distance", "race_distance"])

l200_col = find_col(df, ["last200", "last_200", "last 200", "last200m", "last_200m", "final200"])
l400_col = find_col(df, ["last400", "last_400", "last 400", "last400m", "last_400m", "final400"])
l600_col = find_col(df, ["last600", "last_600", "last 600", "last600m", "last_600m", "final600"])

required = {
    "horse": horse_col,
    "race_date": date_col,
    "track": track_col,
    "race_no": race_col,
    "last200": l200_col,
    "last400": l400_col,
    "last600": l600_col,
}

missing = [k for k, v in required.items() if v is None]
if missing:
    raise ValueError(f"Missing required columns: {missing}. Available columns: {list(df.columns)}")

work = df.copy()

work["horse"] = work[horse_col].astype(str).str.strip()
work["race_date"] = work[date_col].astype(str).str.strip()
work["track"] = work[track_col].astype(str).str.strip()
work["race_no"] = work[race_col].astype(str).str.extract(r"(\d+)").fillna("0").astype(int)

work["last200"] = to_num(work[l200_col])
work["last400"] = to_num(work[l400_col])
work["last600"] = to_num(work[l600_col])

work["sectional_source"] = work[source_col].astype(str).str.strip() if source_col else "UNKNOWN"
work["distance"] = to_num(work[dist_col]) if dist_col else np.nan

valid = work[
    work["horse"].ne("")
    & work["last200"].gt(0)
    & work["last400"].gt(0)
    & work["last600"].gt(0)
].copy()

valid = valid[
    (valid["last200"] < 30)
    & (valid["last400"] < 60)
    & (valid["last600"] < 90)
].copy()

race_keys = ["race_date", "track", "race_no"]

valid["final200_finish_rating"] = valid.groupby(race_keys)["last200"].transform(lambda s: pct_rank_fast(s, ascending=False))
valid["final400_rating"] = valid.groupby(race_keys)["last400"].transform(lambda s: pct_rank_fast(s, ascending=False))
valid["final600_rating"] = valid.groupby(race_keys)["last600"].transform(lambda s: pct_rank_fast(s, ascending=False))

valid["final400_acceleration_raw"] = valid["last400"] - (valid["last200"] * 2)
valid["final400_acceleration_rating"] = valid.groupby(race_keys)["final400_acceleration_raw"].transform(lambda s: pct_rank_fast(s, ascending=False))

valid["midrace_sustain_raw"] = valid["last600"] - valid["last400"]
valid["sustain_rating"] = valid.groupby(race_keys)["midrace_sustain_raw"].transform(lambda s: pct_rank_fast(s, ascending=False))

valid["energy_efficiency_raw"] = valid["last600"] / valid["last200"]
valid["energy_efficiency_rating"] = valid.groupby(race_keys)["energy_efficiency_raw"].transform(lambda s: pct_rank_fast(s, ascending=True))

valid["pace_resistance_rating"] = (
    valid["final600_rating"] * 0.35
    + valid["final400_rating"] * 0.30
    + valid["final200_finish_rating"] * 0.35
)

valid["run_efficiency_rating"] = (
    valid["energy_efficiency_rating"] * 0.45
    + valid["sustain_rating"] * 0.30
    + valid["final400_acceleration_rating"] * 0.25
)

valid["sectional_class_rating"] = (
    valid["final600_rating"] * 0.25
    + valid["final400_rating"] * 0.35
    + valid["final200_finish_rating"] * 0.40
)

valid["sectional_intelligence_score"] = (
    valid["sectional_class_rating"] * 0.35
    + valid["run_efficiency_rating"] * 0.25
    + valid["pace_resistance_rating"] * 0.25
    + valid["final400_acceleration_rating"] * 0.15
).round(2)

valid["sectional_confidence"] = np.where(
    valid.groupby(race_keys)["horse"].transform("count") >= 6,
    "HIGH",
    np.where(valid.groupby(race_keys)["horse"].transform("count") >= 4, "MEDIUM", "LOW")
)

def grade(x):
    if x >= 90: return "ELITE"
    if x >= 80: return "STRONG"
    if x >= 65: return "ABOVE_AVG"
    if x >= 45: return "NEUTRAL"
    return "WEAK"

valid["sectional_run_grade"] = valid["sectional_intelligence_score"].apply(grade)

def signals(r):
    out = []
    if r["final200_finish_rating"] >= 85: out.append("FAST_FINISH")
    if r["sustain_rating"] >= 80: out.append("STRONG_SUSTAIN")
    if r["pace_resistance_rating"] >= 80: out.append("PRESSURE_ABSORBER")
    if r["sectional_intelligence_score"] >= 82 and r["sectional_confidence"] != "LOW": out.append("HIDDEN_MERIT")
    if r["final200_finish_rating"] <= 20: out.append("SLOW_FINISH")
    return "|".join(out) if out else "UNKNOWN"

valid["sectional_signals"] = valid.apply(signals, axis=1)

cols = [
    "horse", "race_date", "track", "race_no", "distance", "sectional_source",
    "last200", "last400", "last600",
    "final200_finish_rating", "final400_acceleration_rating", "sustain_rating",
    "energy_efficiency_rating", "pace_resistance_rating", "run_efficiency_rating",
    "sectional_class_rating", "sectional_intelligence_score",
    "sectional_confidence", "sectional_run_grade", "sectional_signals"
]

out = valid[cols].copy()
out.to_csv(OUT_PATH, index=False)

diag = pd.DataFrame([{
    "rows_analysed": len(df),
    "valid_sectional_rows": len(valid),
    "unique_horses": valid["horse"].nunique(),
    "elite_runs": int((valid["sectional_run_grade"] == "ELITE").sum()),
    "strong_runs": int((valid["sectional_run_grade"] == "STRONG").sum()),
    "fast_finish_count": int(valid["sectional_signals"].str.contains("FAST_FINISH", na=False).sum()),
    "strong_sustain_count": int(valid["sectional_signals"].str.contains("STRONG_SUSTAIN", na=False).sum()),
    "hidden_merit_count": int(valid["sectional_signals"].str.contains("HIDDEN_MERIT", na=False).sum()),
    "input_file": str(IN_PATH),
    "output_file": str(OUT_PATH),
}])
diag.to_csv(DIAG_PATH, index=False)

print(diag.to_string(index=False))
print("SAVED:", OUT_PATH)
print("SAVED:", DIAG_PATH)
