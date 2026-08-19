from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RACE_PATH = DATA / "edgeiq_racingcom_canonical_race_speed_fact_v2_1.csv"
RUNNER_PATH = DATA / "edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv"
SECTIONAL_PATH = DATA / "edgeiq_racingcom_canonical_runner_sectional_fact_v2_1.csv"
SPLIT_PATH = DATA / "edgeiq_racingcom_canonical_runner_split_fact_v2_1.csv"
CANONICAL_AUDIT_PATH = (
    DATA / "edgeiq_racingcom_canonical_speed_warehouse_v2_1_audit.json"
)

OUTPUT_PATH = DATA / "edgeiq_benchmark_observation_fact_v1.csv"
AUDIT_PATH = DATA / "edgeiq_benchmark_observation_fact_v1_audit.json"

SOURCE_PROVIDER = "RACING.COM"
SOURCE_CANONICAL_VERSION = "RACINGCOM_CANONICAL_SPEED_WAREHOUSE_V2_1"
SOURCE_SEMANTIC_VERSION = "RACINGCOM_SPEED_SEMANTICS_V1_1"

PASS_MARKER = "EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1_AUDIT_PASS"

OUTPUT_FIELDS = [
    "benchmark_observation_id",
    "race_key",
    "race_date",
    "track_name",
    "course_name",
    "race_number",
    "official_distance_metres",
    "surface",
    "track_condition",
    "rail_position",
    "race_class",
    "runner_count",
    "race_split_coverage_type",
    "full_race_coverage_runner_count",
    "partial_timing_window_runner_count",
    "unresolved_coverage_runner_count",
    "winner_runner_key",
    "winner_horse_name",
    "winner_race_time_seconds",
    "winner_last_600_seconds",
    "winner_last_400_seconds",
    "winner_last_200_seconds",
    "winner_split_window_start_marker_metres",
    "winner_split_window_distance_metres",
    "winner_split_window_seconds",
    "winner_opening_untimed_distance_metres",
    "source_provider",
    "source_canonical_version",
    "source_semantic_version",
    "observation_status",
    "evidence_complete",
    "race_source_row_sha256",
    "winner_source_row_sha256",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        fail(f"Required input does not exist: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
        fields = list(reader.fieldnames or [])

    if not fields:
        fail(f"CSV has no header: {path}")

    return rows, fields


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def first_value(row: dict[str, str], aliases: Iterable[str]) -> str:
    lowered = {key.lower(): key for key in row}
    for alias in aliases:
        actual = lowered.get(alias.lower())
        if actual is not None:
            value = clean(row.get(actual))
            if value != "":
                return value
    return ""


def parse_int(value: Any) -> int | None:
    text = clean(value)
    if text == "":
        return None

    try:
        return int(float(text))
    except ValueError:
        return None


def canonical_decimal(value: Any) -> str:
    text = clean(value)
    if text == "":
        return ""

    try:
        number = float(text)
    except ValueError:
        return text

    if number.is_integer():
        return str(int(number))

    return format(number, ".10f").rstrip("0").rstrip(".")


def canonical_json(row: dict[str, str]) -> str:
    normalized = {key: clean(row.get(key)) for key in sorted(row)}
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def row_sha256(row: dict[str, str]) -> str:
    return hashlib.sha256(canonical_json(row).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def governed_official_distance(
    winner: dict[str, str] | None,
) -> str:
    """
    Resolve official race distance only from governed full-race evidence.

    For FULL_RACE rows, the winner's reconciled split window begins at the
    race distance and finishes at zero. Partial timing windows must not be
    represented as complete official race distances.
    """
    if winner is None:
        return ""

    coverage_type = first_value(
        winner,
        ("split_coverage_type",),
    ).upper()

    full_race_flag = first_value(
        winner,
        ("full_race_split_coverage",),
    ).lower()

    start_marker = parse_int(
        first_value(
            winner,
            ("split_window_start_marker_metres",),
        )
    )

    finish_marker = parse_int(
        first_value(
            winner,
            ("split_window_finish_marker_metres",),
        )
    )

    window_distance = parse_int(
        first_value(
            winner,
            ("split_window_distance_metres",),
        )
    )

    if coverage_type != "FULL_RACE":
        return ""

    if full_race_flag not in {"true", "1", "yes"}:
        return ""

    if finish_marker != 0:
        return ""

    if window_distance is None or window_distance <= 0:
        return ""

    if (
        start_marker is not None
        and start_marker != window_distance
    ):
        return ""

    return canonical_decimal(window_distance)


def deterministic_id(race_key: str) -> str:
    digest = hashlib.sha256(
        f"EDGEIQ|BENCHMARK_OBSERVATION|V1|{race_key}".encode("utf-8")
    ).hexdigest()
    return f"BOF1-{digest[:24].upper()}"


def parse_race_key(race_key: str) -> tuple[str, str, str]:
    parts = [part.strip() for part in race_key.split("|")]
    race_date = parts[0] if len(parts) >= 1 else ""
    track_name = parts[1] if len(parts) >= 2 else ""
    race_number = parts[2] if len(parts) >= 3 else ""
    race_number = re.sub(r"^[Rr]0*", "", race_number)
    return race_date, track_name, race_number


def canonical_audit_passes(payload: Any) -> bool:
    """
    Accept the governed V2.1 audit across supported audit schemas.

    PASS may be represented by:
    - status / audit_status / overall_status / result = PASS
    - pass / passed / audit_pass = true
    - a PASS marker stored anywhere in the JSON
    - zero failed checks combined with positive governed checks

    Merely containing a field name with the word FAIL must not cause failure.
    """

    pass_markers = {
        "EDGEIQ_RACINGCOM_CANONICAL_SPEED_WAREHOUSE_V2_1_AUDIT_PASS",
        "RACINGCOM_CANONICAL_SPEED_WAREHOUSE_V2_1_AUDIT_PASS",
        "CANONICAL_SPEED_WAREHOUSE_V2_1_AUDIT_PASS",
    }

    status_keys = {
        "status",
        "audit_status",
        "overall_status",
        "result",
    }

    boolean_pass_keys = {
        "pass",
        "passed",
        "audit_pass",
        "is_pass",
        "is_valid",
    }

    failed_count_keys = {
        "failed_checks",
        "failure_count",
        "failed_check_count",
        "errors",
        "error_count",
    }

    explicit_pass = False
    explicit_fail = False
    pass_marker_found = False
    failed_checks_present = False

    def walk(value: Any, parent_key: str = "") -> None:
        nonlocal explicit_pass
        nonlocal explicit_fail
        nonlocal pass_marker_found
        nonlocal failed_checks_present

        if isinstance(value, dict):
            for raw_key, child in value.items():
                key = str(raw_key).strip().lower()

                if key in status_keys:
                    status = clean(child).upper()
                    if status in {
                        "PASS",
                        "PASSED",
                        "SUCCESS",
                        "VALID",
                        "COMPLETE",
                    }:
                        explicit_pass = True
                    elif status in {
                        "FAIL",
                        "FAILED",
                        "ERROR",
                        "INVALID",
                    }:
                        explicit_fail = True

                elif key in boolean_pass_keys:
                    if child is True:
                        explicit_pass = True
                    elif child is False:
                        explicit_fail = True
                    else:
                        status = clean(child).upper()
                        if status in {
                            "TRUE",
                            "PASS",
                            "PASSED",
                            "YES",
                            "1",
                        }:
                            explicit_pass = True
                        elif status in {
                            "FALSE",
                            "FAIL",
                            "FAILED",
                            "NO",
                            "0",
                        }:
                            explicit_fail = True

                elif key in failed_count_keys:
                    if isinstance(child, list):
                        if len(child) > 0:
                            failed_checks_present = True
                    elif isinstance(child, dict):
                        if len(child) > 0:
                            failed_checks_present = True
                    elif isinstance(child, (int, float)):
                        if child != 0:
                            failed_checks_present = True
                    else:
                        text_value = clean(child)
                        if text_value not in {"", "0", "NONE", "[]", "{}"}:
                            failed_checks_present = True

                walk(child, key)

        elif isinstance(value, list):
            for child in value:
                walk(child, parent_key)

        elif isinstance(value, str):
            upper_value = value.strip().upper()

            if upper_value in pass_markers:
                pass_marker_found = True

            if any(marker in upper_value for marker in pass_markers):
                pass_marker_found = True

    walk(payload)

    if explicit_fail or failed_checks_present:
        return False

    if explicit_pass or pass_marker_found:
        return True

    return False


def runner_race_key(row: dict[str, str]) -> str:
    return first_value(row, ["race_key"])


def runner_key(row: dict[str, str]) -> str:
    return first_value(
        row,
        [
            "runner_key",
            "canonical_runner_key",
            "race_runner_key",
            "runner_id",
        ],
    )


def horse_name(row: dict[str, str]) -> str:
    return first_value(
        row,
        [
            "horse_name",
            "runner_name",
            "horse",
            "name",
        ],
    )


def finish_position(row: dict[str, str]) -> int | None:
    value = first_value(
        row,
        [
            "finish_position",
            "finishing_position",
            "position",
            "place",
            "placing",
            "result_position",
        ],
    )

    if not value:
        return None

    match = re.match(r"^\s*(\d+)", value)
    return int(match.group(1)) if match else None


def explicit_winner_flag(row: dict[str, str]) -> bool:
    value = first_value(
        row,
        [
            "is_winner",
            "winner",
            "won",
        ],
    ).upper()

    return value in {"1", "TRUE", "YES", "Y", "WINNER"}


def select_winner(rows: list[dict[str, str]]) -> dict[str, str] | None:
    positional = [row for row in rows if finish_position(row) == 1]
    if len(positional) == 1:
        return positional[0]

    flagged = [row for row in rows if explicit_winner_flag(row)]
    if len(flagged) == 1:
        return flagged[0]

    return None



def marker_metres(row: dict[str, str]) -> int | None:
    """
    Return the exact governed distance-to-finish marker.

    Canonical Runner Sectional Fact V2.1 stores this as
    distance_to_finish_metres. distance_marker is retained only as a
    deterministic fallback for compatible historical rows.
    """
    direct = parse_int(
        first_value(
            row,
            (
                "distance_to_finish_metres",
                "sectional_marker_metres",
                "marker_metres",
            ),
        )
    )

    if direct is not None:
        return direct

    label = first_value(
        row,
        (
            "distance_marker",
            "sectional_marker",
            "sectional",
        ),
    )

    match = re.search(r"(\d+)", label)

    if not match:
        return None

    return int(match.group(1))


def sectional_time(row: dict[str, str]) -> str:
    """
    Return the canonical cumulative time from the marker to the finish.

    Canonical Runner Sectional Fact V2.1 stores this as
    cumulative_time_to_finish_seconds.
    """
    return canonical_decimal(
        first_value(
            row,
            (
                "cumulative_time_to_finish_seconds",
                "sectional_time_seconds",
                "time_seconds",
                "sectional_time",
                "time",
            ),
        )
    )

def match_sectional_to_winner(
    sectionals: list[dict[str, str]],
    winner: dict[str, str] | None,
) -> list[dict[str, str]]:
    if winner is None:
        return []

    w_runner_key = runner_key(winner)
    w_horse_name = horse_name(winner).casefold()

    matched: list[dict[str, str]] = []

    for row in sectionals:
        s_runner_key = first_value(
            row,
            [
                "runner_key",
                "canonical_runner_key",
                "race_runner_key",
                "runner_id",
            ],
        )
        s_horse_name = first_value(
            row,
            [
                "horse_name",
                "runner_name",
                "horse",
                "name",
            ],
        ).casefold()

        if w_runner_key and s_runner_key and w_runner_key == s_runner_key:
            matched.append(row)
            continue

        if w_horse_name and s_horse_name and w_horse_name == s_horse_name:
            matched.append(row)

    return matched


def exact_marker_time(
    sectionals: list[dict[str, str]],
    marker: int,
) -> str:
    values = {
        sectional_time(row)
        for row in sectionals
        if marker_metres(row) == marker and sectional_time(row) != ""
    }

    if len(values) == 1:
        return next(iter(values))

    return ""


def infer_race_coverage(
    runner_rows: list[dict[str, str]],
    canonical_race_row: dict[str, str],
) -> tuple[str, int, int, int]:
    coverages = [
        first_value(row, ["split_coverage_type"]).upper()
        for row in runner_rows
    ]

    full = sum(value == "FULL_RACE" for value in coverages)
    partial = sum(value == "PARTIAL_TIMING_WINDOW" for value in coverages)
    unresolved = sum(
        value not in {"FULL_RACE", "PARTIAL_TIMING_WINDOW"}
        for value in coverages
    )

    race_full = parse_int(
        first_value(
            canonical_race_row,
            ["full_race_coverage_runner_count"],
        )
    )
    race_partial = parse_int(
        first_value(
            canonical_race_row,
            ["partial_timing_window_runner_count"],
        )
    )
    race_unresolved = parse_int(
        first_value(
            canonical_race_row,
            ["unresolved_coverage_runner_count"],
        )
    )

    if race_full is not None and race_full != full:
        fail(
            "Canonical race FULL_RACE count does not reconcile for "
            f"{first_value(canonical_race_row, ['race_key'])}: "
            f"race={race_full}, runners={full}"
        )

    if race_partial is not None and race_partial != partial:
        fail(
            "Canonical race PARTIAL_TIMING_WINDOW count does not reconcile for "
            f"{first_value(canonical_race_row, ['race_key'])}: "
            f"race={race_partial}, runners={partial}"
        )

    if race_unresolved is not None and race_unresolved != unresolved:
        fail(
            "Canonical race unresolved count does not reconcile for "
            f"{first_value(canonical_race_row, ['race_key'])}: "
            f"race={race_unresolved}, runners={unresolved}"
        )

    if unresolved:
        coverage = "UNRESOLVED"
    elif full and partial:
        coverage = "MIXED"
    elif partial:
        coverage = "PARTIAL_TIMING_WINDOW"
    elif full:
        coverage = "FULL_RACE"
    else:
        coverage = "UNRESOLVED"

    return coverage, full, partial, unresolved


def build() -> dict[str, Any]:
    required_paths = [
        RACE_PATH,
        RUNNER_PATH,
        SECTIONAL_PATH,
        SPLIT_PATH,
        CANONICAL_AUDIT_PATH,
    ]

    for path in required_paths:
        if not path.exists():
            fail(f"Required canonical dependency is missing: {path}")

    with CANONICAL_AUDIT_PATH.open("r", encoding="utf-8-sig") as handle:
        canonical_audit = json.load(handle)

    if not canonical_audit_passes(canonical_audit):
        fail(
            "Canonical Speed Warehouse V2.1 audit does not contain a valid "
            "PASS state. Benchmark observation build stopped."
        )

    race_rows, race_fields = read_csv(RACE_PATH)
    runner_rows, runner_fields = read_csv(RUNNER_PATH)
    sectional_rows, sectional_fields = read_csv(SECTIONAL_PATH)
    split_rows, split_fields = read_csv(SPLIT_PATH)

    if not race_rows:
        fail("Canonical race fact contains no rows.")

    runners_by_race: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in runner_rows:
        key = runner_race_key(row)
        if not key:
            fail("Canonical runner fact contains a row without race_key.")
        runners_by_race[key].append(row)

    sectionals_by_race: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sectional_rows:
        key = first_value(row, ["race_key"])
        if not key:
            fail("Canonical sectional fact contains a row without race_key.")
        sectionals_by_race[key].append(row)

    race_keys = [first_value(row, ["race_key"]) for row in race_rows]

    if any(not key for key in race_keys):
        fail("Canonical race fact contains a row without race_key.")

    duplicate_race_keys = [
        key for key, count in Counter(race_keys).items() if count > 1
    ]
    if duplicate_race_keys:
        fail(
            "Duplicate race keys in canonical race fact: "
            + ", ".join(duplicate_race_keys[:20])
        )

    orphan_runner_races = sorted(set(runners_by_race) - set(race_keys))
    if orphan_runner_races:
        fail(
            "Canonical runner facts contain races absent from race fact: "
            + ", ".join(orphan_runner_races[:20])
        )

    output_rows: list[dict[str, str]] = []

    for race_row in sorted(
        race_rows,
        key=lambda row: first_value(row, ["race_key"]),
    ):
        race_key = first_value(race_row, ["race_key"])
        race_runners = runners_by_race.get(race_key, [])
        race_sectionals = sectionals_by_race.get(race_key, [])

        if not race_runners:
            fail(f"Race has no canonical runners: {race_key}")

        parsed_date, parsed_track, parsed_race_number = parse_race_key(race_key)

        race_date = first_value(
            race_row,
            [
                "race_date",
                "meeting_date",
                "date",
            ],
        ) or parsed_date

        track_name = first_value(
            race_row,
            [
                "track_name",
                "meeting_name",
                "venue_name",
                "track",
                "meeting",
            ],
        ) or parsed_track

        race_number = first_value(
            race_row,
            [
                "race_number",
                "race_no",
                "race",
            ],
        ) or parsed_race_number

        coverage, full_count, partial_count, unresolved_count = (
            infer_race_coverage(race_runners, race_row)
        )

        winner = select_winner(race_runners)
        winner_sections = match_sectional_to_winner(
            race_sectionals,
            winner,
        )

        winner_time = ""
        if winner is not None:
            winner_time = canonical_decimal(
                first_value(
                    winner,
                    [
                        "race_time_seconds",
                        "runner_time_seconds",
                        "official_time_seconds",
                        "time_seconds",
                    ],
                )
            )

        if unresolved_count:
            observation_status = "UNRESOLVED_COVERAGE"
        elif not race_key or not race_date or not track_name:
            observation_status = "INCOMPLETE_RACE_IDENTITY"
        elif winner is None:
            observation_status = "INCOMPLETE_WINNER_IDENTITY"
        elif not winner_time:
            observation_status = "INCOMPLETE_WINNER_TIME"
        else:
            observation_status = "COMPLETE"

        evidence_complete = (
            observation_status == "COMPLETE"
        )

        output_rows.append(
            {
                "benchmark_observation_id": deterministic_id(race_key),
                "race_key": race_key,
                "race_date": race_date,
                "track_name": track_name,
                "course_name": first_value(
                    race_row,
                    [
                        "course_name",
                        "course",
                        "track_course",
                    ],
                ),
                "race_number": canonical_decimal(race_number),
                "official_distance_metres": governed_official_distance(winner),
                "surface": first_value(
                    race_row,
                    [
                        "surface",
                        "surface_type",
                    ],
                ),
                "track_condition": first_value(
                    race_row,
                    [
                        "track_condition",
                        "track_rating",
                        "going",
                    ],
                ),
                "rail_position": first_value(
                    race_row,
                    [
                        "rail_position",
                        "rail",
                    ],
                ),
                "race_class": first_value(
                    race_row,
                    [
                        "race_class",
                        "class",
                        "race_grade",
                    ],
                ),
                "runner_count": str(len(race_runners)),
                "race_split_coverage_type": coverage,
                "full_race_coverage_runner_count": str(full_count),
                "partial_timing_window_runner_count": str(partial_count),
                "unresolved_coverage_runner_count": str(unresolved_count),
                "winner_runner_key": runner_key(winner) if winner else "",
                "winner_horse_name": horse_name(winner) if winner else "",
                "winner_race_time_seconds": winner_time,
                "winner_last_600_seconds": exact_marker_time(
                    winner_sections,
                    600,
                ),
                "winner_last_400_seconds": exact_marker_time(
                    winner_sections,
                    400,
                ),
                "winner_last_200_seconds": exact_marker_time(
                    winner_sections,
                    200,
                ),
                "winner_split_window_start_marker_metres": (
                    canonical_decimal(
                        first_value(
                            winner,
                            ["split_window_start_marker_metres"],
                        )
                    )
                    if winner
                    else ""
                ),
                "winner_split_window_distance_metres": (
                    canonical_decimal(
                        first_value(
                            winner,
                            ["split_window_distance_metres"],
                        )
                    )
                    if winner
                    else ""
                ),
                "winner_split_window_seconds": (
                    canonical_decimal(
                        first_value(
                            winner,
                            ["split_window_seconds"],
                        )
                    )
                    if winner
                    else ""
                ),
                "winner_opening_untimed_distance_metres": (
                    canonical_decimal(
                        first_value(
                            winner,
                            ["opening_untimed_distance_metres"],
                        )
                    )
                    if winner
                    else ""
                ),
                "source_provider": SOURCE_PROVIDER,
                "source_canonical_version": SOURCE_CANONICAL_VERSION,
                "source_semantic_version": SOURCE_SEMANTIC_VERSION,
                "observation_status": observation_status,
                "evidence_complete": (
                    "true" if evidence_complete else "false"
                ),
                "race_source_row_sha256": row_sha256(race_row),
                "winner_source_row_sha256": (
                    row_sha256(winner) if winner else ""
                ),
            }
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open(
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
        writer.writerows(output_rows)

    observation_ids = [
        row["benchmark_observation_id"] for row in output_rows
    ]

    audit = {
        "audit_name": "EDGEIQ Benchmark Observation Fact V1 Build Audit",
        "audit_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "pass_marker": PASS_MARKER,
        "source_canonical_version": SOURCE_CANONICAL_VERSION,
        "source_semantic_version": SOURCE_SEMANTIC_VERSION,
        "input_files": {
            str(path.relative_to(ROOT)).replace("\\", "/"): {
                "sha256": file_sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in required_paths
        },
        "output_file": {
            "path": str(OUTPUT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": file_sha256(OUTPUT_PATH),
            "bytes": OUTPUT_PATH.stat().st_size,
        },
        "source_counts": {
            "canonical_races": len(race_rows),
            "canonical_runners": len(runner_rows),
            "canonical_sectionals": len(sectional_rows),
            "canonical_splits": len(split_rows),
        },
        "output_counts": {
            "benchmark_observations": len(output_rows),
            "unique_race_keys": len(
                {row["race_key"] for row in output_rows}
            ),
            "unique_observation_ids": len(set(observation_ids)),
        },
        "coverage_counts": dict(
            sorted(
                Counter(
                    row["race_split_coverage_type"]
                    for row in output_rows
                ).items()
            )
        ),
        "observation_status_counts": dict(
            sorted(
                Counter(
                    row["observation_status"]
                    for row in output_rows
                ).items()
            )
        ),
        "complete_evidence_count": sum(
            row["evidence_complete"] == "true"
            for row in output_rows
        ),
        "incomplete_evidence_count": sum(
            row["evidence_complete"] != "true"
            for row in output_rows
        ),
        "governance_checks": {
            "canonical_audit_passed": True,
            "one_output_per_canonical_race": (
                len(output_rows) == len(race_rows)
            ),
            "unique_race_keys": (
                len({row["race_key"] for row in output_rows})
                == len(output_rows)
            ),
            "unique_observation_ids": (
                len(set(observation_ids)) == len(output_rows)
            ),
            "zero_unresolved_runner_coverage": all(
                row["unresolved_coverage_runner_count"] == "0"
                for row in output_rows
            ),
            "zero_unresolved_race_coverage": all(
                row["race_split_coverage_type"] != "UNRESOLVED"
                for row in output_rows
            ),
            "runner_counts_reconciled": all(
                int(row["runner_count"])
                == (
                    int(row["full_race_coverage_runner_count"])
                    + int(
                        row[
                            "partial_timing_window_runner_count"
                        ]
                    )
                    + int(row["unresolved_coverage_runner_count"])
                )
                for row in output_rows
            ),
            "deterministic_ordering": (
                [row["race_key"] for row in output_rows]
                == sorted(row["race_key"] for row in output_rows)
            ),
            "no_standard_time_fields": all(
                "standard" not in field.lower()
                and "benchmark_time" not in field.lower()
                and "rating" not in field.lower()
                and "lengths_vs" not in field.lower()
                for field in OUTPUT_FIELDS
            ),
        },
        "source_headers": {
            "race_fact": race_fields,
            "runner_fact": runner_fields,
            "sectional_fact": sectional_fields,
            "split_fact": split_fields,
        },
    }

    failed_checks = [
        check
        for check, passed in audit["governance_checks"].items()
        if not passed
    ]

    if failed_checks:
        audit["status"] = "FAIL"
        audit["failed_checks"] = failed_checks
        audit["pass_marker"] = ""

    with AUDIT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    if failed_checks:
        fail(
            "Benchmark Observation Fact V1 governance failed: "
            + ", ".join(failed_checks)
        )

    return audit


def main() -> int:
    try:
        audit = build()
    except Exception as exc:
        print(
            f"EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1_BUILD_FAIL: {exc}",
            file=sys.stderr,
        )
        return 1

    print("Benchmark Observation Fact V1 built.")
    print(
        "Observations:",
        audit["output_counts"]["benchmark_observations"],
    )
    print("Coverage:", audit["coverage_counts"])
    print("Statuses:", audit["observation_status_counts"])
    print(PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
