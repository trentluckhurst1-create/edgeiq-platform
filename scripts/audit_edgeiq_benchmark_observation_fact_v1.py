from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OBSERVATION_PATH = DATA / "edgeiq_benchmark_observation_fact_v1.csv"
BUILD_AUDIT_PATH = (
    DATA / "edgeiq_benchmark_observation_fact_v1_audit.json"
)
RACE_PATH = DATA / "edgeiq_racingcom_canonical_race_speed_fact_v2_1.csv"
RUNNER_PATH = DATA / "edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv"

PASS_MARKER = "EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1_AUDIT_PASS"

REQUIRED_FIELDS = [
    "benchmark_observation_id",
    "race_key",
    "race_date",
    "track_name",
    "race_number",
    "official_distance_metres",
    "runner_count",
    "race_split_coverage_type",
    "full_race_coverage_runner_count",
    "partial_timing_window_runner_count",
    "unresolved_coverage_runner_count",
    "winner_runner_key",
    "winner_horse_name",
    "winner_race_time_seconds",
    "winner_last_600_seconds",
    "winner_last_400_seconds",
    "winner_last_200_seconds",
    "source_provider",
    "source_canonical_version",
    "source_semantic_version",
    "observation_status",
    "evidence_complete",
    "race_source_row_sha256",
    "winner_source_row_sha256",
]


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader], list(reader.fieldnames or [])


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit() -> dict[str, Any]:
    observations, fields = read_csv(OBSERVATION_PATH)
    race_rows, _ = read_csv(RACE_PATH)
    runner_rows, _ = read_csv(RUNNER_PATH)

    with BUILD_AUDIT_PATH.open("r", encoding="utf-8-sig") as handle:
        build_audit = json.load(handle)

    missing_fields = [
        field for field in REQUIRED_FIELDS if field not in fields
    ]

    race_keys = [clean(row.get("race_key")) for row in observations]
    observation_ids = [
        clean(row.get("benchmark_observation_id"))
        for row in observations
    ]

    runner_counts: dict[str, int] = defaultdict(int)
    for row in runner_rows:
        runner_counts[clean(row.get("race_key"))] += 1

    checks: dict[str, bool] = {
        "build_audit_status_pass": (
            clean(build_audit.get("status")).upper() == "PASS"
        ),
        "required_fields_present": not missing_fields,
        "non_empty_output": bool(observations),
        "one_observation_per_canonical_race": (
            len(observations) == len(race_rows)
        ),
        "unique_race_keys": (
            len(race_keys) == len(set(race_keys))
        ),
        "unique_observation_ids": (
            len(observation_ids) == len(set(observation_ids))
        ),
        "no_blank_race_keys": all(race_keys),
        "no_blank_observation_ids": all(observation_ids),
        "allowed_coverage_types_only": all(
            clean(row.get("race_split_coverage_type"))
            in {"FULL_RACE", "PARTIAL_TIMING_WINDOW", "MIXED"}
            for row in observations
        ),
        "zero_unresolved_runner_coverage": all(
            clean(row.get("unresolved_coverage_runner_count")) == "0"
            for row in observations
        ),
        "runner_counts_match_canonical": all(
            int(clean(row.get("runner_count")) or "0")
            == runner_counts.get(clean(row.get("race_key")), 0)
            for row in observations
        ),
        "coverage_counts_sum_to_runner_count": all(
            int(clean(row.get("runner_count")) or "0")
            == (
                int(
                    clean(
                        row.get("full_race_coverage_runner_count")
                    )
                    or "0"
                )
                + int(
                    clean(
                        row.get(
                            "partial_timing_window_runner_count"
                        )
                    )
                    or "0"
                )
                + int(
                    clean(
                        row.get("unresolved_coverage_runner_count")
                    )
                    or "0"
                )
            )
            for row in observations
        ),
        "source_provider_locked": all(
            clean(row.get("source_provider")) == "RACING.COM"
            for row in observations
        ),
        "source_canonical_version_locked": all(
            clean(row.get("source_canonical_version"))
            == "RACINGCOM_CANONICAL_SPEED_WAREHOUSE_V2_1"
            for row in observations
        ),
        "source_semantic_version_locked": all(
            clean(row.get("source_semantic_version"))
            == "RACINGCOM_SPEED_SEMANTICS_V1_1"
            for row in observations
        ),
        "evidence_complete_is_boolean_string": all(
            clean(row.get("evidence_complete")) in {"true", "false"}
            for row in observations
        ),
        "complete_rows_have_winner_identity": all(
            clean(row.get("observation_status")) != "COMPLETE"
            or (
                clean(row.get("winner_horse_name"))
                and clean(row.get("winner_race_time_seconds"))
            )
            for row in observations
        ),
        "no_derived_standard_fields": all(
            "standard" not in field.lower()
            and "benchmark_time" not in field.lower()
            and "rating" not in field.lower()
            and "lengths_vs" not in field.lower()
            for field in fields
        ),
        "output_hash_matches_build_audit": (
            clean(
                build_audit.get("output_file", {}).get("sha256")
            )
            == file_sha256(OBSERVATION_PATH)
        ),
    }

    failed_checks = [
        name for name, passed in checks.items() if not passed
    ]

    result = {
        "audit_name": "EDGEIQ Benchmark Observation Fact V1 Independent Audit",
        "audit_version": "1.0.0",
        "status": "PASS" if not failed_checks else "FAIL",
        "pass_marker": PASS_MARKER if not failed_checks else "",
        "counts": {
            "canonical_races": len(race_rows),
            "canonical_runners": len(runner_rows),
            "observations": len(observations),
            "complete_observations": sum(
                clean(row.get("observation_status")) == "COMPLETE"
                for row in observations
            ),
            "incomplete_observations": sum(
                clean(row.get("observation_status")) != "COMPLETE"
                for row in observations
            ),
        },
        "coverage_counts": dict(
            sorted(
                Counter(
                    clean(row.get("race_split_coverage_type"))
                    for row in observations
                ).items()
            )
        ),
        "status_counts": dict(
            sorted(
                Counter(
                    clean(row.get("observation_status"))
                    for row in observations
                ).items()
            )
        ),
        "checks": checks,
        "failed_checks": failed_checks,
        "missing_fields": missing_fields,
    }

    return result


def main() -> int:
    try:
        result = audit()
    except Exception as exc:
        print(
            f"EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1_AUDIT_FAIL: {exc}",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, indent=2))

    if result["status"] != "PASS":
        return 1

    print(PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
