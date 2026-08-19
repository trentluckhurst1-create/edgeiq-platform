import pandas as pd
import numpy as np
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_runner_dna_v6_1_rebalance.csv"

OUT = DATA / "edgeiq_runner_dna_v6_1_component_distribution_audit.csv"
COUNTS = DATA / "edgeiq_runner_dna_v6_1_component_value_counts.csv"
TOPS = DATA / "edgeiq_runner_dna_v6_1_component_top20.csv"
SUMMARY_JSON = DATA / "edgeiq_runner_dna_v6_1_component_distribution_audit.json"

COMPONENTS = [
    "form_score",
    "rating_score",
    "profile_score",
    "pace_score",
    "sectional_score",
    "distance_fit_score",
    "condition_fit_score",
    "class_fit_score",
    "fitness_score",
    "late_power_score",
    "track_score",
    "barrier_score",
]

df = pd.read_csv(SRC, low_memory=False)

rows = []
count_rows = []
top_rows = []

for c in COMPONENTS:
    if c not in df.columns:
        rows.append({
            "component": c,
            "exists": "NO",
            "count": 0,
            "missing": "",
            "mean": "",
            "median": "",
            "std": "",
            "min": "",
            "max": "",
            "unique_values": "",
            "constant_risk": "NO_COLUMN",
        })
        continue

    s = pd.to_numeric(df[c], errors="coerce")
    nonnull = s.dropna()

    if len(nonnull) == 0:
        rows.append({
            "component": c,
            "exists": "YES",
            "count": 0,
            "missing": len(df),
            "mean": "",
            "median": "",
            "std": "",
            "min": "",
            "max": "",
            "unique_values": 0,
            "constant_risk": "ALL_MISSING",
        })
        continue

    rounded = nonnull.round(1)
    vc = rounded.value_counts(dropna=False).reset_index()
    vc.columns = ["score", "count"]

    top_value_share = float(vc["count"].max()) / float(len(nonnull)) if len(nonnull) else 0
    std = float(nonnull.std()) if len(nonnull) > 1 else 0

    if top_value_share >= 0.65:
        risk = "HIGH_CONSTANT_RISK"
    elif top_value_share >= 0.45:
        risk = "MEDIUM_CONSTANT_RISK"
    elif std <= 6:
        risk = "LOW_SPREAD_RISK"
    else:
        risk = "OK"

    rows.append({
        "component": c,
        "exists": "YES",
        "count": int(nonnull.count()),
        "missing": int(s.isna().sum()),
        "mean": round(float(nonnull.mean()), 2),
        "median": round(float(nonnull.median()), 2),
        "std": round(float(nonnull.std()), 2) if len(nonnull) > 1 else 0,
        "min": round(float(nonnull.min()), 2),
        "max": round(float(nonnull.max()), 2),
        "unique_values": int(rounded.nunique()),
        "top_value_share_pct": round(top_value_share * 100, 2),
        "constant_risk": risk,
    })

    for _, r in vc.head(25).iterrows():
        count_rows.append({
            "component": c,
            "score": r["score"],
            "count": int(r["count"]),
        })

    t = df.copy()
    t[c + "_num"] = s
    t = t.sort_values(c + "_num", ascending=False).head(20)

    for _, r in t.iterrows():
        top_rows.append({
            "component": c,
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "horse": r.get("horse", ""),
            "score": r.get(c + "_num", ""),
            "overall": r.get("runner_dna_v6_1_score", ""),
            "overall_band": r.get("runner_dna_v6_1_band", ""),
        })

audit = pd.DataFrame(rows)
counts = pd.DataFrame(count_rows)
tops = pd.DataFrame(top_rows)

audit.to_csv(OUT, index=False)
counts.to_csv(COUNTS, index=False)
tops.to_csv(TOPS, index=False)

summary = {
    "status": "RUNNER_DNA_V6_1_COMPONENT_DISTRIBUTION_AUDIT_COMPLETE",
    "rows": len(df),
    "components_checked": len(COMPONENTS),
    "high_constant_risk": audit[audit["constant_risk"].eq("HIGH_CONSTANT_RISK")]["component"].tolist(),
    "medium_constant_risk": audit[audit["constant_risk"].eq("MEDIUM_CONSTANT_RISK")]["component"].tolist(),
    "low_spread_risk": audit[audit["constant_risk"].eq("LOW_SPREAD_RISK")]["component"].tolist(),
}

SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("[RUNNER_DNA_V6_1_COMPONENT_DISTRIBUTION_AUDIT] COMPLETE")
print(audit.to_string(index=False))
print()
print(json.dumps(summary, indent=2))
