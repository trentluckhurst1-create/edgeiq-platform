from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

FACT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_epi_parameter_fact_v1.csv"
)

AUDIT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_epi_parameter_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_epi_parameter_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"
EXPECTED_PARAMETER_VERSION = "EPI_V1_2026_01"
EXPECTED_METHODOLOGY = (
    "NORMALISED_WEIGHTED_ADDITIVE_EPI_V1"
)

EXPECTED_BASE = Decimal("100.000000")
EXPECTED_HISTORICAL_WEIGHT = Decimal("0.500000")
EXPECTED_SUITABILITY_WEIGHT = Decimal("0.300000")
EXPECTED_RACE_CONTEXT_WEIGHT = Decimal("0.200000")

EXPECTED_PUBLICATION = "EPI_PARAMETER_AUTHORISED"
EXPECTED_RECONCILIATION = "EPI_PARAMETER_RECONCILED"
EXPECTED_STATUS = "GOVERNED_EPI_PARAMETER"


def text(value: object) -> str:
    return str(
        value if value is not None else ""
    ).strip()


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(
        text(part)
        for part in parts
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def parse_decimal(value: object) -> Decimal | None:
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

    missing_paths = [
        str(path.relative_to(ROOT))
        for path in [
            FACT_PATH,
            CONTRACT_PATH,
        ]
        if not path.exists()
    ]

    check(
        "required_files_exist",
        not missing_paths,
        missing_paths,
    )

    if missing_paths:
        payload = {
            "audit_name": "edgeiq_epi_parameter_fact_v1",
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(
            AUDIT_PATH,
            payload,
        )

        raise SystemExit(
            "EDGEIQ_EPI_PARAMETER_FACT_V1_AUDIT_FAIL"
        )

    fact_fields, rows = read_csv(
        FACT_PATH
    )

    contract = json.loads(
        CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    check(
        "contract_fields_exact",
        fact_fields == contract["required_fields"],
        {
            "actual": fact_fields,
            "expected": contract["required_fields"],
        },
    )

    check(
        "exactly_one_parameter_row",
        len(rows) == 1,
        {
            "row_count": len(rows),
        },
    )

    identity_errors: list[str] = []
    arithmetic_errors: list[str] = []
    governance_errors: list[str] = []
    evidence_errors: list[str] = []
    lineage_errors: list[str] = []

    for row in rows:
        parameter_version = text(
            row["epi_parameter_version"]
        )

        methodology = text(
            row["epi_methodology"]
        )

        effective_from_date = text(
            row["effective_from_date"]
        )

        publication = text(
            row[
                "epi_parameter_publication_decision"
            ]
        )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                parameter_version,
                methodology,
                effective_from_date,
                publication,
            ]
        )

        expected_id = (
            f"EPIP1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if text(
            row["epi_parameter_id"]
        ) != expected_id:
            identity_errors.append(
                "epi_parameter_id"
            )

        base_value = parse_decimal(
            row["epi_base_value"]
        )

        historical_weight = parse_decimal(
            row["historical_performance_weight"]
        )

        suitability_weight = parse_decimal(
            row["suitability_weight"]
        )

        race_context_weight = parse_decimal(
            row["race_context_weight"]
        )

        total_weight = parse_decimal(
            row["total_component_weight"]
        )

        expected_numeric = {
            "epi_base_value": EXPECTED_BASE,
            "historical_performance_weight": (
                EXPECTED_HISTORICAL_WEIGHT
            ),
            "suitability_weight": (
                EXPECTED_SUITABILITY_WEIGHT
            ),
            "race_context_weight": (
                EXPECTED_RACE_CONTEXT_WEIGHT
            ),
            "total_component_weight": Decimal(
                "1.000000"
            ),
        }

        actual_numeric = {
            "epi_base_value": base_value,
            "historical_performance_weight": (
                historical_weight
            ),
            "suitability_weight": suitability_weight,
            "race_context_weight": race_context_weight,
            "total_component_weight": total_weight,
        }

        for field_name, expected_value in expected_numeric.items():
            if actual_numeric[field_name] != expected_value:
                arithmetic_errors.append(
                    field_name
                )

        if (
            historical_weight is None
            or suitability_weight is None
            or race_context_weight is None
            or total_weight is None
            or (
                historical_weight
                + suitability_weight
                + race_context_weight
            ) != total_weight
        ):
            arithmetic_errors.append(
                "component_weight_reconciliation"
            )

        expected_governance = {
            "epi_parameter_version": (
                EXPECTED_PARAMETER_VERSION
            ),
            "epi_methodology": EXPECTED_METHODOLOGY,
            "historical_performance_required": "TRUE",
            "suitability_required": "TRUE",
            "race_context_required": "TRUE",
            "minimum_required_component_count": "3",
            "epi_output_decimal_places": "6",
            "epi_rounding_mode": "ROUND_HALF_EVEN",
            "effective_from_date": "2026-01-01",
            "effective_to_date": "",
            "epi_parameter_publication_decision": (
                EXPECTED_PUBLICATION
            ),
            "epi_parameter_reconciliation_decision": (
                EXPECTED_RECONCILIATION
            ),
            "epi_parameter_status": EXPECTED_STATUS,
            "contract_version": CONTRACT_VERSION,
        }

        for field_name, expected_value in expected_governance.items():
            if text(
                row[field_name]
            ) != expected_value:
                governance_errors.append(
                    field_name
                )

        expected_evidence = sha256_payload(
            [
                text(row["epi_parameter_id"]),
                parameter_version,
                methodology,
                text(row["epi_base_value"]),
                text(
                    row[
                        "historical_performance_weight"
                    ]
                ),
                text(row["suitability_weight"]),
                text(row["race_context_weight"]),
                text(row["total_component_weight"]),
                text(
                    row[
                        "historical_performance_required"
                    ]
                ),
                text(row["suitability_required"]),
                text(row["race_context_required"]),
                text(
                    row[
                        "minimum_required_component_count"
                    ]
                ),
                text(
                    row[
                        "epi_output_decimal_places"
                    ]
                ),
                text(row["epi_rounding_mode"]),
                effective_from_date,
                text(row["effective_to_date"]),
                publication,
                text(
                    row[
                        "epi_parameter_reconciliation_decision"
                    ]
                ),
                text(row["epi_parameter_status"]),
            ]
        )

        if text(
            row[
                "epi_parameter_evidence_sha256"
            ]
        ) != expected_evidence:
            evidence_errors.append(
                "epi_parameter_evidence_sha256"
            )

        for field_name in [
            "epi_parameter_id",
            "epi_parameter_evidence_sha256",
            "builder_version",
            "contract_version",
            "built_at_utc",
        ]:
            if not text(row[field_name]):
                lineage_errors.append(
                    field_name
                )

    check(
        "deterministic_parameter_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "parameter_arithmetic_exact",
        not arithmetic_errors,
        arithmetic_errors,
    )

    check(
        "parameter_governance_exact",
        not governance_errors,
        governance_errors,
    )

    check(
        "deterministic_parameter_evidence",
        not evidence_errors,
        evidence_errors,
    )

    check(
        "parameter_lineage_complete",
        not lineage_errors,
        lineage_errors,
    )

    forbidden_fields = sorted(
        set(
            contract["forbidden_fields"]
        ).intersection(fact_fields)
    )

    check(
        "no_forbidden_fields",
        not forbidden_fields,
        forbidden_fields,
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
        "audit_name": "edgeiq_epi_parameter_fact_v1",
        "audit_version": "1.0.0",
        "audited_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "status": status,
        "counts": {
            "epi_parameter_rows": len(rows),
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
            "EDGEIQ_EPI_PARAMETER_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_EPI_PARAMETER_FACT_V1_AUDIT_PASS"
    )
    print(
        f"epi_parameter_rows={len(rows)}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
