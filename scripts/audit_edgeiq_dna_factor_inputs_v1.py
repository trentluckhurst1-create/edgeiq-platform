from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DNA = DATA / "edgeiq_live_runner_dna_v6_2.csv"
FACTOR = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"

dna = pd.read_csv(DNA, dtype=str).fillna("")
factor = pd.read_csv(FACTOR, dtype=str).fillna("")

print("\nDNA columns")
print(sorted(dna.columns.tolist()))

print("\nFACTOR columns")
print(sorted(factor.columns.tolist()))
