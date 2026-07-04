from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT.parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
PROJECTION = DATA / "edgeiq_current_field_projection_v5_2.csv"
RA_RUNS = MODEL_ROOT / "outputs" / "ra_careers" / "ra_horse_runs.csv"
HIST = DATA / "edgeiq_historical_performance_rating_v5_1.csv"

OUT = DATA / "edgeiq_historical_universe_coverage_audit_v1.csv"
SUMMARY = DATA / "edgeiq_historical_universe_coverage_audit_v1_summary.csv"

def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def key(value):
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("’", "").replace("'", "")
    return re.sub(r"[^A-Z0-9]+", "", text)

def read(path):
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)

print("=" * 90)
print("EDGEIQ HISTORICAL UNIVERSE COVERAGE AUDIT V1")
print("=" * 90)

live = read(LIVE)
projection = read(PROJECTION)
ra = read(RA_RUNS)
hist = read(HIST)

live["horse_key_audit"] = live["horse"].map(key)
projection["horse_key_audit"] = projection["horse"].map(key)
ra["horse_key_audit"] = ra["horse"].map(key)
hist["horse_key_audit"] = hist["horse"].map(key)

ra_keys = set(ra["horse_key_audit"])
hist_keys = set(hist["horse_key_audit"])

base_cols = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "race_class",
    "trainer",
    "jockey",
    "live_price",
    "fair_price",
    "edge_pct",
]

for col in base_cols:
    if col not in live.columns:
        live[col] = ""

proj_keep = [
    "horse_key_audit",
    "history_match_status_v5_2",
    "starts_found_v5_2",
    "projection_band_v5_2",
    "projected_rating_v5_2",
    "race_target_rating_v5_2",
    "projection_gap_v5_2",
]
for col in proj_keep:
    if col not in projection.columns:
        projection[col] = ""

audit = live[base_cols + ["horse_key_audit"]].copy()
audit = audit.merge(
    projection[proj_keep].drop_duplicates("horse_key_audit", keep="first"),
    on="horse_key_audit",
    how="left",
)

audit["in_ra_career_runs"] = audit["horse_key_audit"].isin(ra_keys).map(lambda x: "TRUE" if x else "FALSE")
audit["in_historical_performance_v5_1"] = audit["horse_key_audit"].isin(hist_keys).map(lambda x: "TRUE" if x else "FALSE")

audit["coverage_status"] = "OK_HISTORY"
audit.loc[audit["in_ra_career_runs"].eq("FALSE"), "coverage_status"] = "MISSING_RA_CAREER"
audit.loc[
    audit["in_ra_career_runs"].eq("TRUE") & audit["in_historical_performance_v5_1"].eq("FALSE"),
    "coverage_status"
] = "IN_RA_NOT_IN_PERFORMANCE"
audit.loc[
    audit["history_match_status_v5_2"].eq("NO_HISTORY"),
    "coverage_status"
] = "NO_PROJECTION_HISTORY"

audit["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

audit.to_csv(OUT, index=False, encoding="utf-8")

summary_rows = []
def add(section, metric, value):
    summary_rows.append({
        "section": section,
        "metric": metric,
        "value": value,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })

add("overall", "live_rows", len(audit))
add("overall", "unique_live_horses", audit["horse_key_audit"].nunique())
add("overall", "ra_rows", len(ra))
add("overall", "ra_unique_horses", ra["horse_key_audit"].nunique())
add("overall", "historical_rows", len(hist))
add("overall", "historical_unique_horses", hist["horse_key_audit"].nunique())

for status, count in audit["coverage_status"].value_counts().sort_index().items():
    add("coverage_status", status, int(count))

for cls, group in audit.groupby("race_class", dropna=False):
    add("coverage_by_class", clean(cls) or "BLANK", len(group))
    add("missing_ra_by_class", clean(cls) or "BLANK", int(group["in_ra_career_runs"].eq("FALSE").sum()))
    add("no_projection_history_by_class", clean(cls) or "BLANK", int(group["history_match_status_v5_2"].eq("NO_HISTORY").sum()))

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False, encoding="utf-8")

print(f"wrote: {OUT}")
print(f"wrote: {SUMMARY}")
print()
print(summary.to_string(index=False))
print("=" * 90)
