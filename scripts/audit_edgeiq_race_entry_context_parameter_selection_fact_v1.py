from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ELIGIBILITY_PATH = (
    DATA
    / "edgeiq_race_entry_context_eligibility_fact_v1.csv"
)

CONTEXT_PATH = (
    DATA
    / "edgeiq_race_entry_performance_context_fact_v1.csv"
)

PARAMETER_PATH = (
    DATA
    / "edgeiq_context_parameter_registry_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_context_parameter_selection_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_context_parameter_selection_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_context_parameter_selection_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

ALLOWED_DECISIONS = {
    "PARAMETER_SELECTED",
    "PARAMETER_NOT_AVAILABLE",
    "CONTEXT_INELIGIBLE",
}

ALLOWED_STATUSES = {
    "EXACT_CONTEXT_PARAMETER_SELECTED",
    "EXACT_CONTEXT_PARAMETER_NOT_AVAILABLE",
    "CONTEXT_NOT_ELIGIBLE_FOR_PARAMETER_SELECTION",
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
        ELIGIBILITY_PATH,
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
                "edgeiq_race_entry_context_parameter_selection_fact_v1"
            ),
            "audit_version": "1.1.0_all_ineligible_context_allowed",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(
            AUDIT_PATH,
            payload,
        )

        raise SystemExit(
            "EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_AUDIT_FAIL"
        )

    _, eligibility_rows = read_csv(
        ELIGIBILITY_PATH
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

    if eligibility_rows:
        context_exists = CONTEXT_PATH.exists()
        parameter_exists = PARAMETER_PATH.exists()

        check(
            "context_required_when_eligibility_rows_exist",
            context_exists,
            context_exists,
        )

        eligible_context_rows = [
            row
            for row in eligibility_rows
            if text(row.get("complete_context_eligibility")) == "ELIGIBLE"
        ]

        check(
            "parameter_registry_required_when_eligible_context_rows_exist",
            parameter_exists or not eligible_context_rows,
            {
                "parameter_registry_exists": parameter_exists,
                "eligible_context_rows": len(eligible_context_rows),
            },
        )

        context_rows = (
            read_csv(CONTEXT_PATH)[1]
            if context_exists
            else []
        )

        parameter_rows = (
            read_csv(PARAMETER_PATH)[1]
            if parameter_exists
            else []
        )
    else:
        context_rows = []
        parameter_rows = []

        check(
            "downstream_inputs_not_required_for_empty_population",
            True,
            {
                "context_exists": CONTEXT_PATH.exists(),
                "parameter_registry_exists": PARAMETER_PATH.exists(),
            },
        )

    eligibility_ids = [
        text(
            row["race_entry_context_eligibility_id"]
        )
        for row in eligibility_rows
    ]

    fact_eligibility_ids = [
        text(
            row["race_entry_context_eligibility_id"]
        )
        for row in fact_rows
    ]

    check(
        "selection_population_exact",
        set(eligibility_ids)
        == set(fact_eligibility_ids)
        and len(eligibility_ids)
        == len(fact_eligibility_ids),
        {
            "eligibility_rows": len(eligibility_rows),
            "selection_rows": len(fact_rows),
        },
    )

    duplicate_selection_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_context_parameter_selection_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_eligibility_links = sorted(
        value
        for value, count
        in Counter(
            fact_eligibility_ids
        ).items()
        if value and count != 1
    )

    check(
        "selection_ids_unique",
        not duplicate_selection_ids,
        duplicate_selection_ids,
    )

    check(
        "one_selection_per_eligibility",
        not duplicate_eligibility_links,
        duplicate_eligibility_links,
    )

    decision_errors: list[str] = []
    identity_errors: list[str] = []
    governance_errors: list[str] = []

    for row in fact_rows:
        selection_id = text(
            row[
                "race_entry_context_parameter_selection_id"
            ]
        )

        eligibility_id = text(
            row[
                "race_entry_context_eligibility_id"
            ]
        )

        complete_eligibility = text(
            row["complete_context_eligibility"]
        )

        parameter_id = text(
            row["context_parameter_id"]
        )

        parameter_evidence = text(
            row["source_parameter_evidence_sha256"]
        )

        parameter_builder = text(
            row["source_parameter_builder_version"]
        )

        decision = text(
            row["context_parameter_selection_decision"]
        )

        status = text(
            row[
                "race_entry_context_parameter_selection_status"
            ]
        )

        if (
            decision not in ALLOWED_DECISIONS
            or status not in ALLOWED_STATUSES
        ):
            decision_errors.append(
                selection_id
            )
            continue

        if decision == "PARAMETER_SELECTED":
            valid = (
                complete_eligibility == "ELIGIBLE"
                and bool(parameter_id)
                and bool(parameter_evidence)
                and bool(parameter_builder)
                and status
                == "EXACT_CONTEXT_PARAMETER_SELECTED"
            )
        elif decision == "PARAMETER_NOT_AVAILABLE":
            valid = (
                complete_eligibility == "ELIGIBLE"
                and not parameter_id
                and not parameter_evidence
                and not parameter_builder
                and status
                == "EXACT_CONTEXT_PARAMETER_NOT_AVAILABLE"
            )
        else:
            valid = (
                complete_eligibility == "INELIGIBLE"
                and not parameter_id
                and not parameter_evidence
                and not parameter_builder
                and status
                == "CONTEXT_NOT_ELIGIBLE_FOR_PARAMETER_SELECTION"
            )

        if not valid:
            decision_errors.append(
                selection_id
            )

        expected_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                eligibility_id,
                (
                    parameter_id
                    if parameter_id
                    else "NO_PARAMETER"
                ),
                decision,
            ]
        )

        expected_id = (
            f"RECPS1-{expected_hash[:24].upper()}"
        )

        if selection_id != expected_id:
            identity_errors.append(
                selection_id
            )

        required_values = [
            selection_id,
            eligibility_id,
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
            text(row["context_signature_sha256"]),
            text(
                row[
                    "source_eligibility_evidence_sha256"
                ]
            ),
            text(row["source_context_evidence_sha256"]),
            text(
                row[
                    "race_entry_context_parameter_selection_evidence_sha256"
                ]
            ),
            text(
                row[
                    "source_eligibility_builder_version"
                ]
            ),
            text(row["source_context_builder_version"]),
            text(row["builder_version"]),
        ]

        if (
            any(not value for value in required_values)
            or text(row["contract_version"])
            != CONTRACT_VERSION
        ):
            governance_errors.append(
                selection_id
            )

    check(
        "selection_decisions_governed",
        not decision_errors,
        decision_errors,
    )

    check(
        "deterministic_selection_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "selection_governance",
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

    selected_rows = sum(
        1
        for row in fact_rows
        if text(
            row["context_parameter_selection_decision"]
        )
        == "PARAMETER_SELECTED"
    )

    unavailable_rows = sum(
        1
        for row in fact_rows
        if text(
            row["context_parameter_selection_decision"]
        )
        == "PARAMETER_NOT_AVAILABLE"
    )

    ineligible_rows = sum(
        1
        for row in fact_rows
        if text(
            row["context_parameter_selection_decision"]
        )
        == "CONTEXT_INELIGIBLE"
    )

    check(
        "current_population_expected",
        len(fact_rows) == len(eligibility_rows),
        {
            "eligibility_rows": len(eligibility_rows),
            "selection_rows": len(fact_rows),
            "parameter_selected_rows": selected_rows,
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
            "edgeiq_race_entry_context_parameter_selection_fact_v1"
        ),
        "audit_version": "1.1.0_all_ineligible_context_allowed",
        "audited_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "status": status,
        "counts": {
            "context_eligibility_rows": len(
                eligibility_rows
            ),
            "performance_context_rows": len(
                context_rows
            ),
            "context_parameter_registry_rows": len(
                parameter_rows
            ),
            "parameter_selected_rows": selected_rows,
            "parameter_not_available_rows": unavailable_rows,
            "context_ineligible_rows": ineligible_rows,
            "context_parameter_selection_rows": len(
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
            "EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_AUDIT_PASS"
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
