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

RATING_PATH = (
    DATA / "edgeiq_horse_performance_rating_fact_v1.csv"
)

RACE_ENTRY_PATH = (
    DATA / "edgeiq_race_entry_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"

BUILDER_VERSION = (
    "edgeiq_race_entry_horse_performance_snapshot_fact_v1.0.0"
)

SOURCE_RATING_METHOD = (
    "DIRECT_HISTORICAL_AGGREGATE_VALUE"
)

SOURCE_RATING_STATUS = (
    "HISTORICAL_HORSE_RATING_GOVERNED"
)

SNAPSHOT_STATUS = (
    "POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE"
)

OUTPUT_FIELDS = [
    "race_entry_horse_performance_snapshot_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "selected_horse_performance_rating_id",
    "selected_rating_as_of_date",
    "rating_age_days",
    "eligible_historical_rating_count",
    "first_eligible_rating_date",
    "latest_eligible_rating_date",
    "selected_horse_performance_rating_value",
    "highest_eligible_historical_rating_value",
    "lowest_eligible_historical_rating_value",
    "average_eligible_historical_rating_value",
    "selected_included_observation_count",
    "horse_performance_rating_method",
    "race_entry_horse_performance_snapshot_status",
    "source_race_entry_evidence_sha256",
    "source_selected_rating_evidence_sha256",
    "source_eligible_rating_ids_sha256",
    "source_eligible_rating_evidence_sha256",
    "race_entry_horse_performance_snapshot_evidence_sha256",
    "source_race_entry_builder_version",
    "source_rating_builder_version",
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
            f"Invalid decimal field {field_name}: {raw!r}"
        ) from exc

    if not parsed.is_finite():
        fail(
            f"Non-finite decimal field {field_name}: {raw!r}"
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
            f"Invalid integer field {field_name}: {raw!r}"
        ) from exc

    if parsed <= 0:
        fail(
            f"Non-positive integer field {field_name}: {raw!r}"
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
    path: Path,
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
            f"{path.name} missing required fields: {missing}"
        )


def atomic_write_csv(
    path: Path,
    rows: list[dict[str, object]],
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
    rating_fields, rating_rows = read_csv(
        RATING_PATH
    )

    require_fields(
        RATING_PATH,
        rating_fields,
        [
            "horse_performance_rating_id",
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

    if not rating_rows:
        atomic_write_csv(
            OUTPUT_PATH,
            [],
        )

        print(
            "EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_BUILD_PASS"
        )
        print("horse_performance_rating_rows=0")
        print("race_entry_rows=NOT_REQUIRED")
        print("eligible_race_entries=0")
        print(
            "race_entry_horse_performance_snapshot_rows=0"
        )
        print(f"output={OUTPUT_PATH}")
        return

    race_entry_fields, raw_race_entry_rows = read_csv(
        RACE_ENTRY_PATH
    )

    legacy_race_entry_fields = [
        "race_entry_id",
        "race_id",
        "race_date",
        "runner_id",
        "canonical_horse_id",
        "canonical_horse_name",
        "race_entry_status",
        "race_entry_evidence_sha256",
        "builder_version",
    ]

    current_race_entry_fields = [
        "canonical_race_id",
        "canonical_runner_id",
        "race_date",
        "runner_name",
        "declaration_status",
        "scratching_status",
        "source_hash",
        "source_system",
        "source_record_id",
    ]

    if all(
        field in race_entry_fields
        for field in legacy_race_entry_fields
    ):
        race_entry_rows = raw_race_entry_rows
    elif all(
        field in race_entry_fields
        for field in current_race_entry_fields
    ):
        adapter_builder_version = (
            "edgeiq_race_entry_fact_v1.current_contract_adapter.1.0.0"
        )
        race_entry_rows = []
        for row in raw_race_entry_rows:
            canonical_race_id = text(row["canonical_race_id"])
            canonical_runner_id = text(row["canonical_runner_id"])
            source_record_id = text(row["source_record_id"])
            race_entry_id = (
                "RE1-"
                + sha256_payload(
                    [
                        adapter_builder_version,
                        canonical_race_id,
                        canonical_runner_id,
                        source_record_id,
                    ]
                )[:24].upper()
            )
            declared = (
                text(row["declaration_status"]) == "ACTIVE_ENTRY"
                and text(row["scratching_status"]) != "SCRATCHED"
            )
            race_entry_rows.append(
                {
                    "race_entry_id": race_entry_id,
                    "race_id": canonical_race_id,
                    "race_date": text(row["race_date"]),
                    "runner_id": canonical_runner_id,
                    "canonical_horse_id": canonical_runner_id,
                    "canonical_horse_name": text(row["runner_name"]),
                    "race_entry_status": (
                        "DECLARED_GOVERNED"
                        if declared
                        else "NOT_DECLARED_GOVERNED"
                    ),
                    "race_entry_evidence_sha256": text(row["source_hash"]),
                    "builder_version": adapter_builder_version,
                }
            )
    else:
        require_fields(
            RACE_ENTRY_PATH,
            race_entry_fields,
            legacy_race_entry_fields,
        )

    ratings_by_horse: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    seen_rating_ids: set[str] = set()

    for rating in rating_rows:
        rating_id = text(
            rating["horse_performance_rating_id"]
        )

        if not rating_id:
            fail(
                "Blank horse_performance_rating_id."
            )

        if rating_id in seen_rating_ids:
            fail(
                f"Duplicate source rating ID: {rating_id}"
            )

        seen_rating_ids.add(
            rating_id
        )

        canonical_horse_id = text(
            rating["canonical_horse_id"]
        )

        if not canonical_horse_id:
            fail(
                f"{rating_id}: blank canonical_horse_id."
            )

        if not text(
            rating["canonical_horse_name"]
        ):
            fail(
                f"{rating_id}: blank canonical_horse_name."
            )

        date_value(
            rating["rating_as_of_date"],
            "rating_as_of_date",
        )

        decimal_value(
            rating[
                "horse_performance_rating_value"
            ],
            "horse_performance_rating_value",
        )

        positive_integer(
            rating["included_observation_count"],
            "included_observation_count",
        )

        if (
            text(
                rating[
                    "horse_performance_rating_method"
                ]
            )
            != SOURCE_RATING_METHOD
        ):
            fail(
                f"{rating_id}: invalid source rating method."
            )

        if (
            text(
                rating[
                    "horse_performance_rating_status"
                ]
            )
            != SOURCE_RATING_STATUS
        ):
            fail(
                f"{rating_id}: invalid source rating status."
            )

        if not text(
            rating[
                "horse_performance_rating_evidence_sha256"
            ]
        ):
            fail(
                f"{rating_id}: blank rating evidence."
            )

        ratings_by_horse[
            canonical_horse_id
        ].append(
            rating
        )

    for horse_rows in ratings_by_horse.values():
        horse_rows.sort(
            key=lambda row: (
                date_value(
                    row["rating_as_of_date"],
                    "rating_as_of_date",
                ),
                text(
                    row["horse_performance_rating_id"]
                ),
            )
        )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[
        dict[str, object]
    ] = []

    seen_race_entry_ids: set[str] = set()
    seen_snapshot_ids: set[str] = set()

    eligible_race_entries = 0

    for entry in race_entry_rows:
        race_entry_id = text(
            entry["race_entry_id"]
        )

        if not race_entry_id:
            fail(
                "Blank race_entry_id."
            )

        if race_entry_id in seen_race_entry_ids:
            fail(
                f"Duplicate race entry ID: {race_entry_id}"
            )

        seen_race_entry_ids.add(
            race_entry_id
        )

        if (
            text(entry["race_entry_status"])
            != "DECLARED_GOVERNED"
        ):
            continue

        race_id = text(
            entry["race_id"]
        )

        runner_id = text(
            entry["runner_id"]
        )

        canonical_horse_id = text(
            entry["canonical_horse_id"]
        )

        canonical_horse_name = text(
            entry["canonical_horse_name"]
        )

        if (
            not race_id
            or not runner_id
            or not canonical_horse_id
            or not canonical_horse_name
        ):
            fail(
                f"{race_entry_id}: incomplete governed identity."
            )

        race_date = date_value(
            entry["race_date"],
            "race_date",
        )

        race_entry_evidence = text(
            entry["race_entry_evidence_sha256"]
        )

        race_entry_builder_version = text(
            entry["builder_version"]
        )

        if (
            not race_entry_evidence
            or not race_entry_builder_version
        ):
            fail(
                f"{race_entry_id}: incomplete race-entry lineage."
            )

        horse_ratings = ratings_by_horse.get(
            canonical_horse_id,
            [],
        )

        eligible_ratings = [
            rating
            for rating in horse_ratings
            if (
                date_value(
                    rating["rating_as_of_date"],
                    "rating_as_of_date",
                )
                < race_date
            )
        ]

        if not eligible_ratings:
            continue

        eligible_race_entries += 1

        eligible_ratings.sort(
            key=lambda row: (
                date_value(
                    row["rating_as_of_date"],
                    "rating_as_of_date",
                ),
                text(
                    row["horse_performance_rating_id"]
                ),
            )
        )

        selected_rating = eligible_ratings[-1]

        # Horse identity is governed by canonical_horse_id. Names are a
        # secondary consistency check only, so compare a deterministic
        # presentation-normalised form while preserving source spelling/case.
        normalise_horse_name = lambda value: " ".join(
            text(value).split()
        ).upper()

        source_names = {
            normalise_horse_name(
                rating["canonical_horse_name"]
            )
            for rating in eligible_ratings
        }

        if len(source_names) != 1:
            fail(
                f"{race_entry_id}: rating source names disagree."
            )

        source_name = next(
            iter(source_names)
        )

        if source_name != normalise_horse_name(canonical_horse_name):
            fail(
                f"{race_entry_id}: race-entry and rating "
                "canonical names disagree."
            )

        selected_rating_id = text(
            selected_rating[
                "horse_performance_rating_id"
            ]
        )

        selected_rating_date = date_value(
            selected_rating[
                "rating_as_of_date"
            ],
            "rating_as_of_date",
        )

        rating_age_days = (
            race_date - selected_rating_date
        ).days

        if rating_age_days <= 0:
            fail(
                f"{race_entry_id}: invalid rating age."
            )

        rating_values = [
            decimal_value(
                rating[
                    "horse_performance_rating_value"
                ],
                "horse_performance_rating_value",
            )
            for rating in eligible_ratings
        ]

        rating_dates = [
            date_value(
                rating["rating_as_of_date"],
                "rating_as_of_date",
            )
            for rating in eligible_ratings
        ]

        with localcontext() as context:
            context.prec = 40

            average_rating = (
                sum(
                    rating_values,
                    Decimal("0"),
                )
                / Decimal(
                    len(eligible_ratings)
                )
            )

        selected_rating_value = decimal_value(
            selected_rating[
                "horse_performance_rating_value"
            ],
            "horse_performance_rating_value",
        )

        selected_observation_count = positive_integer(
            selected_rating[
                "included_observation_count"
            ],
            "included_observation_count",
        )

        selected_rating_evidence = text(
            selected_rating[
                "horse_performance_rating_evidence_sha256"
            ]
        )

        selected_rating_builder_version = text(
            selected_rating["builder_version"]
        )

        if (
            not selected_rating_evidence
            or not selected_rating_builder_version
        ):
            fail(
                f"{race_entry_id}: incomplete rating lineage."
            )

        eligible_rating_ids = [
            text(
                rating[
                    "horse_performance_rating_id"
                ]
            )
            for rating in eligible_ratings
        ]

        eligible_rating_evidence = [
            text(
                rating[
                    "horse_performance_rating_evidence_sha256"
                ]
            )
            for rating in eligible_ratings
        ]

        eligible_rating_ids_sha256 = sha256_payload(
            eligible_rating_ids
        )

        eligible_rating_evidence_sha256 = sha256_payload(
            eligible_rating_evidence
        )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_entry_id,
                selected_rating_id,
                race_date.isoformat(),
            ]
        )

        snapshot_id = (
            f"REHPS1-{identity_hash[:24].upper()}"
        )

        if snapshot_id in seen_snapshot_ids:
            fail(
                f"Duplicate deterministic snapshot ID: "
                f"{snapshot_id}"
            )

        seen_snapshot_ids.add(
            snapshot_id
        )

        snapshot_evidence = sha256_payload(
            [
                snapshot_id,
                race_entry_evidence,
                selected_rating_evidence,
                eligible_rating_evidence_sha256,
                format_decimal(
                    selected_rating_value
                ),
                len(eligible_ratings),
                rating_age_days,
                SNAPSHOT_STATUS,
            ]
        )

        output_rows.append(
            {
                "race_entry_horse_performance_snapshot_id": (
                    snapshot_id
                ),
                "race_entry_id": race_entry_id,
                "race_id": race_id,
                "race_date": race_date.isoformat(),
                "runner_id": runner_id,
                "canonical_horse_id": canonical_horse_id,
                "canonical_horse_name": canonical_horse_name,
                "selected_horse_performance_rating_id": (
                    selected_rating_id
                ),
                "selected_rating_as_of_date": (
                    selected_rating_date.isoformat()
                ),
                "rating_age_days": rating_age_days,
                "eligible_historical_rating_count": (
                    len(eligible_ratings)
                ),
                "first_eligible_rating_date": (
                    min(rating_dates).isoformat()
                ),
                "latest_eligible_rating_date": (
                    max(rating_dates).isoformat()
                ),
                "selected_horse_performance_rating_value": (
                    format_decimal(
                        selected_rating_value
                    )
                ),
                "highest_eligible_historical_rating_value": (
                    format_decimal(
                        max(rating_values)
                    )
                ),
                "lowest_eligible_historical_rating_value": (
                    format_decimal(
                        min(rating_values)
                    )
                ),
                "average_eligible_historical_rating_value": (
                    format_decimal(
                        average_rating
                    )
                ),
                "selected_included_observation_count": (
                    selected_observation_count
                ),
                "horse_performance_rating_method": (
                    SOURCE_RATING_METHOD
                ),
                "race_entry_horse_performance_snapshot_status": (
                    SNAPSHOT_STATUS
                ),
                "source_race_entry_evidence_sha256": (
                    race_entry_evidence
                ),
                "source_selected_rating_evidence_sha256": (
                    selected_rating_evidence
                ),
                "source_eligible_rating_ids_sha256": (
                    eligible_rating_ids_sha256
                ),
                "source_eligible_rating_evidence_sha256": (
                    eligible_rating_evidence_sha256
                ),
                "race_entry_horse_performance_snapshot_evidence_sha256": (
                    snapshot_evidence
                ),
                "source_race_entry_builder_version": (
                    race_entry_builder_version
                ),
                "source_rating_builder_version": (
                    selected_rating_builder_version
                ),
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

    output_rows.sort(
        key=lambda row: (
            text(row["race_date"]),
            text(row["race_id"]),
            text(row["race_entry_id"]),
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_SNAPSHOT_FACT_V1_BUILD_PASS"
    )
    print(
        f"horse_performance_rating_rows={len(rating_rows)}"
    )
    print(
        f"race_entry_rows={len(race_entry_rows)}"
    )
    print(
        f"eligible_race_entries={eligible_race_entries}"
    )
    print(
        "race_entry_horse_performance_snapshot_rows="
        f"{len(output_rows)}"
    )
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
