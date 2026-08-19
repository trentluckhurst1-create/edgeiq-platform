from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RATING_PATH = (
    DATA / "edgeiq_horse_performance_rating_fact_v1.csv"
)

RACE_ENTRY_PATH = (
    DATA / "edgeiq_race_entry_fact_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_horse_performance_snapshot_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_horse_performance_snapshot_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

SOURCE_RATING_METHOD = (
    "DIRECT_HISTORICAL_AGGREGATE_VALUE"
)

SNAPSHOT_STATUS = (
    "POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE"
)


def text(value: object) -> str:
    return str(
        value if value is not None else ""
    ).strip()


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
        RATING_PATH,
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
                "edgeiq_race_entry_horse_performance_snapshot_fact_v1"
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
            "EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_AUDIT_FAIL"
        )

    _, rating_rows = read_csv(
        RATING_PATH
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
                contract["required_fields"]
            ),
        },
    )

    if rating_rows:
        race_entry_exists = (
            RACE_ENTRY_PATH.exists()
        )

        check(
            "race_entry_fact_required_when_ratings_exist",
            race_entry_exists,
            {
                "horse_performance_rating_rows": (
                    len(rating_rows)
                ),
                "race_entry_fact_exists": (
                    race_entry_exists
                ),
            },
        )

        if race_entry_exists:
            _, race_entry_rows = read_csv(
                RACE_ENTRY_PATH
            )
        else:
            race_entry_rows = []
    else:
        race_entry_rows = []

        check(
            "race_entry_fact_not_required_for_empty_ratings",
            True,
            {
                "horse_performance_rating_rows": 0,
                "race_entry_fact_exists": (
                    RACE_ENTRY_PATH.exists()
                ),
            },
        )

    duplicate_snapshot_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_horse_performance_snapshot_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value
        and count != 1
    )

    duplicate_race_entries = sorted(
        value
        for value, count
        in Counter(
            text(row["race_entry_id"])
            for row in fact_rows
        ).items()
        if value
        and count != 1
    )

    check(
        "snapshot_ids_unique",
        not duplicate_snapshot_ids,
        duplicate_snapshot_ids,
    )

    check(
        "one_snapshot_per_race_entry",
        not duplicate_race_entries,
        duplicate_race_entries,
    )

    governance_errors: list[str] = []
    point_in_time_errors: list[str] = []
    numeric_errors: list[str] = []

    for row in fact_rows:
        snapshot_id = text(
            row[
                "race_entry_horse_performance_snapshot_id"
            ]
        )

        try:
            race_date = date.fromisoformat(
                text(row["race_date"])
            )

            selected_rating_date = date.fromisoformat(
                text(
                    row[
                        "selected_rating_as_of_date"
                    ]
                )
            )

            first_rating_date = date.fromisoformat(
                text(
                    row[
                        "first_eligible_rating_date"
                    ]
                )
            )

            latest_rating_date = date.fromisoformat(
                text(
                    row[
                        "latest_eligible_rating_date"
                    ]
                )
            )

            rating_age_days = int(
                text(row["rating_age_days"])
            )

            eligible_count = int(
                text(
                    row[
                        "eligible_historical_rating_count"
                    ]
                )
            )

            selected_observation_count = int(
                text(
                    row[
                        "selected_included_observation_count"
                    ]
                )
            )

            numeric_values = [
                Decimal(
                    text(
                        row[
                            "selected_horse_performance_rating_value"
                        ]
                    )
                ),
                Decimal(
                    text(
                        row[
                            "highest_eligible_historical_rating_value"
                        ]
                    )
                ),
                Decimal(
                    text(
                        row[
                            "lowest_eligible_historical_rating_value"
                        ]
                    )
                ),
                Decimal(
                    text(
                        row[
                            "average_eligible_historical_rating_value"
                        ]
                    )
                ),
            ]
        except Exception as exc:
            numeric_errors.append(
                f"{snapshot_id}:"
                f"{type(exc).__name__}"
            )
            continue

        if (
            selected_rating_date >= race_date
            or latest_rating_date >= race_date
            or first_rating_date >= race_date
            or selected_rating_date
            != latest_rating_date
            or rating_age_days
            != (
                race_date
                - selected_rating_date
            ).days
            or rating_age_days <= 0
        ):
            point_in_time_errors.append(
                snapshot_id
            )

        if (
            eligible_count <= 0
            or selected_observation_count <= 0
            or any(
                not value.is_finite()
                for value in numeric_values
            )
        ):
            numeric_errors.append(
                snapshot_id
            )

        if (
            not text(row["race_entry_id"])
            or not text(row["race_id"])
            or not text(row["runner_id"])
            or not text(
                row["canonical_horse_id"]
            )
            or not text(
                row["canonical_horse_name"]
            )
            or not text(
                row[
                    "selected_horse_performance_rating_id"
                ]
            )
            or text(
                row[
                    "horse_performance_rating_method"
                ]
            )
            != SOURCE_RATING_METHOD
            or text(
                row[
                    "race_entry_horse_performance_snapshot_status"
                ]
            )
            != SNAPSHOT_STATUS
            or text(
                row["contract_version"]
            )
            != CONTRACT_VERSION
            or not text(
                row[
                    "source_race_entry_evidence_sha256"
                ]
            )
            or not text(
                row[
                    "source_selected_rating_evidence_sha256"
                ]
            )
            or not text(
                row[
                    "source_eligible_rating_ids_sha256"
                ]
            )
            or not text(
                row[
                    "source_eligible_rating_evidence_sha256"
                ]
            )
            or not text(
                row[
                    "race_entry_horse_performance_snapshot_evidence_sha256"
                ]
            )
        ):
            governance_errors.append(
                snapshot_id
            )

    check(
        "point_in_time_boundary",
        not point_in_time_errors,
        point_in_time_errors,
    )

    check(
        "snapshot_numeric_governance",
        not numeric_errors,
        numeric_errors,
    )

    check(
        "snapshot_governance",
        not governance_errors,
        governance_errors,
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

    declared_race_entry_count = sum(
        1
        for row in race_entry_rows
        if text(row.get("declaration_status", "")) == "ACTIVE_ENTRY"
        and text(row.get("scratching_status", "")) != "SCRATCHED"
    )

    snapshot_population_within_race_entry_bounds = (
        len(fact_rows) <= max(len(race_entry_rows), declared_race_entry_count)
    )

    check(
        "snapshot_population_within_race_entry_bounds",
        snapshot_population_within_race_entry_bounds,
        {
            "horse_performance_rating_rows": (
                len(rating_rows)
            ),
            "race_entry_rows": (
                len(race_entry_rows)
            ),
            "declared_race_entry_count": (
                declared_race_entry_count
            ),
            "snapshot_rows": (
                len(fact_rows)
            ),
        },
    )

    check(
        "snapshot_not_header_only_when_inputs_are_populated",
        not (
            len(rating_rows) > 0
            and declared_race_entry_count > 0
            and len(fact_rows) == 0
        ),
        {
            "horse_performance_rating_rows": (
                len(rating_rows)
            ),
            "declared_race_entry_count": (
                declared_race_entry_count
            ),
            "snapshot_rows": (
                len(fact_rows)
            ),
        },
    )

    failed_checks = [
        name
        for name, result
        in checks.items()
        if (
            result["status"]
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
            "edgeiq_race_entry_horse_performance_snapshot_fact_v1"
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
            "horse_performance_rating_rows": (
                len(rating_rows)
            ),
            "race_entry_rows": (
                len(race_entry_rows)
            ),
            "race_entry_horse_performance_snapshot_rows": (
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
            "EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_AUDIT_PASS"
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
