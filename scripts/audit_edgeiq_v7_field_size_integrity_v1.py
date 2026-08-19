import pandas as pd
from pathlib import Path

f = Path(r".\public\data\edgeiq_probability_research_v7_candidate_t575.csv")

df = pd.read_csv(f, low_memory=False)

print("")
print("[FIELD_SIZE_NULLS]")
print(df["field_size"].isna().sum())

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

print("")
print("[TOP_ROWS]")
print(
    df[
        [
            "race_date",
            "track",
            "race_no",
            "horse",
            "field_size"
        ]
    ]
    .head(20)
    .to_string(index=False)
)
