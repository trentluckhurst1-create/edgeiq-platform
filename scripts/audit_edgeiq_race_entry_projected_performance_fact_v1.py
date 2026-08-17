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
DATA = ROOT / "public" / "data"

ADJUSTED_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv"
)

AGGREGATE_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_projected_performance_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_projected_performance_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_projected_performance_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"


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


def row_id(prefix: str, parts: Iterable[object]) -> str:
    return f"{prefix}-{sha256_payload(parts)[:24].upper()}"


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
        AGGREGATE_PATH,
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
                "edgeiq_race_entry_projected_performance_fact_v1"
            ),
            "audit_version": "1.1.0_current_empty_projection_allowed",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(
            AUDIT_PATH,
            payload,
        )

        raise SystemExit(
            "EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_AUDIT_FAIL"
        )

    _, adjusted_rows = read_csv(
        ADJUSTED_PATH
    )

    _, aggregate_rows = read_csv(
        AGGREGATE_PATH
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

    aggregate_by_id: dict[str, dict[str, str]] = {}
    duplicate_aggregate_ids: list[str] = []

    for row in aggregate_rows:
        aggregate_id = text(
            row[
                "race_entry_suitability_aggregate_id"
            ]
        )

        if aggregate_id in aggregate_by_id:
            duplicate_aggregate_ids.append(
                aggregate_id
            )

        aggregate_by_id[aggregate_id] = row

    check(
        "adjusted_performance_ids_unique",
        not duplicate_adjusted_ids,
        sorted(
            set(
                duplicate_adjusted_ids
            )
        ),
    )

    check(
        "suitability_aggregate_ids_unique",
        not duplicate_aggregate_ids,
        sorted(
            set(
                duplicate_aggregate_ids
            )
        ),
    )

    check(
        "projected_population_exact",
        len(fact_rows)
        == len(aggregate_rows),
        {
            "suitability_aggregate_rows": (
                len(aggregate_rows)
            ),
            "projected_performance_rows": (
                len(fact_rows)
            ),
        },
    )

    duplicate_projected_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_projected_performance_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_projected_natural_keys = sorted(
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

    check(
        "projected_ids_unique",
        not duplicate_projected_ids,
        duplicate_projected_ids,
    )

    check(
        "projected_natural_keys_unique",
        not duplicate_projected_natural_keys,
        duplicate_projected_natural_keys,
    )

    source_errors: list[str] = []
    arithmetic_errors: list[str] = []
    reconciliation_errors: list[str] = []
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
        projected_id = text(
            row[
                "race_entry_projected_performance_id"
            ]
        )

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

        aggregate = aggregate_by_id.get(
            aggregate_id
        )

        adjusted = adjusted_by_id.get(
            adjusted_id
        )

        if aggregate is None:
            source_errors.append(
                projected_id
            )
            continue

        current_runner_parent = (
            not adjusted_id
            and aggregate_id.startswith("RESA-CUR-")
        )

        if adjusted is None and not current_runner_parent:
            source_errors.append(
                projected_id
            )
            continue

        if text(
            aggregate[
                "race_entry_context_adjusted_performance_id"
            ]
        ) != adjusted_id:
            source_errors.append(
                f"{projected_id}:adjusted_id"
            )

        for field_name in copied_fields:
            if text(
                row[field_name]
            ) != text(
                aggregate[field_name]
            ):
                source_errors.append(
                    f"{projected_id}:{field_name}"
                )

            if (
                adjusted is not None
                and text(row[field_name])
                != text(adjusted[field_name])
            ):
                source_errors.append(
                    f"{projected_id}:adjusted:{field_name}"
                )

        if text(
            row[
                "aggregate_suitability_value"
            ]
        ) != text(
            aggregate[
                "aggregate_suitability_value"
            ]
        ):
            source_errors.append(
                f"{projected_id}:aggregate_value"
            )

        historical = parse_decimal(
            row[
                "historical_rating_value"
            ]
        )

        aggregate_value = parse_decimal(
            row[
                "aggregate_suitability_value"
            ]
        )

        total_adjustment = parse_decimal(
            row[
                "total_context_adjustment"
            ]
        )

        context_adjusted = parse_decimal(
            row[
                "context_adjusted_performance_value"
            ]
        )

        projected = parse_decimal(
            row[
                "projected_performance_value"
            ]
        )

        delta = parse_decimal(
            row[
                "projected_performance_delta_from_historical"
            ]
        )

        required_values = [
            historical,
            aggregate_value,
            context_adjusted,
            projected,
            delta,
        ]

        if not current_runner_parent:
            required_values.append(total_adjustment)

        if any(value is None for value in required_values):
            arithmetic_errors.append(
                projected_id
            )
            continue

        assert historical is not None
        assert aggregate_value is not None
        assert context_adjusted is not None
        assert projected is not None
        assert delta is not None

        if current_runner_parent:
            if projected != context_adjusted:
                arithmetic_errors.append(
                    projected_id
                )

            if text(row["total_context_adjustment"]):
                reconciliation_errors.append(
                    f"{projected_id}:unexpected_total_adjustment"
                )

        else:
            assert total_adjustment is not None

            if projected != historical + aggregate_value:
                arithmetic_errors.append(
                    projected_id
                )

            if aggregate_value != total_adjustment:
                reconciliation_errors.append(
                    f"{projected_id}:aggregate_total"
                )

            if projected != context_adjusted:
                reconciliation_errors.append(
                    f"{projected_id}:projected_context"
                )

        if delta != projected - historical:
            arithmetic_errors.append(
                f"{projected_id}:delta"
            )

        if (
            text(
                row[
                    "projected_performance_publication_decision"
                ]
            )
            != "PROJECTED_PERFORMANCE_PUBLISHED"
            or text(
                row[
                    "projected_performance_reconciliation_decision"
                ]
            )
            != "PROJECTED_PERFORMANCE_RECONCILED"
            or text(
                row[
                    "race_entry_projected_performance_status"
                ]
            )
            != "GOVERNED_PROJECTED_PERFORMANCE"
            or text(
                row[
                    "contract_version"
                ]
            )
            != CONTRACT_VERSION
        ):
            governance_errors.append(
                projected_id
            )

        if current_runner_parent:
            expected_projected_id = row_id(
                "REPP-CUR",
                [
                    row["race_entry_id"],
                    row["race_id"],
                    row["canonical_horse_id"],
                    row[
                        "context_adjusted_performance_value"
                    ],
                ],
            )
        else:
            expected_identity_hash = sha256_payload(
                [
                    CONTRACT_VERSION,
                    aggregate_id,
                    "PROJECTED_PERFORMANCE_PUBLISHED",
                ]
            )

            expected_projected_id = (
                f"REPP1-"
                f"{expected_identity_hash[:24].upper()}"
            )

        if projected_id != expected_projected_id:
            identity_errors.append(
                projected_id
            )

        adjusted_evidence = text(
            row[
                "source_adjusted_performance_evidence_sha256"
            ]
        )

        aggregate_evidence = text(
            row[
                "source_suitability_aggregate_evidence_sha256"
            ]
        )

        expected_evidence = (
            adjusted_evidence
            if current_runner_parent
            else sha256_payload(
                [
                    projected_id,
                    adjusted_evidence,
                    aggregate_evidence,
                    text(
                        row[
                            "historical_rating_value"
                        ]
                    ),
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
                            "context_adjusted_performance_value"
                        ]
                    ),
                    text(
                        row[
                            "projected_performance_value"
                        ]
                    ),
                    text(
                        row[
                            "projected_performance_publication_decision"
                        ]
                    ),
                    text(
                        row[
                            "projected_performance_reconciliation_decision"
                        ]
                    ),
                    text(
                        row[
                            "race_entry_projected_performance_status"
                        ]
                    ),
                ]
            )
        )

        if text(
            row[
                "race_entry_projected_performance_evidence_sha256"
            ]
        ) != expected_evidence:
            evidence_errors.append(
                projected_id
            )

        required_lineage = [
            projected_id,
            aggregate_id,
            adjusted_evidence,
            aggregate_evidence,
            text(
                row[
                    "race_entry_projected_performance_evidence_sha256"
                ]
            ),
            text(
                row[
                    "source_adjusted_performance_builder_version"
                ]
            ),
            text(
                row[
                    "source_suitability_aggregate_builder_version"
                ]
            ),
            text(
                row[
                    "builder_version"
                ]
            ),
            text(
                row[
                    "contract_version"
                ]
            ),
            text(
                row[
                    "built_at_utc"
                ]
            ),
        ]

        if not current_runner_parent:
            required_lineage.append(adjusted_id)

        if any(
            not value
            for value in required_lineage
        ):
            governance_errors.append(
                f"{projected_id}:lineage"
            )

    projected_aggregate_ids = {
        text(
            row[
                "race_entry_suitability_aggregate_id"
            ]
        )
        for row in fact_rows
    }

    expected_aggregate_ids = set(
        aggregate_by_id
    )

    missing_owners = sorted(
        expected_aggregate_ids
        - projected_aggregate_ids
    )

    unexpected_owners = sorted(
        projected_aggregate_ids
        - expected_aggregate_ids
    )

    check(
        "one_projected_row_per_aggregate",
        (
            not missing_owners
            and not unexpected_owners
        ),
        {
            "missing": missing_owners,
            "unexpected": unexpected_owners,
        },
    )

    check(
        "projected_sources_exact",
        not source_errors,
        source_errors,
    )

    check(
        "projected_arithmetic_exact",
        not arithmetic_errors,
        arithmetic_errors,
    )

    check(
        "projected_reconciliation_exact",
        not reconciliation_errors,
        reconciliation_errors,
    )

    check(
        "projected_governance_complete",
        not governance_errors,
        governance_errors,
    )

    check(
        "deterministic_projected_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "deterministic_projected_evidence",
        not evidence_errors,
        evidence_errors,
    )

    forbidden_fields = set(
        contract[
            "forbidden_fields"
        ]
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
        len(fact_rows) == len(aggregate_rows),
        {
            "context_adjusted_performance_rows": (
                len(adjusted_rows)
            ),
            "suitability_aggregate_rows": (
                len(aggregate_rows)
            ),
            "projected_performance_rows": (
                len(fact_rows)
            ),
        },
    )

    failed_checks = [
        name
        for name, result
        in checks.items()
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
            "edgeiq_race_entry_projected_performance_fact_v1"
        ),
        "audit_version": "1.1.0_current_empty_projection_allowed",
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
            "suitability_aggregate_rows": (
                len(aggregate_rows)
            ),
            "projected_performance_rows": (
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
            "EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_AUDIT_PASS"
    )

    for name, value in payload[
        "counts"
    ].items():
        print(
            f"{name}={value}"
        )

    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
