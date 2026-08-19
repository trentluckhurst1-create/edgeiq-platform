from __future__ import annotations

import ast
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


AUDIT_ID = "EDGEIQ_ACTIVE_CANONICAL_RUNTIME_ARCHITECTURE_V3"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPOSITORY_ROOT / "docs" / "architecture-audit-v3"

IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
}

SOURCE_SUFFIXES = {
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
}

DATA_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".parquet",
    ".feather",
    ".sqlite",
    ".db",
    ".txt",
}

FRONTEND_SUFFIXES = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
}

HISTORICAL_MARKERS = {
    "CHECKPOINT",
    "BACKUP",
    "BEFORE",
    "PRE_",
    "_PRE",
    "OLD",
    "LEGACY",
    "CANDIDATE",
    "WORKING",
    "RECOVERY",
    "COPY",
    "TMP",
    "TEMP",
    "EXPERIMENT",
    "PROBE",
    "DEBUG",
    "RESEARCH",
    "REPLAY",
    "ARCHIVE",
    "SNAPSHOT",
    "LOCKED",
}

OUTPUT_HINTS = {
    "output",
    "output_root",
    "write",
    "writer",
    "set-content",
    "out-file",
    "export-csv",
    "to_csv",
    "to_json",
    "write_text",
    "write_bytes",
    "dump",
    "save",
    "mkdir",
}

INPUT_HINTS = {
    "input",
    "source",
    "read",
    "reader",
    "get-content",
    "import-csv",
    "read_csv",
    "read_json",
    "read_text",
    "open",
    "load",
    "fetch",
}

STRING_DATA_REFERENCE_PATTERN = re.compile(
    r"""(?P<value>
        [A-Za-z0-9_./\\:@$(){}\[\]\- ]+
        \.(?:csv|json|jsonl|parquet|feather|sqlite|db|txt)
    )""",
    re.IGNORECASE | re.VERBOSE,
)

FRONTEND_IMPORT_PATTERN = re.compile(
    r"""
    (?:
        import\s+(?:[\s\S]*?\s+from\s+)?|
        export\s+(?:[\s\S]*?\s+from\s+)?|
        require\s*\(
    )
    ["']
    (?P<module>[^"']+)
    ["']
    """,
    re.VERBOSE,
)

DYNAMIC_IMPORT_PATTERN = re.compile(
    r"""import\s*\(\s*["'](?P<module>[^"']+)["']\s*\)""",
    re.VERBOSE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative_path(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def safe_read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except Exception:
            return None
    except Exception:
        return None


def should_ignore(path: Path) -> bool:
    try:
        rel = path.relative_to(REPOSITORY_ROOT)
    except ValueError:
        return True

    return any(part in IGNORED_DIRECTORIES for part in rel.parts)


def iter_repository_files() -> Iterable[Path]:
    for root, directories, files in os.walk(REPOSITORY_ROOT):
        root_path = Path(root)

        directories[:] = [
            name
            for name in directories
            if name not in IGNORED_DIRECTORIES
            and not should_ignore(root_path / name)
        ]

        for name in files:
            path = root_path / name
            if not should_ignore(path):
                yield path


def historical_markers(path_text: str) -> list[str]:
    upper = path_text.upper()
    return sorted(marker for marker in HISTORICAL_MARKERS if marker in upper)


def classify_embedded_state(path_text: str) -> str:
    markers = historical_markers(path_text)

    if not markers:
        return "CANONICAL_NAME_CANDIDATE"

    upper = path_text.upper()

    if "CHECKPOINT" in upper:
        return "EMBEDDED_CHECKPOINT"

    if "BACKUP" in upper or "BEFORE" in upper:
        return "EMBEDDED_BACKUP"

    if "CANDIDATE" in upper:
        return "CANDIDATE"

    if "WORKING" in upper:
        return "WORKING_COPY"

    if "LEGACY" in upper or "OLD" in upper:
        return "LEGACY"

    if "TMP" in upper or "TEMP" in upper:
        return "TEMPORARY"

    if "PROBE" in upper or "DEBUG" in upper:
        return "INVESTIGATION"

    if "RESEARCH" in upper or "REPLAY" in upper:
        return "RESEARCH"

    if "RECOVERY" in upper:
        return "RECOVERY"

    return "HISTORICAL_OR_NONCANONICAL"


def classify_repository_domain(path_text: str) -> str:
    value = path_text.replace("\\", "/").lower()

    if value.startswith("src/"):
        return "frontend"

    if value.startswith("scripts/"):
        return "automation"

    if value.startswith("public/data/"):
        return "public_data"

    if value.startswith("public/"):
        return "public_asset"

    if value.startswith("data/"):
        return "source_data"

    if value.startswith("contracts/"):
        return "contract"

    if value.startswith("docs/"):
        return "documentation"

    if value.startswith("outputs/"):
        return "generated_output"

    if value.startswith("checkpoints/"):
        return "checkpoint"

    if value.startswith("_archive") or value.startswith("archive/"):
        return "archive"

    if "/" not in value:
        return "repository_root"

    return "other"


def resolve_frontend_module(source: Path, module: str) -> Path | None:
    if not module.startswith("."):
        return None

    base = (source.parent / module).resolve()

    candidates = [
        base,
        *[Path(str(base) + suffix) for suffix in FRONTEND_SUFFIXES],
        *[
            base / f"index{suffix}"
            for suffix in FRONTEND_SUFFIXES
        ],
    ]

    for candidate in candidates:
        try:
            if (
                candidate.exists()
                and candidate.is_file()
                and candidate.is_relative_to(REPOSITORY_ROOT)
            ):
                return candidate
        except OSError:
            continue

    return None


def frontend_dependencies(path: Path) -> list[Path]:
    text = safe_read_text(path)

    if text is None:
        return []

    modules = [
        match.group("module")
        for match in FRONTEND_IMPORT_PATTERN.finditer(text)
    ]

    modules.extend(
        match.group("module")
        for match in DYNAMIC_IMPORT_PATTERN.finditer(text)
    )

    dependencies: list[Path] = []
    seen: set[str] = set()

    for module in modules:
        resolved = resolve_frontend_module(path, module)

        if resolved is None:
            continue

        key = str(resolved)

        if key in seen:
            continue

        seen.add(key)
        dependencies.append(resolved)

    return dependencies


def python_module_index(
    files: list[Path],
) -> dict[str, list[Path]]:
    index: defaultdict[str, list[Path]] = defaultdict(list)

    for path in files:
        if path.suffix.lower() != ".py":
            continue

        index[path.stem].append(path)

        try:
            rel = path.relative_to(REPOSITORY_ROOT)
        except ValueError:
            continue

        dotted = ".".join(rel.with_suffix("").parts)
        index[dotted].append(path)

    return dict(index)


def python_dependencies(
    path: Path,
    module_index: dict[str, list[Path]],
) -> list[Path]:
    text = safe_read_text(path)

    if text is None:
        return []

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    dependencies: list[Path] = []
    seen: set[str] = set()

    for node in ast.walk(tree):
        names: list[str] = []

        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)

        for name in names:
            candidates = []

            candidates.extend(module_index.get(name, []))
            candidates.extend(
                module_index.get(name.split(".")[-1], [])
            )

            for candidate in candidates:
                key = str(candidate)

                if key in seen:
                    continue

                seen.add(key)
                dependencies.append(candidate)

    return dependencies


def powershell_script_dependencies(path: Path) -> list[Path]:
    text = safe_read_text(path)

    if text is None:
        return []

    patterns = [
        re.compile(
            r"""(?i)(?:python|py)\s+(?:-u\s+)?["']?(?P<path>[^"' \r\n]+\.py)"""
        ),
        re.compile(
            r"""(?i)&\s*["']?(?P<path>[^"'\r\n]+\.ps1)"""
        ),
        re.compile(
            r"""(?i)\.\s+["']?(?P<path>[^"'\r\n]+\.ps1)"""
        ),
    ]

    dependencies: list[Path] = []
    seen: set[str] = set()

    for pattern in patterns:
        for match in pattern.finditer(text):
            raw = match.group("path")
            raw = raw.replace("$PSScriptRoot", str(path.parent))
            raw = raw.replace("$PWD", str(REPOSITORY_ROOT))
            raw = raw.strip("'\"")

            candidate = Path(raw)

            if not candidate.is_absolute():
                candidate = path.parent / candidate

            try:
                candidate = candidate.resolve()
            except OSError:
                continue

            try:
                valid = (
                    candidate.exists()
                    and candidate.is_file()
                    and candidate.is_relative_to(REPOSITORY_ROOT)
                )
            except OSError:
                valid = False

            if not valid:
                continue

            key = str(candidate)

            if key in seen:
                continue

            seen.add(key)
            dependencies.append(candidate)

    return dependencies


def discover_entrypoints(all_files: list[Path]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    explicit_candidates = [
        REPOSITORY_ROOT / "package.json",
        REPOSITORY_ROOT / "vite.config.ts",
        REPOSITORY_ROOT / "vite.config.js",
        REPOSITORY_ROOT / "src" / "main.tsx",
        REPOSITORY_ROOT / "src" / "main.ts",
        REPOSITORY_ROOT / "src" / "main.jsx",
        REPOSITORY_ROOT / "src" / "main.js",
        REPOSITORY_ROOT / "src" / "App.tsx",
        REPOSITORY_ROOT / "src" / "App.ts",
    ]

    for path in explicit_candidates:
        if not path.exists() or not path.is_file():
            continue

        key = str(path.resolve())

        if key in seen:
            continue

        seen.add(key)
        entries.append(
            {
                "entrypoint": relative_path(path),
                "entrypoint_type": "explicit_application_entry",
                "reason": "Known application or build entry candidate",
            }
        )

    for path in all_files:
        rel = relative_path(path)
        lower_name = path.name.lower()
        lower_rel = rel.lower()

        is_orchestrator = (
            path.suffix.lower() == ".ps1"
            and (
                lower_name.startswith("run_")
                or "pipeline" in lower_name
                or "orchestrat" in lower_name
                or "scheduled" in lower_name
                or "refresh" in lower_name
                or "startup" in lower_name
            )
        )

        is_root_python_entry = (
            path.parent == REPOSITORY_ROOT
            and path.suffix.lower() == ".py"
            and (
                lower_name.startswith("run_")
                or lower_name.startswith("build_")
                or lower_name.startswith("audit_")
            )
        )

        is_package_manifest = lower_rel in {
            "package.json",
            "vite.config.ts",
            "vite.config.js",
        }

        if not (
            is_orchestrator
            or is_root_python_entry
            or is_package_manifest
        ):
            continue

        state = classify_embedded_state(rel)

        if state != "CANONICAL_NAME_CANDIDATE":
            continue

        key = str(path.resolve())

        if key in seen:
            continue

        seen.add(key)

        entries.append(
            {
                "entrypoint": rel,
                "entrypoint_type": (
                    "powershell_orchestrator"
                    if is_orchestrator
                    else "root_governed_entry"
                ),
                "reason": "Canonical-name runtime entry candidate",
            }
        )

    entries.sort(key=lambda row: row["entrypoint"])

    return entries


def trace_reachable_sources(
    entrypoints: list[dict[str, Any]],
    all_files: list[Path],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    module_index = python_module_index(all_files)

    queue: deque[tuple[Path, str, int]] = deque()
    visited: dict[str, dict[str, Any]] = {}
    edge_rows: list[dict[str, Any]] = []

    for entry in entrypoints:
        path = REPOSITORY_ROOT / entry["entrypoint"]

        if not path.exists() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue

        queue.append((path.resolve(), entry["entrypoint"], 0))

    while queue:
        path, root_entry, depth = queue.popleft()
        key = str(path)

        if key in visited:
            if depth < int(visited[key]["minimum_depth"]):
                visited[key]["minimum_depth"] = depth
            visited[key]["entrypoints"].add(root_entry)
            continue

        rel = relative_path(path)

        visited[key] = {
            "relative_path": rel,
            "suffix": path.suffix.lower(),
            "domain": classify_repository_domain(rel),
            "embedded_state": classify_embedded_state(rel),
            "markers": historical_markers(rel),
            "minimum_depth": depth,
            "entrypoints": {root_entry},
        }

        suffix = path.suffix.lower()

        if suffix in FRONTEND_SUFFIXES:
            dependencies = frontend_dependencies(path)

        elif suffix == ".py":
            dependencies = python_dependencies(path, module_index)

        elif suffix == ".ps1":
            dependencies = powershell_script_dependencies(path)

        else:
            dependencies = []

        for dependency in dependencies:
            dep_rel = relative_path(dependency)

            edge_rows.append(
                {
                    "source_file": rel,
                    "target_file": dep_rel,
                    "edge_type": "source_dependency",
                    "root_entrypoint": root_entry,
                    "depth": depth + 1,
                    "target_embedded_state": classify_embedded_state(dep_rel),
                }
            )

            queue.append((dependency, root_entry, depth + 1))

    reachable_rows: list[dict[str, Any]] = []

    for row in visited.values():
        reachable_rows.append(
            {
                "relative_path": row["relative_path"],
                "suffix": row["suffix"],
                "domain": row["domain"],
                "embedded_state": row["embedded_state"],
                "markers": json.dumps(
                    row["markers"],
                    ensure_ascii=False,
                ),
                "minimum_depth": row["minimum_depth"],
                "entrypoint_count": len(row["entrypoints"]),
                "entrypoints": json.dumps(
                    sorted(row["entrypoints"]),
                    ensure_ascii=False,
                ),
            }
        )

    reachable_rows.sort(
        key=lambda row: (
            int(row["minimum_depth"]),
            row["relative_path"],
        )
    )

    edge_rows.sort(
        key=lambda row: (
            row["root_entrypoint"],
            int(row["depth"]),
            row["source_file"],
            row["target_file"],
        )
    )

    return reachable_rows, edge_rows


def reference_role(text: str, start: int, end: int) -> str:
    context_start = max(0, start - 180)
    context_end = min(len(text), end + 180)
    context = text[context_start:context_end].lower()

    output_score = sum(hint in context for hint in OUTPUT_HINTS)
    input_score = sum(hint in context for hint in INPUT_HINTS)

    if output_score > input_score and output_score > 0:
        return "GENERATED_OUTPUT_REFERENCE"

    if input_score > output_score and input_score > 0:
        return "REQUIRED_INPUT_REFERENCE"

    if output_score > 0 and input_score > 0:
        return "AMBIGUOUS_INPUT_OUTPUT_REFERENCE"

    return "UNCLASSIFIED_DATA_REFERENCE"


def clean_reference(value: str) -> str:
    cleaned = value.strip().strip("'\"`")
    cleaned = cleaned.rstrip(".,;:)]}")
    return cleaned.replace("\\\\", "\\")


def resolve_data_reference(
    source_path: Path,
    reference: str,
) -> tuple[bool, str]:
    normalised = reference.replace("\\", "/")
    ref_path = Path(normalised)

    candidates: list[Path] = []

    if ref_path.is_absolute():
        candidates.append(ref_path)
    else:
        candidates.extend(
            [
                source_path.parent / ref_path,
                REPOSITORY_ROOT / ref_path,
                REPOSITORY_ROOT / "public" / ref_path,
                REPOSITORY_ROOT / "public" / "data" / ref_path.name,
                REPOSITORY_ROOT / "data" / ref_path.name,
            ]
        )

    seen: set[str] = set()

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue

        key = str(resolved)

        if key in seen:
            continue

        seen.add(key)

        try:
            if resolved.exists() and resolved.is_file():
                if resolved.is_relative_to(REPOSITORY_ROOT):
                    return True, relative_path(resolved)

                return True, str(resolved)
        except OSError:
            continue

    return False, ""


def scan_reachable_data_references(
    reachable_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    source_rows = [
        row
        for row in reachable_rows
        if row["suffix"] in SOURCE_SUFFIXES
    ]

    for index, row in enumerate(source_rows, start=1):
        if index == 1 or index % 100 == 0:
            print(
                f"[data references] {index}/{len(source_rows)} "
                f"{row['relative_path']}",
                flush=True,
            )

        path = REPOSITORY_ROOT / row["relative_path"]
        text = safe_read_text(path)

        if text is None:
            continue

        for match in STRING_DATA_REFERENCE_PATTERN.finditer(text):
            reference = clean_reference(match.group("value"))

            if not reference:
                continue

            exists, resolved = resolve_data_reference(path, reference)
            role = reference_role(text, match.start(), match.end())

            results.append(
                {
                    "source_file": row["relative_path"],
                    "source_embedded_state": row["embedded_state"],
                    "referenced_value": reference,
                    "reference_role": role,
                    "exists": exists,
                    "resolved_path": resolved,
                    "resolved_domain": (
                        classify_repository_domain(resolved)
                        if exists
                        and resolved
                        and not Path(resolved).is_absolute()
                        else ""
                    ),
                    "resolved_embedded_state": (
                        classify_embedded_state(resolved)
                        if exists and resolved
                        else ""
                    ),
                }
            )

    return results


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fields: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {field: row.get(field, "") for field in fields}
            )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(f"REPOSITORY_ROOT={REPOSITORY_ROOT}", flush=True)
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}", flush=True)
    print("", flush=True)

    print("[1/6] Inventorying repository files...", flush=True)

    all_files = list(iter_repository_files())

    inventory_rows: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()

    total = len(all_files)

    for index, path in enumerate(all_files, start=1):
        if index == 1 or index % 1000 == 0:
            print(f"[inventory] {index}/{total}", flush=True)

        rel = relative_path(path)
        state = classify_embedded_state(rel)
        domain = classify_repository_domain(rel)

        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        inventory_rows.append(
            {
                "relative_path": rel,
                "domain": domain,
                "suffix": path.suffix.lower() or "(no suffix)",
                "size_bytes": size,
                "embedded_state": state,
                "markers": json.dumps(
                    historical_markers(rel),
                    ensure_ascii=False,
                ),
            }
        )

        state_counts[state] += 1
        domain_counts[domain] += 1

    print(
        f"[inventory] files={len(inventory_rows)}",
        flush=True,
    )

    print("[2/6] Discovering runtime entrypoints...", flush=True)

    entrypoints = discover_entrypoints(all_files)

    print(
        f"[entrypoints] discovered={len(entrypoints)}",
        flush=True,
    )

    for row in entrypoints[:30]:
        print(
            f"[entrypoint] {row['entrypoint_type']} "
            f"{row['entrypoint']}",
            flush=True,
        )

    print("[3/6] Tracing reachable source dependencies...", flush=True)

    reachable_rows, edge_rows = trace_reachable_sources(
        entrypoints,
        all_files,
    )

    print(
        f"[runtime graph] reachable_sources={len(reachable_rows)} "
        f"dependency_edges={len(edge_rows)}",
        flush=True,
    )

    print("[4/6] Scanning reachable runtime data references...", flush=True)

    data_reference_rows = scan_reachable_data_references(
        reachable_rows
    )

    print(
        f"[data references] total={len(data_reference_rows)}",
        flush=True,
    )

    required_input_rows = [
        row
        for row in data_reference_rows
        if row["reference_role"] == "REQUIRED_INPUT_REFERENCE"
    ]

    generated_output_rows = [
        row
        for row in data_reference_rows
        if row["reference_role"] == "GENERATED_OUTPUT_REFERENCE"
    ]

    missing_required_rows = [
        row
        for row in required_input_rows
        if not row["exists"]
    ]

    reachable_historical_rows = [
        row
        for row in reachable_rows
        if row["embedded_state"] != "CANONICAL_NAME_CANDIDATE"
    ]

    canonical_reachable_rows = [
        row
        for row in reachable_rows
        if row["embedded_state"] == "CANONICAL_NAME_CANDIDATE"
    ]

    print("[5/6] Identifying canonicality conflicts...", flush=True)

    logical_groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    marker_pattern = re.compile(
        r"""
        (?:
            _CHECKPOINT[^.]*
            |_BACKUP[^.]*
            |_BEFORE[^.]*
            |_CANDIDATE[^.]*
            |_WORKING[^.]*
            |_LEGACY[^.]*
            |_OLD[^.]*
            |_PRE_[^.]*
            |_TMP[^.]*
            |_TEMP[^.]*
            |_RECOVERY[^.]*
            |_RESEARCH[^.]*
            |_REPLAY[^.]*
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    for row in inventory_rows:
        path = Path(row["relative_path"])

        if path.suffix.lower() not in SOURCE_SUFFIXES | DATA_SUFFIXES:
            continue

        stem = marker_pattern.sub("", path.stem)
        logical_key = (
            f"{path.parent.as_posix().lower()}/"
            f"{stem.lower()}{path.suffix.lower()}"
        )

        logical_groups[logical_key].append(row)

    canonicality_rows: list[dict[str, Any]] = []

    for logical_key, rows in logical_groups.items():
        states = sorted({row["embedded_state"] for row in rows})
        canonical_candidates = [
            row
            for row in rows
            if row["embedded_state"] == "CANONICAL_NAME_CANDIDATE"
        ]

        historical_candidates = [
            row
            for row in rows
            if row["embedded_state"] != "CANONICAL_NAME_CANDIDATE"
        ]

        if len(rows) < 2:
            continue

        canonicality_rows.append(
            {
                "logical_key": logical_key,
                "file_count": len(rows),
                "canonical_candidate_count": len(canonical_candidates),
                "historical_candidate_count": len(historical_candidates),
                "states": json.dumps(states, ensure_ascii=False),
                "paths": json.dumps(
                    sorted(row["relative_path"] for row in rows),
                    ensure_ascii=False,
                ),
                "status": (
                    "SINGLE_CANONICAL_WITH_HISTORY"
                    if len(canonical_candidates) == 1
                    else "CANONICAL_CONFLICT_REVIEW"
                ),
            }
        )

    canonicality_rows.sort(
        key=lambda row: (
            row["status"] == "CANONICAL_CONFLICT_REVIEW",
            int(row["file_count"]),
        ),
        reverse=True,
    )

    print(
        f"[canonicality] grouped_conflicts={len(canonicality_rows)}",
        flush=True,
    )

    print("[6/6] Writing governed outputs...", flush=True)

    write_csv(
        OUTPUT_ROOT / f"{AUDIT_ID}_REPOSITORY_CLASSIFICATION.csv",
        inventory_rows,
        [
            "relative_path",
            "domain",
            "suffix",
            "size_bytes",
            "embedded_state",
            "markers",
        ],
    )

    write_csv(
        OUTPUT_ROOT / f"{AUDIT_ID}_ENTRYPOINTS.csv",
        entrypoints,
        [
            "entrypoint",
            "entrypoint_type",
            "reason",
        ],
    )

    write_csv(
        OUTPUT_ROOT / f"{AUDIT_ID}_REACHABLE_SOURCES.csv",
        reachable_rows,
        [
            "relative_path",
            "suffix",
            "domain",
            "embedded_state",
            "markers",
            "minimum_depth",
            "entrypoint_count",
            "entrypoints",
        ],
    )

    write_csv(
        OUTPUT_ROOT / f"{AUDIT_ID}_SOURCE_DEPENDENCY_EDGES.csv",
        edge_rows,
        [
            "source_file",
            "target_file",
            "edge_type",
            "root_entrypoint",
            "depth",
            "target_embedded_state",
        ],
    )

    write_csv(
        OUTPUT_ROOT / f"{AUDIT_ID}_DATA_REFERENCES.csv",
        data_reference_rows,
        [
            "source_file",
            "source_embedded_state",
            "referenced_value",
            "reference_role",
            "exists",
            "resolved_path",
            "resolved_domain",
            "resolved_embedded_state",
        ],
    )

    write_csv(
        OUTPUT_ROOT / f"{AUDIT_ID}_MISSING_REQUIRED_INPUTS.csv",
        missing_required_rows,
        [
            "source_file",
            "source_embedded_state",
            "referenced_value",
            "reference_role",
            "exists",
            "resolved_path",
            "resolved_domain",
            "resolved_embedded_state",
        ],
    )

    write_csv(
        OUTPUT_ROOT / f"{AUDIT_ID}_GENERATED_OUTPUT_REFERENCES.csv",
        generated_output_rows,
        [
            "source_file",
            "source_embedded_state",
            "referenced_value",
            "reference_role",
            "exists",
            "resolved_path",
            "resolved_domain",
            "resolved_embedded_state",
        ],
    )

    write_csv(
        OUTPUT_ROOT / f"{AUDIT_ID}_REACHABLE_HISTORICAL_ARTEFACTS.csv",
        reachable_historical_rows,
        [
            "relative_path",
            "suffix",
            "domain",
            "embedded_state",
            "markers",
            "minimum_depth",
            "entrypoint_count",
            "entrypoints",
        ],
    )

    write_csv(
        OUTPUT_ROOT / f"{AUDIT_ID}_CANONICALITY_GROUPS.csv",
        canonicality_rows,
        [
            "logical_key",
            "file_count",
            "canonical_candidate_count",
            "historical_candidate_count",
            "states",
            "paths",
            "status",
        ],
    )

    counts = {
        "repository_files": len(inventory_rows),
        "runtime_entrypoints": len(entrypoints),
        "reachable_source_files": len(reachable_rows),
        "canonical_name_reachable_sources": len(
            canonical_reachable_rows
        ),
        "historical_or_noncanonical_reachable_sources": len(
            reachable_historical_rows
        ),
        "source_dependency_edges": len(edge_rows),
        "runtime_data_references": len(data_reference_rows),
        "required_input_references": len(required_input_rows),
        "missing_required_input_references": len(
            missing_required_rows
        ),
        "generated_output_references": len(
            generated_output_rows
        ),
        "canonicality_groups_requiring_review": sum(
            row["status"] == "CANONICAL_CONFLICT_REVIEW"
            for row in canonicality_rows
        ),
        "single_canonical_with_history_groups": sum(
            row["status"] == "SINGLE_CANONICAL_WITH_HISTORY"
            for row in canonicality_rows
        ),
    }

    overall_status = "PASS"

    if (
        counts["missing_required_input_references"] > 0
        or counts[
            "historical_or_noncanonical_reachable_sources"
        ] > 0
        or counts[
            "canonicality_groups_requiring_review"
        ] > 0
    ):
        overall_status = "REVIEW_REQUIRED"

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": utc_now(),
        "repository_root": str(REPOSITORY_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "overall_status": overall_status,
        "counts": counts,
        "embedded_state_counts": dict(
            sorted(state_counts.items())
        ),
        "domain_counts": dict(sorted(domain_counts.items())),
        "principles": [
            "No repository files deleted, moved, renamed or repaired.",
            "Only docs/architecture-audit-v3 outputs are written.",
            "Runtime evidence begins from discovered entrypoints.",
            "Reachability is evidence of use, not proof of execution.",
            "Historical filename markers do not automatically mean deletion.",
            "Missing required-input classification is heuristic and requires review.",
            "Generated outputs are separated from required runtime inputs.",
            "Canonicality conflicts require evidence before remediation.",
        ],
    }

    write_json(
        OUTPUT_ROOT / f"{AUDIT_ID}_SUMMARY.json",
        summary,
    )

    report = {
        **summary,
        "entrypoints": entrypoints,
        "top_missing_required_inputs": missing_required_rows[:100],
        "reachable_historical_artefacts": (
            reachable_historical_rows[:100]
        ),
        "canonicality_review_groups": [
            row
            for row in canonicality_rows
            if row["status"] == "CANONICAL_CONFLICT_REVIEW"
        ][:100],
    }

    write_json(
        OUTPUT_ROOT / f"{AUDIT_ID}_REPORT.json",
        report,
    )

    markdown = [
        f"# {AUDIT_ID}",
        "",
        f"- Generated UTC: `{summary['generated_at_utc']}`",
        f"- Overall status: **{overall_status}**",
        "",
        "## Counts",
        "",
    ]

    for key, value in counts.items():
        markdown.append(f"- {key}: `{value}`")

    markdown.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Reachable source files are linked from identified runtime entrypoints.",
            "- Historical artefacts reachable from an entrypoint require review.",
            "- Generated outputs are not treated as missing runtime inputs.",
            "- Canonical-name candidates are not automatically proven canonical.",
            "- No cleanup was performed.",
            "",
        ]
    )

    (
        OUTPUT_ROOT / f"{AUDIT_ID}_SUMMARY.md"
    ).write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    print("", flush=True)
    print("=== V3 AUDIT COMPLETE ===", flush=True)
    print(
        json.dumps(
            {
                "overall_status": overall_status,
                **counts,
            },
            indent=2,
        ),
        flush=True,
    )
    print("", flush=True)
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}", flush=True)
    print(f"OVERALL_STATUS={overall_status}", flush=True)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("AUDIT_INTERRUPTED", file=sys.stderr, flush=True)
        raise
    except Exception as exc:
        print(
            f"AUDIT_FAILED={type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
