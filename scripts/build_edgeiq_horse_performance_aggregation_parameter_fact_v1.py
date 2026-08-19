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
    / "edgeiq_horse_performance_aggregation_parameter_source_v1.csv"
)

OUTPUT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_horse_performance_aggregation_parameter_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_horse_performance_aggregation_parameter_fact_v1.0.0"
)

SUPPORTED_AGGREGATION_METHODS = {
    "ARITHMETIC_MEAN",
    "WEIGHTED_ARITHMETIC_MEAN",
}

SUPPORTED_RECENCY_METHODS = {
    "NONE",
    "EXPONENTIAL_HALF_LIFE",
}

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

SOURCE_FIELDS = [
    "aggregation_method",
    "maximum_observations",
    "lookback_days",
    "minimum_observations",
    "recency_weighting_method",
    "recency_half_life_days",
    "aggregation_model_version",
    "parameter_status",
    "effective_from_date",
    "effective_to_date",
    "evidence_reference",
    "evidence_sha256",
]

OUTPUT_FIELDS = [
    "horse_performance_aggregation_parameter_id",
    "aggregation_method",
    "maximum_observations",
    "lookback_days",
    "minimum_observations",
    "recency_weighting_method",
    "recency_half_life_days",
    "aggregation_model_version",
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


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def positive_integer(value: object, field_name: str) -> int:
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


def positive_decimal(value: object, field_name: str) -> Decimal:
    raw = text(value)

    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Invalid decimal field {field_name}: {raw!r}"
        ) from exc

    if not parsed.is_finite() or parsed <= 0:
        fail(f"Invalid positive decimal field {field_name}: {raw!r}")

    return parsed


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


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


def ranges_overlap(
    left_from: date,
    left_to: date | None,
    right_from: date,
    right_to: date | None,
) -> bool:
    return (
        left_from <= (right_to or date.max)
        and right_from <= (left_to or date.max)
    )


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
            fail(f"Missing governed source header: {SOURCE_PATH}")

        actual_fields = list(reader.fieldnames)

        if actual_fields != SOURCE_FIELDS:
            fail(
                "Horse aggregation parameter source fields do not "
                f"match the governed schema. Actual: {actual_fields}"
            )

        return list(reader)


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
    source_rows = read_source()
    output_rows: list[dict[str, object]] = []

    published_ranges: list[
        tuple[date, date | None, str]
    ] = []

    seen_parameter_ids: set[str] = set()

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    for ordinal, row in enumerate(source_rows, start=1):
        if text(row["parameter_status"]) != "APPROVED":
            continue

        aggregation_method = text(row["aggregation_method"])

        if aggregation_method not in SUPPORTED_AGGREGATION_METHODS:
            fail(
                f"Source row {ordinal}: unsupported aggregation "
                f"method {aggregation_method!r}."
            )

        maximum_observations = positive_integer(
            row["maximum_observations"],
            "maximum_observations",
        )

        lookback_days = positive_integer(
            row["lookback_days"],
            "lookback_days",
        )

        minimum_observations = positive_integer(
            row["minimum_observations"],
            "minimum_observations",
        )

        if minimum_observations > maximum_observations:
            fail(
                f"Source row {ordinal}: minimum observations exceed "
                "maximum observations."
            )

        recency_method = text(row["recency_weighting_method"])

        if recency_method not in SUPPORTED_RECENCY_METHODS:
            fail(
                f"Source row {ordinal}: unsupported recency method "
                f"{recency_method!r}."
            )

        raw_half_life = text(row["recency_half_life_days"])

        if recency_method == "NONE":
            if raw_half_life:
                fail(
                    f"Source row {ordinal}: NONE recency method must "
                    "not contain a half-life."
                )

            half_life_value = ""
        else:
            if not raw_half_life:
                fail(
                    f"Source row {ordinal}: exponential recency "
                    "method requires a half-life."
                )

            half_life_value = format_decimal(
                positive_decimal(
                    raw_half_life,
                    "recency_half_life_days",
                )
            )

        model_version = text(row["aggregation_model_version"])

        if not model_version:
            fail(
                f"Source row {ordinal}: blank aggregation model "
                "version."
            )

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
                f"Source row {ordinal}: effective-to date precedes "
                "effective-from date."
            )

        evidence_reference = text(row["evidence_reference"])

        if not evidence_reference:
            fail(
                f"Source row {ordinal}: blank evidence_reference."
            )

        source_evidence_sha256 = text(
            row["evidence_sha256"]
        ).lower()

        if not SHA256_PATTERN.fullmatch(source_evidence_sha256):
            fail(
                f"Source row {ordinal}: invalid evidence_sha256."
            )

        for prior_from, prior_to, prior_id in published_ranges:
            if ranges_overlap(
                effective_from,
                effective_to,
                prior_from,
                prior_to,
            ):
                fail(
                    f"Source row {ordinal}: effective-date overlap "
                    f"with {prior_id}."
                )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                aggregation_method,
                maximum_observations,
                lookback_days,
                minimum_observations,
                recency_method,
                half_life_value,
                model_version,
                effective_from.isoformat(),
                (
                    effective_to.isoformat()
                    if effective_to is not None
                    else ""
                ),
                source_evidence_sha256,
            ]
        )

        parameter_id = (
            f"HPAP1-{identity_hash[:24].upper()}"
        )

        if parameter_id in seen_parameter_ids:
            fail(
                f"Duplicate deterministic parameter ID: "
                f"{parameter_id}"
            )

        seen_parameter_ids.add(parameter_id)

        parameter_evidence_sha256 = sha256_payload(
            [
                parameter_id,
                evidence_reference,
                source_evidence_sha256,
            ]
        )

        published_ranges.append(
            (
                effective_from,
                effective_to,
                parameter_id,
            )
        )

        output_rows.append(
            {
                "horse_performance_aggregation_parameter_id": (
                    parameter_id
                ),
                "aggregation_method": aggregation_method,
                "maximum_observations": maximum_observations,
                "lookback_days": lookback_days,
                "minimum_observations": minimum_observations,
                "recency_weighting_method": recency_method,
                "recency_half_life_days": half_life_value,
                "aggregation_model_version": model_version,
                "parameter_status": "AVAILABLE",
                "effective_from_date": effective_from.isoformat(),
                "effective_to_date": (
                    effective_to.isoformat()
                    if effective_to is not None
                    else ""
                ),
                "evidence_reference": evidence_reference,
                "source_evidence_sha256": source_evidence_sha256,
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
            text(row["effective_from_date"]),
            text(row["effective_to_date"]),
            text(
                row[
                    "horse_performance_aggregation_parameter_id"
                ]
            ),
        )
    )

    atomic_write_csv(OUTPUT_PATH, output_rows)

    print(
        "EDGEIQ_HORSE_PERFORMANCE_AGGREGATION_PARAMETER_FACT_V1_BUILD_PASS"
    )
    print(f"source_exists={SOURCE_PATH.exists()}")
    print(f"source_rows={len(source_rows)}")
    print(f"published_parameter_rows={len(output_rows)}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
