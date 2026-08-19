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

OBSERVATION_PATH = DATA / "edgeiq_benchmark_observation_fact_v1.csv"
ELIGIBILITY_PATH = DATA / "edgeiq_benchmark_eligibility_fact_v1.csv"
MEMBERSHIP_PATH = (
    DATA / "edgeiq_benchmark_accumulation_membership_fact_v1.csv"
)
STANDARD_TIME_PATH = DATA / "edgeiq_standard_time_fact_v1.csv"
OUTPUT_PATH = (
    DATA / "edgeiq_race_time_delta_versus_standard_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_race_time_delta_versus_standard_v1.0.0"
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
    return str(value if value is not None else "").strip()


def decimal_value(value: object, field: str) -> Decimal:
    raw = text(value)
    if not raw:
        fail(f"Blank required decimal field: {field}")
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Invalid decimal value for {field}: {raw!r}"
        ) from exc
    if not parsed.is_finite() or parsed <= 0:
        fail(f"Non-positive decimal value for {field}: {raw!r}")
    return parsed


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def interpretation(delta: Decimal) -> str:
    if delta < 0:
        return "FASTER_THAN_STANDARD"
    if delta > 0:
        return "SLOWER_THAN_STANDARD"
    return "EQUAL_TO_STANDARD"


def main() -> None:
    observation_fields, observation_rows = read_csv(
        OBSERVATION_PATH
    )
    eligibility_fields, eligibility_rows = read_csv(
        ELIGIBILITY_PATH
    )
    membership_fields, membership_rows = read_csv(
        MEMBERSHIP_PATH
    )
    standard_fields, standard_rows = read_csv(
        STANDARD_TIME_PATH
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

    observation_by_id: dict[str, dict[str, str]] = {}
    for row in observation_rows:
        observation_id = text(row["benchmark_observation_id"])

        if not observation_id:
            fail("Blank benchmark_observation_id in observation fact.")

        if observation_id in observation_by_id:
            fail(f"Duplicate observation ID: {observation_id}")

        observation_by_id[observation_id] = row

    eligibility_by_id: dict[str, dict[str, str]] = {}
    for row in eligibility_rows:
        observation_id = text(row["benchmark_observation_id"])

        if not observation_id:
            fail("Blank benchmark_observation_id in eligibility fact.")

        if observation_id in eligibility_by_id:
            fail(f"Duplicate eligibility ID: {observation_id}")

        eligibility_by_id[observation_id] = row

    group_by_observation: dict[str, str] = {}
    for row in membership_rows:
        observation_id = text(row["benchmark_observation_id"])
        group_id = text(row["benchmark_group_id"])

        if not observation_id or not group_id:
            fail("Blank key in accumulation membership fact.")

        if observation_id in group_by_observation:
            fail(
                "Observation belongs to multiple benchmark groups: "
                f"{observation_id}"
            )

        group_by_observation[observation_id] = group_id

    standard_by_group: dict[str, dict[str, str]] = {}
    standard_by_track_distance: dict[tuple[str, str], dict[str, str]] = {}
    for row in standard_rows:
        group_id = text(row["benchmark_group_id"])

        if not group_id:
            fail("Blank benchmark_group_id in standard time fact.")

        if group_id in standard_by_group:
            fail(f"Duplicate standard for benchmark group: {group_id}")

        if text(row["standard_time_status"]) != "AVAILABLE":
            fail(f"Non-available row in Standard Time Fact: {group_id}")

        standard_by_group[group_id] = row
        track_distance_key = (
            text(row["track_name"]).upper(),
            text(row["official_distance_metres"]),
        )
        if track_distance_key in standard_by_track_distance:
            fail(
                "Duplicate Standard Time track-distance key: "
                f"{track_distance_key}"
            )
        standard_by_track_distance[track_distance_key] = row

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []

    for observation_id in sorted(observation_by_id):
        observation = observation_by_id[observation_id]
        eligibility = eligibility_by_id.get(observation_id)

        if eligibility is None:
            fail(
                f"Observation has no eligibility row: {observation_id}"
            )

        if (
            text(eligibility["benchmark_use_class"])
            != ELIGIBLE_CLASS
        ):
            continue

        group_id = group_by_observation.get(observation_id)

        if group_id is None:
            fail(
                f"Eligible observation has no accumulation membership: "
                f"{observation_id}"
            )

        standard = standard_by_group.get(group_id)
        if standard is None:
            standard = standard_by_track_distance.get(
                (
                    text(observation["track_name"]).upper(),
                    text(observation["official_distance_metres"]),
                )
            )

        if standard is None:
            continue

        group_id = text(standard["benchmark_group_id"])

        winner_time = decimal_value(
            observation["winner_race_time_seconds"],
            "winner_race_time_seconds",
        )
        standard_time = decimal_value(
            standard["standard_time_seconds"],
            "standard_time_seconds",
        )

        delta = winner_time - standard_time

        standard_time_id = text(standard["standard_time_id"])

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                observation_id,
                standard_time_id,
                CALCULATION_METHOD,
            ]
        )

        race_time_delta_id = (
            f"RTD1-{identity_hash[:24].upper()}"
        )

        evidence_hash = sha256_payload(
            [
                race_time_delta_id,
                format_decimal(winner_time),
                format_decimal(standard_time),
                format_decimal(delta),
            ]
        )

        source_observation_hash = sha256_payload(
            [
                text(observation["race_source_row_sha256"]),
                text(observation["winner_source_row_sha256"]),
            ]
        )

        output_rows.append(
            {
                "race_time_delta_id": race_time_delta_id,
                "benchmark_observation_id": observation_id,
                "benchmark_group_id": group_id,
                "standard_time_id": standard_time_id,
                "race_key": text(observation["race_key"]),
                "race_date": text(observation["race_date"]),
                "track_name": text(observation["track_name"]),
                "official_distance_metres": text(
                    observation["official_distance_metres"]
                ),
                "winner_horse_name": text(
                    observation["winner_horse_name"]
                ),
                "winner_race_time_seconds": format_decimal(
                    winner_time
                ),
                "standard_time_seconds": format_decimal(
                    standard_time
                ),
                "time_delta_seconds": format_decimal(delta),
                "time_delta_interpretation": interpretation(delta),
                "calculation_method": CALCULATION_METHOD,
                "source_observation_sha256": source_observation_hash,
                "source_standard_time_evidence_sha256": text(
                    standard["standard_time_evidence_sha256"]
                ),
                "race_time_delta_evidence_sha256": evidence_hash,
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

    print("EDGEIQ_RACE_TIME_DELTA_VERSUS_STANDARD_V1_BUILD_PASS")
    print(f"observation_rows={len(observation_rows)}")
    print(f"standard_time_rows={len(standard_rows)}")
    print(f"race_time_delta_rows={len(output_rows)}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
