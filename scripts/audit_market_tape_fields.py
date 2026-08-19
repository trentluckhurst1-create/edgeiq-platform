import pandas as pd

df = pd.read_csv(
    r".\public\data\edgeiq_market_tape.csv",
    low_memory=False
)

for col in [
    "timestamp",
    "snapshot_time",
    "move_direction",
    "move_delta"
]:
    if col in df.columns:
        print()
        print(col)
        print(df[col].dropna().head(20).tolist())
