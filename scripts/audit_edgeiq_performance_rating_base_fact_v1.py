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
    DATA / "edgeiq_performance_normalisation_fact_v1.csv"
)

FACT_PATH = (
    DATA / "edgeiq_performance_rating_base_fact_v1.csv"
)

AUDIT_PATH = (
    DATA / "edgeiq_performance_rating_base_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_performance_rating_base_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"
RATING_METHOD = "DIRECT_NORMALISED_PERFORMANCE_VALUE"
RATING_STATUS = "OBSERVED_NORMALISED_GOVERNED"


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
                "edgeiq_performance_rating_base_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(AUDIT_PATH, payload)

        raise SystemExit(
            "EDGEIQ_PERFORMANCE_RATING_BASE_FACT_V1_AUDIT_FAIL"
        )

    _, source_rows = read_csv(SOURCE_PATH)
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
    canonical_field_count = fact_fields.count("winner_canonical_horse_id")
    canonical_field_index = (
        fact_fields.index("winner_canonical_horse_id")
        if canonical_field_count == 1
        else -1
    )
    winner_name_index = (
        fact_fields.index("winner_horse_name")
        if "winner_horse_name" in fact_fields
        else -1
    )
    check(
        "winner_canonical_horse_id_field_order",
        canonical_field_count == 1
        and canonical_field_index == winner_name_index - 1
        and canonical_field_index == 10,
        {
            "winner_canonical_horse_id_count": canonical_field_count,
            "winner_canonical_horse_id_index": canonical_field_index,
            "winner_horse_name_index": winner_name_index,
        },
    )

    source_by_id = {
        text(row["performance_normalisation_id"]): row
        for row in source_rows
    }

    fact_source_ids = [
        text(row["performance_normalisation_id"])
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

    duplicate_rating_ids = sorted(
        value
        for value, count in Counter(
            text(row["performance_rating_base_id"])
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_source_ids = sorted(
        value
        for value, count in Counter(
            fact_source_ids
        ).items()
        if value and count != 1
    )

    check(
        "unique_performance_rating_base_ids",
        not duplicate_rating_ids,
        duplicate_rating_ids,
    )

    check(
        "one_row_per_normalisation_observation",
        not duplicate_source_ids,
        duplicate_source_ids,
    )

    value_errors: list[str] = []
    identity_errors: list[str] = []
    canonical_identity_errors: list[str] = []
    canonical_identity_blanks: list[str] = []
    canonical_identity_conflicts: list[str] = []
    lineage_errors: list[str] = []
    governance_errors: list[str] = []
    horse_ids_by_source: dict[str, set[str]] = {}

    for fact in fact_rows:
        source_id = text(
            fact["performance_normalisation_id"]
        )

        source = source_by_id.get(source_id)

        if source is None:
            lineage_errors.append(
                f"{source_id}: unknown source row"
            )
            continue

        source_value = Decimal(
            text(source["normalised_performance_value"])
        )

        fact_normalised_value = Decimal(
            text(fact["normalised_performance_value"])
        )

        fact_rating_value = Decimal(
            text(fact["rating_base_value"])
        )

        if (
            format_decimal(source_value)
            != format_decimal(fact_normalised_value)
            or format_decimal(source_value)
            != format_decimal(fact_rating_value)
        ):
            value_errors.append(source_id)

        source_horse_id = text(source.get("winner_canonical_horse_id"))
        fact_horse_id = text(fact.get("winner_canonical_horse_id"))
        if source_horse_id and not fact_horse_id:
            canonical_identity_blanks.append(source_id)
        if source_horse_id != fact_horse_id:
            canonical_identity_errors.append(
                f"{source_id}:source={source_horse_id}:fact={fact_horse_id}"
            )
        if source_id:
            horse_ids_by_source.setdefault(source_id, set()).add(fact_horse_id)

        source_evidence_hash = text(
            source[
                "performance_normalisation_evidence_sha256"
            ]
        )

        identity_hash_v1 = sha256_payload(
            [
                CONTRACT_VERSION,
                source_id,
                RATING_METHOD,
            ]
        )
        expected_id_v1 = f"PRB1-{identity_hash_v1[:24].upper()}"
        expected_evidence_hash_v1 = sha256_payload(
            [
                expected_id_v1,
                source_evidence_hash,
                format_decimal(source_value),
                RATING_STATUS,
            ]
        )

        expected_id_v2 = "PRB2-" + sha256_payload(
            [
                CONTRACT_VERSION,
                source_id,
                format_decimal(source_value),
                RATING_STATUS,
            ]
        )[:24].upper()
        expected_evidence_hash_v2 = sha256_payload(
            [
                expected_id_v2,
                source_evidence_hash,
                format_decimal(source_value),
                RATING_STATUS,
            ]
        )

        actual_id = text(fact["performance_rating_base_id"])
        actual_evidence_hash = text(
            fact[
                "performance_rating_base_evidence_sha256"
            ]
        )

        if (actual_id, actual_evidence_hash) not in {
            (expected_id_v1, expected_evidence_hash_v1),
            (expected_id_v2, expected_evidence_hash_v2),
        }:
            identity_errors.append(source_id)

        if (
            text(
                fact[
                    "source_performance_normalisation_evidence_sha256"
                ]
            )
            != text(
                source[
                    "performance_normalisation_evidence_sha256"
                ]
            )
            or text(
                fact["performance_intelligence_base_id"]
            )
            != text(
                source["performance_intelligence_base_id"]
            )
            or text(fact["normalisation_parameter_id"])
            != text(source["normalisation_parameter_id"])
            or text(fact["lengths_versus_standard_id"])
            != text(source["lengths_versus_standard_id"])
            or text(fact["benchmark_observation_id"])
            != text(source["benchmark_observation_id"])
        ):
            lineage_errors.append(source_id)

        if (
            text(fact["rating_method"]) != RATING_METHOD
            or text(fact["rating_status"]) != RATING_STATUS
            or text(fact["contract_version"])
            != CONTRACT_VERSION
        ):
            governance_errors.append(source_id)

    for source_id, horse_ids in horse_ids_by_source.items():
        nonblank_ids = {horse_id for horse_id in horse_ids if horse_id}
        if len(nonblank_ids) > 1:
            canonical_identity_conflicts.append(
                f"{source_id}:{sorted(nonblank_ids)}"
            )

    check(
        "rating_base_value_exact",
        not value_errors,
        value_errors,
    )

    check(
        "deterministic_identity_and_evidence",
        not identity_errors,
        identity_errors,
    )
    check(
        "winner_canonical_horse_id_direct_pass_through",
        not canonical_identity_errors,
        canonical_identity_errors,
    )
    check(
        "winner_canonical_horse_id_nonblank_when_source_present",
        not canonical_identity_blanks,
        canonical_identity_blanks,
    )
    check(
        "winner_canonical_horse_id_no_duplicate_conflict",
        not canonical_identity_conflicts,
        canonical_identity_conflicts,
    )

    check(
        "canonical_lineage",
        not lineage_errors,
        lineage_errors,
    )

    check(
        "rating_governance",
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
            "performance_normalisation_rows": len(
                source_rows
            ),
            "performance_rating_base_rows": len(
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
            "edgeiq_performance_rating_base_fact_v1"
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
            "performance_normalisation_rows": len(
                source_rows
            ),
            "performance_rating_base_rows": len(
                fact_rows
            ),
        },
        "failed_checks": failed_checks,
        "checks": checks,
    }

    atomic_write_json(AUDIT_PATH, payload)

    if status != "PASS":
        print(json.dumps(payload, indent=2))

        raise SystemExit(
            "EDGEIQ_PERFORMANCE_RATING_BASE_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_PERFORMANCE_RATING_BASE_FACT_V1_AUDIT_PASS"
    )
    print(
        "performance_normalisation_rows="
        f"{len(source_rows)}"
    )
    print(
        "performance_rating_base_rows="
        f"{len(fact_rows)}"
    )
    print(f"audit_output={AUDIT_PATH}")


if __name__ == "__main__":
    main()
