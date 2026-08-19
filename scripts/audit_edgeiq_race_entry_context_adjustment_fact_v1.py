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

SELECTION_PATH = (
    DATA
    / "edgeiq_race_entry_context_parameter_selection_fact_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjustment_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjustment_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_context_adjustment_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

ADJUSTMENT_FIELDS = [
    "distance_adjustment",
    "class_adjustment",
    "track_adjustment",
    "track_configuration_adjustment",
    "track_condition_adjustment",
    "surface_adjustment",
    "barrier_adjustment",
    "weight_adjustment",
    "field_size_adjustment",
]


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
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }

    required_paths = [
        SELECTION_PATH,
        FACT_PATH,
        CONTRACT_PATH,
    ]

    missing = [
        str(path.relative_to(ROOT))
        for path in required_paths
        if not path.exists()
    ]

    check(
        "required_files_exist",
        not missing,
        missing,
    )

    if missing:
        payload = {
            "audit_name": (
                "edgeiq_race_entry_context_adjustment_fact_v1"
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
            "EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_AUDIT_FAIL"
        )

    _, selection_rows = read_csv(
        SELECTION_PATH
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

    selection_ids = [
        text(
            row[
                "race_entry_context_parameter_selection_id"
            ]
        )
        for row in selection_rows
    ]

    fact_selection_ids = [
        text(
            row[
                "race_entry_context_parameter_selection_id"
            ]
        )
        for row in fact_rows
    ]

    check(
        "adjustment_population_exact",
        set(selection_ids)
        == set(fact_selection_ids)
        and len(selection_ids)
        == len(fact_selection_ids),
        {
            "selection_rows": len(selection_rows),
            "adjustment_rows": len(fact_rows),
        },
    )

    duplicate_adjustment_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_context_adjustment_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_selection_links = sorted(
        value
        for value, count
        in Counter(
            fact_selection_ids
        ).items()
        if value and count != 1
    )

    check(
        "adjustment_ids_unique",
        not duplicate_adjustment_ids,
        duplicate_adjustment_ids,
    )

    check(
        "one_adjustment_per_selection",
        not duplicate_selection_links,
        duplicate_selection_links,
    )

    decision_errors: list[str] = []
    arithmetic_errors: list[str] = []
    identity_errors: list[str] = []
    governance_errors: list[str] = []

    for row in fact_rows:
        adjustment_id = text(
            row[
                "race_entry_context_adjustment_id"
            ]
        )

        selection_id = text(
            row[
                "race_entry_context_parameter_selection_id"
            ]
        )

        parameter_id = text(
            row["context_parameter_id"]
        )

        source_decision = text(
            row[
                "source_parameter_selection_decision"
            ]
        )

        application_decision = text(
            row[
                "context_adjustment_application_decision"
            ]
        )

        status = text(
            row[
                "race_entry_context_adjustment_status"
            ]
        )

        adjustment_texts = [
            text(row[field_name])
            for field_name in ADJUSTMENT_FIELDS
        ]

        total_text = text(
            row["total_context_adjustment"]
        )

        if source_decision == "PARAMETER_SELECTED":
            valid_decision = (
                application_decision
                == "ADJUSTMENT_APPLIED"
                and status
                == "GOVERNED_CONTEXT_ADJUSTMENT_APPLIED"
                and bool(parameter_id)
                and all(adjustment_texts)
                and bool(total_text)
                and bool(
                    text(
                        row[
                            "source_parameter_evidence_sha256"
                        ]
                    )
                )
                and bool(
                    text(
                        row[
                            "source_parameter_builder_version"
                        ]
                    )
                )
            )

            parsed_adjustments = [
                parse_decimal(value)
                for value in adjustment_texts
            ]

            parsed_total = parse_decimal(
                total_text
            )

            if (
                any(
                    value is None
                    for value in parsed_adjustments
                )
                or parsed_total is None
            ):
                arithmetic_errors.append(
                    adjustment_id
                )
            else:
                expected_total = sum(
                    (
                        value
                        for value in parsed_adjustments
                        if value is not None
                    ),
                    Decimal("0"),
                )

                if parsed_total != expected_total:
                    arithmetic_errors.append(
                        adjustment_id
                    )

        elif source_decision == "PARAMETER_NOT_AVAILABLE":
            valid_decision = (
                application_decision
                == "PARAMETER_NOT_AVAILABLE"
                and status
                == "GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE"
                and not parameter_id
                and not any(adjustment_texts)
                and not total_text
                and not text(
                    row[
                        "source_parameter_evidence_sha256"
                    ]
                )
                and not text(
                    row[
                        "source_parameter_builder_version"
                    ]
                )
            )

        elif source_decision == "CONTEXT_INELIGIBLE":
            valid_decision = (
                application_decision
                == "CONTEXT_INELIGIBLE"
                and status
                == "CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTMENT"
                and not parameter_id
                and not any(adjustment_texts)
                and not total_text
                and not text(
                    row[
                        "source_parameter_evidence_sha256"
                    ]
                )
                and not text(
                    row[
                        "source_parameter_builder_version"
                    ]
                )
            )

        else:
            valid_decision = False

        if not valid_decision:
            decision_errors.append(
                adjustment_id
            )

        expected_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                selection_id,
                (
                    parameter_id
                    if parameter_id
                    else "NO_PARAMETER"
                ),
                application_decision,
            ]
        )

        expected_id = (
            f"RECA1-{expected_hash[:24].upper()}"
        )

        if adjustment_id != expected_id:
            identity_errors.append(
                adjustment_id
            )

        required_values = [
            adjustment_id,
            selection_id,
            text(
                row[
                    "race_entry_context_eligibility_id"
                ]
            ),
            text(
                row[
                    "race_entry_performance_context_id"
                ]
            ),
            text(row["race_entry_id"]),
            text(row["race_id"]),
            text(row["race_date"]),
            text(row["runner_id"]),
            text(row["canonical_horse_id"]),
            text(row["canonical_horse_name"]),
            text(row["historical_rating_value"]),
            text(
                row[
                    "source_selection_evidence_sha256"
                ]
            ),
            text(
                row[
                    "source_context_evidence_sha256"
                ]
            ),
            text(
                row[
                    "race_entry_context_adjustment_evidence_sha256"
                ]
            ),
            text(
                row[
                    "source_selection_builder_version"
                ]
            ),
            text(
                row[
                    "source_context_builder_version"
                ]
            ),
            text(row["builder_version"]),
        ]

        if (
            any(not value for value in required_values)
            or parse_decimal(
                row["historical_rating_value"]
            )
            is None
            or text(row["contract_version"])
            != CONTRACT_VERSION
        ):
            governance_errors.append(
                adjustment_id
            )

    check(
        "adjustment_decisions_governed",
        not decision_errors,
        decision_errors,
    )

    check(
        "adjustment_arithmetic_exact",
        not arithmetic_errors,
        arithmetic_errors,
    )

    check(
        "deterministic_adjustment_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "adjustment_governance",
        not governance_errors,
        governance_errors,
    )

    forbidden = set(
        contract["forbidden_fields"]
    )

    present_forbidden = sorted(
        forbidden.intersection(
            fact_fields
        )
    )

    check(
        "no_forbidden_fields",
        not present_forbidden,
        present_forbidden,
    )

    applied_rows = sum(
        1
        for row in fact_rows
        if text(
            row[
                "context_adjustment_application_decision"
            ]
        )
        == "ADJUSTMENT_APPLIED"
    )

    unavailable_rows = sum(
        1
        for row in fact_rows
        if text(
            row[
                "context_adjustment_application_decision"
            ]
        )
        == "PARAMETER_NOT_AVAILABLE"
    )

    ineligible_rows = sum(
        1
        for row in fact_rows
        if text(
            row[
                "context_adjustment_application_decision"
            ]
        )
        == "CONTEXT_INELIGIBLE"
    )

    check(
        "current_population_expected",
        len(fact_rows) == len(selection_rows),
        {
            "selection_rows": len(selection_rows),
            "adjustment_rows": len(fact_rows),
            "adjustment_applied_rows": applied_rows,
            "context_ineligible_rows": ineligible_rows,
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
            "edgeiq_race_entry_context_adjustment_fact_v1"
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
            "context_parameter_selection_rows": len(
                selection_rows
            ),
            "adjustment_applied_rows": applied_rows,
            "parameter_not_available_rows": unavailable_rows,
            "context_ineligible_rows": ineligible_rows,
            "context_adjustment_rows": len(
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
            "EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_AUDIT_PASS"
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
