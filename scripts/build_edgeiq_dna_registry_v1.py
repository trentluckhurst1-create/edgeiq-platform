from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCES = [
    ("TRACK_DNA", DATA / "edgeiq_track_dna_v1.csv"),
    ("RAIL_DNA", DATA / "edgeiq_rail_dna_v1.csv"),
    ("PREP_DNA", DATA / "edgeiq_spell_prep_dna_v1.csv"),
    ("MARKET_DNA", DATA / "edgeiq_market_dna_v1.csv"),
    ("TDC_DNA", DATA / "edgeiq_track_distance_condition_dna_v1.csv"),
]

frames = []

for dna_type, file in SOURCES:

    if not file.exists():
        continue

    df = pd.read_csv(file, low_memory=False)

    score_col = next(
        (
            c for c in df.columns
            if c.endswith("_score")
        ),
        None,
    )

    band_col = next(
        (
            c for c in df.columns
            if c.endswith("_band")
        ),
        None,
    )

    if score_col is None:
        continue

    keep = pd.DataFrame()

    keep["entity_type"] = df["entity_type"]
    keep["entity_name"] = df["entity_name"]

    keep["dna_type"] = dna_type
    keep["dna_score"] = pd.to_numeric(
        df[score_col],
        errors="coerce"
    )

    keep["dna_band"] = (
        df[band_col]
        if band_col is not None
        else ""
    )

    keep["source_file"] = file.name

    frames.append(keep)

registry = pd.concat(
    frames,
    ignore_index=True
)

registry["built_at"] = datetime.now(
    timezone.utc
).isoformat()

out = DATA / "edgeiq_dna_registry_v1.csv"

registry.to_csv(
    out,
    index=False
)

summary = pd.DataFrame([
    ["status","EDGEIQ_DNA_REGISTRY_V1_BUILT"],
    ["rows",len(registry)],
    ["dna_types",registry["dna_type"].nunique()],
    ["entities",registry["entity_name"].nunique()],
    ["output",str(out)],
])

summary.columns=["metric","value"]

summary.to_csv(
    DATA / "edgeiq_dna_registry_v1_summary.csv",
    index=False
)

print("[DNA_REGISTRY_V1] COMPLETE")
print(f"rows={len(registry)}")
print(f"output={out}")
