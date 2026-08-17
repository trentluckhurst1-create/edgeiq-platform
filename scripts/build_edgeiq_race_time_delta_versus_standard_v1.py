
from __future__ import annotations

from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Iterable
import csv
import hashlib
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OBSERVATION_PATH = (
    DATA
    / "edgeiq_benchmark_observation_native_compatible_authority_v1.csv"
)

ELIGIBILITY_PATH = (
    DATA
    / "edgeiq_benchmark_eligibility_fact_v1.csv"
)

MEMBERSHIP_PATH = (
    DATA
    / "edgeiq_benchmark_accumulation_membership_fact_v1.csv"
)

STANDARD_TIME_PATH = (
    DATA
    / "edgeiq_standard_time_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_time_delta_versus_standard_fact_v1.csv"
)

CONTRACT_VERSION = "1.2.0"
BUILDER_VERSION = "edgeiq_race_time_delta_versus_standard_v1.2.0"

CALCULATION_METHOD = (
    "WINNER_RACE_TIME_MINUS_STANDARD_TIME_SECONDS"
)

ELIGIBLE_CLASS = "STANDARD_TIME_ELIGIBLE"

OUTPUT_FIELDS = [
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
    "time_delta_interpretation",
    "calculation_method",
    "source_observation_sha256",
    "source_standard_time_evidence_sha256",
    "race_time_delta_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def truthy(value: object) -> bool:
    return text(value).lower() in {
        "true",
        "1",
        "yes",
        "y",
    }


def decimal_value(
    value: object,
    field: str,
    positive_only: bool = False,
) -> Decimal:
    value_text = text(value)

    try:
        result = Decimal(value_text)
    except InvalidOperation:
        fail(f"{field}: invalid decimal value {value_text!r}")

    if not result.is_finite():
        fail(f"{field}: non-finite decimal value")

    if positive_only and result <= 0:
        fail(f"{field}: expected positive decimal")

    return result


def format_decimal(value: Decimal) -> str:
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


def interpretation(value: Decimal) -> str:
    if value < 0:
        return "FASTER_THAN_STANDARD"

    if value > 0:
        return "SLOWER_THAN_STANDARD"

    return "EQUAL_TO_STANDARD"


def main() -> None:
    observation_fields, observation_rows = (
        read_csv(OBSERVATION_PATH)
    )

    eligibility_fields, eligibility_rows = (
        read_csv(ELIGIBILITY_PATH)
    )

    membership_fields, membership_rows = (
        read_csv(MEMBERSHIP_PATH)
    )

    standard_fields, standard_rows = (
        read_csv(STANDARD_TIME_PATH)
    )

    require_fields(
        OBSERVATION_PATH,
        observation_fields,
        [
            "benchmark_observation_id",
            "race_key",
            "race_date",
            "track_name",
            "official_distance_metres",
            "surface",
            "track_condition",
            "winner_canonical_horse_id",
            "winner_horse_name",
            "winner_race_time_seconds",
            "race_source_row_sha256",
            "winner_source_row_sha256",
        ],
    )

    require_fields(
        ELIGIBILITY_PATH,
        eligibility_fields,
        [
            "benchmark_observation_id",
            "benchmark_use_class",
            "standard_time_eligible",
        ],
    )

    require_fields(
        MEMBERSHIP_PATH,
        membership_fields,
        [
            "benchmark_group_id",
            "benchmark_observation_id",
        ],
    )

    require_fields(
        STANDARD_TIME_PATH,
        standard_fields,
        [
            "standard_time_id",
            "benchmark_group_id",
            "standard_time_seconds",
            "standard_time_status",
            "standard_time_evidence_sha256",
        ],
    )

    observations_by_id = {}

    for row in observation_rows:
        observation_id = text(
            row["benchmark_observation_id"]
        )

        if not observation_id:
            fail("Blank benchmark_observation_id")

        if observation_id in observations_by_id:
            fail(
                f"Duplicate observation ID: "
                f"{observation_id}"
            )

        observations_by_id[
            observation_id
        ] = row

    eligibility_by_id = {}

    for row in eligibility_rows:
        observation_id = text(
            row["benchmark_observation_id"]
        )

        if not observation_id:
            fail(
                "Blank eligibility observation ID"
            )

        if observation_id in eligibility_by_id:
            fail(
                f"Duplicate eligibility ID: "
                f"{observation_id}"
            )

        eligibility_by_id[
            observation_id
        ] = row

    group_by_observation = {}

    for row in membership_rows:
        observation_id = text(
            row["benchmark_observation_id"]
        )

        group_id = text(
            row["benchmark_group_id"]
        )

        if not observation_id or not group_id:
            fail(
                "Blank accumulation membership key"
            )

        if observation_id in group_by_observation:
            fail(
                "Observation belongs to multiple groups: "
                f"{observation_id}"
            )

        group_by_observation[
            observation_id
        ] = group_id

    standard_by_group = {}

    for row in standard_rows:
        group_id = text(
            row["benchmark_group_id"]
        )

        if not group_id:
            fail(
                "Blank standard-time group ID"
            )

        if group_id in standard_by_group:
            fail(
                f"Duplicate standard-time group: "
                f"{group_id}"
            )

        standard_by_group[
            group_id
        ] = row

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows = []

    for observation_id in sorted(
        observations_by_id
    ):
        observation = observations_by_id[
            observation_id
        ]

        eligibility = eligibility_by_id.get(
            observation_id
        )

        if eligibility is None:
            fail(
                "Observation missing eligibility row: "
                f"{observation_id}"
            )

        if (
            text(
                eligibility[
                    "benchmark_use_class"
                ]
            )
            != ELIGIBLE_CLASS
            or not truthy(
                eligibility[
                    "standard_time_eligible"
                ]
            )
        ):
            continue

        group_id = group_by_observation.get(
            observation_id
        )

        if not group_id:
            continue

        standard = standard_by_group.get(
            group_id
        )

        if standard is None:
            continue

        standard_status = text(
            standard["standard_time_status"]
        ).upper()

        if standard_status not in {
            "AVAILABLE",
            "READY",
            "APPROVED",
        }:
            continue

        winner_id = text(
            observation[
                "winner_canonical_horse_id"
            ]
        )

        if not winner_id:
            fail(
                f"{observation_id}: blank winner ID "
                "for an eligible observation"
            )

        winner_time = decimal_value(
            observation[
                "winner_race_time_seconds"
            ],
            "winner_race_time_seconds",
            positive_only=True,
        )

        standard_time = decimal_value(
            standard[
                "standard_time_seconds"
            ],
            "standard_time_seconds",
            positive_only=True,
        )

        delta = (
            winner_time
            - standard_time
        )

        standard_time_id = text(
            standard["standard_time_id"]
        )

        identity_hash = sha256_payload([
            CONTRACT_VERSION,
            observation_id,
            standard_time_id,
            CALCULATION_METHOD,
        ])

        race_time_delta_id = (
            f"RTD1-"
            f"{identity_hash[:24].upper()}"
        )

        source_observation_hash = (
            sha256_payload([
                text(
                    observation[
                        "race_source_row_sha256"
                    ]
                ),
                text(
                    observation[
                        "winner_source_row_sha256"
                    ]
                ),
            ])
        )

        evidence_hash = sha256_payload([
            race_time_delta_id,
            winner_id,
            text(observation["surface"]),
            text(
                observation[
                    "track_condition"
                ]
            ),
            format_decimal(winner_time),
            format_decimal(standard_time),
            format_decimal(delta),
        ])

        output_rows.append({
            "race_time_delta_id":
                race_time_delta_id,

            "benchmark_observation_id":
                observation_id,

            "benchmark_group_id":
                group_id,

            "standard_time_id":
                standard_time_id,

            "race_key":
                text(
                    observation["race_key"]
                ),

            "race_date":
                text(
                    observation["race_date"]
                ),

            "track_name":
                text(
                    observation["track_name"]
                ),

            "official_distance_metres":
                text(
                    observation[
                        "official_distance_metres"
                    ]
                ),

            "surface_group":
                text(
                    observation["surface"]
                ).upper(),

            "track_condition":
                text(
                    observation[
                        "track_condition"
                    ]
                ),

            "winner_canonical_horse_id":
                winner_id,

            "winner_horse_name":
                text(
                    observation[
                        "winner_horse_name"
                    ]
                ),

            "winner_race_time_seconds":
                format_decimal(
                    winner_time
                ),

            "standard_time_seconds":
                format_decimal(
                    standard_time
                ),

            "time_delta_seconds":
                format_decimal(
                    delta
                ),

            "time_delta_interpretation":
                interpretation(delta),

            "calculation_method":
                CALCULATION_METHOD,

            "source_observation_sha256":
                source_observation_hash,

            "source_standard_time_evidence_sha256":
                text(
                    standard[
                        "standard_time_evidence_sha256"
                    ]
                ),

            "race_time_delta_evidence_sha256":
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

    atomic_write_csv(
        OUTPUT_PATH,
        OUTPUT_FIELDS,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_TIME_DELTA_"
        "VERSUS_STANDARD_V1_BUILD_PASS"
    )

    print(
        f"observation_rows="
        f"{len(observation_rows)}"
    )

    print(
        f"standard_time_rows="
        f"{len(standard_rows)}"
    )

    print(
        f"race_time_delta_rows="
        f"{len(output_rows)}"
    )

    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
