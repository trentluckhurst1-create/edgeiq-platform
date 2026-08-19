from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTED_PATH = (
    DATA
    / "edgeiq_race_entry_projected_performance_fact_v1.csv"
)

ERI_PATH = (
    DATA
    / "edgeiq_race_eri_fact_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_eri_context_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_eri_context_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_eri_context_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"
DECIMAL_PLACES = 6

EXPECTED_CONTEXT_PUBLICATION = (
    "ERI_CONTEXT_PUBLISHED"
)

EXPECTED_CONTEXT_RECONCILIATION = (
    "ERI_CONTEXT_RECONCILED"
)

EXPECTED_CONTEXT_STATUS = (
    "GOVERNED_RACE_ENTRY_ERI_CONTEXT"
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


def governed_decimal_text(
    value: Decimal,
) -> str:
    quantum = Decimal(1).scaleb(
        -DECIMAL_PLACES
    )

    rounded = value.quantize(
        quantum,
        rounding=ROUND_HALF_EVEN,
    )

    return format(
        rounded,
        f".{DECIMAL_PLACES}f",
    )


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
            "status": (
                "PASS"
                if passed
                else "FAIL"
            ),
            "detail": detail,
        }

    required_paths = [
        PROJECTED_PATH,
        ERI_PATH,
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
                "edgeiq_race_entry_eri_context_fact_v1"
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
            "EDGEIQ_RACE_ENTRY_ERI_CONTEXT_FACT_V1_AUDIT_FAIL"
        )

    _, projected_rows = read_csv(
        PROJECTED_PATH
    )

    _, eri_rows = read_csv(
        ERI_PATH
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

    projected_by_id = {
        text(
            row[
                "race_entry_projected_performance_id"
            ]
        ): row
        for row in projected_rows
    }

    eri_by_key = {
        (
            text(
                row[
                    "race_id"
                ]
            ),
            text(
                row[
                    "race_date"
                ]
            ),
        ): row
        for row in eri_rows
    }

    duplicate_context_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_eri_context_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_natural_keys = sorted(
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

    check(
        "context_ids_unique",
        not duplicate_context_ids,
        duplicate_context_ids,
    )

    check(
        "context_natural_keys_unique",
        not duplicate_natural_keys,
        duplicate_natural_keys,
    )

    expected_projected_ids = set(
        projected_by_id
    )

    actual_projected_ids = {
        text(
            row[
                "race_entry_projected_performance_id"
            ]
        )
        for row in fact_rows
    }

    check(
        "published_population_exact",
        actual_projected_ids
        == expected_projected_ids,
        {
            "expected_count": len(
                expected_projected_ids
            ),
            "actual_count": len(
                actual_projected_ids
            ),
            "missing": sorted(
                expected_projected_ids
                - actual_projected_ids
            ),
            "unexpected": sorted(
                actual_projected_ids
                - expected_projected_ids
            ),
        },
    )

    arithmetic_errors: list[str] = []
    identity_errors: list[str] = []
    evidence_errors: list[str] = []
    lineage_errors: list[str] = []
    governance_errors: list[str] = []
    join_errors: list[str] = []

    for row in fact_rows:
        projected_id = text(
            row[
                "race_entry_projected_performance_id"
            ]
        )

        context_id = text(
            row[
                "race_entry_eri_context_id"
            ]
        )

        projected = projected_by_id.get(
            projected_id
        )

        if projected is None:
            join_errors.append(
                f"{projected_id}:missing_projected"
            )
            continue

        race_id = text(
            projected[
                "race_id"
            ]
        )

        race_date = text(
            projected[
                "race_date"
            ]
        )

        eri = eri_by_key.get(
            (
                race_id,
                race_date,
            )
        )

        if eri is None:
            join_errors.append(
                f"{projected_id}:missing_eri"
            )
            continue

        projected_value = parse_decimal(
            projected[
                "projected_performance_value"
            ]
        )

        eri_value = parse_decimal(
            eri[
                "eri_value"
            ]
        )

        if projected_value is None or eri_value is None:
            arithmetic_errors.append(
                f"{projected_id}:source_decimal"
            )
            continue

        expected_projected_text = governed_decimal_text(
            projected_value
        )

        expected_eri_text = governed_decimal_text(
            eri_value
        )

        expected_context_text = governed_decimal_text(
            projected_value
            - eri_value
        )

        expected_values = {
            "race_eri_id": text(
                eri[
                    "race_eri_id"
                ]
            ),
            "race_eri_parameter_id": text(
                eri[
                    "race_eri_parameter_id"
                ]
            ),
            "race_entry_id": text(
                projected[
                    "race_entry_id"
                ]
            ),
            "race_id": race_id,
            "race_date": race_date,
            "projected_performance_value": (
                expected_projected_text
            ),
            "eri_value": expected_eri_text,
            "projected_performance_vs_eri": (
                expected_context_text
            ),
            "context_output_decimal_places": "6",
            "context_rounding_mode": "ROUND_HALF_EVEN",
            "eri_context_publication_decision": (
                EXPECTED_CONTEXT_PUBLICATION
            ),
            "eri_context_reconciliation_decision": (
                EXPECTED_CONTEXT_RECONCILIATION
            ),
            "race_entry_eri_context_status": (
                EXPECTED_CONTEXT_STATUS
            ),
            "source_projected_performance_evidence_sha256": text(
                projected[
                    "race_entry_projected_performance_evidence_sha256"
                ]
            ),
            "source_race_eri_evidence_sha256": text(
                eri[
                    "race_eri_evidence_sha256"
                ]
            ),
            "source_eri_parameter_evidence_sha256": text(
                eri[
                    "source_eri_parameter_evidence_sha256"
                ]
            ),
            "source_projected_performance_builder_version": text(
                projected[
                    "builder_version"
                ]
            ),
            "source_race_eri_builder_version": text(
                eri[
                    "builder_version"
                ]
            ),
            "contract_version": CONTRACT_VERSION,
        }

        for field_name, expected_value in expected_values.items():
            if text(
                row[field_name]
            ) != expected_value:
                arithmetic_errors.append(
                    f"{projected_id}:{field_name}"
                )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                projected_id,
                text(
                    eri[
                        "race_eri_id"
                    ]
                ),
                EXPECTED_CONTEXT_PUBLICATION,
            ]
        )

        expected_context_id = (
            f"ERIC1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if context_id != expected_context_id:
            identity_errors.append(
                projected_id
            )

        expected_evidence = sha256_payload(
            [
                context_id,
                projected_id,
                text(
                    projected[
                        "race_entry_projected_performance_evidence_sha256"
                    ]
                ),
                text(
                    eri[
                        "race_eri_id"
                    ]
                ),
                text(
                    eri[
                        "race_eri_parameter_id"
                    ]
                ),
                text(
                    eri[
                        "race_eri_evidence_sha256"
                    ]
                ),
                text(
                    projected[
                        "race_entry_id"
                    ]
                ),
                race_id,
                race_date,
                expected_projected_text,
                expected_eri_text,
                expected_context_text,
                EXPECTED_CONTEXT_PUBLICATION,
                EXPECTED_CONTEXT_RECONCILIATION,
                EXPECTED_CONTEXT_STATUS,
            ]
        )

        if text(
            row[
                "race_entry_eri_context_evidence_sha256"
            ]
        ) != expected_evidence:
            evidence_errors.append(
                projected_id
            )

        required_lineage = [
            "source_projected_performance_evidence_sha256",
            "source_race_eri_evidence_sha256",
            "source_eri_parameter_evidence_sha256",
            "race_entry_eri_context_evidence_sha256",
            "source_projected_performance_builder_version",
            "source_race_eri_builder_version",
            "builder_version",
            "contract_version",
            "built_at_utc",
        ]

        for field_name in required_lineage:
            if not text(
                row[field_name]
            ):
                lineage_errors.append(
                    f"{projected_id}:{field_name}"
                )

        if (
            text(
                row[
                    "eri_context_publication_decision"
                ]
            )
            != EXPECTED_CONTEXT_PUBLICATION
            or text(
                row[
                    "eri_context_reconciliation_decision"
                ]
            )
            != EXPECTED_CONTEXT_RECONCILIATION
            or text(
                row[
                    "race_entry_eri_context_status"
                ]
            )
            != EXPECTED_CONTEXT_STATUS
        ):
            governance_errors.append(
                projected_id
            )

    check(
        "source_join_exact",
        not join_errors,
        join_errors,
    )

    check(
        "context_arithmetic_exact",
        not arithmetic_errors,
        arithmetic_errors,
    )

    check(
        "deterministic_context_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "deterministic_context_evidence",
        not evidence_errors,
        evidence_errors,
    )

    check(
        "context_lineage_complete",
        not lineage_errors,
        lineage_errors,
    )

    check(
        "context_governance_complete",
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

    check(
        "current_population_expected",
        (
            len(projected_rows) == 0
            and len(eri_rows) == 0
            and len(fact_rows) == 0
        ),
        {
            "projected_performance_rows": (
                len(projected_rows)
            ),
            "race_eri_rows": len(
                eri_rows
            ),
            "race_entry_eri_context_rows": (
                len(fact_rows)
            ),
        },
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
            "edgeiq_race_entry_eri_context_fact_v1"
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
            "projected_performance_rows": (
                len(projected_rows)
            ),
            "race_eri_rows": len(
                eri_rows
            ),
            "race_entry_eri_context_rows": (
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
            "EDGEIQ_RACE_ENTRY_ERI_CONTEXT_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_ERI_CONTEXT_FACT_V1_AUDIT_PASS"
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
