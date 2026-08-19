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

RAW_WAREHOUSE_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "raw"
)

DIMENSION_WAREHOUSE_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "dimensions"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_5"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_5"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_5"
)

AUDIT_VERSION = (
    "BENCHMARK_EVIDENCE_READINESS_V0_1"
)

PROGRESS_INTERVAL = 100_000

FIELD_CANDIDATES = {
    "performance_id": (
        "performance_id",
    ),
    "race_id": (
        "race_id",
    ),
    "race_date": (
        "race_date",
        "date",
    ),
    "state": (
        "state",
        "jurisdiction",
    ),
    "track": (
        "track",
        "canonical_track",
        "venue",
    ),
    "course": (
        "course",
        "course_name",
        "track_course",
        "track_variant",
    ),
    "race_number": (
        "race_number",
        "race_no",
    ),
    "distance": (
        "distance",
        "distance_m",
        "race_distance",
        "distance_metres",
    ),
    "race_class": (
        "class",
        "race_class",
        "class_name",
        "race_grade",
    ),
    "going": (
        "going",
        "track_rating",
        "track_condition",
        "track_condition_name",
    ),
    "rail": (
        "rail",
        "rail_position",
        "rail_setting",
    ),
    "official_time": (
        "official_time",
        "race_time",
        "time",
        "official_race_time",
        "winning_time",
    ),
    "finish_position": (
        "finish",
        "finish_position",
        "finishing_position",
        "position",
    ),
    "margin": (
        "margin",
        "margin_lengths",
        "beaten_margin",
    ),
    "weight": (
        "weight",
        "weight_carried",
    ),
    "barrier": (
        "barrier",
        "barrier_number",
    ),
    "sp": (
        "sp",
        "starting_price",
    ),
}

SECTIONAL_FIELD_CANDIDATES = {
    "performance_sectional_id": (
        "performance_sectional_id",
    ),
    "performance_id": (
        "performance_id",
    ),
    "race_date": (
        "race_date",
    ),
    "track": (
        "canonical_track",
        "track",
    ),
    "race_number": (
        "race_number",
    ),
    "horse": (
        "canonical_horse",
        "horse",
        "horse_name",
    ),
    "last_800": (
        "last_800",
        "last800",
        "l800",
        "raw_last_800",
        "raw_last800",
        "raw_l800",
    ),
    "last_600": (
        "last_600",
        "last600",
        "l600",
        "raw_last_600",
        "raw_last600",
        "raw_l600",
    ),
    "last_400": (
        "last_400",
        "last400",
        "l400",
        "raw_last_400",
        "raw_last400",
        "raw_l400",
    ),
    "last_200": (
        "last_200",
        "last200",
        "l200",
        "raw_last_200",
        "raw_last200",
        "raw_l200",
    ),
    "split_800_600": (
        "800_600",
        "800-600",
        "split_800_600",
        "raw_800_600",
        "raw_split_800_600",
    ),
    "split_600_400": (
        "600_400",
        "600-400",
        "split_600_400",
        "raw_600_400",
        "raw_split_600_400",
    ),
    "split_400_200": (
        "400_200",
        "400-200",
        "split_400_200",
        "raw_400_200",
        "raw_split_400_200",
    ),
    "split_200_finish": (
        "200_finish",
        "200-finish",
        "200_f",
        "split_200_finish",
        "raw_200_finish",
        "raw_split_200_finish",
    ),
    "timing_quality_state": (
        "timing_quality_state",
    ),
}


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_column(
    value: Any,
) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        clean(value).lower(),
    ).strip("_")


def parse_number(
    value: Any,
) -> float | None:
    text = clean(value)

    if not text:
        return None

    text = text.replace(
        ",",
        "",
    )

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

    if not math.isfinite(number):
        return None

    return number


def latest_snapshot(
    root: Path,
    manifest_name: str,
) -> Path:
    candidates = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and (
                path / manifest_name
            ).exists()
        ),
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            f"No snapshot found under {root}"
        )

    return candidates[0]


def detect_fields(
    columns: list[str],
    candidate_map: dict[
        str,
        tuple[str, ...],
    ],
) -> dict[str, str]:
    normalised_lookup = {
        normalise_column(
            column
        ): column
        for column in columns
    }

    detected: dict[str, str] = {}

    for semantic, candidates in (
        candidate_map.items()
    ):
        detected[
            semantic
        ] = ""

        for candidate in candidates:
            key = normalise_column(
                candidate
            )

            if key in normalised_lookup:
                detected[
                    semantic
                ] = normalised_lookup[
                    key
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


def profile_performance_asset(
    path: Path,
) -> dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        columns = list(
            reader.fieldnames or []
        )

        detected = detect_fields(
            columns,
            FIELD_CANDIDATES,
        )

        rows = 0
        non_empty = Counter()
        numeric_valid = Counter()
        distinct_values: dict[
            str,
            set[str],
        ] = {
            semantic: set()
            for semantic in (
                "state",
                "track",
                "course",
                "distance",
                "race_class",
                "going",
                "rail",
            )
        }

        min_date = ""
        max_date = ""

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL == 0
            ):
                print(
                    "BENCHMARK_PERFORMANCE_PROFILE_"
                    f"PROGRESS={row_number}",
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

                if value:
                    non_empty[
                        semantic
                    ] += 1

                if semantic in {
                    "distance",
                    "official_time",
                    "finish_position",
                    "margin",
                    "weight",
                    "barrier",
                    "sp",
                }:
                    if (
                        parse_number(
                            value
                        )
                        is not None
                    ):
                        numeric_valid[
                            semantic
                        ] += 1

                if (
                    semantic
                    in distinct_values
                    and value
                    and len(
                        distinct_values[
                            semantic
                        ]
                    )
                    < 50_000
                ):
                    distinct_values[
                        semantic
                    ].add(value)

            date_field = detected.get(
                "race_date",
                "",
            )

            if date_field:
                race_date = clean(
                    row.get(
                        date_field
                    )
                )[:10]

                if race_date:
                    if (
                        not min_date
                        or race_date
                        < min_date
                    ):
                        min_date = race_date

                    if (
                        not max_date
                        or race_date
                        > max_date
                    ):
                        max_date = race_date

    coverage = {
        semantic: {
            "field": field,
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
                    distinct_values.get(
                        semantic,
                        set(),
                    )
                )
            ),
        }
        for semantic, field
        in detected.items()
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
        "min_race_date": (
            min_date
        ),
        "max_race_date": (
            max_date
        ),
    }


def profile_sectional_asset(
    path: Path,
) -> dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        columns = list(
            reader.fieldnames or []
        )

        detected = detect_fields(
            columns,
            SECTIONAL_FIELD_CANDIDATES,
        )

        rows = 0
        non_empty = Counter()
        numeric_valid = Counter()
        quality_states = Counter()

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL == 0
            ):
                print(
                    "BENCHMARK_SECTIONAL_PROFILE_"
                    f"PROGRESS={row_number}",
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

                if value:
                    non_empty[
                        semantic
                    ] += 1

                if semantic in {
                    "last_800",
                    "last_600",
                    "last_400",
                    "last_200",
                    "split_800_600",
                    "split_600_400",
                    "split_400_200",
                    "split_200_finish",
                }:
                    if (
                        parse_number(
                            value
                        )
                        is not None
                    ):
                        numeric_valid[
                            semantic
                        ] += 1

            quality_field = (
                detected.get(
                    "timing_quality_state",
                    "",
                )
            )

            if quality_field:
                state = clean(
                    row.get(
                        quality_field
                    )
                )

                if state:
                    quality_states[
                        state
                    ] += 1

    coverage = {
        semantic: {
            "field": field,
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
        }
        for semantic, field
        in detected.items()
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
        "quality_state_counts": dict(
            sorted(
                quality_states.items()
            )
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

    raw_snapshot = latest_snapshot(
        RAW_WAREHOUSE_ROOT,
        "warehouse_manifest.json",
    )

    dimension_snapshot = (
        latest_snapshot(
            DIMENSION_WAREHOUSE_ROOT,
            "dimension_manifest.json",
        )
    )

    performance_path = (
        raw_snapshot
        / "canonical_performance_evidence.csv"
    )

    sectional_path = (
        raw_snapshot
        / "canonical_sectional_evidence.csv"
    )

    performance_profile = (
        profile_performance_asset(
            performance_path
        )
    )

    sectional_profile = (
        profile_sectional_asset(
            sectional_path
        )
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    field_catalog_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_benchmark_evidence_"
            f"field_catalog_v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_5_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_5_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_BENCHMARK_ENGINE_"
            "READINESS_V0_1.md"
        )
    )

    field_catalog_rows = []

    for asset_name, profile in (
        (
            "canonical_performance_evidence",
            performance_profile,
        ),
        (
            "canonical_sectional_evidence",
            sectional_profile,
        ),
    ):
        for semantic, details in (
            profile["coverage"].items()
        ):
            field_catalog_rows.append(
                {
                    "asset_name": (
                        asset_name
                    ),
                    "semantic_field": (
                        semantic
                    ),
                    "physical_field": (
                        details.get(
                            "field",
                            "",
                        )
                    ),
                    "rows": (
                        profile["rows"]
                    ),
                    "present_rows": (
                        details.get(
                            "present_rows",
                            0,
                        )
                    ),
                    "coverage_pct": (
                        details.get(
                            "coverage_pct",
                            0.0,
                        )
                    ),
                    "numeric_valid_rows": (
                        details.get(
                            "numeric_valid_rows",
                            0,
                        )
                    ),
                    "numeric_valid_pct": (
                        details.get(
                            "numeric_valid_pct",
                            0.0,
                        )
                    ),
                    "distinct_value_count_capped": (
                        details.get(
                            "distinct_value_count_capped",
                            "",
                        )
                    ),
                }
            )

    write_csv(
        field_catalog_path,
        field_catalog_rows,
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

    required_base_fields = (
        "race_date",
        "track",
        "distance",
        "official_time",
    )

    missing_base_fields = [
        field
        for field in required_base_fields
        if not performance_detected.get(
            field
        )
    ]

    hierarchy_fields = (
        "track",
        "course",
        "distance",
        "race_class",
        "going",
        "rail",
    )

    available_hierarchy_fields = [
        field
        for field in hierarchy_fields
        if performance_detected.get(
            field
        )
    ]

    sectional_time_fields = (
        "last_800",
        "last_600",
        "last_400",
        "last_200",
        "split_800_600",
        "split_600_400",
        "split_400_200",
        "split_200_finish",
    )

    available_sectional_fields = [
        field
        for field in sectional_time_fields
        if sectional_detected.get(
            field
        )
    ]

    checks = [
        {
            "check": (
                "RAW_WAREHOUSE_AVAILABLE"
            ),
            "passed": (
                performance_path.exists()
                and sectional_path.exists()
            ),
            "observed": (
                raw_snapshot.name
            ),
        },
        {
            "check": (
                "DIMENSION_WAREHOUSE_AVAILABLE"
            ),
            "passed": (
                dimension_snapshot.exists()
            ),
            "observed": (
                dimension_snapshot.name
            ),
        },
        {
            "check": (
                "BASE_BENCHMARK_FIELDS"
            ),
            "passed": (
                not missing_base_fields
            ),
            "observed": (
                " | ".join(
                    missing_base_fields
                )
                or "ALL_PRESENT"
            ),
        },
        {
            "check": (
                "BENCHMARK_HIERARCHY_FIELDS"
            ),
            "passed": (
                len(
                    available_hierarchy_fields
                )
                >= 3
            ),
            "observed": (
                " | ".join(
                    available_hierarchy_fields
                )
            ),
        },
        {
            "check": (
                "SECTIONAL_TIME_FIELDS"
            ),
            "passed": (
                len(
                    available_sectional_fields
                )
                > 0
            ),
            "observed": (
                " | ".join(
                    available_sectional_fields
                )
                or "NONE"
            ),
        },
        {
            "check": (
                "NO_BENCHMARKS_CALCULATED"
            ),
            "passed": True,
            "observed": (
                "READINESS_AUDIT_ONLY"
            ),
        },
    ]

    failed_checks = [
        check["check"]
        for check in checks
        if not check["passed"]
    ]

    if not missing_base_fields:
        base_status = (
            "BASE_RACE_TIME_BENCHMARK_"
            "EVIDENCE_AVAILABLE"
        )
    else:
        base_status = (
            "BASE_RACE_TIME_BENCHMARK_"
            "EVIDENCE_BLOCKED"
        )

    if available_sectional_fields:
        sectional_status = (
            "SECTIONAL_BENCHMARK_"
            "EVIDENCE_AVAILABLE"
        )
    else:
        sectional_status = (
            "SECTIONAL_BENCHMARK_"
            "EVIDENCE_BLOCKED"
        )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.5 Benchmark Evidence "
            "Readiness Audit"
        ),
        "generated_utc": (
            utc_now()
        ),
        "audit_version": (
            AUDIT_VERSION
        ),
        "status": (
            "BENCHMARK_EVIDENCE_"
            "READINESS_PASS"
            if not failed_checks
            else
            "BENCHMARK_EVIDENCE_"
            "READINESS_PARTIAL"
        ),
        "production_data_modified": False,
        "benchmarks_calculated": False,
        "raw_warehouse_snapshot_id": (
            raw_snapshot.name
        ),
        "dimension_snapshot_id": (
            dimension_snapshot.name
        ),
        "performance_profile": (
            performance_profile
        ),
        "sectional_profile": (
            sectional_profile
        ),
        "missing_base_fields": (
            missing_base_fields
        ),
        "available_hierarchy_fields": (
            available_hierarchy_fields
        ),
        "available_sectional_fields": (
            available_sectional_fields
        ),
        "base_benchmark_status": (
            base_status
        ),
        "sectional_benchmark_status": (
            sectional_status
        ),
        "checks": checks,
        "failed_checks": (
            failed_checks
        ),
        "next_stage": (
            "Phase 1.5.1 define benchmark "
            "eligibility, exclusion rules, "
            "minimum samples and hierarchy "
            "fallback contracts."
        ),
        "outputs": {
            "field_catalog": str(
                field_catalog_path.relative_to(
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
        """# EDGEiQ Benchmark Engine Readiness V0.1

## Purpose

Phase 1.5 audits whether the immutable warehouse contains sufficient evidence to begin benchmark-engine design.

No benchmark values are calculated in this phase.

## Benchmark hierarchy

The intended hierarchy remains:

1. Track
2. Track and course
3. Track, course and distance
4. Track, course, distance and class
5. Track, course, distance, class and going
6. Track, course, distance, class, going and rail

Each benchmark must retain:

- benchmark ID
- hierarchy level
- sample size
- confidence
- source snapshot
- eligibility rules
- exclusion counts
- benchmark version
- generated timestamp

## Timing convention

Raw official seconds are preserved.

Derived benchmark differences use:

- negative = faster than benchmark
- positive = slower than benchmark

This convention cannot change between engines.

## Evidence restrictions

No benchmark may be built from:

- invalid official times
- missing distance
- abandoned races
- timing inconsistencies
- sectional mismatches
- unresolved race identity
- manually fabricated values

## Next phase

Phase 1.5.1 defines the formal eligibility and hierarchy-fallback contract before benchmark calculation begins.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.5 Benchmark Evidence Readiness Audit

Generated UTC: `{summary['generated_utc']}`

Status: **{summary['status']}**

- Performance rows: **{performance_profile['rows']:,}**
- Sectional rows: **{sectional_profile['rows']:,}**
- Available hierarchy fields: **{', '.join(available_hierarchy_fields)}**
- Available sectional fields: **{', '.join(available_sectional_fields) if available_sectional_fields else 'None'}**
- Missing base fields: **{', '.join(missing_base_fields) if missing_base_fields else 'None'}**
- Benchmarks calculated: **False**

Base benchmark status: **{base_status}**

Sectional benchmark status: **{sectional_status}**
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_5_BENCHMARK_EVIDENCE_"
        "READINESS_PASS"
        if not failed_checks
        else
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_5_BENCHMARK_EVIDENCE_"
        "READINESS_PARTIAL",
        flush=True,
    )

    print(
        f"PERFORMANCE_ROWS="
        f"{performance_profile['rows']}",
        flush=True,
    )

    print(
        f"SECTIONAL_ROWS="
        f"{sectional_profile['rows']}",
        flush=True,
    )

    print(
        "AVAILABLE_HIERARCHY_FIELDS="
        + "|".join(
            available_hierarchy_fields
        ),
        flush=True,
    )

    print(
        "AVAILABLE_SECTIONAL_FIELDS="
        + "|".join(
            available_sectional_fields
        ),
        flush=True,
    )

    print(
        "MISSING_BASE_FIELDS="
        + "|".join(
            missing_base_fields
        ),
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
