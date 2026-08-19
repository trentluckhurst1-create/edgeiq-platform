import pandas as pd
import numpy as np
import re
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASE = DATA / "edgeiq_runner_dna_current.csv"
DIST = DATA / "edgeiq_live_distance_dna_v1.csv"
COND = DATA / "edgeiq_live_condition_dna_v1.csv"
CLASS = DATA / "edgeiq_live_class_dna_v3.csv"

OUT_LIVE = DATA / "edgeiq_live_runner_dna_v6_full.csv"
OUT_CURRENT = DATA / "edgeiq_runner_dna_v6_full.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_full_summary.csv"
JSON_OUT = DATA / "edgeiq_runner_dna_v6_full_summary.json"

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
    df["horse_join"] = df["horse"].apply(canon_horse)
    df["track_join"] = df["track"].astype(str).str.upper().str.strip()
    df["race_join"] = pd.to_numeric(df["race_no"], errors="coerce").fillna(-1).astype(int)
    return df

def num(s):
    return pd.to_numeric(s, errors="coerce")

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

def factor_label(col):
    return {
        "form_score": "FORM",
        "profile_score": "PROFILE",
        "rating_score": "RATING",
        "pace_score": "PACE",
        "tactical_score": "TACTICAL",
        "sectional_score": "SECTIONALS",
        "late_power_score": "LATE POWER",
        "fitness_score": "FITNESS",
        "barrier_score": "BARRIER",
        "track_score": "TRACK",
        "trainer_score": "TRAINER",
        "jockey_score": "JOCKEY",
        "combo_score": "COMBO",
        "distance_fit_score": "DISTANCE",
        "condition_fit_score": "CONDITION",
        "class_fit_score": "CLASS",
    }.get(col, col.upper())

base = keyify(pd.read_csv(BASE, low_memory=False))
dist = keyify(pd.read_csv(DIST, low_memory=False))
cond = keyify(pd.read_csv(COND, low_memory=False))
cls = keyify(pd.read_csv(CLASS, low_memory=False))

join_cols = ["track_join", "race_join", "horse_join"]

dna = base.copy()

dna = dna.merge(
    dist[join_cols + ["distance_fit_score", "distance_fit_band", "distance_starts", "distance_wins", "distance_places", "distance_dna_summary"]],
    on=join_cols,
    how="left"
)

dna = dna.merge(
    cond[join_cols + ["condition_fit_score", "condition_fit_band", "condition_starts", "condition_wins", "condition_places", "condition_dna_summary"]],
    on=join_cols,
    how="left"
)

dna = dna.merge(
    cls[join_cols + ["class_fit_score", "class_fit_band", "class_starts", "class_wins", "class_places", "class_profile_source", "class_movement", "class_dna_summary"]],
    on=join_cols,
    how="left"
)

component_cols = [
    "form_score",
    "profile_score",
    "rating_score",
    "pace_score",
    "tactical_score",
    "sectional_score",
    "late_power_score",
    "fitness_score",
    "barrier_score",
    "track_score",
    "trainer_score",
    "jockey_score",
    "combo_score",
    "distance_fit_score",
    "condition_fit_score",
    "class_fit_score",
]

existing_component_cols = [c for c in component_cols if c in dna.columns]

for c in existing_component_cols:
    dna[c] = num(dna[c])

weights = {
    "form_score": 1.25,
    "profile_score": 1.00,
    "rating_score": 1.20,
    "pace_score": 1.00,
    "tactical_score": 0.90,
    "sectional_score": 1.15,
    "late_power_score": 0.80,
    "fitness_score": 0.75,
    "barrier_score": 0.60,
    "track_score": 0.80,
    "trainer_score": 0.65,
    "jockey_score": 0.65,
    "combo_score": 0.70,
    "distance_fit_score": 1.10,
    "condition_fit_score": 1.05,
    "class_fit_score": 1.10,
}

def weighted_score(row):
    total = 0.0
    denom = 0.0
    for c in existing_component_cols:
        v = row.get(c)
        if pd.notna(v):
            w = weights.get(c, 1.0)
            total += float(v) * w
            denom += w
    if denom <= 0:
        return np.nan
    return round(total / denom, 1)

dna["runner_dna_v6_full_score"] = dna.apply(weighted_score, axis=1)
dna["runner_dna_v6_full_band"] = dna["runner_dna_v6_full_score"].apply(band)
dna["runner_dna_v6_full_component_count"] = dna[existing_component_cols].notna().sum(axis=1)

def top_factors(row, reverse=True, n=3):
    vals = []
    for c in existing_component_cols:
        v = row.get(c)
        if pd.notna(v):
            vals.append((factor_label(c), float(v)))
    if not vals:
        return ""
    vals = sorted(vals, key=lambda x: x[1], reverse=reverse)[:n]
    return " | ".join([f"{k} {v:.1f}" for k, v in vals])

def strongest_name(row):
    vals = []
    for c in existing_component_cols:
        v = row.get(c)
        if pd.notna(v):
            vals.append((factor_label(c), float(v)))
    if not vals:
        return pd.Series(["UNKNOWN", 0.0])
    k, v = sorted(vals, key=lambda x: x[1], reverse=True)[0]
    return pd.Series([k, round(v, 1)])

def weakest_name(row):
    vals = []
    for c in existing_component_cols:
        v = row.get(c)
        if pd.notna(v):
            vals.append((factor_label(c), float(v)))
    if not vals:
        return pd.Series(["UNKNOWN", 0.0])
    k, v = sorted(vals, key=lambda x: x[1])[0]
    return pd.Series([k, round(v, 1)])

dna["strongest_factors_v6"] = dna.apply(lambda r: top_factors(r, True, 3), axis=1)
dna["weakest_factors_v6"] = dna.apply(lambda r: top_factors(r, False, 3), axis=1)
dna[["strongest_factor_v6", "strongest_factor_score_v6"]] = dna.apply(strongest_name, axis=1)
dna[["weakest_factor_v6", "weakest_factor_score_v6"]] = dna.apply(weakest_name, axis=1)

def narrative(row):
    parts = []

    if row.get("distance_fit_band") in ["ELITE", "STRONG"]:
        parts.append(f'{str(row.get("distance_fit_band")).title()} distance profile')
    elif row.get("distance_fit_band") == "NO_PROFILE" or pd.isna(row.get("distance_fit_band")):
        parts.append("Distance profile unknown")

    if row.get("condition_fit_band") in ["ELITE", "STRONG"]:
        parts.append(f'{str(row.get("condition_fit_band")).title()} condition profile')
    elif row.get("condition_fit_band") == "NO_PROFILE" or pd.isna(row.get("condition_fit_band")):
        parts.append("Condition profile unknown")

    if row.get("class_movement") == "CLASS_DROP":
        parts.append("Class drop positive")
    elif row.get("class_movement") == "CLASS_RISE":
        parts.append("Class rise risk")

    if row.get("sectional_score") is not None and pd.notna(row.get("sectional_score")):
        if float(row.get("sectional_score")) >= 72:
            parts.append("Strong sectional profile")
        elif float(row.get("sectional_score")) <= 35:
            parts.append("Sectionals are a risk")

    if row.get("pace_score") is not None and pd.notna(row.get("pace_score")):
        if float(row.get("pace_score")) >= 72:
            parts.append("Pace profile positive")
        elif float(row.get("pace_score")) <= 35:
            parts.append("Pace profile risk")

    if row.get("rating_score") is not None and pd.notna(row.get("rating_score")):
        if float(row.get("rating_score")) >= 72:
            parts.append("Rating profile strong")
        elif float(row.get("rating_score")) <= 35:
            parts.append("Rating profile weak")

    if not parts:
        parts.append("Limited DNA evidence available")

    return ". ".join(parts[:5]) + "."

dna["runner_dna_v6_narrative"] = dna.apply(narrative, axis=1)

dna["runner_dna_v6_customer_summary"] = dna.apply(
    lambda r: f'DNA {r["runner_dna_v6_full_score"]:.1f} {r["runner_dna_v6_full_band"]} | Strong: {r["strongest_factors_v6"]} | Risk: {r["weakest_factors_v6"]}',
    axis=1
)

dna["built_at_runner_dna_v6_full"] = datetime.now(timezone.utc).isoformat()

dna = dna.sort_values(
    ["track", "race_no", "runner_dna_v6_full_score"],
    ascending=[True, True, False]
)

dna["runner_dna_v6_rank_in_race"] = dna.groupby(["track", "race_no"])["runner_dna_v6_full_score"].rank(method="first", ascending=False)

dna.to_csv(OUT_LIVE, index=False)
dna.to_csv(OUT_CURRENT, index=False)

summary_rows = [
    {"metric": "status", "value": "RUNNER_DNA_V6_FULL_BUILT"},
    {"metric": "rows", "value": len(dna)},
    {"metric": "components_available", "value": len(existing_component_cols)},
    {"metric": "component_columns", "value": "|".join(existing_component_cols)},
    {"metric": "avg_score", "value": round(float(dna["runner_dna_v6_full_score"].mean()), 2)},
    {"metric": "elite", "value": int((dna["runner_dna_v6_full_band"] == "ELITE").sum())},
    {"metric": "strong", "value": int((dna["runner_dna_v6_full_band"] == "STRONG").sum())},
    {"metric": "positive", "value": int((dna["runner_dna_v6_full_band"] == "POSITIVE").sum())},
    {"metric": "neutral", "value": int((dna["runner_dna_v6_full_band"] == "NEUTRAL").sum())},
    {"metric": "negative", "value": int((dna["runner_dna_v6_full_band"] == "NEGATIVE").sum())},
    {"metric": "poor", "value": int((dna["runner_dna_v6_full_band"] == "POOR").sum())},
]
summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

JSON_OUT.write_text(
    json.dumps({r["metric"]: r["value"] for r in summary_rows}, indent=2),
    encoding="utf-8"
)

print("[RUNNER_DNA_V6_FULL] COMPLETE")
print(summary.to_string(index=False))
print()
print(dna["runner_dna_v6_full_band"].value_counts(dropna=False).to_string())
