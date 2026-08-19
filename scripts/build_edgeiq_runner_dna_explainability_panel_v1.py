from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_runner_dna_contribution_breakdown_v1.csv"

OUT = DATA / "edgeiq_runner_dna_explainability_panel_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_explainability_panel_v1_summary.csv"

df = pd.read_csv(SRC, dtype=str).fillna("")

built_at = datetime.now(timezone.utc).isoformat()

rows = []

for _, r in df.iterrows():

    rows.append({
        "race_date": r.get("race_date",""),
        "track": r.get("track",""),
        "race_no": r.get("race_no",""),
        "horse": r.get("horse",""),
        "horse_key": r.get("horse_key",""),

        "dna_score": r.get("dna_score",""),
        "dna_band": r.get("dna_band",""),

        "positive_1_factor": r.get("positive_1_factor",""),
        "positive_1_impact": r.get("positive_1_impact",""),

        "positive_2_factor": r.get("positive_2_factor",""),
        "positive_2_impact": r.get("positive_2_impact",""),

        "positive_3_factor": r.get("positive_3_factor",""),
        "positive_3_impact": r.get("positive_3_impact",""),

        "negative_1_factor": r.get("negative_1_factor",""),
        "negative_1_impact": r.get("negative_1_impact",""),

        "negative_2_factor": r.get("negative_2_factor",""),
        "negative_2_impact": r.get("negative_2_impact",""),

        "negative_3_factor": r.get("negative_3_factor",""),
        "negative_3_impact": r.get("negative_3_impact",""),

        "impact_explanation": r.get("impact_explanation",""),

        "dna_breakdown_title": "DNA BREAKDOWN",
        "built_at": built_at
    })

out = pd.DataFrame(rows)
out.to_csv(OUT,index=False)

summary = pd.DataFrame([
    {"metric":"status","value":"RUNNER_DNA_EXPLAINABILITY_PANEL_V1_BUILT"},
    {"metric":"source","value":SRC.name},
    {"metric":"output","value":OUT.name},
    {"metric":"rows","value":len(out)},
    {"metric":"built_at","value":built_at},
])

summary.to_csv(SUMMARY,index=False)

print("[RUNNER_DNA_EXPLAINABILITY_PANEL_V1] COMPLETE")
print(summary.to_string(index=False))

print(
    out[
        [
            "horse",
            "dna_score",
            "dna_band",
            "positive_1_factor",
            "positive_1_impact",
            "negative_1_factor",
            "negative_1_impact"
        ]
    ]
    .head(25)
    .to_string(index=False)
)
