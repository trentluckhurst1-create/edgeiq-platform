from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import ast
import json
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

BUILDER = (
    ROOT
    / "scripts"
    / "build_edgeiq_racingcom_csv_ingestion_v1.py"
)

INVESTIGATION_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "standard-time-investigation"
)

JSON_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_builder_remediation_map_v1.json"
)

REPORT_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_builder_remediation_map_v1.md"
)

EXCERPTS_OUT = (
    INVESTIGATION_DIR
    / "edgeiq_racingcom_builder_remediation_excerpts_v1.txt"
)


TARGET_NAMES = {
    "APP_ROOT",
    "PROJECT_ROOT",
    "RAW_CACHE",
    "MAX_FETCHES",
    "CLOUDFRONT_BASE",
}

SEARCH_PATTERNS = {
    "parent_resolution": re.compile(
        r"\.parents?\s*\[",
        re.IGNORECASE,
    ),
    "twelve_race_expansion": re.compile(
        r"range\s*\(\s*1\s*,\s*13\s*\)",
        re.IGNORECASE,
    ),
    "max_fetches_reference": re.compile(
        r"\bMAX_FETCHES\b",
        re.IGNORECASE,
    ),
    "fetch_break": re.compile(
        r"fetch_attempts\s*>=\s*MAX_FETCHES",
        re.IGNORECASE,
    ),
    "csv_url": re.compile(
        r"\bcsv_url\b",
        re.IGNORECASE,
    ),
    "drop_duplicates": re.compile(
        r"drop_duplicates",
        re.IGNORECASE,
    ),
    "sort_values": re.compile(
        r"sort_values|sorted\s*\(",
        re.IGNORECASE,
    ),
    "race_number": re.compile(
        r"race_no|race_number",
        re.IGNORECASE,
    ),
    "meetcode": re.compile(
        r"meetcode|meet_code",
        re.IGNORECASE,
    ),
    "discovery_method": re.compile(
        r"discovery_method",
        re.IGNORECASE,
    ),
}


def source_segment(
    lines: list[str],
    start: int,
    end: int,
    padding: int = 3,
) -> str:
    first = max(1, start - padding)
    last = min(len(lines), end + padding)

    rendered = []

    for line_number in range(first, last + 1):
        rendered.append(
            f"{line_number:05d}: "
            f"{lines[line_number - 1]}"
        )

    return "\n".join(rendered)


def assignment_name(
    node: ast.Assign | ast.AnnAssign,
) -> str:
    if isinstance(node, ast.AnnAssign):
        target = node.target

        if isinstance(target, ast.Name):
            return target.id

        return ""

    for target in node.targets:
        if isinstance(target, ast.Name):
            return target.id

    return ""


def main() -> int:
    print("EDGEIQ Racing.com Builder Remediation Map V1")
    print()

    if not BUILDER.exists():
        raise FileNotFoundError(
            f"Builder not found: {BUILDER}"
        )

    INVESTIGATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    text = BUILDER.read_text(
        encoding="utf-8",
    )

    lines = text.splitlines()
    tree = ast.parse(text)

    assignments: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    pattern_hits: list[dict[str, Any]] = []

    print("[1/4] Mapping governed constants...")

    for node in tree.body:
        if isinstance(
            node,
            (ast.Assign, ast.AnnAssign),
        ):
            name = assignment_name(node)

            if name not in TARGET_NAMES:
                continue

            start = node.lineno
            end = getattr(
                node,
                "end_lineno",
                node.lineno,
            )

            assignments.append(
                {
                    "name": name,
                    "start_line": start,
                    "end_line": end,
                    "source": source_segment(
                        lines,
                        start,
                        end,
                    ),
                }
            )

    print("[2/4] Mapping candidate and fetch functions...")

    for node in tree.body:
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        start = node.lineno
        end = getattr(
            node,
            "end_lineno",
            node.lineno,
        )

        function_text = "\n".join(
            lines[start - 1:end]
        )

        matched_patterns = [
            name
            for name, pattern in SEARCH_PATTERNS.items()
            if pattern.search(function_text)
        ]

        relevant = bool(
            matched_patterns
            or any(
                token in node.name.lower()
                for token in [
                    "discover",
                    "candidate",
                    "fetch",
                    "csv",
                    "meeting",
                    "race",
                    "main",
                ]
            )
        )

        if not relevant:
            continue

        functions.append(
            {
                "name": node.name,
                "start_line": start,
                "end_line": end,
                "line_count": end - start + 1,
                "matched_patterns": matched_patterns,
                "source": source_segment(
                    lines,
                    start,
                    end,
                    padding=1,
                ),
            }
        )

    print("[3/4] Locating exact defect patterns...")

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        for name, pattern in SEARCH_PATTERNS.items():
            if not pattern.search(line):
                continue

            pattern_hits.append(
                {
                    "pattern": name,
                    "line": line_number,
                    "source": line,
                    "context": source_segment(
                        lines,
                        line_number,
                        line_number,
                        padding=2,
                    ),
                }
            )

    print("[4/4] Writing governed remediation evidence...")

    summary = {
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "governance": {
            "read_only": True,
            "builder_executed": False,
            "builder_modified": False,
            "network_access_performed": False,
            "governed_outputs_modified": False,
        },
        "builder": str(BUILDER),
        "builder_line_count": len(lines),
        "assignments": assignments,
        "relevant_functions": [
            {
                key: value
                for key, value in item.items()
                if key != "source"
            }
            for item in functions
        ],
        "pattern_hits": [
            {
                key: value
                for key, value in item.items()
                if key != "context"
            }
            for item in pattern_hits
        ],
        "decision": (
            "BUILDER_REMEDIATION_SOURCE_MAP_CREATED"
        ),
    }

    JSON_OUT.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    excerpt_sections = []

    for item in assignments:
        excerpt_sections.append(
            "\n".join(
                [
                    "=" * 80,
                    f"ASSIGNMENT: {item['name']}",
                    (
                        f"LINES: {item['start_line']}"
                        f"-{item['end_line']}"
                    ),
                    "=" * 80,
                    item["source"],
                    "",
                ]
            )
        )

    for item in functions:
        excerpt_sections.append(
            "\n".join(
                [
                    "=" * 80,
                    f"FUNCTION: {item['name']}",
                    (
                        f"LINES: {item['start_line']}"
                        f"-{item['end_line']}"
                    ),
                    (
                        "PATTERNS: "
                        + ", ".join(
                            item["matched_patterns"]
                        )
                    ),
                    "=" * 80,
                    item["source"],
                    "",
                ]
            )
        )

    EXCERPTS_OUT.write_text(
        "\n".join(excerpt_sections),
        encoding="utf-8",
    )

    assignment_lines = []

    for item in assignments:
        assignment_lines.append(
            f"- `{item['name']}`: lines "
            f"**{item['start_line']}?{item['end_line']}**"
        )

    if not assignment_lines:
        assignment_lines = [
            "- No target assignments found."
        ]

    function_lines = []

    for item in functions:
        patterns = ", ".join(
            item["matched_patterns"]
        ) or "name-selected"

        function_lines.append(
            f"- `{item['name']}`: lines "
            f"**{item['start_line']}?{item['end_line']}**; "
            f"patterns: `{patterns}`"
        )

    if not function_lines:
        function_lines = [
            "- No relevant functions found."
        ]

    pattern_counts = {}

    for item in pattern_hits:
        pattern_counts[item["pattern"]] = (
            pattern_counts.get(
                item["pattern"],
                0,
            )
            + 1
        )

    pattern_lines = [
        f"- `{name}`: **{count}** hits"
        for name, count in sorted(
            pattern_counts.items()
        )
    ]

    if not pattern_lines:
        pattern_lines = [
            "- No target patterns found."
        ]

    report = f"""# EDGEIQ Racing.com Builder Remediation Map V1

Generated UTC: `{summary['generated_utc']}`

## Governance boundary

- Read-only source inspection.
- Production builder not executed.
- Production builder not modified.
- No network access.
- No cache or governed output modified.

## Builder

- Path: `{BUILDER}`
- Source lines: **{len(lines)}**

## Governed assignments

{chr(10).join(assignment_lines)}

## Relevant functions

{chr(10).join(function_lines)}

## Defect-pattern hits

{chr(10).join(pattern_lines)}

## Remediation constraints

The production remediation must:

1. resolve all repository-owned paths from the actual repository root;
2. stop generating a fixed twelve-race cohort;
3. admit only race numbers supported by meeting or race evidence;
4. sort race numbers numerically;
5. deduplicate by canonical race identity before URL fetch;
6. retain provenance for direct versus derived URLs;
7. write source caches inside the governed repository;
8. avoid using a global first-N URL cap as the population boundary;
9. preserve the existing CSV parser until contrary evidence exists;
10. produce explicit admission and rejection diagnostics.

## Decision

**BUILDER_REMEDIATION_SOURCE_MAP_CREATED**

## Artifacts

- `{JSON_OUT.relative_to(ROOT).as_posix()}`
- `{REPORT_OUT.relative_to(ROOT).as_posix()}`
- `{EXCERPTS_OUT.relative_to(ROOT).as_posix()}`
"""

    REPORT_OUT.write_text(
        report,
        encoding="utf-8",
    )

    print()
    print("COMPLETE")
    print(f"Report: {REPORT_OUT}")
    print(f"Excerpts: {EXCERPTS_OUT}")
    print(f"JSON: {JSON_OUT}")
    print()
    print("KEY COUNTS")
    print(f"Builder lines: {len(lines)}")
    print(
        "Governed assignments: "
        f"{len(assignments)}"
    )
    print(
        "Relevant functions: "
        f"{len(functions)}"
    )
    print(
        "Pattern hits: "
        f"{len(pattern_hits)}"
    )
    print()
    print("DECISION")
    print(
        "BUILDER_REMEDIATION_SOURCE_MAP_CREATED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
