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

ADJUSTED_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv"
)

COMPONENT_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_component_fact_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_aggregate_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_suitability_aggregate_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

COMPONENT_ORDER = [
    "DISTANCE",
    "CLASS",
    "TRACK",
    "TRACK_CONFIGURATION",
    "TRACK_CONDITION",
    "SURFACE",
    "BARRIER",
    "WEIGHT",
    "FIELD_SIZE",
]

COMPONENT_OUTPUT_FIELDS = {
    "DISTANCE": "distance_suitability_value",
    "CLASS": "class_suitability_value",
    "TRACK": "track_suitability_value",
    "TRACK_CONFIGURATION": (
        "track_configuration_suitability_value"
    ),
    "TRACK_CONDITION": (
        "track_condition_suitability_value"
    ),
    "SURFACE": "surface_suitability_value",
    "BARRIER": "barrier_suitability_value",
    "WEIGHT": "weight_suitability_value",
    "FIELD_SIZE": "field_size_suitability_value",
}


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
        checks[name] = {
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }

    required_paths = [
        ADJUSTED_PATH,
        COMPONENT_PATH,
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
                "edgeiq_race_entry_suitability_aggregate_fact_v1"
            ),
            "audit_version": "1.1.0_current_ineligible_context_allowed",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(
            AUDIT_PATH,
            payload,
        )

        raise SystemExit(
            "EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_AUDIT_FAIL"
        )

    _, adjusted_rows = read_csv(
        ADJUSTED_PATH
    )

    _, component_rows = read_csv(
        COMPONENT_PATH
    )

    fact_fields, fact_rows = read_csv(
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
        == contract["required_fields"],
        {
            "actual": fact_fields,
            "expected": contract["required_fields"],
        },
    )

    adjusted_by_id: dict[str, dict[str, str]] = {}

    duplicate_adjusted_ids: list[str] = []

    for row in adjusted_rows:
        adjusted_id = text(
            row[
                "race_entry_context_adjusted_performance_id"
            ]
        )

        if adjusted_id in adjusted_by_id:
            duplicate_adjusted_ids.append(
                adjusted_id
            )

        adjusted_by_id[adjusted_id] = row

    check(
        "adjusted_performance_ids_unique",
        not duplicate_adjusted_ids,
        sorted(set(duplicate_adjusted_ids)),
    )

    eligible_adjusted_ids = {
        adjusted_id
        for adjusted_id, row
        in adjusted_by_id.items()
        if text(
            row[
                "context_adjusted_performance_decision"
            ]
        )
        == "PERFORMANCE_ADJUSTED"
    }

    unavailable_rows = sum(
        1
        for row in adjusted_rows
        if text(
            row[
                "context_adjusted_performance_decision"
            ]
        )
        == "PARAMETER_NOT_AVAILABLE"
    )

    ineligible_rows = sum(
        1
        for row in adjusted_rows
        if text(
            row[
                "context_adjusted_performance_decision"
            ]
        )
        == "CONTEXT_INELIGIBLE"
    )

    components_by_adjusted_id: dict[
        str,
        dict[str, dict[str, str]],
    ] = defaultdict(dict)

    duplicate_component_natural_keys: list[str] = []

    for row in component_rows:
        adjusted_id = text(
            row[
                "race_entry_context_adjusted_performance_id"
            ]
        )

        component_type = text(
            row[
                "suitability_component_type"
            ]
        )

        if (
            component_type
            in components_by_adjusted_id[adjusted_id]
        ):
            duplicate_component_natural_keys.append(
                f"{adjusted_id}:{component_type}"
            )

        components_by_adjusted_id[
            adjusted_id
        ][
            component_type
        ] = row

    check(
        "component_natural_keys_unique",
        not duplicate_component_natural_keys,
        sorted(
            set(
                duplicate_component_natural_keys
            )
        ),
    )

    expected_aggregate_rows = len(
        eligible_adjusted_ids
    )

    check(
        "aggregate_population_exact",
        len(fact_rows)
        == expected_aggregate_rows,
        {
            "eligible_adjusted_performance_rows": (
                expected_aggregate_rows
            ),
            "actual_suitability_aggregate_rows": (
                len(fact_rows)
            ),
        },
    )

    duplicate_aggregate_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_suitability_aggregate_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_aggregate_natural_keys = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_context_adjusted_performance_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    check(
        "aggregate_ids_unique",
        not duplicate_aggregate_ids,
        duplicate_aggregate_ids,
    )

    check(
        "aggregate_natural_keys_unique",
        not duplicate_aggregate_natural_keys,
        duplicate_aggregate_natural_keys,
    )

    source_errors: list[str] = []
    component_set_errors: list[str] = []
    arithmetic_errors: list[str] = []
    governance_errors: list[str] = []
    identity_errors: list[str] = []
    evidence_errors: list[str] = []

    copied_fields = [
        "race_entry_context_adjustment_id",
        "race_entry_context_parameter_selection_id",
        "race_entry_context_eligibility_id",
        "race_entry_performance_context_id",
        "race_entry_id",
        "race_id",
        "race_date",
        "runner_id",
        "canonical_horse_id",
        "canonical_horse_name",
        "historical_rating_value",
        "context_parameter_id",
        "total_context_adjustment",
        "context_adjusted_performance_value",
    ]

    for row in fact_rows:
        aggregate_id = text(
            row[
                "race_entry_suitability_aggregate_id"
            ]
        )

        adjusted_id = text(
            row[
                "race_entry_context_adjusted_performance_id"
            ]
        )

        adjusted = adjusted_by_id.get(
            adjusted_id
        )

        if (
            adjusted is None
            or adjusted_id
            not in eligible_adjusted_ids
        ):
            source_errors.append(
                aggregate_id
            )
            continue

        components = components_by_adjusted_id.get(
            adjusted_id,
            {},
        )

        if set(components) != set(COMPONENT_ORDER):
            component_set_errors.append(
                aggregate_id
            )
            continue

        for copied_field in copied_fields:
            if text(
                row[copied_field]
            ) != text(
                adjusted[copied_field]
            ):
                source_errors.append(
                    f"{aggregate_id}:{copied_field}"
                )

        component_decimals: list[Decimal] = []
        component_values: list[str] = []
        ordered_component_evidence: list[str] = []

        for component_type in COMPONENT_ORDER:
            component = components[
                component_type
            ]

            output_field = COMPONENT_OUTPUT_FIELDS[
                component_type
            ]

            source_value = text(
                component[
                    "suitability_component_value"
                ]
            )

            output_value = text(
                row[output_field]
            )

            if source_value != output_value:
                source_errors.append(
                    f"{aggregate_id}:{component_type}"
                )

            parsed = parse_decimal(
                output_value
            )

            if parsed is None:
                arithmetic_errors.append(
                    f"{aggregate_id}:{component_type}"
                )
                continue

            component_decimals.append(
                parsed
            )

            component_values.append(
                output_value
            )

            ordered_component_evidence.append(
                text(
                    component[
                        "race_entry_suitability_component_evidence_sha256"
                    ]
                )
            )

        aggregate_decimal = parse_decimal(
            row[
                "aggregate_suitability_value"
            ]
        )

        total_adjustment = parse_decimal(
            row[
                "total_context_adjustment"
            ]
        )

        if (
            aggregate_decimal is None
            or total_adjustment is None
            or len(component_decimals)
            != len(COMPONENT_ORDER)
            or aggregate_decimal
            != sum(
                component_decimals,
                Decimal("0"),
            )
            or aggregate_decimal
            != total_adjustment
        ):
            arithmetic_errors.append(
                aggregate_id
            )

        if text(
            row[
                "suitability_component_count"
            ]
        ) != str(
            len(COMPONENT_ORDER)
        ):
            governance_errors.append(
                f"{aggregate_id}:component_count"
            )

        if (
            text(
                row[
                    "suitability_aggregate_decision"
                ]
            )
            != "SUITABILITY_AGGREGATED"
            or text(
                row[
                    "race_entry_suitability_aggregate_status"
                ]
            )
            != "GOVERNED_SUITABILITY_AGGREGATE"
            or text(row["contract_version"])
            != CONTRACT_VERSION
        ):
            governance_errors.append(
                aggregate_id
            )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                adjusted_id,
                "SUITABILITY_AGGREGATED",
            ]
        )

        expected_aggregate_id = (
            f"RESA1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if aggregate_id != expected_aggregate_id:
            identity_errors.append(
                aggregate_id
            )

        expected_component_evidence_set = (
            sha256_payload(
                ordered_component_evidence
            )
        )

        actual_component_evidence_set = text(
            row[
                "source_component_evidence_set_sha256"
            ]
        )

        if (
            actual_component_evidence_set
            != expected_component_evidence_set
        ):
            evidence_errors.append(
                f"{aggregate_id}:component_evidence_set"
            )

        adjusted_evidence = text(
            row[
                "source_adjusted_performance_evidence_sha256"
            ]
        )

        expected_evidence = sha256_payload(
            [
                aggregate_id,
                adjusted_evidence,
                expected_component_evidence_set,
                *component_values,
                text(
                    row[
                        "aggregate_suitability_value"
                    ]
                ),
                text(
                    row[
                        "total_context_adjustment"
                    ]
                ),
                text(
                    row[
                        "suitability_aggregate_decision"
                    ]
                ),
                text(
                    row[
                        "race_entry_suitability_aggregate_status"
                    ]
                ),
            ]
        )

        if text(
            row[
                "race_entry_suitability_aggregate_evidence_sha256"
            ]
        ) != expected_evidence:
            evidence_errors.append(
                aggregate_id
            )

        required_lineage = [
            aggregate_id,
            adjusted_id,
            adjusted_evidence,
            actual_component_evidence_set,
            text(
                row[
                    "race_entry_suitability_aggregate_evidence_sha256"
                ]
            ),
            text(
                row[
                    "source_adjusted_performance_builder_version"
                ]
            ),
            text(
                row[
                    "source_component_builder_version"
                ]
            ),
            text(row["builder_version"]),
            text(row["contract_version"]),
            text(row["built_at_utc"]),
        ]

        if any(
            not value
            for value in required_lineage
        ):
            governance_errors.append(
                f"{aggregate_id}:lineage"
            )

    aggregate_owner_ids = {
        text(
            row[
                "race_entry_context_adjusted_performance_id"
            ]
        )
        for row in fact_rows
    }

    missing_aggregate_owners = sorted(
        eligible_adjusted_ids
        - aggregate_owner_ids
    )

    unexpected_aggregate_owners = sorted(
        aggregate_owner_ids
        - eligible_adjusted_ids
    )

    check(
        "one_aggregate_per_eligible_entry",
        (
            not missing_aggregate_owners
            and not unexpected_aggregate_owners
        ),
        {
            "missing": missing_aggregate_owners,
            "unexpected": (
                unexpected_aggregate_owners
            ),
        },
    )

    check(
        "aggregate_sources_exact",
        not source_errors,
        source_errors,
    )

    check(
        "complete_component_sets",
        not component_set_errors,
        component_set_errors,
    )

    check(
        "aggregate_arithmetic_exact",
        not arithmetic_errors,
        arithmetic_errors,
    )

    check(
        "aggregate_governance_complete",
        not governance_errors,
        governance_errors,
    )

    check(
        "deterministic_aggregate_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "deterministic_aggregate_evidence",
        not evidence_errors,
        evidence_errors,
    )

    forbidden_fields = set(
        contract["forbidden_fields"]
    )

    present_forbidden_fields = sorted(
        forbidden_fields.intersection(
            fact_fields
        )
    )

    check(
        "no_forbidden_fields",
        not present_forbidden_fields,
        present_forbidden_fields,
    )

    check(
        "current_population_expected",
        len(fact_rows) == expected_aggregate_rows,
        {
            "context_adjusted_performance_rows": (
                len(adjusted_rows)
            ),
            "suitability_component_rows": (
                len(component_rows)
            ),
            "eligible_adjusted_performance_rows": (
                len(eligible_adjusted_ids)
            ),
            "expected_suitability_aggregate_rows": (
                expected_aggregate_rows
            ),
            "parameter_not_available_rows": (
                unavailable_rows
            ),
            "context_ineligible_rows": (
                ineligible_rows
            ),
            "suitability_aggregate_rows": (
                len(fact_rows)
            ),
        },
    )

    failed_checks = [
        name
        for name, result
        in checks.items()
        if result["status"] != "PASS"
    ]

    status = (
        "PASS"
        if not failed_checks
        else "FAIL"
    )

    payload = {
        "audit_name": (
            "edgeiq_race_entry_suitability_aggregate_fact_v1"
        ),
        "audit_version": "1.1.0_current_ineligible_context_allowed",
        "audited_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "status": status,
        "counts": {
            "context_adjusted_performance_rows": (
                len(adjusted_rows)
            ),
            "suitability_component_rows": (
                len(component_rows)
            ),
            "eligible_adjusted_performance_rows": (
                len(eligible_adjusted_ids)
            ),
            "parameter_not_available_rows": (
                unavailable_rows
            ),
            "context_ineligible_rows": (
                ineligible_rows
            ),
            "suitability_aggregate_rows": (
                len(fact_rows)
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
            "EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_AUDIT_PASS"
    )

    for name, value in payload["counts"].items():
        print(
            f"{name}={value}"
        )

    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
