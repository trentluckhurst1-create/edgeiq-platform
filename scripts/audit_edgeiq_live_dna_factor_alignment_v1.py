from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PRED = DATA / "edgeiq_factor_predictiveness_factor_rankings_v2.csv"

OUT = DATA / "edgeiq_live_dna_factor_alignment_v1.csv"
SUMMARY = DATA / "edgeiq_live_dna_factor_alignment_v1_summary.csv"

built_at = datetime.now(timezone.utc).isoformat()

pred = pd.read_csv(PRED, dtype=str).fillna("")
pred_map = {r["factor"]: r for _, r in pred.iterrows()}

ALIGNMENT = [
    {
        "live_factor": "RATING",
        "live_score_column": "rating_score",
        "historical_equivalent": "PROJECTED_RATING",
        "current_weight_guess": 0.50,
        "recommended_direction": "INCREASE",
        "alignment_confidence": "HIGH",
        "reason": "Live rating is the customer-facing equivalent of projected historical rating.",
    },
    {
        "live_factor": "SECTIONALS",
        "live_score_column": "sectional_score",
        "historical_equivalent": "SECTIONALS",
        "current_weight_guess": 1.00,
        "recommended_direction": "INCREASE",
        "alignment_confidence": "HIGH",
        "reason": "Historical sectional strength was a strong validated predictor.",
    },
    {
        "live_factor": "JOCKEY",
        "live_score_column": "jockey_score",
        "historical_equivalent": "JOCKEY",
        "current_weight_guess": 0.30,
        "recommended_direction": "CAUTIOUS_INCREASE",
        "alignment_confidence": "HIGH",
        "reason": "Jockey had strong winner gains but also highest loss volatility.",
    },
    {
        "live_factor": "TRAINER",
        "live_score_column": "trainer_score",
        "historical_equivalent": "TRAINER",
        "current_weight_guess": 0.30,
        "recommended_direction": "HOLD_OR_REDUCE",
        "alignment_confidence": "HIGH",
        "reason": "Trainer was weak historically and should remain secondary.",
    },
    {
        "live_factor": "COMBO",
        "live_score_column": "combo_score",
        "historical_equivalent": "CONNECTION",
        "current_weight_guess": 0.40,
        "recommended_direction": "HOLD",
        "alignment_confidence": "MEDIUM",
        "reason": "Combo is closest live proxy for connection, but not identical.",
    },
    {
        "live_factor": "CLASS",
        "live_score_column": "class_score/class_fit_score",
        "historical_equivalent": "GOVERNED_PROJECTION",
        "current_weight_guess": 1.00,
        "recommended_direction": "HOLD",
        "alignment_confidence": "MEDIUM",
        "reason": "Class likely overlaps with governed projection but is not a direct equivalent.",
    },
    {
        "live_factor": "FORM",
        "live_score_column": "form_score",
        "historical_equivalent": "RUNNER_SCORE",
        "current_weight_guess": 1.00,
        "recommended_direction": "HOLD",
        "alignment_confidence": "MEDIUM",
        "reason": "Form contributes to runner score but is not a full equivalent.",
    },
    {
        "live_factor": "DISTANCE",
        "live_score_column": "distance_score/distance_fit_score",
        "historical_equivalent": "",
        "current_weight_guess": 1.00,
        "recommended_direction": "HOLD_PENDING_DIRECT_BACKTEST",
        "alignment_confidence": "LOW",
        "reason": "No direct historical replay factor found yet.",
    },
    {
        "live_factor": "CONDITION",
        "live_score_column": "condition_score/condition_fit_score",
        "historical_equivalent": "",
        "current_weight_guess": 1.00,
        "recommended_direction": "HOLD_PENDING_DIRECT_BACKTEST",
        "alignment_confidence": "LOW",
        "reason": "No direct historical replay factor found yet.",
    },
    {
        "live_factor": "PACE",
        "live_score_column": "pace_score",
        "historical_equivalent": "LIVE_STRENGTH",
        "current_weight_guess": 0.00,
        "recommended_direction": "NO_INCREASE",
        "alignment_confidence": "LOW",
        "reason": "Live strength showed no edge in predictiveness audit.",
    },
    {
        "live_factor": "LATE_POWER",
        "live_score_column": "late_power_score",
        "historical_equivalent": "",
        "current_weight_guess": 0.00,
        "recommended_direction": "HOLD_PENDING_DIRECT_BACKTEST",
        "alignment_confidence": "LOW",
        "reason": "No direct historical equivalent in settled replay.",
    },
    {
        "live_factor": "PROFILE",
        "live_score_column": "profile_score",
        "historical_equivalent": "CONFIDENCE_ADJUSTED",
        "current_weight_guess": 0.50,
        "recommended_direction": "HOLD",
        "alignment_confidence": "LOW",
        "reason": "Profile may overlap with confidence adjusted but mapping is indirect.",
    },
]

rows = []

for item in ALIGNMENT:
    hist = item["historical_equivalent"]
    p = pred_map.get(hist, {})

    rows.append({
        **item,
        "historical_verdict": p.get("verdict", ""),
        "historical_predictive_spread": p.get("predictive_spread", ""),
        "historical_sample_adjusted_score": p.get("sample_adjusted_score", ""),
        "historical_best_bucket": p.get("best_bucket", ""),
        "historical_best_bucket_win_lift": p.get("best_bucket_win_lift", ""),
        "research_only": "YES",
        "built_at": built_at,
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "LIVE_DNA_FACTOR_ALIGNMENT_V1_BUILT"],
    ["rows", len(out)],
    ["high_confidence", int((out["alignment_confidence"] == "HIGH").sum())],
    ["medium_confidence", int((out["alignment_confidence"] == "MEDIUM").sum())],
    ["low_confidence", int((out["alignment_confidence"] == "LOW").sum())],
    ["source_predictiveness", PRED.name],
    ["research_only", "YES"],
    ["built_at", built_at],
], columns=["metric","value"])

summary.to_csv(SUMMARY, index=False)

print("[LIVE_DNA_FACTOR_ALIGNMENT_V1] COMPLETE")
print(summary.to_string(index=False))
print(out.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
