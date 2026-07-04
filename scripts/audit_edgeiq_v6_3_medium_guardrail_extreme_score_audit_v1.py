from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "JOCKEY": DATA / "edgeiq_jockey_score_bucket_flip_analysis_v1.csv",
    "CONNECTION": DATA / "edgeiq_connection_score_bucket_flip_analysis_v1.csv",
}

OUT = DATA / "edgeiq_v6_3_medium_guardrail_extreme_score_audit_v1.csv"
SUMMARY = DATA / "edgeiq_v6_3_medium_guardrail_extreme_score_audit_v1_summary.csv"

def n(x):
    try:
        return float(str(x).strip())
    except Exception:
        return 0.0

rows = []

for factor, path in INPUTS.items():
    df = pd.read_csv(path, dtype=str).fillna("")

    for _, r in df.iterrows():
        base_bucket = r.get("base_bucket", "")
        new_bucket = r.get("new_bucket", "")

        base_score = n(r.get("base_score", ""))
        new_score = n(r.get("new_score", ""))
        delta = new_score - base_score

        is_extreme_jump = (
            (base_bucket in ["00_20", "20_40"] and new_bucket == "80_PLUS") or
            (base_bucket == "40_60" and new_bucket == "80_PLUS") or
            abs(delta) >= 40
        )

        rows.append({
            "factor": factor,
            "race_key": r.get("race_key", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "base_top": r.get("base_top", ""),
            "new_top": r.get("new_top", ""),
            "base_bucket": base_bucket,
            "new_bucket": new_bucket,
            "base_score": base_score,
            "new_score": new_score,
            "score_delta": round(delta, 4),
            "flip_result": r.get("flip_result", ""),
            "is_extreme_jump": is_extreme_jump,
            "research_only": "YES",
            "built_at": datetime.now(timezone.utc).isoformat(),
        })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = (
    out.groupby(["factor", "is_extreme_jump", "flip_result"])
    .agg(
        races=("race_key", "count"),
        avg_score_delta=("score_delta", "mean"),
    )
    .reset_index()
)

summary["avg_score_delta"] = summary["avg_score_delta"].round(4)

pivot = (
    out.groupby(["factor", "is_extreme_jump"])
    .agg(
        races=("race_key", "count"),
        improved_wins=("flip_result", lambda s: (s == "IMPROVED_WIN").sum()),
        worsened_wins=("flip_result", lambda s: (s == "WORSENED_WIN").sum()),
        improved_places=("flip_result", lambda s: (s == "IMPROVED_PLACE").sum()),
        worsened_places=("flip_result", lambda s: (s == "WORSENED_PLACE").sum()),
        neutral=("flip_result", lambda s: (s == "NEUTRAL").sum()),
        avg_score_delta=("score_delta", "mean"),
    )
    .reset_index()
)

pivot["net_win_gain"] = pivot["improved_wins"] - pivot["worsened_wins"]
pivot["net_place_gain"] = pivot["improved_places"] - pivot["worsened_places"]
pivot["avg_score_delta"] = pivot["avg_score_delta"].round(4)

pivot.to_csv(SUMMARY, index=False)

print("[V6_3_MEDIUM_GUARDRAIL_EXTREME_SCORE_AUDIT_V1] COMPLETE")
print(f"detail={OUT}")
print(f"summary={SUMMARY}")
print(pivot.to_string(index=False))
