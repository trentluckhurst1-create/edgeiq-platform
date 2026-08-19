from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FACT_PATH = (
    DATA
    / "edgeiq_race_epi_distribution_fact_v1.csv"
)

SOURCE_PATH = (
    DATA
    / "edgeiq_race_entry_epi_fact_v1.csv"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_epi_distribution_fact_v1_contract.json"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_epi_distribution_fact_v1_audit.json"
)

CONTRACT_VERSION = "1.0.0"

SOURCE_PUBLICATION = "EPI_PUBLISHED"
SOURCE_RECONCILIATION = "EPI_RECONCILED"
SOURCE_STATUS = "GOVERNED_RACE_ENTRY_EPI"

EXPECTED_PUBLICATION = (
    "RACE_EPI_DISTRIBUTION_PUBLISHED"
)

EXPECTED_RECONCILIATION = (
    "RACE_EPI_DISTRIBUTION_RECONCILED"
)

EXPECTED_STATUS = (
    "GOVERNED_RACE_EPI_DISTRIBUTION"
)

QUANTUM = Decimal("0.000001")


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
    checks: dict[
        str,
        dict[str, object],
    ] = {}

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
        SOURCE_PATH,
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
                "edgeiq_race_epi_distribution_fact_v1"
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
            "EDGEIQ_RACE_EPI_DISTRIBUTION_FACT_V1_AUDIT_FAIL"
        )

    fact_fields, fact_rows = read_csv(
        FACT_PATH
    )

    source_fields, source_rows = read_csv(
        SOURCE_PATH
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

    governed_source_errors: list[str] = []

    grouped_source: dict[
        tuple[str, str],
        list[dict[str, object]],
    ] = defaultdict(list)

    seen_source_epi_ids: set[str] = set()
    seen_source_entry_ids: set[str] = set()

    for row in source_rows:
        source_epi_id = text(
            row.get(
                "race_entry_epi_id"
            )
        )

        race_entry_id = text(
            row.get(
                "race_entry_id"
            )
        )

        race_id = text(
            row.get(
                "race_id"
            )
        )

        race_date = text(
            row.get(
                "race_date"
            )
        )

        evidence = text(
            row.get(
                "race_entry_epi_evidence_sha256"
            )
        )

        epi_value = parse_decimal(
            row.get(
                "epi_value"
            )
        )

        if not source_epi_id:
            governed_source_errors.append(
                "missing_source_epi_id"
            )
            continue

        if source_epi_id in seen_source_epi_ids:
            governed_source_errors.append(
                f"duplicate_source_epi_id:{source_epi_id}"
            )

        seen_source_epi_ids.add(
            source_epi_id
        )

        if not race_entry_id:
            governed_source_errors.append(
                f"{source_epi_id}:missing_race_entry_id"
            )
            continue

        if race_entry_id in seen_source_entry_ids:
            governed_source_errors.append(
                f"duplicate_source_race_entry_id:{race_entry_id}"
            )

        seen_source_entry_ids.add(
            race_entry_id
        )

        if not race_id or not race_date:
            governed_source_errors.append(
                f"{source_epi_id}:incomplete_race_identity"
            )
            continue

        if not evidence:
            governed_source_errors.append(
                f"{source_epi_id}:missing_evidence"
            )

        if epi_value is None:
            governed_source_errors.append(
                f"{source_epi_id}:invalid_epi"
            )
            continue

        if text(
            row.get(
                "epi_publication_decision"
            )
        ) != SOURCE_PUBLICATION:
            governed_source_errors.append(
                f"{source_epi_id}:publication"
            )

        if text(
            row.get(
                "epi_reconciliation_decision"
            )
        ) != SOURCE_RECONCILIATION:
            governed_source_errors.append(
                f"{source_epi_id}:reconciliation"
            )

        if text(
            row.get(
                "epi_status"
            )
        ) != SOURCE_STATUS:
            governed_source_errors.append(
                f"{source_epi_id}:status"
            )

        grouped_source[
            (
                race_id,
                race_date,
            )
        ].append(
            {
                "race_entry_epi_id": source_epi_id,
                "race_entry_id": race_entry_id,
                "epi_value": epi_value,
                "epi_value_text": decimal_text(
                    epi_value
                ),
                "source_evidence": evidence,
            }
        )

    check(
        "governed_source_population_valid",
        not governed_source_errors,
        governed_source_errors[:50],
    )

    expected_race_keys = set(
        grouped_source
    )

    actual_race_keys = {
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
        )
        for row in fact_rows
    }

    check(
        "published_race_population_exact",
        actual_race_keys
        == expected_race_keys,
        {
            "actual_count": len(
                actual_race_keys
            ),
            "expected_count": len(
                expected_race_keys
            ),
            "missing": sorted(
                expected_race_keys
                - actual_race_keys
            )[:50],
            "unexpected": sorted(
                actual_race_keys
                - expected_race_keys
            )[:50],
        },
    )

    duplicate_primary_keys = sorted(
        value
        for value, count in Counter(
            text(
                row.get(
                    "race_epi_distribution_id"
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
            )
            for row in fact_rows
        ).items()
        if count != 1
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
    arithmetic_errors: list[str] = []
    population_errors: list[str] = []
    governance_errors: list[str] = []
    evidence_errors: list[str] = []
    lineage_errors: list[str] = []

    with localcontext() as context:
        context.prec = 50

        for row in fact_rows:
            distribution_id = text(
                row.get(
                    "race_epi_distribution_id"
                )
            )

            race_id = text(
                row.get(
                    "race_id"
                )
            )

            race_date = text(
                row.get(
                    "race_date"
                )
            )

            race_key = (
                race_id,
                race_date,
            )

            source_population = sorted(
                grouped_source.get(
                    race_key,
                    [],
                ),
                key=lambda record: (
                    text(
                        record[
                            "race_entry_id"
                        ]
                    ),
                    text(
                        record[
                            "race_entry_epi_id"
                        ]
                    ),
                ),
            )

            if not source_population:
                population_errors.append(
                    f"{distribution_id}:missing_source_population"
                )
                continue

            population_count = len(
                source_population
            )

            epi_values = [
                record[
                    "epi_value"
                ]
                for record in source_population
            ]

            expected_total = sum(
                epi_values,
                Decimal("0"),
            )

            expected_mean = (
                expected_total
                / Decimal(
                    population_count
                )
            )

            expected_variance = (
                sum(
                    (
                        value - expected_mean
                    )
                    * (
                        value - expected_mean
                    )
                    for value in epi_values
                )
                / Decimal(
                    population_count
                )
            )

            expected_standard_deviation = (
                expected_variance.sqrt()
            )

            expected_minimum = min(
                epi_values
            )

            expected_maximum = max(
                epi_values
            )

            expected_range = (
                expected_maximum
                - expected_minimum
            )

            population_parts: list[object] = []

            for record in source_population:
                population_parts.extend(
                    [
                        record[
                            "race_entry_id"
                        ],
                        record[
                            "race_entry_epi_id"
                        ],
                        record[
                            "epi_value_text"
                        ],
                        record[
                            "source_evidence"
                        ],
                    ]
                )

            expected_population_hash = sha256_payload(
                population_parts
            )

            published_population_hash = text(
                row.get(
                    "source_population_sha256"
                )
            )

            if (
                published_population_hash
                != expected_population_hash
            ):
                population_errors.append(
                    f"{distribution_id}:population_hash"
                )

            publication = text(
                row.get(
                    "race_epi_distribution_publication_decision"
                )
            )

            expected_identity_hash = sha256_payload(
                [
                    CONTRACT_VERSION,
                    race_id,
                    race_date,
                    str(
                        population_count
                    ),
                    expected_population_hash,
                    publication,
                ]
            )

            expected_distribution_id = (
                f"REDIST1-"
                f"{expected_identity_hash[:24].upper()}"
            )

            if (
                distribution_id
                != expected_distribution_id
            ):
                identity_errors.append(
                    distribution_id
                    or (
                        f"{race_id}:"
                        f"{race_date}"
                    )
                )

            published_count = text(
                row.get(
                    "eligible_epi_population_count"
                )
            )

            if (
                published_count
                != str(
                    population_count
                )
            ):
                arithmetic_errors.append(
                    f"{distribution_id}:population_count"
                )

            expected_numeric = {
                "field_epi_total": expected_total,
                "field_epi_mean": expected_mean,
                "field_epi_population_variance": (
                    expected_variance
                ),
                "field_epi_population_standard_deviation": (
                    expected_standard_deviation
                ),
                "minimum_epi": expected_minimum,
                "maximum_epi": expected_maximum,
                "epi_range": expected_range,
            }

            for field_name, expected_value in expected_numeric.items():
                published_value = parse_decimal(
                    row.get(
                        field_name
                    )
                )

                if (
                    published_value is None
                    or published_value.quantize(
                        QUANTUM,
                        rounding=ROUND_HALF_EVEN,
                    )
                    != expected_value.quantize(
                        QUANTUM,
                        rounding=ROUND_HALF_EVEN,
                    )
                ):
                    arithmetic_errors.append(
                        f"{distribution_id}:{field_name}"
                    )

            published_minimum = parse_decimal(
                row.get(
                    "minimum_epi"
                )
            )

            published_maximum = parse_decimal(
                row.get(
                    "maximum_epi"
                )
            )

            published_range = parse_decimal(
                row.get(
                    "epi_range"
                )
            )

            published_variance = parse_decimal(
                row.get(
                    "field_epi_population_variance"
                )
            )

            published_standard_deviation = parse_decimal(
                row.get(
                    "field_epi_population_standard_deviation"
                )
            )

            if (
                published_minimum is not None
                and published_maximum is not None
                and published_minimum > published_maximum
            ):
                arithmetic_errors.append(
                    f"{distribution_id}:minimum_greater_than_maximum"
                )

            if (
                published_range is not None
                and published_range < Decimal("0")
            ):
                arithmetic_errors.append(
                    f"{distribution_id}:negative_range"
                )

            if (
                published_variance is not None
                and published_variance < Decimal("0")
            ):
                arithmetic_errors.append(
                    f"{distribution_id}:negative_variance"
                )

            if (
                published_standard_deviation is not None
                and published_standard_deviation < Decimal("0")
            ):
                arithmetic_errors.append(
                    f"{distribution_id}:negative_standard_deviation"
                )

            expected_governance = {
                "race_epi_distribution_publication_decision": (
                    EXPECTED_PUBLICATION
                ),
                "race_epi_distribution_reconciliation_decision": (
                    EXPECTED_RECONCILIATION
                ),
                "race_epi_distribution_status": (
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
                        f"{distribution_id}:{field_name}"
                    )

            expected_source_lineage = (
                "edgeiq_race_entry_epi_fact_v1:"
                + ",".join(
                    text(
                        record[
                            "race_entry_epi_id"
                        ]
                    )
                    for record in source_population
                )
            )

            if text(
                row.get(
                    "source_lineage"
                )
            ) != expected_source_lineage:
                lineage_errors.append(
                    f"{distribution_id}:source_lineage"
                )

            expected_evidence = sha256_payload(
                [
                    distribution_id,
                    race_id,
                    race_date,
                    text(
                        row.get(
                            "eligible_epi_population_count"
                        )
                    ),
                    text(
                        row.get(
                            "field_epi_total"
                        )
                    ),
                    text(
                        row.get(
                            "field_epi_mean"
                        )
                    ),
                    text(
                        row.get(
                            "field_epi_population_variance"
                        )
                    ),
                    text(
                        row.get(
                            "field_epi_population_standard_deviation"
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
                    published_population_hash,
                    publication,
                    text(
                        row.get(
                            "race_epi_distribution_reconciliation_decision"
                        )
                    ),
                    text(
                        row.get(
                            "race_epi_distribution_status"
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
                    "race_epi_distribution_evidence_sha256"
                )
            ) != expected_evidence:
                evidence_errors.append(
                    distribution_id
                )

            for field_name in [
                "race_epi_distribution_id",
                "race_id",
                "race_date",
                "source_population_sha256",
                "race_epi_distribution_evidence_sha256",
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
                        f"{distribution_id}:{field_name}"
                    )

    check(
        "deterministic_distribution_identity",
        not identity_errors,
        identity_errors[:50],
    )

    check(
        "distribution_population_reconciled",
        not population_errors,
        population_errors[:50],
    )

    check(
        "distribution_arithmetic_reconciled",
        not arithmetic_errors,
        arithmetic_errors[:50],
    )

    check(
        "distribution_governance_exact",
        not governance_errors,
        governance_errors[:50],
    )

    check(
        "deterministic_distribution_evidence",
        not evidence_errors,
        evidence_errors[:50],
    )

    check(
        "distribution_lineage_complete",
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
            "edgeiq_race_epi_distribution_fact_v1"
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
                source_rows
            ),
            "source_race_count": len(
                grouped_source
            ),
            "race_epi_distribution_rows": len(
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
            "EDGEIQ_RACE_EPI_DISTRIBUTION_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_EPI_DISTRIBUTION_FACT_V1_AUDIT_PASS"
    )
    print(
        f"race_entry_epi_rows={len(source_rows)}"
    )
    print(
        f"source_race_count={len(grouped_source)}"
    )
    print(
        f"race_epi_distribution_rows={len(fact_rows)}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
