from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_PATH = (
    DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA / "edgeiq_horse_performance_rating_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_horse_performance_rating_fact_v1.0.0"
)

RATING_METHOD = "DIRECT_HISTORICAL_AGGREGATE_VALUE"
RATING_STATUS = "HISTORICAL_HORSE_RATING_GOVERNED"
SOURCE_AGGREGATE_STATUS = "HISTORICAL_AGGREGATE_GOVERNED"

OUTPUT_FIELDS = [
    "horse_performance_rating_id",
    "horse_performance_aggregate_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "rating_as_of_date",
    "horse_performance_aggregation_parameter_id",
    "aggregation_method",
    "included_observation_count",
    "aggregate_rating_value",
    "horse_performance_rating_value",
    "horse_performance_rating_method",
    "horse_performance_rating_status",
    "aggregation_model_version",
    "source_horse_performance_aggregate_evidence_sha256",
    "horse_performance_rating_evidence_sha256",
    "source_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def decimal_value(
    value: object,
    field_name: str,
) -> Decimal:
    raw = text(value)

    if not raw:
        fail(f"Blank decimal field: {field_name}")

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


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        fail(f"Missing canonical input: {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            fail(f"Missing CSV header: {path}")

        return list(reader.fieldnames), list(reader)


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
            f"{INPUT_PATH.name} missing required fields: {missing}"
        )


def atomic_write_csv(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(file_descriptor)

    temporary_path = Path(temporary_name)

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

        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    input_fields, input_rows = read_csv(INPUT_PATH)

    require_fields(
        input_fields,
        [
            "horse_performance_aggregate_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "aggregate_as_of_date",
            "horse_performance_aggregation_parameter_id",
            "aggregation_method",
            "included_observation_count",
            "aggregate_rating_value",
            "aggregate_status",
            "aggregation_model_version",
            "horse_performance_aggregate_evidence_sha256",
            "builder_version",
        ],
    )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []
    seen_aggregate_ids: set[str] = set()
    seen_rating_ids: set[str] = set()

    for row in input_rows:
        aggregate_id = text(
            row["horse_performance_aggregate_id"]
        )

        if not aggregate_id:
            fail("Blank horse_performance_aggregate_id.")

        if aggregate_id in seen_aggregate_ids:
            fail(
                f"Duplicate Horse Performance Aggregate row: "
                f"{aggregate_id}"
            )

        seen_aggregate_ids.add(aggregate_id)

        canonical_horse_id = text(
            row["canonical_horse_id"]
        )

        canonical_horse_name = text(
            row["canonical_horse_name"]
        )

        if not canonical_horse_id:
            fail(
                f"{aggregate_id}: blank canonical_horse_id."
            )

        if not canonical_horse_name:
            fail(
                f"{aggregate_id}: blank canonical_horse_name."
            )

        rating_as_of_date = date_value(
            row["aggregate_as_of_date"],
            "aggregate_as_of_date",
        )

        if (
            text(row["aggregate_status"])
            != SOURCE_AGGREGATE_STATUS
        ):
            fail(
                f"{aggregate_id}: source aggregate status "
                "is not governed."
            )

        included_observation_count = positive_integer(
            row["included_observation_count"],
            "included_observation_count",
        )

        aggregate_rating_value = decimal_value(
            row["aggregate_rating_value"],
            "aggregate_rating_value",
        )

        horse_performance_rating_value = (
            aggregate_rating_value
        )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                aggregate_id,
                canonical_horse_id,
                RATING_METHOD,
            ]
        )

        rating_id = (
            f"HPR1-{identity_hash[:24].upper()}"
        )

        if rating_id in seen_rating_ids:
            fail(
                f"Duplicate deterministic horse rating ID: "
                f"{rating_id}"
            )

        seen_rating_ids.add(rating_id)

        source_evidence_hash = text(
            row[
                "horse_performance_aggregate_evidence_sha256"
            ]
        )

        if not source_evidence_hash:
            fail(
                f"{aggregate_id}: missing source aggregate "
                "evidence hash."
            )

        rating_evidence_hash = sha256_payload(
            [
                rating_id,
                source_evidence_hash,
                format_decimal(
                    horse_performance_rating_value
                ),
                RATING_STATUS,
            ]
        )

        output_rows.append(
            {
                "horse_performance_rating_id": rating_id,
                "horse_performance_aggregate_id": aggregate_id,
                "canonical_horse_id": canonical_horse_id,
                "canonical_horse_name": canonical_horse_name,
                "rating_as_of_date": (
                    rating_as_of_date.isoformat()
                ),
                "horse_performance_aggregation_parameter_id": (
                    text(
                        row[
                            "horse_performance_aggregation_parameter_id"
                        ]
                    )
                ),
                "aggregation_method": text(
                    row["aggregation_method"]
                ),
                "included_observation_count": (
                    included_observation_count
                ),
                "aggregate_rating_value": format_decimal(
                    aggregate_rating_value
                ),
                "horse_performance_rating_value": (
                    format_decimal(
                        horse_performance_rating_value
                    )
                ),
                "horse_performance_rating_method": (
                    RATING_METHOD
                ),
                "horse_performance_rating_status": (
                    RATING_STATUS
                ),
                "aggregation_model_version": text(
                    row["aggregation_model_version"]
                ),
                "source_horse_performance_aggregate_evidence_sha256": (
                    source_evidence_hash
                ),
                "horse_performance_rating_evidence_sha256": (
                    rating_evidence_hash
                ),
                "source_builder_version": text(
                    row["builder_version"]
                ),
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

    output_rows.sort(
        key=lambda row: (
            text(row["canonical_horse_id"]),
            text(row["rating_as_of_date"]),
            text(row["horse_performance_aggregate_id"]),
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_HORSE_PERFORMANCE_RATING_FACT_V1_BUILD_PASS"
    )
    print(
        f"horse_performance_aggregate_rows={len(input_rows)}"
    )
    print(
        f"horse_performance_rating_rows={len(output_rows)}"
    )
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
