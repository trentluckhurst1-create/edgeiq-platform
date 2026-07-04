import pandas as pd
from pathlib import Path

p = Path("public/data/edgeiq_pricing_replay_spine_v3_1_reconstructed.csv")

df = pd.read_csv(
    p,
    nrows=5,
    low_memory=False
)

print("")
print("[COLUMNS]")
for c in df.columns:
    print(c)

print("")
print("[ROW COUNT SAMPLE]")
print(df.head().to_string())
