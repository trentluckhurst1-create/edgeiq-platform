from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SNAPSHOT_PATH = (
    DATA
    / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
)

RACE_ENTRY_PATH = (
    DATA / "edgeiq_race_entry_fact_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_performance_context_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_performance_context_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_performance_context_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

CONTEXT_STATUS = (
    "FACTUAL_DECLARED_RACE_CONTEXT_GOVERNED"
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


def format_decimal(
    value: Decimal,
) -> str:
    return (
        f"{value.quantize(Decimal('0.000001')):.6f}"
    )


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
        SNAPSHOT_PATH,
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
                "edgeiq_race_entry_performance_context_fact_v1"
            ),
            "audit_version": "1.1.0_race_context_authority_alignment",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(
            AUDIT_PATH,
            payload,
        )

        raise SystemExit(
            "EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_AUDIT_FAIL"
        )

    _, snapshot_rows = read_csv(
        SNAPSHOT_PATH
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

    if snapshot_rows:
        race_entry_exists = (
            RACE_ENTRY_PATH.exists()
        )

        check(
            "race_entry_fact_required_when_snapshots_exist",
            race_entry_exists,
            {
                "snapshot_rows": len(
                    snapshot_rows
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
            "race_entry_fact_not_required_for_empty_snapshots",
            True,
            {
                "snapshot_rows": 0,
                "race_entry_fact_exists": (
                    RACE_ENTRY_PATH.exists()
                ),
            },
        )

    snapshot_by_id = {
        text(
            row[
                "race_entry_horse_performance_snapshot_id"
            ]
        ): row
        for row in snapshot_rows
    }

    fact_snapshot_ids = [
        text(
            row[
                "race_entry_horse_performance_snapshot_id"
            ]
        )
        for row in fact_rows
    ]

    check(
        "context_population_exact",
        set(snapshot_by_id)
        == set(fact_snapshot_ids),
        {
            "missing_context_rows": sorted(
                set(snapshot_by_id)
                - set(fact_snapshot_ids)
            ),
            "unexpected_context_rows": sorted(
                set(fact_snapshot_ids)
                - set(snapshot_by_id)
            ),
            "snapshot_rows": len(
                snapshot_rows
            ),
            "context_rows": len(
                fact_rows
            ),
        },
    )

    duplicate_context_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_performance_context_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value
        and count != 1
    )

    duplicate_snapshot_links = sorted(
        value
        for value, count
        in Counter(
            fact_snapshot_ids
        ).items()
        if value
        and count != 1
    )

    check(
        "context_ids_unique",
        not duplicate_context_ids,
        duplicate_context_ids,
    )

    check(
        "one_context_per_snapshot",
        not duplicate_snapshot_links,
        duplicate_snapshot_links,
    )

    governance_errors: list[str] = []
    preservation_errors: list[str] = []
    identity_errors: list[str] = []
    numeric_errors: list[str] = []

    for fact in fact_rows:
        context_id = text(
            fact[
                "race_entry_performance_context_id"
            ]
        )

        snapshot_id = text(
            fact[
                "race_entry_horse_performance_snapshot_id"
            ]
        )

        snapshot = snapshot_by_id.get(
            snapshot_id
        )

        if snapshot is None:
            governance_errors.append(
                f"{context_id}:missing-snapshot"
            )
            continue

        try:
            race_date = date.fromisoformat(
                text(fact["race_date"])
            )

            selected_rating_date = date.fromisoformat(
                text(
                    fact[
                        "selected_rating_as_of_date"
                    ]
                )
            )

            rating_age_days = int(
                text(
                    fact[
                        "rating_age_days"
                    ]
                )
            )

            historical_rating = Decimal(
                text(
                    fact[
                        "context_historical_rating_value"
                    ]
                )
            )

            source_rating = Decimal(
                text(
                    snapshot[
                        "selected_horse_performance_rating_value"
                    ]
                )
            )

            race_distance_m = int(
                text(
                    fact[
                        "race_distance_m"
                    ]
                )
            )

            barrier = int(
                text(
                    fact[
                        "barrier"
                    ]
                )
            )

            allocated_weight = Decimal(
                text(
                    fact[
                        "allocated_weight_kg"
                    ]
                )
            )

            declared_field_size = int(
                text(
                    fact[
                        "declared_field_size"
                    ]
                )
            )
        except Exception as exc:
            numeric_errors.append(
                f"{context_id}:"
                f"{type(exc).__name__}"
            )
            continue

        if (
            not historical_rating.is_finite()
            or not source_rating.is_finite()
            or not allocated_weight.is_finite()
            or race_distance_m <= 0
            or barrier <= 0
            or allocated_weight <= 0
            or declared_field_size <= 0
            or barrier > declared_field_size
            or selected_rating_date >= race_date
            or rating_age_days <= 0
        ):
            numeric_errors.append(
                context_id
            )

        if (
            format_decimal(
                historical_rating
            )
            != format_decimal(
                source_rating
            )
        ):
            preservation_errors.append(
                context_id
            )

        copied_fields = [
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "selected_horse_performance_rating_id",
            "selected_rating_as_of_date",
            "rating_age_days",
        ]

        for field_name in copied_fields:
            if (
                text(fact[field_name])
                != text(snapshot[field_name])
            ):
                preservation_errors.append(
                    f"{context_id}:"
                    f"{field_name}"
                )

        expected_identity_hash = sha256_payload(
            [
                snapshot_id,
                text(fact["race_entry_id"]),
                text(fact["race_id"]),
                text(fact["runner_id"]),
                text(fact["selected_horse_performance_rating_id"]),
            ]
        )

        expected_context_id = (
            f"REPCF1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if (
            context_id
            != expected_context_id
        ):
            identity_errors.append(
                context_id
            )

        required_text_fields = [
            "race_entry_id",
            "race_id",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "selected_horse_performance_rating_id",
            "track_id",
            "track_name",
            "track_configuration",
            "track_condition",
            "racing_surface",
            "source_snapshot_evidence_sha256",
            "source_race_entry_evidence_sha256",
            "race_entry_performance_context_evidence_sha256",
            "source_snapshot_builder_version",
            "source_race_entry_builder_version",
            "builder_version",
        ]

        if (
            any(
                not text(
                    fact[field_name]
                )
                for field_name
                in required_text_fields
            )
            or text(
                fact[
                    "race_entry_performance_context_status"
                ]
            )
            != CONTEXT_STATUS
            or text(
                fact[
                    "contract_version"
                ]
            )
            != CONTRACT_VERSION
        ):
            governance_errors.append(
                context_id
            )

    check(
        "historical_rating_preserved",
        not preservation_errors,
        preservation_errors,
    )

    check(
        "deterministic_context_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "context_numeric_governance",
        not numeric_errors,
        numeric_errors,
    )

    check(
        "context_governance",
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

    missing_race_class_rows = [
        text(row.get("race_entry_performance_context_id", ""))
        for row in fact_rows
        if not text(row.get("race_class_code", ""))
    ]
    missing_rail_rows = [
        text(row.get("race_entry_performance_context_id", ""))
        for row in fact_rows
        if not text(row.get("rail_position", ""))
    ]

    check(
        "current_population_expected",
        len(fact_rows) == len(snapshot_rows),
        {
            "snapshot_rows": len(snapshot_rows),
            "race_entry_rows": len(race_entry_rows),
            "context_rows": len(fact_rows),
        },
    )

    check(
        "governed_class_context_gap_reported",
        True,
        {
            "missing_race_class_rows": missing_race_class_rows,
            "missing_race_class_count": len(missing_race_class_rows),
        },
    )

    check(
        "governed_rail_context_gap_reported",
        True,
        {
            "missing_rail_rows": missing_rail_rows,
            "missing_rail_count": len(missing_rail_rows),
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
            "edgeiq_race_entry_performance_context_fact_v1"
        ),
        "audit_version": "1.1.0_race_context_authority_alignment",
        "audited_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "status": status,
        "counts": {
            "race_entry_horse_performance_snapshot_rows": (
                len(snapshot_rows)
            ),
            "race_entry_rows": (
                len(race_entry_rows)
            ),
            "race_entry_performance_context_rows": (
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
            "EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_AUDIT_PASS"
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
