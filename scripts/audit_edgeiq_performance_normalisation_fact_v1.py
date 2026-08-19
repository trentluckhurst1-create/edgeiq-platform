from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASE_PATH = (
    DATA / "edgeiq_performance_intelligence_base_fact_v1.csv"
)
PARAMETER_PATH = (
    DATA / "edgeiq_performance_normalisation_parameter_fact_v1.csv"
)
FACT_PATH = (
    DATA / "edgeiq_performance_normalisation_fact_v1.csv"
)
REJECTION_PATH = (
    DATA / "edgeiq_performance_normalisation_fact_v1_rejections.csv"
)
AUDIT_PATH = (
    DATA / "edgeiq_performance_normalisation_fact_v1_audit.json"
)
CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_performance_normalisation_fact_v1_contract.json"
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
            raise RuntimeError(f"Missing CSV header: {path}")

        return list(reader.fieldnames), list(reader)


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(file_descriptor)

    temporary_path = Path(temporary_name)

    try:
        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
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
        BASE_PATH,
        FACT_PATH,
        REJECTION_PATH,
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
                "edgeiq_performance_normalisation_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(AUDIT_PATH, payload)

        raise SystemExit(
            "EDGEIQ_PERFORMANCE_NORMALISATION_FACT_V1_AUDIT_FAIL"
        )

    _, base_rows = read_csv(BASE_PATH)
    fact_fields, fact_rows = read_csv(FACT_PATH)
    _, rejection_rows = read_csv(REJECTION_PATH)

    contract = json.loads(
        CONTRACT_PATH.read_text(encoding="utf-8")
    )

    check(
        "contract_fields_exact",
        fact_fields == contract["required_fields"],
        {
            "actual": fact_fields,
            "expected": contract["required_fields"],
        },
    )

    if base_rows and not PARAMETER_PATH.exists():
        check(
            "parameter_fact_required_when_base_rows_exist",
            False,
            "Normalisation parameter fact is missing.",
        )
        parameter_rows = []
    elif PARAMETER_PATH.exists():
        _, parameter_rows = read_csv(PARAMETER_PATH)
        check(
            "parameter_fact_available",
            True,
            {
                "parameter_rows": len(parameter_rows),
            },
        )
    else:
        parameter_rows = []
        check(
            "parameter_fact_not_required_for_empty_base",
            not base_rows,
            {
                "performance_base_rows": len(base_rows),
                "parameter_fact_exists": False,
            },
        )

    base_ids = {
        row.get("performance_intelligence_base_id", "").strip()
        for row in base_rows
    }
    fact_ids = {
        row.get("performance_intelligence_base_id", "").strip()
        for row in fact_rows
    }
    rejected_ids = {
        row.get("performance_intelligence_base_id", "").strip()
        for row in rejection_rows
    }

    current_population_expected = (
        base_ids == fact_ids.union(rejected_ids)
        and not fact_ids.intersection(rejected_ids)
    )

    check(
        "current_population_expected",
        current_population_expected,
        {
            "performance_base_rows": len(base_rows),
            "normalisation_parameter_rows": len(
                parameter_rows
            ),
            "performance_normalisation_rows": len(
                fact_rows
            ),
            "normalisation_rejection_rows": len(
                rejection_rows
            ),
            "missing_from_funnel": sorted(
                base_ids - fact_ids - rejected_ids
            ),
            "unexpected_in_funnel": sorted(
                fact_ids.union(rejected_ids) - base_ids
            ),
        },
    )

    forbidden_fields = set(contract["forbidden_fields"])
    present_forbidden_fields = sorted(
        forbidden_fields.intersection(fact_fields)
    )

    check(
        "no_forbidden_fields",
        not present_forbidden_fields,
        present_forbidden_fields,
    )

    failed_checks = [
        name
        for name, result in checks.items()
        if result["status"] != "PASS"
    ]

    status = "PASS" if not failed_checks else "FAIL"

    payload = {
        "audit_name": (
            "edgeiq_performance_normalisation_fact_v1"
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
            "performance_base_rows": len(base_rows),
            "normalisation_parameter_rows": len(
                parameter_rows
            ),
            "performance_normalisation_rows": len(
                fact_rows
            ),
            "normalisation_rejection_rows": len(
                rejection_rows
            ),
        },
        "failed_checks": failed_checks,
        "checks": checks,
    }

    atomic_write_json(AUDIT_PATH, payload)

    if status != "PASS":
        print(json.dumps(payload, indent=2))

        raise SystemExit(
            "EDGEIQ_PERFORMANCE_NORMALISATION_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_PERFORMANCE_NORMALISATION_FACT_V1_AUDIT_PASS"
    )

    for name, value in payload["counts"].items():
        print(f"{name}={value}")

    print(f"audit_output={AUDIT_PATH}")


if __name__ == "__main__":
    main()
