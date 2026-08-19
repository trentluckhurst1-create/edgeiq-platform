import pandas as pd

path = r".\public\data\all_horse_runs_rated.csv"

df = pd.read_csv(path, dtype=str, low_memory=False)

print("=" * 100)
print("COLUMN COUNT")
print("=" * 100)
print(len(df.columns))

print()
print("=" * 100)
print("FIRST 120 COLUMNS")
print("=" * 100)

for i, c in enumerate(df.columns[:120]):
    print(f"{i:03d} | {c}")

print()
print("=" * 100)
print("POSITIONAL / PACE COLUMNS")
print("=" * 100)

keywords = [
    "in_run",
    "position",
    "settle",
    "800",
    "600",
    "400",
    "200",
    "margin",
    "sectional",
    "pace",
    "run_style",
]

for c in df.columns:
    cl = c.lower()

    if any(k in cl for k in keywords):
        print(c)

print()
print("=" * 100)
print("SAMPLE ROW")
print("=" * 100)

cols = [c for c in df.columns if any(
    k in c.lower()
    for k in [
        "horse",
        "in_run",
        "position",
        "800",
        "600",
        "400",
        "200",
        "margin",
        "sectional",
    ]
)]

print(df[cols].head(5).to_string())
