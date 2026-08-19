from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_PATH = (
    DATA / "edgeiq_performance_normalisation_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA / "edgeiq_performance_rating_base_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_performance_rating_base_fact_v1.0.0"
)
RATING_METHOD = "DIRECT_NORMALISED_PERFORMANCE_VALUE"
RATING_STATUS = "OBSERVED_NORMALISED_GOVERNED"

OUTPUT_FIELDS = [
    "performance_rating_base_id",
    "performance_normalisation_id",
    "performance_intelligence_base_id",
    "normalisation_parameter_id",
    "lengths_versus_standard_id",
    "benchmark_observation_id",
    "race_key",
    "race_date",
    "track_name",
    "official_distance_metres",
    "winner_horse_name",
    "raw_performance_lengths",
    "normalised_performance_value",
    "rating_base_value",
    "rating_method",
    "rating_status",
    "normalisation_model_version",
    "source_performance_normalisation_evidence_sha256",
    "performance_rating_base_evidence_sha256",
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


def integer_value(
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
            "performance_normalisation_id",
            "performance_intelligence_base_id",
            "normalisation_parameter_id",
            "lengths_versus_standard_id",
            "benchmark_observation_id",
            "race_key",
            "race_date",
            "track_name",
            "official_distance_metres",
            "winner_horse_name",
            "raw_performance_lengths",
            "normalised_performance_value",
            "normalisation_status",
            "normalisation_model_version",
            "performance_normalisation_evidence_sha256",
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
    seen_source_ids: set[str] = set()
    seen_output_ids: set[str] = set()

    for row in input_rows:
        source_id = text(
            row["performance_normalisation_id"]
        )

        if not source_id:
            fail("Blank performance_normalisation_id.")

        if source_id in seen_source_ids:
            fail(
                f"Duplicate Performance Normalisation row: "
                f"{source_id}"
            )

        seen_source_ids.add(source_id)

        if (
            text(row["normalisation_status"])
            != "NORMALISED_GOVERNED"
        ):
            fail(
                f"{source_id}: source normalisation status "
                "is not governed."
            )

        distance = integer_value(
            row["official_distance_metres"],
            "official_distance_metres",
        )

        raw_performance_lengths = decimal_value(
            row["raw_performance_lengths"],
            "raw_performance_lengths",
        )

        normalised_value = decimal_value(
            row["normalised_performance_value"],
            "normalised_performance_value",
        )

        rating_base_value = normalised_value

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                source_id,
                RATING_METHOD,
            ]
        )

        rating_base_id = (
            f"PRB1-{identity_hash[:24].upper()}"
        )

        if rating_base_id in seen_output_ids:
            fail(
                f"Duplicate deterministic rating-base ID: "
                f"{rating_base_id}"
            )

        seen_output_ids.add(rating_base_id)

        source_evidence_hash = text(
            row[
                "performance_normalisation_evidence_sha256"
            ]
        )

        if not source_evidence_hash:
            fail(
                f"{source_id}: missing source normalisation "
                "evidence hash."
            )

        rating_evidence_hash = sha256_payload(
            [
                rating_base_id,
                source_evidence_hash,
                format_decimal(rating_base_value),
                RATING_STATUS,
            ]
        )

        output_rows.append(
            {
                "performance_rating_base_id": rating_base_id,
                "performance_normalisation_id": source_id,
                "performance_intelligence_base_id": text(
                    row["performance_intelligence_base_id"]
                ),
                "normalisation_parameter_id": text(
                    row["normalisation_parameter_id"]
                ),
                "lengths_versus_standard_id": text(
                    row["lengths_versus_standard_id"]
                ),
                "benchmark_observation_id": text(
                    row["benchmark_observation_id"]
                ),
                "race_key": text(row["race_key"]),
                "race_date": text(row["race_date"]),
                "track_name": text(row["track_name"]),
                "official_distance_metres": distance,
                "winner_horse_name": text(
                    row["winner_horse_name"]
                ),
                "raw_performance_lengths": format_decimal(
                    raw_performance_lengths
                ),
                "normalised_performance_value": format_decimal(
                    normalised_value
                ),
                "rating_base_value": format_decimal(
                    rating_base_value
                ),
                "rating_method": RATING_METHOD,
                "rating_status": RATING_STATUS,
                "normalisation_model_version": text(
                    row["normalisation_model_version"]
                ),
                "source_performance_normalisation_evidence_sha256": (
                    source_evidence_hash
                ),
                "performance_rating_base_evidence_sha256": (
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
            text(row["race_date"]),
            text(row["track_name"]).casefold(),
            int(text(row["official_distance_metres"])),
            text(row["benchmark_observation_id"]),
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_PERFORMANCE_RATING_BASE_FACT_V1_BUILD_PASS"
    )
    print(
        f"performance_normalisation_rows={len(input_rows)}"
    )
    print(
        f"performance_rating_base_rows={len(output_rows)}"
    )
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
