from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


AUDIT_ID = "EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V2"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPOSITORY_ROOT / "docs" / "architecture-audit-v2"

IGNORED_DIRECTORY_NAMES = {
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

DATA_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".parquet",
    ".feather",
    ".sqlite",
    ".db",
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

HASH_ELIGIBLE_SUFFIXES = DATA_SUFFIXES | SOURCE_SUFFIXES | {
    ".md",
    ".txt",
    ".html",
    ".css",
}

REFERENCE_PATTERN = re.compile(
    r"""(?P<reference>
        [A-Za-z0-9_./\\:@$(){}\[\]\- ]+
        \.(?:csv|json|jsonl|parquet|feather|sqlite|db)
    )""",
    re.IGNORECASE | re.VERBOSE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalise_relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def should_ignore(path: Path) -> bool:
    try:
        relative = path.relative_to(REPOSITORY_ROOT)
    except ValueError:
        return True

    return any(part in IGNORED_DIRECTORY_NAMES for part in relative.parts)


def classify_domain(relative_path: str) -> str:
    value = relative_path.replace("\\", "/").lower()
    parts = value.split("/")
    first = parts[0] if parts else ""

    if value.startswith("docs/architecture-audit"):
        return "audit_output"

    if first == "checkpoints" or "/checkpoints/" in value:
        return "checkpoint"

    if (
        first.startswith("_archive")
        or first == "archive"
        or "/_archive/" in value
        or "/archive/" in value
    ):
        return "archive"

    if value.startswith("docs/performance-intelligence/"):
        return "performance_intelligence_evidence"

    if value.startswith("outputs/performance-intelligence/"):
        return "performance_intelligence_output"

    if value.startswith("outputs/"):
        return "generated_output"

    if value.startswith("data/weather-source-audit/"):
        return "source_discovery_evidence"

    if value.startswith("docs/"):
        return "documentation"

    if value.startswith("public/data/"):
        return "production_public_data"

    if value.startswith("public/"):
        return "production_public_asset"

    if value.startswith("src/"):
        return "production_frontend"

    if value.startswith("scripts/"):
        return "production_automation"

    if len(parts) == 1:
        suffix = Path(value).suffix.lower()
        if suffix in SOURCE_SUFFIXES or suffix in {
            ".json",
            ".md",
            ".txt",
            ".yaml",
            ".yml",
            ".toml",
        }:
            return "production_root"

    return "other_repository"


def classify_category(relative_path: str, suffix: str) -> str:
    value = relative_path.lower()

    if suffix in DATA_SUFFIXES:
        if "warehouse" in value or "_fact" in value or "/facts/" in value:
            return "warehouse_or_fact"
        if "canonical" in value or "registry" in value or "manifest" in value:
            return "canonical_or_registry"
        if "feed" in value:
            return "feed"
        return "data"

    if suffix == ".py":
        name = Path(value).name
        if name.startswith("audit_") or "audit" in name:
            return "python_audit"
        if name.startswith("build_") or name.startswith("apply_"):
            return "python_builder"
        return "python"

    if suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        if "service" in value:
            return "frontend_service"
        if suffix in {".tsx", ".jsx"}:
            return "frontend_component"
        return "frontend_code"

    if suffix == ".ps1":
        return "powershell"

    if suffix == ".md":
        return "documentation"

    if suffix in {".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"}:
        return "asset"

    return "other"


def is_live_production_domain(domain: str) -> bool:
    return domain in {
        "production_public_data",
        "production_public_asset",
        "production_frontend",
        "production_automation",
        "production_root",
    }


def is_live_code_domain(domain: str) -> bool:
    return domain in {
        "production_frontend",
        "production_automation",
        "production_root",
    }


def iter_repository_files() -> Iterable[Path]:
    for root, directory_names, file_names in os.walk(REPOSITORY_ROOT):
        root_path = Path(root)

        directory_names[:] = [
            name
            for name in directory_names
            if name not in IGNORED_DIRECTORY_NAMES
            and not should_ignore(root_path / name)
        ]

        for file_name in file_names:
            path = root_path / file_name
            if should_ignore(path):
                continue
            if path.resolve() == Path(__file__).resolve():
                yield path
                continue
            yield path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


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


def clean_reference(raw_value: str) -> str:
    value = raw_value.strip()
    value = value.strip("'\"`")
    value = value.rstrip(".,;:)]}")
    value = value.replace("\\\\", "\\")
    return value.strip()


def reference_candidates(source_path: Path, reference: str) -> list[Path]:
    normalised = reference.replace("\\", "/")
    candidates: list[Path] = []

    candidate_path = Path(normalised)

    if candidate_path.is_absolute():
        candidates.append(candidate_path)
    else:
        candidates.append(REPOSITORY_ROOT / candidate_path)
        candidates.append(source_path.parent / candidate_path)

        if normalised.startswith("/data/"):
            candidates.append(
                REPOSITORY_ROOT / "public" / normalised.lstrip("/")
            )

        if normalised.startswith("data/"):
            candidates.append(REPOSITORY_ROOT / "public" / normalised)

        basename = Path(normalised).name
        if basename:
            candidates.append(REPOSITORY_ROOT / "public" / "data" / basename)

    unique: list[Path] = []
    seen: set[str] = set()

    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)

    return unique


def resolve_reference(source_path: Path, reference: str) -> tuple[bool, str]:
    for candidate in reference_candidates(source_path, reference):
        try:
            if candidate.exists():
                if candidate.is_relative_to(REPOSITORY_ROOT):
                    return True, normalise_relative(candidate)
                return True, str(candidate)
        except OSError:
            continue

    return False, ""


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def scan_python_dependencies(
    inventory: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    production_python_files = [
        row
        for row in inventory
        if row["suffix"] == ".py"
        and is_live_code_domain(row["domain"])
    ]

    local_modules: set[str] = set()

    for row in production_python_files:
        path = REPOSITORY_ROOT / row["relative_path"]
        local_modules.add(path.stem)

    rows: list[dict[str, Any]] = []

    for index, item in enumerate(production_python_files, start=1):
        path = REPOSITORY_ROOT / item["relative_path"]

        if index == 1 or index % 100 == 0:
            print(
                f"[dependencies] {index}/{len(production_python_files)} "
                f"{item['relative_path']}",
                flush=True,
            )

        text = safe_read_text(path)
        if text is None:
            continue

        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            rows.append(
                {
                    "source_file": item["relative_path"],
                    "module": "",
                    "top_level_module": "",
                    "dependency_type": "syntax_error",
                    "local_module_exists": "",
                    "detail": f"{exc.msg} at line {exc.lineno}",
                }
            )
            continue

        for node in ast.walk(tree):
            module_name = ""

            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    top_level = module_name.split(".")[0]
                    rows.append(
                        {
                            "source_file": item["relative_path"],
                            "module": module_name,
                            "top_level_module": top_level,
                            "dependency_type": "import",
                            "local_module_exists": top_level in local_modules,
                            "detail": "",
                        }
                    )

            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                top_level = module_name.split(".")[0] if module_name else ""

                rows.append(
                    {
                        "source_file": item["relative_path"],
                        "module": module_name,
                        "top_level_module": top_level,
                        "dependency_type": "import_from",
                        "local_module_exists": (
                            top_level in local_modules if top_level else ""
                        ),
                        "detail": f"level={node.level}",
                    }
                )

    return rows


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(f"REPOSITORY_ROOT={REPOSITORY_ROOT}", flush=True)
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}", flush=True)
    print("", flush=True)

    print("[1/7] Building repository inventory...", flush=True)

    inventory: list[dict[str, Any]] = []
    domain_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    suffix_counts: Counter[str] = Counter()

    paths = list(iter_repository_files())
    total_paths = len(paths)

    for index, path in enumerate(paths, start=1):
        if index == 1 or index % 1000 == 0:
            print(f"[inventory] {index}/{total_paths}", flush=True)

        try:
            stat = path.stat()
        except OSError:
            continue

        relative_path = normalise_relative(path)
        suffix = path.suffix.lower()
        domain = classify_domain(relative_path)
        category = classify_category(relative_path, suffix)

        row = {
            "relative_path": relative_path,
            "domain": domain,
            "category": category,
            "suffix": suffix or "(no suffix)",
            "size_bytes": stat.st_size,
            "modified_utc": datetime.fromtimestamp(
                stat.st_mtime,
                tz=timezone.utc,
            ).isoformat(),
            "is_live_production": is_live_production_domain(domain),
            "is_live_code": is_live_code_domain(domain),
        }

        inventory.append(row)
        domain_counts[domain] += 1
        category_counts[category] += 1
        suffix_counts[suffix or "(no suffix)"] += 1

    production_inventory = [
        row for row in inventory if row["is_live_production"]
    ]

    production_data = [
        row
        for row in production_inventory
        if row["suffix"] in DATA_SUFFIXES
    ]

    production_sources = [
        row
        for row in production_inventory
        if row["suffix"] in SOURCE_SUFFIXES
        and row["is_live_code"]
    ]

    print(
        f"[inventory] repository={len(inventory)} "
        f"production={len(production_inventory)} "
        f"production_data={len(production_data)} "
        f"production_sources={len(production_sources)}",
        flush=True,
    )

    print("[2/7] Scanning live production data references...", flush=True)

    reference_rows: list[dict[str, Any]] = []
    source_reference_counts: Counter[str] = Counter()
    target_reference_counts: Counter[str] = Counter()

    for index, item in enumerate(production_sources, start=1):
        if index == 1 or index % 100 == 0:
            print(
                f"[references] {index}/{len(production_sources)} "
                f"{item['relative_path']}",
                flush=True,
            )

        source_path = REPOSITORY_ROOT / item["relative_path"]
        text = safe_read_text(source_path)

        if text is None:
            continue

        for match in REFERENCE_PATTERN.finditer(text):
            reference = clean_reference(match.group("reference"))

            if not reference:
                continue

            exists, resolved_path = resolve_reference(source_path, reference)

            row = {
                "source_file": item["relative_path"],
                "source_domain": item["domain"],
                "referenced_value": reference,
                "exists": exists,
                "resolved_path": resolved_path,
                "resolved_domain": (
                    classify_domain(resolved_path)
                    if exists and resolved_path
                    and not Path(resolved_path).is_absolute()
                    else ""
                ),
            }

            reference_rows.append(row)
            source_reference_counts[item["relative_path"]] += 1

            if exists and resolved_path:
                target_reference_counts[resolved_path] += 1

    missing_reference_rows = [
        row for row in reference_rows if not row["exists"]
    ]

    print(
        f"[references] discovered={len(reference_rows)} "
        f"missing={len(missing_reference_rows)}",
        flush=True,
    )

    print("[3/7] Calculating live production data usage...", flush=True)

    data_usage_rows: list[dict[str, Any]] = []

    for row in production_data:
        relative_path = row["relative_path"]
        basename = Path(relative_path).name

        reference_count = target_reference_counts.get(relative_path, 0)

        if reference_count == 0:
            reference_count = sum(
                count
                for target, count in target_reference_counts.items()
                if Path(target).name == basename
            )

        data_usage_rows.append(
            {
                "relative_path": relative_path,
                "domain": row["domain"],
                "category": row["category"],
                "suffix": row["suffix"],
                "size_bytes": row["size_bytes"],
                "reference_count": reference_count,
                "is_unreferenced": reference_count == 0,
            }
        )

    unreferenced_production_data = [
        row for row in data_usage_rows if row["is_unreferenced"]
    ]

    print(
        f"[usage] production_data={len(data_usage_rows)} "
        f"unreferenced={len(unreferenced_production_data)}",
        flush=True,
    )

    print("[4/7] Detecting live production duplicate candidates...", flush=True)

    size_groups: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)

    for row in production_inventory:
        if row["suffix"] in HASH_ELIGIBLE_SUFFIXES:
            size_groups[int(row["size_bytes"])].append(row)

    hash_candidates: list[dict[str, Any]] = []

    for size, rows in size_groups.items():
        if len(rows) > 1:
            hash_candidates.extend(rows)

    hash_groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for index, row in enumerate(hash_candidates, start=1):
        if index == 1 or index % 250 == 0:
            print(
                f"[hashing] {index}/{len(hash_candidates)} "
                f"{row['relative_path']}",
                flush=True,
            )

        path = REPOSITORY_ROOT / row["relative_path"]

        try:
            digest = sha256_file(path)
        except OSError:
            continue

        hash_groups[digest].append(row)

    duplicate_rows: list[dict[str, Any]] = []

    for digest, rows in hash_groups.items():
        if len(rows) < 2:
            continue

        file_size = int(rows[0]["size_bytes"])

        duplicate_rows.append(
            {
                "sha256": digest,
                "file_count": len(rows),
                "file_size_bytes": file_size,
                "total_bytes": file_size * len(rows),
                "potential_redundant_bytes": file_size * (len(rows) - 1),
                "domains": json.dumps(
                    sorted({row["domain"] for row in rows}),
                    ensure_ascii=False,
                ),
                "paths": json.dumps(
                    sorted(row["relative_path"] for row in rows),
                    ensure_ascii=False,
                ),
            }
        )

    duplicate_rows.sort(
        key=lambda row: (
            int(row["potential_redundant_bytes"]),
            int(row["file_count"]),
        ),
        reverse=True,
    )

    print(
        f"[duplicates] exact_production_groups={len(duplicate_rows)}",
        flush=True,
    )

    print("[5/7] Detecting live production basename collisions...", flush=True)

    basename_groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in production_inventory:
        basename_groups[Path(row["relative_path"]).name.lower()].append(row)

    basename_collision_rows: list[dict[str, Any]] = []

    for basename, rows in basename_groups.items():
        if len(rows) < 2:
            continue

        basename_collision_rows.append(
            {
                "basename": basename,
                "file_count": len(rows),
                "domains": json.dumps(
                    sorted({row["domain"] for row in rows}),
                    ensure_ascii=False,
                ),
                "paths": json.dumps(
                    sorted(row["relative_path"] for row in rows),
                    ensure_ascii=False,
                ),
            }
        )

    basename_collision_rows.sort(
        key=lambda row: int(row["file_count"]),
        reverse=True,
    )

    print(
        f"[collisions] production_basename_groups="
        f"{len(basename_collision_rows)}",
        flush=True,
    )

    print("[6/7] Scanning live Python dependencies...", flush=True)

    dependency_rows = scan_python_dependencies(inventory)

    syntax_error_rows = [
        row
        for row in dependency_rows
        if row["dependency_type"] == "syntax_error"
    ]

    print(
        f"[dependencies] rows={len(dependency_rows)} "
        f"syntax_errors={len(syntax_error_rows)}",
        flush=True,
    )

    print("[7/7] Writing governed audit outputs...", flush=True)

    inventory_path = (
        OUTPUT_ROOT / f"{AUDIT_ID}_REPOSITORY_INVENTORY.csv"
    )
    production_inventory_path = (
        OUTPUT_ROOT / f"{AUDIT_ID}_PRODUCTION_INVENTORY.csv"
    )
    reference_path = (
        OUTPUT_ROOT / f"{AUDIT_ID}_PRODUCTION_DATA_REFERENCES.csv"
    )
    missing_reference_path = (
        OUTPUT_ROOT / f"{AUDIT_ID}_PRODUCTION_MISSING_REFERENCES.csv"
    )
    data_usage_path = (
        OUTPUT_ROOT / f"{AUDIT_ID}_PRODUCTION_DATA_USAGE.csv"
    )
    duplicate_path = (
        OUTPUT_ROOT / f"{AUDIT_ID}_PRODUCTION_DUPLICATE_GROUPS.csv"
    )
    basename_path = (
        OUTPUT_ROOT / f"{AUDIT_ID}_PRODUCTION_BASENAME_COLLISIONS.csv"
    )
    dependency_path = (
        OUTPUT_ROOT / f"{AUDIT_ID}_PRODUCTION_PYTHON_DEPENDENCIES.csv"
    )

    inventory_fields = [
        "relative_path",
        "domain",
        "category",
        "suffix",
        "size_bytes",
        "modified_utc",
        "is_live_production",
        "is_live_code",
    ]

    write_csv(inventory_path, inventory, inventory_fields)
    write_csv(
        production_inventory_path,
        production_inventory,
        inventory_fields,
    )

    write_csv(
        reference_path,
        reference_rows,
        [
            "source_file",
            "source_domain",
            "referenced_value",
            "exists",
            "resolved_path",
            "resolved_domain",
        ],
    )

    write_csv(
        missing_reference_path,
        missing_reference_rows,
        [
            "source_file",
            "source_domain",
            "referenced_value",
            "exists",
            "resolved_path",
            "resolved_domain",
        ],
    )

    write_csv(
        data_usage_path,
        sorted(
            data_usage_rows,
            key=lambda row: (
                bool(row["is_unreferenced"]),
                int(row["size_bytes"]),
            ),
            reverse=True,
        ),
        [
            "relative_path",
            "domain",
            "category",
            "suffix",
            "size_bytes",
            "reference_count",
            "is_unreferenced",
        ],
    )

    write_csv(
        duplicate_path,
        duplicate_rows,
        [
            "sha256",
            "file_count",
            "file_size_bytes",
            "total_bytes",
            "potential_redundant_bytes",
            "domains",
            "paths",
        ],
    )

    write_csv(
        basename_path,
        basename_collision_rows,
        [
            "basename",
            "file_count",
            "domains",
            "paths",
        ],
    )

    write_csv(
        dependency_path,
        dependency_rows,
        [
            "source_file",
            "module",
            "top_level_module",
            "dependency_type",
            "local_module_exists",
            "detail",
        ],
    )

    domain_summary_rows = []

    for domain, count in sorted(domain_counts.items()):
        domain_size = sum(
            int(row["size_bytes"])
            for row in inventory
            if row["domain"] == domain
        )

        domain_summary_rows.append(
            {
                "domain": domain,
                "file_count": count,
                "total_bytes": domain_size,
            }
        )

    write_csv(
        OUTPUT_ROOT / f"{AUDIT_ID}_DOMAIN_SUMMARY.csv",
        domain_summary_rows,
        ["domain", "file_count", "total_bytes"],
    )

    production_duplicate_redundant_bytes = sum(
        int(row["potential_redundant_bytes"])
        for row in duplicate_rows
    )

    counts = {
        "repository_files": len(inventory),
        "live_production_files": len(production_inventory),
        "live_production_data_files": len(production_data),
        "live_production_source_files": len(production_sources),
        "production_data_references": len(reference_rows),
        "production_missing_data_references": len(
            missing_reference_rows
        ),
        "production_unreferenced_data_files": len(
            unreferenced_production_data
        ),
        "production_exact_duplicate_groups": len(duplicate_rows),
        "production_duplicate_potential_redundant_bytes": (
            production_duplicate_redundant_bytes
        ),
        "production_basename_collision_groups": len(
            basename_collision_rows
        ),
        "production_python_dependency_rows": len(dependency_rows),
        "production_python_syntax_errors": len(syntax_error_rows),
    }

    overall_status = "PASS"

    if (
        counts["production_missing_data_references"] > 0
        or counts["production_python_syntax_errors"] > 0
    ):
        overall_status = "REVIEW_REQUIRED"

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": utc_now(),
        "repository_root": str(REPOSITORY_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "overall_status": overall_status,
        "scope": {
            "production_domains": [
                "production_public_data",
                "production_public_asset",
                "production_frontend",
                "production_automation",
                "production_root",
            ],
            "non_production_domains_are_inventoried_but_excluded_from_"
            "production_findings": True,
            "ignored_directories": sorted(IGNORED_DIRECTORY_NAMES),
        },
        "counts": counts,
        "domain_counts": dict(sorted(domain_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "suffix_counts": dict(sorted(suffix_counts.items())),
        "principles": [
            "No files modified outside docs/architecture-audit-v2.",
            "No files deleted or moved.",
            "No thresholds changed.",
            "No data fabricated.",
            "Checkpoints and archives are excluded from production findings.",
            "Unreferenced does not automatically mean obsolete.",
            "String-reference discovery is evidence, not full runtime proof.",
            "Duplicate detection hashes live production candidates only.",
        ],
    }

    write_json(
        OUTPUT_ROOT / f"{AUDIT_ID}_SUMMARY.json",
        summary,
    )

    report = {
        **summary,
        "top_missing_references": missing_reference_rows[:100],
        "top_unreferenced_production_data": sorted(
            unreferenced_production_data,
            key=lambda row: int(row["size_bytes"]),
            reverse=True,
        )[:100],
        "top_production_duplicate_groups": duplicate_rows[:100],
        "top_production_basename_collisions": (
            basename_collision_rows[:100]
        ),
        "python_syntax_errors": syntax_error_rows,
    }

    write_json(
        OUTPUT_ROOT / f"{AUDIT_ID}_REPORT.json",
        report,
    )

    markdown_lines = [
        f"# {AUDIT_ID}",
        "",
        f"- Generated UTC: `{summary['generated_at_utc']}`",
        f"- Repository: `{REPOSITORY_ROOT}`",
        f"- Overall status: **{overall_status}**",
        "",
        "## Production findings",
        "",
    ]

    for key, value in counts.items():
        markdown_lines.append(f"- {key}: `{value}`")

    markdown_lines.extend(
        [
            "",
            "## Domain separation",
            "",
        ]
    )

    for row in domain_summary_rows:
        markdown_lines.append(
            f"- {row['domain']}: "
            f"`{row['file_count']}` files, "
            f"`{row['total_bytes']}` bytes"
        )

    markdown_lines.extend(
        [
            "",
            "## Interpretation rules",
            "",
            "- Checkpoints and archives are not treated as live production.",
            "- A missing string reference requires review; it is not "
            "automatically a runtime defect.",
            "- An unreferenced data file is not automatically obsolete.",
            "- Duplicate files are evidence for review only; nothing was "
            "deleted.",
            "",
        ]
    )

    (
        OUTPUT_ROOT / f"{AUDIT_ID}_SUMMARY.md"
    ).write_text(
        "\n".join(markdown_lines),
        encoding="utf-8",
    )

    print("", flush=True)
    print("=== AUDIT COMPLETE ===", flush=True)
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
