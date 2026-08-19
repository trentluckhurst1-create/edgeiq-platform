from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_relative_context_fact_v1.csv"
)

EPI_PATH = (
    DATA
    / "edgeiq_race_entry_epi_fact_v1.csv"
)

DISTRIBUTION_PATH = (
    DATA
    / "edgeiq_race_epi_distribution_fact_v1.csv"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_epi_relative_context_fact_v1_contract.json"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_relative_context_fact_v1_audit.json"
)

CONTRACT_VERSION = "1.0.0"
QUANTUM = Decimal("0.000001")

EXPECTED_PUBLICATION = (
    "EPI_RELATIVE_CONTEXT_PUBLISHED"
)

EXPECTED_RECONCILIATION = (
    "EPI_RELATIVE_CONTEXT_RECONCILED"
)

EXPECTED_STATUS = (
    "GOVERNED_RACE_ENTRY_EPI_RELATIVE_CONTEXT"
)


def text(value: object) -> str:
    return str(
        value if value is not None else ""
    ).strip()


def sha256_payload(
    parts: Iterable[object],
) -> str:
    payload = "\x1f".join(
        text(part)
        for part in parts
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def parse_decimal(
    value: object,
) -> Decimal | None:
    raw = text(value)

    if not raw:
        return None

    try:
        parsed = Decimal(raw)
    except InvalidOperation:
        return None

    if not parsed.is_finite():
        return None

    return parsed


def decimal_text(
    value: Decimal,
) -> str:
    return format(
        value.quantize(
            QUANTUM,
            rounding=ROUND_HALF_EVEN,
        ),
        ".6f",
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
            raise RuntimeError(
                f"Missing CSV header: {path}"
            )

        return list(reader.fieldnames), list(reader)


def atomic_write_json(
    path: Path,
    payload: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )

    os.close(descriptor)
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

        os.replace(
            temporary_path,
            path,
        )

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
            "status": (
                "PASS"
                if passed
                else "FAIL"
            ),
            "detail": detail,
        }

    required_paths = [
        FACT_PATH,
        EPI_PATH,
        DISTRIBUTION_PATH,
        CONTRACT_PATH,
    ]

    missing_paths = [
        str(
            path.relative_to(ROOT)
        )
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
                "edgeiq_race_entry_epi_relative_context_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(
            AUDIT_PATH,
            payload,
        )

        raise SystemExit(
            "EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_AUDIT_FAIL"
        )

    fact_fields, fact_rows = read_csv(
        FACT_PATH
    )

    epi_fields, epi_rows = read_csv(
        EPI_PATH
    )

    distribution_fields, distribution_rows = read_csv(
        DISTRIBUTION_PATH
    )

    contract = json.loads(
        CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    check(
        "contract_fields_exact",
        fact_fields
        == contract[
            "required_fields"
        ],
        {
            "actual": fact_fields,
            "expected": contract[
                "required_fields"
            ],
        },
    )

    forbidden_fields = sorted(
        set(
            contract[
                "forbidden_fields"
            ]
        ).intersection(
            fact_fields
        )
    )

    check(
        "no_forbidden_fields",
        not forbidden_fields,
        forbidden_fields,
    )

    epi_by_entry = {
        text(
            row.get(
                "race_entry_id"
            )
        ): row
        for row in epi_rows
    }

    distribution_by_race = {
        (
            text(
                row.get(
                    "race_id"
                )
            ),
            text(
                row.get(
                    "race_date"
                )
            ),
        ): row
        for row in distribution_rows
    }

    check(
        "published_population_exact",
        {
            text(
                row.get(
                    "race_entry_id"
                )
            )
            for row in fact_rows
        }
        == set(
            epi_by_entry
        ),
        {
            "fact_rows": len(
                fact_rows
            ),
            "epi_rows": len(
                epi_rows
            ),
        },
    )

    duplicate_primary_keys = sorted(
        value
        for value, count in Counter(
            text(
                row.get(
                    "race_entry_epi_relative_context_id"
                )
            )
            for row in fact_rows
        ).items()
        if value
        and count != 1
    )

    duplicate_natural_keys = sorted(
        value
        for value, count in Counter(
            text(
                row.get(
                    "race_entry_id"
                )
            )
            for row in fact_rows
        ).items()
        if value
        and count != 1
    )

    check(
        "primary_keys_unique",
        not duplicate_primary_keys,
        duplicate_primary_keys,
    )

    check(
        "natural_keys_unique",
        not duplicate_natural_keys,
        duplicate_natural_keys,
    )

    identity_errors: list[str] = []
    join_errors: list[str] = []
    arithmetic_errors: list[str] = []
    governance_errors: list[str] = []
    evidence_errors: list[str] = []
    lineage_errors: list[str] = []

    with localcontext() as context:
        context.prec = 50

        for row in fact_rows:
            context_id = text(
                row.get(
                    "race_entry_epi_relative_context_id"
                )
            )

            race_entry_id = text(
                row.get(
                    "race_entry_id"
                )
            )

            source_epi = epi_by_entry.get(
                race_entry_id
            )

            if source_epi is None:
                join_errors.append(
                    f"{race_entry_id}:missing_epi_source"
                )
                continue

            race_entry_epi_id = text(
                source_epi.get(
                    "race_entry_epi_id"
                )
            )

            race_id = text(
                source_epi.get(
                    "race_id"
                )
            )

            race_date = text(
                source_epi.get(
                    "race_date"
                )
            )

            distribution = distribution_by_race.get(
                (
                    race_id,
                    race_date,
                )
            )

            if distribution is None:
                join_errors.append(
                    f"{race_entry_id}:missing_distribution"
                )
                continue

            distribution_id = text(
                distribution.get(
                    "race_epi_distribution_id"
                )
            )

            expected_identity_hash = sha256_payload(
                [
                    CONTRACT_VERSION,
                    race_entry_id,
                    race_entry_epi_id,
                    race_id,
                    race_date,
                    distribution_id,
                    text(
                        row.get(
                            "epi_relative_context_publication_decision"
                        )
                    ),
                ]
            )

            expected_context_id = (
                f"REERC1-"
                f"{expected_identity_hash[:24].upper()}"
            )

            if context_id != expected_context_id:
                identity_errors.append(
                    context_id
                    or race_entry_id
                )

            expected_identity_fields = {
                "race_entry_epi_id": (
                    race_entry_epi_id
                ),
                "race_id": (
                    race_id
                ),
                "race_date": (
                    race_date
                ),
                "race_epi_distribution_id": (
                    distribution_id
                ),
                "race_entry_epi_evidence_sha256": text(
                    source_epi.get(
                        "race_entry_epi_evidence_sha256"
                    )
                ),
                "race_epi_distribution_evidence_sha256": text(
                    distribution.get(
                        "race_epi_distribution_evidence_sha256"
                    )
                ),
            }

            for field_name, expected_value in expected_identity_fields.items():
                if text(
                    row.get(
                        field_name
                    )
                ) != expected_value:
                    join_errors.append(
                        f"{race_entry_id}:{field_name}"
                    )

            runner_epi = parse_decimal(
                source_epi.get(
                    "epi_value"
                )
            )

            field_mean = parse_decimal(
                distribution.get(
                    "field_epi_mean"
                )
            )

            standard_deviation = parse_decimal(
                distribution.get(
                    "field_epi_population_standard_deviation"
                )
            )

            minimum_epi = parse_decimal(
                distribution.get(
                    "minimum_epi"
                )
            )

            maximum_epi = parse_decimal(
                distribution.get(
                    "maximum_epi"
                )
            )

            epi_range = parse_decimal(
                distribution.get(
                    "epi_range"
                )
            )

            if any(
                value is None
                for value in [
                    runner_epi,
                    field_mean,
                    standard_deviation,
                    minimum_epi,
                    maximum_epi,
                    epi_range,
                ]
            ):
                arithmetic_errors.append(
                    f"{race_entry_id}:invalid_source_numeric"
                )
                continue

            expected_minus_mean = (
                runner_epi
                - field_mean
            )

            expected_z_score = (
                Decimal("0")
                if standard_deviation == Decimal("0")
                else expected_minus_mean
                / standard_deviation
            )

            expected_above_minimum = (
                runner_epi
                - minimum_epi
            )

            expected_below_maximum = (
                maximum_epi
                - runner_epi
            )

            expected_numeric = {
                "runner_epi_value": (
                    runner_epi
                ),
                "field_epi_mean": (
                    field_mean
                ),
                "epi_minus_field_mean": (
                    expected_minus_mean
                ),
                "field_epi_population_standard_deviation": (
                    standard_deviation
                ),
                "epi_population_z_score": (
                    expected_z_score
                ),
                "minimum_epi": (
                    minimum_epi
                ),
                "maximum_epi": (
                    maximum_epi
                ),
                "epi_range": (
                    epi_range
                ),
                "distance_above_minimum_epi": (
                    expected_above_minimum
                ),
                "distance_below_maximum_epi": (
                    expected_below_maximum
                ),
            }

            for field_name, expected_value in expected_numeric.items():
                published = parse_decimal(
                    row.get(
                        field_name
                    )
                )

                if (
                    published is None
                    or published.quantize(
                        QUANTUM,
                        rounding=ROUND_HALF_EVEN,
                    )
                    != expected_value.quantize(
                        QUANTUM,
                        rounding=ROUND_HALF_EVEN,
                    )
                ):
                    arithmetic_errors.append(
                        f"{race_entry_id}:{field_name}"
                    )

            expected_population_count = text(
                distribution.get(
                    "eligible_epi_population_count"
                )
            )

            if text(
                row.get(
                    "eligible_epi_population_count"
                )
            ) != expected_population_count:
                arithmetic_errors.append(
                    f"{race_entry_id}:population_count"
                )

            if (
                expected_above_minimum < Decimal("0")
                or expected_below_maximum < Decimal("0")
            ):
                arithmetic_errors.append(
                    f"{race_entry_id}:negative_distance"
                )

            if (
                (
                    expected_above_minimum
                    + expected_below_maximum
                ).quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_EVEN,
                )
                != epi_range.quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_EVEN,
                )
            ):
                arithmetic_errors.append(
                    f"{race_entry_id}:range_reconciliation"
                )

            expected_governance = {
                "epi_relative_context_publication_decision": (
                    EXPECTED_PUBLICATION
                ),
                "epi_relative_context_reconciliation_decision": (
                    EXPECTED_RECONCILIATION
                ),
                "epi_relative_context_status": (
                    EXPECTED_STATUS
                ),
                "contract_version": (
                    CONTRACT_VERSION
                ),
            }

            for field_name, expected_value in expected_governance.items():
                if text(
                    row.get(
                        field_name
                    )
                ) != expected_value:
                    governance_errors.append(
                        f"{race_entry_id}:{field_name}"
                    )

            expected_source_lineage = (
                "edgeiq_race_entry_epi_fact_v1:"
                f"{race_entry_epi_id}"
                "|edgeiq_race_epi_distribution_fact_v1:"
                f"{distribution_id}"
            )

            if text(
                row.get(
                    "source_lineage"
                )
            ) != expected_source_lineage:
                lineage_errors.append(
                    f"{race_entry_id}:source_lineage"
                )

            expected_evidence = sha256_payload(
                [
                    context_id,
                    race_entry_id,
                    race_entry_epi_id,
                    race_id,
                    race_date,
                    distribution_id,
                    text(
                        row.get(
                            "runner_epi_value"
                        )
                    ),
                    text(
                        row.get(
                            "eligible_epi_population_count"
                        )
                    ),
                    text(
                        row.get(
                            "field_epi_mean"
                        )
                    ),
                    text(
                        row.get(
                            "epi_minus_field_mean"
                        )
                    ),
                    text(
                        row.get(
                            "field_epi_population_standard_deviation"
                        )
                    ),
                    text(
                        row.get(
                            "epi_population_z_score"
                        )
                    ),
                    text(
                        row.get(
                            "minimum_epi"
                        )
                    ),
                    text(
                        row.get(
                            "maximum_epi"
                        )
                    ),
                    text(
                        row.get(
                            "epi_range"
                        )
                    ),
                    text(
                        row.get(
                            "distance_above_minimum_epi"
                        )
                    ),
                    text(
                        row.get(
                            "distance_below_maximum_epi"
                        )
                    ),
                    text(
                        row.get(
                            "race_entry_epi_evidence_sha256"
                        )
                    ),
                    text(
                        row.get(
                            "race_epi_distribution_evidence_sha256"
                        )
                    ),
                    text(
                        row.get(
                            "epi_relative_context_publication_decision"
                        )
                    ),
                    text(
                        row.get(
                            "epi_relative_context_reconciliation_decision"
                        )
                    ),
                    text(
                        row.get(
                            "epi_relative_context_status"
                        )
                    ),
                    text(
                        row.get(
                            "source_lineage"
                        )
                    ),
                ]
            )

            if text(
                row.get(
                    "race_entry_epi_relative_context_evidence_sha256"
                )
            ) != expected_evidence:
                evidence_errors.append(
                    race_entry_id
                )

            for field_name in [
                "race_entry_epi_relative_context_id",
                "race_entry_id",
                "race_entry_epi_id",
                "race_id",
                "race_date",
                "race_epi_distribution_id",
                "race_entry_epi_evidence_sha256",
                "race_epi_distribution_evidence_sha256",
                "race_entry_epi_relative_context_evidence_sha256",
                "source_lineage",
                "builder_version",
                "contract_version",
                "built_at_utc",
            ]:
                if not text(
                    row.get(
                        field_name
                    )
                ):
                    lineage_errors.append(
                        f"{race_entry_id}:{field_name}"
                    )

    check(
        "deterministic_relative_context_identity",
        not identity_errors,
        identity_errors[:50],
    )

    check(
        "relative_context_sources_reconciled",
        not join_errors,
        join_errors[:50],
    )

    check(
        "relative_context_arithmetic_reconciled",
        not arithmetic_errors,
        arithmetic_errors[:50],
    )

    check(
        "relative_context_governance_exact",
        not governance_errors,
        governance_errors[:50],
    )

    check(
        "deterministic_relative_context_evidence",
        not evidence_errors,
        evidence_errors[:50],
    )

    check(
        "relative_context_lineage_complete",
        not lineage_errors,
        lineage_errors[:50],
    )

    failed_checks = [
        name
        for name, result in checks.items()
        if result[
            "status"
        ] != "PASS"
    ]

    status = (
        "PASS"
        if not failed_checks
        else "FAIL"
    )

    payload = {
        "audit_name": (
            "edgeiq_race_entry_epi_relative_context_fact_v1"
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
            "race_entry_epi_rows": len(
                epi_rows
            ),
            "race_epi_distribution_rows": len(
                distribution_rows
            ),
            "relative_context_rows": len(
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
        print(
            json.dumps(
                payload,
                indent=2,
            )
        )

        raise SystemExit(
            "EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_AUDIT_PASS"
    )
    print(
        f"race_entry_epi_rows={len(epi_rows)}"
    )
    print(
        f"race_epi_distribution_rows={len(distribution_rows)}"
    )
    print(
        f"relative_context_rows={len(fact_rows)}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
