from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

SECTIONAL = PUBLIC / "edgeiq_sectional_intelligence_v2.csv"
WAREHOUSE = PUBLIC / "edgeiq_vic_90day_sectional_warehouse_final_v1.csv"
EXECUTION_SECTIONALS = PUBLIC / "edgeiq_execution_board_live_sectionals_v1.csv"

OUT = PUBLIC / "edgeiq_sectional_feature_engine_v2.csv"
DIAG = PUBLIC / "edgeiq_sectional_feature_engine_v2_diagnostics.csv"

sectionals = pd.read_csv(SECTIONAL)
warehouse = pd.read_csv(WAREHOUSE)

def key(x):
    return re.sub(r"[^A-Z0-9]", "", str(x).upper())

warehouse["horse_key"] = warehouse["horse"].apply(key)

for c in [
    "early_speed_kmh",
    "mid_speed_kmh",
    "late_speed_kmh",
    "peak_speed_kmh",
    "avg_speed_kmh",
    "late_vs_mid_delta",
    "peak_vs_avg_delta",
]:
    warehouse[c] = pd.to_numeric(warehouse[c], errors="coerce")

features = warehouse.groupby(["horse_key", "horse"]).agg(
    runs=("horse_key", "size"),
    latest_run=("race_date", "max"),
    tracks_seen=("track", lambda x: ", ".join(sorted(set(map(str, x))))[:250]),

    early_mean=("early_speed_kmh", "mean"),
    mid_mean=("mid_speed_kmh", "mean"),
    late_mean=("late_speed_kmh", "mean"),
    peak_mean=("peak_speed_kmh", "mean"),
    avg_speed_mean=("avg_speed_kmh", "mean"),

    early_max=("early_speed_kmh", "max"),
    late_max=("late_speed_kmh", "max"),
    peak_max=("peak_speed_kmh", "max"),

    late_delta_mean=("late_vs_mid_delta", "mean"),
    late_delta_max=("late_vs_mid_delta", "max"),
    burst_delta_mean=("peak_vs_avg_delta", "mean"),
    burst_delta_max=("peak_vs_avg_delta", "max"),
).reset_index()

features["late_power_index"] = (
    features["late_mean"].rank(pct=True) * 55
    + features["late_delta_mean"].rank(pct=True) * 25
    + features["late_delta_max"].rank(pct=True) * 20
).round(2)

features["burst_index"] = (
    features["peak_mean"].rank(pct=True) * 45
    + features["burst_delta_mean"].rank(pct=True) * 35
    + features["peak_max"].rank(pct=True) * 20
).round(2)

features["sustain_index"] = (
    features["avg_speed_mean"].rank(pct=True) * 45
    + features["late_mean"].rank(pct=True) * 30
    + features["mid_mean"].rank(pct=True) * 25
).round(2)

features["fatigue_risk_index"] = (
    (1 - features["late_delta_mean"].rank(pct=True)) * 60
    + (1 - features["late_mean"].rank(pct=True)) * 40
).round(2)

def style(row):
    if row["runs"] < 2:
        return "LOW_SAMPLE"
    if row["late_power_index"] >= 85 and row["late_delta_mean"] > 1:
        return "STRONG_CLOSER"
    if row["sustain_index"] >= 85:
        return "HIGH_CRUISE_SUSTAIN"
    if row["burst_index"] >= 85:
        return "HIGH_PEAK_BURST"
    if row["fatigue_risk_index"] >= 80:
        return "FADES_LATE"
    return "BALANCED"

features["run_style_cluster"] = features.apply(style, axis=1)

features["sectional_weapon_score"] = (
    features["late_power_index"] * 0.35
    + features["burst_index"] * 0.25
    + features["sustain_index"] * 0.30
    + (100 - features["fatigue_risk_index"]) * 0.10
).round(2)

features = features.sort_values(
    ["sectional_weapon_score", "runs"],
    ascending=[False, False]
)

features.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "warehouse_rows": len(warehouse),
    "feature_rows": len(features),
    "unique_horses": features["horse_key"].nunique(),
    "strong_closers": int((features["run_style_cluster"] == "STRONG_CLOSER").sum()),
    "high_cruise_sustain": int((features["run_style_cluster"] == "HIGH_CRUISE_SUSTAIN").sum()),
    "high_peak_burst": int((features["run_style_cluster"] == "HIGH_PEAK_BURST").sum()),
    "fades_late": int((features["run_style_cluster"] == "FADES_LATE").sum()),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ SECTIONAL FEATURE ENGINE V2 BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print("=" * 100)
print(features.head(40).to_string(index=False))
print("=" * 100)
print("SAVED:", OUT)
print("SAVED:", DIAG)
