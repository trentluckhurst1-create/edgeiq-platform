import csv
import json
from pathlib import Path

path = Path(
    r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
    r"\public\data\edgeiq_epi_workspace_terminal_feed_v1.csv"
)

with path.open("r", encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))

if not rows:
    raise SystemExit("NO_ROWS")

columns = list(rows[0].keys())

runner_candidates = [
    "runner",
    "runner_name",
    "runnerName",
    "horse",
    "horse_name",
    "horseName",
]

runner_column = next(
    (column for column in runner_candidates if column in columns),
    None,
)

start_columns = [f"start_{number}" for number in range(10, 0, -1)]

def numeric(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None

rows_with_numeric_history = 0
numeric_tiles = 0
context_tiles = 0
samples = []

for row in rows:
    populated = {}

    for column in start_columns:
        value = numeric(row.get(column))

        if value is None:
            continue

        numeric_tiles += 1
        populated[column] = value

        context_value = str(row.get(f"{column}_context") or "").strip()

        if context_value:
            try:
                context = json.loads(context_value)
                context_tiles += 1
            except json.JSONDecodeError:
                context = {"INVALID_CONTEXT": context_value}

            populated[f"{column}_context"] = context

    if populated:
        rows_with_numeric_history += 1

        if len(samples) < 10:
            samples.append(
                {
                    "race_date": row.get("race_date"),
                    "track": row.get("track"),
                    "race_no": row.get("race_no"),
                    "runner_column": runner_column,
                    "runner": row.get(runner_column) if runner_column else None,
                    **populated,
                }
            )

print(f"ROWS={len(rows)}")
print(f"COLUMNS={columns}")
print(f"RUNNER_COLUMN={runner_column}")
print(f"ROWS_WITH_NUMERIC_HISTORY={rows_with_numeric_history}")
print(f"NUMERIC_HISTORICAL_TILES={numeric_tiles}")
print(f"CONTEXT_TILES={context_tiles}")

for sample in samples:
    print(sample)

if numeric_tiles == 0:
    raise SystemExit("NO_NUMERIC_HISTORICAL_EPI_VALUES")

print("EPI_WORKSPACE_NUMERIC_HISTORICAL_FEED_PASS")
