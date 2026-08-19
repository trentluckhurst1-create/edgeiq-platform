from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_runner_dna_v6_2.csv"
OUT = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"
SUMMARY = DATA / "edgeiq_runner_factor_scorecard_v2_summary.csv"

FACTORS = [
    ("FORM", "form_score", "Form profile"),
    ("RATING", "rating_score", "Rating strength"),
    ("PACE", "pace_score", "Pace / tactical setup"),
    ("DISTANCE", "distance_fit_score", "Distance suitability"),
    ("CONDITION", "condition_fit_score", "Track condition suitability"),
    ("CLASS", "class_fit_score", "Class suitability"),
    ("SECTIONALS", "sectional_score", "Sectional strength"),
    ("PROFILE", "profile_score", "Horse profile"),
    ("TRAINER", "trainer_score", "Trainer edge"),
    ("JOCKEY", "jockey_score", "Jockey edge"),
    ("COMBO", "combo_score", "Trainer / jockey combo"),
]

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(x)
    except Exception:
        return np.nan

def band(score):
    if pd.isna(score):
        return "NO_SCORE"
    if score >= 80:
        return "ELITE"
    if score >= 65:
        return "STRONG"
    if score >= 50:
        return "POSITIVE"
    if score >= 35:
        return "NEUTRAL"
    if score >= 20:
        return "NEGATIVE"
    return "POOR"

def polarity(score):
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 65:
        return "POSITIVE"
    if score < 35:
        return "NEGATIVE"
    return "NEUTRAL"

def explain_factor(name, score, factor_band):
    if pd.isna(score):
        return f"{name} has no usable score."
    s = round(score, 1)
    if factor_band == "ELITE":
        return f"{name} is an elite positive at {s}."
    if factor_band == "STRONG":
        return f"{name} is a strong positive at {s}."
    if factor_band == "POSITIVE":
        return f"{name} is positive at {s}."
    if factor_band == "NEUTRAL":
        return f"{name} is neutral at {s}."
    if factor_band == "NEGATIVE":
        return f"{name} is a negative at {s}."
    return f"{name} is poor at {s}."

if not SRC.exists():
    raise FileNotFoundError(f"Missing source: {SRC}")

df = pd.read_csv(SRC, dtype=str).fillna("")

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for _, r in df.iterrows():
    base = {
        "race_date": r.get("race_date", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "horse": r.get("horse", ""),
        "horse_key": r.get("horse_key", ""),
        "runner_key": r.get("runner_key", ""),
        "join_key": r.get("join_key", ""),
        "dna_v6_2_score": r.get("dna_v6_2_score", ""),
        "dna_v6_2_band": r.get("dna_v6_2_band", ""),
        "runner_dna_v6_2_rank_in_race": r.get("runner_dna_v6_2_rank_in_race", ""),
        "strongest_factor_v6_2": r.get("strongest_factor_v6_2", ""),
        "weakest_factor_v6_2": r.get("weakest_factor_v6_2", ""),
    }

    for order, (factor, col, label) in enumerate(FACTORS, start=1):
        score = num(r.get(col, ""))
        factor_band = band(score)
        rows.append({
            **base,
            "factor_order": order,
            "factor": factor,
            "factor_label": label,
            "source_column": col,
            "factor_score": "" if pd.isna(score) else round(score, 2),
            "factor_band": factor_band,
            "factor_polarity": polarity(score),
            "factor_explanation": explain_factor(factor, score, factor_band),
            "is_strongest_factor": "YES" if factor == r.get("strongest_factor_v6_2", "") else "NO",
            "is_weakest_factor": "YES" if factor == r.get("weakest_factor_v6_2", "") else "NO",
            "built_at": built_at,
        })

out = pd.DataFrame(rows)

out.to_csv(OUT, index=False)

summary_rows = [
    ["status", "RUNNER_FACTOR_SCORECARD_V2_BUILT"],
    ["source", SRC.name],
    ["rows", len(out)],
    ["runner_rows", len(df)],
    ["factor_count", len(FACTORS)],
    ["expected_rows", len(df) * len(FACTORS)],
    ["nonblank_scores", int(pd.to_numeric(out["factor_score"], errors="coerce").notna().sum())],
    ["blank_scores", int(pd.to_numeric(out["factor_score"], errors="coerce").isna().sum())],
    ["positive_factors", int((out["factor_polarity"] == "POSITIVE").sum())],
    ["neutral_factors", int((out["factor_polarity"] == "NEUTRAL").sum())],
    ["negative_factors", int((out["factor_polarity"] == "NEGATIVE").sum())],
    ["built_at", built_at],
]

for f in FACTORS:
    factor = f[0]
    sub = out[out["factor"] == factor]
    scores = pd.to_numeric(sub["factor_score"], errors="coerce")
    summary_rows.append([f"{factor.lower()}_avg", "" if scores.dropna().empty else round(scores.mean(), 2)])
    summary_rows.append([f"{factor.lower()}_nonblank", int(scores.notna().sum())])

pd.DataFrame(summary_rows, columns=["metric", "value"]).to_csv(SUMMARY, index=False)

print("[RUNNER_FACTOR_SCORECARD_V2] COMPLETE")
print(f"source={SRC.name}")
print(f"rows={len(out)}")
print(f"runner_rows={len(df)}")
print(f"factor_count={len(FACTORS)}")
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
