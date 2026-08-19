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
    / "edgeiq_length_conversion_parameter_source_v1.csv"
)

FACT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_length_conversion_parameter_fact_v1.csv"
)

AUDIT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_length_conversion_parameter_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_length_conversion_parameter_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


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

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(fd)

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

    required_paths = [
        FACT_PATH,
        CONTRACT_PATH,
    ]

    missing_paths = [
        str(path.relative_to(ROOT))
        for path in required_paths
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
                "edgeiq_length_conversion_parameter_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(AUDIT_PATH, payload)

        raise SystemExit(
            "EDGEIQ_LENGTH_CONVERSION_PARAMETER_FACT_V1_AUDIT_FAIL"
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

    duplicate_ids = sorted(
        value
        for value, count in Counter(
            text(row["length_conversion_parameter_id"])
            for row in fact_rows
        ).items()
        if value and count != 1
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

    ranges_by_distance: dict[
        int,
        list[tuple[date, date | None, str]],
    ] = {}

    for row in fact_rows:
        parameter_id = text(
            row["length_conversion_parameter_id"]
        )

        try:
            distance = int(
                text(row["official_distance_metres"])
            )
            seconds_per_length = Decimal(
                text(row["seconds_per_length"])
            )
            effective_from = date.fromisoformat(
                text(row["effective_from_date"])
            )

            effective_to_raw = text(
                row["effective_to_date"]
            )

            effective_to = (
                date.fromisoformat(effective_to_raw)
                if effective_to_raw
                else None
            )
        except Exception as exc:
            governance_errors.append(
                f"{parameter_id}: {type(exc).__name__}"
            )
            continue

        if (
            text(row["conversion_scope"]) != "DISTANCE_EXACT"
            or text(row["parameter_status"]) != "AVAILABLE"
            or distance <= 0
            or not seconds_per_length.is_finite()
            or seconds_per_length <= 0
            or (
                effective_to is not None
                and effective_to < effective_from
            )
            or not text(row["conversion_model_version"])
            or not text(row["evidence_reference"])
            or not SHA256_PATTERN.fullmatch(
                text(row["source_evidence_sha256"])
            )
        ):
            governance_errors.append(parameter_id)

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                text(row["conversion_scope"]),
                distance,
                format_decimal(seconds_per_length),
                text(row["conversion_model_version"]),
                effective_from.isoformat(),
                (
                    effective_to.isoformat()
                    if effective_to is not None
                    else ""
                ),
                text(row["source_evidence_sha256"]),
            ]
        )

        expected_id = (
            f"LCP1-{identity_hash[:24].upper()}"
        )

        if parameter_id != expected_id:
            identity_errors.append(parameter_id)

        expected_parameter_evidence = sha256_payload(
            [
                expected_id,
                text(row["evidence_reference"]),
                text(row["source_evidence_sha256"]),
            ]
        )

        if (
            text(row["parameter_evidence_sha256"])
            != expected_parameter_evidence
        ):
            evidence_errors.append(parameter_id)

        existing_ranges = ranges_by_distance.setdefault(
            distance,
            [],
        )

        for (
            prior_from,
            prior_to,
            prior_id,
        ) in existing_ranges:
            if ranges_overlap(
                effective_from,
                effective_to,
                prior_from,
                prior_to,
            ):
                overlap_errors.append(
                    f"{parameter_id}<->{prior_id}"
                )

        existing_ranges.append(
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
            "edgeiq_length_conversion_parameter_fact_v1"
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
            "EDGEIQ_LENGTH_CONVERSION_PARAMETER_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_LENGTH_CONVERSION_PARAMETER_FACT_V1_AUDIT_PASS"
    )
    print(f"source_exists={SOURCE_PATH.exists()}")
    print(f"parameter_rows={len(fact_rows)}")
    print(f"audit_output={AUDIT_PATH}")


if __name__ == "__main__":
    main()
