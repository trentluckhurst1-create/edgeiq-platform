from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

RESULTS = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_historical_results_warehouse_v2_graphql.csv"
)

SECTIONALS = (
    ROOT
    / "public"
    / "data"
    / "racingcom_sectional_warehouse_v2.csv"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase0_6"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase0_6"
)

SAMPLE_LIMIT = 50
UNIQUE_SAMPLE_LIMIT = 5000
PROGRESS_INTERVAL = 100_000

SEMANTIC_GROUPS = {
    "race_date": (
        "race_date",
        "date",
        "meeting_date",
        "run_date",
        "run_date_iso",
    ),
    "track": (
        "track",
        "track_name",
        "venue",
        "venue_name",
        "course",
    ),
    "race_number": (
        "race_no",
        "race_number",
        "race",
        "race_num",
    ),
    "race_id": (
        "race_id",
        "race_key",
        "provider_race_id",
        "event_id",
    ),
    "runner_id": (
        "runner_id",
        "horse_id",
        "horse_code",
        "runner_code",
        "provider_runner_id",
    ),
    "horse": (
        "horse",
        "horse_name",
        "runner",
        "runner_name",
        "sectional_runner",
    ),
    "distance": (
        "distance",
        "distance_metres",
        "race_distance",
    ),
    "finish": (
        "finish",
        "finish_pos",
        "position",
        "placing",
    ),
}

HIGH_VALUE_PATTERNS = (
    "race",
    "track",
    "date",
    "horse",
    "runner",
    "meeting",
    "event",
    "distance",
    "finish",
    "sectional",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_text(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\s+", " ", text)
    return text


def normalise_key_text(value: Any) -> str:
    text = normalise_text(value)
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_date(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    )

    for fmt in formats:
        try:
            parsed = datetime.strptime(
                text[:19],
                fmt,
            )
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        text,
    )

    return match.group(1) if match else ""


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
        path.write_text("", encoding="utf-8")
        return

    fields: list[str] = []

    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

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


def profile_file(
    label: str,
    path: Path,
) -> dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])

        non_empty = Counter()
        unique_values: dict[
            str,
            set[str],
        ] = defaultdict(set)
        samples: list[dict[str, Any]] = []
        row_count = 0

        interesting_columns = [
            column
            for column in columns
            if any(
                pattern in column.lower()
                for pattern in HIGH_VALUE_PATTERNS
            )
        ]

        for row_count, row in enumerate(
            reader,
            start=1,
        ):
            if (
                row_count == 1
                or row_count % PROGRESS_INTERVAL == 0
            ):
                print(
                    f"PROFILE_PROGRESS={label} "
                    f"ROWS={row_count}",
                    flush=True,
                )

            if row_count <= SAMPLE_LIMIT:
                samples.append(
                    {
                        key: clean(row.get(key))
                        for key in columns
                    }
                )

            for column in interesting_columns:
                value = clean(row.get(column))

                if value:
                    non_empty[column] += 1

                    if (
                        len(unique_values[column])
                        < UNIQUE_SAMPLE_LIMIT
                    ):
                        unique_values[column].add(
                            value
                        )

        semantic_matches: dict[
            str,
            list[str],
        ] = {}

        lower_columns = {
            column.lower(): column
            for column in columns
        }

        for semantic, candidates in (
            SEMANTIC_GROUPS.items()
        ):
            semantic_matches[semantic] = [
                lower_columns[candidate]
                for candidate in candidates
                if candidate in lower_columns
            ]

        column_profiles = []

        for column in columns:
            count = non_empty.get(
                column,
                0,
            )

            column_profiles.append(
                {
                    "file_label": label,
                    "column": column,
                    "non_empty_rows": count,
                    "non_empty_pct": (
                        round(
                            count
                            / row_count
                            * 100,
                            4,
                        )
                        if row_count
                        else 0.0
                    ),
                    "sample_unique_count_capped": len(
                        unique_values.get(
                            column,
                            set(),
                        )
                    ),
                    "sample_values": " | ".join(
                        sorted(
                            unique_values.get(
                                column,
                                set(),
                            )
                        )[:20]
                    ),
                }
            )

        return {
            "label": label,
            "path": str(
                path.relative_to(ROOT)
            ).replace("\\", "/"),
            "rows": row_count,
            "columns": columns,
            "column_count": len(columns),
            "semantic_matches": semantic_matches,
            "column_profiles": column_profiles,
            "sample_rows": samples,
        }


def first_present(
    semantic_matches: dict[
        str,
        list[str],
    ],
    semantic: str,
) -> str:
    values = semantic_matches.get(
        semantic,
        [],
    )
    return values[0] if values else ""


def build_candidate_key_plan(
    results_profile: dict[str, Any],
    sectionals_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    result_map = results_profile[
        "semantic_matches"
    ]
    sectional_map = sectionals_profile[
        "semantic_matches"
    ]

    candidate_definitions = [
        {
            "name": "PROVIDER_RACE_AND_RUNNER_ID",
            "components": (
                "race_id",
                "runner_id",
            ),
            "strength": "STRONGEST",
        },
        {
            "name": "DATE_TRACK_RACE_AND_HORSE",
            "components": (
                "race_date",
                "track",
                "race_number",
                "horse",
            ),
            "strength": "STRONG",
        },
        {
            "name": "DATE_TRACK_DISTANCE_AND_HORSE",
            "components": (
                "race_date",
                "track",
                "distance",
                "horse",
            ),
            "strength": "CONDITIONAL",
        },
        {
            "name": "DATE_HORSE_ONLY",
            "components": (
                "race_date",
                "horse",
            ),
            "strength": "UNSAFE_WITHOUT_UNIQUENESS",
        },
    ]

    for definition in candidate_definitions:
        result_columns = []
        sectional_columns = []
        missing_results = []
        missing_sectionals = []

        for semantic in definition[
            "components"
        ]:
            result_column = first_present(
                result_map,
                semantic,
            )
            sectional_column = first_present(
                sectional_map,
                semantic,
            )

            if result_column:
                result_columns.append(
                    result_column
                )
            else:
                missing_results.append(
                    semantic
                )

            if sectional_column:
                sectional_columns.append(
                    sectional_column
                )
            else:
                missing_sectionals.append(
                    semantic
                )

        available = (
            not missing_results
            and not missing_sectionals
        )

        rows.append(
            {
                "candidate_name": (
                    definition["name"]
                ),
                "strength": (
                    definition["strength"]
                ),
                "components": " | ".join(
                    definition["components"]
                ),
                "results_columns": " | ".join(
                    result_columns
                ),
                "sectional_columns": " | ".join(
                    sectional_columns
                ),
                "missing_results_semantics": (
                    " | ".join(
                        missing_results
                    )
                ),
                "missing_sectional_semantics": (
                    " | ".join(
                        missing_sectionals
                    )
                ),
                "available_for_test": available,
            }
        )

    return rows


def get_value(
    row: dict[str, str],
    column: str,
    semantic: str,
) -> str:
    value = clean(row.get(column))

    if semantic == "race_date":
        return normalise_date(value)

    if semantic in {
        "track",
        "horse",
    }:
        return normalise_key_text(
            value
        )

    return normalise_text(value)


def build_key(
    row: dict[str, str],
    semantic_to_column: dict[str, str],
    components: tuple[str, ...],
) -> str:
    values = []

    for semantic in components:
        column = semantic_to_column.get(
            semantic,
            "",
        )

        if not column:
            return ""

        value = get_value(
            row,
            column,
            semantic,
        )

        if not value:
            return ""

        values.append(value)

    return "|".join(values)


def test_candidate_linkage(
    candidate_plan: list[dict[str, Any]],
    results_profile: dict[str, Any],
    sectionals_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    test_rows: list[dict[str, Any]] = []

    available_candidates = [
        row
        for row in candidate_plan
        if row["available_for_test"]
    ]

    result_semantics = {
        semantic: first_present(
            results_profile[
                "semantic_matches"
            ],
            semantic,
        )
        for semantic in SEMANTIC_GROUPS
    }

    sectional_semantics = {
        semantic: first_present(
            sectionals_profile[
                "semantic_matches"
            ],
            semantic,
        )
        for semantic in SEMANTIC_GROUPS
    }

    for candidate in available_candidates:
        components = tuple(
            candidate["components"].split(
                " | "
            )
        )

        print(
            f"LINK_TEST_START="
            f"{candidate['candidate_name']}",
            flush=True,
        )

        result_key_counts: Counter[str] = Counter()

        with RESULTS.open(
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
                if (
                    row_number == 1
                    or row_number
                    % PROGRESS_INTERVAL
                    == 0
                ):
                    print(
                        f"LINK_RESULTS_PROGRESS="
                        f"{candidate['candidate_name']} "
                        f"{row_number}",
                        flush=True,
                    )

                key = build_key(
                    row,
                    result_semantics,
                    components,
                )

                if key:
                    result_key_counts[key] += 1

        sectional_rows = 0
        populated_sectional_keys = 0
        exact_unique_matches = 0
        ambiguous_matches = 0
        unmatched = 0

        with SECTIONALS.open(
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
                sectional_rows += 1

                if (
                    row_number == 1
                    or row_number
                    % PROGRESS_INTERVAL
                    == 0
                ):
                    print(
                        f"LINK_SECTIONAL_PROGRESS="
                        f"{candidate['candidate_name']} "
                        f"{row_number}",
                        flush=True,
                    )

                key = build_key(
                    row,
                    sectional_semantics,
                    components,
                )

                if not key:
                    unmatched += 1
                    continue

                populated_sectional_keys += 1
                count = result_key_counts.get(
                    key,
                    0,
                )

                if count == 1:
                    exact_unique_matches += 1
                elif count > 1:
                    ambiguous_matches += 1
                else:
                    unmatched += 1

        test_rows.append(
            {
                "candidate_name": (
                    candidate["candidate_name"]
                ),
                "strength": (
                    candidate["strength"]
                ),
                "components": (
                    candidate["components"]
                ),
                "result_unique_keys": sum(
                    1
                    for count
                    in result_key_counts.values()
                    if count == 1
                ),
                "result_ambiguous_keys": sum(
                    1
                    for count
                    in result_key_counts.values()
                    if count > 1
                ),
                "sectional_rows": (
                    sectional_rows
                ),
                "sectional_rows_with_complete_key": (
                    populated_sectional_keys
                ),
                "exact_unique_matches": (
                    exact_unique_matches
                ),
                "ambiguous_matches": (
                    ambiguous_matches
                ),
                "unmatched_rows": unmatched,
                "exact_unique_match_pct": (
                    round(
                        exact_unique_matches
                        / sectional_rows
                        * 100,
                        4,
                    )
                    if sectional_rows
                    else 0.0
                ),
                "ambiguous_match_pct": (
                    round(
                        ambiguous_matches
                        / sectional_rows
                        * 100,
                        4,
                    )
                    if sectional_rows
                    else 0.0
                ),
            }
        )

    return test_rows


def markdown_report(
    summary: dict[str, Any],
) -> str:
    lines = [
        "# EDGEiQ Performance Intelligence",
        "## Phase 0.6 Sectional Linkage Diagnosis",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        "## Finding",
        "",
        "Phase 0.5 produced zero sectional links because the assumed provider-ID and composite field names were not shared by both source files.",
        "",
        "This is a schema-contract mismatch, not evidence that the records cannot be linked.",
        "",
        "## Candidate linkage tests",
        "",
        "| Candidate | Strength | Exact matches | Exact % | Ambiguous | Unmatched |",
        "|---|---|---:|---:|---:|---:|",
    ]

    for row in summary[
        "linkage_tests"
    ]:
        lines.append(
            f"| {row['candidate_name']} | "
            f"{row['strength']} | "
            f"{row['exact_unique_matches']} | "
            f"{row['exact_unique_match_pct']} | "
            f"{row['ambiguous_matches']} | "
            f"{row['unmatched_rows']} |"
        )

    lines.extend(
        [
            "",
            "## Governance rule",
            "",
            "Only unique deterministic matches may be promoted automatically.",
            "",
            "Ambiguous matches must remain unresolved until stronger identity evidence exists.",
            "",
            "Name-only or date-and-horse matches must never be silently promoted without uniqueness and supporting race evidence.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results_profile = profile_file(
        "results",
        RESULTS,
    )
    sectionals_profile = profile_file(
        "sectionals",
        SECTIONALS,
    )

    candidate_plan = build_candidate_key_plan(
        results_profile,
        sectionals_profile,
    )

    linkage_tests = test_candidate_linkage(
        candidate_plan,
        results_profile,
        sectionals_profile,
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    column_profiles_path = (
        AUDIT_DIR
        / f"edgeiq_phase0_6_column_profiles_{run_id}.csv"
    )
    candidate_plan_path = (
        ARCH_DIR
        / "edgeiq_sectional_linkage_candidate_plan_v0_1.csv"
    )
    linkage_tests_path = (
        AUDIT_DIR
        / f"edgeiq_phase0_6_linkage_tests_{run_id}.csv"
    )
    detail_path = (
        AUDIT_DIR
        / f"edgeiq_phase0_6_detail_{run_id}.json"
    )
    summary_path = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase0_6_summary_{run_id}.json"
    )
    latest_path = (
        AUDIT_DIR
        / "edgeiq_performance_intelligence_phase0_6_latest.json"
    )
    report_path = (
        AUDIT_DIR
        / f"EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE0_6_REPORT_{run_id}.md"
    )

    write_csv(
        column_profiles_path,
        (
            results_profile[
                "column_profiles"
            ]
            + sectionals_profile[
                "column_profiles"
            ]
        ),
    )

    write_csv(
        candidate_plan_path,
        candidate_plan,
    )

    write_csv(
        linkage_tests_path,
        linkage_tests,
    )

    detail = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 0.6 Sectional Linkage Diagnosis"
        ),
        "generated_utc": utc_now(),
        "results_profile": (
            results_profile
        ),
        "sectionals_profile": (
            sectionals_profile
        ),
        "candidate_plan": (
            candidate_plan
        ),
        "linkage_tests": (
            linkage_tests
        ),
    }

    write_json(
        detail_path,
        detail,
    )

    best_candidate = (
        sorted(
            linkage_tests,
            key=lambda row: (
                -row[
                    "exact_unique_matches"
                ],
                row[
                    "ambiguous_matches"
                ],
            ),
        )[0]
        if linkage_tests
        else None
    )

    summary = {
        "audit_name": detail[
            "audit_name"
        ],
        "generated_utc": detail[
            "generated_utc"
        ],
        "results_rows": (
            results_profile["rows"]
        ),
        "sectional_rows": (
            sectionals_profile["rows"]
        ),
        "results_columns": (
            results_profile["column_count"]
        ),
        "sectional_columns": (
            sectionals_profile[
                "column_count"
            ]
        ),
        "candidate_plans": len(
            candidate_plan
        ),
        "candidate_tests_run": len(
            linkage_tests
        ),
        "best_candidate": (
            best_candidate
        ),
        "phase0_5_zero_link_reason": (
            "ASSUMED_FIELD_NAMES_DID_NOT_"
            "MATCH_ACTUAL_WAREHOUSE_SCHEMA"
        ),
        "canonical_status": (
            "LINKAGE_STRATEGY_NOT_YET_"
            "PROMOTED"
        ),
        "next_stage": (
            "Phase 0.7 governed sectional "
            "performance linkage prototype "
            "using the strongest unique key"
        ),
        "linkage_tests": linkage_tests,
    }

    write_json(
        summary_path,
        summary,
    )
    write_json(
        latest_path,
        summary,
    )

    report_path.write_text(
        markdown_report(summary),
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE0_6_SECTIONAL_LINKAGE_"
        "DIAGNOSIS_PASS",
        flush=True,
    )
    print(
        f"COLUMN_PROFILES={column_profiles_path}",
        flush=True,
    )
    print(
        f"CANDIDATE_PLAN={candidate_plan_path}",
        flush=True,
    )
    print(
        f"LINKAGE_TESTS={linkage_tests_path}",
        flush=True,
    )
    print(
        f"DETAIL={detail_path}",
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
