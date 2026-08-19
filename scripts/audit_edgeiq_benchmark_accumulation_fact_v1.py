from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OBSERVATION_PATH = DATA / "edgeiq_benchmark_observation_fact_v1.csv"
ELIGIBILITY_PATH = DATA / "edgeiq_benchmark_eligibility_fact_v1.csv"
GROUP_PATH = DATA / "edgeiq_benchmark_accumulation_fact_v1.csv"
MEMBERSHIP_PATH = (
    DATA / "edgeiq_benchmark_accumulation_membership_fact_v1.csv"
)
AUDIT_PATH = DATA / "edgeiq_benchmark_accumulation_fact_v1_audit.json"

GROUP_CONTRACT_PATH = (
    ROOT
    / "contracts/performance-intelligence"
    / "edgeiq_benchmark_accumulation_fact_v1_contract.json"
)
MEMBERSHIP_CONTRACT_PATH = (
    ROOT
    / "contracts/performance-intelligence"
    / "edgeiq_benchmark_accumulation_membership_fact_v1_contract.json"
)

GROUP_BASIS = "TRACK_DISTANCE"
MINIMUM_REQUIRED_SAMPLE = 20
CONTRACT_VERSION = "1.0.0"
ELIGIBLE_CLASS = "STANDARD_TIME_ELIGIBLE"
UNAVAILABLE_STATUS = "NOT_AVAILABLE_IN_SOURCE"

FORBIDDEN_TOKENS = (
    "average",
    "mean",
    "median",
    "percentile",
    "variance",
    "regression",
    "weight",
    "interpolation",
    "smoothing",
    "benchmark_time",
    "standard_time",
    "track_variant",
    "lengths_vs_standard",
    "performance_rating",
    "speed_rating",
    "epi",
)


def canonical_text(value: object) -> str:
    return str(value if value is not None else "").strip()


def canonical_distance(value: object) -> str:
    text = canonical_text(value)
    number = float(text)
    if not number.is_integer() or number <= 0:
        raise ValueError(text)
    return str(int(number))


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(canonical_text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"Missing CSV header: {path}")
        return list(reader.fieldnames), list(reader)


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def main() -> None:
    checks: dict[str, dict[str, object]] = {}

    def check(name: str, passed: bool, detail: object) -> None:
        checks[name] = {
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }

    required_paths = [
        OBSERVATION_PATH,
        ELIGIBILITY_PATH,
        GROUP_PATH,
        MEMBERSHIP_PATH,
        GROUP_CONTRACT_PATH,
        MEMBERSHIP_CONTRACT_PATH,
    ]
    missing_paths = [
        str(path.relative_to(ROOT))
        for path in required_paths
        if not path.exists()
    ]
    check("required_files_exist", not missing_paths, missing_paths)

    if missing_paths:
        payload = {
            "audit_name": "edgeiq_benchmark_accumulation_fact_v1",
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }
        atomic_write_json(AUDIT_PATH, payload)
        raise SystemExit("AUDIT_FAIL: required files missing")

    observation_fields, observation_rows = read_csv(OBSERVATION_PATH)
    eligibility_fields, eligibility_rows = read_csv(ELIGIBILITY_PATH)
    group_fields, group_rows = read_csv(GROUP_PATH)
    membership_fields, membership_rows = read_csv(MEMBERSHIP_PATH)

    group_contract = json.loads(
        GROUP_CONTRACT_PATH.read_text(encoding="utf-8")
    )
    membership_contract = json.loads(
        MEMBERSHIP_CONTRACT_PATH.read_text(encoding="utf-8")
    )

    required_group_fields = group_contract["required_fields"]
    required_membership_fields = membership_contract["required_fields"]

    check(
        "group_contract_fields",
        group_fields == required_group_fields,
        {
            "actual": group_fields,
            "expected": required_group_fields,
        },
    )
    check(
        "membership_contract_fields",
        membership_fields == required_membership_fields,
        {
            "actual": membership_fields,
            "expected": required_membership_fields,
        },
    )

    observation_by_id = {
        canonical_text(row["benchmark_observation_id"]): row
        for row in observation_rows
    }
    eligibility_by_id = {
        canonical_text(row["benchmark_observation_id"]): row
        for row in eligibility_rows
    }

    eligible_ids = sorted(
        observation_id
        for observation_id, row in eligibility_by_id.items()
        if canonical_text(row["benchmark_use_class"])
        == ELIGIBLE_CLASS
    )

    membership_ids = [
        canonical_text(row["benchmark_observation_id"])
        for row in membership_rows
    ]

    membership_counts = Counter(membership_ids)
    duplicate_memberships = sorted(
        observation_id
        for observation_id, count in membership_counts.items()
        if count != 1
    )

    check(
        "eligible_population_accounted_for",
        set(membership_ids) == set(eligible_ids),
        {
            "eligible_count": len(eligible_ids),
            "membership_count": len(membership_ids),
            "missing": sorted(set(eligible_ids) - set(membership_ids)),
            "unexpected": sorted(
                set(membership_ids) - set(eligible_ids)
            ),
        },
    )
    check(
        "membership_exactly_once",
        not duplicate_memberships
        and len(membership_ids) == len(set(membership_ids)),
        duplicate_memberships,
    )

    noneligible_members = sorted(
        observation_id
        for observation_id in membership_ids
        if canonical_text(
            eligibility_by_id[observation_id]["benchmark_use_class"]
        )
        != ELIGIBLE_CLASS
    )
    check(
        "no_ineligible_memberships",
        not noneligible_members,
        noneligible_members,
    )

    group_ids = [
        canonical_text(row["benchmark_group_id"])
        for row in group_rows
    ]
    duplicate_group_ids = sorted(
        value
        for value, count in Counter(group_ids).items()
        if count != 1
    )
    group_dimension_keys = [
        (
            canonical_text(row["track_name"]),
            canonical_distance(row["official_distance_metres"]),
        )
        for row in group_rows
    ]
    duplicate_dimension_keys = sorted(
        key
        for key, count in Counter(group_dimension_keys).items()
        if count != 1
    )

    check(
        "unique_benchmark_group_ids",
        not duplicate_group_ids,
        duplicate_group_ids,
    )
    check(
        "unique_group_dimensions",
        not duplicate_dimension_keys,
        duplicate_dimension_keys,
    )

    memberships_by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in membership_rows:
        memberships_by_group[
            canonical_text(row["benchmark_group_id"])
        ].append(row)

    deterministic_errors: list[str] = []
    readiness_errors: list[str] = []
    dimension_errors: list[str] = []
    membership_integrity_errors: list[str] = []

    for group in group_rows:
        group_id = canonical_text(group["benchmark_group_id"])
        track_name = canonical_text(group["track_name"])
        distance = canonical_distance(
            group["official_distance_metres"]
        )

        expected_dimension_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                GROUP_BASIS,
                track_name,
                distance,
            ]
        )
        expected_group_id = (
            f"BGF1-{expected_dimension_hash[:24].upper()}"
        )

        if group["group_dimension_sha256"] != expected_dimension_hash:
            deterministic_errors.append(
                f"{group_id}: group_dimension_sha256"
            )
        if group_id != expected_group_id:
            deterministic_errors.append(
                f"{group_id}: benchmark_group_id"
            )

        members = sorted(
            memberships_by_group.get(group_id, []),
            key=lambda row: int(row["membership_ordinal"]),
        )
        member_ids = [
            canonical_text(row["benchmark_observation_id"])
            for row in members
        ]
        expected_membership_hash = sha256_payload(
            [group_id, *member_ids]
        )

        if group["membership_sha256"] != expected_membership_hash:
            deterministic_errors.append(
                f"{group_id}: membership_sha256"
            )

        expected_ordinals = list(range(1, len(members) + 1))
        actual_ordinals = [
            int(row["membership_ordinal"]) for row in members
        ]
        if actual_ordinals != expected_ordinals:
            membership_integrity_errors.append(
                f"{group_id}: membership ordinals"
            )

        if member_ids != sorted(member_ids):
            membership_integrity_errors.append(
                f"{group_id}: membership ordering"
            )

        for member in members:
            observation_id = canonical_text(
                member["benchmark_observation_id"]
            )
            expected_member_hash = sha256_payload(
                [group_id, observation_id]
            )
            if member["membership_sha256"] != expected_member_hash:
                deterministic_errors.append(
                    f"{group_id}/{observation_id}: membership_sha256"
                )

            observation = observation_by_id[observation_id]
            expected_track = canonical_text(observation["track_name"])
            expected_distance = canonical_distance(
                observation["official_distance_metres"]
            )
            if (
                canonical_text(member["track_name"]) != expected_track
                or canonical_distance(
                    member["official_distance_metres"]
                )
                != expected_distance
                or expected_track != track_name
                or expected_distance != distance
            ):
                membership_integrity_errors.append(
                    f"{group_id}/{observation_id}: dimension mismatch"
                )

        count = len(members)
        recorded_count = int(group["eligible_observation_count"])
        ready = count >= MINIMUM_REQUIRED_SAMPLE
        expected_ready = str(ready).lower()
        expected_status = (
            "READY" if ready else "INSUFFICIENT_SAMPLE"
        )

        if (
            recorded_count != count
            or int(group["minimum_required_sample"])
            != MINIMUM_REQUIRED_SAMPLE
            or canonical_text(group["benchmark_ready"])
            != expected_ready
            or canonical_text(group["accumulation_status"])
            != expected_status
        ):
            readiness_errors.append(group_id)

        if (
            canonical_text(group["benchmark_group_basis"])
            != GROUP_BASIS
            or canonical_text(group["course_name"])
            or canonical_text(group["surface"])
            or canonical_text(group["track_condition"])
            or canonical_text(group["course_name_status"])
            != UNAVAILABLE_STATUS
            or canonical_text(group["surface_status"])
            != UNAVAILABLE_STATUS
            or canonical_text(group["track_condition_status"])
            != UNAVAILABLE_STATUS
        ):
            dimension_errors.append(group_id)

    unknown_membership_groups = sorted(
        set(memberships_by_group) - set(group_ids)
    )

    check(
        "deterministic_identifiers_and_hashes",
        not deterministic_errors,
        deterministic_errors,
    )
    check(
        "readiness_governance",
        not readiness_errors,
        readiness_errors,
    )
    check(
        "unavailable_dimension_governance",
        not dimension_errors,
        dimension_errors,
    )
    check(
        "membership_integrity",
        not membership_integrity_errors
        and not unknown_membership_groups,
        {
            "errors": membership_integrity_errors,
            "unknown_groups": unknown_membership_groups,
        },
    )

    lower_headers = [
        field.casefold()
        for field in group_fields + membership_fields
    ]
    statistical_fields = sorted(
        {
            field
            for field in lower_headers
            if any(token in field for token in FORBIDDEN_TOKENS)
        }
    )
    check(
        "no_statistical_fields",
        not statistical_fields,
        statistical_fields,
    )

    source_group_keys = {
        (
            canonical_text(observation_by_id[observation_id]["track_name"]),
            canonical_distance(
                observation_by_id[observation_id][
                    "official_distance_metres"
                ]
            ),
        )
        for observation_id in eligible_ids
    }
    output_group_keys = set(group_dimension_keys)

    check(
        "source_groups_equal_output_groups",
        source_group_keys == output_group_keys,
        {
            "source_group_count": len(source_group_keys),
            "output_group_count": len(output_group_keys),
            "missing": sorted(source_group_keys - output_group_keys),
            "unexpected": sorted(output_group_keys - source_group_keys),
        },
    )

    ready_count = sum(
        1
        for row in group_rows
        if canonical_text(row["benchmark_ready"]) == "true"
    )
    insufficient_count = sum(
        1
        for row in group_rows
        if canonical_text(row["accumulation_status"])
        == "INSUFFICIENT_SAMPLE"
    )

    check(
        "current_expected_population",
        len(eligible_ids) == 24
        and len(group_rows) == 12
        and len(membership_rows) == 24
        and ready_count == 0
        and insufficient_count == 12,
        {
            "eligible_observations": len(eligible_ids),
            "benchmark_groups": len(group_rows),
            "membership_rows": len(membership_rows),
            "ready_groups": ready_count,
            "insufficient_sample_groups": insufficient_count,
        },
    )

    failed_checks = [
        name
        for name, result in checks.items()
        if result["status"] != "PASS"
    ]
    overall_status = "PASS" if not failed_checks else "FAIL"

    audit_payload = {
        "audit_name": "edgeiq_benchmark_accumulation_fact_v1",
        "audit_version": "1.0.0",
        "audited_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "status": overall_status,
        "counts": {
            "observation_rows": len(observation_rows),
            "eligibility_rows": len(eligibility_rows),
            "standard_time_eligible_rows": len(eligible_ids),
            "benchmark_group_rows": len(group_rows),
            "membership_rows": len(membership_rows),
            "ready_groups": ready_count,
            "insufficient_sample_groups": insufficient_count,
        },
        "failed_checks": failed_checks,
        "checks": checks,
    }

    atomic_write_json(AUDIT_PATH, audit_payload)

    if overall_status != "PASS":
        print(json.dumps(audit_payload, indent=2))
        raise SystemExit(
            "EDGEIQ_BENCHMARK_ACCUMULATION_FACT_V1_AUDIT_FAIL"
        )

    print("EDGEIQ_BENCHMARK_ACCUMULATION_FACT_V1_AUDIT_PASS")
    for key, value in audit_payload["counts"].items():
        print(f"{key}={value}")
    print(f"audit_output={AUDIT_PATH}")


if __name__ == "__main__":
    main()
