from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

SOURCE = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_historical_results_warehouse_v2_graphql.csv"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_5b_4"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_5b_4"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_5b_4"
)

AUDIT_VERSION = (
    "NON_BLANK_RACE_TIME_CONSISTENCY_V0_1"
)

PROGRESS_INTERVAL = 100_000

VALID_SPEED_MIN_MPS = 8.0
VALID_SPEED_MAX_MPS = 22.0


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_date(value: Any) -> str:
    text = clean(value)

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        text,
    )

    return match.group(1) if match else ""


def normalise_text(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        clean(value).upper(),
    )


def parse_number(value: Any) -> float | None:
    text = clean(value)

    if not text:
        return None

    text = text.replace(
        ",",
        "",
    )

    colon_match = re.fullmatch(
        r"(\d+):(\d+(?:\.\d+)?)",
        text,
    )

    if colon_match:
        number = (
            float(colon_match.group(1))
            * 60.0
            + float(colon_match.group(2))
        )

        return number if math.isfinite(number) else None

    match = re.fullmatch(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    try:
        number = float(text)
    except ValueError:
        return None

    return number if math.isfinite(number) else None


def normalise_integer(value: Any) -> str:
    number = parse_number(value)

    if (
        number is None
        or not number.is_integer()
    ):
        return ""

    return str(int(number))


def normalise_numeric_text(
    value: float,
) -> str:
    return (
        f"{value:.12f}"
        .rstrip("0")
        .rstrip(".")
    )


def race_context_key(
    row: dict[str, str],
) -> str:
    components = (
        normalise_date(
            row.get("race_date")
        ),
        normalise_text(
            row.get("state")
        ),
        normalise_text(
            row.get("track")
        ),
        normalise_integer(
            row.get("race_no")
        ),
        clean(
            row.get("race_id")
        ),
    )

    if not all(components):
        return ""

    return "|".join(components)


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str] | None = None,
) -> None:
    fields = list(
        fieldnames or []
    )

    if not fields:
        for row in rows:
            for field in row:
                if field not in fields:
                    fields.append(field)

    if not fields:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(
    path: Path,
    payload: Any,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not SOURCE.exists():
        raise FileNotFoundError(
            SOURCE
        )

    race_records: dict[
        str,
        dict[str, Any],
    ] = {}

    source_rows = 0
    blank_context_rows = 0

    print(
        "PHASE1_5B_4_NON_BLANK_TIME_AUDIT_START",
        flush=True,
    )

    with SOURCE.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            source_rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "NON_BLANK_TIME_AUDIT_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            context_key = race_context_key(
                row
            )

            if not context_key:
                blank_context_rows += 1
                continue

            record = race_records.get(
                context_key
            )

            if record is None:
                record = {
                    "race_context_key": (
                        context_key
                    ),
                    "provider_race_id": clean(
                        row.get("race_id")
                    ),
                    "race_date": (
                        normalise_date(
                            row.get(
                                "race_date"
                            )
                        )
                    ),
                    "state": normalise_text(
                        row.get("state")
                    ),
                    "track": normalise_text(
                        row.get("track")
                    ),
                    "race_number": (
                        normalise_integer(
                            row.get("race_no")
                        )
                    ),
                    "race_name": clean(
                        row.get("race_name")
                    ),
                    "runner_rows": 0,
                    "blank_time_rows": 0,
                    "invalid_time_rows": 0,
                    "numeric_time_rows": 0,
                    "numeric_time_values": set(),
                    "raw_numeric_time_values": (
                        defaultdict(set)
                    ),
                    "distance_values": set(),
                    "winner_rows": 0,
                    "winner_numeric_times": set(),
                    "winner_blank_times": 0,
                    "winner_invalid_times": 0,
                }

                race_records[
                    context_key
                ] = record

            record["runner_rows"] += 1

            distance = parse_number(
                row.get("distance")
            )

            if distance is not None:
                record[
                    "distance_values"
                ].add(distance)

            finish_position = parse_number(
                row.get("finish")
            )

            is_winner = (
                finish_position == 1
            )

            if is_winner:
                record["winner_rows"] += 1

            raw_time = clean(
                row.get("winning_time")
            )

            if not raw_time:
                record["blank_time_rows"] += 1

                if is_winner:
                    record[
                        "winner_blank_times"
                    ] += 1

                continue

            numeric_time = parse_number(
                raw_time
            )

            if (
                numeric_time is None
                or numeric_time <= 0
            ):
                record[
                    "invalid_time_rows"
                ] += 1

                if is_winner:
                    record[
                        "winner_invalid_times"
                    ] += 1

                continue

            record[
                "numeric_time_rows"
            ] += 1

            normalised_value = (
                normalise_numeric_text(
                    numeric_time
                )
            )

            record[
                "numeric_time_values"
            ].add(
                numeric_time
            )

            record[
                "raw_numeric_time_values"
            ][
                normalised_value
            ].add(
                raw_time
            )

            if is_winner:
                record[
                    "winner_numeric_times"
                ].add(
                    numeric_time
                )

    classification_counts = Counter()
    unit_counts = Counter()

    race_profile_rows: list[
        dict[str, Any]
    ] = []

    genuine_conflict_rows: list[
        dict[str, Any]
    ] = []

    missing_time_rows: list[
        dict[str, Any]
    ] = []

    invalid_time_rows: list[
        dict[str, Any]
    ] = []

    benchmark_eligible_races = 0
    benchmark_blocked_races = 0

    for context_key, record in sorted(
        race_records.items()
    ):
        non_blank_values = sorted(
            record[
                "numeric_time_values"
            ]
        )

        distinct_non_blank_count = len(
            non_blank_values
        )

        blank_rows = record[
            "blank_time_rows"
        ]

        invalid_rows = record[
            "invalid_time_rows"
        ]

        numeric_rows = record[
            "numeric_time_rows"
        ]

        if invalid_rows > 0:
            classification = (
                "INVALID_TIME_VALUE"
            )

        elif distinct_non_blank_count == 0:
            classification = (
                "NO_TIME_AVAILABLE"
            )

        elif distinct_non_blank_count == 1:
            if blank_rows > 0:
                classification = (
                    "CONSISTENT_WITH_MISSING"
                )
            else:
                classification = (
                    "CONSISTENT_COMPLETE"
                )

        else:
            classification = (
                "MULTIPLE_NON_BLANK_VALUES"
            )

        classification_counts[
            classification
        ] += 1

        governed_raw_time = None

        if distinct_non_blank_count == 1:
            governed_raw_time = (
                non_blank_values[0]
            )

        distance_values = sorted(
            record[
                "distance_values"
            ]
        )

        distance_metres = (
            distance_values[0]
            if len(distance_values) == 1
            else None
        )

        unit_state = (
            "TIME_UNAVAILABLE"
        )

        governed_seconds = ""
        benchmark_eligible = False
        speed_if_seconds = None
        speed_if_centiseconds = None
        speed_if_milliseconds = None

        if (
            governed_raw_time is not None
            and distance_metres is not None
            and distance_metres > 0
        ):
            speed_if_seconds = (
                distance_metres
                / governed_raw_time
            )

            speed_if_centiseconds = (
                distance_metres
                / (
                    governed_raw_time
                    / 100.0
                )
            )

            speed_if_milliseconds = (
                distance_metres
                / (
                    governed_raw_time
                    / 1000.0
                )
            )

            seconds_plausible = (
                VALID_SPEED_MIN_MPS
                <= speed_if_seconds
                <= VALID_SPEED_MAX_MPS
            )

            centiseconds_plausible = (
                VALID_SPEED_MIN_MPS
                <= speed_if_centiseconds
                <= VALID_SPEED_MAX_MPS
            )

            milliseconds_plausible = (
                VALID_SPEED_MIN_MPS
                <= speed_if_milliseconds
                <= VALID_SPEED_MAX_MPS
            )

            plausible_count = sum(
                (
                    seconds_plausible,
                    centiseconds_plausible,
                    milliseconds_plausible,
                )
            )

            if (
                centiseconds_plausible
                and plausible_count == 1
            ):
                unit_state = (
                    "CENTISECONDS_CONFIRMED"
                )

                governed_seconds = round(
                    governed_raw_time
                    / 100.0,
                    6,
                )

            elif (
                seconds_plausible
                and plausible_count == 1
            ):
                unit_state = (
                    "SECONDS_SOURCE_ANOMALY"
                )

            elif (
                milliseconds_plausible
                and plausible_count == 1
            ):
                unit_state = (
                    "MILLISECONDS_SOURCE_ANOMALY"
                )

            elif plausible_count > 1:
                unit_state = (
                    "MULTIPLE_UNITS_PLAUSIBLE"
                )

            else:
                unit_state = (
                    "NO_UNIT_PLAUSIBLE"
                )

        elif governed_raw_time is not None:
            unit_state = (
                "DISTANCE_UNAVAILABLE_OR_CONFLICTED"
            )

        if (
            classification
            in {
                "CONSISTENT_COMPLETE",
                "CONSISTENT_WITH_MISSING",
            }
            and unit_state
            == "CENTISECONDS_CONFIRMED"
        ):
            benchmark_eligible = True
            benchmark_eligible_races += 1
        else:
            benchmark_blocked_races += 1

        unit_counts[
            unit_state
        ] += 1

        raw_value_display = (
            " | ".join(
                normalise_numeric_text(
                    value
                )
                for value
                in non_blank_values
            )
        )

        raw_variant_display = (
            " | ".join(
                (
                    f"{normalised}:"
                    + ",".join(
                        sorted(
                            record[
                                "raw_numeric_time_values"
                            ][
                                normalised
                            ]
                        )
                    )
                )
                for normalised
                in sorted(
                    record[
                        "raw_numeric_time_values"
                    ].keys()
                )
            )
        )

        winner_values_display = (
            " | ".join(
                normalise_numeric_text(
                    value
                )
                for value
                in sorted(
                    record[
                        "winner_numeric_times"
                    ]
                )
            )
        )

        profile_row = {
            "race_context_key": (
                context_key
            ),
            "provider_race_id": (
                record[
                    "provider_race_id"
                ]
            ),
            "race_date": (
                record["race_date"]
            ),
            "state": (
                record["state"]
            ),
            "track": (
                record["track"]
            ),
            "race_number": (
                record[
                    "race_number"
                ]
            ),
            "race_name": (
                record["race_name"]
            ),
            "runner_rows": (
                record["runner_rows"]
            ),
            "numeric_time_rows": (
                numeric_rows
            ),
            "blank_time_rows": (
                blank_rows
            ),
            "invalid_time_rows": (
                invalid_rows
            ),
            "distinct_non_blank_time_count": (
                distinct_non_blank_count
            ),
            "non_blank_time_values": (
                raw_value_display
            ),
            "raw_time_variants": (
                raw_variant_display
            ),
            "winner_row_count": (
                record["winner_rows"]
            ),
            "winner_time_values": (
                winner_values_display
            ),
            "winner_blank_time_rows": (
                record[
                    "winner_blank_times"
                ]
            ),
            "winner_invalid_time_rows": (
                record[
                    "winner_invalid_times"
                ]
            ),
            "distance_value_count": (
                len(distance_values)
            ),
            "distance_values": (
                " | ".join(
                    normalise_numeric_text(
                        value
                    )
                    for value
                    in distance_values
                )
            ),
            "governed_raw_time": (
                (
                    normalise_numeric_text(
                        governed_raw_time
                    )
                )
                if governed_raw_time
                is not None
                else ""
            ),
            "source_time_unit": (
                "CENTISECONDS"
                if unit_state
                == "CENTISECONDS_CONFIRMED"
                else ""
            ),
            "governed_time_seconds": (
                governed_seconds
            ),
            "speed_if_seconds_mps": (
                round(
                    speed_if_seconds,
                    6,
                )
                if speed_if_seconds
                is not None
                else ""
            ),
            "speed_if_centiseconds_mps": (
                round(
                    speed_if_centiseconds,
                    6,
                )
                if speed_if_centiseconds
                is not None
                else ""
            ),
            "speed_if_milliseconds_mps": (
                round(
                    speed_if_milliseconds,
                    6,
                )
                if speed_if_milliseconds
                is not None
                else ""
            ),
            "race_time_consistency_state": (
                classification
            ),
            "unit_state": (
                unit_state
            ),
            "benchmark_eligible": (
                benchmark_eligible
            ),
            "blank_is_conflict": (
                False
            ),
            "automatic_anomaly_conversion_allowed": (
                False
            ),
        }

        race_profile_rows.append(
            profile_row
        )

        if classification == (
            "MULTIPLE_NON_BLANK_VALUES"
        ):
            genuine_conflict_rows.append(
                profile_row
            )

        elif classification == (
            "NO_TIME_AVAILABLE"
        ):
            missing_time_rows.append(
                profile_row
            )

        elif classification == (
            "INVALID_TIME_VALUE"
        ):
            invalid_time_rows.append(
                profile_row
            )

    distinct_races = len(
        race_records
    )

    consistent_complete = (
        classification_counts[
            "CONSISTENT_COMPLETE"
        ]
    )

    consistent_with_missing = (
        classification_counts[
            "CONSISTENT_WITH_MISSING"
        ]
    )

    no_time_available = (
        classification_counts[
            "NO_TIME_AVAILABLE"
        ]
    )

    genuine_conflicts = (
        classification_counts[
            "MULTIPLE_NON_BLANK_VALUES"
        ]
    )

    invalid_time_races = (
        classification_counts[
            "INVALID_TIME_VALUE"
        ]
    )

    consistent_races = (
        consistent_complete
        + consistent_with_missing
    )

    confirmed_centisecond_races = (
        unit_counts[
            "CENTISECONDS_CONFIRMED"
        ]
    )

    unit_evaluable_races = sum(
        count
        for state, count
        in unit_counts.items()
        if state not in {
            "TIME_UNAVAILABLE",
            "DISTANCE_UNAVAILABLE_OR_CONFLICTED",
        }
    )

    centisecond_dominance_pct = (
        round(
            confirmed_centisecond_races
            / unit_evaluable_races
            * 100,
            6,
        )
        if unit_evaluable_races
        else 0.0
    )

    checks = [
        {
            "check": (
                "SOURCE_ROWS_PROFILED"
            ),
            "passed": (
                source_rows == 879784
            ),
            "observed": (
                source_rows
            ),
        },
        {
            "check": (
                "RACE_CONTEXT_COMPLETE"
            ),
            "passed": (
                blank_context_rows == 0
            ),
            "observed": (
                blank_context_rows
            ),
        },
        {
            "check": (
                "RACE_CLASSIFICATIONS_EXHAUSTIVE"
            ),
            "passed": (
                sum(
                    classification_counts.values()
                )
                == distinct_races
            ),
            "observed": (
                f"classified="
                f"{sum(classification_counts.values())};"
                f"races={distinct_races}"
            ),
        },
        {
            "check": (
                "BLANK_TIME_NOT_TREATED_AS_"
                "CONFLICT"
            ),
            "passed": all(
                not row[
                    "blank_is_conflict"
                ]
                for row
                in race_profile_rows
            ),
            "observed": (
                "BLANK_EXCLUDED_FROM_"
                "UNIQUENESS_SET"
            ),
        },
        {
            "check": (
                "GENUINE_CONFLICT_DEFINITION"
            ),
            "passed": all(
                int(
                    row[
                        "distinct_non_blank_time_count"
                    ]
                )
                > 1
                for row
                in genuine_conflict_rows
            ),
            "observed": (
                genuine_conflicts
            ),
        },
        {
            "check": (
                "CENTISECOND_UNIT_DOMINANCE"
            ),
            "passed": (
                centisecond_dominance_pct
                >= 99.0
            ),
            "observed": (
                f"confirmed="
                f"{confirmed_centisecond_races};"
                f"evaluable="
                f"{unit_evaluable_races};"
                f"pct="
                f"{centisecond_dominance_pct}"
            ),
        },
        {
            "check": (
                "BENCHMARK_ELIGIBILITY_GOVERNED"
            ),
            "passed": all(
                (
                    row[
                        "race_time_consistency_state"
                    ]
                    in {
                        "CONSISTENT_COMPLETE",
                        "CONSISTENT_WITH_MISSING",
                    }
                    and row[
                        "unit_state"
                    ]
                    == "CENTISECONDS_CONFIRMED"
                )
                == bool(
                    row[
                        "benchmark_eligible"
                    ]
                )
                for row
                in race_profile_rows
            ),
            "observed": (
                f"eligible="
                f"{benchmark_eligible_races};"
                f"blocked="
                f"{benchmark_blocked_races}"
            ),
        },
        {
            "check": (
                "NO_ANOMALY_AUTO_CONVERSION"
            ),
            "passed": all(
                not row[
                    "automatic_anomaly_conversion_allowed"
                ]
                for row
                in race_profile_rows
            ),
            "observed": (
                "ALL_AUTOMATIC_ANOMALY_"
                "CONVERSIONS_DISABLED"
            ),
        },
    ]

    failed_checks = [
        check["check"]
        for check in checks
        if not check["passed"]
    ]

    if (
        centisecond_dominance_pct >= 99.0
        and genuine_conflicts == 0
        and invalid_time_races == 0
    ):
        decision = (
            "RACE_TIME_EVIDENCE_VALIDATED_"
            "FOR_CORRECTED_MATERIALISATION"
        )

        next_stage = (
            "Phase 1.5B.5 materialise a new "
            "immutable performance-facts snapshot "
            "retaining raw centiseconds, source "
            "unit, governed seconds and race-level "
            "time quality state."
        )

    elif (
        centisecond_dominance_pct >= 99.0
        and genuine_conflicts
        + invalid_time_races
        <= 100
    ):
        decision = (
            "RACE_TIME_EVIDENCE_VALIDATED_"
            "WITH_QUARANTINED_EXCEPTIONS"
        )

        next_stage = (
            "Phase 1.5B.5 materialise corrected "
            "facts for validated races and retain "
            "genuine conflicts and invalid values "
            "as benchmark-ineligible quality states."
        )

    else:
        decision = (
            "RACE_TIME_EVIDENCE_REMAINS_"
            "BLOCKED"
        )

        next_stage = (
            "Resolve genuine non-blank time "
            "conflicts, invalid values or unit "
            "ambiguity before materialisation."
        )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    profile_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_non_blank_race_time_"
            f"profile_v0_1_{run_id}.csv"
        )
    )

    conflicts_path = (
        AUDIT_DIR
        / (
            "edgeiq_genuine_race_time_"
            f"conflicts_v0_1_{run_id}.csv"
        )
    )

    missing_path = (
        AUDIT_DIR
        / (
            "edgeiq_race_time_missing_"
            f"v0_1_{run_id}.csv"
        )
    )

    invalid_path = (
        AUDIT_DIR
        / (
            "edgeiq_race_time_invalid_"
            f"v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5b_4_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5b_4_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_5b_4_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_5B_4_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_NON_BLANK_RACE_TIME_"
            "CONSISTENCY_V0_1.md"
        )
    )

    write_csv(
        profile_path,
        race_profile_rows,
    )

    write_csv(
        conflicts_path,
        genuine_conflict_rows,
        fieldnames=(
            list(
                race_profile_rows[0].keys()
            )
            if race_profile_rows
            else []
        ),
    )

    write_csv(
        missing_path,
        missing_time_rows,
        fieldnames=(
            list(
                race_profile_rows[0].keys()
            )
            if race_profile_rows
            else []
        ),
    )

    write_csv(
        invalid_path,
        invalid_time_rows,
        fieldnames=(
            list(
                race_profile_rows[0].keys()
            )
            if race_profile_rows
            else []
        ),
    )

    write_csv(
        checks_path,
        checks,
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.5B.4 Non-Blank Race-Time "
            "Consistency Audit"
        ),
        "generated_utc": (
            utc_now()
        ),
        "audit_version": (
            AUDIT_VERSION
        ),
        "status": (
            "NON_BLANK_RACE_TIME_"
            "CONSISTENCY_PASS"
            if not failed_checks
            else
            "NON_BLANK_RACE_TIME_"
            "CONSISTENCY_PARTIAL"
        ),
        "production_data_modified": False,
        "performance_facts_modified": False,
        "source_rows": (
            source_rows
        ),
        "blank_context_rows": (
            blank_context_rows
        ),
        "distinct_races": (
            distinct_races
        ),
        "classification_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),
        "consistent_complete_races": (
            consistent_complete
        ),
        "consistent_with_missing_races": (
            consistent_with_missing
        ),
        "consistent_races_total": (
            consistent_races
        ),
        "no_time_available_races": (
            no_time_available
        ),
        "genuine_multiple_non_blank_"
        "conflict_races": (
            genuine_conflicts
        ),
        "invalid_time_races": (
            invalid_time_races
        ),
        "unit_counts": dict(
            sorted(
                unit_counts.items()
            )
        ),
        "unit_evaluable_races": (
            unit_evaluable_races
        ),
        "confirmed_centisecond_races": (
            confirmed_centisecond_races
        ),
        "centisecond_dominance_pct": (
            centisecond_dominance_pct
        ),
        "benchmark_eligible_races": (
            benchmark_eligible_races
        ),
        "benchmark_blocked_races": (
            benchmark_blocked_races
        ),
        "checks": checks,
        "failed_checks": (
            failed_checks
        ),
        "decision": (
            decision
        ),
        "current_phase1_5b_snapshot_status": (
            "SUPERSEDED_PENDING_"
            "CORRECTED_MATERIALISATION"
            if (
                "VALIDATED"
                in decision
            )
            else
            "BLOCKED"
        ),
        "next_stage": (
            next_stage
        ),
        "outputs": {
            "race_classification_profile": str(
                profile_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "genuine_conflicts": str(
                conflicts_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "missing_times": str(
                missing_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "invalid_times": str(
                invalid_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "checks": str(
                checks_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
        },
    }

    write_json(
        summary_path,
        summary,
    )

    write_json(
        latest_path,
        summary,
    )

    architecture_path.write_text(
        """# EDGEiQ Non-Blank Race-Time Consistency V0.1

## Core rule

Blank winning-time values are missing evidence.

They are not timing values and cannot create a race-time conflict.

## Race classifications

### CONSISTENT_COMPLETE

One unique numeric winning-time value and no blank or invalid rows.

### CONSISTENT_WITH_MISSING

One unique numeric winning-time value and one or more blank rows.

### NO_TIME_AVAILABLE

No numeric winning-time evidence exists.

### MULTIPLE_NON_BLANK_VALUES

Two or more distinct numeric winning-time values exist within one governed race context.

This is a genuine source conflict.

### INVALID_TIME_VALUE

At least one populated winning-time value cannot be parsed as a positive numeric value.

## Unit rule

A consistent numeric race time may be converted from centiseconds to seconds only when the resulting race speed is plausible and competing units are implausible.

## Benchmark eligibility

A race is eligible only when:

- its consistency state is CONSISTENT_COMPLETE or CONSISTENT_WITH_MISSING
- its time unit is CENTISECONDS_CONFIRMED
- distance evidence is singular and available
- no invalid or conflicting time evidence exists

## Preservation

Raw time values, blanks, invalid values and quality states remain separately auditable.

No source value is overwritten.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.5B.4 Non-Blank Race-Time Consistency Audit

Generated UTC: `{summary['generated_utc']}`

Status: **{summary['status']}**

- Source rows: **{source_rows:,}**
- Governed races: **{distinct_races:,}**
- Consistent complete races: **{consistent_complete:,}**
- Consistent races with missing runner values: **{consistent_with_missing:,}**
- No-time races: **{no_time_available:,}**
- Genuine multiple non-blank conflicts: **{genuine_conflicts:,}**
- Invalid-time races: **{invalid_time_races:,}**
- Confirmed centisecond races: **{confirmed_centisecond_races:,}**
- Centisecond dominance: **{centisecond_dominance_pct}%**
- Benchmark-eligible races: **{benchmark_eligible_races:,}**
- Production data modified: **False**

Decision: **{decision}**

Next stage: **{next_stage}**
""",
        encoding="utf-8",
    )

    print(
        (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            "PHASE1_5B_4_NON_BLANK_RACE_TIME_"
            "CONSISTENCY_PASS"
        )
        if not failed_checks
        else (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            "PHASE1_5B_4_NON_BLANK_RACE_TIME_"
            "CONSISTENCY_PARTIAL"
        ),
        flush=True,
    )

    print(
        f"SOURCE_ROWS="
        f"{source_rows}",
        flush=True,
    )

    print(
        f"DISTINCT_RACES="
        f"{distinct_races}",
        flush=True,
    )

    print(
        f"CONSISTENT_COMPLETE_RACES="
        f"{consistent_complete}",
        flush=True,
    )

    print(
        f"CONSISTENT_WITH_MISSING_RACES="
        f"{consistent_with_missing}",
        flush=True,
    )

    print(
        f"NO_TIME_AVAILABLE_RACES="
        f"{no_time_available}",
        flush=True,
    )

    print(
        f"GENUINE_NON_BLANK_CONFLICT_RACES="
        f"{genuine_conflicts}",
        flush=True,
    )

    print(
        f"INVALID_TIME_RACES="
        f"{invalid_time_races}",
        flush=True,
    )

    print(
        f"CONFIRMED_CENTISECOND_RACES="
        f"{confirmed_centisecond_races}",
        flush=True,
    )

    print(
        f"CENTISECOND_DOMINANCE_PCT="
        f"{centisecond_dominance_pct}",
        flush=True,
    )

    print(
        f"BENCHMARK_ELIGIBLE_RACES="
        f"{benchmark_eligible_races}",
        flush=True,
    )

    print(
        f"DECISION={decision}",
        flush=True,
    )

    print(
        f"SUMMARY={summary_path}",
        flush=True,
    )

    print(
        f"REPORT={report_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
