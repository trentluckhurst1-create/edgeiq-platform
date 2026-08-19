from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = DATA / "edgeiq_benchmark_observation_fact_v1.csv"
ELIGIBILITY_PATH = DATA / "edgeiq_benchmark_eligibility_fact_v1.csv"
BUILD_AUDIT_PATH = (
    DATA / "edgeiq_benchmark_eligibility_fact_v1_audit.json"
)

PASS_MARKER = "EDGEIQ_BENCHMARK_ELIGIBILITY_FACT_V1_AUDIT_PASS"

REQUIRED_FIELDS = [
    "benchmark_eligibility_id",
    "benchmark_observation_id",
    "race_key",
    "race_split_coverage_type",
    "benchmark_use_class",
    "standard_time_eligible",
    "sectional_reference_eligible",
    "eligibility_rule_version",
    "eligibility_reason_codes",
    "failed_rule_count",
    "source_observation_sha256",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        return (
            [dict(row) for row in reader],
            list(reader.fieldnames or []),
        )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def audit() -> dict[str, Any]:
    sources, _ = read_csv(SOURCE_PATH)
    rows, fields = read_csv(ELIGIBILITY_PATH)

    with BUILD_AUDIT_PATH.open(
        "r",
        encoding="utf-8-sig",
    ) as handle:
        build_audit = json.load(handle)

    missing_fields = [
        field
        for field in REQUIRED_FIELDS
        if field not in fields
    ]

    source_ids = {
        clean(row.get("benchmark_observation_id"))
        for row in sources
    }

    output_source_ids = [
        clean(row.get("benchmark_observation_id"))
        for row in rows
    ]

    eligibility_ids = [
        clean(row.get("benchmark_eligibility_id"))
        for row in rows
    ]

    allowed_classes = {
        "STANDARD_TIME_ELIGIBLE",
        "SECTIONAL_REFERENCE_ONLY",
        "INELIGIBLE",
    }

    checks = {
        "build_audit_status_pass": (
            clean(build_audit.get("status")).upper()
            == "PASS"
        ),
        "required_fields_present": not missing_fields,
        "non_empty_output": bool(rows),
        "one_row_per_source_observation": (
            len(rows) == len(sources)
        ),
        "source_identity_reconciled": (
            set(output_source_ids) == source_ids
        ),
        "unique_observation_ids": (
            len(output_source_ids)
            == len(set(output_source_ids))
        ),
        "unique_eligibility_ids": (
            len(eligibility_ids)
            == len(set(eligibility_ids))
        ),
        "allowed_classes_only": all(
            clean(row.get("benchmark_use_class"))
            in allowed_classes
            for row in rows
        ),
        "standard_eligible_is_full_race_only": all(
            clean(row.get("standard_time_eligible"))
            != "true"
            or clean(
                row.get("race_split_coverage_type")
            )
            == "FULL_RACE"
            for row in rows
        ),
        "partial_window_never_standard_eligible": all(
            not (
                clean(
                    row.get("race_split_coverage_type")
                )
                == "PARTIAL_TIMING_WINDOW"
                and clean(
                    row.get("standard_time_eligible")
                )
                == "true"
            )
            for row in rows
        ),
        "class_and_boolean_consistent": all(
            (
                clean(row.get("benchmark_use_class"))
                == "STANDARD_TIME_ELIGIBLE"
                and clean(
                    row.get("standard_time_eligible")
                )
                == "true"
                and clean(
                    row.get(
                        "sectional_reference_eligible"
                    )
                )
                == "false"
            )
            or (
                clean(row.get("benchmark_use_class"))
                == "SECTIONAL_REFERENCE_ONLY"
                and clean(
                    row.get("standard_time_eligible")
                )
                == "false"
                and clean(
                    row.get(
                        "sectional_reference_eligible"
                    )
                )
                == "true"
            )
            or (
                clean(row.get("benchmark_use_class"))
                == "INELIGIBLE"
                and clean(
                    row.get("standard_time_eligible")
                )
                == "false"
                and clean(
                    row.get(
                        "sectional_reference_eligible"
                    )
                )
                == "false"
            )
            for row in rows
        ),
        "ineligible_rows_have_failure_reasons": all(
            clean(row.get("benchmark_use_class"))
            != "INELIGIBLE"
            or (
                clean(
                    row.get("eligibility_reason_codes")
                )
                and int(
                    clean(row.get("failed_rule_count"))
                    or "0"
                )
                > 0
            )
            for row in rows
        ),
        "eligible_rows_have_zero_failed_rules": all(
            clean(row.get("benchmark_use_class"))
            == "INELIGIBLE"
            or clean(row.get("failed_rule_count")) == "0"
            for row in rows
        ),
        "output_hash_matches_build_audit": (
            clean(
                build_audit.get(
                    "output_file",
                    {},
                ).get("sha256")
            )
            == file_sha256(ELIGIBILITY_PATH)
        ),
        "no_standard_time_calculation_fields": all(
            forbidden not in field.lower()
            for field in fields
            for forbidden in (
                "standard_time_seconds",
                "average_time",
                "median_time",
                "lengths_vs_standard",
                "performance_rating",
            )
        ),
    }

    failed_checks = [
        name
        for name, passed in checks.items()
        if not passed
    ]

    return {
        "audit_name": (
            "EDGEIQ Benchmark Eligibility Fact V1 "
            "Independent Audit"
        ),
        "audit_version": "1.0.0",
        "status": (
            "PASS" if not failed_checks else "FAIL"
        ),
        "pass_marker": (
            PASS_MARKER if not failed_checks else ""
        ),
        "counts": {
            "source_observations": len(sources),
            "eligibility_rows": len(rows),
            "standard_time_eligible": sum(
                clean(row.get("benchmark_use_class"))
                == "STANDARD_TIME_ELIGIBLE"
                for row in rows
            ),
            "sectional_reference_only": sum(
                clean(row.get("benchmark_use_class"))
                == "SECTIONAL_REFERENCE_ONLY"
                for row in rows
            ),
            "ineligible": sum(
                clean(row.get("benchmark_use_class"))
                == "INELIGIBLE"
                for row in rows
            ),
        },
        "benchmark_use_class_counts": dict(
            sorted(
                Counter(
                    clean(
                        row.get("benchmark_use_class")
                    )
                    for row in rows
                ).items()
            )
        ),
        "checks": checks,
        "failed_checks": failed_checks,
        "missing_fields": missing_fields,
    }


def main() -> int:
    try:
        result = audit()
    except Exception as exc:
        print(
            "EDGEIQ_BENCHMARK_ELIGIBILITY_FACT_V1_AUDIT_FAIL: "
            f"{exc}",
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
