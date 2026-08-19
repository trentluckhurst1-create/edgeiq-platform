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
    / "phase1_5b_1"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_5b_1"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_5b_1"
)

AUDIT_VERSION = (
    "PERFORMANCE_FACT_UNIT_SEMANTICS_AUDIT_V0_1"
)

PROGRESS_INTERVAL = 100_000


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def parse_number(value: Any) -> float | None:
    text = clean(value)

    if not text:
        return None

    text = text.replace(",", "")

    time_match = re.fullmatch(
        r"(\d+):(\d+(?:\.\d+)?)",
        text,
    )

    if time_match:
        return (
            float(time_match.group(1)) * 60.0
            + float(time_match.group(2))
        )

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    try:
        number = float(match.group(0))
    except ValueError:
        return None

    return number if math.isfinite(number) else None


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


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    fields: list[str] = []

    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)

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


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    race_observations: dict[
        str,
        dict[str, Any],
    ] = {}

    raw_time_format_counts = Counter()
    raw_time_range_counts = Counter()
    raw_margin_counts = Counter()
    raw_margin_l_counts = Counter()
    race_conflicts = Counter()

    rows = 0
    rows_with_time = 0
    rows_with_margin = 0
    rows_with_margin_l = 0

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
            rows += 1

            if (
                row_number == 1
                or row_number % PROGRESS_INTERVAL == 0
            ):
                print(
                    "UNIT_SEMANTICS_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            race_id = clean(
                row.get("race_id")
            )

            distance = parse_number(
                row.get("distance")
            )

            raw_time = clean(
                row.get("winning_time")
            )

            time_value = parse_number(
                raw_time
            )

            margin = parse_number(
                row.get("margin")
            )

            margin_l = parse_number(
                row.get("margin_l")
            )

            if raw_time:
                rows_with_time += 1

                if ":" in raw_time:
                    raw_time_format_counts[
                        "COLON_TIME"
                    ] += 1

                elif re.fullmatch(
                    r"\d+",
                    raw_time,
                ):
                    raw_time_format_counts[
                        "INTEGER_TEXT"
                    ] += 1

                elif re.fullmatch(
                    r"\d+\.\d+",
                    raw_time,
                ):
                    raw_time_format_counts[
                        "DECIMAL_TEXT"
                    ] += 1

                else:
                    raw_time_format_counts[
                        "OTHER"
                    ] += 1

            if time_value is not None:
                if time_value < 30:
                    raw_time_range_counts[
                        "LT_30"
                    ] += 1
                elif time_value < 300:
                    raw_time_range_counts[
                        "30_TO_299"
                    ] += 1
                elif time_value < 3_000:
                    raw_time_range_counts[
                        "300_TO_2999"
                    ] += 1
                elif time_value < 30_000:
                    raw_time_range_counts[
                        "3000_TO_29999"
                    ] += 1
                else:
                    raw_time_range_counts[
                        "GE_30000"
                    ] += 1

            if margin is not None:
                rows_with_margin += 1
                raw_margin_counts[
                    "ZERO"
                    if margin == 0
                    else "NON_ZERO"
                ] += 1

            if margin_l is not None:
                rows_with_margin_l += 1
                raw_margin_l_counts[
                    "ZERO"
                    if margin_l == 0
                    else "NON_ZERO"
                ] += 1

            if not race_id:
                continue

            candidate = {
                "race_id": race_id,
                "race_date": clean(
                    row.get("race_date")
                )[:10],
                "track": clean(
                    row.get("track")
                ),
                "race_no": clean(
                    row.get("race_no")
                ),
                "distance": distance,
                "raw_winning_time": raw_time,
                "raw_winning_time_numeric": (
                    time_value
                ),
            }

            existing = race_observations.get(
                race_id
            )

            if existing is None:
                race_observations[
                    race_id
                ] = candidate

            else:
                signature_existing = (
                    existing["distance"],
                    existing[
                        "raw_winning_time"
                    ],
                )

                signature_candidate = (
                    candidate["distance"],
                    candidate[
                        "raw_winning_time"
                    ],
                )

                if (
                    signature_existing
                    != signature_candidate
                ):
                    race_conflicts[
                        race_id
                    ] += 1

    unit_rows: list[dict[str, Any]] = []
    unit_class_counts = Counter()

    for race_id, observation in sorted(
        race_observations.items()
    ):
        distance = observation[
            "distance"
        ]

        raw_value = observation[
            "raw_winning_time_numeric"
        ]

        raw_seconds_speed = None
        centisecond_speed = None
        millisecond_speed = None

        if (
            distance is not None
            and raw_value is not None
            and raw_value > 0
        ):
            raw_seconds_speed = (
                distance / raw_value
            )

            centisecond_speed = (
                distance
                / (
                    raw_value / 100.0
                )
            )

            millisecond_speed = (
                distance
                / (
                    raw_value / 1000.0
                )
            )

        plausible_raw = (
            raw_seconds_speed is not None
            and 8.0
            <= raw_seconds_speed
            <= 22.0
        )

        plausible_centiseconds = (
            centisecond_speed is not None
            and 8.0
            <= centisecond_speed
            <= 22.0
        )

        plausible_milliseconds = (
            millisecond_speed is not None
            and 8.0
            <= millisecond_speed
            <= 22.0
        )

        plausible_count = sum(
            (
                plausible_raw,
                plausible_centiseconds,
                plausible_milliseconds,
            )
        )

        if raw_value is None:
            classification = (
                "TIME_UNAVAILABLE"
            )

        elif plausible_count == 1:
            if plausible_raw:
                classification = (
                    "SECONDS_PLAUSIBLE"
                )
            elif plausible_centiseconds:
                classification = (
                    "CENTISECONDS_PLAUSIBLE"
                )
            else:
                classification = (
                    "MILLISECONDS_PLAUSIBLE"
                )

        elif plausible_count > 1:
            classification = (
                "MULTIPLE_UNITS_PLAUSIBLE"
            )

        else:
            classification = (
                "NO_UNIT_PLAUSIBLE"
            )

        unit_class_counts[
            classification
        ] += 1

        unit_rows.append(
            {
                **observation,
                "raw_seconds_speed_mps": (
                    round(
                        raw_seconds_speed,
                        6,
                    )
                    if raw_seconds_speed
                    is not None
                    else ""
                ),
                "centisecond_speed_mps": (
                    round(
                        centisecond_speed,
                        6,
                    )
                    if centisecond_speed
                    is not None
                    else ""
                ),
                "millisecond_speed_mps": (
                    round(
                        millisecond_speed,
                        6,
                    )
                    if millisecond_speed
                    is not None
                    else ""
                ),
                "unit_classification": (
                    classification
                ),
                "automatic_conversion_allowed": (
                    False
                ),
            }
        )

    timed_races = sum(
        count
        for classification, count
        in unit_class_counts.items()
        if classification
        != "TIME_UNAVAILABLE"
    )

    centisecond_races = (
        unit_class_counts[
            "CENTISECONDS_PLAUSIBLE"
        ]
    )

    centisecond_dominance_pct = (
        round(
            centisecond_races
            / timed_races
            * 100,
            6,
        )
        if timed_races
        else 0.0
    )

    checks = [
        {
            "check": (
                "SOURCE_ROWS_PROFILED"
            ),
            "passed": (
                rows == 879784
            ),
            "observed": rows,
        },
        {
            "check": (
                "RACE_TIME_CONSISTENCY"
            ),
            "passed": (
                not race_conflicts
            ),
            "observed": (
                sum(
                    race_conflicts.values()
                )
            ),
        },
        {
            "check": (
                "TIME_UNIT_IDENTIFIED"
            ),
            "passed": (
                centisecond_dominance_pct
                >= 99.0
            ),
            "observed": (
                f"centisecond_dominance_pct="
                f"{centisecond_dominance_pct}"
            ),
        },
        {
            "check": (
                "NO_AUTOMATIC_CONVERSION"
            ),
            "passed": all(
                not row[
                    "automatic_conversion_allowed"
                ]
                for row in unit_rows
            ),
            "observed": (
                "AUDIT_ONLY"
            ),
        },
    ]

    failed_checks = [
        check["check"]
        for check in checks
        if not check["passed"]
    ]

    if (
        centisecond_dominance_pct
        >= 99.0
        and not race_conflicts
    ):
        time_decision = (
            "WINNING_TIME_IS_CENTISECONDS_"
            "CONVERSION_TO_SECONDS_REQUIRED"
        )

        next_stage = (
            "Phase 1.5B.2 supersede the "
            "performance-facts snapshot with "
            "winning_time / 100.0 and preserve "
            "the raw source value."
        )

    else:
        time_decision = (
            "WINNING_TIME_UNIT_REMAINS_"
            "UNRESOLVED"
        )

        next_stage = (
            "Resolve mixed or conflicting "
            "winning-time units before benchmarks."
        )

    output_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_race_time_unit_"
            f"profile_v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5b_1_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5b_1_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_5b_1_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_5B_1_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_PERFORMANCE_FACT_"
            "UNIT_SEMANTICS_V0_1.md"
        )
    )

    write_csv(
        output_path,
        unit_rows,
    )

    write_csv(
        checks_path,
        checks,
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.5B.1 Performance-Fact "
            "Unit Semantics Audit"
        ),
        "generated_utc": utc_now(),
        "audit_version": AUDIT_VERSION,
        "status": (
            "PERFORMANCE_FACT_UNIT_"
            "SEMANTICS_PASS"
            if not failed_checks
            else
            "PERFORMANCE_FACT_UNIT_"
            "SEMANTICS_PARTIAL"
        ),
        "production_data_modified": False,
        "performance_facts_modified": False,
        "source_rows": rows,
        "distinct_races": (
            len(race_observations)
        ),
        "rows_with_winning_time": (
            rows_with_time
        ),
        "raw_time_format_counts": dict(
            sorted(
                raw_time_format_counts.items()
            )
        ),
        "raw_time_range_counts": dict(
            sorted(
                raw_time_range_counts.items()
            )
        ),
        "race_time_unit_counts": dict(
            sorted(
                unit_class_counts.items()
            )
        ),
        "centisecond_dominance_pct": (
            centisecond_dominance_pct
        ),
        "race_time_conflicts": (
            len(race_conflicts)
        ),
        "rows_with_margin": (
            rows_with_margin
        ),
        "rows_with_margin_lengths": (
            rows_with_margin_l
        ),
        "raw_margin_counts": dict(
            sorted(
                raw_margin_counts.items()
            )
        ),
        "raw_margin_length_counts": dict(
            sorted(
                raw_margin_l_counts.items()
            )
        ),
        "checks": checks,
        "failed_checks": failed_checks,
        "time_unit_decision": (
            time_decision
        ),
        "current_snapshot_status": (
            "SUPERSEDED_PENDING_"
            "UNIT_CORRECTION"
            if (
                "CENTISECONDS"
                in time_decision
            )
            else
            "BLOCKED_PENDING_"
            "UNIT_RESOLUTION"
        ),
        "next_stage": next_stage,
        "outputs": {
            "race_time_unit_profile": str(
                output_path.relative_to(
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
        """# EDGEiQ Performance-Fact Unit Semantics V0.1

## Winning-time rule

A numeric source value must never be labelled as seconds until its source unit has been validated.

The historical GraphQL warehouse may encode winning time in integer centiseconds.

Example:

`12383` represents `123.83 seconds` when the unit is centiseconds.

## Required fields

The corrected performance-facts warehouse must retain both:

- `official_winning_time_raw`
- `official_winning_time_source_unit`
- `official_winning_time_seconds`

## Immutability

The existing Phase 1.5B snapshot is not overwritten.

A corrected snapshot supersedes it while preserving the original snapshot and audit lineage.

## Benchmark boundary

No race-time benchmark may consume an unresolved or mislabelled time field.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.5B.1 Performance-Fact Unit Semantics Audit

Generated UTC: `{summary['generated_utc']}`

Status: **{summary['status']}**

- Source rows: **{rows:,}**
- Distinct races: **{len(race_observations):,}**
- Timed races: **{timed_races:,}**
- Centisecond-plausible races: **{centisecond_races:,}**
- Centisecond dominance: **{centisecond_dominance_pct}%**
- Race-level time conflicts: **{len(race_conflicts):,}**
- Performance facts modified: **False**

Decision: **{time_decision}**
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_5B_1_UNIT_SEMANTICS_PASS"
        if not failed_checks
        else
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_5B_1_UNIT_SEMANTICS_PARTIAL",
        flush=True,
    )

    print(
        f"DISTINCT_RACES="
        f"{len(race_observations)}",
        flush=True,
    )

    print(
        f"TIMED_RACES={timed_races}",
        flush=True,
    )

    print(
        f"CENTISECOND_PLAUSIBLE_RACES="
        f"{centisecond_races}",
        flush=True,
    )

    print(
        f"CENTISECOND_DOMINANCE_PCT="
        f"{centisecond_dominance_pct}",
        flush=True,
    )

    print(
        f"RACE_TIME_CONFLICTS="
        f"{len(race_conflicts)}",
        flush=True,
    )

    print(
        f"TIME_UNIT_DECISION="
        f"{time_decision}",
        flush=True,
    )

    print(
        f"SUMMARY={summary_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
