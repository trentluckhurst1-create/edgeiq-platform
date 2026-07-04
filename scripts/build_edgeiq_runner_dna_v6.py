import pandas as pd
import numpy as np
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASE_DNA = DATA / "edgeiq_runner_dna_current.csv"
DIST = DATA / "edgeiq_live_distance_dna_v1.csv"
COND = DATA / "edgeiq_live_condition_dna_v1.csv"
CLASS = DATA / "edgeiq_live_class_dna_v3.csv"

OUT = DATA / "edgeiq_live_runner_dna_v6.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_summary.csv"
JSON_OUT = DATA / "edgeiq_runner_dna_v6_summary.json"

def canon_horse(x):
    if pd.isna(x):
        return ""
    s = str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def band(score):
    if pd.isna(score):
        return "NO_PROFILE"
    if score >= 85:
        return "ELITE"
    if score >= 72:
        return "STRONG"
    if score >= 58:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 30:
        return "NEGATIVE"
    return "POOR"

base = pd.read_csv(BASE_DNA, low_memory=False)
dist = pd.read_csv(DIST, low_memory=False)
cond = pd.read_csv(COND, low_memory=False)
cls = pd.read_csv(CLASS, low_memory=False)

for df in [base, dist, cond, cls]:
    df["horse_join"] = df["horse"].apply(canon_horse)
    df["track_join"] = df["track"].astype(str).str.upper().str.strip()
    df["race_join"] = pd.to_numeric(df["race_no"], errors="coerce").fillna(-1).astype(int)

join_cols = ["track_join","race_join","horse_join"]

dna = base.copy()

dna = dna.merge(
    dist[
        join_cols + [
            "distance_fit_score",
            "distance_fit_band"
        ]
    ],
    on=join_cols,
    how="left"
)

dna = dna.merge(
    cond[
        join_cols + [
            "condition_fit_score",
            "condition_fit_band"
        ]
    ],
    on=join_cols,
    how="left"
)

dna = dna.merge(
    cls[
        join_cols + [
            "class_fit_score",
            "class_fit_band",
            "class_movement"
        ]
    ],
    on=join_cols,
    how="left"
)

for c in [
    "distance_fit_score",
    "condition_fit_score",
    "class_fit_score"
]:
    dna[c] = pd.to_numeric(dna[c], errors="coerce")

score_candidates = []

if "distance_fit_score" in dna.columns:
    score_candidates.append("distance_fit_score")

if "condition_fit_score" in dna.columns:
    score_candidates.append("condition_fit_score")

if "class_fit_score" in dna.columns:
    score_candidates.append("class_fit_score")

dna["dna_v6_component_count"] = dna[score_candidates].notna().sum(axis=1)

dna["dna_v6_score"] = (
    dna[score_candidates]
    .mean(axis=1, skipna=True)
    .round(1)
)

dna["dna_v6_band"] = dna["dna_v6_score"].apply(band)

def strongest_factor(row):
    vals = {
        "DISTANCE": row.get("distance_fit_score"),
        "CONDITION": row.get("condition_fit_score"),
        "CLASS": row.get("class_fit_score"),
    }

    vals = {
        k: float(v)
        for k, v in vals.items()
        if pd.notna(v)
    }

    if len(vals) == 0:
        return pd.Series(["UNKNOWN",0])

    best = max(vals, key=vals.get)
    return pd.Series([best, round(vals[best],1)])

def weakest_factor(row):
    vals = {
        "DISTANCE": row.get("distance_fit_score"),
        "CONDITION": row.get("condition_fit_score"),
        "CLASS": row.get("class_fit_score"),
    }

    vals = {
        k: float(v)
        for k, v in vals.items()
        if pd.notna(v)
    }

    if len(vals) == 0:
        return pd.Series(["UNKNOWN",0])

    worst = min(vals, key=vals.get)
    return pd.Series([worst, round(vals[worst],1)])

dna[["strongest_factor","strongest_factor_score"]] = dna.apply(strongest_factor, axis=1)
dna[["weakest_factor","weakest_factor_score"]] = dna.apply(weakest_factor, axis=1)

def build_narrative(row):

    bullets = []

    if row.get("distance_fit_band") == "ELITE":
        bullets.append("Elite distance profile")

    elif row.get("distance_fit_band") == "STRONG":
        bullets.append("Strong distance profile")

    if row.get("condition_fit_band") == "ELITE":
        bullets.append("Outstanding condition profile")

    elif row.get("condition_fit_band") == "STRONG":
        bullets.append("Condition positive")

    if row.get("class_movement") == "CLASS_RISE":
        bullets.append("Rising in grade")

    elif row.get("class_movement") == "CLASS_DROP":
        bullets.append("Class drop positive")

    if row.get("class_fit_band") == "ELITE":
        bullets.append("Elite class performance")

    elif row.get("class_fit_band") == "STRONG":
        bullets.append("Strong class performance")

    if len(bullets) == 0:
        bullets.append("Limited DNA evidence available")

    return ". ".join(bullets) + "."

dna["runner_dna_narrative"] = dna.apply(build_narrative, axis=1)

dna.to_csv(OUT, index=False)

summary_rows = [
    {"metric":"status","value":"RUNNER_DNA_V6_BUILT"},
    {"metric":"rows","value":len(dna)},
    {"metric":"avg_score","value":round(float(dna["dna_v6_score"].mean()),2)},
    {"metric":"elite","value":int((dna["dna_v6_band"]=="ELITE").sum())},
    {"metric":"strong","value":int((dna["dna_v6_band"]=="STRONG").sum())},
    {"metric":"positive","value":int((dna["dna_v6_band"]=="POSITIVE").sum())},
    {"metric":"neutral","value":int((dna["dna_v6_band"]=="NEUTRAL").sum())},
    {"metric":"negative","value":int((dna["dna_v6_band"]=="NEGATIVE").sum())},
    {"metric":"poor","value":int((dna["dna_v6_band"]=="POOR").sum())},
]
summary = pd.DataFrame(summary_rows)

summary.to_csv(SUMMARY,index=False)

JSON_OUT.write_text(
    json.dumps(
        {r["metric"]:r["value"] for _,r in summary.iterrows()},
        indent=2
    ),
    encoding="utf-8"
)

print("[RUNNER_DNA_V6] COMPLETE")
print(summary.to_string(index=False))
