from __future__ import annotations

import json
import textwrap
from pathlib import Path


ROOT = Path.cwd()

SPEC_PATH = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "EDGEIQ_BENCHMARK_ELIGIBILITY_FACT_V1_SPEC.md"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_benchmark_eligibility_fact_v1_contract.json"
)

BUILDER_PATH = (
    ROOT
    / "scripts"
    / "build_edgeiq_benchmark_eligibility_fact_v1.py"
)

AUDITOR_PATH = (
    ROOT
    / "scripts"
    / "audit_edgeiq_benchmark_eligibility_fact_v1.py"
)


SPEC_TEXT = r"""
# EDGEiQ Benchmark Eligibility Fact V1

## Status

GOVERNED SPECIFICATION

## Purpose

Classify every governed Benchmark Observation Fact V1 row according to its
permitted future benchmark use.

This component is an eligibility and governance layer only.

It must not calculate:

- standard times
- average times
- median times
- benchmark values
- ratings
- lengths versus standard
- pace scores
- EPI
- ERI

## Architectural Position

Canonical Speed Warehouse V2.1
→ Benchmark Observation Fact V1
→ Benchmark Eligibility Fact V1
→ future Standard Time Engine V1

## Authoritative Input

- public/data/edgeiq_benchmark_observation_fact_v1.csv
- public/data/edgeiq_benchmark_observation_fact_v1_audit.json

No provider data or earlier warehouse layer may be consumed directly.

## Grain

One row per benchmark_observation_id.

## Benchmark Use Classes

### STANDARD_TIME_ELIGIBLE

The observation may be consumed by a future whole-race Standard Time Engine.

Required:

- observation_status = COMPLETE
- evidence_complete = true
- race_split_coverage_type = FULL_RACE
- race identity present
- track present
- official distance greater than zero
- winner identity present
- winner race time greater than zero
- runner count at least 2
- unresolved runner coverage count = 0

### SECTIONAL_REFERENCE_ONLY

The observation cannot be used for whole-race standard-time calculation but may
remain available for governed sectional research.

Required:

- observation_status = COMPLETE
- evidence_complete = true
- race_split_coverage_type = PARTIAL_TIMING_WINDOW
- race identity present
- track present
- governed partial split-window identity is present
- winner identity present
- winner race time greater than zero
- runner count at least 2
- unresolved runner coverage count = 0
- at least one exact winner closing sectional is available

A complete official race distance is not required for
SECTIONAL_REFERENCE_ONLY classification. A partial timing window must never be
represented as the complete official race distance.

### INELIGIBLE

The observation fails one or more required eligibility rules.

Every failed rule must be recorded explicitly.

## Governance Rules

1. Every Benchmark Observation Fact V1 row produces exactly one eligibility row.
2. No observations may be silently dropped.
3. Eligibility must be deterministic.
4. Eligibility reasons must be explicit.
5. Partial timing-window observations must never become standard-time eligible.
6. Unresolved coverage must never become eligible.
7. Missing values must not be inferred.
8. No thresholds may be hidden in React.
9. Input and output hashes must be recorded.
10. Output ordering must be deterministic.

## Outputs

- public/data/edgeiq_benchmark_eligibility_fact_v1.csv
- public/data/edgeiq_benchmark_eligibility_fact_v1_audit.json

## PASS Marker

EDGEIQ_BENCHMARK_ELIGIBILITY_FACT_V1_AUDIT_PASS
""".strip() + "\n"


CONTRACT = {
    "contract_name": "EDGEIQ Benchmark Eligibility Fact V1",
    "contract_version": "1.0.0",
    "grain": "one row per benchmark_observation_id",
    "source_fact": "EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1",
    "minimum_runner_count": 2,
    "allowed_benchmark_use_classes": [
        "STANDARD_TIME_ELIGIBLE",
        "SECTIONAL_REFERENCE_ONLY",
        "INELIGIBLE",
    ],
    "standard_time_eligibility": {
        "required_coverage_type": "FULL_RACE",
        "requires_complete_observation": True,
        "requires_complete_evidence": True,
        "requires_positive_official_distance": True,
        "requires_positive_winner_race_time": True,
        "requires_winner_identity": True,
        "requires_zero_unresolved_coverage": True,
        "minimum_runner_count": 2,
    },
    "sectional_reference_eligibility": {
        "required_coverage_type": "PARTIAL_TIMING_WINDOW",
        "requires_complete_observation": True,
        "requires_complete_evidence": True,
        "requires_positive_official_distance": False,
        "requires_governed_partial_window_identity": True,
        "requires_positive_winner_race_time": True,
        "requires_winner_identity": True,
        "requires_zero_unresolved_coverage": True,
        "requires_at_least_one_exact_closing_sectional": True,
        "minimum_runner_count": 2,
    },
    "fields": [
        {
            "name": "benchmark_eligibility_id",
            "type": "string",
            "nullable": False,
        },
        {
            "name": "benchmark_observation_id",
            "type": "string",
            "nullable": False,
        },
        {
            "name": "race_key",
            "type": "string",
            "nullable": False,
        },
        {
            "name": "benchmark_use_class",
            "type": "enum-string",
            "nullable": False,
        },
        {
            "name": "standard_time_eligible",
            "type": "boolean-string",
            "nullable": False,
        },
        {
            "name": "sectional_reference_eligible",
            "type": "boolean-string",
            "nullable": False,
        },
        {
            "name": "eligibility_rule_version",
            "type": "string",
            "nullable": False,
        },
        {
            "name": "eligibility_reason_codes",
            "type": "pipe-delimited-string",
            "nullable": False,
        },
        {
            "name": "failed_rule_count",
            "type": "integer-string",
            "nullable": False,
        },
        {
            "name": "source_observation_sha256",
            "type": "sha256-string",
            "nullable": False,
        },
    ],
}


BUILDER_TEXT = r'''from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OBSERVATION_PATH = DATA / "edgeiq_benchmark_observation_fact_v1.csv"
OBSERVATION_AUDIT_PATH = (
    DATA / "edgeiq_benchmark_observation_fact_v1_audit.json"
)

OUTPUT_PATH = DATA / "edgeiq_benchmark_eligibility_fact_v1.csv"
AUDIT_PATH = DATA / "edgeiq_benchmark_eligibility_fact_v1_audit.json"

RULE_VERSION = "EDGEIQ_BENCHMARK_ELIGIBILITY_RULES_V1"
MINIMUM_RUNNER_COUNT = 2

PASS_MARKER = "EDGEIQ_BENCHMARK_ELIGIBILITY_FACT_V1_AUDIT_PASS"

OUTPUT_FIELDS = [
    "benchmark_eligibility_id",
    "benchmark_observation_id",
    "race_key",
    "race_date",
    "track_name",
    "official_distance_metres",
    "runner_count",
    "race_split_coverage_type",
    "winner_horse_name",
    "winner_race_time_seconds",
    "winner_last_600_seconds",
    "winner_last_400_seconds",
    "winner_last_200_seconds",
    "benchmark_use_class",
    "standard_time_eligible",
    "sectional_reference_eligible",
    "eligibility_rule_version",
    "eligibility_reason_codes",
    "failed_rule_count",
    "source_observation_sha256",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_float(value: Any) -> float | None:
    text = clean(value)
    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    number = parse_float(value)
    if number is None:
        return None

    if not number.is_integer():
        return None

    return int(number)


def parse_bool(value: Any) -> bool | None:
    text = clean(value).lower()

    if text in {"true", "1", "yes", "y"}:
        return True

    if text in {"false", "0", "no", "n"}:
        return False

    return None


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        fail(f"Required input does not exist: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
        fields = list(reader.fieldnames or [])

    if not fields:
        fail(f"CSV contains no header: {path}")

    return rows, fields


def canonical_json(row: dict[str, str]) -> str:
    normalized = {
        key: clean(row.get(key))
        for key in sorted(row)
    }

    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def row_sha256(row: dict[str, str]) -> str:
    return hashlib.sha256(
        canonical_json(row).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def deterministic_id(observation_id: str) -> str:
    digest = hashlib.sha256(
        (
            "EDGEIQ|BENCHMARK_ELIGIBILITY|V1|"
            + observation_id
        ).encode("utf-8")
    ).hexdigest()

    return f"BEF1-{digest[:24].upper()}"


def audit_passes(payload: Any) -> bool:
    explicit_pass = False
    explicit_fail = False
    failed_checks = False
    pass_marker = False

    def walk(value: Any, key_name: str = "") -> None:
        nonlocal explicit_pass
        nonlocal explicit_fail
        nonlocal failed_checks
        nonlocal pass_marker

        if isinstance(value, dict):
            for raw_key, child in value.items():
                key = clean(raw_key).lower()

                if key in {
                    "status",
                    "audit_status",
                    "overall_status",
                    "result",
                }:
                    status = clean(child).upper()

                    if status in {
                        "PASS",
                        "PASSED",
                        "SUCCESS",
                        "VALID",
                    }:
                        explicit_pass = True

                    if status in {
                        "FAIL",
                        "FAILED",
                        "ERROR",
                        "INVALID",
                    }:
                        explicit_fail = True

                if key == "failed_checks":
                    if isinstance(child, list) and child:
                        failed_checks = True
                    elif isinstance(child, dict) and child:
                        failed_checks = True
                    elif isinstance(child, (int, float)) and child != 0:
                        failed_checks = True

                walk(child, key)

        elif isinstance(value, list):
            for child in value:
                walk(child, key_name)

        elif isinstance(value, str):
            if (
                "EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1_AUDIT_PASS"
                in value.upper()
            ):
                pass_marker = True

    walk(payload)

    return (
        not explicit_fail
        and not failed_checks
        and (explicit_pass or pass_marker)
    )


def classify(
    row: dict[str, str],
) -> tuple[str, bool, bool, list[str]]:
    reasons: list[str] = []

    observation_status = clean(
        row.get("observation_status")
    ).upper()

    evidence_complete = parse_bool(
        row.get("evidence_complete")
    )

    race_key = clean(row.get("race_key"))
    race_date = clean(row.get("race_date"))
    track_name = clean(row.get("track_name"))

    distance = parse_float(
        row.get("official_distance_metres")
    )

    runner_count = parse_int(row.get("runner_count"))

    coverage = clean(
        row.get("race_split_coverage_type")
    ).upper()

    unresolved_count = parse_int(
        row.get("unresolved_coverage_runner_count")
    )

    winner_name = clean(row.get("winner_horse_name"))
    winner_time = parse_float(
        row.get("winner_race_time_seconds")
    )

    exact_sectionals = [
        parse_float(row.get("winner_last_600_seconds")),
        parse_float(row.get("winner_last_400_seconds")),
        parse_float(row.get("winner_last_200_seconds")),
    ]

    if observation_status != "COMPLETE":
        reasons.append("OBSERVATION_NOT_COMPLETE")

    if evidence_complete is not True:
        reasons.append("EVIDENCE_NOT_COMPLETE")

    if not race_key:
        reasons.append("MISSING_RACE_KEY")

    if not race_date:
        reasons.append("MISSING_RACE_DATE")

    if not track_name:
        reasons.append("MISSING_TRACK_NAME")

    if coverage == "FULL_RACE":
        if distance is None:
            reasons.append("MISSING_OFFICIAL_DISTANCE")
        elif distance <= 0:
            reasons.append("NON_POSITIVE_OFFICIAL_DISTANCE")

    if runner_count is None:
        reasons.append("MISSING_RUNNER_COUNT")
    elif runner_count < MINIMUM_RUNNER_COUNT:
        reasons.append("INSUFFICIENT_RUNNER_COUNT")

    if unresolved_count is None:
        reasons.append("MISSING_UNRESOLVED_COVERAGE_COUNT")
    elif unresolved_count != 0:
        reasons.append("UNRESOLVED_RUNNER_COVERAGE")

    if not winner_name:
        reasons.append("MISSING_WINNER_IDENTITY")

    if winner_time is None:
        reasons.append("MISSING_WINNER_RACE_TIME")
    elif winner_time <= 0:
        reasons.append("NON_POSITIVE_WINNER_RACE_TIME")

    common_eligible = not reasons

    standard_time_eligible = (
        common_eligible
        and coverage == "FULL_RACE"
    )

    sectional_reference_eligible = (
        common_eligible
        and coverage == "PARTIAL_TIMING_WINDOW"
        and any(
            value is not None and value > 0
            for value in exact_sectionals
        )
    )

    if coverage not in {
        "FULL_RACE",
        "PARTIAL_TIMING_WINDOW",
    }:
        reasons.append("UNSUPPORTED_COVERAGE_TYPE")

    elif (
        coverage == "PARTIAL_TIMING_WINDOW"
        and not any(
            value is not None and value > 0
            for value in exact_sectionals
        )
    ):
        reasons.append("NO_EXACT_CLOSING_SECTIONAL")

    if standard_time_eligible:
        return (
            "STANDARD_TIME_ELIGIBLE",
            True,
            False,
            ["ELIGIBLE_FULL_RACE_EVIDENCE"],
        )

    if sectional_reference_eligible:
        return (
            "SECTIONAL_REFERENCE_ONLY",
            False,
            True,
            ["PARTIAL_WINDOW_SECTIONAL_EVIDENCE_ONLY"],
        )

    return (
        "INELIGIBLE",
        False,
        False,
        sorted(set(reasons)),
    )


def build() -> dict[str, Any]:
    if not OBSERVATION_AUDIT_PATH.exists():
        fail(
            "Benchmark Observation Fact V1 audit is missing: "
            f"{OBSERVATION_AUDIT_PATH}"
        )

    with OBSERVATION_AUDIT_PATH.open(
        "r",
        encoding="utf-8-sig",
    ) as handle:
        source_audit = json.load(handle)

    if not audit_passes(source_audit):
        fail(
            "Benchmark Observation Fact V1 audit does not contain "
            "a valid PASS state."
        )

    observations, source_fields = read_csv(OBSERVATION_PATH)

    if not observations:
        fail("Benchmark Observation Fact V1 contains no rows.")

    observation_ids = [
        clean(row.get("benchmark_observation_id"))
        for row in observations
    ]

    if any(not value for value in observation_ids):
        fail(
            "Benchmark Observation Fact V1 contains a blank "
            "benchmark_observation_id."
        )

    if len(observation_ids) != len(set(observation_ids)):
        fail(
            "Benchmark Observation Fact V1 contains duplicate "
            "benchmark_observation_id values."
        )

    output_rows: list[dict[str, str]] = []

    for row in sorted(
        observations,
        key=lambda item: (
            clean(item.get("race_key")),
            clean(item.get("benchmark_observation_id")),
        ),
    ):
        use_class, standard_eligible, sectional_eligible, reasons = (
            classify(row)
        )

        observation_id = clean(
            row.get("benchmark_observation_id")
        )

        output_rows.append(
            {
                "benchmark_eligibility_id": deterministic_id(
                    observation_id
                ),
                "benchmark_observation_id": observation_id,
                "race_key": clean(row.get("race_key")),
                "race_date": clean(row.get("race_date")),
                "track_name": clean(row.get("track_name")),
                "official_distance_metres": clean(
                    row.get("official_distance_metres")
                ),
                "runner_count": clean(row.get("runner_count")),
                "race_split_coverage_type": clean(
                    row.get("race_split_coverage_type")
                ),
                "winner_horse_name": clean(
                    row.get("winner_horse_name")
                ),
                "winner_race_time_seconds": clean(
                    row.get("winner_race_time_seconds")
                ),
                "winner_last_600_seconds": clean(
                    row.get("winner_last_600_seconds")
                ),
                "winner_last_400_seconds": clean(
                    row.get("winner_last_400_seconds")
                ),
                "winner_last_200_seconds": clean(
                    row.get("winner_last_200_seconds")
                ),
                "benchmark_use_class": use_class,
                "standard_time_eligible": (
                    "true" if standard_eligible else "false"
                ),
                "sectional_reference_eligible": (
                    "true" if sectional_eligible else "false"
                ),
                "eligibility_rule_version": RULE_VERSION,
                "eligibility_reason_codes": "|".join(reasons),
                "failed_rule_count": (
                    "0"
                    if use_class != "INELIGIBLE"
                    else str(len(reasons))
                ),
                "source_observation_sha256": row_sha256(row),
            }
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=OUTPUT_FIELDS,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    output_ids = [
        row["benchmark_eligibility_id"]
        for row in output_rows
    ]

    governance_checks = {
        "source_audit_passed": True,
        "one_output_per_source_observation": (
            len(output_rows) == len(observations)
        ),
        "unique_eligibility_ids": (
            len(output_ids) == len(set(output_ids))
        ),
        "unique_observation_ids": (
            len(
                {
                    row["benchmark_observation_id"]
                    for row in output_rows
                }
            )
            == len(output_rows)
        ),
        "no_silent_observation_loss": (
            {
                row["benchmark_observation_id"]
                for row in output_rows
            }
            == set(observation_ids)
        ),
        "partial_never_standard_time_eligible": all(
            not (
                row["race_split_coverage_type"]
                == "PARTIAL_TIMING_WINDOW"
                and row["standard_time_eligible"] == "true"
            )
            for row in output_rows
        ),
        "full_race_required_for_standard_time": all(
            row["standard_time_eligible"] != "true"
            or row["race_split_coverage_type"] == "FULL_RACE"
            for row in output_rows
        ),
        "ineligible_rows_have_reasons": all(
            row["benchmark_use_class"] != "INELIGIBLE"
            or (
                row["eligibility_reason_codes"]
                and int(row["failed_rule_count"]) > 0
            )
            for row in output_rows
        ),
        "eligible_rows_have_zero_failed_rules": all(
            row["benchmark_use_class"] == "INELIGIBLE"
            or row["failed_rule_count"] == "0"
            for row in output_rows
        ),
        "no_benchmark_calculation_fields": all(
            forbidden not in field.lower()
            for field in OUTPUT_FIELDS
            for forbidden in (
                "standard_time_seconds",
                "average_time",
                "median_time",
                "rating",
                "lengths_vs_standard",
            )
        ),
        "deterministic_ordering": (
            [
                (
                    row["race_key"],
                    row["benchmark_observation_id"],
                )
                for row in output_rows
            ]
            == sorted(
                (
                    row["race_key"],
                    row["benchmark_observation_id"],
                )
                for row in output_rows
            )
        ),
    }

    failed_checks = [
        name
        for name, passed in governance_checks.items()
        if not passed
    ]

    audit = {
        "audit_name": (
            "EDGEIQ Benchmark Eligibility Fact V1 Build Audit"
        ),
        "audit_version": "1.0.0",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "status": "PASS" if not failed_checks else "FAIL",
        "pass_marker": (
            PASS_MARKER if not failed_checks else ""
        ),
        "eligibility_rule_version": RULE_VERSION,
        "minimum_runner_count": MINIMUM_RUNNER_COUNT,
        "input_file": {
            "path": str(
                OBSERVATION_PATH.relative_to(ROOT)
            ).replace("\\", "/"),
            "sha256": file_sha256(OBSERVATION_PATH),
            "bytes": OBSERVATION_PATH.stat().st_size,
        },
        "input_audit_file": {
            "path": str(
                OBSERVATION_AUDIT_PATH.relative_to(ROOT)
            ).replace("\\", "/"),
            "sha256": file_sha256(
                OBSERVATION_AUDIT_PATH
            ),
            "bytes": OBSERVATION_AUDIT_PATH.stat().st_size,
        },
        "output_file": {
            "path": str(
                OUTPUT_PATH.relative_to(ROOT)
            ).replace("\\", "/"),
            "sha256": file_sha256(OUTPUT_PATH),
            "bytes": OUTPUT_PATH.stat().st_size,
        },
        "counts": {
            "source_observations": len(observations),
            "eligibility_rows": len(output_rows),
            "standard_time_eligible": sum(
                row["standard_time_eligible"] == "true"
                for row in output_rows
            ),
            "sectional_reference_only": sum(
                row["benchmark_use_class"]
                == "SECTIONAL_REFERENCE_ONLY"
                for row in output_rows
            ),
            "ineligible": sum(
                row["benchmark_use_class"] == "INELIGIBLE"
                for row in output_rows
            ),
        },
        "benchmark_use_class_counts": dict(
            sorted(
                Counter(
                    row["benchmark_use_class"]
                    for row in output_rows
                ).items()
            )
        ),
        "eligibility_reason_counts": dict(
            sorted(
                Counter(
                    reason
                    for row in output_rows
                    for reason in row[
                        "eligibility_reason_codes"
                    ].split("|")
                    if reason
                ).items()
            )
        ),
        "governance_checks": governance_checks,
        "failed_checks": failed_checks,
        "source_headers": source_fields,
    }

    with AUDIT_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            audit,
            handle,
            indent=2,
            ensure_ascii=False,
        )
        handle.write("\n")

    if failed_checks:
        fail(
            "Benchmark Eligibility Fact V1 governance failed: "
            + ", ".join(failed_checks)
        )

    return audit


def main() -> int:
    try:
        audit = build()
    except Exception as exc:
        print(
            "EDGEIQ_BENCHMARK_ELIGIBILITY_FACT_V1_BUILD_FAIL: "
            f"{exc}",
            file=sys.stderr,
        )
        return 1

    print("Benchmark Eligibility Fact V1 built.")
    print(
        "Source observations:",
        audit["counts"]["source_observations"],
    )
    print(
        "Standard-time eligible:",
        audit["counts"]["standard_time_eligible"],
    )
    print(
        "Sectional reference only:",
        audit["counts"]["sectional_reference_only"],
    )
    print(
        "Ineligible:",
        audit["counts"]["ineligible"],
    )
    print(PASS_MARKER)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


AUDITOR_TEXT = r'''from __future__ import annotations

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
'''


for path in (
    SPEC_PATH,
    CONTRACT_PATH,
    BUILDER_PATH,
    AUDITOR_PATH,
):
    path.parent.mkdir(parents=True, exist_ok=True)

SPEC_PATH.write_text(
    SPEC_TEXT,
    encoding="utf-8",
)

CONTRACT_PATH.write_text(
    json.dumps(
        CONTRACT,
        indent=2,
        ensure_ascii=False,
    )
    + "\n",
    encoding="utf-8",
)

BUILDER_PATH.write_text(
    textwrap.dedent(BUILDER_TEXT).lstrip(),
    encoding="utf-8",
)

AUDITOR_PATH.write_text(
    textwrap.dedent(AUDITOR_TEXT).lstrip(),
    encoding="utf-8",
)

print("Created:")

for path in (
    SPEC_PATH,
    CONTRACT_PATH,
    BUILDER_PATH,
    AUDITOR_PATH,
):
    print(f"  {path.relative_to(ROOT)}")
