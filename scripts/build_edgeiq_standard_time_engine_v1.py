from __future__ import annotations

import csv
import hashlib
import os
import re
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OBSERVATION_PATH = DATA / "edgeiq_benchmark_observation_native_compatible_authority_v1.csv"
ACCUMULATION_PATH = DATA / "edgeiq_benchmark_accumulation_fact_v1.csv"
MEMBERSHIP_PATH = DATA / "edgeiq_benchmark_accumulation_membership_fact_v1.csv"
HISTORICAL_RESULTS_PATH = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
OUTPUT_PATH = DATA / "edgeiq_standard_time_fact_v1.csv"

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_standard_time_engine_v1.1.0"
ACCUMULATION_BUILDER_VERSION = "edgeiq_benchmark_accumulation_builder_v1.0.0"
HISTORICAL_BRIDGE_VERSION = "edgeiq_standard_time_historical_results_bridge_v1.0.0"
STANDARD_TIME_METHOD = "MEDIAN_WINNER_RACE_TIME_SECONDS"
AVAILABLE_STATUS = "AVAILABLE"
MINIMUM_REQUIRED_SAMPLE = 20

OUTPUT_FIELDS = [
    "standard_time_id",
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
    "standard_time_method",
    "standard_time_seconds",
    "sample_observation_count",
    "sample_minimum_time_seconds",
    "sample_maximum_time_seconds",
    "minimum_required_sample",
    "standard_time_status",
    "source_group_dimension_sha256",
    "source_membership_sha256",
    "standard_time_evidence_sha256",
    "source_accumulation_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def truthy(value: object) -> bool:
    return text(value).lower() in {"true", "1", "yes"}


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        fail(f"Missing canonical input: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail(f"CSV header missing: {path}")
        return list(reader.fieldnames), list(reader)


def require_fields(path: Path, fields: list[str], required: Iterable[str]) -> None:
    missing = [field for field in required if field not in fields]
    if missing:
        fail(f"{path.name} missing required fields: {missing}")


def atomic_write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        with temporary_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def decimal_value(value: object, field: str) -> Decimal:
    raw = text(value)
    if not raw:
        fail(f"Blank required decimal field: {field}")
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(f"Invalid decimal value for {field}: {raw!r}") from exc
    if not parsed.is_finite() or parsed <= 0:
        fail(f"Non-positive decimal value for {field}: {raw!r}")
    return parsed


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal(2)


def parse_distance(value: object) -> str:
    raw = text(value).upper().replace("M", "").replace(",", "")
    if not raw:
        return ""
    try:
        parsed = Decimal(raw)
    except InvalidOperation:
        return ""
    if parsed <= 0:
        return ""
    return str(int(parsed.to_integral_value()))


def parse_winning_time(value: object) -> Decimal | None:
    raw = text(value).lower().replace("s", "")
    if not raw:
        return None
    try:
        if ":" in raw:
            parts = [Decimal(part) for part in raw.split(":")]
            if len(parts) == 2:
                return (parts[0] * Decimal(60)) + parts[1]
            if len(parts) == 3:
                return (parts[0] * Decimal(3600)) + (parts[1] * Decimal(60)) + parts[2]
        parsed = Decimal(raw)
    except InvalidOperation:
        return None
    if parsed > Decimal(1000):
        parsed = parsed / Decimal(100)
    if parsed <= 0:
        return None
    return parsed


def is_winner(row: dict[str, str]) -> bool:
    won = text(row.get("won")).lower()
    if won in {"true", "1", "yes", "y"}:
        return True
    finish = text(row.get("finish_num") or row.get("finish"))
    try:
        return int(Decimal(finish).to_integral_value()) == 1
    except InvalidOperation:
        return finish.upper() in {"1ST", "FIRST"}


def is_flat_race(row: dict[str, str]) -> bool:
    raw = " ".join([text(row.get("race_class")), text(row.get("race_name"))]).upper()
    blocked = ["TRIAL", "HURDLE", "STEEPLE", "JUMP", "CHASE"]
    return not any(token in raw for token in blocked)


def row_hash(row: dict[str, str]) -> str:
    canonical = "\x1e".join(f"{key}={text(row.get(key))}" for key in sorted(row))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_from_ready_accumulations(
    accumulation_rows: list[dict[str, str]],
    membership_rows: list[dict[str, str]],
    observation_rows: list[dict[str, str]],
    built_at_utc: str,
) -> list[dict[str, object]]:
    observation_by_id = {}
    for row in observation_rows:
        observation_id = text(row["benchmark_observation_id"])
        if not observation_id:
            fail("Blank benchmark_observation_id in observation fact.")
        if observation_id in observation_by_id:
            fail(f"Duplicate observation ID: {observation_id}")
        observation_by_id[observation_id] = row

    memberships_by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_memberships: set[tuple[str, str]] = set()
    for row in membership_rows:
        group_id = text(row["benchmark_group_id"])
        observation_id = text(row["benchmark_observation_id"])
        key = (group_id, observation_id)
        if not group_id or not observation_id:
            fail("Blank key in accumulation membership fact.")
        if key in seen_memberships:
            fail(f"Duplicate accumulation membership: {key}")
        if observation_id not in observation_by_id:
            fail(f"Membership references unknown observation: {key}")
        seen_memberships.add(key)
        memberships_by_group[group_id].append(row)

    output_rows: list[dict[str, object]] = []
    for group in sorted(accumulation_rows, key=lambda row: (text(row["track_name"]).casefold(), int(text(row["official_distance_metres"])))):
        recorded_count = int(text(group["eligible_observation_count"]))
        required_sample = int(text(group["minimum_required_sample"]))
        if required_sample != MINIMUM_REQUIRED_SAMPLE:
            fail(f"{text(group['benchmark_group_id'])}: minimum sample changed from governed value.")
        ready = truthy(group["benchmark_ready"])
        if ready != (text(group["accumulation_status"]) == "READY"):
            fail(f"{text(group['benchmark_group_id'])}: readiness fields disagree.")
        if ready != (recorded_count >= required_sample):
            fail(f"{text(group['benchmark_group_id'])}: readiness threshold is incorrect.")
        if not ready:
            continue
        group_id = text(group["benchmark_group_id"])
        members = sorted(memberships_by_group.get(group_id, []), key=lambda row: int(text(row["membership_ordinal"])))
        if len(members) != recorded_count:
            fail(f"{group_id}: membership count does not equal eligible_observation_count.")
        evidence_pairs = []
        for member in members:
            observation_id = text(member["benchmark_observation_id"])
            race_time = decimal_value(observation_by_id[observation_id]["winner_race_time_seconds"], "winner_race_time_seconds")
            evidence_pairs.append((observation_id, race_time))
        output_rows.append(make_output_row(
            group_id=group_id,
            track_name=text(group["track_name"]),
            distance=text(group["official_distance_metres"]),
            race_times=[pair[1] for pair in evidence_pairs],
            evidence_pairs=evidence_pairs,
            group_dimension_hash=text(group["group_dimension_sha256"]),
            membership_hash=text(group["membership_sha256"]),
            source_builder=text(group["builder_version"]),
            built_at_utc=built_at_utc,
        ))
    return output_rows


def make_output_row(
    group_id: str,
    track_name: str,
    distance: str,
    race_times: list[Decimal],
    evidence_pairs: list[tuple[str, Decimal]],
    group_dimension_hash: str,
    membership_hash: str,
    source_builder: str,
    built_at_utc: str,
) -> dict[str, object]:
    standard_time = median(race_times)
    identity_hash = sha256_payload([CONTRACT_VERSION, group_id, STANDARD_TIME_METHOD, membership_hash])
    standard_time_id = f"STF1-{identity_hash[:24].upper()}"
    evidence_parts: list[object] = [standard_time_id]
    for observation_id, race_time in evidence_pairs:
        evidence_parts.extend([observation_id, format_decimal(race_time)])
    return {
        "standard_time_id": standard_time_id,
        "benchmark_group_id": group_id,
        "benchmark_group_basis": "TRACK_DISTANCE",
        "track_name": track_name,
        "official_distance_metres": distance,
        "course_name": "",
        "course_name_status": "NOT_AVAILABLE_IN_SOURCE",
        "surface": "",
        "surface_status": "NOT_AVAILABLE_IN_SOURCE",
        "track_condition": "",
        "track_condition_status": "NOT_AVAILABLE_IN_SOURCE",
        "standard_time_method": STANDARD_TIME_METHOD,
        "standard_time_seconds": format_decimal(standard_time),
        "sample_observation_count": len(race_times),
        "sample_minimum_time_seconds": format_decimal(min(race_times)),
        "sample_maximum_time_seconds": format_decimal(max(race_times)),
        "minimum_required_sample": MINIMUM_REQUIRED_SAMPLE,
        "standard_time_status": AVAILABLE_STATUS,
        "source_group_dimension_sha256": group_dimension_hash,
        "source_membership_sha256": membership_hash,
        "standard_time_evidence_sha256": sha256_payload(evidence_parts),
        "source_accumulation_builder_version": source_builder,
        "builder_version": BUILDER_VERSION,
        "contract_version": CONTRACT_VERSION,
        "built_at_utc": built_at_utc,
    }


def build_from_historical_results(built_at_utc: str) -> list[dict[str, object]]:
    fields, rows = read_csv(HISTORICAL_RESULTS_PATH)
    require_fields(HISTORICAL_RESULTS_PATH, fields, ["race_date", "track", "race_no", "race_name", "race_class", "distance", "winning_time", "finish_num", "won"])
    grouped: dict[tuple[str, str], list[tuple[str, Decimal]]] = defaultdict(list)
    seen_race_keys: set[str] = set()
    for row in rows:
        if not is_winner(row) or not is_flat_race(row):
            continue
        race_time = parse_winning_time(row.get("winning_time"))
        distance = parse_distance(row.get("distance"))
        track = text(row.get("track")).upper()
        race_date = text(row.get("race_date"))[:10]
        race_no = text(row.get("race_no"))
        if not race_time or not distance or not track or not race_date or not race_no:
            continue
        race_no_clean = re.sub(r"\.0$", "", race_no)
        race_key = f"{race_date}|{track}|R{race_no_clean}|{distance}"
        if race_key in seen_race_keys:
            continue
        seen_race_keys.add(race_key)
        observation_id = "HSTBOF1-" + sha256_payload([HISTORICAL_BRIDGE_VERSION, race_key, row_hash(row)])[:24].upper()
        grouped[(track, distance)].append((observation_id, race_time))

    output_rows = []
    for (track, distance), evidence_pairs in sorted(grouped.items()):
        if len(evidence_pairs) < MINIMUM_REQUIRED_SAMPLE:
            continue
        membership_hash = sha256_payload([item for pair in evidence_pairs for item in (pair[0], format_decimal(pair[1]))])
        group_dimension_hash = sha256_payload([HISTORICAL_BRIDGE_VERSION, "TRACK_DISTANCE", track, distance])
        group_id = "BGF1-" + group_dimension_hash[:24].upper()
        output_rows.append(make_output_row(
            group_id=group_id,
            track_name=track,
            distance=distance,
            race_times=[pair[1] for pair in evidence_pairs],
            evidence_pairs=evidence_pairs,
            group_dimension_hash=group_dimension_hash,
            membership_hash=membership_hash,
            source_builder=HISTORICAL_BRIDGE_VERSION,
            built_at_utc=built_at_utc,
        ))
    return output_rows


def main() -> None:
    observation_fields, observation_rows = read_csv(OBSERVATION_PATH)
    accumulation_fields, accumulation_rows = read_csv(ACCUMULATION_PATH)
    membership_fields, membership_rows = read_csv(MEMBERSHIP_PATH)

    require_fields(OBSERVATION_PATH, observation_fields, ["benchmark_observation_id", "winner_race_time_seconds"])
    require_fields(ACCUMULATION_PATH, accumulation_fields, ["benchmark_group_id", "benchmark_group_basis", "track_name", "official_distance_metres", "eligible_observation_count", "minimum_required_sample", "benchmark_ready", "accumulation_status", "group_dimension_sha256", "membership_sha256", "builder_version"])
    require_fields(MEMBERSHIP_PATH, membership_fields, ["benchmark_group_id", "benchmark_observation_id", "membership_ordinal"])

    built_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ready_accumulation_groups = [row for row in accumulation_rows if truthy(row["benchmark_ready"]) and text(row["accumulation_status"]) == "READY" and int(text(row["eligible_observation_count"])) >= MINIMUM_REQUIRED_SAMPLE]

    if ready_accumulation_groups:
        output_rows = build_from_ready_accumulations(accumulation_rows, membership_rows, observation_rows, built_at_utc)
        source_mode = "BENCHMARK_ACCUMULATION"
    else:
        output_rows = build_from_historical_results(built_at_utc)
        source_mode = "HISTORICAL_RESULTS_BRIDGE"

    atomic_write_csv(OUTPUT_PATH, OUTPUT_FIELDS, output_rows)

    print("EDGEIQ_STANDARD_TIME_ENGINE_V1_BUILD_PASS")
    print(f"source_mode={source_mode}")
    print(f"accumulation_groups={len(accumulation_rows)}")
    print(f"ready_accumulation_groups={len(ready_accumulation_groups)}")
    print(f"standard_time_rows={len(output_rows)}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
