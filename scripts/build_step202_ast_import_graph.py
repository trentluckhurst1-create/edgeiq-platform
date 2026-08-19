from __future__ import annotations

import ast
import csv
import json
import sys

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ==============================================================================
# STEP202-002
# CANONICAL AST IMPORT GRAPH
# ==============================================================================

ROOT = Path(__file__).resolve().parent.parent

DOCS = ROOT / "docs" / "architecture" / "step202"
DOCS.mkdir(parents=True, exist_ok=True)

MODULE_REGISTRY = DOCS / "STEP202_MODULE_REGISTRY.csv"

if not MODULE_REGISTRY.exists():
    raise FileNotFoundError(
        f"Module registry not found: {MODULE_REGISTRY}"
    )

def now_iso():
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()

def write_csv(path, rows, fieldnames):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

def load_registry():

    registry = {}

    with MODULE_REGISTRY.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            registry[
                row["module_name"]
            ] = row

    return registry

print("=" * 80)
print("STEP202-002 AST IMPORT GRAPH")
print("=" * 80)

module_registry = load_registry()

print()
print("Modules loaded :", len(module_registry))
print()


# ==============================================================================
# LOAD PYTHON SOURCES
# ==============================================================================

scan_rows = []

for module_name in sorted(module_registry):

    record = module_registry[module_name]

    repository_path = (
        record["repository_path"]
        .replace("/", "\\")
    )

    absolute_path = ROOT / Path(repository_path)

    if not absolute_path.exists():

        scan_rows.append({
            "module_name": module_name,
            "repository_path": repository_path,
            "status": "MISSING"
        })

        continue

    scan_rows.append({
        "module_name": module_name,
        "repository_path": repository_path,
        "absolute_path": absolute_path,
        "status": "READY"
    })

ready_modules = [
    r
    for r in scan_rows
    if r["status"] == "READY"
]

missing_modules = [
    r
    for r in scan_rows
    if r["status"] == "MISSING"
]

print(f"Ready modules   : {len(ready_modules):,}")
print(f"Missing modules : {len(missing_modules):,}")
print()

import_rows = []
parse_errors = []


# ==============================================================================
# AST IMPORT SCAN
# ==============================================================================

for module in ready_modules:

    module_name = module["module_name"]
    path = module["absolute_path"]

    try:

        source = path.read_text(
            encoding="utf-8-sig",
            errors="replace"
        )

        tree = ast.parse(
            source,
            filename=str(path)
        )

    except Exception as ex:

        parse_errors.append({
            "module_name": module_name,
            "repository_path": module["repository_path"],
            "error": str(ex)
        })

        continue

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                target = alias.name.split(".")[0]

                resolved = (
                    target
                    if target in module_registry
                    else ""
                )

                import_rows.append({
                    "source_module": module_name,
                    "import_type": "IMPORT",
                    "imported_module": target,
                    "resolved_module": resolved,
                    "alias": alias.asname or "",
                    "level": 0,
                    "line": getattr(node, "lineno", ""),
                    "resolved": bool(resolved)
                })

        elif isinstance(node, ast.ImportFrom):

            base = node.module or ""

            root = base.split(".")[0] if base else ""

            resolved = (
                root
                if root in module_registry
                else ""
            )

            for alias in node.names:

                import_rows.append({
                    "source_module": module_name,
                    "import_type": "FROM_IMPORT",
                    "imported_module": root,
                    "resolved_module": resolved,
                    "alias": alias.name,
                    "level": node.level,
                    "line": getattr(node, "lineno", ""),
                    "resolved": bool(resolved)
                })

print(f"Imports discovered : {len(import_rows):,}")
print(f"Parse errors       : {len(parse_errors):,}")
print()


# ==============================================================================
# WRITE OUTPUTS
# ==============================================================================

IMPORT_GRAPH_CSV = DOCS / "STEP202_IMPORT_GRAPH.csv"
PARSE_ERRORS_CSV = DOCS / "STEP202_IMPORT_PARSE_ERRORS.csv"
AUDIT_MD = DOCS / "STEP202_IMPORT_GRAPH_AUDIT.md"

write_csv(
    IMPORT_GRAPH_CSV,
    import_rows,
    [
        "source_module",
        "import_type",
        "imported_module",
        "resolved_module",
        "alias",
        "level",
        "line",
        "resolved"
    ]
)

write_csv(
    PARSE_ERRORS_CSV,
    parse_errors,
    [
        "module_name",
        "repository_path",
        "error"
    ]
)

resolved_count = sum(
    1 for r in import_rows
    if r["resolved"]
)

unresolved_count = len(import_rows) - resolved_count

with AUDIT_MD.open(
    "w",
    encoding="utf-8-sig"
) as f:

    f.write("# STEP202 AST IMPORT GRAPH AUDIT\n\n")
    f.write(f"Generated: {now_iso()}\n\n")
    f.write(f"Modules scanned: {len(ready_modules):,}\n")
    f.write(f"Imports discovered: {len(import_rows):,}\n")
    f.write(f"Resolved imports: {resolved_count:,}\n")
    f.write(f"Unresolved imports: {unresolved_count:,}\n")
    f.write(f"Parse errors: {len(parse_errors):,}\n")

print("=" * 80)
print("OUTPUTS")
print("=" * 80)
print(IMPORT_GRAPH_CSV)
print(PARSE_ERRORS_CSV)
print(AUDIT_MD)
print()

# ==============================================================================
# VALIDATION
# ==============================================================================

errors = []

if len(import_rows) == 0:
    errors.append("No imports discovered.")

if len(ready_modules) == 0:
    errors.append("No modules scanned.")

if errors:

    print("=" * 80)
    print("STEP202-002 FAILED")
    print("=" * 80)

    for error in errors:
        print("ERROR:", error)

    sys.exit(1)

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Modules scanned     : {len(ready_modules):,}")
print(f"Imports discovered  : {len(import_rows):,}")
print(f"Resolved imports    : {resolved_count:,}")
print(f"Unresolved imports  : {unresolved_count:,}")
print(f"Parse errors        : {len(parse_errors):,}")
print()
print("STATUS : PASS")

sys.exit(0)


