from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]

LIVE_PATH = ROOT / "public" / "data" / "live_speed_map_v3.csv"
DNA_PATH = ROOT / "public" / "data" / "edgeiq_master_positional_dna_v1.csv"

OUT_PATH = ROOT / "public" / "data" / "edgeiq_master_dna_live_audit_v1.csv"
DIAG_PATH = ROOT / "public" / "data" / "edgeiq_master_dna_live_audit_v1_diagnostics.csv"

SUFFIXES = [
    " NZ",
    " GB",
    " IRE",
    " FR",
    " USA",
    " SAF",
    " GER",
    " JAP",
]

def canon(x):
    if pd.isna(x):
        return ""

    x = str(x).upper().strip()

    x = re.sub(r"\(.*?\)", "", x)

    for s in SUFFIXES:
        if x.endswith(s):
            x = x[:-len(s)]

    x = re.sub(r"[^A-Z0-9]", "", x)

    return x.strip()

print("=" * 80)
print("EDGEIQ MASTER DNA LIVE COVERAGE AUDIT V1")
print("=" * 80)

live = pd.read_csv(LIVE_PATH)
dna = pd.read_csv(DNA_PATH)

live.columns = [c.strip() for c in live.columns]
dna.columns = [c.strip() for c in dna.columns]

live_horse_col = None
dna_horse_col = None

for c in live.columns:
    if c.lower() in ["horse", "horse_name", "runner_name"]:
        live_horse_col = c
        break

for c in dna.columns:
    if c.lower() in ["horse", "horse_name", "runner_name"]:
        dna_horse_col = c
        break

if live_horse_col is None:
    raise Exception("NO LIVE HORSE COLUMN FOUND")

if dna_horse_col is None:
    raise Exception("NO DNA HORSE COLUMN FOUND")

live["canonical_horse"] = live[live_horse_col].apply(canon)
dna["canonical_horse"] = dna[dna_horse_col].apply(canon)

dna_keys = set(dna["canonical_horse"].dropna().unique())

live["dna_match"] = live["canonical_horse"].isin(dna_keys)

merged = live.merge(
    dna,
    on="canonical_horse",
    how="left",
    suffixes=("", "_dna")
)

live_unique = live["canonical_horse"].nunique()
dna_unique = dna["canonical_horse"].nunique()

matched = merged["dna_match"].sum()

match_rate = round((matched / max(len(live), 1)) * 100, 2)

matched_examples = (
    merged.loc[merged["dna_match"] == True, live_horse_col]
    .dropna()
    .astype(str)
    .unique()[:20]
)

missing_examples = (
    merged.loc[merged["dna_match"] == False, live_horse_col]
    .dropna()
    .astype(str)
    .unique()[:50]
)

diag = pd.DataFrame([
    {
        "live_rows": len(live),
        "live_unique_horses": live_unique,
        "dna_unique_horses": dna_unique,
        "matched_live_rows": int(matched),
        "match_rate_pct": match_rate,
    }
])

merged.to_csv(OUT_PATH, index=False)
diag.to_csv(DIAG_PATH, index=False)

print()
print("=" * 80)
print("RESULTS")
print("=" * 80)

print(f"LIVE ROWS: {len(live)}")
print(f"LIVE UNIQUE: {live_unique}")
print(f"DNA HORSES: {dna_unique}")
print(f"MATCHED LIVE ROWS: {matched}")
print(f"MATCH RATE: {match_rate}%")

print()
print("=" * 80)
print("MATCHED EXAMPLES")
print("=" * 80)

for x in matched_examples:
    print(x)

print()
print("=" * 80)
print("MISSING EXAMPLES")
print("=" * 80)

for x in missing_examples:
    print(x)

print()
print("=" * 80)
print("FILES WRITTEN")
print("=" * 80)

print(OUT_PATH)
print(DIAG_PATH)
