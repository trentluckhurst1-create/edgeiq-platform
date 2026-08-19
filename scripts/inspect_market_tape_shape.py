import pandas as pd

df = pd.read_csv(
    r".\public\data\edgeiq_market_tape.csv",
    low_memory=False
)

print("=" * 80)
print("ROWS")
print("=" * 80)
print(len(df))

print("=" * 80)
print("COLUMNS")
print("=" * 80)
for c in df.columns:
    print(c)

print("=" * 80)
print("SAMPLE")
print("=" * 80)
print(df.head(10).to_string())
