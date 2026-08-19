from __future__ import annotations

import ast
import csv
import json
import re
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = "EDGEIQ_EPI_WORKSPACE_LINEAGE_V1"
TARGET_FEED = "edgeiq_epi_workspace_terminal_feed_v1.csv"

SOURCE_EXTENSIONS = {".py"}

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
    "checkpoints",
    "checkpoint",
    "archive",
    "archives",
    "backup",
    "backups",
}

NON_PRODUCER_NAME_MARKERS = (
    "audit_",
    "verify_",
    "check_",
    "test_",
    "report",
    "readiness",
    "inventory",
    "baseline_doc",
    "browser_acceptance",
    "smoke",
)

FILE_LITERAL_PATTERN = re.compile(
    r"""["']([^"']+\.(?:csv|json|parquet|feather|arrow|sqlite|db))["']""",
    re.IGNORECASE,
)

PYTHON_SCRIPT_LITERAL_PATTERN = re.compile(
    r"""["']([^"']+\.py)["']""",
    re.IGNORECASE,
)

WRITE_MARKERS = (
    "write_text",
    "write_bytes",
    "csv.DictWriter",
    "csv.writer",
    "writerow",
    "writerows",
    "to_csv",
    "to_json",
    "json.dump",
    "json.dumps",
    "open(",
)

READ_MARKERS = (
    "csv.DictReader",
    "csv.reader",
    "json.load",
    "json.loads",
    "read_text",
    "read_csv",
    "read_json",
    "open(",
)

CALCULATION_MARKERS = (
    "mean(",
    "median(",
    "average",
    "sum(",
    "rank",
    "percentile",
    "stdev",
    "standard_deviation",
    "difference",
    "diff",
    "current_epi",
    "field_avg",
)

ORCHESTRATION_MARKERS = (
    "subprocess",
    "runpy",
    "exec(",
    "python",
    "Popen",
    "check_call",
    "check_output",
    "import_module",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def is_excluded(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True

    lowered_parts = {part.lower() for part in relative.parts}

    return bool(lowered_parts.intersection(EXCLUDED_DIRECTORY_NAMES))


def normalise(path: Path) -> str:
    return path.as_posix()


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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


def find_target_feed(root: Path) -> list[Path]:
    matches: list[Path] = []

    for path in root.rglob(TARGET_FEED):
        if path.is_file() and not is_excluded(path, root):
            matches.append(path)

    return sorted(matches)


def profile_feed(path: Path) -> tuple[int, list[dict[str, Any]]]:
    rows = load_csv(path)

    if not rows:
        return 0, []

    fields = list(rows[0].keys())
    profile_rows: list[dict[str, Any]] = []

    for field in fields:
        values = [
            str(row.get(field, "") or "").strip()
            for row in rows
        ]

        populated = [
            value
            for value in values
            if value
            and value.lower() not in {
                "none",
                "null",
                "nan",
                "n/a",
                "na",
            }
        ]

        unique_values = sorted(set(populated))

        profile_rows.append(
            {
                "field_name": field,
                "row_count": len(rows),
                "populated_count": len(populated),
                "empty_count": len(rows) - len(populated),
                "population_rate": (
                    round(len(populated) / len(rows), 6)
                    if rows
                    else 0.0
                ),
                "unique_populated_count": len(unique_values),
                "constant_value_suspected": (
                    len(populated) > 0
                    and len(unique_values) == 1
                ),
                "sample_values": " | ".join(unique_values[:8]),
            }
        )

    return len(rows), profile_rows


def parse_imported_local_modules(
    path: Path,
    text: str,
    root: Path,
) -> list[str]:
    results: list[str] = []

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return results

    module_paths: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            module_paths.extend(alias.name for alias in node.names)

        elif isinstance(node, ast.ImportFrom) and node.module:
            module_paths.append(node.module)

    for module_name in module_paths:
        candidate_relative = Path(*module_name.split(".")).with_suffix(".py")

        search_candidates = [
            root / candidate_relative,
            path.parent / candidate_relative.name,
            root / "scripts" / candidate_relative.name,
        ]

        for candidate in search_candidates:
            if candidate.exists() and candidate.is_file():
                relative = normalise(candidate.relative_to(root))

                if relative not in results:
                    results.append(relative)

    return results


def parse_called_scripts(
    path: Path,
    text: str,
    root: Path,
) -> list[str]:
    results: list[str] = []

    for match in PYTHON_SCRIPT_LITERAL_PATTERN.finditer(text):
        literal = match.group(1).replace("\\", "/")
        literal_name = Path(literal).name

        candidates = [
            root / literal,
            path.parent / literal,
            root / "scripts" / literal_name,
        ]

        for candidate in candidates:
            try:
                candidate = candidate.resolve()
            except OSError:
                continue

            if candidate.exists() and candidate.is_file():
                try:
                    relative = normalise(candidate.relative_to(root))
                except ValueError:
                    continue

                if relative not in results:
                    results.append(relative)

    return results


def script_features(
    relative: str,
    text: str,
    target_fields: set[str],
) -> dict[str, Any]:
    lowered = text.lower()
    name = Path(relative).name.lower()
    lines = text.splitlines()

    target_feed_lines = [
        number
        for number, line in enumerate(lines, start=1)
        if TARGET_FEED.lower() in line.lower()
    ]

    write_lines: list[int] = []

    for target_line in target_feed_lines:
        start = max(0, target_line - 12)
        end = min(len(lines), target_line + 18)
        context = "\n".join(lines[start:end])

        if any(marker.lower() in context.lower() for marker in WRITE_MARKERS):
            write_lines.append(target_line)

    fields_found = sorted(
        field
        for field in target_fields
        if re.search(
            rf"""(?<![A-Za-z0-9_]){re.escape(field)}(?![A-Za-z0-9_])""",
            text,
            flags=re.IGNORECASE,
        )
    )

    assignment_fields: list[str] = []
    output_fields: list[str] = []

    for field in fields_found:
        escaped = re.escape(field)

        assignment_patterns = (
            rf"""(?m)^\s*{escaped}\s*=""",
            rf"""(?m)^\s*[A-Za-z_][A-Za-z0-9_]*\s*\[\s*["']{escaped}["']\s*\]\s*=""",
            rf"""(?m)^\s*["']{escaped}["']\s*:\s*""",
        )

        if any(re.search(pattern, text) for pattern in assignment_patterns):
            assignment_fields.append(field)

        if (
            re.search(
                rf"""["']{escaped}["']\s*:""",
                text,
                flags=re.IGNORECASE,
            )
            or re.search(
                rf"""fieldnames\s*=\s*\[[^\]]*["']{escaped}["']""",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
        ):
            output_fields.append(field)

    file_literals = []

    for match in FILE_LITERAL_PATTERN.finditer(text):
        literal = match.group(1).replace("\\", "/")

        if literal not in file_literals:
            file_literals.append(literal)

    producer_score = 0

    if name.startswith("build_"):
        producer_score += 20

    if "epi" in name:
        producer_score += 20

    if "workspace" in name:
        producer_score += 10

    if "terminal_feed" in name:
        producer_score += 10

    if target_feed_lines:
        producer_score += 20

    producer_score += len(write_lines) * 30
    producer_score += min(len(assignment_fields), 20)
    producer_score += min(len(output_fields), 20)

    if any(marker in name for marker in NON_PRODUCER_NAME_MARKERS):
        producer_score -= 35

    is_orchestrator = any(
        marker.lower() in lowered
        for marker in ORCHESTRATION_MARKERS
    )

    if is_orchestrator and not write_lines:
        producer_score -= 10

    return {
        "script_path": relative,
        "producer_score": producer_score,
        "target_feed_reference_count": len(target_feed_lines),
        "target_feed_reference_lines": ",".join(
            str(value)
            for value in target_feed_lines[:20]
        ),
        "target_feed_write_evidence_count": len(write_lines),
        "target_feed_write_evidence_lines": ",".join(
            str(value)
            for value in write_lines[:20]
        ),
        "is_orchestrator_suspected": is_orchestrator,
        "write_marker_count": sum(
            lowered.count(marker.lower())
            for marker in WRITE_MARKERS
        ),
        "read_marker_count": sum(
            lowered.count(marker.lower())
            for marker in READ_MARKERS
        ),
        "calculation_marker_count": sum(
            lowered.count(marker.lower())
            for marker in CALCULATION_MARKERS
        ),
        "problem_field_reference_count": len(fields_found),
        "problem_fields_found": " | ".join(fields_found),
        "problem_field_assignment_count": len(assignment_fields),
        "problem_fields_assigned": " | ".join(assignment_fields),
        "problem_field_output_count": len(output_fields),
        "problem_fields_output": " | ".join(output_fields),
        "file_literals": " | ".join(file_literals[:30]),
    }


def field_lineage_rows(
    target_fields: list[dict[str, Any]],
    script_rows: list[dict[str, Any]],
    source_text: dict[str, str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    ranked_scripts = sorted(
        script_rows,
        key=lambda row: (
            -int(row["target_feed_write_evidence_count"]),
            -int(row["producer_score"]),
            row["script_path"],
        ),
    )

    candidate_paths = [
        row["script_path"]
        for row in ranked_scripts[:40]
    ]

    for problem in target_fields:
        field = problem["field_name"]
        escaped = re.escape(field)

        reference_files: list[str] = []
        assignment_files: list[str] = []
        output_files: list[str] = []
        calculation_files: list[str] = []
        occurrences: list[str] = []

        for relative in candidate_paths:
            text = source_text.get(relative, "")

            if not text:
                continue

            matching_lines = [
                number
                for number, line in enumerate(
                    text.splitlines(),
                    start=1,
                )
                if re.search(
                    rf"""(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])""",
                    line,
                    flags=re.IGNORECASE,
                )
            ]

            if not matching_lines:
                continue

            reference_files.append(relative)
            occurrences.append(
                f"{relative}:{','.join(str(number) for number in matching_lines[:15])}"
            )

            assignment_patterns = (
                rf"""(?m)^\s*{escaped}\s*=""",
                rf"""(?m)^\s*[A-Za-z_][A-Za-z0-9_]*\s*\[\s*["']{escaped}["']\s*\]\s*=""",
                rf"""(?m)^\s*["']{escaped}["']\s*:\s*""",
            )

            if any(
                re.search(pattern, text)
                for pattern in assignment_patterns
            ):
                assignment_files.append(relative)

            if (
                re.search(
                    rf"""["']{escaped}["']\s*:""",
                    text,
                    flags=re.IGNORECASE,
                )
                or re.search(
                    rf"""fieldnames\s*=\s*\[[^\]]*["']{escaped}["']""",
                    text,
                    flags=re.IGNORECASE | re.DOTALL,
                )
            ):
                output_files.append(relative)

            for matching_line in matching_lines:
                lines = text.splitlines()
                start = max(0, matching_line - 5)
                end = min(len(lines), matching_line + 6)
                context = "\n".join(lines[start:end]).lower()

                if any(
                    marker.lower() in context
                    for marker in CALCULATION_MARKERS
                ):
                    calculation_files.append(relative)
                    break

        reference_files = sorted(set(reference_files))
        assignment_files = sorted(set(assignment_files))
        output_files = sorted(set(output_files))
        calculation_files = sorted(set(calculation_files))

        population_issue = problem["population_issue"]

        if not reference_files:
            status = "FIELD_ABSENT_FROM_PRODUCER_CHAIN"
        elif output_files and calculation_files:
            status = (
                "LOGIC_AND_OUTPUT_PRESENT_BUT_EMPTY"
                if population_issue == "EMPTY"
                else "LOGIC_AND_OUTPUT_PRESENT_PARTIAL"
            )
        elif output_files and not calculation_files:
            status = "OUTPUT_DECLARED_CALCULATION_NOT_CONFIRMED"
        elif calculation_files and not output_files:
            status = "CALCULATION_PRESENT_OUTPUT_NOT_CONFIRMED"
        elif assignment_files:
            status = "ASSIGNMENT_PRESENT_LINEAGE_INCOMPLETE"
        else:
            status = "REFERENCE_ONLY"

        results.append(
            {
                "feed_name": TARGET_FEED,
                "field_name": field,
                "population_issue": population_issue,
                "population_rate": problem.get("population_rate", ""),
                "populated_count": problem.get("populated_count", ""),
                "empty_count": problem.get("empty_count", ""),
                "reference_files": " | ".join(reference_files),
                "assignment_files": " | ".join(assignment_files),
                "calculation_files": " | ".join(calculation_files),
                "output_files": " | ".join(output_files),
                "occurrences": " | ".join(occurrences),
                "lineage_status": status,
            }
        )

    return results


def main() -> int:
    root = Path.cwd().resolve()

    phase_b_root = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-b-runtime-feed-population"
    )

    empty_path = (
        phase_b_root
        / "EDGEIQ_RUNTIME_FEED_POPULATION_V1_EMPTY_FIELDS.csv"
    )

    low_path = (
        phase_b_root
        / "EDGEIQ_RUNTIME_FEED_POPULATION_V1_LOW_POPULATION_FIELDS.csv"
    )

    output_root = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-d1-epi-workspace-lineage"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    if not empty_path.exists() or not low_path.exists():
        print(
            "ERROR: Phase B population audit files were not found.",
            file=sys.stderr,
        )
        return 2

    empty_rows = [
        {
            **row,
            "population_issue": "EMPTY",
        }
        for row in load_csv(empty_path)
        if Path(row.get("feed_path", "")).name == TARGET_FEED
    ]

    low_rows = [
        {
            **row,
            "population_issue": "LOW_POPULATION",
        }
        for row in load_csv(low_path)
        if Path(row.get("feed_path", "")).name == TARGET_FEED
    ]

    problem_rows = empty_rows + low_rows
    target_fields = {
        row["field_name"]
        for row in problem_rows
        if row.get("field_name")
    }

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(f"target_feed={TARGET_FEED}", flush=True)
    print(f"empty_fields={len(empty_rows)}", flush=True)
    print(f"low_population_fields={len(low_rows)}", flush=True)

    feed_matches = find_target_feed(root)

    print(f"physical_feed_matches={len(feed_matches)}", flush=True)

    feed_profile_rows: list[dict[str, Any]] = []
    selected_feed_path = ""

    if feed_matches:
        selected = max(
            feed_matches,
            key=lambda path: path.stat().st_mtime,
        )

        selected_feed_path = normalise(selected.relative_to(root))
        row_count, feed_profile_rows = profile_feed(selected)

        print(
            f"selected_feed={selected_feed_path}",
            flush=True,
        )
        print(
            f"selected_feed_rows={row_count}",
            flush=True,
        )
    else:
        print("selected_feed=NOT_FOUND", flush=True)

    print("\n[1/4] Indexing eligible Python scripts...", flush=True)

    python_files = sorted(
        path
        for path in root.rglob("*.py")
        if path.is_file()
        and not is_excluded(path, root)
    )

    source_text: dict[str, str] = {}

    for index, path in enumerate(python_files, start=1):
        relative = normalise(path.relative_to(root))
        text = safe_read_text(path)

        if text:
            source_text[relative] = text

        if index % 500 == 0 or index == len(python_files):
            print(
                f"[index] {index}/{len(python_files)}",
                flush=True,
            )

    print("\n[2/4] Discovering producer and orchestration chain...", flush=True)

    direct_seed_scripts = sorted(
        relative
        for relative, text in source_text.items()
        if TARGET_FEED.lower() in text.lower()
    )

    graph: dict[str, set[str]] = defaultdict(set)

    for relative, text in source_text.items():
        path = root / relative

        for target in parse_called_scripts(path, text, root):
            graph[relative].add(target)

        for target in parse_imported_local_modules(path, text, root):
            graph[relative].add(target)

    reachable: set[str] = set(direct_seed_scripts)
    queue: deque[tuple[str, int]] = deque(
        (relative, 0)
        for relative in direct_seed_scripts
    )
    depth_by_script: dict[str, int] = {
        relative: 0
        for relative in direct_seed_scripts
    }

    while queue:
        current, depth = queue.popleft()

        if depth >= 5:
            continue

        for neighbour in graph.get(current, set()):
            if neighbour not in source_text:
                continue

            next_depth = depth + 1

            if (
                neighbour not in depth_by_script
                or next_depth < depth_by_script[neighbour]
            ):
                depth_by_script[neighbour] = next_depth

            if neighbour not in reachable:
                reachable.add(neighbour)
                queue.append((neighbour, next_depth))

    script_rows: list[dict[str, Any]] = []

    for relative in sorted(reachable):
        row = script_features(
            relative=relative,
            text=source_text[relative],
            target_fields=target_fields,
        )

        row["graph_depth"] = depth_by_script.get(relative, "")
        row["called_scripts"] = " | ".join(
            sorted(graph.get(relative, set()))
        )

        script_rows.append(row)

    script_rows.sort(
        key=lambda row: (
            -int(row["target_feed_write_evidence_count"]),
            -int(row["producer_score"]),
            int(row["graph_depth"])
            if str(row["graph_depth"]).isdigit()
            else 999,
            row["script_path"],
        )
    )

    print(
        f"direct_seed_scripts={len(direct_seed_scripts)}",
        flush=True,
    )
    print(
        f"reachable_candidate_scripts={len(script_rows)}",
        flush=True,
    )

    for row in script_rows[:20]:
        print(
            "[candidate] "
            f"score={row['producer_score']} "
            f"writes={row['target_feed_write_evidence_count']} "
            f"depth={row['graph_depth']} "
            f"{row['script_path']}",
            flush=True,
        )

    print("\n[3/4] Tracing EPI problem fields...", flush=True)

    lineage_rows = field_lineage_rows(
        target_fields=problem_rows,
        script_rows=script_rows,
        source_text=source_text,
    )

    status_counts: dict[str, int] = defaultdict(int)

    for row in lineage_rows:
        status_counts[row["lineage_status"]] += 1

    print("\n[4/4] Writing governed outputs...", flush=True)

    output_root.mkdir(parents=True, exist_ok=True)

    write_csv(
        output_root / f"{AUDIT_ID}_PRODUCER_CANDIDATES.csv",
        script_rows,
        [
            "script_path",
            "producer_score",
            "graph_depth",
            "target_feed_reference_count",
            "target_feed_reference_lines",
            "target_feed_write_evidence_count",
            "target_feed_write_evidence_lines",
            "is_orchestrator_suspected",
            "write_marker_count",
            "read_marker_count",
            "calculation_marker_count",
            "problem_field_reference_count",
            "problem_fields_found",
            "problem_field_assignment_count",
            "problem_fields_assigned",
            "problem_field_output_count",
            "problem_fields_output",
            "file_literals",
            "called_scripts",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_FIELD_LINEAGE.csv",
        lineage_rows,
        [
            "feed_name",
            "field_name",
            "population_issue",
            "population_rate",
            "populated_count",
            "empty_count",
            "reference_files",
            "assignment_files",
            "calculation_files",
            "output_files",
            "occurrences",
            "lineage_status",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_CURRENT_FEED_PROFILE.csv",
        feed_profile_rows,
        [
            "field_name",
            "row_count",
            "populated_count",
            "empty_count",
            "population_rate",
            "unique_populated_count",
            "constant_value_suspected",
            "sample_values",
        ],
    )

    remediation_rows = [
        row
        for row in lineage_rows
        if row["lineage_status"] not in {
            "LOGIC_AND_OUTPUT_PRESENT_PARTIAL",
        }
    ]

    write_csv(
        output_root / f"{AUDIT_ID}_REMEDIATION_QUEUE.csv",
        remediation_rows,
        [
            "feed_name",
            "field_name",
            "population_issue",
            "population_rate",
            "populated_count",
            "empty_count",
            "reference_files",
            "assignment_files",
            "calculation_files",
            "output_files",
            "occurrences",
            "lineage_status",
        ],
    )

    leaf_candidates = [
        row
        for row in script_rows
        if int(row["target_feed_write_evidence_count"]) > 0
    ]

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": now_utc(),
        "target_feed": TARGET_FEED,
        "selected_physical_feed": selected_feed_path,
        "physical_feed_matches": len(feed_matches),
        "empty_problem_fields": len(empty_rows),
        "low_population_problem_fields": len(low_rows),
        "direct_seed_scripts": len(direct_seed_scripts),
        "reachable_candidate_scripts": len(script_rows),
        "write_confirmed_leaf_candidates": len(leaf_candidates),
        "top_write_confirmed_candidate": (
            leaf_candidates[0]["script_path"]
            if leaf_candidates
            else ""
        ),
        "lineage_status_counts": dict(
            sorted(status_counts.items())
        ),
        "remediation_queue_rows": len(remediation_rows),
        "status": (
            "REVIEW_REQUIRED"
            if remediation_rows
            else "PASS"
        ),
    }

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
        "## Target",
        "",
        f"- Feed: {TARGET_FEED}",
        f"- Physical feed: {selected_feed_path or 'NOT FOUND'}",
        f"- Empty fields: {len(empty_rows)}",
        f"- Low-population fields: {len(low_rows)}",
        "",
        "## Producer Resolution",
        "",
        f"- Direct seed scripts: {len(direct_seed_scripts)}",
        f"- Reachable candidate scripts: {len(script_rows)}",
        f"- Write-confirmed candidates: {len(leaf_candidates)}",
        (
            "- Top write-confirmed candidate: "
            f"{summary['top_write_confirmed_candidate'] or 'NONE'}"
        ),
        "",
        "## Field-Lineage Status",
        "",
    ]

    for status, count in sorted(status_counts.items()):
        report_lines.append(f"- {status}: {count}")

    report_lines.extend(
        [
            "",
            "## Result",
            "",
            f"- Remediation queue rows: {len(remediation_rows)}",
            f"- Status: {summary['status']}",
            "",
        ]
    )

    (
        output_root / f"{AUDIT_ID}_REPORT.md"
    ).write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print("\n=== PHASE D1 COMPLETE ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())