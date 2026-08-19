from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path


ROOT = Path.cwd()

SPEC_PATH = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1_SPEC.md"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_benchmark_observation_fact_v1_contract.json"
)

BUILDER_PATH = (
    ROOT
    / "scripts"
    / "build_edgeiq_benchmark_observation_fact_v1.py"
)

AUDITOR_PATH = (
    ROOT
    / "scripts"
    / "audit_edgeiq_benchmark_observation_fact_v1.py"
)


SPEC_TEXT = r"""
# EDGEiQ Benchmark Observation Fact V1

## Status

GOVERNED SPECIFICATION

## Component

Benchmark Observation Fact V1

## Purpose

Create one immutable benchmark observation row per canonical race from the
EDGEiQ Racing.com Canonical Speed Warehouse V2.1.

This component records evidence only.

It must not calculate:

- standard times
- benchmark averages
- ratings
- lengths versus standard
- pace scores
- performance scores
- EPI
- ERI
- subjective confidence values

## Architectural Position

Canonical Speed Warehouse V2.1
→ Benchmark Observation Fact V1
→ future Standard Time Engine
→ future Lengths versus Standard Engine
→ future Performance Intelligence Engine

## Authoritative Inputs

- public/data/edgeiq_racingcom_canonical_race_speed_fact_v2_1.csv
- public/data/edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv
- public/data/edgeiq_racingcom_canonical_runner_sectional_fact_v2_1.csv
- public/data/edgeiq_racingcom_canonical_runner_split_fact_v2_1.csv
- public/data/edgeiq_racingcom_canonical_speed_warehouse_v2_1_audit.json

No provider payload may be consumed directly.

## Grain

One row per race_key.

## Required Governance Rules

1. Every race in the canonical race fact must produce exactly one observation.
2. Every observation must have a unique benchmark_observation_id.
3. No unresolved split coverage is allowed.
4. Runner counts must reconcile to the canonical runner fact.
5. Winner identity must be supported by canonical runner facts.
6. Winner timing fields must be copied without mathematical transformation.
7. Missing facts must remain null or blank.
8. No race distance may be invented.
9. No course, surface, rail, class, or track condition may be invented.
10. Output ordering must be deterministic.
11. Input and output file hashes must be recorded.
12. The builder must fail closed if the canonical V2.1 audit is not PASS.

## Coverage Semantics

Allowed split coverage classifications:

- FULL_RACE
- PARTIAL_TIMING_WINDOW

UNRESOLVED is prohibited.

Race-level coverage is classified as:

- FULL_RACE
- PARTIAL_TIMING_WINDOW
- MIXED
- UNRESOLVED

MIXED is allowed only when canonical runners within the same race legitimately
contain more than one resolved coverage type.

## Winner Determination

The winner is identified from canonical runner fields where an explicit finish
position equal to 1 is available.

The builder may inspect known canonical aliases, but it must not infer the
winner from the fastest recorded time when an explicit winner field is absent.

If no explicit winner can be identified:

- winner fields remain blank
- observation_status becomes INCOMPLETE_WINNER_IDENTITY
- the audit records the incomplete observation

## Closing Sectionals

Winner closing sectionals may be populated only from exact canonical markers:

- 600 metres
- 400 metres
- 200 metres

No interpolation is permitted.

## Observation Status

Allowed values:

- COMPLETE
- INCOMPLETE_WINNER_IDENTITY
- INCOMPLETE_WINNER_TIME
- INCOMPLETE_RACE_IDENTITY
- UNRESOLVED_COVERAGE

A row may remain governed evidence even when optional provider facts are absent,
but unresolved timing semantics are prohibited.

## Outputs

- public/data/edgeiq_benchmark_observation_fact_v1.csv
- public/data/edgeiq_benchmark_observation_fact_v1_audit.json

## PASS Marker

EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1_AUDIT_PASS
""".strip() + "\n"


CONTRACT = {
    "contract_name": "EDGEIQ Benchmark Observation Fact V1",
    "contract_version": "1.0.0",
    "grain": "one row per race_key",
    "source_canonical_version": "RACINGCOM_CANONICAL_SPEED_WAREHOUSE_V2_1",
    "prohibited_derivations": [
        "standard times",
        "benchmark averages",
        "ratings",
        "lengths versus standard",
        "pace scores",
        "performance scores",
        "EPI",
        "ERI",
        "invented metadata",
    ],
    "allowed_race_coverage_types": [
        "FULL_RACE",
        "PARTIAL_TIMING_WINDOW",
        "MIXED",
    ],
    "allowed_observation_statuses": [
        "COMPLETE",
        "INCOMPLETE_WINNER_IDENTITY",
        "INCOMPLETE_WINNER_TIME",
        "INCOMPLETE_RACE_IDENTITY",
        "UNRESOLVED_COVERAGE",
    ],
    "fields": [
        {
            "name": "benchmark_observation_id",
            "type": "string",
            "nullable": False,
            "source": "derived deterministic identity",
            "semantic": "SHA-256 based immutable observation identifier",
        },
        {
            "name": "race_key",
            "type": "string",
            "nullable": False,
            "source": "canonical race fact",
            "semantic": "canonical race identity",
        },
        {
            "name": "race_date",
            "type": "date-string",
            "nullable": True,
            "source": "canonical race fact or parsed race_key",
            "semantic": "official race date where available",
        },
        {
            "name": "track_name",
            "type": "string",
            "nullable": True,
            "source": "canonical race fact or parsed race_key",
            "semantic": "canonical track display name",
        },
        {
            "name": "course_name",
            "type": "string",
            "nullable": True,
            "source": "canonical race fact",
            "semantic": "course or circuit identity where explicitly available",
        },
        {
            "name": "race_number",
            "type": "integer-string",
            "nullable": True,
            "source": "canonical race fact or parsed race_key",
            "semantic": "meeting race number",
        },
        {
            "name": "official_distance_metres",
            "type": "decimal-string",
            "nullable": True,
            "source": "canonical race fact",
            "semantic": "official race distance; never inferred",
        },
        {
            "name": "surface",
            "type": "string",
            "nullable": True,
            "source": "canonical race fact",
            "semantic": "explicit surface only",
        },
        {
            "name": "track_condition",
            "type": "string",
            "nullable": True,
            "source": "canonical race fact",
            "semantic": "explicit official track condition only",
        },
        {
            "name": "rail_position",
            "type": "string",
            "nullable": True,
            "source": "canonical race fact",
            "semantic": "explicit rail setting only",
        },
        {
            "name": "race_class",
            "type": "string",
            "nullable": True,
            "source": "canonical race fact",
            "semantic": "explicit race class only",
        },
        {
            "name": "runner_count",
            "type": "integer-string",
            "nullable": False,
            "source": "canonical runner fact reconciliation",
            "semantic": "number of canonical runners in race",
        },
        {
            "name": "race_split_coverage_type",
            "type": "enum-string",
            "nullable": False,
            "source": "canonical runner coverage classifications",
            "semantic": "resolved race-level timing coverage",
        },
        {
            "name": "full_race_coverage_runner_count",
            "type": "integer-string",
            "nullable": False,
            "source": "canonical race fact reconciliation",
            "semantic": "runners with full-race split coverage",
        },
        {
            "name": "partial_timing_window_runner_count",
            "type": "integer-string",
            "nullable": False,
            "source": "canonical race fact reconciliation",
            "semantic": "runners with partial timing-window coverage",
        },
        {
            "name": "unresolved_coverage_runner_count",
            "type": "integer-string",
            "nullable": False,
            "source": "canonical race fact reconciliation",
            "semantic": "must equal zero",
        },
        {
            "name": "winner_runner_key",
            "type": "string",
            "nullable": True,
            "source": "canonical runner fact",
            "semantic": "explicit winning runner identity",
        },
        {
            "name": "winner_horse_name",
            "type": "string",
            "nullable": True,
            "source": "canonical runner fact",
            "semantic": "winning horse name",
        },
        {
            "name": "winner_race_time_seconds",
            "type": "decimal-string",
            "nullable": True,
            "source": "canonical runner fact",
            "semantic": "winner official race time copied without transformation",
        },
        {
            "name": "winner_last_600_seconds",
            "type": "decimal-string",
            "nullable": True,
            "source": "canonical sectional fact",
            "semantic": "winner cumulative time at exact 600m marker",
        },
        {
            "name": "winner_last_400_seconds",
            "type": "decimal-string",
            "nullable": True,
            "source": "canonical sectional fact",
            "semantic": "winner cumulative time at exact 400m marker",
        },
        {
            "name": "winner_last_200_seconds",
            "type": "decimal-string",
            "nullable": True,
            "source": "canonical sectional fact",
            "semantic": "winner cumulative time at exact 200m marker",
        },
        {
            "name": "winner_split_window_start_marker_metres",
            "type": "decimal-string",
            "nullable": True,
            "source": "canonical runner fact",
            "semantic": "first available timing marker for winner",
        },
        {
            "name": "winner_split_window_distance_metres",
            "type": "decimal-string",
            "nullable": True,
            "source": "canonical runner fact",
            "semantic": "distance covered by available winner split window",
        },
        {
            "name": "winner_split_window_seconds",
            "type": "decimal-string",
            "nullable": True,
            "source": "canonical runner fact",
            "semantic": "elapsed time inside available winner split window",
        },
        {
            "name": "winner_opening_untimed_distance_metres",
            "type": "decimal-string",
            "nullable": True,
            "source": "canonical runner fact",
            "semantic": "explicit canonical untimed opening distance; never inferred here",
        },
        {
            "name": "source_provider",
            "type": "string",
            "nullable": False,
            "source": "builder constant",
            "semantic": "RACING.COM",
        },
        {
            "name": "source_canonical_version",
            "type": "string",
            "nullable": False,
            "source": "builder constant",
            "semantic": "canonical source version",
        },
        {
            "name": "source_semantic_version",
            "type": "string",
            "nullable": False,
            "source": "builder constant",
            "semantic": "timing semantic version",
        },
        {
            "name": "observation_status",
            "type": "enum-string",
            "nullable": False,
            "source": "governance classification",
            "semantic": "completeness status without subjective scoring",
        },
        {
            "name": "evidence_complete",
            "type": "boolean-string",
            "nullable": False,
            "source": "governance classification",
            "semantic": "true only when required winner and race timing facts exist",
        },
        {
            "name": "race_source_row_sha256",
            "type": "sha256-string",
            "nullable": False,
            "source": "derived from canonical race row",
            "semantic": "canonical race row evidence hash",
        },
        {
            "name": "winner_source_row_sha256",
            "type": "sha256-string",
            "nullable": True,
            "source": "derived from canonical winning runner row",
            "semantic": "canonical winner row evidence hash",
        },
    ],
}


BUILDER_TEXT = r'''from __future__ import annotations

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
    text = json.dumps(payload, ensure_ascii=False).upper()

    if "FAIL" in text and "FAILED_CHECKS" not in text:
        return False

    explicit_candidates: list[Any] = []

    if isinstance(payload, dict):
        for key in (
            "status",
            "audit_status",
            "overall_status",
            "result",
            "pass",
            "passed",
            "audit_pass",
        ):
            if key in payload:
                explicit_candidates.append(payload[key])

        failed_checks = payload.get("failed_checks")
        if isinstance(failed_checks, int) and failed_checks != 0:
            return False
        if isinstance(failed_checks, list) and failed_checks:
            return False

    for value in explicit_candidates:
        if value is True:
            return True
        if clean(value).upper() in {"PASS", "PASSED", "TRUE", "0"}:
            return True
        if clean(value).upper() in {"FAIL", "FAILED", "FALSE"}:
            return False

    return (
        "CANONICAL_SPEED_WAREHOUSE_V2_1_AUDIT_PASS" in text
        or '"STATUS":"PASS"' in text.replace(" ", "")
        or '"AUDIT_STATUS":"PASS"' in text.replace(" ", "")
    )


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
    raw = first_value(
        row,
        [
            "marker_metres",
            "sectional_marker_metres",
            "distance_from_finish_metres",
            "distance_metres",
            "marker",
            "sectional",
        ],
    )

    match = re.search(r"(\d{3,4})", raw)
    return int(match.group(1)) if match else None


def sectional_time(row: dict[str, str]) -> str:
    return canonical_decimal(
        first_value(
            row,
            [
                "cumulative_time_seconds",
                "sectional_time_seconds",
                "time_seconds",
                "time",
            ],
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
                "official_distance_metres": canonical_decimal(
                    first_value(
                        race_row,
                        [
                            "official_distance_metres",
                            "race_distance_metres",
                            "distance_metres",
                            "distance",
                        ],
                    )
                ),
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
'''


AUDITOR_TEXT = r'''from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OBSERVATION_PATH = DATA / "edgeiq_benchmark_observation_fact_v1.csv"
BUILD_AUDIT_PATH = (
    DATA / "edgeiq_benchmark_observation_fact_v1_audit.json"
)
RACE_PATH = DATA / "edgeiq_racingcom_canonical_race_speed_fact_v2_1.csv"
RUNNER_PATH = DATA / "edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv"

PASS_MARKER = "EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1_AUDIT_PASS"

REQUIRED_FIELDS = [
    "benchmark_observation_id",
    "race_key",
    "race_date",
    "track_name",
    "race_number",
    "official_distance_metres",
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
    "source_provider",
    "source_canonical_version",
    "source_semantic_version",
    "observation_status",
    "evidence_complete",
    "race_source_row_sha256",
    "winner_source_row_sha256",
]


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader], list(reader.fieldnames or [])


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit() -> dict[str, Any]:
    observations, fields = read_csv(OBSERVATION_PATH)
    race_rows, _ = read_csv(RACE_PATH)
    runner_rows, _ = read_csv(RUNNER_PATH)

    with BUILD_AUDIT_PATH.open("r", encoding="utf-8-sig") as handle:
        build_audit = json.load(handle)

    missing_fields = [
        field for field in REQUIRED_FIELDS if field not in fields
    ]

    race_keys = [clean(row.get("race_key")) for row in observations]
    observation_ids = [
        clean(row.get("benchmark_observation_id"))
        for row in observations
    ]

    runner_counts: dict[str, int] = defaultdict(int)
    for row in runner_rows:
        runner_counts[clean(row.get("race_key"))] += 1

    checks: dict[str, bool] = {
        "build_audit_status_pass": (
            clean(build_audit.get("status")).upper() == "PASS"
        ),
        "required_fields_present": not missing_fields,
        "non_empty_output": bool(observations),
        "one_observation_per_canonical_race": (
            len(observations) == len(race_rows)
        ),
        "unique_race_keys": (
            len(race_keys) == len(set(race_keys))
        ),
        "unique_observation_ids": (
            len(observation_ids) == len(set(observation_ids))
        ),
        "no_blank_race_keys": all(race_keys),
        "no_blank_observation_ids": all(observation_ids),
        "allowed_coverage_types_only": all(
            clean(row.get("race_split_coverage_type"))
            in {"FULL_RACE", "PARTIAL_TIMING_WINDOW", "MIXED"}
            for row in observations
        ),
        "zero_unresolved_runner_coverage": all(
            clean(row.get("unresolved_coverage_runner_count")) == "0"
            for row in observations
        ),
        "runner_counts_match_canonical": all(
            int(clean(row.get("runner_count")) or "0")
            == runner_counts.get(clean(row.get("race_key")), 0)
            for row in observations
        ),
        "coverage_counts_sum_to_runner_count": all(
            int(clean(row.get("runner_count")) or "0")
            == (
                int(
                    clean(
                        row.get("full_race_coverage_runner_count")
                    )
                    or "0"
                )
                + int(
                    clean(
                        row.get(
                            "partial_timing_window_runner_count"
                        )
                    )
                    or "0"
                )
                + int(
                    clean(
                        row.get("unresolved_coverage_runner_count")
                    )
                    or "0"
                )
            )
            for row in observations
        ),
        "source_provider_locked": all(
            clean(row.get("source_provider")) == "RACING.COM"
            for row in observations
        ),
        "source_canonical_version_locked": all(
            clean(row.get("source_canonical_version"))
            == "RACINGCOM_CANONICAL_SPEED_WAREHOUSE_V2_1"
            for row in observations
        ),
        "source_semantic_version_locked": all(
            clean(row.get("source_semantic_version"))
            == "RACINGCOM_SPEED_SEMANTICS_V1_1"
            for row in observations
        ),
        "evidence_complete_is_boolean_string": all(
            clean(row.get("evidence_complete")) in {"true", "false"}
            for row in observations
        ),
        "complete_rows_have_winner_identity": all(
            clean(row.get("observation_status")) != "COMPLETE"
            or (
                clean(row.get("winner_horse_name"))
                and clean(row.get("winner_race_time_seconds"))
            )
            for row in observations
        ),
        "no_derived_standard_fields": all(
            "standard" not in field.lower()
            and "benchmark_time" not in field.lower()
            and "rating" not in field.lower()
            and "lengths_vs" not in field.lower()
            for field in fields
        ),
        "output_hash_matches_build_audit": (
            clean(
                build_audit.get("output_file", {}).get("sha256")
            )
            == file_sha256(OBSERVATION_PATH)
        ),
    }

    failed_checks = [
        name for name, passed in checks.items() if not passed
    ]

    result = {
        "audit_name": "EDGEIQ Benchmark Observation Fact V1 Independent Audit",
        "audit_version": "1.0.0",
        "status": "PASS" if not failed_checks else "FAIL",
        "pass_marker": PASS_MARKER if not failed_checks else "",
        "counts": {
            "canonical_races": len(race_rows),
            "canonical_runners": len(runner_rows),
            "observations": len(observations),
            "complete_observations": sum(
                clean(row.get("observation_status")) == "COMPLETE"
                for row in observations
            ),
            "incomplete_observations": sum(
                clean(row.get("observation_status")) != "COMPLETE"
                for row in observations
            ),
        },
        "coverage_counts": dict(
            sorted(
                Counter(
                    clean(row.get("race_split_coverage_type"))
                    for row in observations
                ).items()
            )
        ),
        "status_counts": dict(
            sorted(
                Counter(
                    clean(row.get("observation_status"))
                    for row in observations
                ).items()
            )
        ),
        "checks": checks,
        "failed_checks": failed_checks,
        "missing_fields": missing_fields,
    }

    return result


def main() -> int:
    try:
        result = audit()
    except Exception as exc:
        print(
            f"EDGEIQ_BENCHMARK_OBSERVATION_FACT_V1_AUDIT_FAIL: {exc}",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, indent=2))

    if result["status"] != "PASS":
        return 1

    print(PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


for path in (
    SPEC_PATH,
    CONTRACT_PATH,
    BUILDER_PATH,
    AUDITOR_PATH,
):
    path.parent.mkdir(parents=True, exist_ok=True)

SPEC_PATH.write_text(SPEC_TEXT, encoding="utf-8")

CONTRACT_PATH.write_text(
    json.dumps(CONTRACT, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

BUILDER_PATH.write_text(
    textwrap.dedent(BUILDER_TEXT).lstrip(),
    encoding="utf-8",
)

AUDITOR_PATH.write_text(
    textwrap.dedent(AUDITOR_TEXT).lstrip(),
    encoding="utf-8",
)

print("Created:")
for path in (
    SPEC_PATH,
    CONTRACT_PATH,
    BUILDER_PATH,
    AUDITOR_PATH,
):
    print(f"  {path.relative_to(ROOT)}")
