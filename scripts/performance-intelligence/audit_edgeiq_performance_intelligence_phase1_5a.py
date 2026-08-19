from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

HISTORICAL_RESULTS = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_historical_results_warehouse_v2_graphql.csv"
)

SECTIONAL_SOURCE = (
    ROOT
    / "public"
    / "data"
    / "racingcom_sectional_warehouse_v2.csv"
)

RAW_WAREHOUSE_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "raw"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_5a"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_5a"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_5a"
)

AUDIT_VERSION = (
    "CANONICAL_PERFORMANCE_EVIDENCE_"
    "SOURCE_CONTRACT_V0_1"
)

PROGRESS_INTERVAL = 100_000
SAMPLE_LIMIT = 250


PERFORMANCE_FIELD_CANDIDATES = {
    "race_date": (
        "race_date",
        "meeting_date",
        "date",
    ),
    "state": (
        "state",
        "jurisdiction",
        "state_code",
    ),
    "track": (
        "track",
        "track_name",
        "venue",
        "meeting_name",
    ),
    "course": (
        "course",
        "course_name",
        "track_course",
        "track_variant",
        "layout",
    ),
    "race_number": (
        "race_number",
        "race_no",
        "raceno",
        "race_num",
    ),
    "race_name": (
        "race_name",
        "name",
    ),
    "distance": (
        "distance",
        "distance_m",
        "distance_metres",
        "race_distance",
        "race_distance_metres",
    ),
    "race_class": (
        "race_class",
        "class",
        "class_name",
        "race_grade",
        "grade",
    ),
    "going": (
        "going",
        "track_rating",
        "track_condition",
        "track_condition_name",
        "condition",
    ),
    "rail": (
        "rail",
        "rail_position",
        "rail_setting",
        "rail_description",
    ),
    "official_time": (
        "official_time",
        "race_time",
        "winning_time",
        "official_race_time",
        "time",
    ),
    "horse_code": (
        "horse_code",
    ),
    "horse_name": (
        "horse",
        "horse_name",
        "runner_name",
    ),
    "finish_position": (
        "finish_position",
        "finishing_position",
        "finish",
        "position",
        "place",
    ),
    "margin": (
        "margin",
        "margin_lengths",
        "beaten_margin",
        "beaten_margin_lengths",
    ),
    "barrier": (
        "barrier",
        "barrier_number",
        "draw",
    ),
    "weight": (
        "weight",
        "weight_carried",
        "carried_weight",
    ),
    "jockey": (
        "jockey",
        "jockey_name",
    ),
    "trainer": (
        "trainer",
        "trainer_name",
    ),
    "sp": (
        "sp",
        "starting_price",
        "official_sp",
    ),
    "field_size": (
        "field_size",
        "runner_count",
        "starters",
    ),
    "race_status": (
        "race_status",
        "status",
    ),
}


SECTIONAL_FIELD_CANDIDATES = {
    "meeting_date": (
        "meeting_date",
        "race_date",
        "date",
    ),
    "track": (
        "track",
        "track_name",
    ),
    "race_number": (
        "race_no",
        "race_number",
        "raceno",
    ),
    "horse_name": (
        "horse_name",
        "horse",
        "runner_name",
    ),
    "position": (
        "position",
        "finish_position",
        "finish",
    ),
    "distance_run": (
        "dist_run",
        "distance_run",
        "distance",
    ),
    "layout_type": (
        "layout_type",
        "layout",
    ),
    "early_speed": (
        "early_speed",
    ),
    "mid_speed": (
        "mid_speed",
    ),
    "late_speed": (
        "late_speed",
    ),
    "peak_speed": (
        "peak_speed",
    ),
    "average_speed": (
        "avg_speed",
        "average_speed",
    ),
    "last_800": (
        "last_800",
        "last800",
        "l800",
    ),
    "last_600": (
        "last_600",
        "last600",
        "l600",
    ),
    "last_400": (
        "last_400",
        "last400",
        "l400",
    ),
    "last_200": (
        "last_200",
        "last200",
        "l200",
    ),
    "split_800_600": (
        "800_600",
        "split_800_600",
    ),
    "split_600_400": (
        "600_400",
        "split_600_400",
    ),
    "split_400_200": (
        "400_200",
        "split_400_200",
    ),
    "split_200_finish": (
        "200_finish",
        "200_f",
        "split_200_finish",
    ),
    "source_file": (
        "source_file",
    ),
    "source_url": (
        "source_url",
    ),
}


NUMERIC_PERFORMANCE_FIELDS = {
    "distance",
    "official_time",
    "finish_position",
    "margin",
    "barrier",
    "weight",
    "sp",
    "field_size",
}


NUMERIC_SECTIONAL_FIELDS = {
    "position",
    "distance_run",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "average_speed",
    "last_800",
    "last_600",
    "last_400",
    "last_200",
    "split_800_600",
    "split_600_400",
    "split_400_200",
    "split_200_finish",
}


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_column(value: Any) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        clean(value).lower(),
    ).strip("_")


def normalise_text(value: Any) -> str:
    return re.sub(
        r"[^A-Z0-9]+",
        "",
        clean(value).upper(),
    )


def normalise_date(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    )

    for date_format in formats:
        try:
            return datetime.strptime(
                text[:10],
                date_format,
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        text,
    )

    return match.group(1) if match else ""


def normalise_integer(value: Any) -> str:
    number = parse_number(value)

    if number is None:
        return ""

    if not number.is_integer():
        return ""

    return str(int(number))


def parse_number(value: Any) -> float | None:
    text = clean(value)

    if not text:
        return None

    text = text.replace(
        ",",
        "",
    )

    time_match = re.fullmatch(
        r"(\d+):(\d+(?:\.\d+)?)",
        text,
    )

    if time_match:
        minutes = float(
            time_match.group(1)
        )
        seconds = float(
            time_match.group(2)
        )

        number = (
            minutes * 60.0
            + seconds
        )

        return (
            number
            if math.isfinite(number)
            else None
        )

    number_match = re.search(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if not number_match:
        return None

    try:
        number = float(
            number_match.group(0)
        )
    except ValueError:
        return None

    return (
        number
        if math.isfinite(number)
        else None
    )


def latest_raw_snapshot() -> Path:
    candidates = sorted(
        (
            path
            for path
            in RAW_WAREHOUSE_ROOT.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and (
                path
                / "warehouse_manifest.json"
            ).exists()
        ),
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            "No immutable raw warehouse snapshot found."
        )

    return candidates[0]


def detect_fields(
    columns: list[str],
    candidate_map: dict[
        str,
        tuple[str, ...],
    ],
) -> dict[str, str]:
    lookup = {
        normalise_column(
            column
        ): column
        for column in columns
    }

    detected: dict[str, str] = {}

    for semantic, candidates in (
        candidate_map.items()
    ):
        detected[semantic] = ""

        for candidate in candidates:
            normalised = normalise_column(
                candidate
            )

            if normalised in lookup:
                detected[
                    semantic
                ] = lookup[
                    normalised
                ]
                break

    return detected


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


def profile_source(
    path: Path,
    candidates: dict[
        str,
        tuple[str, ...],
    ],
    numeric_fields: set[str],
    label: str,
) -> dict[str, Any]:
    rows = 0
    non_empty = Counter()
    numeric_valid = Counter()
    distinct_values: dict[
        str,
        set[str],
    ] = {}

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        columns = list(
            reader.fieldnames or []
        )

        detected = detect_fields(
            columns,
            candidates,
        )

        for semantic in detected:
            distinct_values[
                semantic
            ] = set()

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    f"{label}_PROFILE_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            for semantic, field in (
                detected.items()
            ):
                if not field:
                    continue

                value = clean(
                    row.get(field)
                )

                if not value:
                    continue

                non_empty[
                    semantic
                ] += 1

                if (
                    len(
                        distinct_values[
                            semantic
                        ]
                    )
                    < 50_000
                ):
                    distinct_values[
                        semantic
                    ].add(value)

                if (
                    semantic
                    in numeric_fields
                    and parse_number(
                        value
                    )
                    is not None
                ):
                    numeric_valid[
                        semantic
                    ] += 1

    coverage = {}

    for semantic, field in (
        detected.items()
    ):
        coverage[semantic] = {
            "physical_field": (
                field
            ),
            "present_rows": (
                non_empty[
                    semantic
                ]
            ),
            "coverage_pct": (
                round(
                    non_empty[
                        semantic
                    ]
                    / rows
                    * 100,
                    6,
                )
                if rows
                else 0.0
            ),
            "numeric_valid_rows": (
                numeric_valid[
                    semantic
                ]
            ),
            "numeric_valid_pct": (
                round(
                    numeric_valid[
                        semantic
                    ]
                    / rows
                    * 100,
                    6,
                )
                if rows
                else 0.0
            ),
            "distinct_value_count_capped": (
                len(
                    distinct_values[
                        semantic
                    ]
                )
            ),
        }

    return {
        "path": str(
            path.relative_to(
                ROOT
            )
        ).replace("\\", "/"),
        "rows": rows,
        "columns": columns,
        "detected_fields": (
            detected
        ),
        "coverage": coverage,
    }


def verify_performance_lineage(
    source_path: Path,
    canonical_path: Path,
    detected: dict[str, str],
) -> dict[str, Any]:
    rows_checked = 0
    source_row_matches = 0
    source_row_mismatches = 0
    identity_matches = 0
    identity_mismatches = 0
    samples: list[
        dict[str, Any]
    ] = []

    with source_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle, canonical_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as canonical_handle:
        source_reader = csv.DictReader(
            source_handle
        )

        canonical_reader = csv.DictReader(
            canonical_handle
        )

        for data_index, (
            source_row,
            canonical_row,
        ) in enumerate(
            zip(
                source_reader,
                canonical_reader,
                strict=False,
            ),
            start=1,
        ):
            rows_checked += 1

            if (
                data_index == 1
                or data_index
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "PERFORMANCE_LINEAGE_PROGRESS="
                    f"{data_index}",
                    flush=True,
                )

            expected_source_line = (
                data_index + 1
            )

            stored_source_line = (
                normalise_integer(
                    canonical_row.get(
                        "source_row_number"
                    )
                )
            )

            if (
                stored_source_line
                == str(
                    expected_source_line
                )
            ):
                source_row_matches += 1
            else:
                source_row_mismatches += 1

            source_date = (
                normalise_date(
                    source_row.get(
                        detected.get(
                            "race_date",
                            "",
                        )
                    )
                )
                if detected.get(
                    "race_date"
                )
                else ""
            )

            canonical_date = (
                normalise_date(
                    canonical_row.get(
                        "race_date"
                    )
                )
            )

            source_track = (
                normalise_text(
                    source_row.get(
                        detected.get(
                            "track",
                            "",
                        )
                    )
                )
                if detected.get(
                    "track"
                )
                else ""
            )

            canonical_track = (
                normalise_text(
                    canonical_row.get(
                        "track"
                    )
                )
            )

            source_race = (
                normalise_integer(
                    source_row.get(
                        detected.get(
                            "race_number",
                            "",
                        )
                    )
                )
                if detected.get(
                    "race_number"
                )
                else ""
            )

            canonical_race = (
                normalise_integer(
                    canonical_row.get(
                        "race_number"
                    )
                )
            )

            source_horse = (
                normalise_text(
                    source_row.get(
                        detected.get(
                            "horse_name",
                            "",
                        )
                    )
                )
                if detected.get(
                    "horse_name"
                )
                else ""
            )

            canonical_horse = (
                normalise_text(
                    canonical_row.get(
                        "horse_name"
                    )
                )
            )

            components = (
                source_date
                == canonical_date,
                source_track
                == canonical_track,
                source_race
                == canonical_race,
                source_horse
                == canonical_horse,
            )

            if all(components):
                identity_matches += 1
            else:
                identity_mismatches += 1

                if len(samples) < SAMPLE_LIMIT:
                    samples.append(
                        {
                            "data_index": (
                                data_index
                            ),
                            "expected_source_line": (
                                expected_source_line
                            ),
                            "stored_source_line": (
                                stored_source_line
                            ),
                            "source_date": (
                                source_date
                            ),
                            "canonical_date": (
                                canonical_date
                            ),
                            "source_track": (
                                source_track
                            ),
                            "canonical_track": (
                                canonical_track
                            ),
                            "source_race_number": (
                                source_race
                            ),
                            "canonical_race_number": (
                                canonical_race
                            ),
                            "source_horse": (
                                source_horse
                            ),
                            "canonical_horse": (
                                canonical_horse
                            ),
                        }
                    )

    return {
        "rows_checked": (
            rows_checked
        ),
        "source_row_matches": (
            source_row_matches
        ),
        "source_row_mismatches": (
            source_row_mismatches
        ),
        "source_row_match_pct": (
            round(
                source_row_matches
                / rows_checked
                * 100,
                6,
            )
            if rows_checked
            else 0.0
        ),
        "identity_matches": (
            identity_matches
        ),
        "identity_mismatches": (
            identity_mismatches
        ),
        "identity_match_pct": (
            round(
                identity_matches
                / rows_checked
                * 100,
                6,
            )
            if rows_checked
            else 0.0
        ),
        "mismatch_samples": (
            samples
        ),
    }


def verify_sectional_lineage(
    source_path: Path,
    canonical_path: Path,
    detected: dict[str, str],
) -> dict[str, Any]:
    rows_checked = 0
    source_row_matches = 0
    source_row_mismatches = 0
    identity_matches = 0
    identity_mismatches = 0
    samples: list[
        dict[str, Any]
    ] = []

    with source_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle, canonical_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as canonical_handle:
        source_reader = csv.DictReader(
            source_handle
        )

        canonical_reader = csv.DictReader(
            canonical_handle
        )

        canonical_iterator = iter(
            canonical_reader
        )

        canonical_row = next(
            canonical_iterator,
            None,
        )

        for source_data_index, source_row in enumerate(
            source_reader,
            start=1,
        ):
            if canonical_row is None:
                break

            source_line_number = (
                source_data_index + 1
            )

            canonical_source_line = (
                normalise_integer(
                    canonical_row.get(
                        "source_row_number"
                    )
                )
            )

            if (
                canonical_source_line
                != str(
                    source_line_number
                )
            ):
                continue

            rows_checked += 1
            source_row_matches += 1

            if (
                rows_checked == 1
                or rows_checked
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "SECTIONAL_LINEAGE_PROGRESS="
                    f"{rows_checked}",
                    flush=True,
                )

            source_date = (
                normalise_date(
                    source_row.get(
                        detected.get(
                            "meeting_date",
                            "",
                        )
                    )
                )
                if detected.get(
                    "meeting_date"
                )
                else ""
            )

            canonical_date = (
                normalise_date(
                    canonical_row.get(
                        "race_date"
                    )
                )
            )

            source_track = (
                normalise_text(
                    source_row.get(
                        detected.get(
                            "track",
                            "",
                        )
                    )
                )
                if detected.get(
                    "track"
                )
                else ""
            )

            canonical_track = (
                normalise_text(
                    canonical_row.get(
                        "canonical_track"
                    )
                )
            )

            source_race = (
                normalise_integer(
                    source_row.get(
                        detected.get(
                            "race_number",
                            "",
                        )
                    )
                )
                if detected.get(
                    "race_number"
                )
                else ""
            )

            canonical_race = (
                normalise_integer(
                    canonical_row.get(
                        "race_number"
                    )
                )
            )

            source_horse = (
                normalise_text(
                    source_row.get(
                        detected.get(
                            "horse_name",
                            "",
                        )
                    )
                )
                if detected.get(
                    "horse_name"
                )
                else ""
            )

            canonical_horse = (
                normalise_text(
                    canonical_row.get(
                        "canonical_horse"
                    )
                )
            )

            components = (
                source_date
                == canonical_date,
                source_track
                == canonical_track,
                source_race
                == canonical_race,
                source_horse
                == canonical_horse,
            )

            if all(components):
                identity_matches += 1
            else:
                identity_mismatches += 1

                if len(samples) < SAMPLE_LIMIT:
                    samples.append(
                        {
                            "source_line_number": (
                                source_line_number
                            ),
                            "canonical_source_line": (
                                canonical_source_line
                            ),
                            "source_date": (
                                source_date
                            ),
                            "canonical_date": (
                                canonical_date
                            ),
                            "source_track": (
                                source_track
                            ),
                            "canonical_track": (
                                canonical_track
                            ),
                            "source_race_number": (
                                source_race
                            ),
                            "canonical_race_number": (
                                canonical_race
                            ),
                            "source_horse": (
                                source_horse
                            ),
                            "canonical_horse": (
                                canonical_horse
                            ),
                        }
                    )

            canonical_row = next(
                canonical_iterator,
                None,
            )

        if canonical_row is not None:
            source_row_mismatches += 1

            for _ in canonical_iterator:
                source_row_mismatches += 1

    return {
        "rows_checked": (
            rows_checked
        ),
        "source_row_matches": (
            source_row_matches
        ),
        "source_row_mismatches": (
            source_row_mismatches
        ),
        "identity_matches": (
            identity_matches
        ),
        "identity_mismatches": (
            identity_mismatches
        ),
        "identity_match_pct": (
            round(
                identity_matches
                / rows_checked
                * 100,
                6,
            )
            if rows_checked
            else 0.0
        ),
        "mismatch_samples": (
            samples
        ),
    }


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

    if not HISTORICAL_RESULTS.exists():
        raise FileNotFoundError(
            HISTORICAL_RESULTS
        )

    if not SECTIONAL_SOURCE.exists():
        raise FileNotFoundError(
            SECTIONAL_SOURCE
        )

    raw_snapshot = (
        latest_raw_snapshot()
    )

    canonical_performance = (
        raw_snapshot
        / "canonical_performance_evidence.csv"
    )

    canonical_sectional = (
        raw_snapshot
        / "canonical_sectional_evidence.csv"
    )

    print(
        "PHASE1_5A_PROFILE_HISTORICAL_SOURCE_START",
        flush=True,
    )

    performance_profile = profile_source(
        HISTORICAL_RESULTS,
        PERFORMANCE_FIELD_CANDIDATES,
        NUMERIC_PERFORMANCE_FIELDS,
        "HISTORICAL_SOURCE",
    )

    print(
        "PHASE1_5A_PROFILE_SECTIONAL_SOURCE_START",
        flush=True,
    )

    sectional_profile = profile_source(
        SECTIONAL_SOURCE,
        SECTIONAL_FIELD_CANDIDATES,
        NUMERIC_SECTIONAL_FIELDS,
        "SECTIONAL_SOURCE",
    )

    print(
        "PHASE1_5A_VERIFY_PERFORMANCE_LINEAGE_START",
        flush=True,
    )

    performance_lineage = (
        verify_performance_lineage(
            HISTORICAL_RESULTS,
            canonical_performance,
            performance_profile[
                "detected_fields"
            ],
        )
    )

    print(
        "PHASE1_5A_VERIFY_SECTIONAL_LINEAGE_START",
        flush=True,
    )

    sectional_lineage = (
        verify_sectional_lineage(
            SECTIONAL_SOURCE,
            canonical_sectional,
            sectional_profile[
                "detected_fields"
            ],
        )
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    field_catalog_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_canonical_performance_"
            f"source_field_catalog_v0_1_{run_id}.csv"
        )
    )

    performance_mismatch_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_source_"
            f"lineage_mismatches_v0_1_{run_id}.csv"
        )
    )

    sectional_mismatch_path = (
        AUDIT_DIR
        / (
            "edgeiq_sectional_source_"
            f"lineage_mismatches_v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5a_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5a_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_5a_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_5A_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_CANONICAL_PERFORMANCE_"
            "EVIDENCE_SOURCE_CONTRACT_V0_1.md"
        )
    )

    field_catalog_rows = []

    for source_name, profile in (
        (
            "historical_results",
            performance_profile,
        ),
        (
            "sectional_source",
            sectional_profile,
        ),
    ):
        for semantic, details in (
            profile["coverage"].items()
        ):
            field_catalog_rows.append(
                {
                    "source_name": (
                        source_name
                    ),
                    "source_path": (
                        profile["path"]
                    ),
                    "semantic_field": (
                        semantic
                    ),
                    "physical_field": (
                        details[
                            "physical_field"
                        ]
                    ),
                    "source_rows": (
                        profile["rows"]
                    ),
                    "present_rows": (
                        details[
                            "present_rows"
                        ]
                    ),
                    "coverage_pct": (
                        details[
                            "coverage_pct"
                        ]
                    ),
                    "numeric_valid_rows": (
                        details[
                            "numeric_valid_rows"
                        ]
                    ),
                    "numeric_valid_pct": (
                        details[
                            "numeric_valid_pct"
                        ]
                    ),
                    "distinct_value_count_capped": (
                        details[
                            "distinct_value_count_capped"
                        ]
                    ),
                }
            )

    write_csv(
        field_catalog_path,
        field_catalog_rows,
    )

    write_csv(
        performance_mismatch_path,
        performance_lineage[
            "mismatch_samples"
        ],
    )

    write_csv(
        sectional_mismatch_path,
        sectional_lineage[
            "mismatch_samples"
        ],
    )

    performance_detected = (
        performance_profile[
            "detected_fields"
        ]
    )

    sectional_detected = (
        sectional_profile[
            "detected_fields"
        ]
    )

    mandatory_performance_fields = (
        "race_date",
        "track",
        "race_number",
        "horse_name",
        "distance",
        "official_time",
        "finish_position",
    )

    missing_mandatory_fields = [
        field
        for field
        in mandatory_performance_fields
        if not performance_detected.get(
            field
        )
    ]

    optional_hierarchy_fields = (
        "course",
        "race_class",
        "going",
        "rail",
    )

    available_optional_fields = [
        field
        for field
        in optional_hierarchy_fields
        if performance_detected.get(
            field
        )
    ]

    true_sectional_time_fields = (
        "last_800",
        "last_600",
        "last_400",
        "last_200",
        "split_800_600",
        "split_600_400",
        "split_400_200",
        "split_200_finish",
    )

    available_true_sectional_fields = [
        field
        for field
        in true_sectional_time_fields
        if sectional_detected.get(
            field
        )
    ]

    speed_evidence_fields = (
        "early_speed",
        "mid_speed",
        "late_speed",
        "peak_speed",
        "average_speed",
    )

    available_speed_fields = [
        field
        for field
        in speed_evidence_fields
        if sectional_detected.get(
            field
        )
    ]

    checks = [
        {
            "check": (
                "HISTORICAL_SOURCE_ROW_COUNT"
            ),
            "passed": (
                performance_profile[
                    "rows"
                ]
                == 879784
            ),
            "observed": (
                performance_profile[
                    "rows"
                ]
            ),
        },
        {
            "check": (
                "PERFORMANCE_LINEAGE_ROW_MATCH"
            ),
            "passed": (
                performance_lineage[
                    "source_row_mismatches"
                ]
                == 0
            ),
            "observed": (
                f"matches="
                f"{performance_lineage['source_row_matches']};"
                f"mismatches="
                f"{performance_lineage['source_row_mismatches']}"
            ),
        },
        {
            "check": (
                "PERFORMANCE_LINEAGE_"
                "IDENTITY_MATCH"
            ),
            "passed": (
                performance_lineage[
                    "identity_mismatches"
                ]
                == 0
            ),
            "observed": (
                f"matches="
                f"{performance_lineage['identity_matches']};"
                f"mismatches="
                f"{performance_lineage['identity_mismatches']}"
            ),
        },
        {
            "check": (
                "SECTIONAL_LINEAGE_ROW_MATCH"
            ),
            "passed": (
                sectional_lineage[
                    "source_row_mismatches"
                ]
                == 0
                and sectional_lineage[
                    "rows_checked"
                ]
                == 103766
            ),
            "observed": (
                f"checked="
                f"{sectional_lineage['rows_checked']};"
                f"mismatches="
                f"{sectional_lineage['source_row_mismatches']}"
            ),
        },
        {
            "check": (
                "SECTIONAL_LINEAGE_"
                "IDENTITY_MATCH"
            ),
            "passed": (
                sectional_lineage[
                    "identity_mismatches"
                ]
                == 0
            ),
            "observed": (
                f"matches="
                f"{sectional_lineage['identity_matches']};"
                f"mismatches="
                f"{sectional_lineage['identity_mismatches']}"
            ),
        },
        {
            "check": (
                "MANDATORY_PERFORMANCE_FIELDS"
            ),
            "passed": (
                not missing_mandatory_fields
            ),
            "observed": (
                " | ".join(
                    missing_mandatory_fields
                )
                or "ALL_PRESENT"
            ),
        },
        {
            "check": (
                "TRUE_SECTIONAL_TIME_FIELDS"
            ),
            "passed": (
                len(
                    available_true_sectional_fields
                )
                > 0
            ),
            "observed": (
                " | ".join(
                    available_true_sectional_fields
                )
                or "NONE"
            ),
        },
        {
            "check": (
                "SPEED_EVIDENCE_FIELDS"
            ),
            "passed": (
                len(
                    available_speed_fields
                )
                > 0
            ),
            "observed": (
                " | ".join(
                    available_speed_fields
                )
                or "NONE"
            ),
        },
        {
            "check": (
                "NO_PERFORMANCE_VALUES_"
                "FABRICATED"
            ),
            "passed": True,
            "observed": (
                "SOURCE_CONTRACT_AUDIT_ONLY"
            ),
        },
    ]

    failed_checks = [
        check["check"]
        for check in checks
        if not check["passed"]
    ]

    materialisation_eligible = (
        performance_lineage[
            "source_row_mismatches"
        ]
        == 0
        and performance_lineage[
            "identity_mismatches"
        ]
        == 0
        and not missing_mandatory_fields
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.5A Canonical Performance "
            "Evidence Source Contract Audit"
        ),
        "generated_utc": (
            utc_now()
        ),
        "audit_version": (
            AUDIT_VERSION
        ),
        "status": (
            "PERFORMANCE_EVIDENCE_"
            "SOURCE_CONTRACT_PASS"
            if materialisation_eligible
            else
            "PERFORMANCE_EVIDENCE_"
            "SOURCE_CONTRACT_PARTIAL"
        ),
        "production_data_modified": False,
        "performance_values_materialised": (
            False
        ),
        "raw_warehouse_snapshot_id": (
            raw_snapshot.name
        ),
        "performance_source_profile": (
            performance_profile
        ),
        "sectional_source_profile": (
            sectional_profile
        ),
        "performance_lineage": (
            performance_lineage
        ),
        "sectional_lineage": (
            sectional_lineage
        ),
        "missing_mandatory_performance_fields": (
            missing_mandatory_fields
        ),
        "available_optional_hierarchy_fields": (
            available_optional_fields
        ),
        "available_true_sectional_fields": (
            available_true_sectional_fields
        ),
        "available_speed_evidence_fields": (
            available_speed_fields
        ),
        "canonical_performance_materialisation_eligible": (
            materialisation_eligible
        ),
        "checks": checks,
        "failed_checks": (
            failed_checks
        ),
        "next_stage": (
            "Phase 1.5B materialise immutable "
            "canonical performance facts from "
            "the validated source-row lineage."
            if materialisation_eligible
            else
            "Resolve missing mandatory source "
            "fields before canonical performance "
            "materialisation."
        ),
        "outputs": {
            "field_catalog": str(
                field_catalog_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "performance_lineage_mismatches": str(
                performance_mismatch_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "sectional_lineage_mismatches": str(
                sectional_mismatch_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "architecture": str(
                architecture_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
        },
    }

    write_csv(
        checks_path,
        checks,
    )

    write_json(
        summary_path,
        summary,
    )

    write_json(
        latest_path,
        summary,
    )

    architecture_path.write_text(
        """# EDGEiQ Canonical Performance Evidence Source Contract V0.1

## Purpose

The immutable raw warehouse currently contains canonical identity and lineage.

Phase 1.5A verifies the upstream evidence required to materialise official performance facts.

## Lineage rule

Every canonical performance fact must be traceable to:

- immutable performance ID
- source evidence ID
- source file
- source row number
- source file hash
- source field
- evidence version
- materialisation version

## Performance facts

Eligible raw facts include:

- distance
- class
- going
- rail
- official time
- finish position
- official margin
- barrier
- weight
- jockey
- trainer
- starting price

## Sectional evidence

Speed-derived fields and official split times are separate evidence types.

Speed estimates must not be relabelled as official sectional times.

If official split times are absent, the canonical warehouse records them as unavailable.

## Prohibited behaviour

The materialiser may not:

- estimate missing distance
- infer class from race name
- fabricate official time
- convert speed into an official split
- invent rail or going
- silently drop unavailable fields

## Next phase

Phase 1.5B may materialise only source fields that pass this contract.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.5A Canonical Performance Evidence Source Contract

Generated UTC: `{summary['generated_utc']}`

Status: **{summary['status']}**

- Historical source rows: **{performance_profile['rows']:,}**
- Performance source-row matches: **{performance_lineage['source_row_matches']:,}**
- Performance identity matches: **{performance_lineage['identity_matches']:,}**
- Sectional source rows linked: **{sectional_lineage['rows_checked']:,}**
- Sectional identity matches: **{sectional_lineage['identity_matches']:,}**
- Missing mandatory performance fields: **{', '.join(missing_mandatory_fields) if missing_mandatory_fields else 'None'}**
- Optional hierarchy fields available: **{', '.join(available_optional_fields) if available_optional_fields else 'None'}**
- Official sectional time fields available: **{', '.join(available_true_sectional_fields) if available_true_sectional_fields else 'None'}**
- Speed evidence fields available: **{', '.join(available_speed_fields) if available_speed_fields else 'None'}**
- Materialisation eligible: **{materialisation_eligible}**
- Performance values materialised: **False**

Production data was not modified.
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_5A_PERFORMANCE_EVIDENCE_"
        "SOURCE_CONTRACT_PASS"
        if materialisation_eligible
        else
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_5A_PERFORMANCE_EVIDENCE_"
        "SOURCE_CONTRACT_PARTIAL",
        flush=True,
    )

    print(
        f"PERFORMANCE_SOURCE_ROWS="
        f"{performance_profile['rows']}",
        flush=True,
    )

    print(
        f"PERFORMANCE_LINEAGE_MATCHES="
        f"{performance_lineage['identity_matches']}",
        flush=True,
    )

    print(
        f"PERFORMANCE_LINEAGE_MISMATCHES="
        f"{performance_lineage['identity_mismatches']}",
        flush=True,
    )

    print(
        f"SECTIONAL_LINEAGE_MATCHES="
        f"{sectional_lineage['identity_matches']}",
        flush=True,
    )

    print(
        "MISSING_MANDATORY_FIELDS="
        + "|".join(
            missing_mandatory_fields
        ),
        flush=True,
    )

    print(
        "AVAILABLE_OPTIONAL_HIERARCHY_FIELDS="
        + "|".join(
            available_optional_fields
        ),
        flush=True,
    )

    print(
        "AVAILABLE_TRUE_SECTIONAL_FIELDS="
        + "|".join(
            available_true_sectional_fields
        ),
        flush=True,
    )

    print(
        "AVAILABLE_SPEED_FIELDS="
        + "|".join(
            available_speed_fields
        ),
        flush=True,
    )

    print(
        f"MATERIALISATION_ELIGIBLE="
        f"{materialisation_eligible}",
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
