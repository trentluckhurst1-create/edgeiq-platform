from __future__ import annotations

import pandas as pd
from pathlib import Path

DATA = ROOT / "public" / "data"
df = pd.read_csv(DATA / "ratings_audit_elite_v3.csv", low_memory=False)

print("PACE MATCHED:", len(df), "of", len(df))
print()
print("STYLE DISTRIBUTION:")
print(df["runner_style"].value_counts(dropna=False))
print()
print("PACE PRESSURE DISTRIBUTION:")
print(df["pressure_index"].value_counts(dropna=False).sort_index())
print()
print("MATCHED SAMPLE:")
print(df[[
    "race_date",
    "track",
    "race_no",
    "horse",
    "runner_style",
    "runs_used",
    "official_runs_found",
    "pressure_index",
    "leader_probability",
    "collapse_probability",
    "pace_adjusted_rating",
    "elite_rated_price",
]].head(60).to_string(index=False))
