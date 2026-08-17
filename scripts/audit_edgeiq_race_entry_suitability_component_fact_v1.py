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

ADJUSTMENT_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjustment_fact_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_component_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_component_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_suitability_component_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

COMPONENT_MAPPING = {
    "DISTANCE": "distance_adjustment",
    "CLASS": "class_adjustment",
    "TRACK": "track_adjustment",
    "TRACK_CONFIGURATION": (
        "track_configuration_adjustment"
    ),
    "TRACK_CONDITION": (
        "track_condition_adjustment"
    ),
    "SURFACE": "surface_adjustment",
    "BARRIER": "barrier_adjustment",
    "WEIGHT": "weight_adjustment",
    "FIELD_SIZE": "field_size_adjustment",
}

EXPECTED_COMPONENT_TYPES = set(
    COMPONENT_MAPPING
)

CURRENT_COMPONENT_TYPE = "LIVE_CURRENT_SUITABILITY"


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
        ADJUSTMENT_PATH,
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
                "edgeiq_race_entry_suitability_component_fact_v1"
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
            "EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_AUDIT_FAIL"
        )

    _, adjusted_rows = read_csv(
        ADJUSTED_PATH
    )

    _, adjustment_rows = read_csv(
        ADJUSTMENT_PATH
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

    adjusted_by_id = {
        text(
            row[
                "race_entry_context_adjusted_performance_id"
            ]
        ): row
        for row in adjusted_rows
    }

    adjustment_by_id = {
        text(
            row[
                "race_entry_context_adjustment_id"
            ]
        ): row
        for row in adjustment_rows
    }

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

    expected_component_rows = (
        len(eligible_adjusted_ids)
        * len(EXPECTED_COMPONENT_TYPES)
    )

    current_component_rows = [
        row
        for row in fact_rows
        if text(row.get("suitability_component_type"))
        == CURRENT_COMPONENT_TYPE
        and not text(
            row.get(
                "race_entry_context_adjusted_performance_id"
            )
        )
    ]

    current_runner_mode = (
        not adjusted_rows
        and len(current_component_rows) == len(fact_rows)
        and bool(fact_rows)
    )

    check(
        "component_population_exact",
        (
            len(fact_rows) == expected_component_rows
            or current_runner_mode
        ),
        {
            "eligible_adjusted_performance_rows": (
                len(eligible_adjusted_ids)
            ),
            "expected_component_rows": (
                expected_component_rows
            ),
            "current_runner_component_rows": (
                len(current_component_rows)
            ),
            "actual_component_rows": len(
                fact_rows
            ),
        },
    )

    duplicate_component_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_suitability_component_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_natural_keys = sorted(
        f"{adjusted_id}:{component_type}"
        for (
            adjusted_id,
            component_type,
        ), count
        in Counter(
            (
                text(
                    row[
                        "race_entry_context_adjusted_performance_id"
                    ]
                )
                or text(row["race_entry_id"]),
                text(
                    row[
                        "suitability_component_type"
                    ]
                ),
            )
            for row in fact_rows
        ).items()
        if count != 1
    )

    check(
        "component_ids_unique",
        not duplicate_component_ids,
        duplicate_component_ids,
    )

    check(
        "component_natural_keys_unique",
        not duplicate_natural_keys,
        duplicate_natural_keys,
    )

    types_by_adjusted_id: dict[str, set[str]] = (
        defaultdict(set)
    )

    governance_errors: list[str] = []
    source_errors: list[str] = []
    value_errors: list[str] = []
    identity_errors: list[str] = []
    evidence_errors: list[str] = []

    for row in fact_rows:
        component_id = text(
            row[
                "race_entry_suitability_component_id"
            ]
        )

        adjusted_id = text(
            row[
                "race_entry_context_adjusted_performance_id"
            ]
        )

        adjustment_id = text(
            row[
                "race_entry_context_adjustment_id"
            ]
        )

        component_type = text(
            row["suitability_component_type"]
        )

        source_field = text(
            row["source_component_field"]
        )

        component_value = text(
            row["suitability_component_value"]
        )

        types_by_adjusted_id[
            adjusted_id
        ].add(
            component_type
        )

        if (
            current_runner_mode
            and component_type == CURRENT_COMPONENT_TYPE
            and not adjusted_id
        ):
            if text(row["source_component_field"]) != "suitability":
                source_errors.append(
                    f"{component_id}:current_source_field"
                )

            if parse_decimal(component_value) is None:
                value_errors.append(
                    f"{component_id}:non_finite"
                )

            if not component_id.startswith("RESC-CUR-"):
                identity_errors.append(component_id)

            expected_evidence = sha256_payload(
                [component_id, component_value]
            )

            if text(
                row[
                    "race_entry_suitability_component_evidence_sha256"
                ]
            ) != expected_evidence:
                evidence_errors.append(component_id)

            required_lineage = [
                component_id,
                text(row["race_entry_id"]),
                text(row["race_id"]),
                text(row["race_date"]),
                text(row["runner_id"]),
                text(row["canonical_horse_id"]),
                text(
                    row[
                        "source_adjusted_performance_evidence_sha256"
                    ]
                ),
                text(
                    row[
                        "race_entry_suitability_component_evidence_sha256"
                    ]
                ),
                text(
                    row[
                        "source_adjusted_performance_builder_version"
                    ]
                ),
                text(row["builder_version"]),
                text(row["contract_version"]),
                text(row["built_at_utc"]),
            ]

            if (
                any(not value for value in required_lineage)
                or text(row["suitability_component_decision"])
                != "SUITABILITY_COMPONENT_PUBLISHED"
                or text(
                    row[
                        "race_entry_suitability_component_status"
                    ]
                )
                != "GOVERNED_SUITABILITY_COMPONENT"
                or text(row["contract_version"])
                != CONTRACT_VERSION
            ):
                governance_errors.append(component_id)

            continue

        adjusted = adjusted_by_id.get(
            adjusted_id
        )

        adjustment = adjustment_by_id.get(
            adjustment_id
        )

        if (
            adjusted is None
            or adjustment is None
        ):
            source_errors.append(
                component_id
            )
            continue

        if adjusted_id not in eligible_adjusted_ids:
            source_errors.append(
                f"{component_id}:source_not_eligible"
            )

        expected_source_field = (
            COMPONENT_MAPPING.get(
                component_type
            )
        )

        if (
            expected_source_field is None
            or source_field
            != expected_source_field
        ):
            source_errors.append(
                f"{component_id}:component_mapping"
            )
            continue

        expected_component_value = text(
            adjustment[source_field]
        )

        if component_value != expected_component_value:
            value_errors.append(
                component_id
            )

        if parse_decimal(component_value) is None:
            value_errors.append(
                f"{component_id}:non_finite"
            )

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

        for field_name in copied_fields:
            expected_source = (
                adjustment
                if field_name
                != "context_adjusted_performance_value"
                else adjusted
            )

            if text(
                row[field_name]
            ) != text(
                expected_source[field_name]
            ):
                source_errors.append(
                    f"{component_id}:{field_name}"
                )

        expected_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                adjusted_id,
                component_type,
            ]
        )

        expected_id = (
            f"RESC1-{expected_hash[:24].upper()}"
        )

        if component_id != expected_id:
            identity_errors.append(
                component_id
            )

        adjusted_evidence = text(
            row[
                "source_adjusted_performance_evidence_sha256"
            ]
        )

        adjustment_evidence = text(
            row[
                "source_context_adjustment_evidence_sha256"
            ]
        )

        expected_evidence = sha256_payload(
            [
                component_id,
                adjusted_evidence,
                adjustment_evidence,
                component_type,
                source_field,
                component_value,
                text(
                    row[
                        "suitability_component_decision"
                    ]
                ),
                text(
                    row[
                        "race_entry_suitability_component_status"
                    ]
                ),
            ]
        )

        if text(
            row[
                "race_entry_suitability_component_evidence_sha256"
            ]
        ) != expected_evidence:
            evidence_errors.append(
                component_id
            )

        required_lineage = [
            component_id,
            adjusted_id,
            adjustment_id,
            adjusted_evidence,
            adjustment_evidence,
            text(
                row[
                    "race_entry_suitability_component_evidence_sha256"
                ]
            ),
            text(
                row[
                    "source_adjusted_performance_builder_version"
                ]
            ),
            text(
                row[
                    "source_context_adjustment_builder_version"
                ]
            ),
            text(row["builder_version"]),
            text(row["contract_version"]),
            text(row["built_at_utc"]),
        ]

        if (
            any(
                not value
                for value in required_lineage
            )
            or text(
                row[
                    "suitability_component_decision"
                ]
            )
            != "COMPONENT_PUBLISHED"
            or text(
                row[
                    "race_entry_suitability_component_status"
                ]
            )
            != "GOVERNED_SUITABILITY_COMPONENT"
            or text(row["contract_version"])
            != CONTRACT_VERSION
        ):
            governance_errors.append(
                component_id
            )

    incomplete_component_sets = sorted(
        adjusted_id
        for adjusted_id
        in eligible_adjusted_ids
        if types_by_adjusted_id.get(
            adjusted_id,
            set(),
        )
        != EXPECTED_COMPONENT_TYPES
    )

    unexpected_component_owners = sorted(
        adjusted_id
        for adjusted_id
        in types_by_adjusted_id
        if adjusted_id
        not in eligible_adjusted_ids
    )

    if current_runner_mode:
        unexpected_component_owners = []

    check(
        "nine_components_per_eligible_entry",
        not incomplete_component_sets,
        incomplete_component_sets,
    )

    check(
        "no_components_for_ineligible_entries",
        not unexpected_component_owners,
        unexpected_component_owners,
    )

    check(
        "component_sources_exact",
        not source_errors,
        source_errors,
    )

    check(
        "component_values_exact",
        not value_errors,
        value_errors,
    )

    check(
        "deterministic_component_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "deterministic_component_evidence",
        not evidence_errors,
        evidence_errors,
    )

    check(
        "component_governance_complete",
        not governance_errors,
        governance_errors,
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
        (
            len(fact_rows) == expected_component_rows
            or current_runner_mode
        ),
        {
            "context_adjusted_performance_rows": (
                len(adjusted_rows)
            ),
            "context_adjustment_rows": (
                len(adjustment_rows)
            ),
            "eligible_adjusted_performance_rows": (
                len(eligible_adjusted_ids)
            ),
            "expected_component_rows": (
                expected_component_rows
            ),
            "current_runner_component_rows": (
                len(current_component_rows)
            ),
            "parameter_not_available_rows": (
                unavailable_rows
            ),
            "context_ineligible_rows": (
                ineligible_rows
            ),
            "suitability_component_rows": (
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
            "edgeiq_race_entry_suitability_component_fact_v1"
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
            "context_adjustment_rows": (
                len(adjustment_rows)
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
            "suitability_component_rows": (
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
            "EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_AUDIT_PASS"
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
