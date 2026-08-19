from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

FILES = {
    "RACE": DATA / "edgeiq_racingcom_canonical_race_speed_fact_v2_1.csv",
    "RUNNER": DATA / "edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv",
    "SECTIONAL": DATA / "edgeiq_racingcom_canonical_runner_sectional_fact_v2_1.csv",
    "SPLIT": DATA / "edgeiq_racingcom_canonical_runner_split_fact_v2_1.csv",
}


def read_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


for label, path in FILES.items():
    print()
    print("=" * 100)
    print(label)
    print(path)
    print("=" * 100)

    fields, rows = read_rows(path)

    print("ROW COUNT:", len(rows))
    print()
    print("ALL HEADERS:")

    for field in fields:
        print(f"  {field}")

    relevant_fields = [
        field
        for field in fields
        if any(
            token in field.lower()
            for token in (
                "distance",
                "metre",
                "meter",
                "section",
                "marker",
                "time",
                "split",
                "finish",
                "position",
                "race_key",
                "runner_key",
                "horse",
                "name",
            )
        )
    ]

    print()
    print("RELEVANT SAMPLE VALUES:")

    for index, row in enumerate(rows[:5], start=1):
        print()
        print(f"ROW {index}")

        for field in relevant_fields:
            value = str(row.get(field, "")).strip()

            if value:
                print(f"  {field} = {value}")
