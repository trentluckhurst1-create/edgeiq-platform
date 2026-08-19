import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

INTEL = DATA / "edgeiq_intelligence_score_engine_v1.csv"
DNA_CANDIDATES = [
    DATA / "edgeiq_live_runner_dna_v6_2.csv",
    DATA / "edgeiq_runner_dna_v6_2.csv",
]

OUT = DATA / "edgeiq_intelligence_score_engine_v1_dna_join_audit.csv"

if not INTEL.exists():
    raise FileNotFoundError(f"Missing input: {INTEL}")

intel = pd.read_csv(INTEL, dtype=str).fillna("")

dna_path = None
for p in DNA_CANDIDATES:
    if p.exists():
        dna_path = p
        break

if dna_path is None:
    raise FileNotFoundError("No DNA V6.2 file found.")

dna = pd.read_csv(dna_path, dtype=str).fillna("")

def norm(x):
    return "".join(ch for ch in str(x).upper() if ch.isalnum())

intel["horse_key_join"] = intel["horse"].map(norm)
dna["horse_key_join"] = dna["horse"].map(norm) if "horse" in dna.columns else ""

merged = intel.merge(
    dna[["horse_key_join"]].drop_duplicates(),
    on="horse_key_join",
    how="left",
    indicator=True
)

matched = int((merged["_merge"] == "both").sum())
unmatched = int((merged["_merge"] == "left_only").sum())

rows = [
    {"metric": "status", "value": "DNA_JOIN_AUDIT_BUILT"},
    {"metric": "dna_source", "value": str(dna_path)},
    {"metric": "intel_rows", "value": len(intel)},
    {"metric": "dna_rows", "value": len(dna)},
    {"metric": "matched", "value": matched},
    {"metric": "unmatched", "value": unmatched},
    {"metric": "match_rate_pct", "value": round((matched / len(intel)) * 100, 2) if len(intel) else 0},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
]

pd.DataFrame(rows).to_csv(OUT, index=False)

print("[INTELLIGENCE_SCORE_ENGINE_V1_DNA_JOIN_AUDIT] COMPLETE")
print(f"dna_source={dna_path}")
print(f"out={OUT}")
print(pd.DataFrame(rows).to_string(index=False))
