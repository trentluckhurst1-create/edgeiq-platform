from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

SEARCH_TERMS = [
    "probability",
    "fair_price",
    "live_runner_board",
    "runner_board",
    "calibration",
    "replay",
    "rating",
    "v6_1",
    "v5",
    "price",
    "edge",
    "market",
    "historical",
    "archive",
    "current"
]

records = []

for folder in [DATA, SCRIPTS]:
    if not folder.exists():
        continue

    for p in folder.rglob("*"):
        if not p.is_file():
            continue

        name = p.name.lower()

        matches = [
            t for t in SEARCH_TERMS
            if t in name
        ]

        if not matches:
            continue

        try:
            size = p.stat().st_size
            modified = datetime.fromtimestamp(
                p.stat().st_mtime,
                timezone.utc
            ).isoformat()
        except Exception:
            size = None
            modified = None

        records.append({
            "path": str(p.relative_to(ROOT)),
            "filename": p.name,
            "extension": p.suffix.lower(),
            "size_bytes": size,
            "modified_utc": modified,
            "matched_terms": ",".join(matches)
        })

df = pd.DataFrame(records)

if len(df):
    df = (
        df
        .sort_values(
            ["matched_terms", "filename"],
            ascending=[True, True]
        )
        .reset_index(drop=True)
    )

out = DATA / "edgeiq_archived_probability_rating_sources_v1.csv"
summary = DATA / "edgeiq_archived_probability_rating_sources_summary_v1.csv"

df.to_csv(out, index=False)

if len(df):
    summary_df = (
        df.assign(term=df["matched_terms"].str.split(","))
          .explode("term")
          .groupby("term")
          .agg(
              files=("filename", "count")
          )
          .reset_index()
          .sort_values(
              "files",
              ascending=False
          )
    )
else:
    summary_df = pd.DataFrame(
        columns=["term", "files"]
    )

summary_df.to_csv(summary, index=False)

print("[ARCHIVED_PROBABILITY_RATING_SOURCE_AUDIT] COMPLETE")
print(f"files_found={len(df)}")
print(f"out={out}")
print(f"summary={summary}")
