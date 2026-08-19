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
    / "phase1_5b_2"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_5b_2"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_5b_2"
)

AUDIT_VERSION = (
    "GOVERNED_RACE_TIME_UNIT_RESOLUTION_V0_1"
)

PROGRESS_INTERVAL = 100_000


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

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    try:
        number = float(
            match.group(0)
        )
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

    race_records: dict[
        str,
        dict[str, Any],
    ] = {}

    race_values: dict[
        str,
        set[tuple[str, str]],
    ] = defaultdict(set)

    source_rows = 0
    blank_context_rows = 0

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
                    "GOVERNED_TIME_AUDIT_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            context_key = race_context_key(
                row
            )

            if not context_key:
                blank_context_rows += 1
                continue

            distance_text = clean(
                row.get("distance")
            )

            time_text = clean(
                row.get("winning_time")
            )

            race_values[
                context_key
            ].add(
                (
                    distance_text,
                    time_text,
                )
            )

            if context_key not in race_records:
                race_records[
                    context_key
                ] = {
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
                    "distance_metres": (
                        parse_number(
                            distance_text
                        )
                    ),
                    "raw_winning_time": (
                        time_text
                    ),
                    "raw_winning_time_numeric": (
                        parse_number(
                            time_text
                        )
                    ),
                    "runner_rows": 0,
                }

            race_records[
                context_key
            ]["runner_rows"] += 1

    true_conflict_rows = []

    for context_key, values in sorted(
        race_values.items()
    ):
        if len(values) <= 1:
            continue

        record = race_records[
            context_key
        ]

        true_conflict_rows.append(
            {
                **record,
                "distinct_distance_time_pairs": (
                    len(values)
                ),
                "distance_time_pairs": (
                    " | ".join(
                        f"{distance}:{time}"
                        for distance, time
                        in sorted(values)
                    )
                ),
                "classification": (
                    "WITHIN_RACE_SOURCE_CONFLICT"
                ),
            }
        )

    conflict_keys = {
        row["race_context_key"]
        for row in true_conflict_rows
    }

    profile_rows = []
    classification_counts = Counter()

    for context_key, record in sorted(
        race_records.items()
    ):
        distance = record[
            "distance_metres"
        ]

        raw_time = record[
            "raw_winning_time_numeric"
        ]

        raw_seconds_speed = None
        centisecond_speed = None
        millisecond_speed = None

        if (
            distance is not None
            and raw_time is not None
            and distance > 0
            and raw_time > 0
        ):
            raw_seconds_speed = (
                distance / raw_time
            )

            centisecond_speed = (
                distance
                / (
                    raw_time / 100.0
                )
            )

            millisecond_speed = (
                distance
                / (
                    raw_time / 1000.0
                )
            )

        seconds_plausible = (
            raw_seconds_speed is not None
            and 8.0
            <= raw_seconds_speed
            <= 22.0
        )

        centiseconds_plausible = (
            centisecond_speed is not None
            and 8.0
            <= centisecond_speed
            <= 22.0
        )

        milliseconds_plausible = (
            millisecond_speed is not None
            and 8.0
            <= millisecond_speed
            <= 22.0
        )

        plausible_count = sum(
            (
                seconds_plausible,
                centiseconds_plausible,
                milliseconds_plausible,
            )
        )

        if context_key in conflict_keys:
            classification = (
                "WITHIN_RACE_SOURCE_CONFLICT"
            )

        elif raw_time is None:
            classification = (
                "TIME_UNAVAILABLE"
            )

        elif plausible_count == 1:
            if centiseconds_plausible:
                classification = (
                    "CENTISECONDS_CONFIRMED"
                )
            elif seconds_plausible:
                classification = (
                    "SECONDS_SOURCE_ANOMALY"
                )
            else:
                classification = (
                    "MILLISECONDS_SOURCE_ANOMALY"
                )

        elif plausible_count > 1:
            classification = (
                "MULTIPLE_UNITS_PLAUSIBLE"
            )

        else:
            classification = (
                "NO_UNIT_PLAUSIBLE"
            )

        classification_counts[
            classification
        ] += 1

        corrected_seconds = ""

        if classification == (
            "CENTISECONDS_CONFIRMED"
        ):
            corrected_seconds = round(
                raw_time / 100.0,
                6,
            )

        profile_rows.append(
            {
                **record,
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
                "governed_time_seconds": (
                    corrected_seconds
                ),
                "benchmark_eligible": (
                    classification
                    == "CENTISECONDS_CONFIRMED"
                ),
                "automatic_anomaly_conversion_allowed": (
                    False
                ),
            }
        )

    timed_races = sum(
        count
        for classification, count
        in classification_counts.items()
        if classification
        != "TIME_UNAVAILABLE"
    )

    confirmed_centisecond_races = (
        classification_counts[
            "CENTISECONDS_CONFIRMED"
        ]
    )

    anomaly_races = sum(
        classification_counts[
            classification
        ]
        for classification in (
            "SECONDS_SOURCE_ANOMALY",
            "MILLISECONDS_SOURCE_ANOMALY",
            "MULTIPLE_UNITS_PLAUSIBLE",
            "NO_UNIT_PLAUSIBLE",
            "WITHIN_RACE_SOURCE_CONFLICT",
        )
    )

    dominance_pct = (
        round(
            confirmed_centisecond_races
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
                source_rows == 879784
            ),
            "observed": source_rows,
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
                "WITHIN_RACE_TIME_CONSISTENCY"
            ),
            "passed": (
                len(
                    true_conflict_rows
                )
                == 0
            ),
            "observed": (
                len(
                    true_conflict_rows
                )
            ),
        },
        {
            "check": (
                "CENTISECOND_SOURCE_UNIT"
            ),
            "passed": (
                dominance_pct >= 99.9
            ),
            "observed": (
                f"confirmed="
                f"{confirmed_centisecond_races};"
                f"timed={timed_races};"
                f"pct={dominance_pct}"
            ),
        },
        {
            "check": (
                "ANOMALIES_QUARANTINED"
            ),
            "passed": all(
                not row[
                    "benchmark_eligible"
                ]
                for row in profile_rows
                if row[
                    "unit_classification"
                ]
                not in {
                    "CENTISECONDS_CONFIRMED",
                    "TIME_UNAVAILABLE",
                }
            ),
            "observed": (
                anomaly_races
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
                for row in profile_rows
            ),
            "observed": (
                "ALL_ANOMALY_CONVERSIONS_DISABLED"
            ),
        },
    ]

    failed_checks = [
        check["check"]
        for check in checks
        if not check["passed"]
    ]

    if (
        dominance_pct >= 99.9
        and not true_conflict_rows
    ):
        unit_decision = (
            "SOURCE_WINNING_TIME_UNIT_"
            "CONFIRMED_AS_CENTISECONDS"
        )

        current_snapshot_status = (
            "SUPERSEDED_PENDING_"
            "CORRECTED_MATERIALISATION"
        )

        next_stage = (
            "Phase 1.5B.3 materialise a corrected "
            "immutable performance-facts snapshot "
            "with raw centiseconds retained and "
            "governed seconds derived by division "
            "by 100; quarantine all anomalous races."
        )

    else:
        unit_decision = (
            "SOURCE_WINNING_TIME_UNIT_"
            "REMAINS_BLOCKED"
        )

        current_snapshot_status = (
            "BLOCKED"
        )

        next_stage = (
            "Resolve genuine within-race source "
            "conflicts before materialisation."
        )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    profile_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_governed_race_time_"
            f"profile_v0_1_{run_id}.csv"
        )
    )

    anomalies_path = (
        AUDIT_DIR
        / (
            "edgeiq_race_time_"
            f"anomalies_v0_1_{run_id}.csv"
        )
    )

    conflicts_path = (
        AUDIT_DIR
        / (
            "edgeiq_within_race_time_"
            f"conflicts_v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5b_2_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5b_2_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_5b_2_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_5B_2_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_GOVERNED_RACE_TIME_"
            "UNIT_RESOLUTION_V0_1.md"
        )
    )

    anomaly_rows = [
        row
        for row in profile_rows
        if row[
            "unit_classification"
        ]
        not in {
            "CENTISECONDS_CONFIRMED",
            "TIME_UNAVAILABLE",
        }
    ]

    write_csv(
        profile_path,
        profile_rows,
    )

    write_csv(
        anomalies_path,
        anomaly_rows,
    )

    write_csv(
        conflicts_path,
        true_conflict_rows,
    )

    write_csv(
        checks_path,
        checks,
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.5B.2 Governed Race-Time "
            "Unit Resolution"
        ),
        "generated_utc": utc_now(),
        "audit_version": (
            AUDIT_VERSION
        ),
        "status": (
            "GOVERNED_RACE_TIME_"
            "UNIT_RESOLUTION_PASS"
            if not failed_checks
            else
            "GOVERNED_RACE_TIME_"
            "UNIT_RESOLUTION_PARTIAL"
        ),
        "production_data_modified": False,
        "performance_facts_modified": False,
        "source_rows": source_rows,
        "distinct_governed_races": (
            len(race_records)
        ),
        "timed_races": timed_races,
        "confirmed_centisecond_races": (
            confirmed_centisecond_races
        ),
        "centisecond_dominance_pct": (
            dominance_pct
        ),
        "time_unavailable_races": (
            classification_counts[
                "TIME_UNAVAILABLE"
            ]
        ),
        "anomaly_races": anomaly_races,
        "within_race_source_conflicts": (
            len(true_conflict_rows)
        ),
        "classification_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),
        "checks": checks,
        "failed_checks": failed_checks,
        "time_unit_decision": (
            unit_decision
        ),
        "current_snapshot_status": (
            current_snapshot_status
        ),
        "next_stage": next_stage,
        "outputs": {
            "governed_race_time_profile": str(
                profile_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "anomalies": str(
                anomalies_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "within_race_conflicts": str(
                conflicts_path.relative_to(
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
        """# EDGEiQ Governed Race-Time Unit Resolution V0.1

## Race identity

Race-time consistency must use:

- race date
- jurisdiction
- track
- race number
- provider race ID

Provider race ID alone is not globally unique.

## Source unit

The historical GraphQL winning-time field is predominantly stored as centiseconds.

The governed conversion is:

seconds = raw centiseconds / 100

## Preservation

A corrected warehouse must retain:

- raw source value
- source unit
- governed seconds
- unit-rule version
- quality state

## Anomalies

Values that plausibly use another unit are quarantined.

They do not redefine the source contract and are not automatically converted.

## Benchmark rule

Only races classified as CENTISECONDS_CONFIRMED are benchmark eligible.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.5B.2 Governed Race-Time Unit Resolution

Generated UTC: `{summary['generated_utc']}`

Status: **{summary['status']}**

- Source rows: **{source_rows:,}**
- Governed race contexts: **{len(race_records):,}**
- Timed races: **{timed_races:,}**
- Confirmed centisecond races: **{confirmed_centisecond_races:,}**
- Centisecond dominance: **{dominance_pct}%**
- Anomalous races quarantined: **{anomaly_races:,}**
- Genuine within-race conflicts: **{len(true_conflict_rows):,}**

Decision: **{unit_decision}**
""",
        encoding="utf-8",
    )

    print(
        (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            "PHASE1_5B_2_GOVERNED_RACE_TIME_"
            "UNIT_RESOLUTION_PASS"
        )
        if not failed_checks
        else (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            "PHASE1_5B_2_GOVERNED_RACE_TIME_"
            "UNIT_RESOLUTION_PARTIAL"
        ),
        flush=True,
    )

    print(
        f"DISTINCT_GOVERNED_RACES="
        f"{len(race_records)}",
        flush=True,
    )

    print(
        f"TIMED_RACES={timed_races}",
        flush=True,
    )

    print(
        f"CONFIRMED_CENTISECOND_RACES="
        f"{confirmed_centisecond_races}",
        flush=True,
    )

    print(
        f"CENTISECOND_DOMINANCE_PCT="
        f"{dominance_pct}",
        flush=True,
    )

    print(
        f"ANOMALY_RACES="
        f"{anomaly_races}",
        flush=True,
    )

    print(
        f"WITHIN_RACE_SOURCE_CONFLICTS="
        f"{len(true_conflict_rows)}",
        flush=True,
    )

    print(
        f"TIME_UNIT_DECISION="
        f"{unit_decision}",
        flush=True,
    )

    print(
        f"SUMMARY={summary_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
