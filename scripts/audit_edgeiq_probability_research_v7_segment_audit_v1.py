from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_probability_research_v7_candidate_t575.csv"

OUT = DATA / "edgeiq_probability_research_v7_segment_audit_v1.csv"
SUMMARY = DATA / "edgeiq_probability_research_v7_segment_audit_v1_summary.csv"

print("[PROBABILITY_RESEARCH_V7_SEGMENT_AUDIT_V1] START")

df = pd.read_csv(SRC, low_memory=False)

df["_prob"] = pd.to_numeric(
    df["replay_probability_temperature6_v3_3"],
    errors="coerce"
)

if "_prob" not in df:
    raise RuntimeError("Probability column missing")

df["_fair"] = np.where(
    df["_prob"] > 0,
    1 / df["_prob"],
    np.nan
)

df["_won"] = pd.to_numeric(
    df["won"],
    errors="coerce"
).fillna(0)

df["field_size"] = pd.to_numeric(
    df["field_size"],
    errors="coerce"
)

eps = 1e-12
p = df["_prob"].clip(eps, 1 - eps)

df["_log_loss"] = -(
    df["_won"] * np.log(p) +
    (1 - df["_won"]) * np.log(1 - p)
)

df["_brier"] = (
    p - df["_won"]
) ** 2

df["field_bucket"] = pd.cut(
    df["field_size"],
    bins=[0,5,8,10,12,14,30],
    labels=[
        "1-5",
        "6-8",
        "9-10",
        "11-12",
        "13-14",
        "15+"
    ]
)

df["prob_bucket"] = pd.cut(
    df["_prob"],
    bins=[0,0.02,0.05,0.10,0.15,0.20,0.30,1.00],
    labels=[
        "0-2%",
        "2-5%",
        "5-10%",
        "10-15%",
        "15-20%",
        "20-30%",
        "30%+"
    ]
)

df["price_bucket"] = pd.cut(
    df["_fair"],
    bins=[0,2,3,5,10,20,1000],
    labels=[
        "<$2",
        "$2-$3",
        "$3-$5",
        "$5-$10",
        "$10-$20",
        "$20+"
    ]
)

records = []

for group_name, col in [
    ("FIELD_SIZE", "field_bucket"),
    ("PROBABILITY", "prob_bucket"),
    ("PRICE", "price_bucket"),
    ("TRACK", "track")
]:

    g = (
        df.groupby(col, dropna=False)
        .agg(
            rows=("horse", "count"),
            winners=("_won", "sum"),
            avg_probability=("_prob", "mean"),
            avg_fair_price=("_fair", "mean"),
            avg_log_loss=("_log_loss", "mean"),
            avg_brier=("_brier", "mean")
        )
        .reset_index()
    )

    g["segment_type"] = group_name
    g["segment"] = g[col].astype(str)

    records.append(
        g[
            [
                "segment_type",
                "segment",
                "rows",
                "winners",
                "avg_probability",
                "avg_fair_price",
                "avg_log_loss",
                "avg_brier"
            ]
        ]
    )

out = pd.concat(records, ignore_index=True)

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "built_at":
        datetime.now(timezone.utc).isoformat(),
    "rows":
        len(df),
    "races":
        (
            pd.to_datetime(df["race_date"], errors="coerce").dt.date.astype("string") +
            "|" +
            df["track"].astype(str) +
            "|" +
            df["race_no"].astype(str)
        ).nunique(),
    "segments":
        len(out),
    "status":
        "PROBABILITY_RESEARCH_V7_SEGMENT_AUDIT_COMPLETE"
}])

summary.to_csv(SUMMARY, index=False)

print("[PROBABILITY_RESEARCH_V7_SEGMENT_AUDIT_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print("")
print(out.head(50).to_string(index=False))
print("")
print(summary.to_string(index=False))
