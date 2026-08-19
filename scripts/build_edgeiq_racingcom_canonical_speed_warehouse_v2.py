from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import csv
import json
import math
import sys


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_RUNNERS = DATA / "edgeiq_racingcom_runner_speed_fact_v1.csv"
SOURCE_SECTIONALS = DATA / "edgeiq_racingcom_runner_sectional_fact_v1.csv"
SOURCE_SPLITS = DATA / "edgeiq_racingcom_runner_split_fact_v1.csv"
SOURCE_RACES = DATA / "edgeiq_racingcom_race_speed_summary_v1.csv"
SEMANTICS_AUDIT = DATA / "edgeiq_racingcom_speed_semantics_v1_audit.json"

RUNNER_OUT = DATA / "edgeiq_racingcom_canonical_runner_speed_fact_v2.csv"
SECTIONAL_OUT = DATA / "edgeiq_racingcom_canonical_runner_sectional_fact_v2.csv"
SPLIT_OUT = DATA / "edgeiq_racingcom_canonical_runner_split_fact_v2.csv"
RACE_OUT = DATA / "edgeiq_racingcom_canonical_race_speed_fact_v2.csv"
AUDIT_OUT = DATA / "edgeiq_racingcom_canonical_speed_warehouse_v2_audit.json"


RUNNER_COLUMNS = [
    "race_key",
    "race_date",
    "track",
    "race_number",
    "runner_key",
    "runner_id",
    "saddle_number",
    "horse_name",
    "trainer_name",
    "jockey_name",
    "barrier_number",
    "finish_position",
    "finish_position_abbreviation",
    "start_position",
    "race_time_seconds",
    "time_behind_winner_seconds",
    "time_behind_winner_centiseconds",
    "beaten_margin_source",
    "distance_travelled_metres",
    "distance_variation_to_winner_metres",
    "last_600_seconds",
    "last_200_seconds",
    "sectional_count",
    "split_count",
    "early_speed_source",
    "mid_speed_source",
    "late_speed_source",
    "overall_peak_speed_source",
    "peak_speed_location_source",
    "overall_average_speed_source",
    "distance_from_rail_source",
    "comment",
    "source_provider",
    "source_page_url",
    "source_payload_file",
    "timing_source",
    "is_timing_complete",
    "is_complete_data",
    "semantic_version",
]

SECTIONAL_COLUMNS = [
    "race_key",
    "runner_key",
    "race_date",
    "track",
    "race_number",
    "runner_id",
    "saddle_number",
    "horse_name",
    "sectional_sequence",
    "distance_marker",
    "distance_to_finish_metres",
    "cumulative_time_to_finish_seconds",
    "position_at_marker",
    "average_speed_source",
    "source_page_url",
    "source_payload_file",
    "semantic_version",
]

SPLIT_COLUMNS = [
    "race_key",
    "runner_key",
    "race_date",
    "track",
    "race_number",
    "runner_id",
    "saddle_number",
    "horse_name",
    "split_sequence",
    "split_label",
    "split_start_distance_metres",
    "split_end_distance_metres",
    "split_distance_metres",
    "segment_time_seconds",
    "position_at_split_end",
    "average_speed_source",
    "source_page_url",
    "source_payload_file",
    "semantic_version",
]

RACE_COLUMNS = [
    "race_key",
    "race_date",
    "track",
    "race_number",
    "race_time_seconds",
    "runner_count",
    "timing_source",
    "is_timing_complete",
    "is_complete_data",
    "sectional_distances_json",
    "split_distances_json",
    "field_sectional_times_json",
    "fastest_early_source",
    "fastest_mid_source",
    "fastest_late_source",
    "fastest_peak_speed_source",
    "fastest_average_speed_source",
    "fastest_early_info_json",
    "fastest_mid_info_json",
    "fastest_late_info_json",
    "fastest_peak_speed_info_json",
    "fastest_average_speed_info_json",
    "fastest_sectional_times_json",
    "fastest_split_times_json",
    "source_provider",
    "source_page_url",
    "source_payload_file",
    "semantic_version",
]


SEMANTIC_VERSION = "RACINGCOM_SPEED_SEMANTICS_V1"


def log(message: str) -> None:
    print(f"[canonical_speed_warehouse_v2] {message}", flush=True)


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def clean(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def to_float(value: Any) -> float | None:
    text = clean(value)

    if not text:
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def numeric(value: float | None) -> str:
    if value is None:
        return ""

    return f"{value:.6f}".rstrip("0").rstrip(".")


def to_int_text(value: Any) -> str:
    number = to_float(value)

    if number is None:
        return ""

    if math.isclose(number, round(number), abs_tol=0.000001):
        return str(int(round(number)))

    return numeric(number)


def marker_to_metres(marker: str) -> str:
    text = clean(marker).upper()

    if text == "FINISH":
        return "0"

    if text.endswith("M"):
        return to_int_text(text[:-1])

    return ""


def parse_split_distances(label: str) -> tuple[str, str, str]:
    text = clean(label).upper()

    if "-" not in text:
        return "", "", ""

    start_text, end_text = text.split("-", 1)

    start_metres = marker_to_metres(start_text)
    end_metres = marker_to_metres(end_text)

    start_value = to_float(start_metres)
    end_value = to_float(end_metres)

    split_distance = (
        start_value - end_value
        if start_value is not None and end_value is not None
        else None
    )

    return start_metres, end_metres, numeric(split_distance)


def make_runner_key(race_key: str, runner_id: str) -> str:
    return f"{race_key}|RUNNER:{runner_id}"


def write_csv(
    path: Path,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow({
                column: row.get(column, "")
                for column in columns
            })


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    semantics = load_json(SEMANTICS_AUDIT)

    if semantics.get("status") != "PASS":
        raise RuntimeError(
            "Speed semantics audit has not passed."
        )

    source_runners = load_csv(SOURCE_RUNNERS)
    source_sectionals = load_csv(SOURCE_SECTIONALS)
    source_splits = load_csv(SOURCE_SPLITS)
    source_races = load_csv(SOURCE_RACES)

    runners: list[dict[str, Any]] = []
    sectionals: list[dict[str, Any]] = []
    splits: list[dict[str, Any]] = []
    races: list[dict[str, Any]] = []

    failures: list[str] = []
    details: dict[str, Any] = {}

    winner_time_by_race: dict[str, float] = {}

    for row in source_runners:
        if clean(row.get("finish_position")) == "1":
            winner_time = to_float(
                row.get("runner_race_time_seconds")
            )

            if winner_time is not None:
                winner_time_by_race[row["race_key"]] = winner_time

    for row in source_runners:
        race_key = row["race_key"]
        runner_id = clean(row.get("runner_id"))
        runner_key = make_runner_key(race_key, runner_id)

        runner_time = to_float(
            row.get("runner_race_time_seconds")
        )
        winner_time = winner_time_by_race.get(race_key)

        calculated_time_behind = (
            runner_time - winner_time
            if runner_time is not None and winner_time is not None
            else None
        )

        source_centiseconds = to_float(
            row.get("time_variation_to_winner_source")
        )

        runners.append({
            "race_key": race_key,
            "race_date": row.get("race_date", ""),
            "track": row.get("track", ""),
            "race_number": row.get("race_number", ""),
            "runner_key": runner_key,
            "runner_id": runner_id,
            "saddle_number": row.get("saddle_number", ""),
            "horse_name": row.get("horse_name", ""),
            "trainer_name": row.get("trainer_name", ""),
            "jockey_name": row.get("jockey_name", ""),
            "barrier_number": row.get("barrier_number", ""),
            "finish_position": row.get("finish_position", ""),
            "finish_position_abbreviation": row.get(
                "finish_position_abbreviation",
                "",
            ),
            "start_position": row.get("start_position", ""),
            "race_time_seconds": numeric(runner_time),
            "time_behind_winner_seconds": numeric(
                calculated_time_behind
            ),
            "time_behind_winner_centiseconds": numeric(
                source_centiseconds
            ),
            "beaten_margin_source": row.get(
                "beaten_margin_source",
                "",
            ),
            "distance_travelled_metres": row.get(
                "distance_run_source",
                "",
            ),
            "distance_variation_to_winner_metres": row.get(
                "distance_variation_to_winner_source",
                "",
            ),
            "last_600_seconds": row.get(
                "six_hundred_metres_time_seconds",
                "",
            ),
            "last_200_seconds": row.get(
                "two_hundred_metres_time_seconds",
                "",
            ),
            "sectional_count": row.get("sectional_count", ""),
            "split_count": row.get("split_count", ""),
            "early_speed_source": row.get(
                "early_speed_source",
                "",
            ),
            "mid_speed_source": row.get(
                "mid_speed_source",
                "",
            ),
            "late_speed_source": row.get(
                "late_speed_source",
                "",
            ),
            "overall_peak_speed_source": row.get(
                "overall_peak_speed_source",
                "",
            ),
            "peak_speed_location_source": row.get(
                "peak_speed_location",
                "",
            ),
            "overall_average_speed_source": row.get(
                "overall_average_speed_source",
                "",
            ),
            "distance_from_rail_source": row.get(
                "distance_from_rail_source",
                "",
            ),
            "comment": row.get("comment", ""),
            "source_provider": row.get(
                "source_provider",
                "RACING.COM",
            ),
            "source_page_url": row.get(
                "source_page_url",
                "",
            ),
            "source_payload_file": row.get(
                "source_payload_file",
                "",
            ),
            "timing_source": row.get("timing_source", ""),
            "is_timing_complete": row.get(
                "is_timing_complete",
                "",
            ),
            "is_complete_data": row.get(
                "is_complete_data",
                "",
            ),
            "semantic_version": SEMANTIC_VERSION,
        })

    for row in source_sectionals:
        race_key = row["race_key"]
        runner_id = clean(row.get("runner_id"))

        sectionals.append({
            "race_key": race_key,
            "runner_key": make_runner_key(race_key, runner_id),
            "race_date": row.get("race_date", ""),
            "track": row.get("track", ""),
            "race_number": row.get("race_number", ""),
            "runner_id": runner_id,
            "saddle_number": row.get("saddle_number", ""),
            "horse_name": row.get("horse_name", ""),
            "sectional_sequence": row.get(
                "sectional_sequence",
                "",
            ),
            "distance_marker": row.get(
                "distance_marker",
                "",
            ),
            "distance_to_finish_metres": marker_to_metres(
                row.get("distance_marker", "")
            ),
            "cumulative_time_to_finish_seconds": row.get(
                "cumulative_time_seconds",
                "",
            ),
            "position_at_marker": row.get("position", ""),
            "average_speed_source": row.get(
                "average_speed_source",
                "",
            ),
            "source_page_url": row.get(
                "source_page_url",
                "",
            ),
            "source_payload_file": row.get(
                "source_payload_file",
                "",
            ),
            "semantic_version": SEMANTIC_VERSION,
        })

    for row in source_splits:
        race_key = row["race_key"]
        runner_id = clean(row.get("runner_id"))
        label = row.get("split_distance", "")

        start_metres, end_metres, split_metres = (
            parse_split_distances(label)
        )

        splits.append({
            "race_key": race_key,
            "runner_key": make_runner_key(race_key, runner_id),
            "race_date": row.get("race_date", ""),
            "track": row.get("track", ""),
            "race_number": row.get("race_number", ""),
            "runner_id": runner_id,
            "saddle_number": row.get("saddle_number", ""),
            "horse_name": row.get("horse_name", ""),
            "split_sequence": row.get("split_sequence", ""),
            "split_label": label,
            "split_start_distance_metres": start_metres,
            "split_end_distance_metres": end_metres,
            "split_distance_metres": split_metres,
            "segment_time_seconds": row.get(
                "split_time_seconds",
                "",
            ),
            "position_at_split_end": row.get("position", ""),
            "average_speed_source": row.get(
                "average_speed_source",
                "",
            ),
            "source_page_url": row.get(
                "source_page_url",
                "",
            ),
            "source_payload_file": row.get(
                "source_payload_file",
                "",
            ),
            "semantic_version": SEMANTIC_VERSION,
        })

    for row in source_races:
        races.append({
            "race_key": row.get("race_key", ""),
            "race_date": row.get("race_date", ""),
            "track": row.get("track", ""),
            "race_number": row.get("race_number", ""),
            "race_time_seconds": row.get(
                "race_time_seconds",
                "",
            ),
            "runner_count": row.get("runner_count", ""),
            "timing_source": row.get("timing_source", ""),
            "is_timing_complete": row.get(
                "is_timing_complete",
                "",
            ),
            "is_complete_data": row.get(
                "is_complete_data",
                "",
            ),
            "sectional_distances_json": row.get(
                "sectional_distances_json",
                "",
            ),
            "split_distances_json": row.get(
                "split_distances_json",
                "",
            ),
            "field_sectional_times_json": row.get(
                "field_sectional_times_json",
                "",
            ),
            "fastest_early_source": row.get(
                "fastest_early_source",
                "",
            ),
            "fastest_mid_source": row.get(
                "fastest_mid_source",
                "",
            ),
            "fastest_late_source": row.get(
                "fastest_late_source",
                "",
            ),
            "fastest_peak_speed_source": row.get(
                "fastest_peak_speed_source",
                "",
            ),
            "fastest_average_speed_source": row.get(
                "fastest_average_speed_source",
                "",
            ),
            "fastest_early_info_json": row.get(
                "fastest_early_info_json",
                "",
            ),
            "fastest_mid_info_json": row.get(
                "fastest_mid_info_json",
                "",
            ),
            "fastest_late_info_json": row.get(
                "fastest_late_info_json",
                "",
            ),
            "fastest_peak_speed_info_json": row.get(
                "fastest_peak_speed_info_json",
                "",
            ),
            "fastest_average_speed_info_json": row.get(
                "fastest_average_speed_info_json",
                "",
            ),
            "fastest_sectional_times_json": row.get(
                "fastest_sectional_times_json",
                "",
            ),
            "fastest_split_times_json": row.get(
                "fastest_split_times_json",
                "",
            ),
            "source_provider": row.get(
                "source_provider",
                "RACING.COM",
            ),
            "source_page_url": row.get(
                "source_page_url",
                "",
            ),
            "source_payload_file": row.get(
                "source_payload_file",
                "",
            ),
            "semantic_version": SEMANTIC_VERSION,
        })

    runner_key_counts = Counter(
        row["runner_key"]
        for row in runners
    )

    duplicate_runner_keys = sorted(
        key
        for key, count in runner_key_counts.items()
        if count > 1
    )

    runner_keys = {
        row["runner_key"]
        for row in runners
    }

    orphan_sectionals = [
        row["runner_key"]
        for row in sectionals
        if row["runner_key"] not in runner_keys
    ]

    orphan_splits = [
        row["runner_key"]
        for row in splits
        if row["runner_key"] not in runner_keys
    ]

    race_runner_counts: dict[str, int] = defaultdict(int)

    for row in runners:
        race_runner_counts[row["race_key"]] += 1

    race_count_mismatches = []

    for race in races:
        expected = to_float(race.get("runner_count"))
        actual = race_runner_counts.get(race["race_key"], 0)

        if expected is None or int(expected) != actual:
            race_count_mismatches.append({
                "race_key": race["race_key"],
                "expected": expected,
                "actual": actual,
            })

    sectional_count_by_runner: dict[str, int] = defaultdict(int)
    split_count_by_runner: dict[str, int] = defaultdict(int)

    for row in sectionals:
        sectional_count_by_runner[row["runner_key"]] += 1

    for row in splits:
        split_count_by_runner[row["runner_key"]] += 1

    runner_child_count_mismatches = []

    for runner in runners:
        runner_key = runner["runner_key"]

        expected_sectionals = int(
            to_float(runner["sectional_count"]) or 0
        )
        expected_splits = int(
            to_float(runner["split_count"]) or 0
        )

        actual_sectionals = sectional_count_by_runner.get(
            runner_key,
            0,
        )
        actual_splits = split_count_by_runner.get(
            runner_key,
            0,
        )

        if (
            expected_sectionals != actual_sectionals
            or expected_splits != actual_splits
        ):
            runner_child_count_mismatches.append({
                "runner_key": runner_key,
                "expected_sectionals": expected_sectionals,
                "actual_sectionals": actual_sectionals,
                "expected_splits": expected_splits,
                "actual_splits": actual_splits,
            })

    required_runner_fields = [
        "race_key",
        "runner_key",
        "runner_id",
        "horse_name",
        "race_date",
        "track",
        "race_number",
    ]

    missing_required_runner_values = []

    for runner in runners:
        missing = [
            field
            for field in required_runner_fields
            if not clean(runner.get(field))
        ]

        if missing:
            missing_required_runner_values.append({
                "runner_key": runner.get("runner_key", ""),
                "missing": missing,
            })

    if not races:
        failures.append("NO_CANONICAL_RACES")

    if not runners:
        failures.append("NO_CANONICAL_RUNNERS")

    if not sectionals:
        failures.append("NO_CANONICAL_SECTIONALS")

    if not splits:
        failures.append("NO_CANONICAL_SPLITS")

    if duplicate_runner_keys:
        failures.append("DUPLICATE_RUNNER_KEYS")

    if orphan_sectionals:
        failures.append("ORPHAN_SECTIONALS")

    if orphan_splits:
        failures.append("ORPHAN_SPLITS")

    if race_count_mismatches:
        failures.append("RACE_RUNNER_COUNT_MISMATCH")

    if runner_child_count_mismatches:
        failures.append("RUNNER_CHILD_COUNT_MISMATCH")

    if missing_required_runner_values:
        failures.append("MISSING_REQUIRED_RUNNER_VALUES")

    runners.sort(
        key=lambda row: (
            row["race_date"],
            row["track"],
            int(row["race_number"] or 0),
            int(row["finish_position"] or 999),
            int(row["saddle_number"] or 999),
        )
    )

    sectionals.sort(
        key=lambda row: (
            row["race_date"],
            row["track"],
            int(row["race_number"] or 0),
            int(row["saddle_number"] or 999),
            int(row["sectional_sequence"] or 0),
        )
    )

    splits.sort(
        key=lambda row: (
            row["race_date"],
            row["track"],
            int(row["race_number"] or 0),
            int(row["saddle_number"] or 999),
            int(row["split_sequence"] or 0),
        )
    )

    races.sort(
        key=lambda row: (
            row["race_date"],
            row["track"],
            int(row["race_number"] or 0),
        )
    )

    write_csv(RUNNER_OUT, RUNNER_COLUMNS, runners)
    write_csv(SECTIONAL_OUT, SECTIONAL_COLUMNS, sectionals)
    write_csv(SPLIT_OUT, SPLIT_COLUMNS, splits)
    write_csv(RACE_OUT, RACE_COLUMNS, races)

    status = "PASS" if not failures else "FAIL"

    audit = {
        "audit_name": (
            "EDGEIQ_RACINGCOM_CANONICAL_SPEED_WAREHOUSE_V2"
        ),
        "generated_at_utc": generated_at,
        "status": status,
        "failures": failures,
        "semantic_dependency": {
            "file": SEMANTICS_AUDIT.relative_to(ROOT).as_posix(),
            "required_status": "PASS",
            "actual_status": semantics.get("status"),
            "semantic_version": SEMANTIC_VERSION,
        },
        "source_counts": {
            "races": len(source_races),
            "runners": len(source_runners),
            "sectionals": len(source_sectionals),
            "splits": len(source_splits),
        },
        "canonical_counts": {
            "races": len(races),
            "runners": len(runners),
            "sectionals": len(sectionals),
            "splits": len(splits),
        },
        "duplicate_runner_keys": duplicate_runner_keys,
        "orphan_sectionals": orphan_sectionals,
        "orphan_splits": orphan_splits,
        "race_runner_count_mismatches": race_count_mismatches,
        "runner_child_count_mismatches": (
            runner_child_count_mismatches
        ),
        "missing_required_runner_values": (
            missing_required_runner_values
        ),
        "semantic_controls": {
            "confirmed_time_fields_renamed": True,
            "confirmed_distance_fields_renamed": True,
            "source_speed_values_preserved": True,
            "unresolved_units_asserted": False,
            "ratings_calculated": False,
            "standard_times_calculated": False,
            "lengths_vs_standard_calculated": False,
            "estimated_values_created": False,
        },
        "outputs": {
            "runner_fact": RUNNER_OUT.relative_to(ROOT).as_posix(),
            "sectional_fact": (
                SECTIONAL_OUT.relative_to(ROOT).as_posix()
            ),
            "split_fact": SPLIT_OUT.relative_to(ROOT).as_posix(),
            "race_fact": RACE_OUT.relative_to(ROOT).as_posix(),
        },
    }

    AUDIT_OUT.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    log(f"canonical races: {len(races)}")
    log(f"canonical runners: {len(runners)}")
    log(f"canonical sectionals: {len(sectionals)}")
    log(f"canonical splits: {len(splits)}")
    log(f"audit status: {status}")
    log(f"wrote {RUNNER_OUT.relative_to(ROOT)}")
    log(f"wrote {SECTIONAL_OUT.relative_to(ROOT)}")
    log(f"wrote {SPLIT_OUT.relative_to(ROOT)}")
    log(f"wrote {RACE_OUT.relative_to(ROOT)}")
    log(f"wrote {AUDIT_OUT.relative_to(ROOT)}")

    if status != "PASS":
        log(f"failures: {', '.join(failures)}")
        return 1

    print(
        "EDGEIQ_RACINGCOM_CANONICAL_SPEED_"
        "WAREHOUSE_V2_AUDIT_PASS"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
