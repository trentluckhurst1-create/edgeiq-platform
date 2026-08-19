from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path.cwd()

ELIGIBILITY_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_benchmark_eligibility_fact_v1.csv"
)

OBSERVATION_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_benchmark_observation_fact_v1.csv"
)

OUTPUT_PATH = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "EDGEIQ_BENCHMARK_ACCUMULATION_PREFLIGHT_V1_1.json"
)


def clean(value: object) -> str:
    return str(value or "").strip()


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


eligibility_rows = load_csv(ELIGIBILITY_PATH)
observation_rows = load_csv(OBSERVATION_PATH)

observation_by_id = {
    clean(row.get("benchmark_observation_id")): row
    for row in observation_rows
    if clean(row.get("benchmark_observation_id"))
}

standard_rows = [
    row
    for row in eligibility_rows
    if clean(row.get("benchmark_use_class"))
    == "STANDARD_TIME_ELIGIBLE"
]

joined_rows: list[dict[str, str]] = []
missing_join_ids: list[str] = []

for eligibility_row in standard_rows:
    observation_id = clean(
        eligibility_row.get("benchmark_observation_id")
    )

    observation_row = observation_by_id.get(observation_id)

    if observation_row is None:
        missing_join_ids.append(observation_id)
        continue

    joined_rows.append(
        {
            **observation_row,
            "benchmark_use_class": clean(
                eligibility_row.get("benchmark_use_class")
            ),
            "standard_time_eligible": clean(
                eligibility_row.get("standard_time_eligible")
            ),
            "benchmark_eligibility_id": clean(
                eligibility_row.get("benchmark_eligibility_id")
            ),
            "eligibility_source_observation_sha256": clean(
                eligibility_row.get("source_observation_sha256")
            ),
        }
    )


DIMENSIONS = [
    "track_name",
    "course_name",
    "surface",
    "official_distance_metres",
    "track_condition",
]


def dimension_summary(
    rows: list[dict[str, str]],
    field: str,
) -> dict[str, object]:
    values = [
        clean(row.get(field))
        for row in rows
    ]

    populated = [
        value
        for value in values
        if value
    ]

    counts = Counter(populated)

    return {
        "row_count": len(rows),
        "populated_count": len(populated),
        "blank_count": len(rows) - len(populated),
        "distinct_count": len(counts),
        "distinct_values": dict(
            sorted(
                counts.items(),
                key=lambda item: item[0],
            )
        ),
    }


dimension_coverage = {
    field: dimension_summary(joined_rows, field)
    for field in DIMENSIONS
}

group_signatures = Counter()

for row in joined_rows:
    signature = "|".join(
        [
            clean(row.get("track_name")),
            clean(row.get("course_name")),
            clean(row.get("surface")),
            clean(row.get("official_distance_metres")),
            clean(row.get("track_condition")),
        ]
    )
    group_signatures[signature] += 1

joined_examples = []

for row in joined_rows[:10]:
    joined_examples.append(
        {
            "benchmark_observation_id": clean(
                row.get("benchmark_observation_id")
            ),
            "race_key": clean(row.get("race_key")),
            "track_name": clean(row.get("track_name")),
            "course_name": clean(row.get("course_name")),
            "surface": clean(row.get("surface")),
            "official_distance_metres": clean(
                row.get("official_distance_metres")
            ),
            "track_condition": clean(
                row.get("track_condition")
            ),
            "winner_race_time_seconds": clean(
                row.get("winner_race_time_seconds")
            ),
        }
    )

payload = {
    "audit_name": (
        "EDGEIQ Benchmark Accumulation "
        "Input Preflight V1.1"
    ),
    "status": (
        "PASS"
        if len(joined_rows) == len(standard_rows)
        and not missing_join_ids
        else "FAIL"
    ),
    "join_key": "benchmark_observation_id",
    "counts": {
        "eligibility_rows": len(eligibility_rows),
        "observation_rows": len(observation_rows),
        "standard_time_eligible_rows": len(standard_rows),
        "joined_standard_rows": len(joined_rows),
        "missing_join_rows": len(missing_join_ids),
    },
    "missing_join_ids": missing_join_ids,
    "dimension_coverage": dimension_coverage,
    "candidate_benchmark_groups": {
        "group_count": len(group_signatures),
        "groups": dict(
            sorted(
                group_signatures.items(),
                key=lambda item: item[0],
            )
        ),
    },
    "joined_examples": joined_examples,
}

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_PATH.write_text(
    json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    )
    + "\n",
    encoding="utf-8",
)

print(
    "EDGEIQ_BENCHMARK_ACCUMULATION_PREFLIGHT_V1_1_"
    + payload["status"]
)

print()
print("Join:")
print("  join_key: benchmark_observation_id")

for key, value in payload["counts"].items():
    print(f"  {key}: {value}")

print()
print("Dimension coverage:")

for field, summary in dimension_coverage.items():
    print(f"  {field}:")
    print(
        f"    populated={summary['populated_count']}"
    )
    print(
        f"    blank={summary['blank_count']}"
    )
    print(
        f"    distinct={summary['distinct_count']}"
    )
    print(
        "    values="
        + json.dumps(
            summary["distinct_values"],
            ensure_ascii=False,
        )
    )

print()
print("Candidate benchmark groups:")
print(f"  group_count: {len(group_signatures)}")

for signature, count in sorted(group_signatures.items()):
    print(f"  {signature}: {count}")

print()
print("Joined examples:")
print(
    json.dumps(
        joined_examples,
        indent=2,
        ensure_ascii=False,
    )
)

if payload["status"] != "PASS":
    raise SystemExit(1)
