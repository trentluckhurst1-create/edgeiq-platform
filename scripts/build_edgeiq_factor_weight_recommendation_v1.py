from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_factor_predictiveness_factor_rankings_v2.csv"

OUT = DATA / "edgeiq_factor_weight_recommendation_v1.csv"
SUMMARY = DATA / "edgeiq_factor_weight_recommendation_v1_summary.csv"

BASE_WEIGHTS = {
    "RUNNER_SCORE": 1.00,
    "PROJECTED_RATING": 1.00,
    "GOVERNED_PROJECTION": 1.00,
    "SECTIONALS": 1.00,
    "STRENGTH_ADJUSTED": 1.00,
    "CONFIDENCE_ADJUSTED": 1.00,
    "TRAINER": 0.25,
    "JOCKEY": 0.25,
    "CONFIDENCE": 0.50,
    "LIVE_STRENGTH": 0.50,
    "PROJECTION_GAP": 0.00,
    "CONNECTION": 0.25,
    "MARKET": 0.00,
}

def num(x):
    try:
        s = str(x).strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

df = pd.read_csv(SRC, dtype=str).fillna("")
built_at = datetime.now(timezone.utc).isoformat()

rows = []

for _, r in df.iterrows():
    factor = str(r.get("factor", "")).strip()
    verdict = str(r.get("verdict", "")).strip()
    spread = num(r.get("predictive_spread", ""))
    score = num(r.get("sample_adjusted_score", ""))
    best_lift = num(r.get("best_bucket_win_lift", ""))
    best_runners = num(r.get("best_bucket_runners", ""))

    base = BASE_WEIGHTS.get(factor, 0.25)

    if factor == "MARKET":
        recommended = 0.00
        reason = "excluded: market score direction requires separate audit"
    elif verdict == "STRONG" and not pd.isna(score):
        recommended = min(1.50, max(base, 0.75 + (score / 100.0)))
        reason = "strong historical sample-adjusted predictiveness"
    elif verdict == "POSITIVE" and not pd.isna(score):
        recommended = min(1.25, max(base, 0.50 + (score / 120.0)))
        reason = "positive historical predictiveness"
    elif verdict == "WEAK":
        recommended = min(base, 0.25)
        reason = "weak historical predictiveness"
    else:
        recommended = 0.00
        reason = "no reliable edge or insufficient predictive value"

    rows.append({
        "factor": factor,
        "base_weight": round(base, 3),
        "recommended_weight_v1": round(recommended, 3),
        "weight_delta": round(recommended - base, 3),
        "verdict": verdict,
        "predictive_spread": r.get("predictive_spread", ""),
        "sample_adjusted_score": r.get("sample_adjusted_score", ""),
        "best_bucket": r.get("best_bucket", ""),
        "best_bucket_runners": r.get("best_bucket_runners", ""),
        "best_bucket_win_lift": r.get("best_bucket_win_lift", ""),
        "worst_bucket": r.get("worst_bucket", ""),
        "worst_bucket_win_lift": r.get("worst_bucket_win_lift", ""),
        "recommendation_reason": reason,
        "research_only": "YES",
        "built_at": built_at,
    })

out = pd.DataFrame(rows)
out["_sort"] = pd.to_numeric(out["recommended_weight_v1"], errors="coerce")
out = out.sort_values("_sort", ascending=False).drop(columns=["_sort"])
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "FACTOR_WEIGHT_RECOMMENDATION_V1_BUILT"],
    ["source", SRC.name],
    ["rows", len(out)],
    ["market_excluded", "YES"],
    ["research_only", "YES"],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[FACTOR_WEIGHT_RECOMMENDATION_V1] COMPLETE")
print(summary.to_string(index=False))
print(out.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
