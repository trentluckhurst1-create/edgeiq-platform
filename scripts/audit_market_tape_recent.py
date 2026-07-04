import pandas as pd

df = pd.read_csv(
    r".\public\data\edgeiq_market_tape.csv",
    low_memory=False
)

print("=" * 80)
print("TAPE COLUMNS")
print("=" * 80)

for c in df.columns:
    print(c)

print("=" * 80)
print("LAST 20 ROWS")
print("=" * 80)

print(df.tail(20).to_string())
