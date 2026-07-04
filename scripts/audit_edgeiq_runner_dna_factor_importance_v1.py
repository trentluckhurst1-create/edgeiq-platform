from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"
OUT = DATA / "edgeiq_runner_dna_factor_importance_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_factor_importance_v1_summary.csv"

FACTOR_WEIGHTS = {
    "FORM": 1.00,
    "RATING": 0.50,
    "PACE": 0.00,
    "DISTANCE": 1.25,
    "CONDITION": 1.25,
    "CLASS": 1.25,
    "SECTIONALS": 1.00,
    "PROFILE": 0.50,
    "TRAINER": 0.25,
    "JOCKEY": 0.25,
    "COMBO": 0.25,
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

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for _, r in df.iterrows():
    factor = str(r.get("factor", "")).upper()
    score = num(r.get("factor_score", ""))
    weight = FACTOR_WEIGHTS.get(factor, 0.0)

    if pd.isna(score):
        contribution = 0.0
    else:
        contribution = ((score - 50.0) / 50.0) * weight

    rows.append({
        "race_date": r.get("race_date", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "horse": r.get("horse", ""),
        "join_key": r.get("join_key", ""),
        "factor": factor,
        "factor_score": "" if pd.isna(score) else round(score, 2),
        "factor_weight": weight,
        "dna_contribution": round(contribution, 4),
        "abs_dna_contribution": round(abs(contribution), 4),
        "contribution_direction": "POSITIVE" if contribution > 0 else "NEGATIVE" if contribution < 0 else "NEUTRAL",
        "built_at": built_at,
    })

out = pd.DataFrame(rows)

out["rank_positive_in_runner"] = (
    out.sort_values(["join_key", "dna_contribution"], ascending=[True, False])
    .groupby("join_key")
    .cumcount() + 1
)

out["rank_risk_in_runner"] = (
    out.sort_values(["join_key", "dna_contribution"], ascending=[True, True])
    .groupby("join_key")
    .cumcount() + 1
)

out.to_csv(OUT, index=False)

summary_rows = []
for factor, g in out.groupby("factor"):
    summary_rows.append({
        "factor": factor,
        "rows": len(g),
        "avg_contribution": round(g["dna_contribution"].mean(), 4),
        "avg_abs_contribution": round(g["abs_dna_contribution"].mean(), 4),
        "positive_rows": int((g["dna_contribution"] > 0).sum()),
        "negative_rows": int((g["dna_contribution"] < 0).sum()),
        "neutral_rows": int((g["dna_contribution"] == 0).sum()),
    })

summary = pd.DataFrame(summary_rows).sort_values("avg_abs_contribution", ascending=False)

header = pd.DataFrame([
    {
        "factor": "__STATUS__",
        "rows": len(out),
        "avg_contribution": "",
        "avg_abs_contribution": "",
        "positive_rows": "",
        "negative_rows": "",
        "neutral_rows": "RUNNER_DNA_FACTOR_IMPORTANCE_V1_BUILT",
    }
])

pd.concat([header, summary], ignore_index=True).to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_FACTOR_IMPORTANCE_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
