import pandas as pd
import numpy as np
import re
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_runner_dna_v6_full.csv"

OUT_LIVE = DATA / "edgeiq_live_runner_dna_v6_1_rebalance.csv"
OUT_CURRENT = DATA / "edgeiq_runner_dna_v6_1_rebalance.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_1_rebalance_summary.csv"
JSON_OUT = DATA / "edgeiq_runner_dna_v6_1_rebalance_summary.json"

def num(x):
    return pd.to_numeric(x, errors="coerce")

def band(score):
    if pd.isna(score):
        return "NO_PROFILE"
    if score >= 82:
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

def label(col):
    return {
        "form_score": "FORM",
        "rating_score": "RATING",
        "distance_fit_score": "DISTANCE",
        "condition_fit_score": "CONDITION",
        "class_fit_score": "CLASS",
        "sectional_score": "SECTIONALS",
        "profile_score": "PROFILE",
        "pace_score": "PACE",
        "fitness_score": "FITNESS",
        "late_power_score": "LATE POWER",
        "track_score": "TRACK",
        "barrier_score": "BARRIER",
        "trainer_score": "TRAINER",
        "jockey_score": "JOCKEY",
        "combo_score": "COMBO",
    }.get(col, col.upper())

CORE = [
    "form_score",
    "rating_score",
    "distance_fit_score",
    "condition_fit_score",
    "class_fit_score",
    "sectional_score",
]

SECONDARY = [
    "profile_score",
    "pace_score",
    "fitness_score",
    "late_power_score",
]

CONTEXT = [
    "track_score",
    "barrier_score",
    "trainer_score",
    "jockey_score",
    "combo_score",
]

WEIGHTS = {}
for c in CORE:
    WEIGHTS[c] = 1.00
for c in SECONDARY:
    WEIGHTS[c] = 0.50
for c in CONTEXT:
    WEIGHTS[c] = 0.20

CONTEXT_PLACEHOLDER_VALUES = {0.0, 8.0, 10.0}

dna = pd.read_csv(SRC, low_memory=False)

all_cols = [c for c in CORE + SECONDARY + CONTEXT if c in dna.columns]

for c in all_cols:
    dna[c] = num(dna[c])

for c in CONTEXT:
    if c in dna.columns:
        dna[c + "_clean"] = dna[c].where(~dna[c].isin(CONTEXT_PLACEHOLDER_VALUES), np.nan)

for c in CORE + SECONDARY:
    if c in dna.columns:
        dna[c + "_clean"] = dna[c].replace(0, np.nan)

clean_cols = []
for c in CORE + SECONDARY + CONTEXT:
    clean = c + "_clean"
    if clean in dna.columns:
        clean_cols.append(clean)

clean_to_raw = {c + "_clean": c for c in CORE + SECONDARY + CONTEXT}

def weighted_score(row):
    total = 0.0
    denom = 0.0

    for clean_col in clean_cols:
        raw_col = clean_to_raw[clean_col]
        v = row.get(clean_col)

        if pd.notna(v):
            w = WEIGHTS.get(raw_col, 1.0)
            total += float(v) * w
            denom += w

    if denom <= 0:
        return np.nan

    return round(total / denom, 1)

dna["runner_dna_v6_1_score"] = dna.apply(weighted_score, axis=1)
dna["runner_dna_v6_1_band"] = dna["runner_dna_v6_1_score"].apply(band)
dna["runner_dna_v6_1_component_count"] = dna[clean_cols].notna().sum(axis=1)

def top_factors(row, reverse=True, n=3):
    vals = []
    for clean_col in clean_cols:
        raw_col = clean_to_raw[clean_col]
        v = row.get(clean_col)
        if pd.notna(v):
            vals.append((label(raw_col), float(v)))

    if not vals:
        return ""

    vals = sorted(vals, key=lambda x: x[1], reverse=reverse)[:n]
    return " | ".join([f"{k} {v:.1f}" for k, v in vals])

def best_factor(row):
    vals = []
    for clean_col in clean_cols:
        raw_col = clean_to_raw[clean_col]
        v = row.get(clean_col)
        if pd.notna(v):
            vals.append((label(raw_col), float(v)))

    if not vals:
        return pd.Series(["UNKNOWN", 0.0])

    k, v = sorted(vals, key=lambda x: x[1], reverse=True)[0]
    return pd.Series([k, round(v, 1)])

def worst_factor(row):
    vals = []
    for clean_col in clean_cols:
        raw_col = clean_to_raw[clean_col]
        v = row.get(clean_col)
        if pd.notna(v):
            vals.append((label(raw_col), float(v)))

    if not vals:
        return pd.Series(["UNKNOWN", 0.0])

    k, v = sorted(vals, key=lambda x: x[1])[0]
    return pd.Series([k, round(v, 1)])

dna["strongest_factors_v6_1"] = dna.apply(lambda r: top_factors(r, True, 3), axis=1)
dna["weakest_factors_v6_1"] = dna.apply(lambda r: top_factors(r, False, 3), axis=1)
dna[["strongest_factor_v6_1", "strongest_factor_score_v6_1"]] = dna.apply(best_factor, axis=1)
dna[["weakest_factor_v6_1", "weakest_factor_score_v6_1"]] = dna.apply(worst_factor, axis=1)

def narrative(row):
    parts = []

    if row.get("distance_fit_band") in ["ELITE", "STRONG"]:
        parts.append(f'{str(row.get("distance_fit_band")).title()} distance profile')
    elif pd.isna(row.get("distance_fit_score_clean")):
        parts.append("Distance profile unknown")

    if row.get("condition_fit_band") in ["ELITE", "STRONG"]:
        parts.append(f'{str(row.get("condition_fit_band")).title()} condition profile')
    elif pd.isna(row.get("condition_fit_score_clean")):
        parts.append("Condition profile unknown")

    if row.get("class_movement") == "CLASS_DROP":
        parts.append("Class drop positive")
    elif row.get("class_movement") == "CLASS_RISE":
        parts.append("Class rise risk")

    if pd.notna(row.get("sectional_score_clean")):
        if float(row.get("sectional_score_clean")) >= 72:
            parts.append("Strong sectional profile")
        elif float(row.get("sectional_score_clean")) <= 35:
            parts.append("Sectionals are a risk")

    if pd.notna(row.get("rating_score_clean")):
        if float(row.get("rating_score_clean")) >= 72:
            parts.append("Rating profile strong")
        elif float(row.get("rating_score_clean")) <= 35:
            parts.append("Rating profile weak")

    if pd.notna(row.get("form_score_clean")):
        if float(row.get("form_score_clean")) >= 80:
            parts.append("Current form is strong")
        elif float(row.get("form_score_clean")) <= 45:
            parts.append("Current form is weak")

    if not parts:
        parts.append("Balanced DNA profile with no dominant standout")

    return ". ".join(parts[:5]) + "."

dna["runner_dna_v6_1_narrative"] = dna.apply(narrative, axis=1)

dna["runner_dna_v6_1_customer_summary"] = dna.apply(
    lambda r: f'DNA {r["runner_dna_v6_1_score"]:.1f} {r["runner_dna_v6_1_band"]} | Strong: {r["strongest_factors_v6_1"]} | Risk: {r["weakest_factors_v6_1"]}',
    axis=1
)

dna["built_at_runner_dna_v6_1_rebalance"] = datetime.now(timezone.utc).isoformat()

dna = dna.sort_values(
    ["track", "race_no", "runner_dna_v6_1_score"],
    ascending=[True, True, False]
)

dna["runner_dna_v6_1_rank_in_race"] = dna.groupby(["track", "race_no"])["runner_dna_v6_1_score"].rank(method="first", ascending=False)

dna.to_csv(OUT_LIVE, index=False)
dna.to_csv(OUT_CURRENT, index=False)

summary_rows = [
    {"metric": "status", "value": "RUNNER_DNA_V6_1_REBALANCE_BUILT"},
    {"metric": "rows", "value": len(dna)},
    {"metric": "clean_components_available", "value": len(clean_cols)},
    {"metric": "clean_component_columns", "value": "|".join(clean_cols)},
    {"metric": "avg_score", "value": round(float(dna["runner_dna_v6_1_score"].mean()), 2)},
    {"metric": "elite", "value": int((dna["runner_dna_v6_1_band"] == "ELITE").sum())},
    {"metric": "strong", "value": int((dna["runner_dna_v6_1_band"] == "STRONG").sum())},
    {"metric": "positive", "value": int((dna["runner_dna_v6_1_band"] == "POSITIVE").sum())},
    {"metric": "neutral", "value": int((dna["runner_dna_v6_1_band"] == "NEUTRAL").sum())},
    {"metric": "negative", "value": int((dna["runner_dna_v6_1_band"] == "NEGATIVE").sum())},
    {"metric": "poor", "value": int((dna["runner_dna_v6_1_band"] == "POOR").sum())},
]
summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

JSON_OUT.write_text(
    json.dumps({r["metric"]: r["value"] for r in summary_rows}, indent=2),
    encoding="utf-8"
)

print("[RUNNER_DNA_V6_1_REBALANCE] COMPLETE")
print(summary.to_string(index=False))
print()
print(dna["runner_dna_v6_1_band"].value_counts(dropna=False).to_string())
