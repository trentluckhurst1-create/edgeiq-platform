from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = (
    DATA / "edgeiq_horse_performance_rating_fact_v1.csv"
)

FACT_PATH = (
    DATA / "edgeiq_horse_performance_profile_fact_v1.csv"
)

AUDIT_PATH = (
    DATA / "edgeiq_horse_performance_profile_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_horse_performance_profile_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

SOURCE_RATING_METHOD = (
    "DIRECT_HISTORICAL_AGGREGATE_VALUE"
)

SOURCE_RATING_STATUS = (
    "HISTORICAL_HORSE_RATING_GOVERNED"
)

PROFILE_STATUS = (
    "HISTORICAL_HORSE_PROFILE_GOVERNED"
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

    file_descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
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
                "edgeiq_horse_performance_profile_fact_v1"
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
            "EDGEIQ_HORSE_PERFORMANCE_PROFILE_FACT_V1_AUDIT_FAIL"
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

    source_by_horse: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    source_rating_ids: list[str] = []
    invalid_source_rows: list[str] = []

    for row in source_rows:
        rating_id = text(
            row[
                "horse_performance_rating_id"
            ]
        )

        source_rating_ids.append(
            rating_id
        )

        canonical_horse_id = text(
            row["canonical_horse_id"]
        )

        try:
            date.fromisoformat(
                text(
                    row[
                        "rating_as_of_date"
                    ]
                )
            )

            rating_value = Decimal(
                text(
                    row[
                        "horse_performance_rating_value"
                    ]
                )
            )

            observation_count = int(
                text(
                    row[
                        "included_observation_count"
                    ]
                )
            )
        except Exception as exc:
            invalid_source_rows.append(
                f"{rating_id}:"
                f"{type(exc).__name__}"
            )
            continue

        if (
            not rating_id
            or not canonical_horse_id
            or not text(
                row[
                    "canonical_horse_name"
                ]
            )
            or not rating_value.is_finite()
            or observation_count <= 0
            or text(
                row[
                    "horse_performance_rating_method"
                ]
            )
            != SOURCE_RATING_METHOD
            or text(
                row[
                    "horse_performance_rating_status"
                ]
            )
            != SOURCE_RATING_STATUS
            or not text(
                row[
                    "horse_performance_rating_evidence_sha256"
                ]
            )
        ):
            invalid_source_rows.append(
                rating_id
            )
            continue

        source_by_horse[
            canonical_horse_id
        ].append(row)

    duplicate_source_rating_ids = sorted(
        value
        for value, count
        in Counter(
            source_rating_ids
        ).items()
        if value
        and count != 1
    )

    check(
        "source_rating_governance",
        not invalid_source_rows,
        invalid_source_rows,
    )

    check(
        "source_rating_ids_unique",
        not duplicate_source_rating_ids,
        duplicate_source_rating_ids,
    )

    fact_horse_ids = [
        text(
            row[
                "canonical_horse_id"
            ]
        )
        for row in fact_rows
    ]

    duplicate_fact_horses = sorted(
        value
        for value, count
        in Counter(
            fact_horse_ids
        ).items()
        if value
        and count != 1
    )

    check(
        "one_profile_per_canonical_horse",
        not duplicate_fact_horses,
        duplicate_fact_horses,
    )

    source_horse_ids = set(
        source_by_horse
    )

    fact_horse_id_set = set(
        fact_horse_ids
    )

    check(
        "profile_population_exact",
        source_horse_ids
        == fact_horse_id_set,
        {
            "missing_profiles": sorted(
                source_horse_ids
                - fact_horse_id_set
            ),
            "unexpected_profiles": sorted(
                fact_horse_id_set
                - source_horse_ids
            ),
            "source_horses": len(
                source_horse_ids
            ),
            "profile_rows": len(
                fact_rows
            ),
        },
    )

    profile_ids = [
        text(
            row[
                "horse_performance_profile_id"
            ]
        )
        for row in fact_rows
    ]

    duplicate_profile_ids = sorted(
        value
        for value, count
        in Counter(
            profile_ids
        ).items()
        if value
        and count != 1
    )

    check(
        "profile_ids_unique",
        not duplicate_profile_ids,
        duplicate_profile_ids,
    )

    metric_errors: list[str] = []
    identity_errors: list[str] = []
    lineage_errors: list[str] = []
    governance_errors: list[str] = []

    for fact in fact_rows:
        canonical_horse_id = text(
            fact[
                "canonical_horse_id"
            ]
        )

        profile_id = text(
            fact[
                "horse_performance_profile_id"
            ]
        )

        horse_rows = source_by_horse.get(
            canonical_horse_id
        )

        if not horse_rows:
            lineage_errors.append(
                f"{profile_id}: "
                "unknown canonical horse"
            )
            continue

        horse_rows = sorted(
            horse_rows,
            key=lambda row: (
                date.fromisoformat(
                    text(
                        row[
                            "rating_as_of_date"
                        ]
                    )
                ),
                text(
                    row[
                        "horse_performance_rating_id"
                    ]
                ),
            ),
        )

        names = {
            text(
                row[
                    "canonical_horse_name"
                ]
            )
            for row in horse_rows
        }

        if len(names) != 1:
            governance_errors.append(
                f"{profile_id}: "
                "source canonical names differ"
            )
            continue

        expected_name = next(
            iter(names)
        )

        rating_ids = [
            text(
                row[
                    "horse_performance_rating_id"
                ]
            )
            for row in horse_rows
        ]

        rating_values = [
            Decimal(
                text(
                    row[
                        "horse_performance_rating_value"
                    ]
                )
            )
            for row in horse_rows
        ]

        observation_counts = [
            int(
                text(
                    row[
                        "included_observation_count"
                    ]
                )
            )
            for row in horse_rows
        ]

        rating_dates = [
            date.fromisoformat(
                text(
                    row[
                        "rating_as_of_date"
                    ]
                )
            )
            for row in horse_rows
        ]

        evidence_hashes = [
            text(
                row[
                    "horse_performance_rating_evidence_sha256"
                ]
            )
            for row in horse_rows
        ]

        source_builder_versions = [
            text(
                row[
                    "builder_version"
                ]
            )
            for row in horse_rows
        ]

        latest_row = horse_rows[-1]

        latest_rating_id = text(
            latest_row[
                "horse_performance_rating_id"
            ]
        )

        latest_rating_value = Decimal(
            text(
                latest_row[
                    "horse_performance_rating_value"
                ]
            )
        )

        latest_observation_count = int(
            text(
                latest_row[
                    "included_observation_count"
                ]
            )
        )

        with localcontext() as context:
            context.prec = 40

            average_rating = (
                sum(
                    rating_values,
                    Decimal("0"),
                )
                / Decimal(
                    len(
                        rating_values
                    )
                )
            )

        expected_metrics = {
            "canonical_horse_name": (
                expected_name
            ),
            "historical_rating_count": (
                str(
                    len(
                        horse_rows
                    )
                )
            ),
            "first_governed_rating_date": (
                min(
                    rating_dates
                ).isoformat()
            ),
            "latest_governed_rating_date": (
                max(
                    rating_dates
                ).isoformat()
            ),
            "latest_horse_performance_rating_id": (
                latest_rating_id
            ),
            "latest_horse_performance_rating_value": (
                format_decimal(
                    latest_rating_value
                )
            ),
            "highest_historical_rating_value": (
                format_decimal(
                    max(
                        rating_values
                    )
                )
            ),
            "lowest_historical_rating_value": (
                format_decimal(
                    min(
                        rating_values
                    )
                )
            ),
            "average_historical_rating_value": (
                format_decimal(
                    average_rating
                )
            ),
            "latest_included_observation_count": (
                str(
                    latest_observation_count
                )
            ),
            "maximum_included_observation_count": (
                str(
                    max(
                        observation_counts
                    )
                )
            ),
            "minimum_included_observation_count": (
                str(
                    min(
                        observation_counts
                    )
                )
            ),
            "total_included_observation_count": (
                str(
                    sum(
                        observation_counts
                    )
                )
            ),
        }

        for (
            field_name,
            expected_value,
        ) in expected_metrics.items():
            if (
                text(
                    fact[
                        field_name
                    ]
                )
                != expected_value
            ):
                metric_errors.append(
                    f"{profile_id}:"
                    f"{field_name}"
                )

        expected_source_ids_hash = (
            sha256_payload(
                rating_ids
            )
        )

        expected_source_evidence_hash = (
            sha256_payload(
                evidence_hashes
            )
        )

        expected_source_builder_hash = (
            sha256_payload(
                source_builder_versions
            )
        )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                canonical_horse_id,
                *rating_ids,
            ]
        )

        expected_profile_id = (
            f"HPP1-"
            f"{identity_hash[:24].upper()}"
        )

        expected_profile_evidence = (
            sha256_payload(
                [
                    expected_profile_id,
                    expected_source_evidence_hash,
                    len(
                        horse_rows
                    ),
                    min(
                        rating_dates
                    ).isoformat(),
                    max(
                        rating_dates
                    ).isoformat(),
                    format_decimal(
                        latest_rating_value
                    ),
                    format_decimal(
                        max(
                            rating_values
                        )
                    ),
                    format_decimal(
                        min(
                            rating_values
                        )
                    ),
                    format_decimal(
                        average_rating
                    ),
                    PROFILE_STATUS,
                ]
            )
        )

        if (
            profile_id
            != expected_profile_id
            or text(
                fact[
                    "horse_performance_profile_evidence_sha256"
                ]
            )
            != expected_profile_evidence
        ):
            identity_errors.append(
                profile_id
            )

        if (
            text(
                fact[
                    "source_horse_performance_rating_ids_sha256"
                ]
            )
            != expected_source_ids_hash
            or text(
                fact[
                    "source_horse_performance_rating_evidence_sha256"
                ]
            )
            != expected_source_evidence_hash
            or text(
                fact[
                    "source_builder_versions_sha256"
                ]
            )
            != expected_source_builder_hash
        ):
            lineage_errors.append(
                profile_id
            )

        if (
            text(
                fact[
                    "horse_performance_profile_status"
                ]
            )
            != PROFILE_STATUS
            or text(
                fact[
                    "contract_version"
                ]
            )
            != CONTRACT_VERSION
            or not canonical_horse_id
            or not expected_name
        ):
            governance_errors.append(
                profile_id
            )

    check(
        "profile_metrics_exact",
        not metric_errors,
        metric_errors,
    )

    check(
        "deterministic_profile_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "source_rating_lineage",
        not lineage_errors,
        lineage_errors,
    )

    check(
        "profile_governance",
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

    current_population_expected = (
        len(
            source_rows
        )
        == 0
        and len(
            fact_rows
        )
        == 0
    )

    check(
        "current_population_expected",
        current_population_expected,
        {
            "horse_performance_rating_rows": (
                len(
                    source_rows
                )
            ),
            "canonical_horses": (
                len(
                    source_by_horse
                )
            ),
            "horse_performance_profile_rows": (
                len(
                    fact_rows
                )
            ),
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
            "edgeiq_horse_performance_profile_fact_v1"
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
                len(
                    source_rows
                )
            ),
            "canonical_horses": (
                len(
                    source_by_horse
                )
            ),
            "horse_performance_profile_rows": (
                len(
                    fact_rows
                )
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
            "EDGEIQ_HORSE_PERFORMANCE_PROFILE_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_HORSE_PERFORMANCE_PROFILE_FACT_V1_AUDIT_PASS"
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
