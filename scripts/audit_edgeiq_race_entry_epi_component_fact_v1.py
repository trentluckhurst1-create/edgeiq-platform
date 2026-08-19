from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_component_fact_v1.csv"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_epi_component_fact_v1_contract.json"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_component_fact_v1_audit.json"
)

EPI_PARAMETER_PATH = (
    DATA
    / "edgeiq_epi_parameter_fact_v1.csv"
)

NORMALISATION_PARAMETER_PATH = (
    DATA
    / "edgeiq_epi_component_normalisation_parameter_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"

EXPECTED_COMPONENTS = {
    "HISTORICAL_PERFORMANCE",
    "SUITABILITY",
    "RACE_CONTEXT",
}

EXPECTED_WEIGHTS = {
    "HISTORICAL_PERFORMANCE": Decimal(
        "0.500000"
    ),
    "SUITABILITY": Decimal(
        "0.300000"
    ),
    "RACE_CONTEXT": Decimal(
        "0.200000"
    ),
}

EXPECTED_PUBLICATION = (
    "EPI_COMPONENT_PUBLISHED"
)

EXPECTED_RECONCILIATION = (
    "EPI_COMPONENT_RECONCILED"
)

EXPECTED_STATUS = (
    "GOVERNED_RACE_ENTRY_EPI_COMPONENT"
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
    checks: dict[
        str,
        dict[str, object],
    ] = {}

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

    required_paths = [
        FACT_PATH,
        CONTRACT_PATH,
        EPI_PARAMETER_PATH,
        NORMALISATION_PARAMETER_PATH,
    ]

    missing_paths = [
        str(
            path.relative_to(
                ROOT
            )
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
                "edgeiq_race_entry_epi_component_fact_v1"
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
            "EDGEIQ_RACE_ENTRY_EPI_COMPONENT_FACT_V1_AUDIT_FAIL"
        )

    fields, rows = read_csv(
        FACT_PATH
    )

    contract = json.loads(
        CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    check(
        "contract_fields_exact",
        fields
        == contract[
            "required_fields"
        ],
        {
            "actual": fields,
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
            fields
        )
    )

    check(
        "no_forbidden_fields",
        not forbidden_fields,
        forbidden_fields,
    )

    epi_fields, epi_parameter_rows = read_csv(
        EPI_PARAMETER_PATH
    )

    normalisation_fields, normalisation_rows = read_csv(
        NORMALISATION_PARAMETER_PATH
    )

    check(
        "one_epi_parameter_row",
        len(
            epi_parameter_rows
        ) == 1,
        {
            "row_count": len(
                epi_parameter_rows
            ),
        },
    )

    check(
        "three_normalisation_parameter_rows",
        len(
            normalisation_rows
        ) == 3,
        {
            "row_count": len(
                normalisation_rows
            ),
        },
    )

    epi_parameter_id = (
        text(
            epi_parameter_rows[0].get(
                "epi_parameter_id"
            )
        )
        if len(
            epi_parameter_rows
        ) == 1
        else ""
    )

    normalisation_ids = {
        text(
            row.get(
                "epi_component_code"
            )
        ): text(
            row.get(
                "epi_component_normalisation_parameter_id"
            )
        )
        for row in normalisation_rows
    }

    duplicate_primary_keys = sorted(
        value
        for value, count in Counter(
            text(
                row.get(
                    "race_entry_epi_component_id"
                )
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
                    row.get(
                        "race_entry_id"
                    )
                ),
                text(
                    row.get(
                        "epi_component_code"
                    )
                ),
            )
            for row in rows
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

    components_by_entry: dict[
        str,
        set[str],
    ] = defaultdict(set)

    rows_by_race_component: dict[
        tuple[str, str, str],
        list[dict[str, str]],
    ] = defaultdict(list)

    identity_errors: list[str] = []
    numeric_errors: list[str] = []
    parameter_errors: list[str] = []
    governance_errors: list[str] = []
    evidence_errors: list[str] = []
    lineage_errors: list[str] = []

    for row in rows:
        component_id = text(
            row.get(
                "race_entry_epi_component_id"
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

        component_code = text(
            row.get(
                "epi_component_code"
            )
        )

        source_fact_id = text(
            row.get(
                "component_source_fact_id"
            )
        )

        row_epi_parameter_id = text(
            row.get(
                "epi_parameter_id"
            )
        )

        normalisation_parameter_id = text(
            row.get(
                "epi_component_normalisation_parameter_id"
            )
        )

        publication = text(
            row.get(
                "epi_component_publication_decision"
            )
        )

        components_by_entry[
            race_entry_id
        ].add(
            component_code
        )

        rows_by_race_component[
            (
                race_id,
                race_date,
                component_code,
            )
        ].append(
            row
        )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_entry_id,
                race_id,
                race_date,
                component_code,
                source_fact_id,
                row_epi_parameter_id,
                normalisation_parameter_id,
                publication,
            ]
        )

        expected_component_id = (
            f"REEPIC1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if component_id != expected_component_id:
            identity_errors.append(
                component_id
                or (
                    f"{race_entry_id}:"
                    f"{component_code}"
                )
            )

        if component_code not in EXPECTED_COMPONENTS:
            parameter_errors.append(
                f"{component_id}:component"
            )

        if row_epi_parameter_id != epi_parameter_id:
            parameter_errors.append(
                f"{component_id}:epi_parameter_id"
            )

        if (
            normalisation_parameter_id
            != normalisation_ids.get(
                component_code
            )
        ):
            parameter_errors.append(
                f"{component_id}:normalisation_parameter_id"
            )

        weight = parse_decimal(
            row.get(
                "authorised_component_weight"
            )
        )

        expected_weight = EXPECTED_WEIGHTS.get(
            component_code
        )

        if weight != expected_weight:
            parameter_errors.append(
                f"{component_id}:weight"
            )

        raw_value = parse_decimal(
            row.get(
                "raw_component_value"
            )
        )

        mean = parse_decimal(
            row.get(
                "field_component_mean"
            )
        )

        standard_deviation = parse_decimal(
            row.get(
                "field_component_population_standard_deviation"
            )
        )

        unbounded = parse_decimal(
            row.get(
                "unbounded_normalised_component_value"
            )
        )

        capped = parse_decimal(
            row.get(
                "capped_normalised_component_value"
            )
        )

        weighted = parse_decimal(
            row.get(
                "weighted_component_value"
            )
        )

        numeric_values = [
            raw_value,
            mean,
            standard_deviation,
            unbounded,
            capped,
            weight,
            weighted,
        ]

        if any(
            value is None
            for value in numeric_values
        ):
            numeric_errors.append(
                f"{component_id}:missing_numeric"
            )

        if (
            standard_deviation is not None
            and standard_deviation <= Decimal(
                "0"
            )
        ):
            numeric_errors.append(
                f"{component_id}:non_positive_standard_deviation"
            )

        if (
            capped is not None
            and (
                capped < Decimal(
                    "-3.000000"
                )
                or capped > Decimal(
                    "3.000000"
                )
            )
        ):
            numeric_errors.append(
                f"{component_id}:cap"
            )

        if (
            capped is not None
            and weight is not None
            and weighted is not None
            and (
                capped * weight
            ).quantize(
                Decimal(
                    "0.000001"
                )
            ) != weighted
        ):
            numeric_errors.append(
                f"{component_id}:weighted_arithmetic"
            )

        expected_governance = {
            "epi_component_publication_decision": (
                EXPECTED_PUBLICATION
            ),
            "epi_component_reconciliation_decision": (
                EXPECTED_RECONCILIATION
            ),
            "epi_component_status": (
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
                    f"{component_id}:{field_name}"
                )

        expected_evidence = sha256_payload(
            [
                component_id,
                race_entry_id,
                race_id,
                race_date,
                component_code,
                text(
                    row.get(
                        "component_source_fact_name"
                    )
                ),
                source_fact_id,
                text(
                    row.get(
                        "component_source_value_field"
                    )
                ),
                text(
                    row.get(
                        "component_source_evidence_sha256"
                    )
                ),
                text(
                    row.get(
                        "raw_component_value"
                    )
                ),
                text(
                    row.get(
                        "field_population_count"
                    )
                ),
                text(
                    row.get(
                        "field_component_mean"
                    )
                ),
                text(
                    row.get(
                        "field_component_population_standard_deviation"
                    )
                ),
                text(
                    row.get(
                        "unbounded_normalised_component_value"
                    )
                ),
                text(
                    row.get(
                        "capped_normalised_component_value"
                    )
                ),
                text(
                    row.get(
                        "authorised_component_weight"
                    )
                ),
                text(
                    row.get(
                        "weighted_component_value"
                    )
                ),
                row_epi_parameter_id,
                normalisation_parameter_id,
                publication,
                text(
                    row.get(
                        "epi_component_reconciliation_decision"
                    )
                ),
                text(
                    row.get(
                        "epi_component_status"
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
                "race_entry_epi_component_evidence_sha256"
            )
        ) != expected_evidence:
            evidence_errors.append(
                component_id
            )

        for field_name in [
            "race_entry_epi_component_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "component_source_fact_name",
            "component_source_fact_id",
            "component_source_value_field",
            "component_source_evidence_sha256",
            "epi_parameter_id",
            "epi_component_normalisation_parameter_id",
            "race_entry_epi_component_evidence_sha256",
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
                    f"{component_id}:{field_name}"
                )

    incomplete_entries = sorted(
        race_entry_id
        for race_entry_id, components in components_by_entry.items()
        if components != EXPECTED_COMPONENTS
    )

    check(
        "three_components_per_entry",
        not incomplete_entries,
        incomplete_entries[:50],
    )

    component_row_count_exact = (
        len(
            rows
        )
        == (
            len(
                components_by_entry
            )
            * 3
        )
    )

    check(
        "component_row_count_exact",
        component_row_count_exact,
        {
            "race_entry_count": len(
                components_by_entry
            ),
            "actual_component_rows": len(
                rows
            ),
            "expected_component_rows": (
                len(
                    components_by_entry
                )
                * 3
            ),
        },
    )

    population_stat_errors: list[str] = []

    for group_key, group_rows in rows_by_race_component.items():
        raw_values = [
            parse_decimal(
                row.get(
                    "raw_component_value"
                )
            )
            for row in group_rows
        ]

        if any(
            value is None
            for value in raw_values
        ):
            population_stat_errors.append(
                f"{group_key}:raw_values"
            )
            continue

        population_count = len(
            group_rows
        )

        expected_mean = (
            sum(
                raw_values,
                Decimal(
                    "0"
                ),
            )
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
                for value in raw_values
            )
            / Decimal(
                population_count
            )
        )

        if expected_variance <= Decimal(
            "0"
        ):
            population_stat_errors.append(
                f"{group_key}:variance"
            )
            continue

        expected_standard_deviation = (
            expected_variance.sqrt()
        )

        for row in group_rows:
            published_count = text(
                row.get(
                    "field_population_count"
                )
            )

            published_mean = parse_decimal(
                row.get(
                    "field_component_mean"
                )
            )

            published_standard_deviation = parse_decimal(
                row.get(
                    "field_component_population_standard_deviation"
                )
            )

            if published_count != str(
                population_count
            ):
                population_stat_errors.append(
                    f"{group_key}:population_count"
                )

            if (
                published_mean is None
                or published_mean.quantize(
                    Decimal(
                        "0.000001"
                    )
                )
                != expected_mean.quantize(
                    Decimal(
                        "0.000001"
                    )
                )
            ):
                population_stat_errors.append(
                    f"{group_key}:mean"
                )

            if (
                published_standard_deviation is None
                or published_standard_deviation.quantize(
                    Decimal(
                        "0.000001"
                    )
                )
                != expected_standard_deviation.quantize(
                    Decimal(
                        "0.000001"
                    )
                )
            ):
                population_stat_errors.append(
                    f"{group_key}:standard_deviation"
                )

    check(
        "deterministic_component_identity",
        not identity_errors,
        identity_errors[:50],
    )

    check(
        "component_numeric_integrity",
        not numeric_errors,
        numeric_errors[:50],
    )

    check(
        "component_parameters_exact",
        not parameter_errors,
        parameter_errors[:50],
    )

    check(
        "population_statistics_reconciled",
        not population_stat_errors,
        population_stat_errors[:50],
    )

    check(
        "component_governance_exact",
        not governance_errors,
        governance_errors[:50],
    )

    check(
        "deterministic_component_evidence",
        not evidence_errors,
        evidence_errors[:50],
    )

    check(
        "component_lineage_complete",
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
            "edgeiq_race_entry_epi_component_fact_v1"
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
            "race_entry_count": len(
                components_by_entry
            ),
            "epi_component_rows": len(
                rows
            ),
            "race_component_population_count": len(
                rows_by_race_component
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
            "EDGEIQ_RACE_ENTRY_EPI_COMPONENT_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_EPI_COMPONENT_FACT_V1_AUDIT_PASS"
    )
    print(
        f"race_entry_count={len(components_by_entry)}"
    )
    print(
        f"epi_component_rows={len(rows)}"
    )
    print(
        f"race_component_population_count={len(rows_by_race_component)}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
