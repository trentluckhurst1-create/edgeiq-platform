from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path.cwd()

ELIGIBILITY = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_benchmark_eligibility_fact_v1.csv"
)

OBSERVATION = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_benchmark_observation_fact_v1.csv"
)

OUTPUT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "EDGEIQ_BENCHMARK_ACCUMULATION_PREFLIGHT_V1.json"
)


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        headers = list(reader.fieldnames or [])

    return headers, rows


eligibility_headers, eligibility_rows = load_csv(ELIGIBILITY)
observation_headers, observation_rows = load_csv(OBSERVATION)

observation_by_id = {
    row.get("observation_id", ""): row
    for row in observation_rows
    if row.get("observation_id", "")
}

standard_rows = [
    row
    for row in eligibility_rows
    if row.get("benchmark_use_class", "")
    == "STANDARD_TIME_ELIGIBLE"
]

joined_examples: list[dict[str, object]] = []

for eligibility_row in standard_rows[:5]:
    observation_id = eligibility_row.get(
        "observation_id",
        "",
    )

    observation_row = observation_by_id.get(
        observation_id,
        {},
    )

    joined_examples.append(
        {
            "observation_id": observation_id,
            "eligibility_row": eligibility_row,
            "observation_row": observation_row,
        }
    )

candidate_fields = [
    "observation_id",
    "race_key",
    "track_code",
    "track_name",
    "track",
    "course",
    "course_name",
    "surface",
    "official_distance_metres",
    "distance_metres",
    "track_condition",
    "track_condition_code",
    "benchmark_use_class",
    "standard_time_eligible",
]

field_coverage: dict[str, dict[str, int]] = {}

for field in candidate_fields:
    eligibility_non_blank = sum(
        1
        for row in eligibility_rows
        if str(row.get(field, "")).strip()
    )

    observation_non_blank = sum(
        1
        for row in observation_rows
        if str(row.get(field, "")).strip()
    )

    field_coverage[field] = {
        "eligibility_non_blank": eligibility_non_blank,
        "observation_non_blank": observation_non_blank,
    }

payload = {
    "audit_name": (
        "EDGEIQ Benchmark Accumulation Fact V1 Preflight"
    ),
    "status": "COMPLETE",
    "eligibility_source": str(
        ELIGIBILITY.relative_to(ROOT)
    ),
    "observation_source": str(
        OBSERVATION.relative_to(ROOT)
    ),
    "eligibility_headers": eligibility_headers,
    "observation_headers": observation_headers,
    "counts": {
        "eligibility_rows": len(eligibility_rows),
        "observation_rows": len(observation_rows),
        "standard_time_eligible_rows": len(standard_rows),
        "joined_standard_rows": sum(
            1
            for row in standard_rows
            if row.get("observation_id", "")
            in observation_by_id
        ),
    },
    "candidate_field_coverage": field_coverage,
    "standard_time_join_examples": joined_examples,
}

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT.write_text(
    json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    )
    + "\n",
    encoding="utf-8",
)

print(
    "EDGEIQ_BENCHMARK_ACCUMULATION_PREFLIGHT_V1_COMPLETE"
)
print()
print("Eligibility headers:")
for header in eligibility_headers:
    print(f"  {header}")

print()
print("Observation headers:")
for header in observation_headers:
    print(f"  {header}")

print()
print("Counts:")
for key, value in payload["counts"].items():
    print(f"  {key}: {value}")

print()
print("Candidate field coverage:")
for field, counts in field_coverage.items():
    print(
        f"  {field}: "
        f"eligibility={counts['eligibility_non_blank']}, "
        f"observation={counts['observation_non_blank']}"
    )

print()
print("Joined STANDARD_TIME_ELIGIBLE examples:")
print(
    json.dumps(
        joined_examples,
        indent=2,
        ensure_ascii=False,
    )
)
