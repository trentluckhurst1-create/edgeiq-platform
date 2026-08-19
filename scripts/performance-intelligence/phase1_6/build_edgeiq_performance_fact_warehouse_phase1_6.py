from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_historical_results_warehouse_v2_graphql.csv"
)

OUTPUT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_6"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_6"
)

PROGRESS_INTERVAL = 100000


def clean(value):
    return str(value or "").strip()


def parse_number(value):
    text = clean(value)

    if not text:
        return None

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text
    )

    if not match:
        return None

    return float(match.group())


def parse_distance(value):
    number = parse_number(value)

    if number is None:
        return None

    return int(number)


def parse_weight(value):
    return parse_number(value)


def parse_margin(value):
    return parse_number(value)


def parse_time(value):
    number = parse_number(value)

    if number is None:
        return None

    return round(
        number / 100,
        6
    )


def normalise_text(value):
    return re.sub(
        r"\s+",
        " ",
        clean(value)
    )


def performance_id(race_id, runner_id):
    raw = (
        f"{race_id}|{runner_id}"
    )

    return (
        "pf_"
        +
        hashlib.sha256(
            raw.encode("utf-8")
        )
        .hexdigest()[:24]
    )


def write_csv(path, rows):

    fields = list(
        rows[0].keys()
    )

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


def write_json(path, data):

    path.write_text(
        json.dumps(
            data,
            indent=2
        ),
        encoding="utf-8"
    )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = (
        OUTPUT_DIR
        /
        f"edgeiq_performance_fact_v0_1_{timestamp}.csv"
    )

    rows_out = []

    source_rows = 0
    complete_rows = 0
    incomplete_rows = 0
    benchmark_eligible = 0

    print(
        "PHASE1_6_PERFORMANCE_FACT_BUILD_START",
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
                    f"PERFORMANCE_FACT_PROGRESS={row_number}",
                    flush=True
                )


            distance = parse_distance(
                row.get("distance")
            )

            governed_seconds = parse_time(
                row.get("winning_time")
            )


            if (
                distance is not None
                and governed_seconds is not None
            ):

                quality_state = (
                    "COMPLETE"
                )

                benchmark_state = True

                benchmark_eligible += 1
                complete_rows += 1

            else:

                quality_state = (
                    "SOURCE_INCOMPLETE"
                )

                benchmark_state = False

                incomplete_rows += 1



            output = {

                "performance_fact_id":
                    performance_id(
                        row.get("race_id"),
                        row.get("runner_id")
                    ),

                "source_version":
                    "EDGEIQ_RESULTS_WAREHOUSE_V2",

                "generated_timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),


                "race_id":
                    row.get("race_id"),

                "runner_id":
                    row.get("runner_id"),


                "race_date":
                    row.get("race_date"),

                "track":
                    row.get("track"),

                "state":
                    row.get("state"),

                "race_number":
                    row.get("race_no"),

                "race_name":
                    row.get("race_name"),

                "race_class":
                    row.get("race_class"),


                "distance_raw":
                    row.get("distance"),

                "distance_metres":
                    distance or "",


                "track_condition":
                    row.get("track_condition"),

                "track_rating":
                    row.get("track_rating"),

                "rail_position":
                    row.get("rail_position"),

                "weather":
                    row.get("weather"),


                "horse":
                    row.get("horse"),

                "horse_code":
                    row.get("horse_code"),


                "trainer":
                    row.get("trainer"),

                "trainer_code":
                    row.get("trainer_code"),


                "jockey":
                    row.get("jockey"),

                "jockey_code":
                    row.get("jockey_code"),


                "barrier":
                    row.get("barrier"),

                "weight":
                    parse_weight(
                        row.get("weight")
                    ) or "",


                "finish_position":
                    row.get("finish"),


                "margin_raw":
                    row.get("margin"),

                "margin_lengths":
                    parse_margin(
                        row.get("margin_l")
                    ) or "",


                "starting_price":
                    row.get("starting_price"),

                "starting_price_decimal":
                    row.get(
                        "starting_price_decimal"
                    ),


                "raw_winning_time":
                    row.get("winning_time"),

                "governed_time_seconds":
                    governed_seconds or "",

                "time_unit":
                    (
                        "CENTISECONDS"
                        if governed_seconds
                        else ""
                    ),


                "benchmark_eligible":
                    benchmark_state,

                "quality_state":
                    quality_state,

            }


            rows_out.append(
                output
            )


    write_csv(
        output_file,
        rows_out
    )


    audit = {

        "audit_name":
            "EDGEiQ Performance Intelligence Phase 1.6 Performance Fact Materialisation",

        "generated_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "production_data_modified":
            False,

        "source_rows":
            source_rows,

        "performance_fact_rows":
            len(rows_out),

        "complete_rows":
            complete_rows,

        "incomplete_rows":
            incomplete_rows,

        "benchmark_eligible_rows":
            benchmark_eligible,

        "output":
            str(
                output_file.relative_to(ROOT)
            ).replace(
                "\\",
                "/"
            ),

        "status":
            "PERFORMANCE_FACT_MATERIALISED"

    }


    audit_file = (
        AUDIT_DIR
        /
        "edgeiq_performance_fact_phase1_6_latest.json"
    )


    write_json(
        audit_file,
        audit
    )


    print(
        "EDGEIQ_PERFORMANCE_FACT_PHASE1_6_PASS",
        flush=True
    )

    print(
        f"PERFORMANCE_FACT_ROWS={len(rows_out)}",
        flush=True
    )

    print(
        f"BENCHMARK_ELIGIBLE_ROWS={benchmark_eligible}",
        flush=True
    )

    print(
        f"AUDIT={audit_file}",
        flush=True
    )


if __name__ == "__main__":
    main()
