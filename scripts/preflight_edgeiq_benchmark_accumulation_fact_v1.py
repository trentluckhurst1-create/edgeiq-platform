from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

TARGET_FILES = {
    "observation": "edgeiq_benchmark_observation_fact_v1.csv",
    "eligibility": "edgeiq_benchmark_eligibility_fact_v1.csv",
}


def fail(message: str) -> None:
    print(f"PREFLIGHT_FAIL: {message}")
    raise SystemExit(1)


def find_unique_file(filename: str) -> Path:
    matches = sorted(
        path
        for path in REPO_ROOT.rglob(filename)
        if ".git" not in path.parts
        and "node_modules" not in path.parts
        and "__pycache__" not in path.parts
    )

    print(f"\nSEARCH_FILE: {filename}")
    print(f"MATCH_COUNT: {len(matches)}")

    for match in matches:
        print(f"  - {match.relative_to(REPO_ROOT)}")

    if not matches:
        fail(f"Canonical input not found: {filename}")

    preferred = [
        path
        for path in matches
        if "public" in path.parts and "data" in path.parts
    ]

    candidates = preferred or matches

    if len(candidates) > 1:
        exact_public_data = [
            path
            for path in candidates
            if path.parent == REPO_ROOT / "public" / "data"
        ]
        if len(exact_public_data) == 1:
            return exact_public_data[0]

        fail(
            f"Multiple possible canonical files found for {filename}. "
            "Do not guess which one is authoritative."
        )

    return candidates[0]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            fail(f"No CSV header found in {path}")

        rows = list(reader)
        return list(reader.fieldnames), rows


def print_field_profile(
    label: str,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    print(f"\n{label}_ROW_COUNT: {len(rows)}")
    print(f"{label}_FIELD_COUNT: {len(fieldnames)}")
    print(f"{label}_FIELDS:")

    for index, field in enumerate(fieldnames, start=1):
        populated = sum(
            1 for row in rows if str(row.get(field, "")).strip()
        )
        distinct_values = {
            str(row.get(field, "")).strip()
            for row in rows
            if str(row.get(field, "")).strip()
        }

        print(
            f"  {index:02d}. {field} | "
            f"populated={populated} | distinct={len(distinct_values)}"
        )


def locate_field(
    fieldnames: list[str],
    exact_name: str,
    contains_terms: tuple[str, ...] = (),
) -> str | None:
    if exact_name in fieldnames:
        return exact_name

    lowered = {field.lower(): field for field in fieldnames}
    if exact_name.lower() in lowered:
        return lowered[exact_name.lower()]

    for field in fieldnames:
        candidate = field.lower()
        if all(term.lower() in candidate for term in contains_terms):
            return field

    return None


def print_value_counts(
    label: str,
    rows: list[dict[str, str]],
    field: str | None,
) -> None:
    if field is None:
        print(f"\n{label}: FIELD_NOT_FOUND")
        return

    counts = Counter(
        str(row.get(field, "")).strip() or "<BLANK>"
        for row in rows
    )

    print(f"\n{label}: {field}")
    for value, count in sorted(counts.items()):
        print(f"  {value}: {count}")


def run_git_command(arguments: list[str]) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout.strip()
    error = result.stderr.strip()

    if result.returncode != 0:
        return f"GIT_COMMAND_FAILED: {' '.join(arguments)}\n{error}"

    return output or "<NO_OUTPUT>"


def main() -> None:
    print("=" * 88)
    print("EDGEIQ BENCHMARK ACCUMULATION FACT V1 — GOVERNED PREFLIGHT")
    print("=" * 88)
    print(f"REPO_ROOT: {REPO_ROOT}")

    observation_path = find_unique_file(TARGET_FILES["observation"])
    eligibility_path = find_unique_file(TARGET_FILES["eligibility"])

    print(
        "\nSELECTED_OBSERVATION_PATH: "
        f"{observation_path.relative_to(REPO_ROOT)}"
    )
    print(
        "SELECTED_ELIGIBILITY_PATH: "
        f"{eligibility_path.relative_to(REPO_ROOT)}"
    )

    observation_fields, observation_rows = read_csv(observation_path)
    eligibility_fields, eligibility_rows = read_csv(eligibility_path)

    print_field_profile(
        "OBSERVATION",
        observation_fields,
        observation_rows,
    )
    print_field_profile(
        "ELIGIBILITY",
        eligibility_fields,
        eligibility_rows,
    )

    observation_join_field = locate_field(
        observation_fields,
        "benchmark_observation_id",
        ("benchmark", "observation", "id"),
    )
    eligibility_join_field = locate_field(
        eligibility_fields,
        "benchmark_observation_id",
        ("benchmark", "observation", "id"),
    )
    eligibility_classification_field = locate_field(
        eligibility_fields,
        "eligibility_classification",
        ("eligibility",),
    )

    print("\nGOVERNED_FIELD_RESOLUTION:")
    print(f"  observation_join_field={observation_join_field}")
    print(f"  eligibility_join_field={eligibility_join_field}")
    print(
        "  eligibility_classification_field="
        f"{eligibility_classification_field}"
    )

    if observation_join_field != "benchmark_observation_id":
        fail(
            "Observation fact does not expose the exact governed join key "
            "'benchmark_observation_id'."
        )

    if eligibility_join_field != "benchmark_observation_id":
        fail(
            "Eligibility fact does not expose the exact governed join key "
            "'benchmark_observation_id'."
        )

    observation_ids = [
        str(row.get(observation_join_field, "")).strip()
        for row in observation_rows
    ]
    eligibility_ids = [
        str(row.get(eligibility_join_field, "")).strip()
        for row in eligibility_rows
    ]

    blank_observation_ids = sum(1 for value in observation_ids if not value)
    blank_eligibility_ids = sum(1 for value in eligibility_ids if not value)

    duplicate_observation_ids = sorted(
        value
        for value, count in Counter(observation_ids).items()
        if value and count > 1
    )
    duplicate_eligibility_ids = sorted(
        value
        for value, count in Counter(eligibility_ids).items()
        if value and count > 1
    )

    observation_id_set = {value for value in observation_ids if value}
    eligibility_id_set = {value for value in eligibility_ids if value}

    print("\nJOIN_KEY_INTEGRITY:")
    print(f"  blank_observation_ids={blank_observation_ids}")
    print(f"  blank_eligibility_ids={blank_eligibility_ids}")
    print(
        "  duplicate_observation_ids="
        f"{len(duplicate_observation_ids)}"
    )
    print(
        "  duplicate_eligibility_ids="
        f"{len(duplicate_eligibility_ids)}"
    )
    print(
        "  eligibility_ids_missing_from_observation="
        f"{len(eligibility_id_set - observation_id_set)}"
    )
    print(
        "  observation_ids_missing_from_eligibility="
        f"{len(observation_id_set - eligibility_id_set)}"
    )

    if duplicate_observation_ids:
        print(
            "  duplicate_observation_id_values="
            + json.dumps(duplicate_observation_ids, indent=2)
        )

    if duplicate_eligibility_ids:
        print(
            "  duplicate_eligibility_id_values="
            + json.dumps(duplicate_eligibility_ids, indent=2)
        )

    print_value_counts(
        "ELIGIBILITY_CLASSIFICATION_COUNTS",
        eligibility_rows,
        eligibility_classification_field,
    )

    for expected_field in (
        "track_name",
        "official_distance_metres",
        "course_name",
        "surface",
        "track_condition",
    ):
        resolved_field = locate_field(
            observation_fields,
            expected_field,
            tuple(expected_field.split("_")),
        )
        print_value_counts(
            f"OBSERVATION_{expected_field.upper()}_COUNTS",
            observation_rows,
            resolved_field,
        )

    print("\nGIT_STATUS_PORCELAIN:")
    print(run_git_command(["status", "--porcelain"]))

    print("\nGIT_HEAD:")
    print(run_git_command(["log", "-1", "--oneline"]))

    print("\nPREFLIGHT_COMPLETE")
    print(
        "No repository files were modified other than this preflight script."
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPREFLIGHT_CANCELLED")
        sys.exit(130)