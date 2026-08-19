import csv
from pathlib import Path

path = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data\edgeiq_epi_workspace_terminal_feed_v1.csv")

if not path.exists():
    raise SystemExit(f"FILE_NOT_FOUND: {path}")

with path.open("r", encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))

historical_columns = [
    column
    for column in (rows[0].keys() if rows else [])
    if column.lower().startswith("start_")
    or "historical" in column.lower()
]

print(f"ROWS={len(rows)}")
print(f"HISTORICAL_COLUMNS={historical_columns}")

populated_rows = 0
sample_rows = []

for row in rows:
    populated = {
        column: row.get(column)
        for column in historical_columns
        if str(row.get(column) or "").strip()
    }

    if populated:
        populated_rows += 1

        if len(sample_rows) < 10:
            sample_rows.append({
                "race_date": row.get("race_date"),
                "track": row.get("track"),
                "race_no": row.get("race_no"),
                "runner": row.get("runner"),
                **populated,
            })

print(f"ROWS_WITH_HISTORICAL_VALUES={populated_rows}")

for sample in sample_rows:
    print(sample)

print("EPI_WORKSPACE_HISTORICAL_FEED_PROBE_PASS")
