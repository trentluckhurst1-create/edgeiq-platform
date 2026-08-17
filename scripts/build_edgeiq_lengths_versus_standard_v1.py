
from __future__ import annotations

from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timezone
from typing import Iterable
import csv
import hashlib
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DELTA_PATH = (
    DATA
    / "edgeiq_race_time_delta_versus_standard_fact_v1.csv"
)

PARAMETER_PATH = (
    DATA
    / "edgeiq_length_conversion_parameter_fact_v2.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_lengths_versus_standard_fact_v1.csv"
)

REJECTION_PATH = (
    DATA
    / "edgeiq_lengths_versus_standard_v2_rejections.csv"
)

CONTRACT_VERSION = "2.0.0"
BUILDER_VERSION = "edgeiq_lengths_versus_standard_v2.0.0"

CALCULATION_METHOD = (
    "NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH"
)

CONVERSION_SCOPE = "SURFACE_CONDITION"

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
    "winner_canonical_horse_id",
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

REJECTION_FIELDS = [
    "race_time_delta_id",
    "benchmark_observation_id",
    "race_key",
    "race_date",
    "track_name",
    "official_distance_metres",
    "surface_group",
    "track_condition",
    "rejection_reason",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def decimal_value(
    value: object,
    field: str,
    positive_only: bool = False,
) -> Decimal:
    value_text = text(value)

    try:
        result = Decimal(value_text)
    except InvalidOperation:
        fail(
            f"{field}: invalid decimal "
            f"{value_text!r}"
        )

    if not result.is_finite():
        fail(
            f"{field}: non-finite decimal"
        )

    if positive_only and result <= 0:
        fail(
            f"{field}: expected positive decimal"
        )

    return result


def integer_value(
    value: object,
    field: str,
) -> int:
    result = decimal_value(
        value,
        field,
    )

    if result != result.to_integral_value():
        fail(
            f"{field}: expected integer value"
        )

    return int(result)


def optional_integer(
    value: object,
) -> int | None:
    value_text = text(value)

    if not value_text:
        return None

    try:
        result = Decimal(value_text)
    except InvalidOperation:
        return None

    if (
        not result.is_finite()
        or result
        != result.to_integral_value()
    ):
        return None

    return int(result)


def date_value(
    value: object,
    field: str,
) -> date:
    value_text = text(value)

    try:
        return date.fromisoformat(
            value_text[:10]
        )
    except Exception:
        fail(
            f"{field}: invalid date "
            f"{value_text!r}"
        )


def optional_date_value(
    value: object,
    field: str,
) -> date | None:
    value_text = text(value)

    if not value_text:
        return None

    return date_value(
        value_text,
        field,
    )


def format_decimal(
    value: Decimal,
) -> str:
    return (
        f"{value.quantize(Decimal('0.000001')):.6f}"
    )


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


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
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
        fail(
            f"{path.name} missing required fields: "
            f"{missing}"
        )


def atomic_write_csv(
    path: Path,
    fields: list[str],
    rows: list[dict[str, object]],
) -> None:
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(rows)

    os.replace(
        temporary,
        path,
    )


def normalise_surface(
    value: object,
) -> str:
    surface = (
        text(value)
        .upper()
        .replace(" ", "_")
        .replace("-", "_")
    )

    if surface in {
        "SYNTHETIC",
        "POLYTRACK",
        "TAPETA",
        "PRO_RIDE",
        "PRO_RIDE_SYNTHETIC",
        "ALL_WEATHER",
        "AWT",
    }:
        return "AUSTRALIAN_SYNTHETIC"

    if surface in {
        "AUSTRALIAN_SYNTHETIC",
        "TURF",
    }:
        return surface

    return surface


def track_condition_number(
    value: object,
) -> int | None:
    condition = (
        text(value)
        .upper()
        .replace("_", " ")
        .strip()
    )

    direct = optional_integer(
        condition
    )

    if direct is not None:
        return direct

    number_match = re.search(
        r"\b(10|[1-9])\b",
        condition,
    )

    if number_match:
        return int(
            number_match.group(1)
        )

    if "FIRM" in condition:
        return 1

    if "GOOD" in condition:
        return 3

    if "SOFT" in condition:
        return 5

    if "HEAVY" in condition:
        return 8

    return None


def track_condition_group(
    value: object,
    surface_group: str,
) -> str:
    if (
        surface_group
        == "AUSTRALIAN_SYNTHETIC"
    ):
        return "STANDARD_SYNTHETIC"

    condition_number = (
        track_condition_number(value)
    )

    if condition_number is None:
        condition = (
            text(value)
            .upper()
            .replace("_", " ")
        )

        if "FIRM" in condition:
            return "FIRM"

        if "GOOD" in condition:
            return "GOOD"

        if "SOFT" in condition:
            return "SOFT"

        if "HEAVY" in condition:
            return "HEAVY"

        return ""

    if 1 <= condition_number <= 2:
        return "FIRM"

    if 3 <= condition_number <= 4:
        return "GOOD"

    if 5 <= condition_number <= 7:
        return "SOFT"

    if 8 <= condition_number <= 10:
        return "HEAVY"

    return ""


def interpretation(
    value: Decimal,
) -> str:
    if value > 0:
        return "FASTER_THAN_STANDARD"

    if value < 0:
        return "SLOWER_THAN_STANDARD"

    return "EQUAL_TO_STANDARD"


def parameter_matches(
    parameter: dict[str, str],
    race_date: date,
    race_surface: str,
    condition_number: int | None,
    condition_group: str,
) -> bool:
    if (
        text(
            parameter[
                "conversion_scope"
            ]
        )
        != CONVERSION_SCOPE
    ):
        return False

    if (
        text(
            parameter[
                "parameter_status"
            ]
        )
        != "AVAILABLE"
    ):
        return False

    parameter_surface = (
        normalise_surface(
            parameter[
                "surface_group"
            ]
        )
    )

    if parameter_surface != race_surface:
        return False

    effective_from = date_value(
        parameter[
            "effective_from_date"
        ],
        "effective_from_date",
    )

    effective_to = optional_date_value(
        parameter[
            "effective_to_date"
        ],
        "effective_to_date",
    )

    if race_date < effective_from:
        return False

    if (
        effective_to is not None
        and race_date > effective_to
    ):
        return False

    parameter_group = text(
        parameter[
            "track_condition_group"
        ]
    ).upper()

    if (
        race_surface
        == "AUSTRALIAN_SYNTHETIC"
    ):
        return (
            parameter_group
            == "STANDARD_SYNTHETIC"
        )

    parameter_min = optional_integer(
        parameter[
            "track_condition_min"
        ]
    )

    parameter_max = optional_integer(
        parameter[
            "track_condition_max"
        ]
    )

    if (
        condition_number is not None
        and parameter_min is not None
        and parameter_max is not None
    ):
        return (
            parameter_min
            <= condition_number
            <= parameter_max
        )

    return (
        bool(condition_group)
        and parameter_group
        == condition_group
    )


def main() -> None:
    delta_fields, delta_rows = (
        read_csv(DELTA_PATH)
    )

    parameter_fields, parameter_rows = (
        read_csv(PARAMETER_PATH)
    )

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
            "surface_group",
            "track_condition",
            "winner_canonical_horse_id",
            "winner_horse_name",
            "winner_race_time_seconds",
            "standard_time_seconds",
            "time_delta_seconds",
            "race_time_delta_evidence_sha256",
        ],
    )

    require_fields(
        PARAMETER_PATH,
        parameter_fields,
        [
            "length_conversion_parameter_id",
            "conversion_scope",
            "surface_group",
            "track_condition_min",
            "track_condition_max",
            "track_condition_group",
            "lengths_per_second",
            "seconds_per_length",
            "conversion_model_version",
            "parameter_status",
            "effective_from_date",
            "effective_to_date",
            "parameter_evidence_sha256",
        ],
    )

    if len(parameter_rows) != 5:
        fail(
            "Expected exactly five approved V2 "
            "conversion parameters"
        )

    seen_parameter_ids = set()

    for parameter in parameter_rows:
        parameter_id = text(
            parameter[
                "length_conversion_parameter_id"
            ]
        )

        if not parameter_id:
            fail(
                "Blank conversion parameter ID"
            )

        if parameter_id in seen_parameter_ids:
            fail(
                "Duplicate conversion parameter: "
                f"{parameter_id}"
            )

        seen_parameter_ids.add(
            parameter_id
        )

        if (
            text(
                parameter[
                    "conversion_scope"
                ]
            )
            != CONVERSION_SCOPE
        ):
            fail(
                f"{parameter_id}: unsupported "
                "conversion scope"
            )

        if (
            text(
                parameter[
                    "parameter_status"
                ]
            )
            != "AVAILABLE"
        ):
            fail(
                f"{parameter_id}: unavailable "
                "parameter"
            )

        decimal_value(
            parameter[
                "seconds_per_length"
            ],
            "seconds_per_length",
            positive_only=True,
        )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows = []
    rejection_rows = []
    seen_delta_ids = set()
    parameter_usage = {}

    for delta in delta_rows:
        delta_id = text(
            delta["race_time_delta_id"]
        )

        if not delta_id:
            fail(
                "Blank race-time-delta ID"
            )

        if delta_id in seen_delta_ids:
            fail(
                f"Duplicate delta row: {delta_id}"
            )

        seen_delta_ids.add(
            delta_id
        )

        race_date = date_value(
            delta["race_date"],
            "race_date",
        )

        race_surface = normalise_surface(
            delta["surface_group"]
        )

        condition_number = (
            track_condition_number(
                delta[
                    "track_condition"
                ]
            )
        )

        condition_group = (
            track_condition_group(
                delta[
                    "track_condition"
                ],
                race_surface,
            )
        )

        matches = [
            parameter
            for parameter in parameter_rows
            if parameter_matches(
                parameter,
                race_date,
                race_surface,
                condition_number,
                condition_group,
            )
        ]

        if not matches:
            rejection_rows.append({
                "race_time_delta_id":
                    delta_id,

                "benchmark_observation_id":
                    text(
                        delta[
                            "benchmark_observation_id"
                        ]
                    ),

                "race_key":
                    text(
                        delta["race_key"]
                    ),

                "race_date":
                    text(
                        delta["race_date"]
                    ),

                "track_name":
                    text(
                        delta["track_name"]
                    ),

                "official_distance_metres":
                    text(
                        delta[
                            "official_distance_metres"
                        ]
                    ),

                "surface_group":
                    race_surface,

                "track_condition":
                    text(
                        delta[
                            "track_condition"
                        ]
                    ),

                "rejection_reason":
                    (
                        "NO_GOVERNED_SURFACE_"
                        "CONDITION_LENGTH_PARAMETER"
                    ),

                "builder_version":
                    BUILDER_VERSION,

                "contract_version":
                    CONTRACT_VERSION,

                "built_at_utc":
                    built_at_utc,
            })

            continue

        if len(matches) > 1:
            parameter_ids = [
                text(
                    row[
                        "length_conversion_parameter_id"
                    ]
                )
                for row in matches
            ]

            fail(
                f"{delta_id}: ambiguous V2 "
                f"parameters {parameter_ids}"
            )

        parameter = matches[0]

        parameter_id = text(
            parameter[
                "length_conversion_parameter_id"
            ]
        )

        parameter_usage[
            parameter_id
        ] = (
            parameter_usage.get(
                parameter_id,
                0,
            )
            + 1
        )

        time_delta = decimal_value(
            delta[
                "time_delta_seconds"
            ],
            "time_delta_seconds",
        )

        seconds_per_length = decimal_value(
            parameter[
                "seconds_per_length"
            ],
            "seconds_per_length",
            positive_only=True,
        )

        lengths_value = -(
            time_delta
            / seconds_per_length
        )

        identity_hash = sha256_payload([
            CONTRACT_VERSION,
            delta_id,
            parameter_id,
            CALCULATION_METHOD,
        ])

        lengths_id = (
            f"LVS1-"
            f"{identity_hash[:24].upper()}"
        )

        evidence_hash = sha256_payload([
            lengths_id,
            race_surface,
            condition_group,
            format_decimal(
                time_delta
            ),
            format_decimal(
                seconds_per_length
            ),
            format_decimal(
                lengths_value
            ),
        ])

        output_rows.append({
            "lengths_versus_standard_id":
                lengths_id,

            "race_time_delta_id":
                delta_id,

            "benchmark_observation_id":
                text(
                    delta[
                        "benchmark_observation_id"
                    ]
                ),

            "benchmark_group_id":
                text(
                    delta[
                        "benchmark_group_id"
                    ]
                ),

            "standard_time_id":
                text(
                    delta[
                        "standard_time_id"
                    ]
                ),

            "length_conversion_parameter_id":
                parameter_id,

            "race_key":
                text(
                    delta["race_key"]
                ),

            "race_date":
                text(
                    delta["race_date"]
                ),

            "track_name":
                text(
                    delta["track_name"]
                ),

            "official_distance_metres":
                integer_value(
                    delta[
                        "official_distance_metres"
                    ],
                    "official_distance_metres",
                ),

            "winner_canonical_horse_id":
                text(
                    delta[
                        "winner_canonical_horse_id"
                    ]
                ),

            "winner_horse_name":
                text(
                    delta[
                        "winner_horse_name"
                    ]
                ),

            "winner_race_time_seconds":
                text(
                    delta[
                        "winner_race_time_seconds"
                    ]
                ),

            "standard_time_seconds":
                text(
                    delta[
                        "standard_time_seconds"
                    ]
                ),

            "time_delta_seconds":
                format_decimal(
                    time_delta
                ),

            "seconds_per_length":
                format_decimal(
                    seconds_per_length
                ),

            "lengths_versus_standard":
                format_decimal(
                    lengths_value
                ),

            "lengths_versus_standard_interpretation":
                interpretation(
                    lengths_value
                ),

            "calculation_method":
                CALCULATION_METHOD,

            "conversion_scope":
                text(
                    parameter[
                        "conversion_scope"
                    ]
                ),

            "conversion_model_version":
                text(
                    parameter[
                        "conversion_model_version"
                    ]
                ),

            "source_race_time_delta_evidence_sha256":
                text(
                    delta[
                        "race_time_delta_evidence_sha256"
                    ]
                ),

            "source_conversion_parameter_evidence_sha256":
                text(
                    parameter[
                        "parameter_evidence_sha256"
                    ]
                ),

            "lengths_versus_standard_evidence_sha256":
                evidence_hash,

            "builder_version":
                BUILDER_VERSION,

            "contract_version":
                CONTRACT_VERSION,

            "built_at_utc":
                built_at_utc,
        })

    output_rows.sort(
        key=lambda row: (
            text(row["race_date"]),
            text(row["track_name"]).casefold(),
            int(
                text(
                    row[
                        "official_distance_metres"
                    ]
                )
            ),
            text(
                row[
                    "benchmark_observation_id"
                ]
            ),
        )
    )

    rejection_rows.sort(
        key=lambda row: (
            text(row["race_date"]),
            text(row["track_name"]).casefold(),
            text(row["race_key"]),
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        OUTPUT_FIELDS,
        output_rows,
    )

    atomic_write_csv(
        REJECTION_PATH,
        REJECTION_FIELDS,
        rejection_rows,
    )

    print(
        "EDGEIQ_LENGTHS_VERSUS_"
        "STANDARD_V2_BUILD_PASS"
    )

    print(
        f"race_time_delta_rows="
        f"{len(delta_rows)}"
    )

    print(
        f"conversion_parameter_rows="
        f"{len(parameter_rows)}"
    )

    print(
        f"lengths_versus_standard_rows="
        f"{len(output_rows)}"
    )

    print(
        f"rejection_rows="
        f"{len(rejection_rows)}"
    )

    for parameter_id in sorted(
        parameter_usage
    ):
        print(
            f"parameter_usage[{parameter_id}]="
            f"{parameter_usage[parameter_id]}"
        )

    print(f"output={OUTPUT_PATH}")
    print(f"rejections={REJECTION_PATH}")


if __name__ == "__main__":
    main()
