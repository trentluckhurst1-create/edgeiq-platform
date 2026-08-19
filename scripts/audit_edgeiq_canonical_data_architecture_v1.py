from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path.cwd()
OUTPUT_ROOT = REPOSITORY_ROOT / "docs" / "architecture-audit"

EXCLUDED_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".vite",
    ".pytest_cache",
    ".mypy_cache",
}

DATA_SUFFIXES = {".csv", ".json", ".jsonl", ".parquet", ".feather", ".sqlite", ".db"}
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".ps1"}
TEXT_SUFFIXES = CODE_SUFFIXES | {".md", ".txt", ".yaml", ".yml", ".toml"}

CHECKPOINT_PATTERN = re.compile(
    r"(checkpoint|backup|before_|_old\b|copy\b|archive|legacy|deprecated)",
    re.IGNORECASE,
)

BUILDER_PATTERN = re.compile(
    r"(^|_)(build|builder|generate|materialize|compile|enrich|normalise|normalize|orchestrate|pipeline|refresh)(_|$)",
    re.IGNORECASE,
)

AUDIT_PATTERN = re.compile(r"(^|_)(audit|check|validate|verify|checkpoint)(_|$)", re.IGNORECASE)

PUBLIC_DATA_REFERENCE_PATTERN = re.compile(
    r"""["'](?:/data/)?([^"'?#]+\.(?:csv|json|jsonl|parquet|feather|sqlite|db))""",
    re.IGNORECASE,
)

GENERAL_DATA_REFERENCE_PATTERN = re.compile(
    r"""(?P<path>[A-Za-z0-9_./\\-]+\.(?:csv|json|jsonl|parquet|feather|sqlite|db))""",
    re.IGNORECASE,
)


@dataclass
class FileRecord:
    relative_path: str
    suffix: str
    size_bytes: int
    modified_utc: str
    sha256: str | None
    category: str
    is_checkpoint_like: bool
    is_builder_like: bool
    is_audit_like: bool


@dataclass
class DataReference:
    source_file: str
    referenced_value: str
    resolved_path: str | None
    exists: bool
    reference_kind: str


@dataclass
class PythonDependency:
    source_file: str
    imported_module: str
    local_candidate: str | None
    local_exists: bool


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRECTORIES for part in path.parts)


def relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return None


def classify_file(path: Path) -> str:
    suffix = path.suffix.lower()
    name = path.name.lower()
    rel = relative(path).lower()

    if suffix in DATA_SUFFIXES:
        if "/public/data/" in f"/{rel}" or rel.startswith("public/data/"):
            return "public_data"
        if "warehouse" in rel or "fact" in name:
            return "warehouse_or_fact"
        if "feed" in name:
            return "feed"
        if "master" in name or "registry" in name or "canonical" in name:
            return "canonical_or_registry"
        return "data"

    if suffix == ".py":
        if BUILDER_PATTERN.search(path.stem):
            return "python_builder"
        if AUDIT_PATTERN.search(path.stem):
            return "python_audit"
        return "python"

    if suffix in {".ts", ".tsx", ".js", ".jsx"}:
        if "service" in rel or "feed" in name:
            return "frontend_service"
        if "component" in rel or suffix in {".tsx", ".jsx"}:
            return "frontend_component"
        return "frontend_code"

    if suffix == ".ps1":
        return "powershell"

    if suffix == ".md":
        return "documentation"

    return "other"


def iter_repository_files() -> list[Path]:
    files: list[Path] = []
    for path in REPOSITORY_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if is_excluded(path):
            continue
        files.append(path)
    return sorted(files, key=lambda value: relative(value).lower())


def build_file_inventory(files: list[Path]) -> list[FileRecord]:
    records: list[FileRecord] = []

    for path in files:
        suffix = path.suffix.lower()
        stat = path.stat()

        should_hash = (
            suffix in DATA_SUFFIXES
            or suffix in CODE_SUFFIXES
            or stat.st_size <= 5 * 1024 * 1024
        )

        records.append(
            FileRecord(
                relative_path=relative(path),
                suffix=suffix,
                size_bytes=stat.st_size,
                modified_utc=datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                ).isoformat(),
                sha256=sha256_file(path) if should_hash else None,
                category=classify_file(path),
                is_checkpoint_like=bool(CHECKPOINT_PATTERN.search(path.name)),
                is_builder_like=bool(BUILDER_PATTERN.search(path.stem)),
                is_audit_like=bool(AUDIT_PATTERN.search(path.stem)),
            )
        )

    return records


def resolve_data_reference(source: Path, raw_reference: str) -> Path | None:
    cleaned = raw_reference.replace("\\", "/").strip()
    cleaned = cleaned.split("?", 1)[0].split("#", 1)[0]

    candidates: list[Path] = []

    if cleaned.startswith("/data/"):
        candidates.append(REPOSITORY_ROOT / "public" / cleaned.lstrip("/"))
    elif cleaned.startswith("data/"):
        candidates.append(REPOSITORY_ROOT / "public" / cleaned)
        candidates.append(REPOSITORY_ROOT / cleaned)
    else:
        candidates.append(source.parent / cleaned)
        candidates.append(REPOSITORY_ROOT / cleaned)
        candidates.append(REPOSITORY_ROOT / "public" / "data" / Path(cleaned).name)

    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(REPOSITORY_ROOT.resolve())
        except ValueError:
            continue
        if resolved.exists():
            return resolved

    return None


def scan_data_references(files: list[Path]) -> list[DataReference]:
    references: list[DataReference] = []
    seen: set[tuple[str, str, str]] = set()

    for source in files:
        if source.suffix.lower() not in TEXT_SUFFIXES:
            continue

        try:
            text = source.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        matches: list[tuple[str, str]] = []

        for match in PUBLIC_DATA_REFERENCE_PATTERN.finditer(text):
            full = match.group(0).strip("\"'")
            matches.append((full, "quoted_reference"))

        for match in GENERAL_DATA_REFERENCE_PATTERN.finditer(text):
            matches.append((match.group("path"), "general_reference"))

        for raw_reference, kind in matches:
            normalized = raw_reference.replace("\\", "/")
            key = (relative(source), normalized.lower(), kind)
            if key in seen:
                continue
            seen.add(key)

            resolved = resolve_data_reference(source, normalized)

            references.append(
                DataReference(
                    source_file=relative(source),
                    referenced_value=normalized,
                    resolved_path=relative(resolved) if resolved else None,
                    exists=resolved is not None,
                    reference_kind=kind,
                )
            )

    return sorted(
        references,
        key=lambda item: (
            item.source_file.lower(),
            item.referenced_value.lower(),
            item.reference_kind,
        ),
    )


def scan_python_dependencies(files: list[Path]) -> list[PythonDependency]:
    dependencies: list[PythonDependency] = []

    for source in files:
        if source.suffix.lower() != ".py":
            continue

        try:
            text = source.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (OSError, SyntaxError):
            continue

        imported_modules: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module)

        for module in sorted(imported_modules):
            module_parts = module.split(".")
            candidate_file = REPOSITORY_ROOT.joinpath(*module_parts).with_suffix(".py")
            candidate_package = REPOSITORY_ROOT.joinpath(*module_parts) / "__init__.py"

            local_path: Path | None = None

            if candidate_file.exists():
                local_path = candidate_file
            elif candidate_package.exists():
                local_path = candidate_package

            dependencies.append(
                PythonDependency(
                    source_file=relative(source),
                    imported_module=module,
                    local_candidate=relative(local_path) if local_path else None,
                    local_exists=local_path is not None,
                )
            )

    return dependencies


def duplicate_groups(records: list[FileRecord]) -> list[dict[str, Any]]:
    by_hash: dict[str, list[FileRecord]] = defaultdict(list)

    for record in records:
        if record.sha256:
            by_hash[record.sha256].append(record)

    groups: list[dict[str, Any]] = []

    for digest, members in by_hash.items():
        if len(members) < 2:
            continue

        groups.append(
            {
                "sha256": digest,
                "file_count": len(members),
                "total_bytes": sum(item.size_bytes for item in members),
                "paths": [item.relative_path for item in members],
            }
        )

    return sorted(
        groups,
        key=lambda group: (-group["file_count"], -group["total_bytes"]),
    )


def basename_collision_groups(records: list[FileRecord]) -> list[dict[str, Any]]:
    by_name: dict[str, list[str]] = defaultdict(list)

    for record in records:
        by_name[Path(record.relative_path).name.lower()].append(record.relative_path)

    collisions = []

    for basename, paths in by_name.items():
        if len(paths) < 2:
            continue

        collisions.append(
            {
                "basename": basename,
                "file_count": len(paths),
                "paths": sorted(paths),
            }
        )

    return sorted(
        collisions,
        key=lambda group: (-group["file_count"], group["basename"]),
    )


def derive_data_usage(
    records: list[FileRecord],
    references: list[DataReference],
) -> list[dict[str, Any]]:
    usage_counter: Counter[str] = Counter()

    for reference in references:
        if reference.exists and reference.resolved_path:
            usage_counter[reference.resolved_path] += 1

    results = []

    for record in records:
        if record.suffix not in DATA_SUFFIXES:
            continue

        results.append(
            {
                "relative_path": record.relative_path,
                "category": record.category,
                "size_bytes": record.size_bytes,
                "reference_count": usage_counter.get(record.relative_path, 0),
                "is_unreferenced": usage_counter.get(record.relative_path, 0) == 0,
                "is_checkpoint_like": record.is_checkpoint_like,
            }
        )

    return sorted(
        results,
        key=lambda item: (
            not item["is_unreferenced"],
            item["category"],
            item["relative_path"].lower(),
        ),
    )


def scan_builder_output_mentions(
    records: list[FileRecord],
    references: list[DataReference],
) -> list[dict[str, Any]]:
    references_by_source: dict[str, list[DataReference]] = defaultdict(list)

    for reference in references:
        references_by_source[reference.source_file].append(reference)

    output_rows: list[dict[str, Any]] = []

    for record in records:
        if record.category != "python_builder":
            continue

        builder_references = references_by_source.get(record.relative_path, [])

        output_like = [
            reference
            for reference in builder_references
            if any(
                token in reference.referenced_value.lower()
                for token in (
                    "output",
                    "public/data",
                    "docs/",
                    "warehouse",
                    "feed",
                    "fact",
                    "latest",
                    ".csv",
                    ".json",
                )
            )
        ]

        output_rows.append(
            {
                "builder": record.relative_path,
                "data_reference_count": len(builder_references),
                "existing_reference_count": sum(1 for item in builder_references if item.exists),
                "missing_reference_count": sum(1 for item in builder_references if not item.exists),
                "referenced_paths": sorted(
                    {
                        item.resolved_path or item.referenced_value
                        for item in output_like
                    }
                ),
            }
        )

    return output_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []

    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            normalized = {}
            for key, value in row.items():
                if isinstance(value, (list, dict)):
                    normalized[key] = json.dumps(value, ensure_ascii=False)
                else:
                    normalized[key] = value
            writer.writerow(normalized)


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    files = iter_repository_files()
    inventory = build_file_inventory(files)
    references = scan_data_references(files)
    python_dependencies = scan_python_dependencies(files)

    duplicates = duplicate_groups(inventory)
    basename_collisions = basename_collision_groups(inventory)
    data_usage = derive_data_usage(inventory, references)
    builder_outputs = scan_builder_output_mentions(inventory, references)

    missing_references = [
        asdict(reference)
        for reference in references
        if not reference.exists
    ]

    checkpoint_files = [
        asdict(record)
        for record in inventory
        if record.is_checkpoint_like
    ]

    unreferenced_data = [
        row
        for row in data_usage
        if row["is_unreferenced"]
    ]

    category_counts = Counter(record.category for record in inventory)
    suffix_counts = Counter(record.suffix or "(no suffix)" for record in inventory)

    summary = {
        "audit_id": "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(REPOSITORY_ROOT),
        "overall_status": "REVIEW_REQUIRED",
        "counts": {
            "repository_files": len(inventory),
            "data_files": sum(1 for item in inventory if item.suffix in DATA_SUFFIXES),
            "python_builders": sum(1 for item in inventory if item.category == "python_builder"),
            "frontend_services": sum(1 for item in inventory if item.category == "frontend_service"),
            "data_references": len(references),
            "missing_data_references": len(missing_references),
            "unreferenced_data_files": len(unreferenced_data),
            "exact_duplicate_groups": len(duplicates),
            "basename_collision_groups": len(basename_collisions),
            "checkpoint_like_files": len(checkpoint_files),
            "python_dependency_rows": len(python_dependencies),
        },
        "category_counts": dict(sorted(category_counts.items())),
        "suffix_counts": dict(sorted(suffix_counts.items())),
        "principles": [
            "No files modified outside docs/architecture-audit.",
            "No thresholds changed.",
            "No data fabricated.",
            "Audit results require review before any cleanup.",
            "Unreferenced does not automatically mean obsolete.",
            "String-reference discovery is evidence, not full runtime proof.",
        ],
    }

    report = {
        "summary": summary,
        "missing_data_references": missing_references,
        "unreferenced_data_files": unreferenced_data,
        "exact_duplicate_groups": duplicates,
        "basename_collision_groups": basename_collisions,
        "checkpoint_like_files": checkpoint_files,
        "builder_output_mentions": builder_outputs,
    }

    (OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    (OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_REPORT.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    write_csv(
        OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_FILE_INVENTORY.csv",
        [asdict(item) for item in inventory],
    )

    write_csv(
        OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_DATA_REFERENCES.csv",
        [asdict(item) for item in references],
    )

    write_csv(
        OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_MISSING_REFERENCES.csv",
        missing_references,
    )

    write_csv(
        OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_DATA_USAGE.csv",
        data_usage,
    )

    write_csv(
        OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_DUPLICATE_GROUPS.csv",
        duplicates,
    )

    write_csv(
        OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_BASENAME_COLLISIONS.csv",
        basename_collisions,
    )

    write_csv(
        OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_CHECKPOINT_FILES.csv",
        checkpoint_files,
    )

    write_csv(
        OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_BUILDER_OUTPUT_MENTIONS.csv",
        builder_outputs,
    )

    write_csv(
        OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_PYTHON_DEPENDENCIES.csv",
        [asdict(item) for item in python_dependencies],
    )

    markdown_lines = [
        "# EDGEIQ Canonical Data Architecture Audit V1",
        "",
        f"- Generated: `{summary['generated_at_utc']}`",
        f"- Repository files: `{summary['counts']['repository_files']}`",
        f"- Data files: `{summary['counts']['data_files']}`",
        f"- Python builders: `{summary['counts']['python_builders']}`",
        f"- Frontend services: `{summary['counts']['frontend_services']}`",
        f"- Data references: `{summary['counts']['data_references']}`",
        f"- Missing data references: `{summary['counts']['missing_data_references']}`",
        f"- Unreferenced data files: `{summary['counts']['unreferenced_data_files']}`",
        f"- Exact duplicate groups: `{summary['counts']['exact_duplicate_groups']}`",
        f"- Basename collision groups: `{summary['counts']['basename_collision_groups']}`",
        f"- Checkpoint-like files: `{summary['counts']['checkpoint_like_files']}`",
        "",
        "## Interpretation",
        "",
        "This is a discovery audit, not a deletion directive.",
        "",
        "- Missing references require investigation.",
        "- Unreferenced files may still be manual inputs, archival evidence or dynamically resolved.",
        "- Duplicate hashes identify byte-identical files only.",
        "- Basename collisions identify possible canonical ambiguity.",
        "- Checkpoint-like files are reported but not altered.",
        "",
        "## Output files",
        "",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_FILE_INVENTORY.csv`",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_DATA_REFERENCES.csv`",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_MISSING_REFERENCES.csv`",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_DATA_USAGE.csv`",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_DUPLICATE_GROUPS.csv`",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_BASENAME_COLLISIONS.csv`",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_CHECKPOINT_FILES.csv`",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_BUILDER_OUTPUT_MENTIONS.csv`",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_PYTHON_DEPENDENCIES.csv`",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_REPORT.json`",
        "- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_SUMMARY.json`",
    ]

    (OUTPUT_ROOT / "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1.md").write_text(
        "\n".join(markdown_lines) + "\n",
        encoding="utf-8",
    )

    print()
    print("=== EDGEIQ CANONICAL DATA ARCHITECTURE AUDIT V1 ===")
    print(json.dumps(summary["counts"], indent=2))
    print()
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}")
    print("OVERALL_STATUS=REVIEW_REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
