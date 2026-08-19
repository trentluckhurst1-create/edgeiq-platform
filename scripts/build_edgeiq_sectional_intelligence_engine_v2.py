from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()

PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

MASTER_PATH = PUBLIC / "edgeiq_sectional_master_v1.csv"
WAREHOUSE_PATH = PUBLIC / "edgeiq_vic_90day_sectional_warehouse_final_v1.csv"

OUT = PUBLIC / "edgeiq_sectional_intelligence_v2.csv"
DIAG = PUBLIC / "edgeiq_sectional_intelligence_v2_diagnostics.csv"

master = pd.read_csv(MASTER_PATH)
warehouse = pd.read_csv(WAREHOUSE_PATH)

num_cols = [
    "early_speed_kmh",
    "mid_speed_kmh",
    "late_speed_kmh",
    "peak_speed_kmh",
    "avg_speed_kmh",
    "late_vs_mid_delta",
    "peak_vs_avg_delta",
]

for c in num_cols:
    warehouse[c] = pd.to_numeric(warehouse[c], errors="coerce")

track_baselines = (
    warehouse.groupby("track")
    .agg(
        track_avg_late=("late_speed_kmh", "mean"),
        track_avg_peak=("peak_speed_kmh", "mean"),
        track_avg_speed=("avg_speed_kmh", "mean"),
        track_avg_delta=("late_vs_mid_delta", "mean"),
    )
    .reset_index()
)

distance_buckets = []

for _, row in warehouse.iterrows():

    d = row.get("distance_ran_m", np.nan)

    if pd.isna(d):
        bucket = "UNKNOWN"
    elif d < 1100:
        bucket = "SPRINT"
    elif d < 1400:
        bucket = "MILE"
    elif d < 1800:
        bucket = "MIDDLE"
    else:
        bucket = "STAYING"

    distance_buckets.append(bucket)

warehouse["distance_bucket"] = distance_buckets

distance_baselines = (
    warehouse.groupby("distance_bucket")
    .agg(
        bucket_avg_late=("late_speed_kmh", "mean"),
        bucket_avg_peak=("peak_speed_kmh", "mean"),
        bucket_avg_speed=("avg_speed_kmh", "mean"),
    )
    .reset_index()
)

intel = master.copy()

intel = intel.merge(
    warehouse.groupby("horse_key").agg(
        preferred_distance_bucket=("distance_bucket", lambda x: x.mode().iloc[0] if len(x.mode()) else "UNKNOWN"),
        preferred_track=("track", lambda x: x.mode().iloc[0] if len(x.mode()) else ""),
        best_track_late_speed=("late_speed_kmh", "max"),
        best_track_peak_speed=("peak_speed_kmh", "max"),
    ).reset_index(),
    on="horse_key",
    how="left"
)

intel["hidden_run_score"] = (
    (
        intel["avg_late_speed"].rank(pct=True) * 40
        +
        intel["best_late_speed"].rank(pct=True) * 30
        +
        intel["avg_peak_speed"].rank(pct=True) * 20
        +
        intel["avg_late_vs_mid_delta"].rank(pct=True) * 10
    ) * 100
).round(2)

intel["tempo_suitability"] = np.where(
    intel["sectional_profile"].eq("LATE_CLOSER"),
    "FAST_TEMPO",
    np.where(
        intel["sectional_profile"].eq("SUSTAINED_SPEED"),
        "HIGH_PRESSURE",
        np.where(
            intel["sectional_profile"].eq("HIGH_PEAK_BURST"),
            "SHORT_SPRINT",
            "NEUTRAL"
        )
    )
)

intel["sectional_edge_tier"] = np.select(
    [
        intel["sectional_strength_score"] >= 90,
        intel["sectional_strength_score"] >= 80,
        intel["sectional_strength_score"] >= 70,
    ],
    [
        "ELITE",
        "STRONG",
        "SOLID",
    ],
    default="NEUTRAL"
)

intel["hidden_run_flag"] = (
    (intel["avg_late_vs_mid_delta"] > 2)
    &
    (intel["avg_peak_vs_avg_delta"] > 7)
).astype(int)

intel["late_closer_flag"] = (
    intel["sectional_profile"]
    .eq("LATE_CLOSER")
).astype(int)

intel["sustained_runner_flag"] = (
    intel["sectional_profile"]
    .eq("SUSTAINED_SPEED")
).astype(int)

intel = intel.sort_values(
    [
        "sectional_strength_score",
        "hidden_run_score",
        "sectional_runs",
    ],
    ascending=[False, False, False]
)

intel.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "master_rows": len(master),
    "warehouse_rows": len(warehouse),
    "tracks": warehouse["track"].nunique(),
    "distance_buckets": warehouse["distance_bucket"].nunique(),
    "elite_horses": int((intel["sectional_edge_tier"] == "ELITE").sum()),
    "hidden_run_flags": int(intel["hidden_run_flag"].sum()),
    "late_closers": int(intel["late_closer_flag"].sum()),
    "sustained_runners": int(intel["sustained_runner_flag"].sum()),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ SECTIONAL INTELLIGENCE ENGINE V2")
print("=" * 100)
print(diag.to_string(index=False))
print("=" * 100)

print(
    intel[
        [
            "horse",
            "sectional_profile",
            "sectional_edge_tier",
            "sectional_strength_score",
            "hidden_run_score",
            "tempo_suitability",
            "preferred_distance_bucket",
            "preferred_track",
        ]
    ]
    .head(40)
    .to_string(index=False)
)

print("=" * 100)
print("SAVED:", OUT)
print("SAVED:", DIAG)
