from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RATING_PATH = (
    DATA / "edgeiq_performance_rating_base_fact_v1.csv"
)

IDENTITY_PATH = (
    ROOT
    / "config"
    / "performance-intelligence"
    / "edgeiq_horse_performance_identity_map_v1.csv"
)

FACT_PATH = (
    DATA / "edgeiq_horse_performance_observation_fact_v1.csv"
)

REJECTION_PATH = (
    DATA / "edgeiq_horse_performance_observation_fact_v1_rejections.csv"
)

AUDIT_PATH = (
    DATA / "edgeiq_horse_performance_observation_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_horse_performance_observation_fact_v1_contract.json"
)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


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
        RATING_PATH,
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
                "edgeiq_horse_performance_observation_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(AUDIT_PATH, payload)

        raise SystemExit(
            "EDGEIQ_HORSE_PERFORMANCE_OBSERVATION_FACT_V1_AUDIT_FAIL"
        )

    _, rating_rows = read_csv(RATING_PATH)
    fact_fields, fact_rows = read_csv(FACT_PATH)
    rejection_rows = []
    if REJECTION_PATH.exists():
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

    if rating_rows and not IDENTITY_PATH.exists():
        check(
            "identity_map_required_when_rating_rows_exist",
            False,
            "Governed horse identity map is missing.",
        )
        identity_rows = []
    elif IDENTITY_PATH.exists():
        _, identity_rows = read_csv(IDENTITY_PATH)

        check(
            "identity_map_available",
            True,
            {"identity_map_rows": len(identity_rows)},
        )
    else:
        identity_rows = []

        check(
            "identity_map_not_required_for_empty_rating_base",
            not rating_rows,
            {
                "performance_rating_base_rows": len(rating_rows),
                "identity_map_exists": False,
            },
        )

    rating_ids = {
        text(row["performance_rating_base_id"])
        for row in rating_rows
    }

    fact_rating_ids = [
        text(row["performance_rating_base_id"])
        for row in fact_rows
    ]
    rejected_rating_ids = [
        text(row.get("performance_rating_base_id"))
        for row in rejection_rows
        if text(row.get("performance_rating_base_id"))
    ]

    check(
        "source_population_exact",
        rating_ids == set(fact_rating_ids).union(set(rejected_rating_ids)),
        {
            "rating_rows": len(rating_rows),
            "fact_rows": len(fact_rows),
            "rejection_rows": len(rejection_rows),
            "missing": sorted(
                rating_ids - set(fact_rating_ids).union(set(rejected_rating_ids))
            ),
            "unexpected": sorted(
                set(fact_rating_ids).union(set(rejected_rating_ids)) - rating_ids
            ),
        },
    )

    duplicate_observation_ids = sorted(
        value
        for value, count in Counter(
            text(row["horse_performance_observation_id"])
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_rating_links = sorted(
        value
        for value, count in Counter(
            fact_rating_ids
        ).items()
        if value and count != 1
    )

    check(
        "unique_horse_performance_observation_ids",
        not duplicate_observation_ids,
        duplicate_observation_ids,
    )

    check(
        "one_observation_per_rating_base_row",
        not duplicate_rating_links,
        duplicate_rating_links,
    )

    governance_errors = [
        text(row["horse_performance_observation_id"])
        for row in fact_rows
        if (
            text(row["identity_method"])
            not in {
                "EXACT_NORMALISED_NAME_APPROVED_MAP",
                "EXACT_RACINGCOM_WINNER_SOURCE_ID",
                "EXACT_RACING_AUSTRALIA_CURRENT_CROSSWALK",
            }
            or text(row["identity_status"])
            != "IDENTIFIED_GOVERNED"
            or text(row["rating_status"])
            != "OBSERVED_NORMALISED_GOVERNED"
            or not text(row["canonical_horse_id"])
            or not text(row["canonical_horse_name"])
            or text(row["contract_version"]) != "1.0.0"
        )
    ]

    check(
        "observation_governance",
        not governance_errors,
        governance_errors,
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

    current_population_expected = (
        len(rating_rows)
        == len(fact_rows) + len(rejected_rating_ids)
    )

    check(
        "current_population_expected",
        current_population_expected,
        {
            "performance_rating_base_rows": len(rating_rows),
            "identity_map_rows": len(identity_rows),
            "horse_performance_observation_rows": len(
                fact_rows
            ),
            "identity_rejection_rows": len(rejection_rows),
        },
    )

    failed_checks = [
        name
        for name, result in checks.items()
        if result["status"] != "PASS"
    ]

    status = "PASS" if not failed_checks else "FAIL"

    payload = {
        "audit_name": (
            "edgeiq_horse_performance_observation_fact_v1"
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
            "performance_rating_base_rows": len(rating_rows),
            "identity_map_rows": len(identity_rows),
            "horse_performance_observation_rows": len(
                fact_rows
            ),
            "identity_rejection_rows": len(rejection_rows),
        },
        "failed_checks": failed_checks,
        "checks": checks,
    }

    atomic_write_json(AUDIT_PATH, payload)

    if status != "PASS":
        print(json.dumps(payload, indent=2))

        raise SystemExit(
            "EDGEIQ_HORSE_PERFORMANCE_OBSERVATION_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_HORSE_PERFORMANCE_OBSERVATION_FACT_V1_AUDIT_PASS"
    )

    for name, value in payload["counts"].items():
        print(f"{name}={value}")

    print(f"audit_output={AUDIT_PATH}")


if __name__ == "__main__":
    main()
