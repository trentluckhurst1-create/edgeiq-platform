import pandas as pd
import numpy as np
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DNA = DATA / "edgeiq_runner_dna_current.csv"
DIST = DATA / "edgeiq_live_distance_dna_v1.csv"
COND = DATA / "edgeiq_live_condition_dna_v1.csv"
CLASS = DATA / "edgeiq_live_class_dna_v3.csv"

OUT = DATA / "edgeiq_runner_dna_v6_component_audit.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_component_audit_summary.csv"
OUT_JSON = DATA / "edgeiq_runner_dna_v6_component_audit_summary.json"

def canon_horse(x):
    if pd.isna(x):
        return ""
    s = str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def keyify(df):
    df = df.copy()
    if "horse" in df.columns:
        df["horse_canon_join"] = df["horse"].apply(canon_horse)
    if "race_no" in df.columns:
        df["race_no_join"] = pd.to_numeric(df["race_no"], errors="coerce").fillna(-1).astype(int).astype(str)
    if "track" in df.columns:
        df["track_join"] = df["track"].astype(str).str.upper().str.strip()
    return df

base = keyify(pd.read_csv(DNA, low_memory=False))
dist = keyify(pd.read_csv(DIST, low_memory=False))
cond = keyify(pd.read_csv(COND, low_memory=False))
cls = keyify(pd.read_csv(CLASS, low_memory=False))

join_cols = ["track_join", "race_no_join", "horse_canon_join"]

audit = base.copy()

audit = audit.merge(
    dist[join_cols + ["distance_fit_score","distance_fit_band","distance_starts"]],
    on=join_cols,
    how="left"
)

audit = audit.merge(
    cond[join_cols + ["condition_fit_score","condition_fit_band","condition_starts"]],
    on=join_cols,
    how="left"
)

audit = audit.merge(
    cls[join_cols + ["class_fit_score","class_fit_band","class_starts","class_profile_source","class_movement"]],
    on=join_cols,
    how="left"
)

for c in ["distance_fit_score","condition_fit_score","class_fit_score"]:
    audit[c] = pd.to_numeric(audit[c], errors="coerce")

audit["distance_v1_covered"] = audit["distance_fit_score"].notna() & audit["distance_fit_band"].ne("NO_PROFILE")
audit["condition_v1_covered"] = audit["condition_fit_score"].notna() & audit["condition_fit_band"].ne("NO_PROFILE")
audit["class_v3_covered"] = audit["class_fit_score"].notna() & audit["class_fit_band"].ne("NO_PROFILE")

audit_out = audit[[
    "track","race_no","horse",
    "distance_v1_covered","distance_fit_score","distance_fit_band","distance_starts",
    "condition_v1_covered","condition_fit_score","condition_fit_band","condition_starts",
    "class_v3_covered","class_fit_score","class_fit_band","class_starts","class_profile_source","class_movement"
]].copy()

audit_out.to_csv(OUT, index=False)

summary_rows = [
    {"metric": "status", "value": "RUNNER_DNA_V6_COMPONENT_AUDIT_COMPLETE"},
    {"metric": "runner_rows", "value": len(audit)},
    {"metric": "distance_covered", "value": int(audit["distance_v1_covered"].sum())},
    {"metric": "distance_coverage_pct", "value": round(float(audit["distance_v1_covered"].mean() * 100), 2)},
    {"metric": "condition_covered", "value": int(audit["condition_v1_covered"].sum())},
    {"metric": "condition_coverage_pct", "value": round(float(audit["condition_v1_covered"].mean() * 100), 2)},
    {"metric": "class_covered", "value": int(audit["class_v3_covered"].sum())},
    {"metric": "class_coverage_pct", "value": round(float(audit["class_v3_covered"].mean() * 100), 2)},
]
summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)
OUT_JSON.write_text(json.dumps({r["metric"]: r["value"] for r in summary_rows}, indent=2), encoding="utf-8")

print("[RUNNER_DNA_V6_COMPONENT_AUDIT] COMPLETE")
print(summary.to_string(index=False))
