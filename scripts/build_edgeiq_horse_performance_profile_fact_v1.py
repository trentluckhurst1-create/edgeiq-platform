from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_PATH = (
    DATA / "edgeiq_horse_performance_rating_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA / "edgeiq_horse_performance_profile_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_horse_performance_profile_fact_v1.0.0"
)

SOURCE_RATING_METHOD = (
    "DIRECT_HISTORICAL_AGGREGATE_VALUE"
)

SOURCE_RATING_STATUS = (
    "HISTORICAL_HORSE_RATING_GOVERNED"
)

PROFILE_STATUS = (
    "HISTORICAL_HORSE_PROFILE_GOVERNED"
)

OUTPUT_FIELDS = [
    "horse_performance_profile_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "historical_rating_count",
    "first_governed_rating_date",
    "latest_governed_rating_date",
    "latest_horse_performance_rating_id",
    "latest_horse_performance_rating_value",
    "highest_historical_rating_value",
    "lowest_historical_rating_value",
    "average_historical_rating_value",
    "latest_included_observation_count",
    "maximum_included_observation_count",
    "minimum_included_observation_count",
    "total_included_observation_count",
    "horse_performance_profile_status",
    "source_horse_performance_rating_ids_sha256",
    "source_horse_performance_rating_evidence_sha256",
    "horse_performance_profile_evidence_sha256",
    "source_builder_versions_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


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


def date_value(
    value: object,
    field_name: str,
) -> date:
    raw = text(value)

    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid date field {field_name}: {raw!r}"
        ) from exc


def decimal_value(
    value: object,
    field_name: str,
) -> Decimal:
    raw = text(value)

    if not raw:
        fail(
            f"Blank decimal field: {field_name}"
        )

    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Invalid decimal field {field_name}: "
            f"{raw!r}"
        ) from exc

    if not parsed.is_finite():
        fail(
            f"Non-finite decimal field "
            f"{field_name}: {raw!r}"
        )

    return parsed


def positive_integer(
    value: object,
    field_name: str,
) -> int:
    raw = text(value)

    try:
        parsed = int(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid integer field {field_name}: "
            f"{raw!r}"
        ) from exc

    if parsed <= 0:
        fail(
            f"Non-positive integer field "
            f"{field_name}: {raw!r}"
        )

    return parsed


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
    if not path.exists():
        fail(
            f"Missing canonical input: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            fail(
                f"Missing CSV header: {path}"
            )

        return (
            list(reader.fieldnames),
            list(reader),
        )


def require_fields(
    actual_fields: list[str],
    required_fields: Iterable[str],
) -> None:
    missing = [
        field
        for field in required_fields
        if field not in actual_fields
    ]

    if missing:
        fail(
            f"{INPUT_PATH.name} missing "
            f"required fields: {missing}"
        )


def atomic_write_csv(
    path: Path,
    rows: list[dict[str, object]],
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
        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=OUTPUT_FIELDS,
                extrasaction="raise",
                lineterminator="\n",
            )

            writer.writeheader()
            writer.writerows(rows)

        os.replace(
            temporary_path,
            path,
        )
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    input_fields, input_rows = read_csv(
        INPUT_PATH
    )

    require_fields(
        input_fields,
        [
            "horse_performance_rating_id",
            "horse_performance_aggregate_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "rating_as_of_date",
            "included_observation_count",
            "horse_performance_rating_value",
            "horse_performance_rating_method",
            "horse_performance_rating_status",
            "horse_performance_rating_evidence_sha256",
            "builder_version",
        ],
    )

    ratings_by_horse: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    seen_rating_ids: set[str] = set()

    for row in input_rows:
        rating_id = text(
            row["horse_performance_rating_id"]
        )

        if not rating_id:
            fail(
                "Blank horse_performance_rating_id."
            )

        if rating_id in seen_rating_ids:
            fail(
                f"Duplicate source rating ID: "
                f"{rating_id}"
            )

        seen_rating_ids.add(
            rating_id
        )

        canonical_horse_id = text(
            row["canonical_horse_id"]
        )

        canonical_horse_name = text(
            row["canonical_horse_name"]
        )

        if not canonical_horse_id:
            fail(
                f"{rating_id}: blank "
                "canonical_horse_id."
            )

        if not canonical_horse_name:
            fail(
                f"{rating_id}: blank "
                "canonical_horse_name."
            )

        date_value(
            row["rating_as_of_date"],
            "rating_as_of_date",
        )

        decimal_value(
            row[
                "horse_performance_rating_value"
            ],
            "horse_performance_rating_value",
        )

        positive_integer(
            row[
                "included_observation_count"
            ],
            "included_observation_count",
        )

        if (
            text(
                row[
                    "horse_performance_rating_method"
                ]
            )
            != SOURCE_RATING_METHOD
        ):
            fail(
                f"{rating_id}: invalid source "
                "rating method."
            )

        if (
            text(
                row[
                    "horse_performance_rating_status"
                ]
            )
            != SOURCE_RATING_STATUS
        ):
            fail(
                f"{rating_id}: invalid source "
                "rating status."
            )

        if not text(
            row[
                "horse_performance_rating_evidence_sha256"
            ]
        ):
            fail(
                f"{rating_id}: blank source "
                "rating evidence hash."
            )

        ratings_by_horse[
            canonical_horse_id
        ].append(row)

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[
        dict[str, object]
    ] = []

    seen_profile_ids: set[str] = set()

    for (
        canonical_horse_id,
        horse_rows,
    ) in ratings_by_horse.items():
        horse_rows.sort(
            key=lambda row: (
                date_value(
                    row["rating_as_of_date"],
                    "rating_as_of_date",
                ),
                text(
                    row[
                        "horse_performance_rating_id"
                    ]
                ),
            )
        )

        canonical_names = {
            text(
                row[
                    "canonical_horse_name"
                ]
            )
            for row in horse_rows
        }

        if len(canonical_names) != 1:
            fail(
                f"{canonical_horse_id}: "
                "multiple canonical horse names "
                f"exist: {sorted(canonical_names)}"
            )

        canonical_horse_name = next(
            iter(canonical_names)
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
            decimal_value(
                row[
                    "horse_performance_rating_value"
                ],
                "horse_performance_rating_value",
            )
            for row in horse_rows
        ]

        observation_counts = [
            positive_integer(
                row[
                    "included_observation_count"
                ],
                "included_observation_count",
            )
            for row in horse_rows
        ]

        rating_dates = [
            date_value(
                row["rating_as_of_date"],
                "rating_as_of_date",
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
                row["builder_version"]
            )
            for row in horse_rows
        ]

        if any(
            not version
            for version
            in source_builder_versions
        ):
            fail(
                f"{canonical_horse_id}: blank "
                "source builder version."
            )

        latest_row = horse_rows[-1]

        latest_rating_id = text(
            latest_row[
                "horse_performance_rating_id"
            ]
        )

        latest_rating_value = (
            decimal_value(
                latest_row[
                    "horse_performance_rating_value"
                ],
                "horse_performance_rating_value",
            )
        )

        latest_observation_count = (
            positive_integer(
                latest_row[
                    "included_observation_count"
                ],
                "included_observation_count",
            )
        )

        historical_rating_count = len(
            horse_rows
        )

        with localcontext() as context:
            context.prec = 40

            average_rating_value = (
                sum(
                    rating_values,
                    Decimal("0"),
                )
                / Decimal(
                    historical_rating_count
                )
            )

        highest_rating_value = max(
            rating_values
        )

        lowest_rating_value = min(
            rating_values
        )

        first_rating_date = min(
            rating_dates
        )

        latest_rating_date = max(
            rating_dates
        )

        source_rating_ids_sha256 = (
            sha256_payload(
                rating_ids
            )
        )

        source_rating_evidence_sha256 = (
            sha256_payload(
                evidence_hashes
            )
        )

        source_builder_versions_sha256 = (
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

        profile_id = (
            f"HPP1-{identity_hash[:24].upper()}"
        )

        if profile_id in seen_profile_ids:
            fail(
                "Duplicate deterministic "
                "Horse Performance Profile ID: "
                f"{profile_id}"
            )

        seen_profile_ids.add(
            profile_id
        )

        profile_evidence_sha256 = (
            sha256_payload(
                [
                    profile_id,
                    source_rating_evidence_sha256,
                    historical_rating_count,
                    first_rating_date.isoformat(),
                    latest_rating_date.isoformat(),
                    format_decimal(
                        latest_rating_value
                    ),
                    format_decimal(
                        highest_rating_value
                    ),
                    format_decimal(
                        lowest_rating_value
                    ),
                    format_decimal(
                        average_rating_value
                    ),
                    PROFILE_STATUS,
                ]
            )
        )

        output_rows.append(
            {
                "horse_performance_profile_id": (
                    profile_id
                ),
                "canonical_horse_id": (
                    canonical_horse_id
                ),
                "canonical_horse_name": (
                    canonical_horse_name
                ),
                "historical_rating_count": (
                    historical_rating_count
                ),
                "first_governed_rating_date": (
                    first_rating_date.isoformat()
                ),
                "latest_governed_rating_date": (
                    latest_rating_date.isoformat()
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
                        highest_rating_value
                    )
                ),
                "lowest_historical_rating_value": (
                    format_decimal(
                        lowest_rating_value
                    )
                ),
                "average_historical_rating_value": (
                    format_decimal(
                        average_rating_value
                    )
                ),
                "latest_included_observation_count": (
                    latest_observation_count
                ),
                "maximum_included_observation_count": (
                    max(
                        observation_counts
                    )
                ),
                "minimum_included_observation_count": (
                    min(
                        observation_counts
                    )
                ),
                "total_included_observation_count": (
                    sum(
                        observation_counts
                    )
                ),
                "horse_performance_profile_status": (
                    PROFILE_STATUS
                ),
                "source_horse_performance_rating_ids_sha256": (
                    source_rating_ids_sha256
                ),
                "source_horse_performance_rating_evidence_sha256": (
                    source_rating_evidence_sha256
                ),
                "horse_performance_profile_evidence_sha256": (
                    profile_evidence_sha256
                ),
                "source_builder_versions_sha256": (
                    source_builder_versions_sha256
                ),
                "builder_version": (
                    BUILDER_VERSION
                ),
                "contract_version": (
                    CONTRACT_VERSION
                ),
                "built_at_utc": (
                    built_at_utc
                ),
            }
        )

    output_rows.sort(
        key=lambda row: (
            text(
                row[
                    "canonical_horse_id"
                ]
            ),
            text(
                row[
                    "horse_performance_profile_id"
                ]
            ),
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_HORSE_PERFORMANCE_PROFILE_FACT_V1_BUILD_PASS"
    )
    print(
        "horse_performance_rating_rows="
        f"{len(input_rows)}"
    )
    print(
        "canonical_horses="
        f"{len(ratings_by_horse)}"
    )
    print(
        "horse_performance_profile_rows="
        f"{len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
