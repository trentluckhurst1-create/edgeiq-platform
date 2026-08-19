from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

FACT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_epi_component_normalisation_parameter_fact_v1.csv"
)

AUDIT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_epi_component_normalisation_parameter_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_epi_component_normalisation_parameter_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

EXPECTED_PARAMETER_VERSION = (
    "EPI_NORMALISATION_V1_2026_01"
)

EXPECTED_COMPONENTS = {
    "HISTORICAL_PERFORMANCE",
    "SUITABILITY",
    "RACE_CONTEXT",
}

EXPECTED_METHODOLOGY = (
    "WITHIN_RACE_POPULATION_Z_SCORE_CAPPED_V1"
)

EXPECTED_POPULATION_SCOPE = (
    "COMPLETE_GOVERNED_ELIGIBLE_RACE_FIELD"
)

EXPECTED_STANDARD_DEVIATION_BASIS = (
    "POPULATION_N"
)

EXPECTED_PUBLICATION = (
    "EPI_NORMALISATION_PARAMETER_AUTHORISED"
)

EXPECTED_RECONCILIATION = (
    "EPI_NORMALISATION_PARAMETER_RECONCILED"
)

EXPECTED_STATUS = (
    "GOVERNED_EPI_NORMALISATION_PARAMETER"
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
    raw = text(
        value
    )

    if not raw:
        return None

    try:
        parsed = Decimal(
            raw
        )
    except InvalidOperation:
        return None

    if not parsed.is_finite():
        return None

    return parsed


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        if reader.fieldnames is None:
            raise RuntimeError(
                f"Missing CSV header: {path}"
            )

        return list(
            reader.fieldnames
        ), list(
            reader
        )


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

    os.close(
        descriptor
    )

    temporary_path = Path(
        temporary_name
    )

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
        checks[
            name
        ] = {
            "status": (
                "PASS"
                if passed
                else "FAIL"
            ),
            "detail": detail,
        }

    missing_paths = [
        str(
            path.relative_to(
                ROOT
            )
        )
        for path in [
            FACT_PATH,
            CONTRACT_PATH,
        ]
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
                "edgeiq_epi_component_normalisation_parameter_fact_v1"
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
            "EDGEIQ_EPI_COMPONENT_NORMALISATION_PARAMETER_FACT_V1_AUDIT_FAIL"
        )

    fact_fields, rows = read_csv(
        FACT_PATH
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

    check(
        "exact_parameter_row_count",
        len(
            rows
        ) == 3,
        {
            "row_count": len(
                rows
            ),
        },
    )

    actual_components = {
        text(
            row[
                "epi_component_code"
            ]
        )
        for row in rows
    }

    check(
        "component_population_exact",
        actual_components
        == EXPECTED_COMPONENTS,
        {
            "actual": sorted(
                actual_components
            ),
            "expected": sorted(
                EXPECTED_COMPONENTS
            ),
        },
    )

    duplicate_ids = sorted(
        value
        for value, count in Counter(
            text(
                row[
                    "epi_component_normalisation_parameter_id"
                ]
            )
            for row in rows
        ).items()
        if value
        and count != 1
    )

    duplicate_natural_keys = sorted(
        value
        for value, count in Counter(
            (
                text(
                    row[
                        "normalisation_parameter_version"
                    ]
                ),
                text(
                    row[
                        "epi_component_code"
                    ]
                ),
            )
            for row in rows
        ).items()
        if count != 1
    )

    check(
        "parameter_ids_unique",
        not duplicate_ids,
        duplicate_ids,
    )

    check(
        "natural_keys_unique",
        not duplicate_natural_keys,
        duplicate_natural_keys,
    )

    identity_errors: list[str] = []
    arithmetic_errors: list[str] = []
    governance_errors: list[str] = []
    evidence_errors: list[str] = []
    lineage_errors: list[str] = []

    for row in rows:
        component_code = text(
            row[
                "epi_component_code"
            ]
        )

        parameter_version = text(
            row[
                "normalisation_parameter_version"
            ]
        )

        methodology = text(
            row[
                "normalisation_methodology"
            ]
        )

        effective_from_date = text(
            row[
                "effective_from_date"
            ]
        )

        publication = text(
            row[
                "normalisation_parameter_publication_decision"
            ]
        )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                parameter_version,
                component_code,
                methodology,
                effective_from_date,
                publication,
            ]
        )

        expected_id = (
            f"EPINP1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if text(
            row[
                "epi_component_normalisation_parameter_id"
            ]
        ) != expected_id:
            identity_errors.append(
                component_code
            )

        lower_cap = parse_decimal(
            row[
                "normalised_lower_cap"
            ]
        )

        upper_cap = parse_decimal(
            row[
                "normalised_upper_cap"
            ]
        )

        if lower_cap != Decimal(
            "-3.000000"
        ):
            arithmetic_errors.append(
                f"{component_code}:lower_cap"
            )

        if upper_cap != Decimal(
            "3.000000"
        ):
            arithmetic_errors.append(
                f"{component_code}:upper_cap"
            )

        if (
            lower_cap is None
            or upper_cap is None
            or lower_cap >= upper_cap
        ):
            arithmetic_errors.append(
                f"{component_code}:cap_order"
            )

        expected_governance = {
            "normalisation_parameter_version": (
                EXPECTED_PARAMETER_VERSION
            ),
            "normalisation_methodology": (
                EXPECTED_METHODOLOGY
            ),
            "normalisation_population_scope": (
                EXPECTED_POPULATION_SCOPE
            ),
            "standard_deviation_basis": (
                EXPECTED_STANDARD_DEVIATION_BASIS
            ),
            "minimum_population_count": "2",
            "zero_variance_policy": (
                "FAIL_CLOSED"
            ),
            "normalisation_output_decimal_places": "6",
            "normalisation_rounding_mode": (
                "ROUND_HALF_EVEN"
            ),
            "effective_from_date": (
                "2026-01-01"
            ),
            "effective_to_date": "",
            "normalisation_parameter_publication_decision": (
                EXPECTED_PUBLICATION
            ),
            "normalisation_parameter_reconciliation_decision": (
                EXPECTED_RECONCILIATION
            ),
            "normalisation_parameter_status": (
                EXPECTED_STATUS
            ),
            "contract_version": (
                CONTRACT_VERSION
            ),
        }

        for field_name, expected_value in expected_governance.items():
            if text(
                row[
                    field_name
                ]
            ) != expected_value:
                governance_errors.append(
                    f"{component_code}:{field_name}"
                )

        expected_evidence = sha256_payload(
            [
                text(
                    row[
                        "epi_component_normalisation_parameter_id"
                    ]
                ),
                parameter_version,
                component_code,
                methodology,
                text(
                    row[
                        "normalisation_population_scope"
                    ]
                ),
                text(
                    row[
                        "standard_deviation_basis"
                    ]
                ),
                text(
                    row[
                        "minimum_population_count"
                    ]
                ),
                text(
                    row[
                        "normalised_lower_cap"
                    ]
                ),
                text(
                    row[
                        "normalised_upper_cap"
                    ]
                ),
                text(
                    row[
                        "zero_variance_policy"
                    ]
                ),
                text(
                    row[
                        "normalisation_output_decimal_places"
                    ]
                ),
                text(
                    row[
                        "normalisation_rounding_mode"
                    ]
                ),
                effective_from_date,
                text(
                    row[
                        "effective_to_date"
                    ]
                ),
                publication,
                text(
                    row[
                        "normalisation_parameter_reconciliation_decision"
                    ]
                ),
                text(
                    row[
                        "normalisation_parameter_status"
                    ]
                ),
            ]
        )

        if text(
            row[
                "normalisation_parameter_evidence_sha256"
            ]
        ) != expected_evidence:
            evidence_errors.append(
                component_code
            )

        for field_name in [
            "epi_component_normalisation_parameter_id",
            "normalisation_parameter_evidence_sha256",
            "builder_version",
            "contract_version",
            "built_at_utc",
        ]:
            if not text(
                row[
                    field_name
                ]
            ):
                lineage_errors.append(
                    f"{component_code}:{field_name}"
                )

    check(
        "deterministic_parameter_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "parameter_arithmetic_exact",
        not arithmetic_errors,
        arithmetic_errors,
    )

    check(
        "parameter_governance_exact",
        not governance_errors,
        governance_errors,
    )

    check(
        "deterministic_parameter_evidence",
        not evidence_errors,
        evidence_errors,
    )

    check(
        "parameter_lineage_complete",
        not lineage_errors,
        lineage_errors,
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
            "edgeiq_epi_component_normalisation_parameter_fact_v1"
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
            "normalisation_parameter_rows": len(
                rows
            ),
            "component_count": len(
                actual_components
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
            "EDGEIQ_EPI_COMPONENT_NORMALISATION_PARAMETER_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_EPI_COMPONENT_NORMALISATION_PARAMETER_FACT_V1_AUDIT_PASS"
    )
    print(
        f"normalisation_parameter_rows={len(rows)}"
    )
    print(
        f"component_count={len(actual_components)}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
