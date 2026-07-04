from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path.cwd()
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

FEATURES = PUBLIC / "edgeiq_sectional_feature_engine_v2.csv"
EXECUTION = PUBLIC / "edgeiq_execution_board_live_sectionals_v1.csv"

OUT = PUBLIC / "edgeiq_sectional_tempo_engine_v1.csv"
DIAG = PUBLIC / "edgeiq_sectional_tempo_engine_v1_diagnostics.csv"

features = pd.read_csv(FEATURES)
execution = pd.read_csv(EXECUTION)

def key(x):
    return re.sub(r"[^A-Z0-9]", "", str(x).upper())

horse_col = None
for c in ["horse", "runner_name", "selection", "runner"]:
    if c in execution.columns:
        horse_col = c
        break

if horse_col is None:
    raise Exception("NO HORSE COLUMN FOUND")

execution["horse_key"] = execution[horse_col].apply(key)

merge_cols = [
    "horse_key",
    "horse",
    "runs",
    "late_power_index",
    "burst_index",
    "sustain_index",
    "fatigue_risk_index",
    "run_style_cluster",
    "sectional_weapon_score",
]

tempo = execution.merge(
    features[merge_cols],
    on="horse_key",
    how="left",
    suffixes=("", "_sectional")
)

for c in [
    "runs",
    "late_power_index",
    "burst_index",
    "sustain_index",
    "fatigue_risk_index",
    "sectional_weapon_score",
]:
    tempo[c] = pd.to_numeric(tempo[c], errors="coerce").fillna(0)

tempo["run_style_cluster"] = tempo["run_style_cluster"].fillna("UNKNOWN")

tempo["tempo_role"] = np.select(
    [
        tempo["run_style_cluster"].eq("STRONG_CLOSER"),
        tempo["run_style_cluster"].eq("HIGH_CRUISE_SUSTAIN"),
        tempo["run_style_cluster"].eq("HIGH_PEAK_BURST"),
        tempo["run_style_cluster"].eq("FADES_LATE"),
        tempo["run_style_cluster"].eq("LOW_SAMPLE"),
    ],
    [
        "CLOSER",
        "PRESSURE_SUSTAIN",
        "BURST_RUNNER",
        "FADE_RISK",
        "LOW_SAMPLE",
    ],
    default="UNKNOWN"
)

race_keys = []

for _, r in tempo.iterrows():
    race_date = str(r.get("race_date", ""))
    track = str(r.get("track", ""))
    race_no = str(r.get("race_no", r.get("race_number", "")))
    race_keys.append(f"{race_date}|{track}|R{race_no}")

tempo["tempo_race_key"] = race_keys

race_summary = tempo.groupby("tempo_race_key").agg(
    runners=("horse_key", "count"),
    matched_sectional_runners=("sectional_weapon_score", lambda x: int((x > 0).sum())),
    closers=("tempo_role", lambda x: int((x == "CLOSER").sum())),
    pressure_sustain=("tempo_role", lambda x: int((x == "PRESSURE_SUSTAIN").sum())),
    burst_runners=("tempo_role", lambda x: int((x == "BURST_RUNNER").sum())),
    fade_risks=("tempo_role", lambda x: int((x == "FADE_RISK").sum())),
    avg_weapon_score=("sectional_weapon_score", "mean"),
    max_weapon_score=("sectional_weapon_score", "max"),
    avg_late_power=("late_power_index", "mean"),
    avg_sustain=("sustain_index", "mean"),
    avg_fatigue_risk=("fatigue_risk_index", "mean"),
).reset_index()

def pressure_label(row):
    if row["matched_sectional_runners"] < 2:
        return "LOW_SECTIONAL_COVERAGE"
    if row["pressure_sustain"] >= 3:
        return "HIGH_PRESSURE"
    if row["pressure_sustain"] >= 2 and row["closers"] >= 2:
        return "PRESSURE_WITH_CLOSERS"
    if row["closers"] >= 3:
        return "CLOSER_HEAVY"
    if row["fade_risks"] >= 2:
        return "COLLAPSE_RISK"
    return "NEUTRAL_TEMPO"

race_summary["projected_tempo_shape"] = race_summary.apply(pressure_label, axis=1)

race_summary["pace_collapse_risk"] = np.select(
    [
        race_summary["projected_tempo_shape"].eq("HIGH_PRESSURE"),
        race_summary["projected_tempo_shape"].eq("PRESSURE_WITH_CLOSERS"),
        race_summary["projected_tempo_shape"].eq("COLLAPSE_RISK"),
    ],
    [
        "HIGH",
        "MEDIUM_HIGH",
        "MEDIUM",
    ],
    default="LOW"
)

tempo = tempo.merge(
    race_summary[
        [
            "tempo_race_key",
            "projected_tempo_shape",
            "pace_collapse_risk",
            "matched_sectional_runners",
            "closers",
            "pressure_sustain",
            "burst_runners",
            "fade_risks",
        ]
    ],
    on="tempo_race_key",
    how="left"
)

tempo["tempo_fit"] = np.select(
    [
        tempo["tempo_role"].eq("CLOSER") & tempo["pace_collapse_risk"].isin(["HIGH", "MEDIUM_HIGH"]),
        tempo["tempo_role"].eq("PRESSURE_SUSTAIN") & tempo["projected_tempo_shape"].isin(["HIGH_PRESSURE", "PRESSURE_WITH_CLOSERS"]),
        tempo["tempo_role"].eq("BURST_RUNNER") & tempo["projected_tempo_shape"].eq("NEUTRAL_TEMPO"),
        tempo["tempo_role"].eq("FADE_RISK") & tempo["pace_collapse_risk"].isin(["HIGH", "MEDIUM_HIGH"]),
    ],
    [
        "POSITIVE_CLOSER_SETUP",
        "POSITIVE_PRESSURE_SETUP",
        "POSITIVE_BURST_SETUP",
        "NEGATIVE_FADE_SETUP",
    ],
    default="NEUTRAL"
)

tempo["tempo_edge_score"] = (
    tempo["sectional_weapon_score"] * 0.45
    + tempo["late_power_index"] * 0.25
    + tempo["sustain_index"] * 0.20
    + (100 - tempo["fatigue_risk_index"]) * 0.10
).round(2)

tempo["tempo_edge_grade"] = np.select(
    [
        tempo["tempo_edge_score"] >= 90,
        tempo["tempo_edge_score"] >= 80,
        tempo["tempo_edge_score"] >= 70,
        tempo["tempo_edge_score"] >= 60,
    ],
    [
        "ELITE",
        "STRONG",
        "SOLID",
        "WATCH",
    ],
    default="NONE"
)

tempo = tempo.sort_values(
    ["tempo_edge_score", "sectional_weapon_score"],
    ascending=[False, False]
)

tempo.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "execution_rows": len(execution),
    "matched_sectional_runners": int((tempo["sectional_weapon_score"] > 0).sum()),
    "races": tempo["tempo_race_key"].nunique(),
    "positive_closer_setups": int((tempo["tempo_fit"] == "POSITIVE_CLOSER_SETUP").sum()),
    "positive_pressure_setups": int((tempo["tempo_fit"] == "POSITIVE_PRESSURE_SETUP").sum()),
    "negative_fade_setups": int((tempo["tempo_fit"] == "NEGATIVE_FADE_SETUP").sum()),
    "elite_tempo_edges": int((tempo["tempo_edge_grade"] == "ELITE").sum()),
    "strong_tempo_edges": int((tempo["tempo_edge_grade"] == "STRONG").sum()),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ SECTIONAL TEMPO ENGINE V1 BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print("=" * 100)

preview_cols = [
    horse_col,
    "run_style_cluster",
    "tempo_role",
    "projected_tempo_shape",
    "pace_collapse_risk",
    "tempo_fit",
    "sectional_weapon_score",
    "tempo_edge_score",
    "tempo_edge_grade",
]

preview_cols = [c for c in preview_cols if c in tempo.columns]

print(tempo[preview_cols].head(50).to_string(index=False))
print("=" * 100)
print("SAVED:", OUT)
print("SAVED:", DIAG)
