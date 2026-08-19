from __future__ import annotations

import csv
import hashlib
import os
import re
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = (
    ROOT
    / "config"
    / "performance-intelligence"
    / "edgeiq_length_conversion_parameter_source_v1.csv"
)

OUTPUT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_length_conversion_parameter_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_length_conversion_parameter_fact_v1.0.0"
)
CONVERSION_SCOPE = "DISTANCE_EXACT"

SOURCE_FIELDS = [
    "conversion_scope",
    "official_distance_metres",
    "seconds_per_length",
    "conversion_model_version",
    "parameter_status",
    "effective_from_date",
    "effective_to_date",
    "evidence_reference",
    "evidence_sha256",
]

OUTPUT_FIELDS = [
    "length_conversion_parameter_id",
    "conversion_scope",
    "official_distance_metres",
    "seconds_per_length",
    "conversion_model_version",
    "parameter_status",
    "effective_from_date",
    "effective_to_date",
    "evidence_reference",
    "source_evidence_sha256",
    "parameter_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def integer_value(value: object, field: str) -> int:
    raw = text(value)

    try:
        parsed = int(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid integer value for {field}: {raw!r}"
        ) from exc

    if parsed <= 0:
        fail(f"Non-positive integer value for {field}: {raw!r}")

    return parsed


def decimal_value(value: object, field: str) -> Decimal:
    raw = text(value)

    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Invalid decimal value for {field}: {raw!r}"
        ) from exc

    if not parsed.is_finite() or parsed <= 0:
        fail(f"Non-positive decimal value for {field}: {raw!r}")

    return parsed


def date_value(value: object, field: str) -> date:
    raw = text(value)

    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid date value for {field}: {raw!r}"
        ) from exc


def optional_date_value(
    value: object,
    field: str,
) -> date | None:
    raw = text(value)

    if not raw:
        return None

    return date_value(raw, field)


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def read_source() -> list[dict[str, str]]:
    if not SOURCE_PATH.exists():
        return []

    with SOURCE_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            fail(f"Missing source header: {SOURCE_PATH}")

        actual_fields = list(reader.fieldnames)

        if actual_fields != SOURCE_FIELDS:
            fail(
                "Length conversion source fields do not match "
                f"the governed schema. Actual: {actual_fields}"
            )

        return list(reader)


def atomic_write_csv(
    path: Path,
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


def ranges_overlap(
    left_from: date,
    left_to: date | None,
    right_from: date,
    right_to: date | None,
) -> bool:
    maximum_date = date.max

    return (
        left_from <= (right_to or maximum_date)
        and right_from <= (left_to or maximum_date)
    )


def main() -> None:
    source_rows = read_source()

    output_rows: list[dict[str, object]] = []
    published_ranges: dict[
        int,
        list[tuple[date, date | None, str]],
    ] = {}

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    for source_ordinal, row in enumerate(source_rows, start=1):
        scope = text(row["conversion_scope"])

        if scope != CONVERSION_SCOPE:
            fail(
                f"Source row {source_ordinal}: unsupported "
                f"conversion scope {scope!r}."
            )

        distance = integer_value(
            row["official_distance_metres"],
            "official_distance_metres",
        )

        seconds_per_length = decimal_value(
            row["seconds_per_length"],
            "seconds_per_length",
        )

        model_version = text(row["conversion_model_version"])

        if not model_version:
            fail(
                f"Source row {source_ordinal}: blank "
                "conversion_model_version."
            )

        source_status = text(row["parameter_status"])

        if source_status != "APPROVED":
            continue

        effective_from = date_value(
            row["effective_from_date"],
            "effective_from_date",
        )

        effective_to = optional_date_value(
            row["effective_to_date"],
            "effective_to_date",
        )

        if (
            effective_to is not None
            and effective_to < effective_from
        ):
            fail(
                f"Source row {source_ordinal}: effective-to date "
                "precedes effective-from date."
            )

        evidence_reference = text(row["evidence_reference"])

        if not evidence_reference:
            fail(
                f"Source row {source_ordinal}: blank "
                "evidence_reference."
            )

        evidence_sha256 = text(row["evidence_sha256"]).lower()

        if not SHA256_PATTERN.fullmatch(evidence_sha256):
            fail(
                f"Source row {source_ordinal}: evidence_sha256 "
                "is not a valid SHA-256."
            )

        prior_ranges = published_ranges.setdefault(
            distance,
            [],
        )

        for (
            prior_from,
            prior_to,
            prior_parameter_id,
        ) in prior_ranges:
            if ranges_overlap(
                effective_from,
                effective_to,
                prior_from,
                prior_to,
            ):
                fail(
                    f"Source row {source_ordinal}: effective-date "
                    f"overlap at {distance}m with "
                    f"{prior_parameter_id}."
                )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                scope,
                distance,
                format_decimal(seconds_per_length),
                model_version,
                effective_from.isoformat(),
                (
                    effective_to.isoformat()
                    if effective_to is not None
                    else ""
                ),
                evidence_sha256,
            ]
        )

        parameter_id = (
            f"LCP1-{identity_hash[:24].upper()}"
        )

        parameter_evidence_sha256 = sha256_payload(
            [
                parameter_id,
                evidence_reference,
                evidence_sha256,
            ]
        )

        prior_ranges.append(
            (
                effective_from,
                effective_to,
                parameter_id,
            )
        )

        output_rows.append(
            {
                "length_conversion_parameter_id": parameter_id,
                "conversion_scope": scope,
                "official_distance_metres": distance,
                "seconds_per_length": format_decimal(
                    seconds_per_length
                ),
                "conversion_model_version": model_version,
                "parameter_status": "AVAILABLE",
                "effective_from_date": (
                    effective_from.isoformat()
                ),
                "effective_to_date": (
                    effective_to.isoformat()
                    if effective_to is not None
                    else ""
                ),
                "evidence_reference": evidence_reference,
                "source_evidence_sha256": evidence_sha256,
                "parameter_evidence_sha256": (
                    parameter_evidence_sha256
                ),
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

    output_rows.sort(
        key=lambda row: (
            int(text(row["official_distance_metres"])),
            text(row["effective_from_date"]),
            text(row["length_conversion_parameter_id"]),
        )
    )

    parameter_ids = [
        text(row["length_conversion_parameter_id"])
        for row in output_rows
    ]

    if len(parameter_ids) != len(set(parameter_ids)):
        fail("Duplicate deterministic conversion parameter IDs.")

    atomic_write_csv(OUTPUT_PATH, output_rows)

    print(
        "EDGEIQ_LENGTH_CONVERSION_PARAMETER_FACT_V1_BUILD_PASS"
    )
    print(f"source_exists={SOURCE_PATH.exists()}")
    print(f"source_rows={len(source_rows)}")
    print(f"published_parameter_rows={len(output_rows)}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
