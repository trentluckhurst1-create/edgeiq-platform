from __future__ import annotations

import csv
import hashlib
import math
import os
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OBSERVATION_PATH = (
    DATA / "edgeiq_horse_performance_observation_fact_v1.csv"
)

PARAMETER_PATH = (
    DATA
    / "edgeiq_horse_performance_aggregation_parameter_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_horse_performance_aggregate_fact_v1.0.0"
)

AGGREGATE_STATUS = "HISTORICAL_AGGREGATE_GOVERNED"

SUPPORTED_METHOD_PAIRS = {
    ("ARITHMETIC_MEAN", "NONE"),
    (
        "WEIGHTED_ARITHMETIC_MEAN",
        "EXPONENTIAL_HALF_LIFE",
    ),
}

OUTPUT_FIELDS = [
    "horse_performance_aggregate_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "aggregate_as_of_date",
    "horse_performance_aggregation_parameter_id",
    "aggregation_method",
    "maximum_observations",
    "lookback_days",
    "minimum_observations",
    "recency_weighting_method",
    "recency_half_life_days",
    "eligible_observation_count",
    "included_observation_count",
    "oldest_included_race_date",
    "newest_included_race_date",
    "total_weight",
    "aggregate_rating_value",
    "aggregate_status",
    "aggregation_model_version",
    "included_observation_ids_sha256",
    "source_parameter_evidence_sha256",
    "source_observation_evidence_sha256",
    "horse_performance_aggregate_evidence_sha256",
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


def date_value(value: object, field_name: str) -> date:
    raw = text(value)

    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid date field {field_name}: {raw!r}"
        ) from exc


def optional_date_value(value: object) -> date | None:
    raw = text(value)

    if not raw:
        return None

    return date.fromisoformat(raw)


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


def decimal_value(
    value: object,
    field_name: str,
    positive_only: bool = False,
) -> Decimal:
    raw = text(value)

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


def matching_parameter(
    parameters: list[dict[str, str]],
    as_of_date: date,
) -> dict[str, str]:
    matches: list[dict[str, str]] = []

    for parameter in parameters:
        if text(parameter["parameter_status"]) != "AVAILABLE":
            continue

        effective_from = date_value(
            parameter["effective_from_date"],
            "effective_from_date",
        )
        effective_to = optional_date_value(
            parameter["effective_to_date"]
        )

        if as_of_date < effective_from:
            continue

        if effective_to is not None and as_of_date > effective_to:
            continue

        matches.append(parameter)

    if not matches:
        fail(
            "No effective governed horse aggregation parameter for "
            f"{as_of_date.isoformat()}."
        )

    if len(matches) > 1:
        fail(
            "Multiple effective governed horse aggregation "
            f"parameters for {as_of_date.isoformat()}."
        )

    return matches[0]


def main() -> None:
    observation_fields, observation_rows = read_csv(
        OBSERVATION_PATH
    )

    require_fields(
        OBSERVATION_PATH,
        observation_fields,
        [
            "horse_performance_observation_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "race_date",
            "rating_base_value",
            "rating_status",
            "identity_status",
            "horse_performance_observation_evidence_sha256",
        ],
    )

    if not observation_rows:
        atomic_write_csv(OUTPUT_PATH, [])

        print(
            "EDGEIQ_HORSE_PERFORMANCE_AGGREGATE_FACT_V1_BUILD_PASS"
        )
        print("horse_performance_observation_rows=0")
        print("aggregation_parameter_rows=NOT_REQUIRED")
        print("horse_performance_aggregate_rows=0")
        print(f"output={OUTPUT_PATH}")
        return

    parameter_fields, parameter_rows = read_csv(PARAMETER_PATH)

    require_fields(
        PARAMETER_PATH,
        parameter_fields,
        [
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
            "parameter_evidence_sha256",
        ],
    )

    observations_by_horse: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    seen_observation_ids: set[str] = set()

    for observation in observation_rows:
        observation_id = text(
            observation["horse_performance_observation_id"]
        )

        if not observation_id:
            fail("Blank horse_performance_observation_id.")

        if observation_id in seen_observation_ids:
            fail(f"Duplicate observation ID: {observation_id}")

        seen_observation_ids.add(observation_id)

        canonical_horse_id = text(
            observation["canonical_horse_id"]
        )

        if not canonical_horse_id:
            fail(f"{observation_id}: blank canonical_horse_id.")

        if (
            text(observation["rating_status"])
            != "OBSERVED_NORMALISED_GOVERNED"
        ):
            fail(f"{observation_id}: invalid rating status.")

        if (
            text(observation["identity_status"])
            != "IDENTIFIED_GOVERNED"
        ):
            fail(f"{observation_id}: invalid identity status.")

        date_value(observation["race_date"], "race_date")

        decimal_value(
            observation["rating_base_value"],
            "rating_base_value",
        )

        if not text(
            observation[
                "horse_performance_observation_evidence_sha256"
            ]
        ):
            fail(f"{observation_id}: blank observation evidence.")

        observations_by_horse[canonical_horse_id].append(
            observation
        )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []
    seen_aggregate_ids: set[str] = set()

    for canonical_horse_id, horse_rows in observations_by_horse.items():
        horse_rows.sort(
            key=lambda row: (
                date_value(row["race_date"], "race_date"),
                text(row["horse_performance_observation_id"]),
            )
        )

        horse_names = {
            text(row["canonical_horse_name"])
            for row in horse_rows
        }

        if len(horse_names) != 1:
            fail(
                f"{canonical_horse_id}: multiple canonical names "
                f"exist: {sorted(horse_names)}"
            )

        canonical_horse_name = next(iter(horse_names))

        unique_as_of_dates = sorted(
            {
                date_value(row["race_date"], "race_date")
                for row in horse_rows
            }
        )

        for as_of_date in unique_as_of_dates:
            parameter = matching_parameter(
                parameter_rows,
                as_of_date,
            )

            parameter_id = text(
                parameter[
                    "horse_performance_aggregation_parameter_id"
                ]
            )
            aggregation_method = text(
                parameter["aggregation_method"]
            )
            recency_method = text(
                parameter["recency_weighting_method"]
            )

            if (
                aggregation_method,
                recency_method,
            ) not in SUPPORTED_METHOD_PAIRS:
                fail(
                    f"{parameter_id}: unsupported aggregation and "
                    "recency method combination."
                )

            maximum_observations = positive_integer(
                parameter["maximum_observations"],
                "maximum_observations",
            )
            lookback_days = positive_integer(
                parameter["lookback_days"],
                "lookback_days",
            )
            minimum_observations = positive_integer(
                parameter["minimum_observations"],
                "minimum_observations",
            )

            if minimum_observations > maximum_observations:
                fail(
                    f"{parameter_id}: minimum observations exceed "
                    "maximum observations."
                )

            half_life: Decimal | None = None

            if recency_method == "EXPONENTIAL_HALF_LIFE":
                half_life = decimal_value(
                    parameter["recency_half_life_days"],
                    "recency_half_life_days",
                    positive_only=True,
                )
            elif text(parameter["recency_half_life_days"]):
                fail(
                    f"{parameter_id}: NONE recency method contains "
                    "a half-life."
                )

            lookback_start = (
                as_of_date - timedelta(days=lookback_days)
            )

            eligible_rows = [
                row
                for row in horse_rows
                if (
                    lookback_start
                    <= date_value(row["race_date"], "race_date")
                    <= as_of_date
                )
            ]

            eligible_rows.sort(
                key=lambda row: (
                    date_value(row["race_date"], "race_date"),
                    text(row["horse_performance_observation_id"]),
                ),
                reverse=True,
            )

            included_rows = eligible_rows[:maximum_observations]

            if len(included_rows) < minimum_observations:
                continue

            weighted_values: list[tuple[Decimal, Decimal]] = []

            for observation in included_rows:
                rating_value = decimal_value(
                    observation["rating_base_value"],
                    "rating_base_value",
                )
                observation_date = date_value(
                    observation["race_date"],
                    "race_date",
                )
                age_days = (as_of_date - observation_date).days

                if age_days < 0:
                    fail(
                        "Future observation entered historical "
                        "aggregate."
                    )

                if aggregation_method == "ARITHMETIC_MEAN":
                    weight = Decimal("1")
                else:
                    if half_life is None:
                        fail(
                            f"{parameter_id}: missing half-life."
                        )

                    exponent = Decimal(age_days) / half_life

                    weight_float = math.pow(
                        0.5,
                        float(exponent),
                    )

                    if (
                        not math.isfinite(weight_float)
                        or weight_float <= 0
                    ):
                        fail(
                            f"{parameter_id}: invalid recency weight."
                        )

                    weight = Decimal(str(weight_float))

                weighted_values.append(
                    (
                        rating_value,
                        weight,
                    )
                )

            with localcontext() as context:
                context.prec = 40

                total_weight = sum(
                    (
                        weight
                        for _, weight in weighted_values
                    ),
                    Decimal("0"),
                )

                if total_weight <= 0:
                    fail(
                        f"{parameter_id}: aggregate total weight "
                        "is not positive."
                    )

                weighted_sum = sum(
                    (
                        value * weight
                        for value, weight in weighted_values
                    ),
                    Decimal("0"),
                )

                aggregate_value = weighted_sum / total_weight

            included_rows_chronological = sorted(
                included_rows,
                key=lambda row: (
                    date_value(row["race_date"], "race_date"),
                    text(row["horse_performance_observation_id"]),
                ),
            )

            included_ids = [
                text(
                    row["horse_performance_observation_id"]
                )
                for row in included_rows_chronological
            ]

            included_evidence_hashes = [
                text(
                    row[
                        "horse_performance_observation_evidence_sha256"
                    ]
                )
                for row in included_rows_chronological
            ]

            included_ids_sha256 = sha256_payload(included_ids)
            source_observation_evidence_sha256 = (
                sha256_payload(included_evidence_hashes)
            )

            identity_hash = sha256_payload(
                [
                    CONTRACT_VERSION,
                    canonical_horse_id,
                    as_of_date.isoformat(),
                    parameter_id,
                    *included_ids,
                ]
            )

            aggregate_id = (
                f"HPA1-{identity_hash[:24].upper()}"
            )

            if aggregate_id in seen_aggregate_ids:
                fail(
                    f"Duplicate deterministic aggregate ID: "
                    f"{aggregate_id}"
                )

            seen_aggregate_ids.add(aggregate_id)

            parameter_evidence_sha256 = text(
                parameter["parameter_evidence_sha256"]
            )

            if not parameter_evidence_sha256:
                fail(
                    f"{parameter_id}: blank parameter evidence."
                )

            aggregate_evidence_sha256 = sha256_payload(
                [
                    aggregate_id,
                    parameter_evidence_sha256,
                    source_observation_evidence_sha256,
                    format_decimal(aggregate_value),
                    format_decimal(total_weight),
                    len(included_rows),
                    AGGREGATE_STATUS,
                ]
            )

            included_dates = [
                date_value(row["race_date"], "race_date")
                for row in included_rows
            ]

            output_rows.append(
                {
                    "horse_performance_aggregate_id": (
                        aggregate_id
                    ),
                    "canonical_horse_id": canonical_horse_id,
                    "canonical_horse_name": canonical_horse_name,
                    "aggregate_as_of_date": (
                        as_of_date.isoformat()
                    ),
                    "horse_performance_aggregation_parameter_id": (
                        parameter_id
                    ),
                    "aggregation_method": aggregation_method,
                    "maximum_observations": maximum_observations,
                    "lookback_days": lookback_days,
                    "minimum_observations": minimum_observations,
                    "recency_weighting_method": recency_method,
                    "recency_half_life_days": (
                        format_decimal(half_life)
                        if half_life is not None
                        else ""
                    ),
                    "eligible_observation_count": len(
                        eligible_rows
                    ),
                    "included_observation_count": len(
                        included_rows
                    ),
                    "oldest_included_race_date": min(
                        included_dates
                    ).isoformat(),
                    "newest_included_race_date": max(
                        included_dates
                    ).isoformat(),
                    "total_weight": format_decimal(total_weight),
                    "aggregate_rating_value": format_decimal(
                        aggregate_value
                    ),
                    "aggregate_status": AGGREGATE_STATUS,
                    "aggregation_model_version": text(
                        parameter["aggregation_model_version"]
                    ),
                    "included_observation_ids_sha256": (
                        included_ids_sha256
                    ),
                    "source_parameter_evidence_sha256": (
                        parameter_evidence_sha256
                    ),
                    "source_observation_evidence_sha256": (
                        source_observation_evidence_sha256
                    ),
                    "horse_performance_aggregate_evidence_sha256": (
                        aggregate_evidence_sha256
                    ),
                    "builder_version": BUILDER_VERSION,
                    "contract_version": CONTRACT_VERSION,
                    "built_at_utc": built_at_utc,
                }
            )

    output_rows.sort(
        key=lambda row: (
            text(row["canonical_horse_id"]),
            text(row["aggregate_as_of_date"]),
            text(
                row[
                    "horse_performance_aggregation_parameter_id"
                ]
            ),
        )
    )

    atomic_write_csv(OUTPUT_PATH, output_rows)

    print(
        "EDGEIQ_HORSE_PERFORMANCE_AGGREGATE_FACT_V1_BUILD_PASS"
    )
    print(
        "horse_performance_observation_rows="
        f"{len(observation_rows)}"
    )
    print(
        "aggregation_parameter_rows="
        f"{len(parameter_rows)}"
    )
    print(
        "horse_performance_aggregate_rows="
        f"{len(output_rows)}"
    )
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
