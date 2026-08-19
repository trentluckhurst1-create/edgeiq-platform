from __future__ import annotations

import ast
import csv
import json
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = "EDGEIQ_EPI_HELPER_FUNCTION_EXTRACTION_V1"

PRIMARY_BUILDER = Path(
    "scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py"
)

TARGET_FUNCTIONS = (
    "current_epi_value",
    "historical_epi_for_run",
    "metric",
    "metric_float",
)

EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
}

MAX_DEPENDENCY_DEPTH = 2


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def eligible_python_files(root: Path) -> list[Path]:
    files: list[Path] = []

    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue

        if not path.is_file():
            continue

        files.append(path)

    return sorted(files)


def safe_read(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
    except OSError:
        return ""


def parse_tree(path: Path, text: str) -> ast.AST | None:
    try:
        return ast.parse(
            text,
            filename=path.as_posix(),
        )
    except SyntaxError:
        return None


def source_segment(
    lines: list[str],
    node: ast.AST,
    numbered: bool = False,
) -> str:
    start = getattr(node, "lineno", 1)
    end = getattr(node, "end_lineno", start)

    selected = lines[start - 1:end]

    if numbered:
        return "\n".join(
            f"{line_number}: {line}"
            for line_number, line in enumerate(
                selected,
                start=start,
            )
        )

    return "\n".join(selected)


def call_name(node: ast.Call) -> str:
    func = node.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ""


def expression_text(
    lines: list[str],
    node: ast.AST,
) -> str:
    try:
        value = ast.get_source_segment(
            "\n".join(lines),
            node,
        )
        return value or ""
    except Exception:
        return ""


def get_lookup_key(node: ast.Call) -> str:
    if not (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and node.args
    ):
        return ""

    first = node.args[0]

    if isinstance(first, ast.Constant):
        return str(first.value)

    return ""


def subscript_key(
    node: ast.Subscript,
) -> str:
    slice_node = node.slice

    if isinstance(slice_node, ast.Constant):
        return str(slice_node.value)

    try:
        return ast.unparse(slice_node)
    except Exception:
        return ""


def function_details(
    path: Path,
    text: str,
    tree: ast.AST,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, Any]:
    lines = text.splitlines()
    function_source = source_segment(
        lines,
        node,
        numbered=True,
    )

    returns: list[str] = []
    calls: list[str] = []
    get_keys: list[str] = []
    subscripts: list[str] = []
    constants: list[str] = []
    none_return_count = 0

    for child in ast.walk(node):
        if isinstance(child, ast.Return):
            return_text = expression_text(
                lines,
                child,
            )

            returns.append(
                f"{getattr(child, 'lineno', '')}: "
                f"{return_text.strip()}"
            )

            if child.value is None or (
                isinstance(child.value, ast.Constant)
                and child.value.value is None
            ):
                none_return_count += 1

        elif isinstance(child, ast.Call):
            name = call_name(child)

            if name:
                calls.append(name)

            key = get_lookup_key(child)

            if key:
                get_keys.append(key)

        elif isinstance(child, ast.Subscript):
            key = subscript_key(child)

            if key:
                subscripts.append(key)

        elif isinstance(child, ast.Constant):
            if isinstance(child.value, str):
                constants.append(child.value)

    return {
        "function_name": node.name,
        "script_path": path.as_posix(),
        "start_line": node.lineno,
        "end_line": getattr(node, "end_lineno", node.lineno),
        "arguments": " | ".join(
            argument.arg
            for argument in (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
            )
        ),
        "return_statements": "\n".join(returns),
        "none_return_count": none_return_count,
        "called_functions": " | ".join(
            sorted(set(calls))
        ),
        "get_lookup_keys": " | ".join(
            sorted(set(get_keys))
        ),
        "subscript_keys": " | ".join(
            sorted(set(subscripts))
        ),
        "string_constants": " | ".join(
            sorted(set(constants))
        ),
        "source": function_source,
    }


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    root = Path.cwd().resolve()
    primary_builder = root / PRIMARY_BUILDER

    output_root = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-d4-epi-helper-functions"
    )
    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not primary_builder.exists():
        print(
            f"ERROR: Missing builder: {primary_builder}",
            file=sys.stderr,
        )
        return 2

    python_files = eligible_python_files(root)

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(
        f"eligible_python_files={len(python_files)}",
        flush=True,
    )

    definitions: dict[
        str,
        list[
            tuple[
                Path,
                str,
                ast.AST,
                ast.FunctionDef | ast.AsyncFunctionDef,
            ]
        ],
    ] = defaultdict(list)

    parsed_files: dict[
        Path,
        tuple[str, ast.AST],
    ] = {}

    print(
        "\n[1/5] Indexing function definitions...",
        flush=True,
    )

    for index, path in enumerate(
        python_files,
        start=1,
    ):
        text = safe_read(path)

        if not text:
            continue

        tree = parse_tree(path, text)

        if tree is None:
            continue

        relative = path.relative_to(root)
        parsed_files[relative] = (text, tree)

        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                definitions[node.name].append(
                    (
                        relative,
                        text,
                        tree,
                        node,
                    )
                )

        if (
            index % 500 == 0
            or index == len(python_files)
        ):
            print(
                f"[index] {index}/{len(python_files)}",
                flush=True,
            )

    print(
        "\n[2/5] Resolving target helper definitions...",
        flush=True,
    )

    target_rows: list[dict[str, Any]] = []
    selected_definitions: dict[
        str,
        tuple[
            Path,
            str,
            ast.AST,
            ast.FunctionDef | ast.AsyncFunctionDef,
        ],
    ] = {}

    for function_name in TARGET_FUNCTIONS:
        candidates = definitions.get(
            function_name,
            [],
        )

        if not candidates:
            print(
                f"[missing] {function_name}",
                flush=True,
            )
            continue

        selected = sorted(
            candidates,
            key=lambda item: (
                0 if item[0] == PRIMARY_BUILDER else 1,
                len(item[0].parts),
                item[0].as_posix(),
            ),
        )[0]

        selected_definitions[function_name] = selected

        path, text, tree, node = selected
        details = function_details(
            path,
            text,
            tree,
            node,
        )
        details["definition_candidate_count"] = len(
            candidates
        )
        target_rows.append(details)

        print(
            f"[target] {function_name} "
            f"{path.as_posix()}:"
            f"{node.lineno}-"
            f"{getattr(node, 'end_lineno', node.lineno)} "
            f"candidates={len(candidates)}",
            flush=True,
        )

    print(
        "\n[3/5] Discovering callers...",
        flush=True,
    )

    caller_rows: list[dict[str, Any]] = []

    for relative_path, (
        text,
        tree,
    ) in parsed_files.items():
        lines = text.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            called = call_name(node)

            if called not in TARGET_FUNCTIONS:
                continue

            enclosing_function = "<module>"

            for possible_parent in ast.walk(tree):
                if not isinstance(
                    possible_parent,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):
                    continue

                start = possible_parent.lineno
                end = getattr(
                    possible_parent,
                    "end_lineno",
                    start,
                )

                if start <= node.lineno <= end:
                    enclosing_function = (
                        possible_parent.name
                    )

            line_text = (
                lines[node.lineno - 1].strip()
                if 0 < node.lineno <= len(lines)
                else ""
            )

            caller_rows.append(
                {
                    "called_function": called,
                    "script_path": relative_path.as_posix(),
                    "line_number": node.lineno,
                    "enclosing_function": enclosing_function,
                    "source_line": line_text,
                }
            )

    print(
        f"caller_rows={len(caller_rows)}",
        flush=True,
    )

    print(
        "\n[4/5] Extracting immediate dependencies...",
        flush=True,
    )

    dependency_rows: list[dict[str, Any]] = []
    seen_dependencies: set[
        tuple[str, str]
    ] = set()

    queue: deque[
        tuple[str, int]
    ] = deque(
        (function_name, 0)
        for function_name in selected_definitions
    )

    visited: set[tuple[str, int]] = set()

    while queue:
        parent_name, depth = queue.popleft()

        if (
            parent_name,
            depth,
        ) in visited:
            continue

        visited.add((parent_name, depth))

        selected = selected_definitions.get(
            parent_name
        )

        if selected is None:
            continue

        parent_path, parent_text, _, parent_node = (
            selected
        )

        called_names = {
            call_name(node)
            for node in ast.walk(parent_node)
            if isinstance(node, ast.Call)
        }
        called_names.discard("")

        for called_name in sorted(called_names):
            simple_name = called_name.split(".")[-1]

            if simple_name in {
                "get",
                "append",
                "extend",
                "open",
                "read_text",
                "write_text",
                "strip",
                "lower",
                "upper",
                "replace",
                "sort",
                "sorted",
                "len",
                "str",
                "float",
                "int",
                "round",
                "min",
                "max",
                "sum",
                "enumerate",
                "isinstance",
            }:
                continue

            candidates = definitions.get(
                simple_name,
                [],
            )

            dependency_key = (
                parent_name,
                simple_name,
            )

            if dependency_key in seen_dependencies:
                continue

            seen_dependencies.add(
                dependency_key
            )

            if not candidates:
                dependency_rows.append(
                    {
                        "parent_function": parent_name,
                        "dependency_function": simple_name,
                        "depth": depth + 1,
                        "definition_status": "NOT_FOUND_LOCAL",
                        "script_path": "",
                        "start_line": "",
                        "end_line": "",
                        "return_statements": "",
                        "get_lookup_keys": "",
                        "subscript_keys": "",
                        "source": "",
                    }
                )
                continue

            selected_dependency = sorted(
                candidates,
                key=lambda item: (
                    0
                    if item[0] == parent_path
                    else 1,
                    0
                    if item[0] == PRIMARY_BUILDER
                    else 1,
                    item[0].as_posix(),
                ),
            )[0]

            dep_path, dep_text, dep_tree, dep_node = (
                selected_dependency
            )

            dep_details = function_details(
                dep_path,
                dep_text,
                dep_tree,
                dep_node,
            )

            dependency_rows.append(
                {
                    "parent_function": parent_name,
                    "dependency_function": simple_name,
                    "depth": depth + 1,
                    "definition_status": "FOUND",
                    "script_path": dep_path.as_posix(),
                    "start_line": dep_node.lineno,
                    "end_line": getattr(
                        dep_node,
                        "end_lineno",
                        dep_node.lineno,
                    ),
                    "return_statements": dep_details[
                        "return_statements"
                    ],
                    "get_lookup_keys": dep_details[
                        "get_lookup_keys"
                    ],
                    "subscript_keys": dep_details[
                        "subscript_keys"
                    ],
                    "source": dep_details["source"],
                }
            )

            if (
                depth + 1 < MAX_DEPENDENCY_DEPTH
                and simple_name
                not in selected_definitions
            ):
                selected_definitions[
                    simple_name
                ] = selected_dependency

                queue.append(
                    (
                        simple_name,
                        depth + 1,
                    )
                )

    print(
        f"dependency_rows={len(dependency_rows)}",
        flush=True,
    )

    print(
        "\n[5/5] Writing governed outputs...",
        flush=True,
    )

    target_fields = [
        "function_name",
        "script_path",
        "start_line",
        "end_line",
        "definition_candidate_count",
        "arguments",
        "none_return_count",
        "return_statements",
        "called_functions",
        "get_lookup_keys",
        "subscript_keys",
        "string_constants",
        "source",
    ]

    write_csv(
        output_root
        / f"{AUDIT_ID}_TARGET_FUNCTIONS.csv",
        target_rows,
        target_fields,
    )

    write_csv(
        output_root
        / f"{AUDIT_ID}_CALLERS.csv",
        caller_rows,
        [
            "called_function",
            "script_path",
            "line_number",
            "enclosing_function",
            "source_line",
        ],
    )

    write_csv(
        output_root
        / f"{AUDIT_ID}_DEPENDENCIES.csv",
        dependency_rows,
        [
            "parent_function",
            "dependency_function",
            "depth",
            "definition_status",
            "script_path",
            "start_line",
            "end_line",
            "return_statements",
            "get_lookup_keys",
            "subscript_keys",
            "source",
        ],
    )

    combined_source: list[str] = []

    for row in target_rows:
        combined_source.extend(
            [
                "=" * 100,
                (
                    f"FUNCTION: {row['function_name']} "
                    f"FILE: {row['script_path']} "
                    f"LINES: {row['start_line']}-"
                    f"{row['end_line']}"
                ),
                "=" * 100,
                row["source"],
                "",
                "RETURN STATEMENTS:",
                row["return_statements"],
                "",
                "GET LOOKUP KEYS:",
                row["get_lookup_keys"],
                "",
                "SUBSCRIPT KEYS:",
                row["subscript_keys"],
                "",
            ]
        )

    (
        output_root
        / f"{AUDIT_ID}_TARGET_FUNCTION_SOURCE.txt"
    ).write_text(
        "\n".join(combined_source),
        encoding="utf-8",
    )

    status = (
        "EVIDENCE_CAPTURED"
        if len(target_rows) == len(TARGET_FUNCTIONS)
        else "REVIEW_REQUIRED"
    )

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": now_utc(),
        "primary_builder": PRIMARY_BUILDER.as_posix(),
        "eligible_python_files": len(python_files),
        "target_functions_requested": len(
            TARGET_FUNCTIONS
        ),
        "target_functions_found": len(target_rows),
        "target_functions_missing": [
            name
            for name in TARGET_FUNCTIONS
            if name not in {
                row["function_name"]
                for row in target_rows
            }
        ],
        "caller_rows": len(caller_rows),
        "dependency_rows": len(dependency_rows),
        "status": status,
    }

    (
        output_root
        / f"{AUDIT_ID}_SUMMARY.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("\n=== PHASE D4 COMPLETE ===")
    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())