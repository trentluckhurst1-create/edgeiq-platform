from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASE = DATA / "edgeiq_runner_dna_drawer_feed_v1.csv"
PANEL = DATA / "edgeiq_runner_dna_explainability_panel_v1.csv"

OUT = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
SUMMARY = DATA / "edgeiq_runner_dna_drawer_feed_v2_summary.csv"

base = pd.read_csv(BASE, dtype=str).fillna("")
panel = pd.read_csv(PANEL, dtype=str).fillna("")

join_cols = ["race_date", "track", "race_no", "horse"]

merged = base.merge(
    panel,
    on=join_cols,
    how="left",
    suffixes=("", "_panel")
)

def backfill(target, source):
    if target not in merged.columns:
        merged[target] = ""
    if source in merged.columns:
        merged[target] = merged[target].where(merged[target].astype(str).str.strip() != "", merged[source])

backfill("dna_v6_2_score", "dna_score")
backfill("dna_v6_2_band", "dna_band")
backfill("runner_dna_v6_2_narrative", "impact_explanation")
backfill("strongest_factor_v6_2", "positive_1_factor")
backfill("strongest_factor_score_v6_2", "positive_1_impact")
backfill("weakest_factor_v6_2", "negative_1_factor")
backfill("weakest_factor_score_v6_2", "negative_1_impact")

built_at = datetime.now(timezone.utc).isoformat()
merged["built_at_explainability_v2"] = built_at

merged.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "RUNNER_DNA_DRAWER_FEED_V2_BUILT"},
    {"metric": "base_rows", "value": len(base)},
    {"metric": "panel_rows", "value": len(panel)},
    {"metric": "output_rows", "value": len(merged)},
    {"metric": "positive_factor_populated", "value": int((merged["positive_1_factor"].astype(str).str.strip() != "").sum())},
    {"metric": "negative_factor_populated", "value": int((merged["negative_1_factor"].astype(str).str.strip() != "").sum())},
    {"metric": "dna_score_populated", "value": int((merged["dna_v6_2_score"].astype(str).str.strip() != "").sum())},
    {"metric": "dna_band_populated", "value": int((merged["dna_v6_2_band"].astype(str).str.strip() != "").sum())},
    {"metric": "built_at", "value": built_at},
])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_DRAWER_FEED_V2] COMPLETE")
print(summary.to_string(index=False))
print(
    merged[
        [
            "horse",
            "dna_v6_2_score",
            "dna_v6_2_band",
            "positive_1_factor",
            "positive_1_impact",
            "negative_1_factor",
            "negative_1_impact",
        ]
    ].head(20).to_string(index=False)
)
