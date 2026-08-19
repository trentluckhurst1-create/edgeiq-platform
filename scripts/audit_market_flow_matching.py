import pandas as pd

df = pd.read_csv(
    r".\public\data\edgeiq_market_tape.csv",
    low_memory=False
)

print("=" * 80)
print("TRACK VALUES")
print("=" * 80)

if "track" in df.columns:
    print(df["track"].dropna().astype(str).head(20).tolist())

print()
print("=" * 80)
print("RACE VALUES")
print("=" * 80)

race_col = None

for c in ["race_no","race_number","race"]:
    if c in df.columns:
        race_col = c
        break

if race_col:
    print("USING:", race_col)
    print(df[race_col].dropna().astype(str).head(20).tolist())

print()
print("=" * 80)
print("MOVE DIRECTION VALUES")
print("=" * 80)

if "move_direction" in df.columns:
    print(df["move_direction"].dropna().astype(str).value_counts().head(20))

print()
print("=" * 80)
print("LATEST 30 ROWS")
print("=" * 80)

print(df.tail(30).to_string())
