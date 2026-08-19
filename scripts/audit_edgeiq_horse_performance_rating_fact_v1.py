from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = (
    DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv"
)

FACT_PATH = (
    DATA / "edgeiq_horse_performance_rating_fact_v1.csv"
)

AUDIT_PATH = (
    DATA / "edgeiq_horse_performance_rating_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_horse_performance_rating_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"
RATING_METHOD = "DIRECT_HISTORICAL_AGGREGATE_VALUE"
RATING_STATUS = "HISTORICAL_HORSE_RATING_GOVERNED"
SOURCE_AGGREGATE_STATUS = "HISTORICAL_AGGREGATE_GOVERNED"


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
                "edgeiq_horse_performance_rating_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(AUDIT_PATH, payload)

        raise SystemExit(
            "EDGEIQ_HORSE_PERFORMANCE_RATING_FACT_V1_AUDIT_FAIL"
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

    source_by_id = {
        text(row["horse_performance_aggregate_id"]): row
        for row in source_rows
    }

    source_ids = set(source_by_id)

    fact_source_ids = [
        text(row["horse_performance_aggregate_id"])
        for row in fact_rows
    ]

    check(
        "source_population_exact",
        source_ids == set(fact_source_ids),
        {
            "source_rows": len(source_rows),
            "fact_rows": len(fact_rows),
            "missing": sorted(
                source_ids - set(fact_source_ids)
            ),
            "unexpected": sorted(
                set(fact_source_ids) - source_ids
            ),
        },
    )

    duplicate_rating_ids = sorted(
        value
        for value, count in Counter(
            text(row["horse_performance_rating_id"])
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_aggregate_links = sorted(
        value
        for value, count in Counter(
            fact_source_ids
        ).items()
        if value and count != 1
    )

    check(
        "unique_horse_performance_rating_ids",
        not duplicate_rating_ids,
        duplicate_rating_ids,
    )

    check(
        "one_rating_per_aggregate",
        not duplicate_aggregate_links,
        duplicate_aggregate_links,
    )

    value_errors: list[str] = []
    identity_errors: list[str] = []
    lineage_errors: list[str] = []
    governance_errors: list[str] = []

    for fact in fact_rows:
        aggregate_id = text(
            fact["horse_performance_aggregate_id"]
        )

        source = source_by_id.get(aggregate_id)

        if source is None:
            lineage_errors.append(
                f"{aggregate_id}: unknown aggregate"
            )
            continue

        try:
            date.fromisoformat(
                text(fact["rating_as_of_date"])
            )

            source_value = Decimal(
                text(source["aggregate_rating_value"])
            )

            fact_aggregate_value = Decimal(
                text(fact["aggregate_rating_value"])
            )

            fact_rating_value = Decimal(
                text(
                    fact[
                        "horse_performance_rating_value"
                    ]
                )
            )

            included_observation_count = int(
                text(fact["included_observation_count"])
            )
        except Exception as exc:
            governance_errors.append(
                f"{aggregate_id}:{type(exc).__name__}"
            )
            continue

        if (
            not source_value.is_finite()
            or not fact_aggregate_value.is_finite()
            or not fact_rating_value.is_finite()
            or included_observation_count <= 0
        ):
            governance_errors.append(aggregate_id)

        if (
            format_decimal(source_value)
            != format_decimal(fact_aggregate_value)
            or format_decimal(source_value)
            != format_decimal(fact_rating_value)
        ):
            value_errors.append(aggregate_id)

        canonical_horse_id = text(
            fact["canonical_horse_id"]
        )

        identity_hash_v1 = sha256_payload(
            [
                CONTRACT_VERSION,
                aggregate_id,
                canonical_horse_id,
                RATING_METHOD,
            ]
        )
        expected_id_v1 = f"HPR1-{identity_hash_v1[:24].upper()}"

        source_evidence_hash = text(
            source[
                "horse_performance_aggregate_evidence_sha256"
            ]
        )

        expected_evidence_hash_v1 = sha256_payload(
            [
                expected_id_v1,
                source_evidence_hash,
                format_decimal(source_value),
                RATING_STATUS,
            ]
        )

        expected_id_v2 = "HPR2-" + sha256_payload(
            [
                CONTRACT_VERSION,
                aggregate_id,
                canonical_horse_id,
                text(fact["rating_as_of_date"]),
                format_decimal(source_value),
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

        actual_id = text(fact["horse_performance_rating_id"])
        actual_evidence_hash = text(
            fact[
                "horse_performance_rating_evidence_sha256"
            ]
        )

        if (actual_id, actual_evidence_hash) not in {
            (expected_id_v1, expected_evidence_hash_v1),
            (expected_id_v2, expected_evidence_hash_v2),
        }:
            identity_errors.append(aggregate_id)

        if (
            text(fact["canonical_horse_id"])
            != text(source["canonical_horse_id"])
            or text(fact["canonical_horse_name"])
            != text(source["canonical_horse_name"])
            or text(fact["rating_as_of_date"])
            != text(source["aggregate_as_of_date"])
            or text(
                fact[
                    "horse_performance_aggregation_parameter_id"
                ]
            )
            != text(
                source[
                    "horse_performance_aggregation_parameter_id"
                ]
            )
            or text(fact["aggregation_method"])
            != text(source["aggregation_method"])
            or text(
                fact[
                    "source_horse_performance_aggregate_evidence_sha256"
                ]
            )
            != source_evidence_hash
        ):
            lineage_errors.append(aggregate_id)

        if (
            text(source["aggregate_status"])
            != SOURCE_AGGREGATE_STATUS
            or text(
                fact["horse_performance_rating_method"]
            )
            != RATING_METHOD
            or text(
                fact["horse_performance_rating_status"]
            )
            != RATING_STATUS
            or text(fact["contract_version"])
            != CONTRACT_VERSION
            or not text(fact["canonical_horse_id"])
            or not text(fact["canonical_horse_name"])
            or not text(
                fact["aggregation_model_version"]
            )
        ):
            governance_errors.append(aggregate_id)

    check(
        "rating_value_exact",
        not value_errors,
        value_errors,
    )

    check(
        "deterministic_identity_and_evidence",
        not identity_errors,
        identity_errors,
    )

    check(
        "canonical_aggregate_lineage",
        not lineage_errors,
        lineage_errors,
    )

    check(
        "horse_rating_governance",
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
            "horse_performance_aggregate_rows": len(
                source_rows
            ),
            "horse_performance_rating_rows": len(
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
            "edgeiq_horse_performance_rating_fact_v1"
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
            "horse_performance_aggregate_rows": len(
                source_rows
            ),
            "horse_performance_rating_rows": len(
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
            "EDGEIQ_HORSE_PERFORMANCE_RATING_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_HORSE_PERFORMANCE_RATING_FACT_V1_AUDIT_PASS"
    )
    print(
        "horse_performance_aggregate_rows="
        f"{len(source_rows)}"
    )
    print(
        "horse_performance_rating_rows="
        f"{len(fact_rows)}"
    )
    print(f"audit_output={AUDIT_PATH}")


if __name__ == "__main__":
    main()
