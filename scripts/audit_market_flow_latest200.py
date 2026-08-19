import pandas as pd

df = pd.read_csv(
    r".\public\data\edgeiq_market_tape.csv",
    low_memory=False
)

latest = df.tail(200)

cols = [c for c in [
    "track",
    "race_no",
    "race_number",
    "race",
    "horse",
    "move_direction",
    "move_delta",
    "snapshot_time",
    "timestamp"
] if c in latest.columns]

print(latest[cols].to_string())
