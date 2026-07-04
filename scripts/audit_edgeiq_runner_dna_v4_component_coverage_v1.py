from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_runner_dna_current.csv"

OUT = DATA / "edgeiq_runner_dna_v4_component_coverage_audit.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v4_component_coverage_summary.csv"
MISSING = DATA / "edgeiq_runner_dna_v4_component_missing_by_runner.csv"

COMPONENTS = [
    "form_score",
    "rating_score",
    "distance_score",
    "track_score",
    "condition_score",
    "class_score",
    "barrier_score",
    "jockey_score",
    "trainer_score",
    "sectional_score",
    "run_style_score",
    "fitness_score",
    "profile_score",
]

df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

rows = []

for c in COMPONENTS:
    if c not in df.columns:
        rows.append({
            "component": c,
            "present_column": "NO",
            "covered_rows": 0,
            "missing_rows": len(df),
            "coverage_pct": 0,
        })
        continue

    s = df[c].astype(str).str.strip()
    covered = s.ne("") & s.ne("nan") & s.ne("NaN")
    rows.append({
        "component": c,
        "present_column": "YES",
        "covered_rows": int(covered.sum()),
        "missing_rows": int((~covered).sum()),
        "coverage_pct": round((covered.sum() / len(df)) * 100, 2) if len(df) else 0,
    })

coverage = pd.DataFrame(rows)
coverage.to_csv(OUT, index=False)

missing_rows = []

for _, r in df.iterrows():
    missing = []
    covered = []

    for c in COMPONENTS:
        val = str(r.get(c, "")).strip()
        if val == "" or val.lower() == "nan":
            missing.append(c.replace("_score", "").replace("_", " ").upper())
        else:
            covered.append(c.replace("_score", "").replace("_", " ").upper())

    missing_rows.append({
        "race_no": r.get("race_no", ""),
        "horse": r.get("horse", ""),
        "runner_dna_score": r.get("runner_dna_score", ""),
        "runner_dna_band": r.get("runner_dna_band", ""),
        "covered_component_count": len(covered),
        "missing_component_count": len(missing),
        "covered_components": " | ".join(covered),
        "missing_components": " | ".join(missing),
    })

missing = pd.DataFrame(missing_rows)
missing.to_csv(MISSING, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "RUNNER_DNA_V4_COMPONENT_COVERAGE_AUDIT_COMPLETE"},
    {"metric": "rows", "value": len(df)},
    {"metric": "components", "value": len(COMPONENTS)},
    {"metric": "avg_components_covered", "value": round(float(missing["covered_component_count"].mean()), 2)},
    {"metric": "min_components_covered", "value": int(missing["covered_component_count"].min())},
    {"metric": "max_components_covered", "value": int(missing["covered_component_count"].max())},
])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_V4_COMPONENT_COVERAGE_AUDIT] COMPLETE")
print(summary.to_string(index=False))
print(f"coverage={OUT}")
print(f"summary={SUMMARY}")
print(f"missing={MISSING}")
