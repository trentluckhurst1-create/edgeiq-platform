from pathlib import Path
import pandas as pd
import re

PUBLIC = Path(r"public/data")

LIVE = PUBLIC / "live_speed_map_v3.csv"
DNA = PUBLIC / "edgeiq_positional_dna_engine_v2.csv"

def clean(x):
    return re.sub(r"\s+", " ", str(x or "").upper().strip())

def compact(x):
    return re.sub(r"[^A-Z0-9]", "", clean(x))

live = pd.read_csv(LIVE, dtype=str).fillna("")
dna = pd.read_csv(DNA, dtype=str).fillna("")

live["compact"] = live["horse"].map(compact)
dna["compact"] = dna["horse"].map(compact)

live_keys = set(live["compact"])
dna_keys = set(dna["compact"])

matched = live_keys & dna_keys
missing = live_keys - dna_keys

print("=" * 100)
print("EDGEIQ DNA MATCH AUDIT")
print("=" * 100)

print()
print(f"LIVE RUNNERS: {len(live_keys)}")
print(f"DNA HORSES: {len(dna_keys)}")
print(f"MATCHED: {len(matched)}")
print(f"MISSING: {len(missing)}")

print()
print("=" * 100)
print("MATCH RATE")
print("=" * 100)

rate = round(len(matched) / max(len(live_keys),1) * 100, 2)
print(f"{rate}%")

print()
print("=" * 100)
print("MISSING LIVE RUNNERS")
print("=" * 100)

for x in sorted(list(missing))[:120]:
    print(x)
