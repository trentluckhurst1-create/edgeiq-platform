from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_fact_v1.csv"
)

COMPONENT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_component_fact_v1.csv"
)

PARAMETER_PATH = (
    DATA
    / "edgeiq_epi_parameter_fact_v1.csv"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_epi_fact_v1_contract.json"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_fact_v1_audit.json"
)

CONTRACT_VERSION = "1.0.0"
QUANTUM = Decimal("0.000001")

EXPECTED_COMPONENTS = {
    "HISTORICAL_PERFORMANCE",
    "SUITABILITY",
    "RACE_CONTEXT",
}

EXPECTED_METHODOLOGY = (
    "NORMALISED_WEIGHTED_ADDITIVE_EPI_V1"
)

EXPECTED_PUBLICATION = "EPI_PUBLISHED"
EXPECTED_RECONCILIATION = "EPI_RECONCILED"
EXPECTED_STATUS = "GOVERNED_RACE_ENTRY_EPI"


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
        COMPONENT_PATH,
        PARAMETER_PATH,
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
                "edgeiq_race_entry_epi_fact_v1"
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
            "EDGEIQ_RACE_ENTRY_EPI_FACT_V1_AUDIT_FAIL"
        )

    fact_fields, fact_rows = read_csv(
        FACT_PATH
    )

    component_fields, component_rows = read_csv(
        COMPONENT_PATH
    )

    parameter_fields, parameter_rows = read_csv(
        PARAMETER_PATH
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

    check(
        "one_epi_parameter_row",
        len(parameter_rows) == 1,
        {
            "row_count": len(
                parameter_rows
            ),
        },
    )

    parameter = (
        parameter_rows[0]
        if len(parameter_rows) == 1
        else {}
    )

    epi_parameter_id = text(
        parameter.get(
            "epi_parameter_id"
        )
    )

    expected_base = parse_decimal(
        parameter.get(
            "epi_base_value"
        )
    )

    expected_weights = {
        "HISTORICAL_PERFORMANCE": parse_decimal(
            parameter.get(
                "historical_performance_weight"
            )
        ),
        "SUITABILITY": parse_decimal(
            parameter.get(
                "suitability_weight"
            )
        ),
        "RACE_CONTEXT": parse_decimal(
            parameter.get(
                "race_context_weight"
            )
        ),
    }

    components_by_entry: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in component_rows:
        components_by_entry[
            text(
                row.get(
                    "race_entry_id"
                )
            )
        ].append(
            row
        )

    expected_eligible_entries = {
        race_entry_id
        for race_entry_id, rows in components_by_entry.items()
        if (
            race_entry_id
            and len(rows) == 3
            and {
                text(
                    row.get(
                        "epi_component_code"
                    )
                )
                for row in rows
            }
            == EXPECTED_COMPONENTS
        )
    }

    actual_entries = {
        text(
            row.get(
                "race_entry_id"
            )
        )
        for row in fact_rows
        if text(
            row.get(
                "race_entry_id"
            )
        )
    }

    check(
        "published_population_exact",
        actual_entries
        == expected_eligible_entries,
        {
            "actual_count": len(
                actual_entries
            ),
            "expected_count": len(
                expected_eligible_entries
            ),
            "missing": sorted(
                expected_eligible_entries
                - actual_entries
            )[:50],
            "unexpected": sorted(
                actual_entries
                - expected_eligible_entries
            )[:50],
        },
    )

    duplicate_primary_keys = sorted(
        value
        for value, count in Counter(
            text(
                row.get(
                    "race_entry_epi_id"
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
    arithmetic_errors: list[str] = []
    component_errors: list[str] = []
    parameter_errors: list[str] = []
    governance_errors: list[str] = []
    evidence_errors: list[str] = []
    lineage_errors: list[str] = []

    for row in fact_rows:
        race_entry_epi_id = text(
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

        historical_id = text(
            row.get(
                "historical_performance_component_id"
            )
        )

        suitability_id = text(
            row.get(
                "suitability_component_id"
            )
        )

        race_context_id = text(
            row.get(
                "race_context_component_id"
            )
        )

        row_parameter_id = text(
            row.get(
                "epi_parameter_id"
            )
        )

        publication = text(
            row.get(
                "epi_publication_decision"
            )
        )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_entry_id,
                race_id,
                race_date,
                row_parameter_id,
                historical_id,
                suitability_id,
                race_context_id,
                publication,
            ]
        )

        expected_id = (
            f"REEPI1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if race_entry_epi_id != expected_id:
            identity_errors.append(
                race_entry_epi_id
                or race_entry_id
            )

        source_components = components_by_entry.get(
            race_entry_id,
            [],
        )

        source_by_code = {
            text(
                source.get(
                    "epi_component_code"
                )
            ): source
            for source in source_components
        }

        if set(source_by_code) != EXPECTED_COMPONENTS:
            component_errors.append(
                f"{race_entry_id}:component_population"
            )
            continue

        historical_source = source_by_code[
            "HISTORICAL_PERFORMANCE"
        ]

        suitability_source = source_by_code[
            "SUITABILITY"
        ]

        race_context_source = source_by_code[
            "RACE_CONTEXT"
        ]

        expected_component_ids = {
            "historical_performance_component_id": text(
                historical_source.get(
                    "race_entry_epi_component_id"
                )
            ),
            "suitability_component_id": text(
                suitability_source.get(
                    "race_entry_epi_component_id"
                )
            ),
            "race_context_component_id": text(
                race_context_source.get(
                    "race_entry_epi_component_id"
                )
            ),
        }

        for field_name, expected_value in expected_component_ids.items():
            if text(
                row.get(
                    field_name
                )
            ) != expected_value:
                component_errors.append(
                    f"{race_entry_id}:{field_name}"
                )

        expected_component_evidence = {
            "historical_performance_component_evidence_sha256": text(
                historical_source.get(
                    "race_entry_epi_component_evidence_sha256"
                )
            ),
            "suitability_component_evidence_sha256": text(
                suitability_source.get(
                    "race_entry_epi_component_evidence_sha256"
                )
            ),
            "race_context_component_evidence_sha256": text(
                race_context_source.get(
                    "race_entry_epi_component_evidence_sha256"
                )
            ),
        }

        for field_name, expected_value in expected_component_evidence.items():
            if text(
                row.get(
                    field_name
                )
            ) != expected_value:
                component_errors.append(
                    f"{race_entry_id}:{field_name}"
                )

        component_values = {
            "HISTORICAL_PERFORMANCE": {
                "normalised": parse_decimal(
                    row.get(
                        "historical_performance_normalised_value"
                    )
                ),
                "weight": parse_decimal(
                    row.get(
                        "historical_performance_weight"
                    )
                ),
                "weighted": parse_decimal(
                    row.get(
                        "historical_performance_weighted_value"
                    )
                ),
                "source": historical_source,
            },
            "SUITABILITY": {
                "normalised": parse_decimal(
                    row.get(
                        "suitability_normalised_value"
                    )
                ),
                "weight": parse_decimal(
                    row.get(
                        "suitability_weight"
                    )
                ),
                "weighted": parse_decimal(
                    row.get(
                        "suitability_weighted_value"
                    )
                ),
                "source": suitability_source,
            },
            "RACE_CONTEXT": {
                "normalised": parse_decimal(
                    row.get(
                        "race_context_normalised_value"
                    )
                ),
                "weight": parse_decimal(
                    row.get(
                        "race_context_weight"
                    )
                ),
                "weighted": parse_decimal(
                    row.get(
                        "race_context_weighted_value"
                    )
                ),
                "source": race_context_source,
            },
        }

        for component_code, values in component_values.items():
            source = values[
                "source"
            ]

            source_normalised = parse_decimal(
                source.get(
                    "capped_normalised_component_value"
                )
            )

            source_weight = parse_decimal(
                source.get(
                    "authorised_component_weight"
                )
            )

            source_weighted = parse_decimal(
                source.get(
                    "weighted_component_value"
                )
            )

            if (
                values[
                    "normalised"
                ]
                != source_normalised
            ):
                component_errors.append(
                    f"{race_entry_id}:"
                    f"{component_code}:normalised"
                )

            if (
                values[
                    "weight"
                ]
                != source_weight
            ):
                component_errors.append(
                    f"{race_entry_id}:"
                    f"{component_code}:weight"
                )

            if (
                values[
                    "weighted"
                ]
                != source_weighted
            ):
                component_errors.append(
                    f"{race_entry_id}:"
                    f"{component_code}:weighted"
                )

            if (
                values[
                    "weight"
                ]
                != expected_weights.get(
                    component_code
                )
            ):
                parameter_errors.append(
                    f"{race_entry_id}:"
                    f"{component_code}:parameter_weight"
                )

        published_base = parse_decimal(
            row.get(
                "epi_base_value"
            )
        )

        total_weight = parse_decimal(
            row.get(
                "total_component_weight"
            )
        )

        weighted_total = parse_decimal(
            row.get(
                "weighted_component_total"
            )
        )

        epi_value = parse_decimal(
            row.get(
                "epi_value"
            )
        )

        if any(
            value is None
            for value in [
                published_base,
                total_weight,
                weighted_total,
                epi_value,
                *[
                    values[
                        "normalised"
                    ]
                    for values in component_values.values()
                ],
                *[
                    values[
                        "weight"
                    ]
                    for values in component_values.values()
                ],
                *[
                    values[
                        "weighted"
                    ]
                    for values in component_values.values()
                ],
            ]
        ):
            arithmetic_errors.append(
                f"{race_entry_id}:missing_numeric"
            )
        else:
            expected_total_weight = sum(
                (
                    values[
                        "weight"
                    ]
                    for values in component_values.values()
                ),
                Decimal("0"),
            )

            expected_weighted_total = sum(
                (
                    values[
                        "weighted"
                    ]
                    for values in component_values.values()
                ),
                Decimal("0"),
            )

            expected_epi = (
                published_base
                + expected_weighted_total
            )

            if published_base != expected_base:
                arithmetic_errors.append(
                    f"{race_entry_id}:base"
                )

            if (
                total_weight
                != expected_total_weight
                or total_weight
                != Decimal("1.000000")
            ):
                arithmetic_errors.append(
                    f"{race_entry_id}:total_weight"
                )

            if (
                weighted_total.quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_EVEN,
                )
                != expected_weighted_total.quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_EVEN,
                )
            ):
                arithmetic_errors.append(
                    f"{race_entry_id}:weighted_total"
                )

            if (
                epi_value.quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_EVEN,
                )
                != expected_epi.quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_EVEN,
                )
            ):
                arithmetic_errors.append(
                    f"{race_entry_id}:epi"
                )

        if row_parameter_id != epi_parameter_id:
            parameter_errors.append(
                f"{race_entry_id}:epi_parameter_id"
            )

        if text(
            row.get(
                "epi_methodology"
            )
        ) != EXPECTED_METHODOLOGY:
            parameter_errors.append(
                f"{race_entry_id}:methodology"
            )

        expected_governance = {
            "epi_publication_decision": (
                EXPECTED_PUBLICATION
            ),
            "epi_reconciliation_decision": (
                EXPECTED_RECONCILIATION
            ),
            "epi_status": (
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
            "edgeiq_race_entry_epi_component_fact_v1:"
            f"{historical_id},"
            f"{suitability_id},"
            f"{race_context_id}"
            "|edgeiq_epi_parameter_fact_v1:"
            f"{row_parameter_id}"
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
                race_entry_epi_id,
                race_entry_id,
                race_id,
                race_date,
                text(
                    row.get(
                        "epi_methodology"
                    )
                ),
                text(
                    row.get(
                        "epi_base_value"
                    )
                ),
                historical_id,
                text(
                    row.get(
                        "historical_performance_component_evidence_sha256"
                    )
                ),
                text(
                    row.get(
                        "historical_performance_normalised_value"
                    )
                ),
                text(
                    row.get(
                        "historical_performance_weight"
                    )
                ),
                text(
                    row.get(
                        "historical_performance_weighted_value"
                    )
                ),
                suitability_id,
                text(
                    row.get(
                        "suitability_component_evidence_sha256"
                    )
                ),
                text(
                    row.get(
                        "suitability_normalised_value"
                    )
                ),
                text(
                    row.get(
                        "suitability_weight"
                    )
                ),
                text(
                    row.get(
                        "suitability_weighted_value"
                    )
                ),
                race_context_id,
                text(
                    row.get(
                        "race_context_component_evidence_sha256"
                    )
                ),
                text(
                    row.get(
                        "race_context_normalised_value"
                    )
                ),
                text(
                    row.get(
                        "race_context_weight"
                    )
                ),
                text(
                    row.get(
                        "race_context_weighted_value"
                    )
                ),
                text(
                    row.get(
                        "total_component_weight"
                    )
                ),
                text(
                    row.get(
                        "weighted_component_total"
                    )
                ),
                text(
                    row.get(
                        "epi_value"
                    )
                ),
                row_parameter_id,
                publication,
                text(
                    row.get(
                        "epi_reconciliation_decision"
                    )
                ),
                text(
                    row.get(
                        "epi_status"
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
                "race_entry_epi_evidence_sha256"
            )
        ) != expected_evidence:
            evidence_errors.append(
                race_entry_id
            )

        for field_name in [
            "race_entry_epi_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "epi_methodology",
            "historical_performance_component_id",
            "historical_performance_component_evidence_sha256",
            "suitability_component_id",
            "suitability_component_evidence_sha256",
            "race_context_component_id",
            "race_context_component_evidence_sha256",
            "epi_parameter_id",
            "race_entry_epi_evidence_sha256",
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
        "deterministic_epi_identity",
        not identity_errors,
        identity_errors[:50],
    )

    check(
        "component_lineage_reconciled",
        not component_errors,
        component_errors[:50],
    )

    check(
        "epi_arithmetic_reconciled",
        not arithmetic_errors,
        arithmetic_errors[:50],
    )

    check(
        "epi_parameter_reconciled",
        not parameter_errors,
        parameter_errors[:50],
    )

    check(
        "epi_governance_exact",
        not governance_errors,
        governance_errors[:50],
    )

    check(
        "deterministic_epi_evidence",
        not evidence_errors,
        evidence_errors[:50],
    )

    check(
        "epi_lineage_complete",
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
            "edgeiq_race_entry_epi_fact_v1"
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
            "epi_component_rows": len(
                component_rows
            ),
            "eligible_race_entry_count": len(
                expected_eligible_entries
            ),
            "race_entry_epi_rows": len(
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
            "EDGEIQ_RACE_ENTRY_EPI_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_EPI_FACT_V1_AUDIT_PASS"
    )
    print(
        f"epi_component_rows={len(component_rows)}"
    )
    print(
        f"eligible_race_entry_count={len(expected_eligible_entries)}"
    )
    print(
        f"race_entry_epi_rows={len(fact_rows)}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
