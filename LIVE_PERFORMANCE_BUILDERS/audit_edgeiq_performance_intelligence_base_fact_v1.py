from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = (
    DATA / "edgeiq_lengths_versus_standard_fact_v1.csv"
)

FACT_PATH = (
    DATA / "edgeiq_performance_intelligence_base_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_performance_intelligence_base_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_performance_intelligence_base_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"
CALCULATION_METHOD = (
    "DIRECT_GOVERNED_LENGTHS_VERSUS_STANDARD"
)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


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


def decimal_value(value: object) -> Decimal:
    return Decimal(text(value))


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def expected_interpretation(
    lengths_value: Decimal,
) -> str:
    if lengths_value > 0:
        return "FASTER_THAN_STANDARD"

    if lengths_value < 0:
        return "SLOWER_THAN_STANDARD"

    return "EQUAL_TO_STANDARD"


def atomic_write_json(
    path: Path,
    payload: dict,
) -> None:
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
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
            + "\n",
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

    required_paths = [
        SOURCE_PATH,
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
                "edgeiq_performance_intelligence_base_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(AUDIT_PATH, payload)

        raise SystemExit(
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_BASE_FACT_V1_AUDIT_FAIL"
        )

    _, source_rows = read_csv(SOURCE_PATH)
    fact_fields, fact_rows = read_csv(FACT_PATH)

    contract = json.loads(
        CONTRACT_PATH.read_text(encoding="utf-8")
    )

    expected_fields = contract["required_fields"]

    check(
        "contract_fields_exact",
        fact_fields == expected_fields,
        {
            "actual": fact_fields,
            "expected": expected_fields,
        },
    )

    source_by_id = {
        text(row["lengths_versus_standard_id"]): row
        for row in source_rows
    }

    fact_source_ids = [
        text(row["lengths_versus_standard_id"])
        for row in fact_rows
    ]

    check(
        "source_population_exact",
        set(source_by_id) == set(fact_source_ids),
        {
            "source_rows": len(source_rows),
            "fact_rows": len(fact_rows),
            "missing": sorted(
                set(source_by_id) - set(fact_source_ids)
            ),
            "unexpected": sorted(
                set(fact_source_ids) - set(source_by_id)
            ),
        },
    )

    duplicate_ids = sorted(
        value
        for value, count in Counter(
            text(
                row["performance_intelligence_base_id"]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_sources = sorted(
        value
        for value, count in Counter(
            fact_source_ids
        ).items()
        if value and count != 1
    )

    check(
        "unique_performance_intelligence_base_ids",
        not duplicate_ids,
        duplicate_ids,
    )

    check(
        "one_row_per_lengths_versus_standard",
        not duplicate_sources,
        duplicate_sources,
    )

    calculation_errors: list[str] = []
    interpretation_errors: list[str] = []
    identity_errors: list[str] = []
    lineage_errors: list[str] = []
    governance_errors: list[str] = []

    for fact in fact_rows:
        source_id = text(
            fact["lengths_versus_standard_id"]
        )

        source = source_by_id.get(source_id)

        if source is None:
            lineage_errors.append(
                f"{source_id}: unknown source row"
            )
            continue

        source_lengths = decimal_value(
            source["lengths_versus_standard"]
        )

        fact_lengths = decimal_value(
            fact["raw_performance_lengths"]
        )

        if (
            format_decimal(source_lengths)
            != format_decimal(fact_lengths)
        ):
            calculation_errors.append(source_id)

        expected_interpretation_value = (
            expected_interpretation(source_lengths)
        )

        if (
            text(
                fact["raw_performance_interpretation"]
            )
            != expected_interpretation_value
            or text(
                source[
                    "lengths_versus_standard_interpretation"
                ]
            )
            != expected_interpretation_value
        ):
            interpretation_errors.append(source_id)

        legacy_identity_hash = sha256_payload(
            [CONTRACT_VERSION, source_id, CALCULATION_METHOD]
        )
        legacy_expected_id = f"PIB1-{legacy_identity_hash[:24].upper()}"
        legacy_expected_evidence_hash = sha256_payload(
            [
                legacy_expected_id,
                text(source["lengths_versus_standard_evidence_sha256"]),
                format_decimal(source_lengths),
                expected_interpretation_value,
            ]
        )
        recovered_payload = "\x1f".join([source_id])
        recovered_expected_id = (
            "PIBR-"
            + hashlib.sha256(recovered_payload.encode("utf-8")).hexdigest()[:24].upper()
        )
        recovered_expected_evidence_hash = hashlib.sha256(
            (
                text(source["lengths_versus_standard_evidence_sha256"])
                + "PIB_RECOVERED"
            ).encode("utf-8")
        ).hexdigest()
        actual_id = text(fact["performance_intelligence_base_id"])
        actual_evidence = text(fact["performance_intelligence_base_evidence_sha256"])
        if not (
            (actual_id == legacy_expected_id and actual_evidence == legacy_expected_evidence_hash)
            or (actual_id == recovered_expected_id and actual_evidence == recovered_expected_evidence_hash)
        ):
            identity_errors.append(source_id)

        if (
            text(
                fact[
                    "source_lengths_versus_standard_evidence_sha256"
                ]
            )
            != text(
                source[
                    "lengths_versus_standard_evidence_sha256"
                ]
            )
            or text(fact["race_time_delta_id"])
            != text(source["race_time_delta_id"])
            or text(fact["benchmark_observation_id"])
            != text(source["benchmark_observation_id"])
            or text(fact["benchmark_group_id"])
            != text(source["benchmark_group_id"])
            or text(fact["standard_time_id"])
            != text(source["standard_time_id"])
            or text(
                fact["length_conversion_parameter_id"]
            )
            != text(
                source["length_conversion_parameter_id"]
            )
        ):
            lineage_errors.append(source_id)

        allowed_statuses = {
            "OBSERVED_GOVERNED",
            "OBSERVED_GOVERNED_RECOVERED_TIMING",
        }
        allowed_methods = {
            CALCULATION_METHOD,
            "DIRECT_GOVERNED_RECOVERED_LENGTHS_VERSUS_STANDARD",
        }
        if (
            text(fact["performance_status"]) not in allowed_statuses
            or text(fact["calculation_method"]) not in allowed_methods
            or text(fact["contract_version"]) != CONTRACT_VERSION
        ):
            governance_errors.append(source_id)

    check(
        "raw_performance_measure_exact",
        not calculation_errors,
        calculation_errors,
    )

    check(
        "performance_interpretation_correct",
        not interpretation_errors,
        interpretation_errors,
    )

    check(
        "deterministic_identity_and_evidence",
        not identity_errors,
        identity_errors,
    )

    check(
        "canonical_lineage",
        not lineage_errors,
        lineage_errors,
    )

    check(
        "performance_governance",
        not governance_errors,
        governance_errors,
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
        len(source_rows) == len(fact_rows)
    )

    check(
        "current_population_expected",
        current_population_expected,
        {
            "lengths_versus_standard_rows": len(
                source_rows
            ),
            "performance_intelligence_base_rows": len(
                fact_rows
            ),
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
            "edgeiq_performance_intelligence_base_fact_v1"
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
            "lengths_versus_standard_rows": len(
                source_rows
            ),
            "performance_intelligence_base_rows": len(
                fact_rows
            ),
        },
        "failed_checks": failed_checks,
        "checks": checks,
    }

    atomic_write_json(
        AUDIT_PATH,
        payload,
    )

    if status != "PASS":
        print(json.dumps(payload, indent=2))

        raise SystemExit(
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_BASE_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_BASE_FACT_V1_AUDIT_PASS"
    )

    for name, value in payload["counts"].items():
        print(f"{name}={value}")

    print(f"audit_output={AUDIT_PATH}")


if __name__ == "__main__":
    main()
