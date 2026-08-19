from __future__ import annotations

import ast
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = "EDGEIQ_EPI_WORKSPACE_BUILDER_FORENSICS_V1"

TARGET_BUILDER = Path(
    "scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py"
)

TARGET_FEED_NAME = "edgeiq_epi_workspace_terminal_feed_v1.csv"

TARGET_FIELDS = (
    "current_epi",
    "rank",
    "field_avg",
    "diff",
    "start_1",
    "start_1_context",
    "start_2",
    "start_2_context",
    "start_3",
    "start_3_context",
    "start_4",
    "start_4_context",
    "start_5",
    "start_5_context",
    "start_6",
    "start_6_context",
    "start_7",
    "start_7_context",
    "start_8",
    "start_8_context",
    "start_9",
    "start_9_context",
    "start_10",
    "start_10_context",
)

FILE_LITERAL_PATTERN = re.compile(
    r"""["']([^"']+\.(?:csv|json|parquet|feather|arrow|sqlite|db))["']""",
    re.IGNORECASE,
)

FIELD_PATTERN_TEMPLATE = (
    r"""(?<![A-Za-z0-9_]){field}(?![A-Za-z0-9_])"""
)

OUTPUT_MARKERS = (
    "DictWriter",
    "writerow",
    "writerows",
    "to_csv",
    "write_text",
    "json.dump",
    "open(",
)

READ_MARKERS = (
    "DictReader",
    "csv.reader",
    "read_csv",
    "read_text",
    "json.load",
    "open(",
)

JOIN_MARKERS = (
    "merge(",
    ".join(",
    "lookup",
    "index",
    "mapping",
    "by_key",
    "setdefault",
    ".get(",
)

EMPTY_VALUE_MARKERS = (
    '""',
    "None",
    "null",
    "nan",
    "N/A",
)

KEY_NAME_HINTS = (
    "race_date",
    "meeting_date",
    "date",
    "track",
    "venue",
    "race_number",
    "race_no",
    "horse",
    "horse_name",
    "runner",
    "runner_name",
    "horse_code",
    "runner_code",
    "canonical_horse",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
    except OSError:
        return ""


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def resolve_literal_path(
    root: Path,
    builder_path: Path,
    literal: str,
) -> Path | None:
    normalised = literal.replace("\\", "/")

    candidates = [
        root / normalised,
        builder_path.parent / normalised,
        root / "public" / "data" / Path(normalised).name,
        root / "data" / Path(normalised).name,
        root / "docs" / "performance-intelligence" / Path(normalised).name,
    ]

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue

        if resolved.exists() and resolved.is_file():
            return resolved

    matches = [
        path
        for path in root.rglob(Path(normalised).name)
        if path.is_file()
        and ".git" not in path.parts
        and "node_modules" not in path.parts
        and "checkpoints" not in {
            part.lower()
            for part in path.parts
        }
    ]

    if not matches:
        return None

    return max(
        matches,
        key=lambda path: path.stat().st_mtime,
    )


def file_profile(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()

    result: dict[str, Any] = {
        "resolved_path": path.as_posix(),
        "file_type": suffix,
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "row_count": "",
        "column_count": "",
        "columns": "",
        "parse_status": "NOT_PROFILED",
    }

    if suffix == ".csv":
        try:
            rows = load_csv(path)
            columns = list(rows[0].keys()) if rows else []

            result.update(
                {
                    "row_count": len(rows),
                    "column_count": len(columns),
                    "columns": " | ".join(columns),
                    "parse_status": "PASS",
                }
            )
        except Exception as exc:
            result["parse_status"] = f"ERROR:{type(exc).__name__}"

    elif suffix == ".json":
        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8-sig",
                    errors="replace",
                )
            )

            if isinstance(payload, list):
                rows = payload
            elif isinstance(payload, dict):
                list_values = [
                    value
                    for value in payload.values()
                    if isinstance(value, list)
                ]
                rows = max(
                    list_values,
                    key=len,
                    default=[],
                )
            else:
                rows = []

            columns = (
                sorted(
                    {
                        key
                        for row in rows[:1000]
                        if isinstance(row, dict)
                        for key in row.keys()
                    }
                )
                if rows
                else []
            )

            result.update(
                {
                    "row_count": len(rows),
                    "column_count": len(columns),
                    "columns": " | ".join(columns),
                    "parse_status": "PASS",
                }
            )
        except Exception as exc:
            result["parse_status"] = f"ERROR:{type(exc).__name__}"

    return result


def extract_field_contexts(
    text: str,
    field: str,
) -> list[dict[str, Any]]:
    lines = text.splitlines()
    pattern = re.compile(
        FIELD_PATTERN_TEMPLATE.format(
            field=re.escape(field)
        ),
        re.IGNORECASE,
    )

    contexts: list[dict[str, Any]] = []

    for line_number, line in enumerate(lines, start=1):
        if not pattern.search(line):
            continue

        start = max(0, line_number - 7)
        end = min(len(lines), line_number + 7)

        context_lines = lines[start:end]

        contexts.append(
            {
                "field_name": field,
                "line_number": line_number,
                "source_line": line.strip(),
                "context": "\n".join(
                    f"{index + 1}: {value}"
                    for index, value in enumerate(
                        context_lines,
                        start=start,
                    )
                ),
                "assignment_suspected": bool(
                    re.search(
                        rf"""
                        (?:
                            \b{re.escape(field)}\b\s*=|
                            \[\s*["']{re.escape(field)}["']\s*\]\s*=|
                            ["']{re.escape(field)}["']\s*:
                        )
                        """,
                        line,
                        re.IGNORECASE | re.VERBOSE,
                    )
                ),
                "default_blank_suspected": any(
                    marker in line
                    for marker in EMPTY_VALUE_MARKERS
                ),
                "join_context_suspected": any(
                    marker.lower() in "\n".join(context_lines).lower()
                    for marker in JOIN_MARKERS
                ),
            }
        )

    return contexts


def extract_functions(text: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    lines = text.splitlines()
    results: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        start = node.lineno
        end = getattr(node, "end_lineno", node.lineno)

        body = "\n".join(lines[start - 1:end])
        referenced_fields = [
            field
            for field in TARGET_FIELDS
            if re.search(
                FIELD_PATTERN_TEMPLATE.format(
                    field=re.escape(field)
                ),
                body,
                re.IGNORECASE,
            )
        ]

        if not referenced_fields:
            continue

        results.append(
            {
                "function_name": node.name,
                "start_line": start,
                "end_line": end,
                "target_fields": " | ".join(referenced_fields),
                "contains_output_marker": any(
                    marker.lower() in body.lower()
                    for marker in OUTPUT_MARKERS
                ),
                "contains_read_marker": any(
                    marker.lower() in body.lower()
                    for marker in READ_MARKERS
                ),
                "contains_join_marker": any(
                    marker.lower() in body.lower()
                    for marker in JOIN_MARKERS
                ),
                "source_excerpt": body[:12000],
            }
        )

    return results


def key_usage_rows(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        lowered = line.lower()

        matched = [
            key
            for key in KEY_NAME_HINTS
            if re.search(
                rf"""(?<![a-z0-9_]){re.escape(key)}(?![a-z0-9_])""",
                lowered,
            )
        ]

        if not matched:
            continue

        rows.append(
            {
                "line_number": line_number,
                "keys_found": " | ".join(matched),
                "source_line": line.strip(),
                "mapping_or_join_suspected": any(
                    marker.lower() in lowered
                    for marker in JOIN_MARKERS
                ),
            }
        )

    return rows


def profile_target_fields_in_source(
    source_path: Path,
) -> list[dict[str, Any]]:
    suffix = source_path.suffix.lower()
    rows: list[dict[str, Any]] = []

    if suffix != ".csv":
        return rows

    try:
        data = load_csv(source_path)
    except Exception:
        return rows

    if not data:
        return rows

    fields = list(data[0].keys())

    for target in TARGET_FIELDS:
        matching_columns = [
            field
            for field in fields
            if field.lower() == target.lower()
            or target.lower() in field.lower()
            or field.lower() in target.lower()
        ]

        if not matching_columns:
            continue

        for column in matching_columns:
            values = [
                str(row.get(column, "") or "").strip()
                for row in data
            ]

            populated = [
                value
                for value in values
                if value
                and value.lower() not in {
                    "none",
                    "null",
                    "nan",
                    "na",
                    "n/a",
                }
            ]

            rows.append(
                {
                    "source_path": source_path.as_posix(),
                    "target_field": target,
                    "matched_source_column": column,
                    "source_row_count": len(data),
                    "populated_count": len(populated),
                    "empty_count": len(data) - len(populated),
                    "population_rate": (
                        round(len(populated) / len(data), 6)
                        if data
                        else 0
                    ),
                    "sample_values": " | ".join(
                        sorted(set(populated))[:10]
                    ),
                }
            )

    return rows


def main() -> int:
    root = Path.cwd().resolve()
    builder_path = root / TARGET_BUILDER

    output_root = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-d2-epi-builder-forensics"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    if not builder_path.exists():
        print(
            f"ERROR: Builder not found: {builder_path}",
            file=sys.stderr,
        )
        return 2

    builder_text = safe_read_text(builder_path)

    if not builder_text:
        print(
            f"ERROR: Builder could not be read: {builder_path}",
            file=sys.stderr,
        )
        return 2

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(f"builder={TARGET_BUILDER.as_posix()}", flush=True)
    print(
        f"builder_lines={len(builder_text.splitlines())}",
        flush=True,
    )

    print("\n[1/5] Extracting builder field logic...", flush=True)

    field_context_rows: list[dict[str, Any]] = []

    for field in TARGET_FIELDS:
        contexts = extract_field_contexts(
            builder_text,
            field,
        )
        field_context_rows.extend(contexts)

        print(
            f"[field] {field} occurrences={len(contexts)}",
            flush=True,
        )

    function_rows = extract_functions(builder_text)
    key_rows = key_usage_rows(builder_text)

    print("\n[2/5] Resolving builder source files...", flush=True)

    literals: list[str] = []

    for match in FILE_LITERAL_PATTERN.finditer(builder_text):
        value = match.group(1).replace("\\", "/")

        if value not in literals:
            literals.append(value)

    source_rows: list[dict[str, Any]] = []
    resolved_source_paths: list[Path] = []

    for literal in literals:
        resolved = resolve_literal_path(
            root,
            builder_path,
            literal,
        )

        if resolved is None:
            source_rows.append(
                {
                    "literal_path": literal,
                    "resolved_path": "",
                    "file_type": Path(literal).suffix.lower(),
                    "exists": False,
                    "size_bytes": 0,
                    "row_count": "",
                    "column_count": "",
                    "columns": "",
                    "parse_status": "NOT_FOUND",
                }
            )
            continue

        profile = file_profile(resolved)
        profile["literal_path"] = literal
        source_rows.append(profile)

        if resolved not in resolved_source_paths:
            resolved_source_paths.append(resolved)

        print(
            f"[source] {literal} -> "
            f"{resolved.relative_to(root).as_posix()} "
            f"rows={profile['row_count']}",
            flush=True,
        )

    print("\n[3/5] Profiling EPI fields in upstream sources...", flush=True)

    source_field_rows: list[dict[str, Any]] = []

    for source_path in resolved_source_paths:
        rows = profile_target_fields_in_source(source_path)
        source_field_rows.extend(rows)

        if rows:
            print(
                f"[source fields] "
                f"{source_path.relative_to(root).as_posix()} "
                f"matches={len(rows)}",
                flush=True,
            )

    print("\n[4/5] Classifying target fields...", flush=True)

    classification_rows: list[dict[str, Any]] = []

    context_by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in field_context_rows:
        context_by_field[row["field_name"]].append(row)

    source_fields_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in source_field_rows:
        source_fields_by_target[row["target_field"]].append(row)

    for field in TARGET_FIELDS:
        contexts = context_by_field.get(field, [])
        source_matches = source_fields_by_target.get(field, [])

        assignments = [
            row
            for row in contexts
            if row["assignment_suspected"]
        ]

        blank_defaults = [
            row
            for row in contexts
            if row["default_blank_suspected"]
        ]

        join_contexts = [
            row
            for row in contexts
            if row["join_context_suspected"]
        ]

        populated_source_matches = [
            row
            for row in source_matches
            if int(row["populated_count"]) > 0
        ]

        if not contexts:
            status = "MISSING_FROM_CANONICAL_BUILDER"

        elif assignments and populated_source_matches:
            status = "BUILDER_AND_UPSTREAM_DATA_PRESENT"

        elif assignments and source_matches and not populated_source_matches:
            status = "UPSTREAM_COLUMN_PRESENT_BUT_EMPTY"

        elif assignments and not source_matches and join_contexts:
            status = "DERIVED_OR_JOIN_DEPENDENT"

        elif assignments and not source_matches:
            status = "BUILDER_ASSIGNMENT_SOURCE_NOT_IDENTIFIED"

        elif blank_defaults and not assignments:
            status = "OUTPUT_DEFAULT_ONLY"

        else:
            status = "REFERENCE_ONLY_REVIEW"

        classification_rows.append(
            {
                "field_name": field,
                "builder_occurrence_count": len(contexts),
                "assignment_count": len(assignments),
                "blank_default_count": len(blank_defaults),
                "join_context_count": len(join_contexts),
                "upstream_column_match_count": len(source_matches),
                "upstream_populated_match_count": len(
                    populated_source_matches
                ),
                "builder_lines": ",".join(
                    str(row["line_number"])
                    for row in contexts
                ),
                "upstream_matches": " | ".join(
                    (
                        f"{row['source_path']}:"
                        f"{row['matched_source_column']}:"
                        f"{row['population_rate']}"
                    )
                    for row in source_matches
                ),
                "forensic_status": status,
            }
        )

        print(
            f"[classification] {field} -> {status}",
            flush=True,
        )

    print("\n[5/5] Writing governed outputs...", flush=True)

    write_csv(
        output_root / f"{AUDIT_ID}_FIELD_CONTEXTS.csv",
        field_context_rows,
        [
            "field_name",
            "line_number",
            "source_line",
            "assignment_suspected",
            "default_blank_suspected",
            "join_context_suspected",
            "context",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_FUNCTIONS.csv",
        function_rows,
        [
            "function_name",
            "start_line",
            "end_line",
            "target_fields",
            "contains_output_marker",
            "contains_read_marker",
            "contains_join_marker",
            "source_excerpt",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_SOURCE_FILES.csv",
        source_rows,
        [
            "literal_path",
            "resolved_path",
            "file_type",
            "exists",
            "size_bytes",
            "row_count",
            "column_count",
            "columns",
            "parse_status",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_SOURCE_FIELD_POPULATION.csv",
        source_field_rows,
        [
            "source_path",
            "target_field",
            "matched_source_column",
            "source_row_count",
            "populated_count",
            "empty_count",
            "population_rate",
            "sample_values",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_JOIN_KEY_USAGE.csv",
        key_rows,
        [
            "line_number",
            "keys_found",
            "source_line",
            "mapping_or_join_suspected",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_FIELD_CLASSIFICATION.csv",
        classification_rows,
        [
            "field_name",
            "builder_occurrence_count",
            "assignment_count",
            "blank_default_count",
            "join_context_count",
            "upstream_column_match_count",
            "upstream_populated_match_count",
            "builder_lines",
            "upstream_matches",
            "forensic_status",
        ],
    )

    status_counts: dict[str, int] = defaultdict(int)

    for row in classification_rows:
        status_counts[row["forensic_status"]] += 1

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": now_utc(),
        "target_builder": TARGET_BUILDER.as_posix(),
        "target_feed": TARGET_FEED_NAME,
        "builder_line_count": len(builder_text.splitlines()),
        "target_fields": len(TARGET_FIELDS),
        "field_context_rows": len(field_context_rows),
        "functions_with_target_fields": len(function_rows),
        "file_literals": len(literals),
        "resolved_source_files": len(resolved_source_paths),
        "source_field_matches": len(source_field_rows),
        "field_status_counts": dict(
            sorted(status_counts.items())
        ),
        "status": "REVIEW_REQUIRED",
    }

    (
        output_root / f"{AUDIT_ID}_SUMMARY.json"
    ).write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    builder_excerpt_path = (
        output_root
        / f"{AUDIT_ID}_CANONICAL_BUILDER_SOURCE.txt"
    )

    builder_excerpt_path.write_text(
        builder_text,
        encoding="utf-8",
    )

    print("\n=== PHASE D2 COMPLETE ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())