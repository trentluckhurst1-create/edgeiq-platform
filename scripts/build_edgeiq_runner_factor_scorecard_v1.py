import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_runner_dna_ui_feed_v1.csv"

OUT = DATA / "edgeiq_live_runner_factor_scorecard_v1.csv"
SUMMARY = DATA / "edgeiq_runner_factor_scorecard_v1_summary.csv"
JSON_OUT = DATA / "edgeiq_runner_factor_scorecard_v1_summary.json"

FACTOR_MAP = [
    ("FORM", "form_score", "Core form profile"),
    ("RATING", "rating_score", "Current performance rating"),
    ("DISTANCE", "distance_fit_score", "Distance suitability"),
    ("CONDITION", "condition_fit_score", "Condition suitability"),
    ("CLASS", "class_fit_score", "Class suitability"),
    ("SECTIONALS", "sectional_score", "Sectional profile"),
    ("PROFILE", "profile_score", "Career profile quality"),
]

def to_num(x):
    n = pd.to_numeric(x, errors="coerce")
    return n

def band(score):
    if pd.isna(score):
        return "NO PROFILE"
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

df = pd.read_csv(SRC, low_memory=False)

rows = []

for _, r in df.iterrows():
    for factor, col, description in FACTOR_MAP:
        raw = r.get(col, "")
        score = pd.to_numeric(raw, errors="coerce")

        if pd.isna(score) or float(score) == 0.0:
            score_out = ""
            band_out = "NO PROFILE"
            pct = 0
            display = "—"
        else:
            score = round(float(score), 1)
            score_out = score
            band_out = band(score)
            pct = max(0, min(100, score))
            display = f"{score:.1f}"

        rows.append({
            "race_date": r.get("race_date", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "horse": r.get("horse", ""),
            "horse_key": r.get("horse_key", ""),
            "runner_key": r.get("runner_key", ""),
            "runner_dna_v6_1_score": r.get("runner_dna_v6_1_score", ""),
            "runner_dna_v6_1_band": r.get("runner_dna_v6_1_band", ""),
            "runner_dna_v6_1_rank_in_race": r.get("runner_dna_v6_1_rank_in_race", ""),
            "factor": factor,
            "factor_score": score_out,
            "factor_score_display": display,
            "factor_band": band_out,
            "factor_pct": pct,
            "factor_description": description,
        })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary_rows = [
    {"metric": "status", "value": "RUNNER_FACTOR_SCORECARD_V1_BUILT"},
    {"metric": "source_rows", "value": len(df)},
    {"metric": "scorecard_rows", "value": len(out)},
    {"metric": "factors_per_runner", "value": len(FACTOR_MAP)},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
]

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

JSON_OUT.write_text(
    json.dumps({r["metric"]: r["value"] for r in summary_rows}, indent=2),
    encoding="utf-8"
)

print("[RUNNER_FACTOR_SCORECARD_V1] COMPLETE")
print(summary.to_string(index=False))
print()
print(out.head(35).to_string(index=False))
