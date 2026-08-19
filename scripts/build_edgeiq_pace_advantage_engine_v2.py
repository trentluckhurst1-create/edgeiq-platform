import os
import re
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

V1_SRC = os.path.join(DATA, "edgeiq_pace_advantage_engine_v1.csv")
OUT = os.path.join(DATA, "edgeiq_pace_advantage_engine_v2.csv")
AUDIT = os.path.join(DATA, "edgeiq_pace_advantage_engine_v2_audit.csv")

print("=" * 100)
print("EDGEIQ PACE ADVANTAGE ENGINE V2 - PERCENTILE CALIBRATED")
print("=" * 100)
print(f"V1_SRC: {V1_SRC}")

if not os.path.exists(V1_SRC):
    raise FileNotFoundError(f"Missing V1 pace advantage file: {V1_SRC}")

df = pd.read_csv(V1_SRC, dtype=str).fillna("")

def num(x):
    s = str(x).strip().replace("$", "").replace(",", "")
    if s == "":
        return np.nan
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else np.nan

if "pace_advantage_score" not in df.columns:
    raise ValueError("V1 file missing pace_advantage_score.")

df["pace_advantage_raw_score"] = df["pace_advantage_score"].apply(num).astype(float)

if "projected_tempo_shape" not in df.columns:
    df["projected_tempo_shape"] = "UNKNOWN"

if "pace_pressure_confidence" not in df.columns:
    df["pace_pressure_confidence"] = "UNKNOWN"

valid_mask = (
    df["pace_advantage_raw_score"].notna() &
    (df["projected_tempo_shape"].astype(str).str.upper() != "UNKNOWN")
)

df["pace_advantage_percentile"] = np.nan

if valid_mask.any():
    df.loc[valid_mask, "pace_advantage_percentile"] = (
        df.loc[valid_mask, "pace_advantage_raw_score"].rank(pct=True) * 100
    ).round(2)

def calibrated_status(row):
    shape = str(row.get("projected_tempo_shape", "UNKNOWN")).upper().strip()
    p = row.get("pace_advantage_percentile", np.nan)

    if shape == "UNKNOWN" or pd.isna(p):
        return "UNKNOWN"

    p = float(p)

    if p >= 97:
        return "ELITE_ADVANTAGE"
    if p >= 90:
        return "STRONG_ADVANTAGE"
    if p >= 75:
        return "ADVANTAGE"
    if p <= 3:
        return "SEVERE_DISADVANTAGE"
    if p <= 10:
        return "STRONG_DISADVANTAGE"
    if p <= 25:
        return "DISADVANTAGE"
    return "NEUTRAL"

df["pace_advantage_status_v1_raw"] = df["pace_advantage_status"] if "pace_advantage_status" in df.columns else ""
df["pace_advantage_status"] = df.apply(calibrated_status, axis=1)

def signal_strength(row):
    status = str(row["pace_advantage_status"])
    conf = str(row.get("pace_pressure_confidence", "UNKNOWN")).upper()

    if status == "UNKNOWN":
        return "NO_SIGNAL"
    if conf in ["VERY_LOW", "UNKNOWN"]:
        return "LOW_CONFIDENCE_SIGNAL"
    if status in ["ELITE_ADVANTAGE", "SEVERE_DISADVANTAGE"]:
        return "HIGH_IMPACT"
    if status in ["STRONG_ADVANTAGE", "STRONG_DISADVANTAGE"]:
        return "MEDIUM_HIGH_IMPACT"
    if status in ["ADVANTAGE", "DISADVANTAGE"]:
        return "MEDIUM_IMPACT"
    return "LOW_IMPACT"

df["pace_advantage_signal_strength"] = df.apply(signal_strength, axis=1)

def calibrated_reason(row):
    old = str(row.get("pace_advantage_reason", "")).strip()
    p = row.get("pace_advantage_percentile", np.nan)
    status = row.get("pace_advantage_status", "UNKNOWN")

    if status == "UNKNOWN" or pd.isna(p):
        return old if old else "unknown tempo / insufficient pace confidence"

    prefix = f"calibrated P{float(p):.0f} race-shape fit"
    if old:
        return prefix + "; " + old
    return prefix

df["pace_advantage_reason"] = df.apply(calibrated_reason, axis=1)

preferred_cols = [
    "race_key",
    "meeting_date",
    "track",
    "race_no",
    "horse",
    "horse_key_join",
    "barrier_num",
    "projected_tempo_shape",
    "pace_pressure_percentile",
    "pace_pressure_confidence",
    "leader_pct",
    "on_pace_pct",
    "midfield_pct",
    "backmarker_pct",
    "leader_type_score",
    "closer_type_score",
    "tactical_balance",
    "early_trait",
    "late_trait",
    "pace_advantage_raw_score",
    "pace_advantage_percentile",
    "pace_advantage_status",
    "pace_advantage_signal_strength",
    "pace_advantage_status_v1_raw",
    "pace_advantage_reason",
]

extra_cols = [c for c in df.columns if c not in preferred_cols]
out = df[[c for c in preferred_cols if c in df.columns] + extra_cols]

audit = pd.DataFrame([{
    "runner_rows": len(out),
    "valid_calibration_rows": int(valid_mask.sum()),
    "unique_races": out["race_key"].nunique() if "race_key" in out.columns else 0,
    "elite_advantage": int((out["pace_advantage_status"] == "ELITE_ADVANTAGE").sum()),
    "strong_advantage": int((out["pace_advantage_status"] == "STRONG_ADVANTAGE").sum()),
    "advantage": int((out["pace_advantage_status"] == "ADVANTAGE").sum()),
    "neutral": int((out["pace_advantage_status"] == "NEUTRAL").sum()),
    "disadvantage": int((out["pace_advantage_status"] == "DISADVANTAGE").sum()),
    "strong_disadvantage": int((out["pace_advantage_status"] == "STRONG_DISADVANTAGE").sum()),
    "severe_disadvantage": int((out["pace_advantage_status"] == "SEVERE_DISADVANTAGE").sum()),
    "unknown": int((out["pace_advantage_status"] == "UNKNOWN").sum()),
}])

out.to_csv(OUT, index=False)
audit.to_csv(AUDIT, index=False)

print("")
print("DONE")
print(f"WROTE: {OUT}")
print(f"WROTE: {AUDIT}")
print("")
print(audit.to_string(index=False))
print("")
print("PACE ADVANTAGE V2 DISTRIBUTION")
print(out["pace_advantage_status"].value_counts(dropna=False).to_string())
print("")
print("TOP POSITIVE SIGNALS")
print(out.sort_values("pace_advantage_raw_score", ascending=False).head(40)[[
    "meeting_date",
    "track",
    "race_no",
    "horse",
    "projected_tempo_shape",
    "pace_pressure_percentile",
    "pace_advantage_raw_score",
    "pace_advantage_percentile",
    "pace_advantage_status",
    "pace_advantage_signal_strength",
    "pace_advantage_reason",
]].to_string(index=False))
print("")
print("TOP NEGATIVE SIGNALS")
print(out.sort_values("pace_advantage_raw_score", ascending=True).head(40)[[
    "meeting_date",
    "track",
    "race_no",
    "horse",
    "projected_tempo_shape",
    "pace_pressure_percentile",
    "pace_advantage_raw_score",
    "pace_advantage_percentile",
    "pace_advantage_status",
    "pace_advantage_signal_strength",
    "pace_advantage_reason",
]].to_string(index=False))
