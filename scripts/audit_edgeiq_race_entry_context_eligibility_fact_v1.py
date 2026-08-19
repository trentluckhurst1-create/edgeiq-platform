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

SOURCE_PATH = (
    DATA
    / "edgeiq_race_entry_performance_context_fact_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_context_eligibility_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_context_eligibility_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_context_eligibility_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

DIMENSION_FIELDS = [
    "historical_rating_eligibility",
    "distance_context_eligibility",
    "class_context_eligibility",
    "track_context_eligibility",
    "track_configuration_eligibility",
    "track_condition_eligibility",
    "surface_context_eligibility",
    "rail_context_eligibility",
    "barrier_context_eligibility",
    "allocated_weight_eligibility",
    "field_size_eligibility",
]

ALLOWED_DIMENSION_VALUES = {
    "ELIGIBLE",
    "INELIGIBLE_MISSING_CONTEXT",
    "INELIGIBLE_INVALID_CONTEXT",
    "INELIGIBLE_UNSUPPORTED_CONTEXT",
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
) -> tuple[
    list[str],
    list[dict[str, str]],
]:
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

        return (
            list(reader.fieldnames),
            list(reader),
        )


def atomic_write_json(
    path: Path,
    payload: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )

    os.close(file_descriptor)

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
        checks[name] = {
            "status": (
                "PASS"
                if passed
                else "FAIL"
            ),
            "detail": detail,
        }

    required_paths = [
        SOURCE_PATH,
        FACT_PATH,
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
                "edgeiq_race_entry_context_eligibility_fact_v1"
            ),
            "audit_version": "1.1.0_current_context_rows_allowed",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(
            AUDIT_PATH,
            payload,
        )

        raise SystemExit(
            "EDGEIQ_RACE_ENTRY_CONTEXT_ELIGIBILITY_FACT_V1_AUDIT_FAIL"
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

    check(
        "contract_fields_exact",
        fact_fields
        == contract["required_fields"],
        {
            "actual": fact_fields,
            "expected": (
                contract[
                    "required_fields"
                ]
            ),
        },
    )

    source_ids = [
        text(
            row[
                "race_entry_performance_context_id"
            ]
        )
        for row in source_rows
    ]

    fact_source_ids = [
        text(
            row[
                "race_entry_performance_context_id"
            ]
        )
        for row in fact_rows
    ]

    check(
        "eligibility_population_exact",
        set(source_ids)
        == set(fact_source_ids)
        and len(source_ids)
        == len(fact_source_ids),
        {
            "missing_eligibility_rows": sorted(
                set(source_ids)
                - set(fact_source_ids)
            ),
            "unexpected_eligibility_rows": sorted(
                set(fact_source_ids)
                - set(source_ids)
            ),
            "source_rows": len(
                source_rows
            ),
            "eligibility_rows": len(
                fact_rows
            ),
        },
    )

    duplicate_source_links = sorted(
        value
        for value, count
        in Counter(
            fact_source_ids
        ).items()
        if value
        and count != 1
    )

    duplicate_eligibility_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_context_eligibility_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value
        and count != 1
    )

    check(
        "one_eligibility_row_per_context",
        not duplicate_source_links,
        duplicate_source_links,
    )

    check(
        "eligibility_ids_unique",
        not duplicate_eligibility_ids,
        duplicate_eligibility_ids,
    )

    source_by_id = {
        text(
            row[
                "race_entry_performance_context_id"
            ]
        ): row
        for row in source_rows
    }

    decision_errors: list[str] = []
    identity_errors: list[str] = []
    lineage_errors: list[str] = []
    governance_errors: list[str] = []

    for fact in fact_rows:
        eligibility_id = text(
            fact[
                "race_entry_context_eligibility_id"
            ]
        )

        source_id = text(
            fact[
                "race_entry_performance_context_id"
            ]
        )

        source = source_by_id.get(
            source_id
        )

        if source is None:
            governance_errors.append(
                f"{eligibility_id}:missing-source"
            )
            continue

        decisions = [
            text(
                fact[field_name]
            )
            for field_name
            in DIMENSION_FIELDS
        ]

        if any(
            decision
            not in ALLOWED_DIMENSION_VALUES
            for decision in decisions
        ):
            decision_errors.append(
                eligibility_id
            )

        all_eligible = all(
            decision == "ELIGIBLE"
            for decision in decisions
        )

        complete_eligibility = text(
            fact[
                "complete_context_eligibility"
            ]
        )

        eligibility_status = text(
            fact[
                "race_entry_context_eligibility_status"
            ]
        )

        reason_code = text(
            fact[
                "primary_context_eligibility_reason_code"
            ]
        )

        if all_eligible:
            if (
                complete_eligibility
                != "ELIGIBLE"
                or eligibility_status
                != "COMPLETE_CONTEXT_ELIGIBLE"
                or reason_code
                != "ALL_REQUIRED_CONTEXT_ELIGIBLE"
            ):
                decision_errors.append(
                    eligibility_id
                )
        else:
            if (
                complete_eligibility
                != "INELIGIBLE"
                or eligibility_status
                != "COMPLETE_CONTEXT_INELIGIBLE"
                or not reason_code
                or reason_code
                == "ALL_REQUIRED_CONTEXT_ELIGIBLE"
            ):
                decision_errors.append(
                    eligibility_id
                )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                source_id,
            ]
        )

        expected_eligibility_id = (
            f"RECE1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if (
            eligibility_id
            != expected_eligibility_id
        ):
            identity_errors.append(
                eligibility_id
            )

        copied_fields = [
            "race_entry_horse_performance_snapshot_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
        ]

        for field_name in copied_fields:
            if (
                text(
                    fact[field_name]
                )
                != text(
                    source[field_name]
                )
            ):
                lineage_errors.append(
                    f"{eligibility_id}:"
                    f"{field_name}"
                )

        if (
            text(
                fact[
                    "source_context_evidence_sha256"
                ]
            )
            != text(
                source[
                    "race_entry_performance_context_evidence_sha256"
                ]
            )
            or text(
                fact[
                    "source_context_builder_version"
                ]
            )
            != text(
                source[
                    "builder_version"
                ]
            )
        ):
            lineage_errors.append(
                eligibility_id
            )

        if (
            not eligibility_id
            or not source_id
            or not text(
                fact[
                    "race_entry_context_eligibility_evidence_sha256"
                ]
            )
            or not text(
                fact[
                    "builder_version"
                ]
            )
            or text(
                fact[
                    "contract_version"
                ]
            )
            != CONTRACT_VERSION
        ):
            governance_errors.append(
                eligibility_id
            )

    check(
        "dimension_decisions_governed",
        not decision_errors,
        decision_errors,
    )

    check(
        "deterministic_eligibility_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "source_context_lineage",
        not lineage_errors,
        lineage_errors,
    )

    check(
        "eligibility_governance",
        not governance_errors,
        governance_errors,
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

    eligible_rows = sum(
        1
        for row in fact_rows
        if (
            text(
                row[
                    "complete_context_eligibility"
                ]
            )
            == "ELIGIBLE"
        )
    )

    ineligible_rows = (
        len(fact_rows)
        - eligible_rows
    )

    check(
        "current_population_expected",
        len(fact_rows) == len(source_rows),
        {
            "source_context_rows": len(source_rows),
            "eligibility_rows": len(fact_rows),
            "complete_context_eligible_rows": eligible_rows,
            "complete_context_ineligible_rows": ineligible_rows,
        },
    )

    failed_checks = [
        name
        for name, result
        in checks.items()
        if (
            result[
                "status"
            ]
            != "PASS"
        )
    ]

    status = (
        "PASS"
        if not failed_checks
        else "FAIL"
    )

    payload = {
        "audit_name": (
            "edgeiq_race_entry_context_eligibility_fact_v1"
        ),
        "audit_version": "1.1.0_current_context_rows_allowed",
        "audited_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "status": status,
        "counts": {
            "race_entry_performance_context_rows": (
                len(source_rows)
            ),
            "complete_context_eligible_rows": (
                eligible_rows
            ),
            "complete_context_ineligible_rows": (
                ineligible_rows
            ),
            "race_entry_context_eligibility_rows": (
                len(fact_rows)
            ),
        },
        "failed_checks": (
            failed_checks
        ),
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
            "EDGEIQ_RACE_ENTRY_CONTEXT_ELIGIBILITY_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_CONTEXT_ELIGIBILITY_FACT_V1_AUDIT_PASS"
    )

    for (
        name,
        value,
    ) in payload[
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
