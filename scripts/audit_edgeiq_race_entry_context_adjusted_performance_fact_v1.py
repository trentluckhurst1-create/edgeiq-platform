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

SOURCE_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjustment_fact_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjusted_performance_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_context_adjusted_performance_fact_v1_contract.json"
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
                "edgeiq_race_entry_context_adjusted_performance_fact_v1"
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
            "EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_AUDIT_FAIL"
        )

    _, source_rows = read_csv(
        SOURCE_PATH
    )

    fact_fields, fact_rows = read_csv(
        FACT_PATH
    )

    contract = json.loads(
        CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    expected_fields = contract[
        "required_fields"
    ]

    check(
        "contract_fields_exact",
        fact_fields == expected_fields,
        {
            "actual": fact_fields,
            "expected": expected_fields,
        },
    )

    source_adjustment_ids = [
        text(
            row[
                "race_entry_context_adjustment_id"
            ]
        )
        for row in source_rows
    ]

    fact_adjustment_ids = [
        text(
            row[
                "race_entry_context_adjustment_id"
            ]
        )
        for row in fact_rows
    ]

    check(
        "adjusted_performance_population_exact",
        (
            len(source_adjustment_ids)
            == len(fact_adjustment_ids)
            and set(source_adjustment_ids)
            == set(fact_adjustment_ids)
        ),
        {
            "context_adjustment_rows": len(
                source_rows
            ),
            "context_adjusted_performance_rows": len(
                fact_rows
            ),
        },
    )

    duplicate_output_ids = sorted(
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

    duplicate_source_links = sorted(
        value
        for value, count
        in Counter(
            fact_adjustment_ids
        ).items()
        if value and count != 1
    )

    check(
        "adjusted_performance_ids_unique",
        not duplicate_output_ids,
        duplicate_output_ids,
    )

    check(
        "one_output_per_context_adjustment",
        not duplicate_source_links,
        duplicate_source_links,
    )

    source_by_id = {
        text(
            row[
                "race_entry_context_adjustment_id"
            ]
        ): row
        for row in source_rows
    }

    decision_errors: list[str] = []
    arithmetic_errors: list[str] = []
    lineage_errors: list[str] = []
    identity_errors: list[str] = []
    evidence_errors: list[str] = []
    source_copy_errors: list[str] = []

    copied_fields = [
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
    ]

    for row in fact_rows:
        output_id = text(
            row[
                "race_entry_context_adjusted_performance_id"
            ]
        )

        adjustment_id = text(
            row[
                "race_entry_context_adjustment_id"
            ]
        )

        source = source_by_id.get(
            adjustment_id
        )

        if source is None:
            source_copy_errors.append(
                output_id
            )
            continue

        for field_name in copied_fields:
            if text(row[field_name]) != text(
                source[field_name]
            ):
                source_copy_errors.append(
                    f"{output_id}:{field_name}"
                )

        source_decision = text(
            row["source_adjustment_decision"]
        )

        output_decision = text(
            row[
                "context_adjusted_performance_decision"
            ]
        )

        output_status = text(
            row[
                "race_entry_context_adjusted_performance_status"
            ]
        )

        historical = parse_decimal(
            row["historical_rating_value"]
        )

        total_adjustment = parse_decimal(
            row["total_context_adjustment"]
        )

        adjusted_value = parse_decimal(
            row[
                "context_adjusted_performance_value"
            ]
        )

        context_parameter_id = text(
            row["context_parameter_id"]
        )

        if source_decision == "ADJUSTMENT_APPLIED":
            valid_decision = (
                output_decision
                == "PERFORMANCE_ADJUSTED"
                and output_status
                == "GOVERNED_CONTEXT_ADJUSTED_PERFORMANCE"
                and bool(context_parameter_id)
                and historical is not None
                and total_adjustment is not None
                and adjusted_value is not None
            )

            if (
                historical is None
                or total_adjustment is None
                or adjusted_value is None
                or adjusted_value
                != historical + total_adjustment
            ):
                arithmetic_errors.append(
                    output_id
                )

        elif source_decision == "PARAMETER_NOT_AVAILABLE":
            valid_decision = (
                output_decision
                == "PARAMETER_NOT_AVAILABLE"
                and output_status
                == "GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE"
                and not context_parameter_id
                and historical is not None
                and total_adjustment is None
                and adjusted_value is None
            )

        elif source_decision == "CONTEXT_INELIGIBLE":
            valid_decision = (
                output_decision
                == "CONTEXT_INELIGIBLE"
                and output_status
                == "CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTED_PERFORMANCE"
                and not context_parameter_id
                and historical is not None
                and total_adjustment is None
                and adjusted_value is None
            )

        else:
            valid_decision = False

        if not valid_decision:
            decision_errors.append(
                output_id
            )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                adjustment_id,
                output_decision,
            ]
        )

        expected_output_id = (
            f"RECAP1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if output_id != expected_output_id:
            identity_errors.append(
                output_id
            )

        source_evidence = text(
            row[
                "source_adjustment_evidence_sha256"
            ]
        )

        output_evidence = text(
            row[
                "race_entry_context_adjusted_performance_evidence_sha256"
            ]
        )

        expected_evidence = sha256_payload(
            [
                output_id,
                source_evidence,
                text(
                    row[
                        "historical_rating_value"
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
                output_decision,
                output_status,
            ]
        )

        if output_evidence != expected_evidence:
            evidence_errors.append(
                output_id
            )

        required_lineage = [
            source_evidence,
            output_evidence,
            text(
                row[
                    "source_adjustment_builder_version"
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
            or text(row["contract_version"])
            != CONTRACT_VERSION
        ):
            lineage_errors.append(
                output_id
            )

    check(
        "source_values_copied_exactly",
        not source_copy_errors,
        source_copy_errors,
    )

    check(
        "decisions_and_statuses_governed",
        not decision_errors,
        decision_errors,
    )

    check(
        "adjusted_performance_arithmetic_exact",
        not arithmetic_errors,
        arithmetic_errors,
    )

    check(
        "deterministic_output_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "deterministic_evidence_identity",
        not evidence_errors,
        evidence_errors,
    )

    check(
        "lineage_complete",
        not lineage_errors,
        lineage_errors,
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

    adjusted_rows = sum(
        1
        for row in fact_rows
        if text(
            row[
                "context_adjusted_performance_decision"
            ]
        )
        == "PERFORMANCE_ADJUSTED"
    )

    unavailable_rows = sum(
        1
        for row in fact_rows
        if text(
            row[
                "context_adjusted_performance_decision"
            ]
        )
        == "PARAMETER_NOT_AVAILABLE"
    )

    ineligible_rows = sum(
        1
        for row in fact_rows
        if text(
            row[
                "context_adjusted_performance_decision"
            ]
        )
        == "CONTEXT_INELIGIBLE"
    )

    check(
        "current_population_expected",
        len(fact_rows) == len(source_rows),
        {
            "context_adjustment_rows": len(
                source_rows
            ),
            "performance_adjusted_rows": (
                adjusted_rows
            ),
            "parameter_not_available_rows": (
                unavailable_rows
            ),
            "context_ineligible_rows": (
                ineligible_rows
            ),
            "context_adjusted_performance_rows": (
                len(fact_rows)
            ),
        },
    )

    failed_checks = [
        name
        for name, result in checks.items()
        if result["status"] != "PASS"
    ]

    status = (
        "PASS"
        if not failed_checks
        else "FAIL"
    )

    payload = {
        "audit_name": (
            "edgeiq_race_entry_context_adjusted_performance_fact_v1"
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
            "context_adjustment_rows": len(
                source_rows
            ),
            "performance_adjusted_rows": (
                adjusted_rows
            ),
            "parameter_not_available_rows": (
                unavailable_rows
            ),
            "context_ineligible_rows": (
                ineligible_rows
            ),
            "context_adjusted_performance_rows": (
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
            "EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_AUDIT_PASS"
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
