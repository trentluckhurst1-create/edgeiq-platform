from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FACT_PATH = (
    DATA
    / "edgeiq_race_eri_parameter_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_eri_parameter_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_eri_parameter_fact_v1_contract.json"
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
                "edgeiq_race_eri_parameter_fact_v1"
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
            "EDGEIQ_RACE_ERI_PARAMETER_FACT_V1_AUDIT_FAIL"
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

    check(
        "parameter_population_exact",
        len(fact_rows) == 1,
        {
            "expected": 1,
            "actual": len(fact_rows),
        },
    )

    duplicate_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_eri_parameter_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_versions = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "eri_parameter_version"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    check(
        "parameter_ids_unique",
        not duplicate_ids,
        duplicate_ids,
    )

    check(
        "parameter_versions_unique",
        not duplicate_versions,
        duplicate_versions,
    )

    governance_errors: list[str] = []
    value_errors: list[str] = []
    identity_errors: list[str] = []
    evidence_errors: list[str] = []
    date_errors: list[str] = []

    for row in fact_rows:
        parameter_id = text(
            row[
                "race_eri_parameter_id"
            ]
        )

        required_non_blank = [
            "race_eri_parameter_id",
            "eri_parameter_version",
            "eri_methodology_code",
            "eri_methodology_name",
            "eri_input_population_rule",
            "eri_complete_field_required",
            "minimum_eligible_runner_count",
            "eri_output_decimal_places",
            "eri_rounding_mode",
            "eri_parameter_scope",
            "effective_from_date",
            "eri_parameter_decision",
            "race_eri_parameter_status",
            "race_eri_parameter_evidence_sha256",
            "builder_version",
            "contract_version",
            "built_at_utc",
        ]

        for field_name in required_non_blank:
            if not text(
                row[field_name]
            ):
                governance_errors.append(
                    f"{parameter_id}:{field_name}"
                )

        expected_values = {
            "eri_parameter_version": "ERI-V1.0.0",
            "eri_methodology_code": (
                "FIELD_MEAN_PROJECTED_PERFORMANCE"
            ),
            "eri_methodology_name": (
                "Field Mean Projected Performance"
            ),
            "eri_input_population_rule": (
                "ALL_GOVERNED_RECONCILED_"
                "PROJECTED_PERFORMANCE_ROWS_PER_RACE"
            ),
            "eri_complete_field_required": "TRUE",
            "minimum_eligible_runner_count": "2",
            "eri_output_decimal_places": "6",
            "eri_rounding_mode": "ROUND_HALF_EVEN",
            "eri_parameter_scope": "GLOBAL",
            "effective_from_date": "2026-07-22",
            "effective_to_date": "",
            "eri_parameter_decision": (
                "ERI_PARAMETER_AUTHORISED"
            ),
            "race_eri_parameter_status": (
                "GOVERNED_ERI_PARAMETER"
            ),
            "contract_version": CONTRACT_VERSION,
        }

        for field_name, expected in expected_values.items():
            if text(
                row[field_name]
            ) != expected:
                value_errors.append(
                    f"{parameter_id}:{field_name}"
                )

        try:
            effective_from = date.fromisoformat(
                text(
                    row[
                        "effective_from_date"
                    ]
                )
            )
        except ValueError:
            date_errors.append(
                f"{parameter_id}:effective_from_date"
            )
            effective_from = None

        effective_to_text = text(
            row[
                "effective_to_date"
            ]
        )

        if effective_to_text:
            try:
                effective_to = date.fromisoformat(
                    effective_to_text
                )
            except ValueError:
                date_errors.append(
                    f"{parameter_id}:effective_to_date"
                )
                effective_to = None

            if (
                effective_from is not None
                and effective_to is not None
                and effective_to < effective_from
            ):
                date_errors.append(
                    f"{parameter_id}:date_range"
                )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                text(
                    row[
                        "eri_parameter_version"
                    ]
                ),
                text(
                    row[
                        "eri_methodology_code"
                    ]
                ),
                text(
                    row[
                        "effective_from_date"
                    ]
                ),
                text(
                    row[
                        "eri_parameter_scope"
                    ]
                ),
            ]
        )

        expected_parameter_id = (
            f"ERIP1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if parameter_id != expected_parameter_id:
            identity_errors.append(
                parameter_id
            )

        expected_evidence = sha256_payload(
            [
                parameter_id,
                text(
                    row[
                        "eri_parameter_version"
                    ]
                ),
                text(
                    row[
                        "eri_methodology_code"
                    ]
                ),
                text(
                    row[
                        "eri_methodology_name"
                    ]
                ),
                text(
                    row[
                        "eri_input_population_rule"
                    ]
                ),
                text(
                    row[
                        "eri_complete_field_required"
                    ]
                ),
                text(
                    row[
                        "minimum_eligible_runner_count"
                    ]
                ),
                text(
                    row[
                        "eri_output_decimal_places"
                    ]
                ),
                text(
                    row[
                        "eri_rounding_mode"
                    ]
                ),
                text(
                    row[
                        "eri_parameter_scope"
                    ]
                ),
                text(
                    row[
                        "effective_from_date"
                    ]
                ),
                text(
                    row[
                        "effective_to_date"
                    ]
                ),
                text(
                    row[
                        "eri_parameter_decision"
                    ]
                ),
                text(
                    row[
                        "race_eri_parameter_status"
                    ]
                ),
            ]
        )

        if text(
            row[
                "race_eri_parameter_evidence_sha256"
            ]
        ) != expected_evidence:
            evidence_errors.append(
                parameter_id
            )

    check(
        "parameter_values_governed",
        not value_errors,
        value_errors,
    )

    check(
        "parameter_governance_complete",
        not governance_errors,
        governance_errors,
    )

    check(
        "parameter_dates_valid",
        not date_errors,
        date_errors,
    )

    check(
        "deterministic_parameter_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "deterministic_parameter_evidence",
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
            "edgeiq_race_eri_parameter_fact_v1"
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
            "eri_parameter_rows": len(
                fact_rows
            )
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
            "EDGEIQ_RACE_ERI_PARAMETER_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ERI_PARAMETER_FACT_V1_AUDIT_PASS"
    )
    print(
        f"eri_parameter_rows={len(fact_rows)}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
