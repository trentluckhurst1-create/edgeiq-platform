from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_dna_registry_v2.csv"
SUMMARY = DATA / "edgeiq_dna_registry_v2_summary.csv"

SOURCES = [
    {
        "dna_type": "TRACK_DNA",
        "file": DATA / "edgeiq_track_dna_v1.csv",
        "score": "track_dna_score",
        "band": "track_dna_band",
        "key_cols": ["track"],
        "starts": "starts",
        "wins": "wins",
        "places": "places",
    },
    {
        "dna_type": "RAIL_DNA",
        "file": DATA / "edgeiq_rail_dna_v1.csv",
        "score": "rail_dna_score",
        "band": "rail_dna_band",
        "key_cols": ["rail_bucket"],
        "starts": "starts",
        "wins": "wins",
        "places": "places",
    },
    {
        "dna_type": "PREP_DNA",
        "file": DATA / "edgeiq_spell_prep_dna_v1.csv",
        "score": "spell_prep_dna_score",
        "band": "spell_prep_dna_band",
        "key_cols": ["prep_bucket"],
        "starts": "starts",
        "wins": "wins",
        "places": "places",
    },
    {
        "dna_type": "MARKET_DNA",
        "file": DATA / "edgeiq_market_dna_v1.csv",
        "score": "market_dna_score",
        "band": "market_dna_band",
        "key_cols": ["sp_bucket"],
        "starts": "starts",
        "wins": "wins",
        "places": "places",
    },
    {
        "dna_type": "TDC_DNA",
        "file": DATA / "edgeiq_track_distance_condition_dna_v1.csv",
        "score": "track_distance_condition_dna_score",
        "band": "track_distance_condition_dna_band",
        "key_cols": ["track", "distance_bucket", "condition_bucket"],
        "starts": "starts",
        "wins": "wins",
        "places": "places",
    },
]

frames = []
built_at = datetime.now(timezone.utc).isoformat()

for src in SOURCES:
    path = src["file"]
    if not path.exists():
        print(f"[SKIP] missing {path.name}")
        continue

    df = pd.read_csv(path, low_memory=False)

    required = ["entity_type", "entity_name", src["score"], src["band"]]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"[SKIP] {path.name} missing {missing}")
        continue

    out = pd.DataFrame()
    out["entity_type"] = df["entity_type"].astype(str).str.strip()
    out["entity_name"] = df["entity_name"].astype(str).str.strip()
    out["dna_type"] = src["dna_type"]

    key_cols = [c for c in src["key_cols"] if c in df.columns]

    if key_cols:
        out["profile_key"] = df[key_cols].astype(str).agg("|".join, axis=1)
    else:
        out["profile_key"] = "OVERALL"

    out["profile_type"] = src["dna_type"] + "::" + out["profile_key"]

    out["dna_score"] = pd.to_numeric(df[src["score"]], errors="coerce")
    out["dna_band"] = df[src["band"]].astype(str).str.strip()

    out["starts"] = pd.to_numeric(df[src["starts"]], errors="coerce") if src["starts"] in df.columns else 0
    out["wins"] = pd.to_numeric(df[src["wins"]], errors="coerce") if src["wins"] in df.columns else 0
    out["places"] = pd.to_numeric(df[src["places"]], errors="coerce") if src["places"] in df.columns else 0

    out["source_file"] = path.name
    out["built_at"] = built_at

    out = out[
        (out["entity_type"] != "") &
        (out["entity_name"] != "") &
        (out["entity_name"].str.lower() != "nan") &
        (out["dna_score"].notna())
    ]

    frames.append(out)

registry = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

registry.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "EDGEIQ_DNA_REGISTRY_V2_BUILT"],
    ["rows", len(registry)],
    ["dna_types", registry["dna_type"].nunique() if len(registry) else 0],
    ["entities", registry[["entity_type", "entity_name"]].drop_duplicates().shape[0] if len(registry) else 0],
    ["profile_keys", registry["profile_key"].nunique() if len(registry) else 0],
    ["output", str(OUT)],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[DNA_REGISTRY_V2] COMPLETE")
print(f"rows={len(registry)}")
print(f"output={OUT}")
