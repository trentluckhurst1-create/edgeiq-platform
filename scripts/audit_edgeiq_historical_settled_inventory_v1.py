import pandas as pd

f = r".\public\data\edgeiq_historical_replay_settled_v1.csv"

df = pd.read_csv(f, low_memory=False)

print("")
print("[ROWS]")
print(len(df))

print("")
print("[COLUMNS]")
for c in df.columns:
    print(c)

if "field_size" in df.columns:
    print("")
    print("[FIELD_SIZE_DISTRIBUTION]")
    print(
        pd.to_numeric(
            df["field_size"],
            errors="coerce"
        )
        .value_counts(dropna=False)
        .sort_index()
        .to_string()
    )

if "track" in df.columns:
    print("")
    print("[TOP_TRACKS]")
    print(
        df["track"]
        .astype(str)
        .value_counts()
        .head(100)
        .to_string()
    )
