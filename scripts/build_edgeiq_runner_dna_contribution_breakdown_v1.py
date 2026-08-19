from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_runner_dna_v6_2.csv"

OUT = DATA / "edgeiq_runner_dna_contribution_breakdown_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_contribution_breakdown_v1_summary.csv"

FACTOR_SOURCES = {
    "rating": "rating_score",
    "sectionals": "sectional_score",
    "jockey": "jockey_score",
    "trainer": "trainer_score",
    "connection": "tj_blend_score",
    "distance": "distance_fit_score",
    "condition": "condition_fit_score",
    "pace": "pace_score",
    "late_power": "late_power_score",
    "profile": "profile_score",
}

# UI/display weights only.
# These are not changing production DNA.
# They explain approximate contribution pressure around a neutral baseline.
FACTOR_WEIGHTS = {
    "rating": 0.22,
    "sectionals": 0.15,
    "jockey": 0.08,
    "trainer": 0.08,
    "connection": 0.12,
    "distance": 0.10,
    "condition": 0.08,
    "pace": 0.08,
    "late_power": 0.04,
    "profile": 0.05,
}

NEUTRAL_BASELINE = 50.0

def num(v):
    try:
        s = str(v).replace("$", "").replace("%", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def band(score):
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 80:
        return "ELITE"
    if score >= 70:
        return "STRONG"
    if score >= 60:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 30:
        return "NEGATIVE"
    return "POOR"

def tone_from_impact(v):
    if pd.isna(v):
        return "unknown"
    if v >= 4:
        return "positive"
    if v <= -4:
        return "negative"
    return "neutral"

def bar(score):
    if pd.isna(score):
        return "----------"
    blocks = int(round(max(0, min(100, score)) / 10))
    return "█" * blocks + "░" * (10 - blocks)

def impact_bar(impact):
    if pd.isna(impact):
        return "----------"
    capped = max(-10, min(10, impact))
    magnitude = int(round(abs(capped)))
    if capped > 0:
        return "+" + "█" * magnitude
    if capped < 0:
        return "-" + "█" * magnitude
    return "0"

def clean_factor_name(x):
    return x.replace("_", " ").upper()

df = pd.read_csv(SRC, dtype=str).fillna("")
built_at = datetime.now(timezone.utc).isoformat()

rows = []

for _, r in df.iterrows():
    dna_score = num(r.get("dna_v6_2_score", r.get("runner_dna_score", "")))
    dna_band = str(r.get("dna_v6_2_band", r.get("runner_dna_band", ""))).strip()

    row = {
        "race_date": r.get("race_date", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "horse": r.get("horse", ""),
        "horse_key": r.get("horse_key", ""),
        "trainer": r.get("trainer", ""),
        "jockey": r.get("jockey", ""),
        "dna_score": round(dna_score, 1) if not pd.isna(dna_score) else "",
        "dna_band": dna_band,
        "neutral_baseline": NEUTRAL_BASELINE,
        "research_only": "NO",
        "built_at": built_at,
    }

    factor_rows = []

    for factor, source_col in FACTOR_SOURCES.items():
        raw_score = num(r.get(source_col, ""))
        weight = FACTOR_WEIGHTS[factor]

        if pd.isna(raw_score):
            impact = np.nan
        else:
            impact = (raw_score - NEUTRAL_BASELINE) * weight

        factor_rows.append({
            "factor": factor,
            "label": clean_factor_name(factor),
            "source_col": source_col,
            "raw_score": raw_score,
            "impact": impact,
            "weight": weight,
        })

        row[f"{factor}_source_col"] = source_col
        row[f"{factor}_raw"] = round(raw_score, 1) if not pd.isna(raw_score) else ""
        row[f"{factor}_band"] = band(raw_score)
        row[f"{factor}_bar"] = bar(raw_score)
        row[f"{factor}_weight"] = weight
        row[f"{factor}_impact"] = round(impact, 2) if not pd.isna(impact) else ""
        row[f"{factor}_impact_tone"] = tone_from_impact(impact)
        row[f"{factor}_impact_bar"] = impact_bar(impact)

    scored = [x for x in factor_rows if not pd.isna(x["impact"])]

    positives = sorted(scored, key=lambda x: x["impact"], reverse=True)[:3]
    negatives = sorted(scored, key=lambda x: x["impact"])[:3]

    row["top_positive_impacts"] = " | ".join([
        f"{x['label']} {round(x['impact'], 2):+}" for x in positives
    ])

    row["top_negative_impacts"] = " | ".join([
        f"{x['label']} {round(x['impact'], 2):+}" for x in negatives
    ])

    for i, x in enumerate(positives, start=1):
        row[f"positive_{i}_factor"] = x["label"]
        row[f"positive_{i}_raw"] = round(x["raw_score"], 1)
        row[f"positive_{i}_impact"] = round(x["impact"], 2)
        row[f"positive_{i}_source_col"] = x["source_col"]

    for i, x in enumerate(negatives, start=1):
        row[f"negative_{i}_factor"] = x["label"]
        row[f"negative_{i}_raw"] = round(x["raw_score"], 1)
        row[f"negative_{i}_impact"] = round(x["impact"], 2)
        row[f"negative_{i}_source_col"] = x["source_col"]

    if pd.isna(dna_score):
        row["impact_explanation"] = "DNA score unavailable."
    elif dna_score >= 70:
        row["impact_explanation"] = f"Strong DNA profile. Main supports: {row['top_positive_impacts']}. Main risks: {row['top_negative_impacts']}."
    elif dna_score >= 60:
        row["impact_explanation"] = f"Positive DNA profile. Main supports: {row['top_positive_impacts']}. Main risks: {row['top_negative_impacts']}."
    elif dna_score >= 45:
        row["impact_explanation"] = f"Mixed DNA profile. Main supports: {row['top_positive_impacts']}. Main risks: {row['top_negative_impacts']}."
    elif dna_score >= 30:
        row["impact_explanation"] = f"Negative DNA profile. Main supports: {row['top_positive_impacts']}. Main risks: {row['top_negative_impacts']}."
    else:
        row["impact_explanation"] = f"Poor DNA profile. Main supports: {row['top_positive_impacts']}. Main risks: {row['top_negative_impacts']}."

    rows.append(row)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary_rows = [
    {"metric": "status", "value": "RUNNER_DNA_CONTRIBUTION_BREAKDOWN_V1_BUILT"},
    {"metric": "source", "value": SRC.name},
    {"metric": "output", "value": OUT.name},
    {"metric": "rows", "value": len(out)},
    {"metric": "avg_dna_score", "value": round(pd.to_numeric(out["dna_score"], errors="coerce").mean(), 3)},
    {"metric": "neutral_baseline", "value": NEUTRAL_BASELINE},
    {"metric": "production_changed", "value": "NO"},
    {"metric": "built_at", "value": built_at},
]

for factor in FACTOR_SOURCES:
    vals = pd.to_numeric(out[f"{factor}_impact"], errors="coerce")
    summary_rows.append({"metric": f"{factor}_avg_impact", "value": round(vals.mean(), 4)})
    summary_rows.append({"metric": f"{factor}_positive_count", "value": int((vals > 0).sum())})
    summary_rows.append({"metric": f"{factor}_negative_count", "value": int((vals < 0).sum())})

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_CONTRIBUTION_BREAKDOWN_V1] COMPLETE")
print(summary.head(20).to_string(index=False))
print(out[[
    "horse",
    "dna_score",
    "dna_band",
    "top_positive_impacts",
    "top_negative_impacts",
    "impact_explanation"
]].head(25).to_string(index=False))
