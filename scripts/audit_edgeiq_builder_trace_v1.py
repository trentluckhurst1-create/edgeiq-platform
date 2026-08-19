from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = "EDGEIQ_BUILDER_TRACE_V1"

SOURCE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
}

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".vite",
    ".cache",
    "venv",
    ".venv",
    "env",
}

BUILDER_NAME_MARKERS = (
    "build_",
    "builder",
    "apply_",
    "generate_",
    "materialise",
    "materialize",
    "terminal_feed",
    "product_feed",
    "warehouse",
)

WRITE_MARKERS = (
    "csv.DictWriter",
    "csv.writer",
    "writerow",
    "writerows",
    "write_text",
    "json.dump",
    "json.dumps",
    "to_csv",
    "to_json",
    "write_csv",
    "write_json",
)

SOURCE_PATH_PATTERN = re.compile(
    r"""["']([^"']+\.(?:csv|json|parquet|sqlite|db|feather|arrow))["']""",
    re.IGNORECASE,
)

IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")

ASSIGNMENT_TEMPLATE = (
    r"(?m)^\s*{field}\s*=",
    r"(?m)^\s*[A-Za-z_][A-Za-z0-9_]*\[{quote}{field}{quote}\]\s*=",
    r"(?m)^\s*[A-Za-z_][A-Za-z0-9_]*\.get\({quote}{field}{quote}",
    r"(?m)^\s*{quote}{field}{quote}\s*:",
)

OUTPUT_FIELD_TEMPLATE = (
    r"[\"']{field}[\"']\s*:",
    r"fieldnames\s*=\s*\[[^\]]*[\"']{field}[\"']",
    r"columns\s*=\s*\[[^\]]*[\"']{field}[\"']",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalise_path(path: Path) -> str:
    return path.as_posix()


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRECTORY_NAMES for part in path.parts)


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


def builder_score(relative_path: str, text: str, feed_name: str) -> int:
    lowered_path = relative_path.lower()
    lowered_text = text.lower()
    feed_lower = feed_name.lower()
    feed_stem = Path(feed_name).stem.lower()

    score = 0

    if lowered_path.startswith("scripts/"):
        score += 8

    if "/scripts/" in f"/{lowered_path}":
        score += 4

    if Path(lowered_path).suffix == ".py":
        score += 5

    if any(marker in Path(lowered_path).name for marker in BUILDER_NAME_MARKERS):
        score += 8

    if feed_lower in lowered_text:
        score += 15

    if feed_stem in lowered_text:
        score += 10

    if any(marker.lower() in lowered_text for marker in WRITE_MARKERS):
        score += 4

    if "public/data" in lowered_text or "performance-intelligence" in lowered_text:
        score += 3

    return score


def contains_field_assignment(text: str, field: str) -> bool:
    escaped = re.escape(field)

    patterns = []

    for template in ASSIGNMENT_TEMPLATE:
        patterns.append(
            template.format(
                field=escaped,
                quote=r"""["']""",
            )
        )

    return any(re.search(pattern, text) for pattern in patterns)


def contains_output_write(text: str, field: str) -> bool:
    escaped = re.escape(field)

    direct_field_pattern = re.compile(
        rf"""["']{escaped}["']""",
        re.IGNORECASE,
    )

    if not direct_field_pattern.search(text):
        return False

    if any(marker in text for marker in WRITE_MARKERS):
        return True

    for template in OUTPUT_FIELD_TEMPLATE:
        pattern = template.format(field=escaped)

        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            return True

    return False


def line_numbers_for_field(text: str, field: str) -> list[int]:
    pattern = re.compile(
        rf"\b{re.escape(field)}\b",
        re.IGNORECASE,
    )

    matches: list[int] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        if pattern.search(line):
            matches.append(line_number)

        if len(matches) >= 12:
            break

    return matches


def source_hints(
    text: str,
    output_feed_name: str,
) -> list[str]:
    hints: list[str] = []
    output_lower = output_feed_name.lower()

    for match in SOURCE_PATH_PATTERN.finditer(text):
        value = match.group(1).replace("\\", "/")

        if Path(value).name.lower() == output_lower:
            continue

        if value not in hints:
            hints.append(value)

        if len(hints) >= 12:
            break

    return hints


def classify_trace(
    builder_candidates: list[dict[str, Any]],
    field_found_files: list[str],
    assignment_found: bool,
    output_write_found: bool,
    population_issue: str,
) -> str:
    if not builder_candidates:
        return "NO_BUILDER_IDENTIFIED"

    if not field_found_files:
        return "FIELD_NOT_FOUND_IN_BUILDER"

    if assignment_found and output_write_found:
        if population_issue == "EMPTY":
            return "LOGIC_PRESENT_BUT_OUTPUT_EMPTY"
        return "LOGIC_PRESENT_PARTIAL_POPULATION"

    if assignment_found and not output_write_found:
        return "CALCULATED_BUT_WRITE_NOT_CONFIRMED"

    if output_write_found and not assignment_found:
        return "OUTPUT_FIELD_DECLARED_CALCULATION_NOT_CONFIRMED"

    return "FIELD_REFERENCE_ONLY"


def main() -> int:
    root = Path.cwd().resolve()

    phase_b_root = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-b-runtime-feed-population"
    )

    empty_fields_path = (
        phase_b_root
        / "EDGEIQ_RUNTIME_FEED_POPULATION_V1_EMPTY_FIELDS.csv"
    )

    low_fields_path = (
        phase_b_root
        / "EDGEIQ_RUNTIME_FEED_POPULATION_V1_LOW_POPULATION_FIELDS.csv"
    )

    if not empty_fields_path.exists():
        print(
            f"ERROR: Missing Phase B file: {empty_fields_path}",
            file=sys.stderr,
        )
        return 2

    if not low_fields_path.exists():
        print(
            f"ERROR: Missing Phase B file: {low_fields_path}",
            file=sys.stderr,
        )
        return 2

    output_root = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-c-builder-trace"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    empty_rows = load_csv(empty_fields_path)
    low_rows = load_csv(low_fields_path)

    problem_rows: list[dict[str, Any]] = []

    for row in empty_rows:
        problem_rows.append(
            {
                **row,
                "population_issue": "EMPTY",
            }
        )

    for row in low_rows:
        problem_rows.append(
            {
                **row,
                "population_issue": "LOW_POPULATION",
            }
        )

    feed_names = sorted(
        {
            Path(row["feed_path"]).name
            for row in problem_rows
        }
    )

    field_names = {
        row["field_name"]
        for row in problem_rows
        if row.get("field_name")
    }

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(f"problem_fields={len(problem_rows)}", flush=True)
    print(f"affected_feeds={len(feed_names)}", flush=True)
    print(f"unique_field_names={len(field_names)}", flush=True)

    print("\n[1/5] Discovering candidate source files...", flush=True)

    source_files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SOURCE_EXTENSIONS
        and not is_excluded(path.relative_to(root))
    )

    print(
        f"[source discovery complete] source_files={len(source_files)}",
        flush=True,
    )

    print("\n[2/5] Building source and identifier indexes...", flush=True)

    source_text: dict[str, str] = {}
    identifier_index: dict[str, set[str]] = defaultdict(set)
    feed_reference_index: dict[str, set[str]] = defaultdict(set)

    for index, path in enumerate(source_files, start=1):
        relative = normalise_path(path.relative_to(root))
        text = safe_read_text(path)

        if not text:
            continue

        source_text[relative] = text
        identifiers = set(IDENTIFIER_PATTERN.findall(text))

        for identifier in identifiers.intersection(field_names):
            identifier_index[identifier].add(relative)

        lowered_text = text.lower()

        for feed_name in feed_names:
            feed_stem = Path(feed_name).stem

            if (
                feed_name.lower() in lowered_text
                or feed_stem.lower() in lowered_text
            ):
                feed_reference_index[feed_name].add(relative)

        if index % 500 == 0 or index == len(source_files):
            print(
                f"[index] {index}/{len(source_files)} {relative}",
                flush=True,
            )

    print("\n[3/5] Building runtime-feed builder index...", flush=True)

    builder_index_rows: list[dict[str, Any]] = []
    builders_by_feed: dict[str, list[dict[str, Any]]] = {}

    for feed_name in feed_names:
        candidates: list[dict[str, Any]] = []

        for relative in feed_reference_index.get(feed_name, set()):
            text = source_text[relative]
            score = builder_score(relative, text, feed_name)

            if score < 8:
                continue

            candidate = {
                "feed_name": feed_name,
                "candidate_builder": relative,
                "builder_score": score,
                "feed_filename_reference": (
                    feed_name.lower() in text.lower()
                ),
                "feed_stem_reference": (
                    Path(feed_name).stem.lower() in text.lower()
                ),
                "contains_write_marker": any(
                    marker in text
                    for marker in WRITE_MARKERS
                ),
            }

            candidates.append(candidate)

        candidates.sort(
            key=lambda row: (
                -int(row["builder_score"]),
                row["candidate_builder"],
            )
        )

        builders_by_feed[feed_name] = candidates[:12]
        builder_index_rows.extend(candidates[:12])

        top_builder = (
            candidates[0]["candidate_builder"]
            if candidates
            else "NONE"
        )

        print(
            f"[builder index] {feed_name} candidates={len(candidates)} "
            f"top={top_builder}",
            flush=True,
        )

    print("\n[4/5] Tracing problematic fields...", flush=True)

    trace_rows: list[dict[str, Any]] = []

    for index, problem in enumerate(problem_rows, start=1):
        feed_path = problem["feed_path"]
        feed_name = Path(feed_path).name
        field = problem["field_name"]
        population_issue = problem["population_issue"]

        builder_candidates = builders_by_feed.get(feed_name, [])
        candidate_paths = [
            row["candidate_builder"]
            for row in builder_candidates
        ]

        indexed_field_files = identifier_index.get(field, set())

        field_found_files = sorted(
            relative
            for relative in candidate_paths
            if relative in indexed_field_files
        )

        assignment_files: list[str] = []
        output_write_files: list[str] = []
        occurrence_details: list[str] = []
        upstream_hints: list[str] = []

        for relative in field_found_files:
            text = source_text[relative]

            if contains_field_assignment(text, field):
                assignment_files.append(relative)

            if contains_output_write(text, field):
                output_write_files.append(relative)

            line_numbers = line_numbers_for_field(text, field)

            if line_numbers:
                occurrence_details.append(
                    f"{relative}:{','.join(str(value) for value in line_numbers)}"
                )

            for hint in source_hints(text, feed_name):
                if hint not in upstream_hints:
                    upstream_hints.append(hint)

        status = classify_trace(
            builder_candidates=builder_candidates,
            field_found_files=field_found_files,
            assignment_found=bool(assignment_files),
            output_write_found=bool(output_write_files),
            population_issue=population_issue,
        )

        trace_rows.append(
            {
                "feed_path": feed_path,
                "feed_name": feed_name,
                "field_name": field,
                "population_issue": population_issue,
                "population_rate": problem.get("population_rate", ""),
                "sampled_rows": problem.get("sampled_rows", ""),
                "populated_count": problem.get("populated_count", ""),
                "empty_count": problem.get("empty_count", ""),
                "builder_candidate_count": len(builder_candidates),
                "top_builder_candidate": (
                    builder_candidates[0]["candidate_builder"]
                    if builder_candidates
                    else ""
                ),
                "top_builder_score": (
                    builder_candidates[0]["builder_score"]
                    if builder_candidates
                    else ""
                ),
                "field_found_in_builder": bool(field_found_files),
                "field_found_files": " | ".join(field_found_files),
                "calculation_or_assignment_found": bool(assignment_files),
                "calculation_files": " | ".join(assignment_files),
                "output_write_found": bool(output_write_files),
                "output_write_files": " | ".join(output_write_files),
                "field_occurrences": " | ".join(occurrence_details),
                "upstream_source_hints": " | ".join(upstream_hints[:12]),
                "trace_status": status,
            }
        )

        if index % 50 == 0 or index == len(problem_rows):
            print(
                f"[field trace] {index}/{len(problem_rows)} "
                f"{feed_name}:{field} -> {status}",
                flush=True,
            )

    print("\n[5/5] Writing governed outputs...", flush=True)

    missing_calculations = [
        row
        for row in trace_rows
        if row["trace_status"] in {
            "FIELD_NOT_FOUND_IN_BUILDER",
            "OUTPUT_FIELD_DECLARED_CALCULATION_NOT_CONFIRMED",
            "FIELD_REFERENCE_ONLY",
        }
    ]

    missing_writes = [
        row
        for row in trace_rows
        if row["trace_status"] == "CALCULATED_BUT_WRITE_NOT_CONFIRMED"
    ]

    no_builder = [
        row
        for row in trace_rows
        if row["trace_status"] == "NO_BUILDER_IDENTIFIED"
    ]

    logic_present_empty = [
        row
        for row in trace_rows
        if row["trace_status"] in {
            "LOGIC_PRESENT_BUT_OUTPUT_EMPTY",
            "LOGIC_PRESENT_PARTIAL_POPULATION",
        }
    ]

    status_counts: dict[str, int] = defaultdict(int)

    for row in trace_rows:
        status_counts[row["trace_status"]] += 1

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": now_utc(),
        "problem_field_rows": len(problem_rows),
        "empty_field_rows": len(empty_rows),
        "low_population_field_rows": len(low_rows),
        "affected_runtime_feeds": len(feed_names),
        "candidate_source_files_scanned": len(source_files),
        "feeds_with_builder_candidates": sum(
            1
            for feed_name in feed_names
            if builders_by_feed.get(feed_name)
        ),
        "feeds_without_builder_candidates": sum(
            1
            for feed_name in feed_names
            if not builders_by_feed.get(feed_name)
        ),
        "trace_status_counts": dict(sorted(status_counts.items())),
        "missing_calculation_rows": len(missing_calculations),
        "missing_write_rows": len(missing_writes),
        "no_builder_rows": len(no_builder),
        "logic_present_problem_rows": len(logic_present_empty),
        "status": (
            "FAIL"
            if no_builder
            else "REVIEW_REQUIRED"
            if missing_calculations or missing_writes or logic_present_empty
            else "PASS"
        ),
    }

    trace_fieldnames = [
        "feed_path",
        "feed_name",
        "field_name",
        "population_issue",
        "population_rate",
        "sampled_rows",
        "populated_count",
        "empty_count",
        "builder_candidate_count",
        "top_builder_candidate",
        "top_builder_score",
        "field_found_in_builder",
        "field_found_files",
        "calculation_or_assignment_found",
        "calculation_files",
        "output_write_found",
        "output_write_files",
        "field_occurrences",
        "upstream_source_hints",
        "trace_status",
    ]

    write_csv(
        output_root / f"{AUDIT_ID}_EMPTY_FIELD_TRACE.csv",
        trace_rows,
        trace_fieldnames,
    )

    write_csv(
        output_root / f"{AUDIT_ID}_BUILDER_INDEX.csv",
        builder_index_rows,
        [
            "feed_name",
            "candidate_builder",
            "builder_score",
            "feed_filename_reference",
            "feed_stem_reference",
            "contains_write_marker",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_MISSING_CALCULATIONS.csv",
        missing_calculations,
        trace_fieldnames,
    )

    write_csv(
        output_root / f"{AUDIT_ID}_MISSING_WRITES.csv",
        missing_writes,
        trace_fieldnames,
    )

    write_csv(
        output_root / f"{AUDIT_ID}_NO_BUILDER_IDENTIFIED.csv",
        no_builder,
        trace_fieldnames,
    )

    write_csv(
        output_root / f"{AUDIT_ID}_LOGIC_PRESENT_PROBLEMS.csv",
        logic_present_empty,
        trace_fieldnames,
    )

    (
        output_root / f"{AUDIT_ID}_SUMMARY.json"
    ).write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    report_lines = [
        f"# {AUDIT_ID}",
        "",
        f"Generated: {summary['generated_at_utc']}",
        "",
        "## Summary",
        "",
        f"- Problem field rows: {summary['problem_field_rows']}",
        f"- Empty field rows: {summary['empty_field_rows']}",
        f"- Low-population field rows: {summary['low_population_field_rows']}",
        f"- Affected runtime feeds: {summary['affected_runtime_feeds']}",
        f"- Source files scanned: {summary['candidate_source_files_scanned']}",
        f"- Feeds with builder candidates: {summary['feeds_with_builder_candidates']}",
        f"- Feeds without builder candidates: {summary['feeds_without_builder_candidates']}",
        f"- Missing-calculation rows: {summary['missing_calculation_rows']}",
        f"- Missing-write rows: {summary['missing_write_rows']}",
        f"- Logic-present problem rows: {summary['logic_present_problem_rows']}",
        f"- Overall status: {summary['status']}",
        "",
        "## Trace Status Counts",
        "",
    ]

    for status, count in sorted(status_counts.items()):
        report_lines.append(f"- {status}: {count}")

    report_lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- NO_BUILDER_IDENTIFIED means no credible source producer was found.",
            "- FIELD_NOT_FOUND_IN_BUILDER means the feed field is absent from its candidate producer.",
            "- CALCULATED_BUT_WRITE_NOT_CONFIRMED means calculation evidence exists but output mapping was not confirmed.",
            "- OUTPUT_FIELD_DECLARED_CALCULATION_NOT_CONFIRMED means the output schema contains the field but calculation evidence was not found.",
            "- LOGIC_PRESENT_BUT_OUTPUT_EMPTY means both calculation and write evidence exist, so upstream values or governed conditions require inspection.",
            "- LOGIC_PRESENT_PARTIAL_POPULATION means sparse population may be governed or upstream-dependent.",
            "",
        ]
    )

    (
        output_root / f"{AUDIT_ID}_REPORT.md"
    ).write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print("\n=== PHASE C COMPLETE ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())