from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

inventory = pd.read_csv(
    DATA / "edgeiq_archived_probability_rating_sources_v1.csv"
)

candidate_terms = [
    "probability",
    "fair_price",
    "runner_board",
    "live_runner_board",
    "rating",
    "historical",
    "archive"
]

inventory = inventory[
    inventory["matched_terms"]
    .fillna("")
    .str.contains("|".join(candidate_terms), case=False)
].copy()

records = []

for _, row in inventory.iterrows():

    path = ROOT / row["path"]

    if not path.exists():
        continue

    if path.suffix.lower() != ".csv":
        continue

    try:
        sample = pd.read_csv(
            path,
            nrows=5,
            low_memory=False
        )
    except Exception:
        continue

    cols = [str(c) for c in sample.columns]
    lower = [c.lower() for c in cols]

    probability_cols = [
        c for c in cols
        if "prob" in c.lower()
    ]

    price_cols = [
        c for c in cols
        if "price" in c.lower()
    ]

    rating_cols = [
        c for c in cols
        if "rating" in c.lower()
    ]

    race_cols = [
        c for c in cols
        if any(
            x in c.lower()
            for x in [
                "race",
                "horse",
                "runner",
                "track",
                "date"
            ]
        )
    ]

    score = (
        len(probability_cols) * 5
        + len(price_cols) * 3
        + len(rating_cols) * 3
        + len(race_cols)
    )

    records.append({
        "path": row["path"],
        "filename": row["filename"],
        "score": score,
        "columns": len(cols),
        "probability_cols": ",".join(probability_cols),
        "price_cols": ",".join(price_cols),
        "rating_cols": ",".join(rating_cols),
        "race_identity_cols": ",".join(race_cols)
    })

out = pd.DataFrame(records)

if len(out):
    out = (
        out
        .sort_values(
            ["score", "filename"],
            ascending=[False, True]
        )
        .reset_index(drop=True)
    )

outfile = (
    DATA /
    "edgeiq_archived_probability_rating_candidates_v1.csv"
)

summary = (
    DATA /
    "edgeiq_archived_probability_rating_candidates_summary_v1.csv"
)

out.to_csv(outfile, index=False)

out.head(100).to_csv(summary, index=False)

print("[ARCHIVED_PROBABILITY_RATING_CANDIDATE_SCAN] COMPLETE")
print(f"candidates={len(out)}")
print(f"out={outfile}")
print(f"summary={summary}")
