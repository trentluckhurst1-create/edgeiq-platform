from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = (
    ROOT
    / "config"
    / "performance-intelligence"
    / "edgeiq_horse_performance_aggregation_parameter_source_v1.csv"
)

FACT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_horse_performance_aggregation_parameter_fact_v1.csv"
)

AUDIT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_horse_performance_aggregation_parameter_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_horse_performance_aggregation_parameter_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

SUPPORTED_AGGREGATION_METHODS = {
    "ARITHMETIC_MEAN",
    "WEIGHTED_ARITHMETIC_MEAN",
}

SUPPORTED_RECENCY_METHODS = {
    "NONE",
    "EXPONENTIAL_HALF_LIFE",
}

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def optional_date(value: object) -> date | None:
    raw = text(value)

    if not raw:
        return None

    return date.fromisoformat(raw)


def ranges_overlap(
    left_from: date,
    left_to: date | None,
    right_from: date,
    right_to: date | None,
) -> bool:
    return (
        left_from <= (right_to or date.max)
        and right_from <= (left_to or date.max)
    )


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise RuntimeError(f"Missing CSV header: {path}")

        return list(reader.fieldnames), list(reader)


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(file_descriptor)

    temporary_path = Path(temporary_name)

    try:
        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    checks: dict[str, dict[str, object]] = {}

    def check(
        name: str,
        passed: bool,
        detail: object,
    ) -> None:
        checks[name] = {
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }

    missing_paths = [
        str(path.relative_to(ROOT))
        for path in [FACT_PATH, CONTRACT_PATH]
        if not path.exists()
    ]

    check(
        "required_files_exist",
        not missing_paths,
        missing_paths,
    )

    if missing_paths:
        payload = {
            "audit_name": (
                "edgeiq_horse_performance_aggregation_parameter_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(AUDIT_PATH, payload)

        raise SystemExit(
            "EDGEIQ_HORSE_PERFORMANCE_AGGREGATION_PARAMETER_FACT_V1_AUDIT_FAIL"
        )

    fact_fields, fact_rows = read_csv(FACT_PATH)

    contract = json.loads(
        CONTRACT_PATH.read_text(encoding="utf-8")
    )

    check(
        "contract_fields_exact",
        fact_fields == contract["required_fields"],
        {
            "actual": fact_fields,
            "expected": contract["required_fields"],
        },
    )

    parameter_ids = [
        text(
            row[
                "horse_performance_aggregation_parameter_id"
            ]
        )
        for row in fact_rows
    ]

    duplicate_ids = sorted(
        parameter_id
        for parameter_id, count in Counter(
            parameter_ids
        ).items()
        if parameter_id and count != 1
    )

    check(
        "unique_parameter_ids",
        not duplicate_ids,
        duplicate_ids,
    )

    governance_errors: list[str] = []
    identity_errors: list[str] = []
    evidence_errors: list[str] = []
    overlap_errors: list[str] = []

    effective_ranges: list[
        tuple[date, date | None, str]
    ] = []

    for row in fact_rows:
        parameter_id = text(
            row[
                "horse_performance_aggregation_parameter_id"
            ]
        )

        try:
            aggregation_method = text(
                row["aggregation_method"]
            )
            maximum_observations = int(
                text(row["maximum_observations"])
            )
            lookback_days = int(
                text(row["lookback_days"])
            )
            minimum_observations = int(
                text(row["minimum_observations"])
            )
            recency_method = text(
                row["recency_weighting_method"]
            )
            half_life_raw = text(
                row["recency_half_life_days"]
            )
            effective_from = date.fromisoformat(
                text(row["effective_from_date"])
            )
            effective_to = optional_date(
                row["effective_to_date"]
            )
        except Exception as exc:
            governance_errors.append(
                f"{parameter_id}:{type(exc).__name__}"
            )
            continue

        half_life_value = ""

        if recency_method == "NONE":
            half_life_valid = not half_life_raw
        elif recency_method == "EXPONENTIAL_HALF_LIFE":
            try:
                half_life_decimal = Decimal(half_life_raw)
                half_life_valid = (
                    half_life_decimal.is_finite()
                    and half_life_decimal > 0
                )
                half_life_value = format_decimal(
                    half_life_decimal
                )
            except Exception:
                half_life_valid = False
        else:
            half_life_valid = False

        source_evidence = text(
            row["source_evidence_sha256"]
        )

        governed = (
            aggregation_method
            in SUPPORTED_AGGREGATION_METHODS
            and maximum_observations > 0
            and lookback_days > 0
            and minimum_observations > 0
            and minimum_observations
            <= maximum_observations
            and recency_method
            in SUPPORTED_RECENCY_METHODS
            and half_life_valid
            and bool(
                text(row["aggregation_model_version"])
            )
            and text(row["parameter_status"])
            == "AVAILABLE"
            and (
                effective_to is None
                or effective_to >= effective_from
            )
            and bool(text(row["evidence_reference"]))
            and bool(
                SHA256_PATTERN.fullmatch(
                    source_evidence
                )
            )
            and text(row["contract_version"])
            == CONTRACT_VERSION
        )

        if not governed:
            governance_errors.append(parameter_id)

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                aggregation_method,
                maximum_observations,
                lookback_days,
                minimum_observations,
                recency_method,
                half_life_value,
                text(row["aggregation_model_version"]),
                effective_from.isoformat(),
                (
                    effective_to.isoformat()
                    if effective_to is not None
                    else ""
                ),
                source_evidence,
            ]
        )

        expected_id = (
            f"HPAP1-{identity_hash[:24].upper()}"
        )

        if parameter_id != expected_id:
            identity_errors.append(parameter_id)

        expected_evidence = sha256_payload(
            [
                expected_id,
                text(row["evidence_reference"]),
                source_evidence,
            ]
        )

        if (
            text(row["parameter_evidence_sha256"])
            != expected_evidence
        ):
            evidence_errors.append(parameter_id)

        for prior_from, prior_to, prior_id in effective_ranges:
            if ranges_overlap(
                effective_from,
                effective_to,
                prior_from,
                prior_to,
            ):
                overlap_errors.append(
                    f"{parameter_id}<->{prior_id}"
                )

        effective_ranges.append(
            (
                effective_from,
                effective_to,
                parameter_id,
            )
        )

    check(
        "parameter_governance",
        not governance_errors,
        governance_errors,
    )

    check(
        "deterministic_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "evidence_hash_reproducible",
        not evidence_errors,
        evidence_errors,
    )

    check(
        "no_effective_date_overlaps",
        not overlap_errors,
        overlap_errors,
    )

    forbidden_fields = set(contract["forbidden_fields"])
    present_forbidden_fields = sorted(
        forbidden_fields.intersection(fact_fields)
    )

    check(
        "no_forbidden_fields",
        not present_forbidden_fields,
        present_forbidden_fields,
    )

    current_population_expected = (
        not SOURCE_PATH.exists()
        and len(fact_rows) == 0
    )

    check(
        "current_population_expected",
        current_population_expected,
        {
            "source_exists": SOURCE_PATH.exists(),
            "parameter_rows": len(fact_rows),
        },
    )

    failed_checks = [
        name
        for name, result in checks.items()
        if result["status"] != "PASS"
    ]

    status = "PASS" if not failed_checks else "FAIL"

    payload = {
        "audit_name": (
            "edgeiq_horse_performance_aggregation_parameter_fact_v1"
        ),
        "audit_version": "1.0.0",
        "audited_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "status": status,
        "counts": {
            "source_exists": SOURCE_PATH.exists(),
            "parameter_rows": len(fact_rows),
        },
        "failed_checks": failed_checks,
        "checks": checks,
    }

    atomic_write_json(AUDIT_PATH, payload)

    if status != "PASS":
        print(json.dumps(payload, indent=2))

        raise SystemExit(
            "EDGEIQ_HORSE_PERFORMANCE_AGGREGATION_PARAMETER_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_HORSE_PERFORMANCE_AGGREGATION_PARAMETER_FACT_V1_AUDIT_PASS"
    )
    print(f"source_exists={SOURCE_PATH.exists()}")
    print(f"parameter_rows={len(fact_rows)}")
    print(f"audit_output={AUDIT_PATH}")


if __name__ == "__main__":
    main()
