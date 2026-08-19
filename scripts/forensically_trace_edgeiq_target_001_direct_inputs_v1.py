from __future__ import annotations

import ast
import csv
import hashlib
import itertools
import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path.cwd().resolve()

PROGRAM_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "restart-v1"
)

TRACE_002B_JSON = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_target_001_producer_trace_v1.json"
)

PRODUCER_PATH = (
    ROOT
    / "scripts"
    / "build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py"
)

RATING_FACT = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_horse_performance_rating_fact_v1.csv"
)

RACE_ENTRY_FACT = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_race_entry_fact_v1.csv"
)

TARGET_OUTPUT = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
)

OUTPUT_JSON = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_target_001_direct_input_trace_v1.json"
)

OUTPUT_CSV = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_target_001_join_key_profile_v1.csv"
)

OUTPUT_MD = (
    PROGRAM_ROOT
    / "EDGEIQ_PERFORMANCE_INTELLIGENCE_TARGET_001_DIRECT_INPUT_TRACE_V1.md"
)

SOURCE_EVIDENCE = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_target_001_builder_source_evidence_v1.txt"
)

STARTED = time.monotonic()

NULL_TOKENS = {
    "",
    "nan",
    "none",
    "null",
    "nat",
    "<na>",
}


def log(message: str) -> None:
    elapsed = time.monotonic() - STARTED
    print(
        f"[{elapsed:7.2f}s] {message}",
        flush=True,
    )


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return completed.stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required evidence file missing: {rel(path)}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def normalise_scalar(value: Any) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip().casefold()

    if text in NULL_TOKENS:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def normalised_series(series: pd.Series) -> pd.Series:
    return series.map(normalise_scalar)


def inspect_csv(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required input missing: {rel(path)}"
        )

    frame = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )

    return {
        "path": rel(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "column_names": [
            str(column)
            for column in frame.columns
        ],
        "frame": frame,
    }


def call_name(node: ast.AST) -> str:
    parts: list[str] = []

    current: ast.AST | None = node

    while current is not None:
        if isinstance(current, ast.Name):
            parts.append(current.id)
            break

        if isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
            continue

        break

    return ".".join(reversed(parts))


def literal_value(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def source_segment(
    source: str,
    node: ast.AST,
) -> str:
    segment = ast.get_source_segment(
        source,
        node,
    )

    return (
        segment.strip()
        if segment
        else ""
    )


def analyse_builder_source(
    source: str,
) -> dict[str, Any]:
    tree = ast.parse(source)

    operations: list[dict[str, Any]] = []
    named_paths: dict[str, str] = {}
    detected_join_keys: list[list[str]] = []
    detected_filters: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.Assign, ast.AnnAssign),
        ):
            value_node = (
                node.value
                if isinstance(node, ast.Assign)
                else node.value
            )

            if value_node is None:
                continue

            value = literal_value(value_node)

            targets: list[ast.AST] = []

            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif node.target is not None:
                targets = [node.target]

            for target in targets:
                if isinstance(target, ast.Name):
                    if isinstance(value, str):
                        named_paths[target.id] = value

        if not isinstance(node, ast.Call):
            continue

        name = call_name(node.func)

        operation: dict[str, Any] = {
            "line_number": getattr(
                node,
                "lineno",
                None,
            ),
            "call_name": name,
            "source": source_segment(
                source,
                node,
            ),
            "keywords": {},
        }

        for keyword in node.keywords:
            if keyword.arg is None:
                continue

            operation["keywords"][keyword.arg] = (
                literal_value(keyword.value)
            )

        lowered = name.casefold()

        if (
            "read_csv" in lowered
            or lowered.endswith(".merge")
            or lowered == "pandas.merge"
            or lowered == "pd.merge"
            or lowered.endswith(".join")
            or "drop_duplicates" in lowered
            or lowered.endswith(".query")
            or lowered.endswith(".to_csv")
            or "writerow" in lowered
        ):
            operations.append(operation)

        if (
            lowered.endswith(".merge")
            or lowered in {
                "pandas.merge",
                "pd.merge",
            }
        ):
            keywords = operation["keywords"]

            keys: list[str] = []

            on_value = keywords.get("on")

            if isinstance(on_value, str):
                keys = [on_value]
            elif isinstance(on_value, list):
                keys = [
                    str(item)
                    for item in on_value
                ]

            if not keys:
                left_on = keywords.get("left_on")
                right_on = keywords.get("right_on")

                candidate_values: list[Any] = []

                if left_on is not None:
                    candidate_values.append(left_on)

                if right_on is not None:
                    candidate_values.append(right_on)

                for candidate in candidate_values:
                    if isinstance(candidate, str):
                        keys.append(candidate)
                    elif isinstance(candidate, list):
                        keys.extend(
                            str(item)
                            for item in candidate
                        )

            if keys:
                canonical = sorted(
                    set(keys),
                )

                if canonical not in detected_join_keys:
                    detected_join_keys.append(
                        canonical
                    )

        if lowered.endswith(".query"):
            detected_filters.append(operation)

    source_lines = source.splitlines()

    evidence_lines: list[str] = []

    important_line_numbers: set[int] = set()

    for operation in operations:
        line_number = operation.get(
            "line_number"
        )

        if isinstance(line_number, int):
            for number in range(
                max(1, line_number - 2),
                min(
                    len(source_lines),
                    line_number + 3,
                )
                + 1,
            ):
                important_line_numbers.add(number)

    for number in sorted(important_line_numbers):
        evidence_lines.append(
            f"{number:05d}: {source_lines[number - 1]}"
        )

    return {
        "operations": sorted(
            operations,
            key=lambda item: (
                item.get("line_number") or 0
            ),
        ),
        "detected_join_keys": detected_join_keys,
        "detected_filters": detected_filters,
        "named_paths": named_paths,
        "source_evidence_lines": evidence_lines,
    }


def profile_single_key(
    left: pd.DataFrame,
    right: pd.DataFrame,
    column: str,
) -> dict[str, Any]:
    left_values = normalised_series(
        left[column]
    )

    right_values = normalised_series(
        right[column]
    )

    left_non_empty = left_values[
        left_values != ""
    ]

    right_non_empty = right_values[
        right_values != ""
    ]

    left_unique = set(left_non_empty.unique())
    right_unique = set(right_non_empty.unique())

    overlap = left_unique & right_unique

    left_match_rows = int(
        left_non_empty.isin(overlap).sum()
    )

    right_match_rows = int(
        right_non_empty.isin(overlap).sum()
    )

    estimated_inner_rows = 0

    left_counts = Counter(left_non_empty)
    right_counts = Counter(right_non_empty)

    for value in overlap:
        estimated_inner_rows += (
            left_counts[value]
            * right_counts[value]
        )

    return {
        "key_type": "SINGLE_COLUMN",
        "key_columns": column,
        "left_non_empty_rows": int(
            len(left_non_empty)
        ),
        "right_non_empty_rows": int(
            len(right_non_empty)
        ),
        "left_unique_values": int(
            len(left_unique)
        ),
        "right_unique_values": int(
            len(right_unique)
        ),
        "overlap_unique_values": int(
            len(overlap)
        ),
        "left_rows_with_overlap": left_match_rows,
        "right_rows_with_overlap": right_match_rows,
        "estimated_inner_join_rows": int(
            estimated_inner_rows
        ),
        "zero_overlap": len(overlap) == 0,
        "sample_overlap_values": " | ".join(
            sorted(overlap)[:10]
        ),
    }


def composite_series(
    frame: pd.DataFrame,
    columns: list[str],
) -> pd.Series:
    parts = [
        normalised_series(
            frame[column]
        )
        for column in columns
    ]

    result = parts[0]

    for part in parts[1:]:
        result = result + "¦" + part

    valid_mask = pd.Series(
        True,
        index=frame.index,
    )

    for part in parts:
        valid_mask &= part != ""

    return result.where(
        valid_mask,
        "",
    )


def profile_composite_key(
    left: pd.DataFrame,
    right: pd.DataFrame,
    columns: list[str],
) -> dict[str, Any]:
    left_values = composite_series(
        left,
        columns,
    )

    right_values = composite_series(
        right,
        columns,
    )

    left_non_empty = left_values[
        left_values != ""
    ]

    right_non_empty = right_values[
        right_values != ""
    ]

    left_unique = set(left_non_empty.unique())
    right_unique = set(right_non_empty.unique())

    overlap = left_unique & right_unique

    left_counts = Counter(left_non_empty)
    right_counts = Counter(right_non_empty)

    estimated_inner_rows = sum(
        left_counts[value]
        * right_counts[value]
        for value in overlap
    )

    return {
        "key_type": "COMPOSITE",
        "key_columns": ",".join(columns),
        "left_non_empty_rows": int(
            len(left_non_empty)
        ),
        "right_non_empty_rows": int(
            len(right_non_empty)
        ),
        "left_unique_values": int(
            len(left_unique)
        ),
        "right_unique_values": int(
            len(right_unique)
        ),
        "overlap_unique_values": int(
            len(overlap)
        ),
        "left_rows_with_overlap": int(
            left_non_empty.isin(overlap).sum()
        ),
        "right_rows_with_overlap": int(
            right_non_empty.isin(overlap).sum()
        ),
        "estimated_inner_join_rows": int(
            estimated_inner_rows
        ),
        "zero_overlap": len(overlap) == 0,
        "sample_overlap_values": " | ".join(
            sorted(overlap)[:10]
        ),
    }


def infer_identifier_columns(
    columns: list[str],
) -> list[str]:
    tokens = (
        "id",
        "key",
        "code",
        "horse",
        "runner",
        "race",
        "meeting",
        "date",
        "track",
    )

    inferred: list[str] = []

    for column in columns:
        lowered = column.casefold()

        if any(
            token in lowered
            for token in tokens
        ):
            inferred.append(column)

    return inferred


def main() -> int:
    log("PI_RESTART_UNIT_002C START")

    trace_002b = load_json(
        TRACE_002B_JSON
    )

    if trace_002b.get("verdict") != "PASS":
        raise RuntimeError(
            "Unit 002B evidence verdict is not PASS."
        )

    expected_producer = str(
        trace_002b
        .get("summary", {})
        .get(
            "strongest_producer_candidate",
            "",
        )
    )

    if expected_producer != rel(PRODUCER_PATH):
        raise RuntimeError(
            "Unit 002B strongest producer does not "
            "match the governed Unit 002C producer."
        )

    for required_path in (
        PRODUCER_PATH,
        RATING_FACT,
        RACE_ENTRY_FACT,
        TARGET_OUTPUT,
    ):
        if not required_path.is_file():
            raise FileNotFoundError(
                f"Required file missing: {rel(required_path)}"
            )

    log(
        "PRODUCER="
        f"{rel(PRODUCER_PATH)}"
    )

    producer_source = PRODUCER_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    builder_analysis = analyse_builder_source(
        producer_source
    )

    rating = inspect_csv(
        RATING_FACT
    )

    race_entry = inspect_csv(
        RACE_ENTRY_FACT
    )

    target = inspect_csv(
        TARGET_OUTPUT
    )

    log(
        "RATING_FACT_ROWS="
        f"{rating['rows']}"
    )
    log(
        "RACE_ENTRY_FACT_ROWS="
        f"{race_entry['rows']}"
    )
    log(
        "TARGET_OUTPUT_ROWS="
        f"{target['rows']}"
    )

    if rating["rows"] <= 0:
        raise RuntimeError(
            "Rating fact is not populated."
        )

    if race_entry["rows"] <= 0:
        raise RuntimeError(
            "Race-entry fact is not populated."
        )

    if target["rows"] != 0:
        raise RuntimeError(
            "Target 001 is no longer zero-row. "
            "The forensic baseline has changed."
        )

    rating_frame: pd.DataFrame = rating.pop(
        "frame"
    )

    race_entry_frame: pd.DataFrame = (
        race_entry.pop("frame")
    )

    target.pop("frame")

    shared_columns = sorted(
        set(rating_frame.columns)
        & set(race_entry_frame.columns)
    )

    if not shared_columns:
        raise RuntimeError(
            "The two direct inputs share no column names."
        )

    identifier_columns = infer_identifier_columns(
        shared_columns
    )

    single_key_profiles: list[
        dict[str, Any]
    ] = []

    for column in shared_columns:
        single_key_profiles.append(
            profile_single_key(
                rating_frame,
                race_entry_frame,
                column,
            )
        )

    single_key_profiles.sort(
        key=lambda item: (
            -item["estimated_inner_join_rows"],
            -item["overlap_unique_values"],
            item["key_columns"],
        )
    )

    composite_candidates: set[
        tuple[str, ...]
    ] = set()

    for detected in builder_analysis[
        "detected_join_keys"
    ]:
        valid = tuple(
            column
            for column in detected
            if (
                column in rating_frame.columns
                and column
                in race_entry_frame.columns
            )
        )

        if len(valid) >= 2:
            composite_candidates.add(valid)

    candidate_pool = (
        identifier_columns
        if identifier_columns
        else shared_columns
    )

    candidate_pool = candidate_pool[:10]

    for width in (2, 3):
        for combination in itertools.combinations(
            candidate_pool,
            width,
        ):
            composite_candidates.add(
                tuple(combination)
            )

    composite_key_profiles: list[
        dict[str, Any]
    ] = []

    for columns in sorted(
        composite_candidates
    ):
        composite_key_profiles.append(
            profile_composite_key(
                rating_frame,
                race_entry_frame,
                list(columns),
            )
        )

    composite_key_profiles.sort(
        key=lambda item: (
            -item["estimated_inner_join_rows"],
            -item["overlap_unique_values"],
            item["key_columns"],
        )
    )

    all_profiles = (
        single_key_profiles
        + composite_key_profiles
    )

    source_detected_keys = [
        profile
        for profile in all_profiles
        if (
            profile["key_columns"].split(",")
            in builder_analysis[
                "detected_join_keys"
            ]
        )
    ]

    positive_profiles = [
        profile
        for profile in all_profiles
        if profile[
            "estimated_inner_join_rows"
        ] > 0
    ]

    zero_profiles = [
        profile
        for profile in all_profiles
        if profile["zero_overlap"]
    ]

    best_profile = (
        positive_profiles[0]
        if positive_profiles
        else all_profiles[0]
    )

    detected_merge_operations = [
        operation
        for operation in builder_analysis[
            "operations"
        ]
        if (
            operation["call_name"]
            .casefold()
            .endswith(".merge")
            or operation["call_name"]
            .casefold()
            in {
                "pd.merge",
                "pandas.merge",
            }
        )
    ]

    if (
        builder_analysis["detected_join_keys"]
        and source_detected_keys
    ):
        detected_key_rows = max(
            profile[
                "estimated_inner_join_rows"
            ]
            for profile in source_detected_keys
        )

        if detected_key_rows == 0:
            collapse_classification = (
                "PROVEN_ZERO_OVERLAP_ON_SOURCE_DECLARED_JOIN_KEY"
            )
            first_collapse_stage = (
                "BUILDER_JOIN_OPERATION"
            )
            next_action = (
                "FORENSICALLY_COMPARE_JOIN_KEY_SEMANTICS"
            )
        else:
            collapse_classification = (
                "SOURCE_DECLARED_JOIN_HAS_MATCHES"
            )
            first_collapse_stage = (
                "AFTER_JOIN_OR_LATER_FILTER"
            )
            next_action = (
                "TRACE_TARGET_001_POST_JOIN_FILTERS"
            )

    elif positive_profiles:
        collapse_classification = (
            "INPUTS_HAVE_POTENTIAL_KEY_OVERLAP_"
            "BUT_SOURCE_JOIN_KEY_NOT_STATICALLY_RESOLVED"
        )
        first_collapse_stage = (
            "BUILDER_JOIN_OR_POST_JOIN_FILTER"
        )
        next_action = (
            "EXECUTION_TRACE_TARGET_001_BUILDER_LOCALS"
        )

    else:
        collapse_classification = (
            "NO_SHARED_KEY_PROFILE_PRODUCES_MATCHES"
        )
        first_collapse_stage = (
            "INPUT_JOIN_BOUNDARY"
        )
        next_action = (
            "FORENSICALLY_COMPARE_IDENTIFIER_SEMANTICS"
        )

    SOURCE_EVIDENCE.write_text(
        "\n".join(
            [
                (
                    "EDGEIQ PERFORMANCE INTELLIGENCE "
                    "TARGET 001 BUILDER SOURCE EVIDENCE V1"
                ),
                "",
                f"PRODUCER={rel(PRODUCER_PATH)}",
                f"SHA256={sha256_file(PRODUCER_PATH)}",
                "",
                *builder_analysis[
                    "source_evidence_lines"
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )

    csv_fieldnames = [
        "key_type",
        "key_columns",
        "left_non_empty_rows",
        "right_non_empty_rows",
        "left_unique_values",
        "right_unique_values",
        "overlap_unique_values",
        "left_rows_with_overlap",
        "right_rows_with_overlap",
        "estimated_inner_join_rows",
        "zero_overlap",
        "sample_overlap_values",
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=csv_fieldnames,
        )

        writer.writeheader()
        writer.writerows(all_profiles)

    payload = {
        "program": (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE"
        ),
        "unit": "PI_RESTART_UNIT_002C",
        "name": (
            "Target 001 Direct Input and Join Trace"
        ),
        "version": "V1",
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "verdict": "PASS",
        "governance": {
            "engine_logic_changed": False,
            "thresholds_changed": False,
            "source_data_changed": False,
            "warehouse_data_changed": False,
            "runtime_data_changed": False,
            "react_changed": False,
            "producer_executed": False,
        },
        "repository": {
            "branch": run_git(
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
            ),
            "head": run_git(
                "rev-parse",
                "HEAD",
            ),
            "head_short": run_git(
                "rev-parse",
                "--short",
                "HEAD",
            ),
        },
        "producer": {
            "relative_path": rel(
                PRODUCER_PATH
            ),
            "size_bytes": (
                PRODUCER_PATH.stat().st_size
            ),
            "sha256": sha256_file(
                PRODUCER_PATH
            ),
        },
        "datasets": {
            "rating_fact": rating,
            "race_entry_fact": race_entry,
            "target_output": target,
        },
        "builder_analysis": {
            "operation_count": len(
                builder_analysis["operations"]
            ),
            "operations": builder_analysis[
                "operations"
            ],
            "detected_merge_operation_count": len(
                detected_merge_operations
            ),
            "detected_merge_operations": (
                detected_merge_operations
            ),
            "detected_join_keys": (
                builder_analysis[
                    "detected_join_keys"
                ]
            ),
            "detected_filter_count": len(
                builder_analysis[
                    "detected_filters"
                ]
            ),
            "detected_filters": (
                builder_analysis[
                    "detected_filters"
                ]
            ),
        },
        "join_profile": {
            "shared_column_count": len(
                shared_columns
            ),
            "shared_columns": shared_columns,
            "identifier_columns": (
                identifier_columns
            ),
            "single_key_profile_count": len(
                single_key_profiles
            ),
            "composite_key_profile_count": len(
                composite_key_profiles
            ),
            "positive_profile_count": len(
                positive_profiles
            ),
            "zero_overlap_profile_count": len(
                zero_profiles
            ),
            "best_profile": best_profile,
            "source_detected_key_profiles": (
                source_detected_keys
            ),
            "top_profiles": all_profiles[:25],
        },
        "finding": {
            "classification": (
                collapse_classification
            ),
            "first_collapse_stage": (
                first_collapse_stage
            ),
            "direct_inputs_populated": True,
            "target_zero_row": True,
            "repair_authorised": False,
            "next_action": next_action,
        },
        "summary": {
            "rating_fact_rows": (
                rating["rows"]
            ),
            "race_entry_fact_rows": (
                race_entry["rows"]
            ),
            "target_output_rows": (
                target["rows"]
            ),
            "shared_column_count": len(
                shared_columns
            ),
            "detected_join_key_count": len(
                builder_analysis[
                    "detected_join_keys"
                ]
            ),
            "positive_join_profile_count": len(
                positive_profiles
            ),
            "classification": (
                collapse_classification
            ),
            "first_collapse_stage": (
                first_collapse_stage
            ),
            "next_action": next_action,
            "runtime_seconds": round(
                time.monotonic() - STARTED,
                3,
            ),
        },
    }

    OUTPUT_JSON.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    markdown = [
        "# EDGEIQ Performance Intelligence Target 001 Direct Input Trace V1",
        "",
        "## Verdict",
        "",
        "**PASS**",
        "",
        "## Producer",
        "",
        f"`{rel(PRODUCER_PATH)}`",
        "",
        "## Direct Dataset State",
        "",
        "| Dataset | Rows | Columns | Status |",
        "|---|---:|---:|---|",
        (
            f"| `{rating['path']}` "
            f"| {rating['rows']} "
            f"| {rating['columns']} "
            f"| POPULATED |"
        ),
        (
            f"| `{race_entry['path']}` "
            f"| {race_entry['rows']} "
            f"| {race_entry['columns']} "
            f"| POPULATED |"
        ),
        (
            f"| `{target['path']}` "
            f"| {target['rows']} "
            f"| {target['columns']} "
            f"| HEADER_ONLY |"
        ),
        "",
        "## Builder Source Analysis",
        "",
        (
            f"- Relevant operations detected: "
            f"`{len(builder_analysis['operations'])}`"
        ),
        (
            f"- Merge operations detected: "
            f"`{len(detected_merge_operations)}`"
        ),
        (
            f"- Statically detected join keys: "
            f"`{len(builder_analysis['detected_join_keys'])}`"
        ),
        (
            f"- Query-style filters detected: "
            f"`{len(builder_analysis['detected_filters'])}`"
        ),
        "",
        "### Detected Join Keys",
        "",
    ]

    if builder_analysis["detected_join_keys"]:
        for keys in builder_analysis[
            "detected_join_keys"
        ]:
            markdown.append(
                f"- `{', '.join(keys)}`"
            )
    else:
        markdown.append(
            "- No join key was statically resolved."
        )

    markdown.extend(
        [
            "",
            "## Join-Key Profiling",
            "",
            (
                f"- Shared columns: "
                f"`{len(shared_columns)}`"
            ),
            (
                f"- Single-key profiles: "
                f"`{len(single_key_profiles)}`"
            ),
            (
                f"- Composite profiles: "
                f"`{len(composite_key_profiles)}`"
            ),
            (
                f"- Profiles producing at least one "
                f"possible inner-join row: "
                f"`{len(positive_profiles)}`"
            ),
            "",
            "### Strongest Profiles",
            "",
            (
                "| Key | Type | Overlap values | "
                "Estimated inner rows | Zero overlap |"
            ),
            "|---|---|---:|---:|---|",
        ]
    )

    for profile in all_profiles[:15]:
        markdown.append(
            f"| `{profile['key_columns']}` "
            f"| {profile['key_type']} "
            f"| {profile['overlap_unique_values']} "
            f"| {profile['estimated_inner_join_rows']} "
            f"| {str(profile['zero_overlap']).upper()} |"
        )

    markdown.extend(
        [
            "",
            "## Governed Finding",
            "",
            f"**Classification:** `{collapse_classification}`",
            "",
            f"**First collapse stage:** `{first_collapse_stage}`",
            "",
            (
                "Both direct inputs are populated while the "
                "canonical output remains header-only."
            ),
            "",
            (
                "This unit did not execute or modify the "
                "producer. It inspected the governed source "
                "and replayed candidate joins entirely in memory."
            ),
            "",
            "## Governed Next Action",
            "",
            f"**{next_action}**",
            "",
            "No repair is authorised.",
            "",
        ]
    )

    OUTPUT_MD.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    log("PI_RESTART_UNIT_002C VERDICT=PASS")
    log(
        "RATING_FACT_ROWS="
        f"{rating['rows']}"
    )
    log(
        "RACE_ENTRY_FACT_ROWS="
        f"{race_entry['rows']}"
    )
    log(
        "TARGET_OUTPUT_ROWS="
        f"{target['rows']}"
    )
    log(
        "SHARED_COLUMN_COUNT="
        f"{len(shared_columns)}"
    )
    log(
        "DETECTED_JOIN_KEY_COUNT="
        f"{len(builder_analysis['detected_join_keys'])}"
    )
    log(
        "POSITIVE_JOIN_PROFILE_COUNT="
        f"{len(positive_profiles)}"
    )
    log(
        "CLASSIFICATION="
        f"{collapse_classification}"
    )
    log(
        "FIRST_COLLAPSE_STAGE="
        f"{first_collapse_stage}"
    )
    log(
        "NEXT_ACTION="
        f"{next_action}"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log("PI_RESTART_UNIT_002C VERDICT=FAIL")
        print(
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
