from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"

FEED = DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv"
CONFLICTS = DATA / "edgeiq_historical_epi_lookup_conflicts_v1.csv"
OUT = (
    ROOT
    / "docs"
    / "full-product-implementation"
    / "FORM_GUIDE_HISTORICAL_EPI_GOVERNED_RECOVERY_POST_BUILD_AUDIT.txt"
)

if not FEED.exists():
    raise SystemExit(f"FEED_NOT_FOUND={FEED}")

with FEED.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
    rows = list(csv.DictReader(handle))

start_fields = [f"start_{index}" for index in range(10, 0, -1)]
total_slots = len(rows) * len(start_fields)

populated = 0
blank = 0
rows_with_history = 0
rows_without_history = 0
same_duplicate_sources = 0

for row in rows:
    values = [str(row.get(field, "") or "").strip() for field in start_fields]
    row_populated = sum(bool(value) for value in values)

    populated += row_populated
    blank += len(values) - row_populated

    if row_populated:
        rows_with_history += 1
    else:
        rows_without_history += 1

    source = str(row.get("source", "") or "")
    if "same_rating_duplicates_collapsed" in source:
        same_duplicate_sources += 1

conflict_rows = []

if CONFLICTS.exists():
    with CONFLICTS.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        conflict_rows = list(csv.DictReader(handle))

report = [
    "EDGEIQ FORM GUIDE HISTORICAL EPI GOVERNED RECOVERY POST-BUILD AUDIT",
    "=" * 100,
    "",
    f"FEED={FEED}",
    f"ROWS={len(rows)}",
    f"HISTORICAL_START_SLOTS={total_slots}",
    f"POPULATED_START_SLOTS={populated}",
    f"BLANK_START_SLOTS={blank}",
    f"ROWS_WITH_AT_LEAST_ONE_HISTORICAL_EPI={rows_with_history}",
    f"ROWS_WITHOUT_HISTORICAL_EPI={rows_without_history}",
    f"CONFLICTING_LOOKUPS_REJECTED={len(conflict_rows)}",
    f"CONFLICT_FILE={CONFLICTS}",
    "",
]

if len(conflict_rows) == 76:
    decision = "PASS_EXPECTED_76_CONFLICTS_REJECTED"
else:
    decision = f"REVIEW_CONFLICT_COUNT_EXPECTED_76_ACTUAL_{len(conflict_rows)}"

report.append(f"DECISION={decision}")
report.append("")

if conflict_rows:
    report.append("CONFLICT SAMPLE")
    report.append("-" * 100)

    for row in conflict_rows[:20]:
        report.append(
            " | ".join(
                [
                    row.get("horse_key", ""),
                    row.get("race_date", ""),
                    row.get("canonical_track", ""),
                    f'{row.get("distance", "")}m',
                    row.get("candidate_ratings", ""),
                    row.get("source_files", ""),
                ]
            )
        )

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print(f"WROTE={OUT}")

if len(conflict_rows) != 76:
    raise SystemExit(1)

print("EDGEIQ_FORM_GUIDE_HISTORICAL_EPI_GOVERNED_RECOVERY_POST_BUILD_AUDIT_PASS")
