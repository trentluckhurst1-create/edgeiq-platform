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

DELTA_PATH = (
    DATA / "edgeiq_race_time_delta_versus_standard_fact_v1.csv"
)
PARAMETER_PATH = (
    DATA / "edgeiq_length_conversion_parameter_fact_v1.csv"
)
OUTPUT_PATH = (
    DATA / "edgeiq_lengths_versus_standard_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_lengths_versus_standard_v1.0.0"
CALCULATION_METHOD = (
    "NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH"
)
CONVERSION_SCOPE = "DISTANCE_EXACT"

OUTPUT_FIELDS = [
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
    "calculation_method",
    "conversion_scope",
    "conversion_model_version",
    "source_race_time_delta_evidence_sha256",
    "source_conversion_parameter_evidence_sha256",
    "lengths_versus_standard_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        fail(f"Missing canonical input: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            fail(f"Missing CSV header: {path}")

        return list(reader.fieldnames), list(reader)


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
        fail(f"{path.name} missing required fields: {missing}")


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


def integer_value(value: object, field_name: str) -> int:
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


def date_value(value: object, field_name: str) -> date:
    raw = text(value)

    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid date field {field_name}: {raw!r}"
        ) from exc


def optional_date_value(
    value: object,
    field_name: str,
) -> date | None:
    raw = text(value)

    if not raw:
        return None

    return date_value(raw, field_name)


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def interpretation(value: Decimal) -> str:
    if value > 0:
        return "FASTER_THAN_STANDARD"

    if value < 0:
        return "SLOWER_THAN_STANDARD"

    return "EQUAL_TO_STANDARD"


def atomic_write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(fd)

    temporary_path = Path(temporary_name)

    try:
        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
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
    delta_fields, delta_rows = read_csv(DELTA_PATH)

    require_fields(
        DELTA_PATH,
        delta_fields,
        [
            "race_time_delta_id",
            "benchmark_observation_id",
            "benchmark_group_id",
            "standard_time_id",
            "race_key",
            "race_date",
            "track_name",
            "official_distance_metres",
            "winner_horse_name",
            "winner_race_time_seconds",
            "standard_time_seconds",
            "time_delta_seconds",
            "race_time_delta_evidence_sha256",
        ],
    )

    if not delta_rows:
        atomic_write_csv(
            OUTPUT_PATH,
            OUTPUT_FIELDS,
            [],
        )

        print("EDGEIQ_LENGTHS_VERSUS_STANDARD_V1_BUILD_PASS")
        print("race_time_delta_rows=0")
        print("conversion_parameter_rows=NOT_REQUIRED")
        print("lengths_versus_standard_rows=0")
        print(f"output={OUTPUT_PATH}")
        return

    if not PARAMETER_PATH.exists():
        fail(
            "Race Time Delta rows exist but the governed Length "
            "Conversion Parameter Fact V1 is missing."
        )

    parameter_fields, parameter_rows = read_csv(PARAMETER_PATH)

    require_fields(
        PARAMETER_PATH,
        parameter_fields,
        [
            "length_conversion_parameter_id",
            "conversion_scope",
            "official_distance_metres",
            "seconds_per_length",
            "conversion_model_version",
            "parameter_status",
            "effective_from_date",
            "effective_to_date",
            "parameter_evidence_sha256",
        ],
    )

    seen_parameter_ids: set[str] = set()

    for parameter in parameter_rows:
        parameter_id = text(
            parameter["length_conversion_parameter_id"]
        )

        if not parameter_id:
            fail("Blank length_conversion_parameter_id.")

        if parameter_id in seen_parameter_ids:
            fail(f"Duplicate conversion parameter: {parameter_id}")

        seen_parameter_ids.add(parameter_id)

        if text(parameter["conversion_scope"]) != CONVERSION_SCOPE:
            fail(
                f"{parameter_id}: unsupported conversion scope."
            )

        if text(parameter["parameter_status"]) != "AVAILABLE":
            fail(
                f"{parameter_id}: non-available parameter row."
            )

        integer_value(
            parameter["official_distance_metres"],
            "official_distance_metres",
        )

        decimal_value(
            parameter["seconds_per_length"],
            "seconds_per_length",
            positive_only=True,
        )

        effective_from = date_value(
            parameter["effective_from_date"],
            "effective_from_date",
        )

        effective_to = optional_date_value(
            parameter["effective_to_date"],
            "effective_to_date",
        )

        if (
            effective_to is not None
            and effective_to < effective_from
        ):
            fail(
                f"{parameter_id}: effective date range is invalid."
            )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []
    seen_delta_ids: set[str] = set()

    for delta in delta_rows:
        delta_id = text(delta["race_time_delta_id"])

        if not delta_id:
            fail("Blank race_time_delta_id.")

        if delta_id in seen_delta_ids:
            fail(f"Duplicate Race Time Delta row: {delta_id}")

        seen_delta_ids.add(delta_id)

        race_date = date_value(delta["race_date"], "race_date")
        distance = integer_value(
            delta["official_distance_metres"],
            "official_distance_metres",
        )

        matches: list[dict[str, str]] = []

        for parameter in parameter_rows:
            parameter_distance = integer_value(
                parameter["official_distance_metres"],
                "official_distance_metres",
            )

            if parameter_distance != distance:
                continue

            effective_from = date_value(
                parameter["effective_from_date"],
                "effective_from_date",
            )

            effective_to = optional_date_value(
                parameter["effective_to_date"],
                "effective_to_date",
            )

            if race_date < effective_from:
                continue

            if (
                effective_to is not None
                and race_date > effective_to
            ):
                continue

            matches.append(parameter)

        if not matches:
            fail(
                f"{delta_id}: no governed conversion parameter "
                f"for {distance}m on {race_date.isoformat()}."
            )

        if len(matches) > 1:
            parameter_ids = [
                text(row["length_conversion_parameter_id"])
                for row in matches
            ]
            fail(
                f"{delta_id}: ambiguous conversion parameters: "
                f"{parameter_ids}"
            )

        parameter = matches[0]

        time_delta = decimal_value(
            delta["time_delta_seconds"],
            "time_delta_seconds",
        )

        seconds_per_length = decimal_value(
            parameter["seconds_per_length"],
            "seconds_per_length",
            positive_only=True,
        )

        lengths_value = -(time_delta / seconds_per_length)

        parameter_id = text(
            parameter["length_conversion_parameter_id"]
        )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                delta_id,
                parameter_id,
                CALCULATION_METHOD,
            ]
        )

        lengths_id = (
            f"LVS1-{identity_hash[:24].upper()}"
        )

        evidence_hash = sha256_payload(
            [
                lengths_id,
                format_decimal(time_delta),
                format_decimal(seconds_per_length),
                format_decimal(lengths_value),
            ]
        )

        output_rows.append(
            {
                "lengths_versus_standard_id": lengths_id,
                "race_time_delta_id": delta_id,
                "benchmark_observation_id": text(
                    delta["benchmark_observation_id"]
                ),
                "benchmark_group_id": text(
                    delta["benchmark_group_id"]
                ),
                "standard_time_id": text(
                    delta["standard_time_id"]
                ),
                "length_conversion_parameter_id": parameter_id,
                "race_key": text(delta["race_key"]),
                "race_date": text(delta["race_date"]),
                "track_name": text(delta["track_name"]),
                "official_distance_metres": distance,
                "winner_horse_name": text(
                    delta["winner_horse_name"]
                ),
                "winner_race_time_seconds": text(
                    delta["winner_race_time_seconds"]
                ),
                "standard_time_seconds": text(
                    delta["standard_time_seconds"]
                ),
                "time_delta_seconds": format_decimal(
                    time_delta
                ),
                "seconds_per_length": format_decimal(
                    seconds_per_length
                ),
                "lengths_versus_standard": format_decimal(
                    lengths_value
                ),
                "lengths_versus_standard_interpretation": (
                    interpretation(lengths_value)
                ),
                "calculation_method": CALCULATION_METHOD,
                "conversion_scope": text(
                    parameter["conversion_scope"]
                ),
                "conversion_model_version": text(
                    parameter["conversion_model_version"]
                ),
                "source_race_time_delta_evidence_sha256": text(
                    delta["race_time_delta_evidence_sha256"]
                ),
                "source_conversion_parameter_evidence_sha256": text(
                    parameter["parameter_evidence_sha256"]
                ),
                "lengths_versus_standard_evidence_sha256": (
                    evidence_hash
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
        OUTPUT_FIELDS,
        output_rows,
    )

    print("EDGEIQ_LENGTHS_VERSUS_STANDARD_V1_BUILD_PASS")
    print(f"race_time_delta_rows={len(delta_rows)}")
    print(f"conversion_parameter_rows={len(parameter_rows)}")
    print(
        "lengths_versus_standard_rows="
        f"{len(output_rows)}"
    )
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
