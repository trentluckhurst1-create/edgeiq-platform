from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()

PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

SECTIONAL = PUBLIC / "edgeiq_sectional_intelligence_v2.csv"
EXECUTION = PUBLIC / "edgeiq_execution_board_live.csv"

OUT = PUBLIC / "edgeiq_execution_board_live_sectionals_v1.csv"
DIAG = PUBLIC / "edgeiq_execution_board_live_sectionals_diagnostics_v1.csv"

sectionals = pd.read_csv(SECTIONAL)

execution = pd.read_csv(EXECUTION)

def horse_key(x):
    import re
    return re.sub(r'[^A-Z0-9]', '', str(x).upper())

possible_cols = [
    "horse",
    "runner_name",
    "selection",
    "runner",
]

horse_col = None

for c in possible_cols:
    if c in execution.columns:
        horse_col = c
        break

if horse_col is None:
    raise Exception(f"NO HORSE COLUMN FOUND: {execution.columns.tolist()}")

execution["horse_key"] = execution[horse_col].apply(horse_key)

merge_cols = [
    "horse_key",
    "sectional_strength_score",
    "sectional_profile",
    "tempo_suitability",
    "sectional_edge_tier",
    "hidden_run_flag",
    "late_closer_flag",
    "sustained_runner_flag",
    "hidden_run_score",
    "preferred_distance_bucket",
    "preferred_track",
]

merged = execution.merge(
    sectionals[merge_cols],
    on="horse_key",
    how="left"
)

merged["sectional_strength_score"] = pd.to_numeric(
    merged["sectional_strength_score"],
    errors="coerce"
).fillna(0)

merged["hidden_run_score"] = pd.to_numeric(
    merged["hidden_run_score"],
    errors="coerce"
).fillna(0)

merged["sectional_profile"] = merged["sectional_profile"].fillna("UNKNOWN")
merged["tempo_suitability"] = merged["tempo_suitability"].fillna("UNKNOWN")
merged["sectional_edge_tier"] = merged["sectional_edge_tier"].fillna("NONE")

merged["late_closer_flag"] = (
    pd.to_numeric(
        merged["late_closer_flag"],
        errors="coerce"
    ).fillna(0).astype(int)
)

merged["sustained_runner_flag"] = (
    pd.to_numeric(
        merged["sustained_runner_flag"],
        errors="coerce"
    ).fillna(0).astype(int)
)

merged["hidden_run_flag"] = (
    pd.to_numeric(
        merged["hidden_run_flag"],
        errors="coerce"
    ).fillna(0).astype(int)
)

merged["sectional_overlay_signal"] = np.select(
    [
        (
            merged["sectional_edge_tier"].eq("ELITE")
            &
            merged["late_closer_flag"].eq(1)
        ),

        (
            merged["sectional_edge_tier"].eq("ELITE")
            &
            merged["sustained_runner_flag"].eq(1)
        ),

        (
            merged["sectional_edge_tier"].eq("STRONG")
        ),
    ],
    [
        "LATE_SECTIONAL_EDGE",
        "PRESSURE_SECTIONAL_EDGE",
        "SECTIONAL_POSITIVE",
    ],
    default="NEUTRAL"
)

merged["sectional_confidence"] = np.select(
    [
        merged["sectional_strength_score"] >= 90,
        merged["sectional_strength_score"] >= 80,
        merged["sectional_strength_score"] >= 70,
    ],
    [
        "ELITE",
        "STRONG",
        "SOLID",
    ],
    default="NONE"
)

sort_cols = []

for c in [
    "edge_pct",
    "overlay_pct",
    "ev",
    "confidence_score",
]:
    if c in merged.columns:
        sort_cols.append(c)

sort_cols.append("sectional_strength_score")

merged = merged.sort_values(
    sort_cols,
    ascending=False
)

merged.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "execution_rows": len(execution),
    "matched_sectionals": int(
        merged["sectional_strength_score"].gt(0).sum()
    ),
    "elite_sectional_runners": int(
        merged["sectional_edge_tier"].eq("ELITE").sum()
    ),
    "late_closers": int(
        merged["late_closer_flag"].sum()
    ),
    "sustained_runners": int(
        merged["sustained_runner_flag"].sum()
    ),
    "hidden_runs": int(
        merged["hidden_run_flag"].sum()
    ),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ EXECUTION BOARD SECTIONAL LAYER V1")
print("=" * 100)

print(diag.to_string(index=False))

print("=" * 100)

preview_cols = [
    horse_col,
    "sectional_profile",
    "sectional_edge_tier",
    "sectional_strength_score",
    "tempo_suitability",
    "sectional_overlay_signal",
    "sectional_confidence",
]

preview_cols = [c for c in preview_cols if c in merged.columns]

print(
    merged[preview_cols]
    .head(50)
    .to_string(index=False)
)

print("=" * 100)
print("SAVED:", OUT)
print("SAVED:", DIAG)
