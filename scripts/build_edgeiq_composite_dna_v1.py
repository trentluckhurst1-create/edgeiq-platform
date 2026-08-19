from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

src = DATA / "edgeiq_dna_registry_v1.csv"

df = pd.read_csv(src, low_memory=False)

pivot = (
    df.pivot_table(
        index=["entity_type","entity_name"],
        columns="dna_type",
        values="dna_score",
        aggfunc="mean"
    )
    .reset_index()
)

weights = {
    "TRACK_DNA":0.25,
    "MARKET_DNA":0.25,
    "PREP_DNA":0.20,
    "RAIL_DNA":0.10,
    "TDC_DNA":0.20,
}

for col in weights:
    if col not in pivot.columns:
        pivot[col] = 0

pivot["weighted_score"] = (
    pivot["TRACK_DNA"] * .25 +
    pivot["MARKET_DNA"] * .25 +
    pivot["PREP_DNA"] * .20 +
    pivot["RAIL_DNA"] * .10 +
    pivot["TDC_DNA"] * .20
)

pivot["average_score"] = (
    pivot[
        list(weights.keys())
    ]
    .mean(axis=1)
)

pivot["available_dna_count"] = (
    pivot[
        list(weights.keys())
    ]
    .gt(0)
    .sum(axis=1)
)

def band(x):

    if x >= 85:
        return "ELITE"

    if x >= 72:
        return "STRONG"

    if x >= 60:
        return "POSITIVE"

    if x >= 45:
        return "NEUTRAL"

    if x >= 32:
        return "NEGATIVE"

    return "POOR"

pivot["composite_score"] = (
    pivot["weighted_score"]
    .round(2)
)

pivot["composite_band"] = (
    pivot["composite_score"]
    .apply(band)
)

pivot["built_at"] = datetime.now(
    timezone.utc
).isoformat()

out = DATA / "edgeiq_composite_dna_v1.csv"

pivot.to_csv(
    out,
    index=False
)

summary = pd.DataFrame([
    ["status","EDGEIQ_COMPOSITE_DNA_V1_BUILT"],
    ["rows",len(pivot)],
    ["elite",(pivot["composite_band"]=="ELITE").sum()],
    ["strong",(pivot["composite_band"]=="STRONG").sum()],
    ["positive",(pivot["composite_band"]=="POSITIVE").sum()],
    ["output",str(out)],
])

summary.columns=["metric","value"]

summary.to_csv(
    DATA / "edgeiq_composite_dna_v1_summary.csv",
    index=False
)

print("[COMPOSITE_DNA_V1] COMPLETE")
print(f"rows={len(pivot)}")
