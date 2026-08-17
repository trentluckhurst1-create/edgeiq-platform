from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OBSERVATION_PATH = DATA / "edgeiq_benchmark_observation_native_compatible_authority_v1.csv"
ELIGIBILITY_PATH = DATA / "edgeiq_benchmark_eligibility_fact_v1.csv"

GROUP_OUTPUT_PATH = DATA / "edgeiq_benchmark_accumulation_fact_v1.csv"
MEMBERSHIP_OUTPUT_PATH = (
    DATA / "edgeiq_benchmark_accumulation_membership_fact_v1.csv"
)

GROUP_BASIS = "TRACK_DISTANCE"
MINIMUM_REQUIRED_SAMPLE = 20
BUILDER_VERSION = "edgeiq_benchmark_accumulation_builder_v1.0.0"
CONTRACT_VERSION = "1.0.0"
ELIGIBLE_CLASS = "STANDARD_TIME_ELIGIBLE"
UNAVAILABLE_STATUS = "NOT_AVAILABLE_IN_SOURCE"

GROUP_FIELDS = [
    "benchmark_group_id",
    "benchmark_group_basis",
    "track_name",
    "official_distance_metres",
    "course_name",
    "course_name_status",
    "surface",
    "surface_status",
    "track_condition",
    "track_condition_status",
    "eligible_observation_count",
    "minimum_required_sample",
    "benchmark_ready",
    "accumulation_status",
    "group_dimension_sha256",
    "membership_sha256",
    "source_eligibility_rule_version",
    "source_observation_canonical_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

MEMBERSHIP_FIELDS = [
    "benchmark_group_id",
    "benchmark_observation_id",
    "membership_ordinal",
    "track_name",
    "official_distance_metres",
    "membership_sha256",
    "source_benchmark_use_class",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def canonical_text(value: object) -> str:
    return str(value if value is not None else "").strip()


def canonical_distance(value: object) -> str:
    text = canonical_text(value)
    if not text:
        fail("Eligible observation has blank official_distance_metres.")
    try:
        number = float(text)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid official_distance_metres: {text!r}"
        ) from exc
    if not number.is_integer() or number <= 0:
        fail(f"Invalid official_distance_metres: {text!r}")
    return str(int(number))


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(canonical_text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        fail(f"Required input missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail(f"CSV header missing: {path}")
        return list(reader.fieldnames), list(reader)


def require_fields(
    path: Path,
    fieldnames: list[str],
    required: Iterable[str],
) -> None:
    missing = [field for field in required if field not in fieldnames]
    if missing:
        fail(f"{path.name} missing required fields: {missing}")


def atomic_write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with temp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
                extrasaction="raise",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def main() -> None:
    observation_fields, observation_rows = read_csv(OBSERVATION_PATH)
    eligibility_fields, eligibility_rows = read_csv(ELIGIBILITY_PATH)

    require_fields(
        OBSERVATION_PATH,
        observation_fields,
        [
            "benchmark_observation_id",
            "track_name",
            "official_distance_metres",
            "course_name",
            "surface",
            "track_condition",
            "source_canonical_version",
        ],
    )
    require_fields(
        ELIGIBILITY_PATH,
        eligibility_fields,
        [
            "benchmark_observation_id",
            "benchmark_use_class",
            "standard_time_eligible",
            "eligibility_rule_version",
        ],
    )

    observation_by_id: dict[str, dict[str, str]] = {}
    for row in observation_rows:
        observation_id = canonical_text(row["benchmark_observation_id"])
        if not observation_id:
            fail("Blank benchmark_observation_id in observation fact.")
        if observation_id in observation_by_id:
            fail(f"Duplicate observation ID: {observation_id}")
        observation_by_id[observation_id] = row

    eligibility_by_id: dict[str, dict[str, str]] = {}
    for row in eligibility_rows:
        observation_id = canonical_text(row["benchmark_observation_id"])
        if not observation_id:
            fail("Blank benchmark_observation_id in eligibility fact.")
        if observation_id in eligibility_by_id:
            fail(f"Duplicate eligibility membership: {observation_id}")
        eligibility_by_id[observation_id] = row

    if set(observation_by_id) != set(eligibility_by_id):
        fail("Observation and eligibility benchmark_observation_id sets differ.")

    eligible_joined: list[dict[str, str]] = []

    for observation_id in sorted(eligibility_by_id):
        eligibility = eligibility_by_id[observation_id]
        use_class = canonical_text(eligibility["benchmark_use_class"])
        flag = canonical_text(
            eligibility["standard_time_eligible"]
        ).lower()

        is_eligible = use_class == ELIGIBLE_CLASS

        if is_eligible and flag not in {"true", "1", "yes"}:
            fail(
                f"{observation_id}: benchmark_use_class and "
                "standard_time_eligible disagree."
            )

        if not is_eligible:
            continue

        observation = observation_by_id[observation_id]

        track_name = canonical_text(observation["track_name"])
        if not track_name:
            fail(f"{observation_id}: eligible observation has blank track_name.")

        distance = canonical_distance(
            observation["official_distance_metres"]
        )

        eligibility_track = canonical_text(
            eligibility.get("track_name", "")
        )
        eligibility_distance = canonical_text(
            eligibility.get("official_distance_metres", "")
        )

        if eligibility_track and eligibility_track != track_name:
            fail(f"{observation_id}: track_name differs across facts.")

        if (
            eligibility_distance
            and canonical_distance(eligibility_distance) != distance
        ):
            fail(
                f"{observation_id}: official_distance_metres differs "
                "across facts."
            )

        eligible_joined.append(
            {
                "benchmark_observation_id": observation_id,
                "track_name": track_name,
                "official_distance_metres": distance,
                "eligibility_rule_version": canonical_text(
                    eligibility["eligibility_rule_version"]
                ),
                "source_canonical_version": canonical_text(
                    observation["source_canonical_version"]
                ),
            }
        )

    if not eligible_joined:
        fail("No STANDARD_TIME_ELIGIBLE observations found.")

    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in eligible_joined:
        groups[
            (
                row["track_name"],
                row["official_distance_metres"],
            )
        ].append(row)

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    group_rows: list[dict[str, object]] = []
    membership_rows: list[dict[str, object]] = []

    ordered_groups = sorted(
        groups.items(),
        key=lambda item: (
            item[0][0].casefold(),
            int(item[0][1]),
        ),
    )

    for (track_name, distance), members in ordered_groups:
        dimension_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                GROUP_BASIS,
                track_name,
                distance,
            ]
        )
        benchmark_group_id = f"BGF1-{dimension_hash[:24].upper()}"

        ordered_members = sorted(
            members,
            key=lambda row: row["benchmark_observation_id"],
        )
        observation_ids = [
            member["benchmark_observation_id"]
            for member in ordered_members
        ]
        membership_set_hash = sha256_payload(
            [benchmark_group_id, *observation_ids]
        )

        eligibility_versions = sorted(
            {
                member["eligibility_rule_version"]
                for member in ordered_members
            }
        )
        observation_versions = sorted(
            {
                member["source_canonical_version"]
                for member in ordered_members
            }
        )

        if len(eligibility_versions) != 1:
            fail(
                f"{benchmark_group_id}: mixed eligibility rule versions."
            )
        if len(observation_versions) != 1:
            fail(
                f"{benchmark_group_id}: mixed observation canonical versions."
            )

        count = len(ordered_members)
        ready = count >= MINIMUM_REQUIRED_SAMPLE
        status = "READY" if ready else "INSUFFICIENT_SAMPLE"

        group_rows.append(
            {
                "benchmark_group_id": benchmark_group_id,
                "benchmark_group_basis": GROUP_BASIS,
                "track_name": track_name,
                "official_distance_metres": distance,
                "course_name": canonical_text(
                    observation_by_id[
                        ordered_members[0]["benchmark_observation_id"]
                    ]["course_name"]
                ),
                "course_name_status": (
                    "AVAILABLE"
                    if canonical_text(
                        observation_by_id[
                            ordered_members[0]["benchmark_observation_id"]
                        ]["course_name"]
                    )
                    else UNAVAILABLE_STATUS
                ),
                "surface": canonical_text(
                    observation_by_id[
                        ordered_members[0]["benchmark_observation_id"]
                    ]["surface"]
                ),
                "surface_status": (
                    "AVAILABLE"
                    if canonical_text(
                        observation_by_id[
                            ordered_members[0]["benchmark_observation_id"]
                        ]["surface"]
                    )
                    else UNAVAILABLE_STATUS
                ),
                "track_condition": canonical_text(
                    observation_by_id[
                        ordered_members[0]["benchmark_observation_id"]
                    ]["track_condition"]
                ),
                "track_condition_status": (
                    "AVAILABLE"
                    if canonical_text(
                        observation_by_id[
                            ordered_members[0]["benchmark_observation_id"]
                        ]["track_condition"]
                    )
                    else UNAVAILABLE_STATUS
                ),
                "eligible_observation_count": count,
                "minimum_required_sample": MINIMUM_REQUIRED_SAMPLE,
                "benchmark_ready": str(ready).lower(),
                "accumulation_status": status,
                "group_dimension_sha256": dimension_hash,
                "membership_sha256": membership_set_hash,
                "source_eligibility_rule_version": eligibility_versions[0],
                "source_observation_canonical_version": (
                    observation_versions[0]
                ),
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

        for ordinal, member in enumerate(ordered_members, start=1):
            observation_id = member["benchmark_observation_id"]
            membership_hash = sha256_payload(
                [benchmark_group_id, observation_id]
            )
            membership_rows.append(
                {
                    "benchmark_group_id": benchmark_group_id,
                    "benchmark_observation_id": observation_id,
                    "membership_ordinal": ordinal,
                    "track_name": track_name,
                    "official_distance_metres": distance,
                    "membership_sha256": membership_hash,
                    "source_benchmark_use_class": ELIGIBLE_CLASS,
                    "builder_version": BUILDER_VERSION,
                    "contract_version": CONTRACT_VERSION,
                    "built_at_utc": built_at_utc,
                }
            )

    atomic_write_csv(GROUP_OUTPUT_PATH, GROUP_FIELDS, group_rows)
    atomic_write_csv(
        MEMBERSHIP_OUTPUT_PATH,
        MEMBERSHIP_FIELDS,
        membership_rows,
    )

    ready_count = sum(
        1 for row in group_rows if row["benchmark_ready"] == "true"
    )

    print("EDGEIQ_BENCHMARK_ACCUMULATION_FACT_V1_BUILD_PASS")
    print(f"eligible_observations={len(eligible_joined)}")
    print(f"benchmark_groups={len(group_rows)}")
    print(f"membership_rows={len(membership_rows)}")
    print(f"ready_groups={ready_count}")
    print(
        "insufficient_sample_groups="
        f"{len(group_rows) - ready_count}"
    )
    print(f"group_output={GROUP_OUTPUT_PATH}")
    print(f"membership_output={MEMBERSHIP_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
