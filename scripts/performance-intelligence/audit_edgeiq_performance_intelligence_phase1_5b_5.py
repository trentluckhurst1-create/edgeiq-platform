from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


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
    / "phase1_5b_5"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_5b_5"
)

PROGRESS_INTERVAL = 100000


def clean(value):
    return str(value or "").strip()


def parse_distance(value):
    text = clean(value)

    if not text:
        return None

    match = re.search(
        r"(\d+)",
        text
    )

    if not match:
        return None

    return int(match.group(1))


def parse_time(value):
    text = clean(value)

    if not text:
        return None

    match = re.search(
        r"(\d+(?:\.\d+)?)",
        text
    )

    if not match:
        return None

    return float(match.group(1))


def normalise_text(value):
    return re.sub(
        r"\s+",
        " ",
        clean(value).upper()
    )


def race_key(row):
    return "|".join(
        [
            clean(row.get("race_id")),
            clean(row.get("race_date")),
            normalise_text(row.get("track")),
            clean(row.get("race_no")),
        ]
    )


def write_csv(path, rows):
    if not rows:
        path.write_text(
            "",
            encoding="utf-8"
        )
        return

    fields = list(rows[0].keys())

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    path.write_text(
        json.dumps(
            payload,
            indent=2
        ),
        encoding="utf-8"
    )


def main():

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    race_data = {}

    source_rows = 0

    print(
        "PHASE1_5B_5_NORMALISATION_START",
        flush=True
    )

    with SOURCE.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore"
    ) as handle:

        reader = csv.DictReader(handle)

        for row_number, row in enumerate(
            reader,
            start=1
        ):

            source_rows += 1

            if (
                row_number == 1
                or row_number % PROGRESS_INTERVAL == 0
            ):
                print(
                    f"NORMALISATION_PROGRESS={row_number}",
                    flush=True
                )

            key = race_key(row)

            if key not in race_data:

                race_data[key] = {
                    "race_id": clean(
                        row.get("race_id")
                    ),
                    "race_date": clean(
                        row.get("race_date")
                    ),
                    "track": clean(
                        row.get("track")
                    ),
                    "race_no": clean(
                        row.get("race_no")
                    ),
                    "distance_raw": clean(
                        row.get("distance")
                    ),
                    "distance_metres": parse_distance(
                        row.get("distance")
                    ),
                    "time_raw": clean(
                        row.get("winning_time")
                    ),
                    "time_raw_numeric": parse_time(
                        row.get("winning_time")
                    ),
                    "runner_rows": 0,
                    "missing_time_rows": 0,
                    "missing_distance_rows": 0,
                }

            race_data[key]["runner_rows"] += 1


    results = []

    counters = Counter()


    for key, race in race_data.items():

        distance = race["distance_metres"]

        raw_time = race["time_raw_numeric"]

        if distance is None:

            distance_state = (
                "MISSING_OR_INVALID"
            )

        else:

            distance_state = (
                "VALID"
            )


        if raw_time is None:

            time_state = (
                "MISSING"
            )

            governed_seconds = ""

        else:

            time_state = (
                "CENTISECONDS_SOURCE"
            )

            governed_seconds = round(
                raw_time / 100,
                6
            )


        eligible = (
            distance is not None
            and raw_time is not None
        )


        if eligible:
            counters[
                "benchmark_eligible"
            ] += 1

        else:
            counters[
                "benchmark_blocked"
            ] += 1


        counters[
            "distance_" + distance_state
        ] += 1

        counters[
            "time_" + time_state
        ] += 1


        results.append(
            {
                "race_context_key": key,
                "race_id": race["race_id"],
                "race_date": race["race_date"],
                "track": race["track"],
                "race_no": race["race_no"],
                "raw_distance": race["distance_raw"],
                "distance_metres": distance or "",
                "distance_state": distance_state,
                "raw_winning_time": race["time_raw"],
                "winning_time_seconds": governed_seconds,
                "time_state": time_state,
                "benchmark_eligible": eligible,
            }
        )


    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )


    output_csv = (
        PROTOTYPE_DIR
        /
        f"edgeiq_race_time_distance_normalisation_v0_1_{timestamp}.csv"
    )


    summary = {
        "audit_name":
            "EDGEiQ Performance Intelligence Phase 1.5B.5 Time Distance Normalisation",
        "generated_utc":
            datetime.now(timezone.utc).isoformat(),
        "production_data_modified":
            False,
        "source_rows":
            source_rows,
        "distinct_races":
            len(results),
        "distance_valid_races":
            counters["distance_VALID"],
        "distance_invalid_races":
            counters["distance_MISSING_OR_INVALID"],
        "time_converted_races":
            counters["time_CENTISECONDS_SOURCE"],
        "time_missing_races":
            counters["time_MISSING"],
        "benchmark_eligible_races":
            counters["benchmark_eligible"],
        "benchmark_blocked_races":
            counters["benchmark_blocked"],
        "decision":
            "READY_FOR_PERFORMANCE_FACT_MATERIALISATION"
            if counters["benchmark_eligible"] > 0
            else
            "BLOCKED",
    }


    write_csv(
        output_csv,
        results
    )


    summary_path = (
        AUDIT_DIR
        /
        "edgeiq_performance_intelligence_phase1_5b_5_latest.json"
    )

    write_json(
        summary_path,
        summary
    )


    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1_5B_5_PASS",
        flush=True
    )

    print(
        f"DISTINCT_RACES={len(results)}",
        flush=True
    )

    print(
        f"BENCHMARK_ELIGIBLE={counters['benchmark_eligible']}",
        flush=True
    )

    print(
        f"SUMMARY={summary_path}",
        flush=True
    )


if __name__ == "__main__":
    main()
