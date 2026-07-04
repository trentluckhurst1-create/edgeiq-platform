from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"

OUT = DATA / "edgeiq_factor_threshold_audit_v1.csv"
SUMMARY = DATA / "edgeiq_factor_threshold_audit_v1_summary.csv"

df = pd.read_csv(SOURCE, dtype=str).fillna("")

rows = []

for factor, g in df.groupby("factor"):
    scores = pd.to_numeric(g["factor_score"], errors="coerce").dropna()

    if len(scores) == 0:
        continue

    rows.append({
        "factor": factor,
        "count": len(scores),
        "min": round(scores.min(), 2),
        "p10": round(scores.quantile(.10), 2),
        "p25": round(scores.quantile(.25), 2),
        "p50": round(scores.quantile(.50), 2),
        "p75": round(scores.quantile(.75), 2),
        "p90": round(scores.quantile(.90), 2),
        "max": round(scores.max(), 2),
        "avg": round(scores.mean(), 2),
        "recommended_negative_threshold": round(scores.quantile(.25), 2),
        "recommended_positive_threshold": round(scores.quantile(.75), 2),
    })

out = pd.DataFrame(rows).sort_values("factor")

out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status","FACTOR_THRESHOLD_AUDIT_V1_BUILT"],
    ["factors",len(out)],
    ["source","edgeiq_live_runner_factor_scorecard_v2.csv"]
], columns=["metric","value"])

summary.to_csv(SUMMARY,index=False)

print("[FACTOR_THRESHOLD_AUDIT_V1] COMPLETE")
print(out.to_string(index=False))
