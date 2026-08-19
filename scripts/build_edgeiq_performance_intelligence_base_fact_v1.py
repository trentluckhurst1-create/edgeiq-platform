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
    DATA / "edgeiq_lengths_versus_standard_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA / "edgeiq_performance_intelligence_base_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_performance_intelligence_base_fact_v1.0.0"
)
CALCULATION_METHOD = (
    "DIRECT_GOVERNED_LENGTHS_VERSUS_STANDARD"
)
PERFORMANCE_STATUS = "OBSERVED_GOVERNED"

OUTPUT_FIELDS = [
    "performance_intelligence_base_id",
    "lengths_versus_standard_id",
    "race_time_delta_id",
    "benchmark_observation_id",
    "benchmark_group_id",
    "standard_time_id",
    "length_conversion_parameter_id",
    "race_key",
    "race_date",
    "track_name",
    "official_distance_metres",
    "winner_horse_name",
    "winner_race_time_seconds",
    "standard_time_seconds",
    "time_delta_seconds",
    "seconds_per_length",
    "raw_performance_lengths",
    "raw_performance_interpretation",
    "performance_status",
    "calculation_method",
    "source_lengths_versus_standard_evidence_sha256",
    "performance_intelligence_base_evidence_sha256",
    "source_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


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
            f"{INPUT_PATH.name} missing required fields: "
            f"{missing}"
        )


def decimal_value(
    value: object,
    field_name: str,
    positive_only: bool = False,
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
        fail(f"Non-finite decimal field {field_name}: {raw!r}")

    if positive_only and parsed <= 0:
        fail(f"Non-positive decimal field {field_name}: {raw!r}")

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
        fail(f"Non-positive integer field {field_name}: {raw!r}")

    return parsed


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def expected_interpretation(
    lengths_value: Decimal,
) -> str:
    if lengths_value > 0:
        return "FASTER_THAN_STANDARD"

    if lengths_value < 0:
        return "SLOWER_THAN_STANDARD"

    return "EQUAL_TO_STANDARD"


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
            "lengths_versus_standard_id",
            "race_time_delta_id",
            "benchmark_observation_id",
            "benchmark_group_id",
            "standard_time_id",
            "length_conversion_parameter_id",
            "race_key",
            "race_date",
            "track_name",
            "official_distance_metres",
            "winner_horse_name",
            "winner_race_time_seconds",
            "standard_time_seconds",
            "time_delta_seconds",
            "seconds_per_length",
            "lengths_versus_standard",
            "lengths_versus_standard_interpretation",
            "lengths_versus_standard_evidence_sha256",
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
            row["lengths_versus_standard_id"]
        )

        if not source_id:
            fail("Blank lengths_versus_standard_id.")

        if source_id in seen_source_ids:
            fail(
                f"Duplicate Lengths Versus Standard row: "
                f"{source_id}"
            )

        seen_source_ids.add(source_id)

        distance = integer_value(
            row["official_distance_metres"],
            "official_distance_metres",
        )

        winner_time = decimal_value(
            row["winner_race_time_seconds"],
            "winner_race_time_seconds",
            positive_only=True,
        )

        standard_time = decimal_value(
            row["standard_time_seconds"],
            "standard_time_seconds",
            positive_only=True,
        )

        time_delta = decimal_value(
            row["time_delta_seconds"],
            "time_delta_seconds",
        )

        seconds_per_length = decimal_value(
            row["seconds_per_length"],
            "seconds_per_length",
            positive_only=True,
        )

        raw_performance_lengths = decimal_value(
            row["lengths_versus_standard"],
            "lengths_versus_standard",
        )

        interpretation = expected_interpretation(
            raw_performance_lengths
        )

        if (
            text(
                row[
                    "lengths_versus_standard_interpretation"
                ]
            )
            != interpretation
        ):
            fail(
                f"{source_id}: source interpretation does not "
                "match the governed lengths value."
            )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                source_id,
                CALCULATION_METHOD,
            ]
        )

        performance_id = (
            f"PIB1-{identity_hash[:24].upper()}"
        )

        if performance_id in seen_output_ids:
            fail(
                f"Duplicate deterministic performance ID: "
                f"{performance_id}"
            )

        seen_output_ids.add(performance_id)

        source_evidence_hash = text(
            row[
                "lengths_versus_standard_evidence_sha256"
            ]
        )

        if not source_evidence_hash:
            fail(
                f"{source_id}: missing governed source "
                "evidence hash."
            )

        performance_evidence_hash = sha256_payload(
            [
                performance_id,
                source_evidence_hash,
                format_decimal(raw_performance_lengths),
                interpretation,
            ]
        )

        output_rows.append(
            {
                "performance_intelligence_base_id": (
                    performance_id
                ),
                "lengths_versus_standard_id": source_id,
                "race_time_delta_id": text(
                    row["race_time_delta_id"]
                ),
                "benchmark_observation_id": text(
                    row["benchmark_observation_id"]
                ),
                "benchmark_group_id": text(
                    row["benchmark_group_id"]
                ),
                "standard_time_id": text(
                    row["standard_time_id"]
                ),
                "length_conversion_parameter_id": text(
                    row["length_conversion_parameter_id"]
                ),
                "race_key": text(row["race_key"]),
                "race_date": text(row["race_date"]),
                "track_name": text(row["track_name"]),
                "official_distance_metres": distance,
                "winner_horse_name": text(
                    row["winner_horse_name"]
                ),
                "winner_race_time_seconds": format_decimal(
                    winner_time
                ),
                "standard_time_seconds": format_decimal(
                    standard_time
                ),
                "time_delta_seconds": format_decimal(
                    time_delta
                ),
                "seconds_per_length": format_decimal(
                    seconds_per_length
                ),
                "raw_performance_lengths": format_decimal(
                    raw_performance_lengths
                ),
                "raw_performance_interpretation": (
                    interpretation
                ),
                "performance_status": PERFORMANCE_STATUS,
                "calculation_method": CALCULATION_METHOD,
                "source_lengths_versus_standard_evidence_sha256": (
                    source_evidence_hash
                ),
                "performance_intelligence_base_evidence_sha256": (
                    performance_evidence_hash
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
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_BASE_FACT_V1_BUILD_PASS"
    )
    print(f"lengths_versus_standard_rows={len(input_rows)}")
    print(
        "performance_intelligence_base_rows="
        f"{len(output_rows)}"
    )
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
