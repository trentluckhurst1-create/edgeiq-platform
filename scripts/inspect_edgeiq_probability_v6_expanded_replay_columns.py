import pandas as pd
from pathlib import Path

f = Path(r".\public\data\edgeiq_probability_v6_expanded_replay_v1.csv")

df = pd.read_csv(f, nrows=5, low_memory=False)

print("")
print("[COLUMNS]")
for c in df.columns:
    print(c)

print("")
print("[SAMPLE]")
print(df.head().to_string())
