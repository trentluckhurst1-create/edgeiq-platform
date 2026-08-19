import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

dna = pd.read_csv(DATA / "edgeiq_runner_dna_ui_feed_v1.csv")

rows = []

for _, r in dna.iterrows():

    def num(v):
        try:
            return float(v)
        except:
            return np.nan

    runner_score = num(r.get("runner_dna_v6_1_score"))

    rows.append({
        "race_date": r.get("race_date"),
        "track": r.get("track"),
        "race_no": r.get("race_no"),
        "horse": r.get("horse"),

        "fair_price": num(r.get("fair_price")),
        "live_price": num(r.get("live_price")),
        "edge_pct": num(r.get("edge_pct")),

        "projection_gap_v6_1":
            num(r.get("projection_gap_V6_1_RESEARCH")),

        "projection_band_v6_1":
            r.get("projection_band_V6_1_RESEARCH"),

        "rating_score":
            num(r.get("rating_score")),

        "runner_dna_score":
            runner_score,

        "runner_dna_band":
            r.get("runner_dna_v6_1_band"),

        "form_score":
            num(r.get("form_score")),

        "distance_score":
            num(r.get("distance_fit_score")),

        "condition_score":
            num(r.get("condition_fit_score")),

        "class_score":
            num(r.get("class_fit_score")),

        "sectional_score":
            num(r.get("sectional_score")),

        "profile_score":
            num(r.get("profile_score")),

        "dna_rank":
            num(r.get("runner_dna_v6_1_rank_in_race"))
    })

out = pd.DataFrame(rows)

out["dna_adjustment_pct"] = np.select(
    [
        out["runner_dna_band"].eq("ELITE"),
        out["runner_dna_band"].eq("STRONG"),
        out["runner_dna_band"].eq("POSITIVE"),
        out["runner_dna_band"].eq("NEGATIVE"),
        out["runner_dna_band"].eq("POOR")
    ],
    [
        8,
        4,
        2,
        -2,
        -5
    ],
    default=0
)

out["research_fair_price"] = np.where(
    out["fair_price"] > 0,
    out["fair_price"] / (1 + out["dna_adjustment_pct"] / 100),
    np.nan
)

summary = pd.DataFrame([
    {
        "metric":"status",
        "value":"PRICE_ENRICHMENT_RESEARCH_V1_BUILT"
    },
    {
        "metric":"rows",
        "value":len(out)
    },
    {
        "metric":"elite",
        "value":int((out.runner_dna_band=="ELITE").sum())
    },
    {
        "metric":"strong",
        "value":int((out.runner_dna_band=="STRONG").sum())
    },
    {
        "metric":"positive",
        "value":int((out.runner_dna_band=="POSITIVE").sum())
    },
    {
        "metric":"built_at",
        "value":datetime.now(timezone.utc).isoformat()
    }
])

out.to_csv(
    DATA / "edgeiq_price_enrichment_research_v1.csv",
    index=False
)

summary.to_csv(
    DATA / "edgeiq_price_enrichment_research_v1_summary.csv",
    index=False
)

print("[PRICE_ENRICHMENT_RESEARCH_V1] COMPLETE")
print(summary)
