from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

INPUT = PUBLIC / "edgeiq_vic_90day_sectional_warehouse_final_v1.csv"
OUT = PUBLIC / "edgeiq_sectional_master_v1.csv"
DIAG = PUBLIC / "edgeiq_sectional_master_diagnostics_v1.csv"

df = pd.read_csv(INPUT)

num_cols = [
    "distance_ran_m",
    "early_speed_kmh",
    "mid_speed_kmh",
    "late_speed_kmh",
    "peak_speed_kmh",
    "avg_speed_kmh",
    "late_vs_mid_delta",
    "peak_vs_avg_delta",
]

for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df["fast_finisher_flag"] = df["fast_finisher_flag"].astype(str).str.lower().eq("true")
df["sustained_speed_flag"] = df["sustained_speed_flag"].astype(str).str.lower().eq("true")

group = df.groupby(["horse_key", "horse"], dropna=False)

master = group.agg(
    sectional_runs=("horse_key", "size"),
    first_seen=("race_date", "min"),
    last_seen=("race_date", "max"),
    tracks_seen=("track", lambda x: ", ".join(sorted(set(map(str, x))))[:250]),
    avg_distance_m=("distance_ran_m", "mean"),
    avg_early_speed=("early_speed_kmh", "mean"),
    avg_mid_speed=("mid_speed_kmh", "mean"),
    avg_late_speed=("late_speed_kmh", "mean"),
    avg_peak_speed=("peak_speed_kmh", "mean"),
    avg_speed=("avg_speed_kmh", "mean"),
    best_late_speed=("late_speed_kmh", "max"),
    best_peak_speed=("peak_speed_kmh", "max"),
    avg_late_vs_mid_delta=("late_vs_mid_delta", "mean"),
    best_late_vs_mid_delta=("late_vs_mid_delta", "max"),
    avg_peak_vs_avg_delta=("peak_vs_avg_delta", "mean"),
    fast_finisher_rate=("fast_finisher_flag", "mean"),
    sustained_speed_rate=("sustained_speed_flag", "mean"),
).reset_index()

master["fast_finisher_rate"] = (master["fast_finisher_rate"] * 100).round(1)
master["sustained_speed_rate"] = (master["sustained_speed_rate"] * 100).round(1)

master["sectional_strength_score"] = (
    master["avg_late_speed"].rank(pct=True) * 35
    + master["avg_peak_speed"].rank(pct=True) * 25
    + master["avg_speed"].rank(pct=True) * 20
    + master["best_late_vs_mid_delta"].rank(pct=True) * 20
).round(2)

def classify(row):
    if row["sectional_runs"] < 2:
        return "LOW_SAMPLE"
    if row["fast_finisher_rate"] >= 60 and row["avg_late_vs_mid_delta"] > 0:
        return "LATE_CLOSER"
    if row["sustained_speed_rate"] >= 70 and row["avg_speed"] >= 60:
        return "SUSTAINED_SPEED"
    if row["avg_peak_vs_avg_delta"] >= 7:
        return "HIGH_PEAK_BURST"
    if row["avg_late_vs_mid_delta"] <= -4:
        return "FADES_LATE"
    return "BALANCED"

master["sectional_profile"] = master.apply(classify, axis=1)

master = master.sort_values(
    ["sectional_strength_score", "sectional_runs"],
    ascending=[False, False]
)

master.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "input_rows": len(df),
    "unique_horses": master["horse_key"].nunique(),
    "sectional_runs": int(master["sectional_runs"].sum()),
    "tracks": df["track"].nunique(),
    "races": df.groupby(["race_date", "track", "race_no"]).ngroups,
    "output_rows": len(master),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ SECTIONAL MASTER V1 BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(master.head(30).to_string(index=False))
print()
print("SAVED:", OUT)
print("SAVED:", DIAG)
