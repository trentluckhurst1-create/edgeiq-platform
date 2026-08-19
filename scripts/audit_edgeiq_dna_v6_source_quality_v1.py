import pandas as pd

df = pd.read_csv(
    r".\public\data\edgeiq_racingcom_results_warehouse_full_v1.csv",
    low_memory=False
)

print()
print("=== DISTANCE ===")
print(df["distance"].value_counts(dropna=False).head(50))

print()
print("=== CONDITION ===")
print(df["trackCondition"].value_counts(dropna=False))

print()
print("=== CLASS ===")
print(df["raceClass"].value_counts(dropna=False).head(100))

print()
print("=== FINISH POSITION SAMPLE ===")
print(df["finishPosition"].dropna().head(50).tolist())
