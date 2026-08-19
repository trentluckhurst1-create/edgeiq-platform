from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "docs" / "performance-intelligence"
AUDIT_DIR = OUTPUT_ROOT / "audits"
INVENTORY_DIR = OUTPUT_ROOT / "inventories"

SCAN_EXTENSIONS = {
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".csv",
    ".txt",
    ".md",
    ".sql",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".parquet",
    ".feather",
    ".yaml",
    ".yml",
    ".xml",
}

DATA_EXTENSIONS = {
    ".json",
    ".csv",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".parquet",
    ".feather",
}

EXCLUDED_DIRECTORIES = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".vite",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
}

CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "results": (
        "result",
        "results",
        "finishing_position",
        "official_result",
        "race_result",
        "winner",
        "placing",
    ),
    "sectionals": (
        "sectional",
        "split",
        "last_800",
        "last_600",
        "last_400",
        "last_200",
        "800_600",
        "600_400",
        "400_200",
        "200_finish",
        "200-f",
        "8-6",
        "6-4",
        "4-2",
        "2-f",
    ),
    "benchmarks": (
        "benchmark",
        "par_time",
        "standard_time",
        "track_standard",
        "distance_standard",
        "class_standard",
        "pace_standard",
    ),
    "length_conversion": (
        "length_conversion",
        "seconds_to_lengths",
        "seconds per length",
        "seconds_per_length",
        "lengths_vs",
        "lengths difference",
        "lengths_difference",
        "time_to_length",
    ),
    "performance": (
        "performance",
        "runner_profile",
        "historical_form",
        "form_workbench",
        "epi",
        "eri",
        "rating",
        "race_strength",
    ),
    "identity": (
        "canonical_id",
        "horse_id",
        "race_id",
        "meeting_id",
        "track_id",
        "course_id",
        "trainer_id",
        "jockey_id",
        "identity_resolution",
        "deduplicate",
        "duplicate",
        "alias",
        "mapping",
    ),
    "quality": (
        "quality_state",
        "data_quality",
        "confidence",
        "excluded",
        "mismatch",
        "inconsistency",
        "validation",
        "audit_pass",
        "audit_fail",
    ),
    "patterns": (
        "fingerprint",
        "pattern",
        "late_burst",
        "sustained_run",
        "early_pressure",
        "flat_spot",
        "race_shape",
        "pace_shape",
        "campaign",
        "dna",
    ),
    "weather_track": (
        "track_rating",
        "going",
        "rail",
        "weather",
        "wind",
        "temperature",
        "rainfall",
        "irrigation",
    ),
    "frontend_consumer": (
        "fetch(",
        "axios",
        "public/data",
        "useeffect",
        "react",
        "service",
        "workspace",
        "formguide",
        "racefile",
    ),
}

HIGH_VALUE_NAME_PATTERNS = (
    "warehouse",
    "result",
    "sectional",
    "benchmark",
    "length",
    "performance",
    "historical",
    "form",
    "runner",
    "race",
    "meeting",
    "horse",
    "identity",
    "canonical",
    "epi",
    "eri",
    "audit",
    "quality",
    "fingerprint",
    "pattern",
    "campaign",
    "dna",
    "pace",
    "speed",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRECTORIES for part in path.parts)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


def safe_read(path: Path, limit: int = 2_000_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def csv_metadata(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "row_count": None,
        "column_count": None,
        "columns": [],
        "csv_error": "",
    }
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            row_count = sum(1 for _ in reader)
        result["row_count"] = row_count
        result["column_count"] = len(header)
        result["columns"] = header
    except Exception as exc:
        result["csv_error"] = str(exc)
    return result


def json_metadata(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "json_type": None,
        "record_count": None,
        "top_level_keys": [],
        "json_error": "",
    }
    try:
        if path.stat().st_size > 50_000_000:
            result["json_error"] = "Skipped JSON parsing because file exceeds 50 MB."
            return result

        with path.open("r", encoding="utf-8-sig", errors="ignore") as handle:
            payload = json.load(handle)

        result["json_type"] = type(payload).__name__

        if isinstance(payload, list):
            result["record_count"] = len(payload)
            if payload and isinstance(payload[0], dict):
                result["top_level_keys"] = sorted(payload[0].keys())
        elif isinstance(payload, dict):
            result["record_count"] = len(payload)
            result["top_level_keys"] = sorted(payload.keys())
    except Exception as exc:
        result["json_error"] = str(exc)
    return result


def detect_categories(path_text: str, content: str) -> list[str]:
    haystack = f"{path_text}\n{content}".lower()
    matches: list[str] = []

    for category, patterns in CATEGORY_PATTERNS.items():
        if any(pattern.lower() in haystack for pattern in patterns):
            matches.append(category)

    return sorted(set(matches))


def likely_high_value(path_text: str, categories: list[str]) -> bool:
    lowered = path_text.lower()
    return bool(categories) or any(pattern in lowered for pattern in HIGH_VALUE_NAME_PATTERNS)


def scan_files() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if excluded(path):
            continue

        suffix = path.suffix.lower()
        if suffix not in SCAN_EXTENSIONS:
            continue

        stat = path.stat()
        path_text = relative(path)
        content = safe_read(path)
        categories = detect_categories(path_text, content)

        if not likely_high_value(path_text, categories):
            continue

        record: dict[str, Any] = {
            "path": path_text,
            "name": path.name,
            "extension": suffix,
            "size_bytes": stat.st_size,
            "modified_utc": datetime.fromtimestamp(
                stat.st_mtime,
                tz=timezone.utc,
            ).isoformat(),
            "sha256": sha256(path),
            "categories": categories,
            "is_data_asset": suffix in DATA_EXTENSIONS,
            "is_script": suffix in {".py", ".ps1"},
            "is_frontend": suffix in {".ts", ".tsx", ".js", ".jsx"},
            "row_count": None,
            "column_count": None,
            "columns": [],
            "json_type": None,
            "record_count": None,
            "top_level_keys": [],
            "metadata_error": "",
        }

        if suffix == ".csv":
            metadata = csv_metadata(path)
            record["row_count"] = metadata["row_count"]
            record["column_count"] = metadata["column_count"]
            record["columns"] = metadata["columns"]
            record["metadata_error"] = metadata["csv_error"]

        elif suffix == ".json":
            metadata = json_metadata(path)
            record["json_type"] = metadata["json_type"]
            record["record_count"] = metadata["record_count"]
            record["top_level_keys"] = metadata["top_level_keys"]
            record["metadata_error"] = metadata["json_error"]

        records.append(record)

    return sorted(records, key=lambda item: item["path"].lower())


def extract_references(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    data_name_lookup: dict[str, list[str]] = defaultdict(list)

    for record in records:
        if record["is_data_asset"]:
            data_name_lookup[record["name"].lower()].append(record["path"])

    reference_pattern = re.compile(
        r"""(?P<quote>["'])(?P<target>[^"']+\.(?:csv|json|parquet|sqlite|sqlite3|db|feather))(?P=quote)""",
        flags=re.IGNORECASE,
    )

    for record in records:
        if not (record["is_script"] or record["is_frontend"]):
            continue

        source_path = ROOT / record["path"]
        content = safe_read(source_path)

        for match in reference_pattern.finditer(content):
            target_text = match.group("target").replace("\\", "/")
            target_name = Path(target_text).name.lower()
            resolved = data_name_lookup.get(target_name, [])

            references.append(
                {
                    "consumer_path": record["path"],
                    "referenced_text": target_text,
                    "matched_inventory_paths": " | ".join(sorted(resolved)),
                    "reference_status": (
                        "MATCHED"
                        if resolved
                        else "UNRESOLVED_OR_GENERATED"
                    ),
                }
            )

    unique = {
        (
            item["consumer_path"],
            item["referenced_text"],
            item["matched_inventory_paths"],
        ): item
        for item in references
    }

    return sorted(
        unique.values(),
        key=lambda item: (
            item["consumer_path"].lower(),
            item["referenced_text"].lower(),
        ),
    )


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            serialised = dict(row)
            for key, value in serialised.items():
                if isinstance(value, list):
                    serialised[key] = " | ".join(str(item) for item in value)
            writer.writerow(serialised)


def build_summary(
    records: list[dict[str, Any]],
    references: list[dict[str, str]],
) -> dict[str, Any]:
    category_counts = Counter()
    extension_counts = Counter()
    data_asset_counts = Counter()

    for record in records:
        extension_counts[record["extension"]] += 1

        for category in record["categories"]:
            category_counts[category] += 1

        if record["is_data_asset"]:
            data_asset_counts[record["extension"]] += 1

    category_examples: dict[str, list[str]] = {}

    for category in sorted(CATEGORY_PATTERNS):
        category_examples[category] = [
            record["path"]
            for record in records
            if category in record["categories"]
        ][:25]

    unresolved_references = [
        reference
        for reference in references
        if reference["reference_status"] != "MATCHED"
    ]

    return {
        "audit_name": "EDGEiQ Performance Intelligence Phase 0 Repository Inventory",
        "generated_utc": utc_now(),
        "repository_root": str(ROOT),
        "files_scanned_and_retained": len(records),
        "data_assets": sum(1 for item in records if item["is_data_asset"]),
        "scripts": sum(1 for item in records if item["is_script"]),
        "frontend_consumers": sum(
            1 for item in records if item["is_frontend"]
        ),
        "references_found": len(references),
        "unresolved_or_generated_references": len(unresolved_references),
        "extension_counts": dict(sorted(extension_counts.items())),
        "data_asset_extension_counts": dict(
            sorted(data_asset_counts.items())
        ),
        "category_counts": dict(sorted(category_counts.items())),
        "category_examples": category_examples,
        "audit_limitations": [
            "This is a read-only structural inventory.",
            "A file name or PASS audit does not prove canonical status.",
            "Large files may not have been content-scanned.",
            "Database and Parquet schemas are inventoried by file presence only in this first pass.",
            "Canonical, reusable and unsafe classifications require lineage inspection in the next audit stage.",
        ],
    }


def build_markdown(
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    references: list[dict[str, str]],
) -> str:
    lines: list[str] = []

    lines.append("# EDGEiQ Performance Intelligence")
    lines.append("## Phase 0 Repository Inventory")
    lines.append("")
    lines.append(f"Generated UTC: `{summary['generated_utc']}`")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(
        "This audit performs a read-only inventory of existing EDGEiQ assets "
        "relevant to results, sectionals, benchmarks, length conversion, "
        "historical performance, identities, quality, patterns and frontend consumers."
    )
    lines.append("")
    lines.append("It does not classify any asset as canonical.")
    lines.append("")
    lines.append("## Inventory totals")
    lines.append("")
    lines.append(
        f"- Relevant files retained: **{summary['files_scanned_and_retained']}**"
    )
    lines.append(f"- Data assets: **{summary['data_assets']}**")
    lines.append(f"- Scripts: **{summary['scripts']}**")
    lines.append(
        f"- Frontend or service consumers: **{summary['frontend_consumers']}**"
    )
    lines.append(f"- Data references found: **{summary['references_found']}**")
    lines.append(
        "- Unresolved or generated references: "
        f"**{summary['unresolved_or_generated_references']}**"
    )
    lines.append("")
    lines.append("## Category counts")
    lines.append("")
    lines.append("| Category | Files |")
    lines.append("|---|---:|")

    for category, count in summary["category_counts"].items():
        lines.append(f"| {category} | {count} |")

    lines.append("")
    lines.append("## Data asset extensions")
    lines.append("")
    lines.append("| Extension | Count |")
    lines.append("|---|---:|")

    for extension, count in summary["data_asset_extension_counts"].items():
        lines.append(f"| {extension} | {count} |")

    lines.append("")
    lines.append("## High-value assets by category")
    lines.append("")

    for category, paths in summary["category_examples"].items():
        lines.append(f"### {category}")
        lines.append("")

        if not paths:
            lines.append("_No matching assets identified in this pass._")
        else:
            for path in paths:
                lines.append(f"- `{path}`")

        lines.append("")

    lines.append("## Largest relevant data assets")
    lines.append("")
    lines.append("| Path | Size bytes | Categories |")
    lines.append("|---|---:|---|")

    data_assets = sorted(
        (record for record in records if record["is_data_asset"]),
        key=lambda item: item["size_bytes"],
        reverse=True,
    )[:50]

    for record in data_assets:
        categories = ", ".join(record["categories"])
        lines.append(
            f"| `{record['path']}` | {record['size_bytes']} | {categories} |"
        )

    lines.append("")
    lines.append("## First-pass limitations")
    lines.append("")

    for limitation in summary["audit_limitations"]:
        lines.append(f"- {limitation}")

    lines.append("")
    lines.append("## Next audit stage")
    lines.append("")
    lines.append(
        "Trace the actual inputs, transformations, outputs and consumers for the "
        "highest-value assets before making any canonical reuse decision."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    records = scan_files()
    references = extract_references(records)
    summary = build_summary(records, references)

    inventory_json = (
        INVENTORY_DIR
        / f"edgeiq_performance_intelligence_asset_inventory_{run_id}.json"
    )
    inventory_csv = (
        INVENTORY_DIR
        / f"edgeiq_performance_intelligence_asset_inventory_{run_id}.csv"
    )
    references_csv = (
        INVENTORY_DIR
        / f"edgeiq_performance_intelligence_data_references_{run_id}.csv"
    )
    summary_json = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase0_summary_{run_id}.json"
    )
    summary_md = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase0_report_{run_id}.md"
    )
    latest_summary = (
        AUDIT_DIR
        / "edgeiq_performance_intelligence_phase0_latest.json"
    )

    write_json(inventory_json, records)
    write_csv(inventory_csv, records)
    write_csv(references_csv, references)
    write_json(summary_json, summary)
    write_json(latest_summary, summary)
    summary_md.write_text(
        build_markdown(summary, records, references),
        encoding="utf-8",
    )

    print("EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE0_INVENTORY_PASS")
    print(f"REPOSITORY_ROOT={ROOT}")
    print(f"FILES_RETAINED={len(records)}")
    print(
        "DATA_ASSETS="
        f"{sum(1 for item in records if item['is_data_asset'])}"
    )
    print(f"REFERENCES_FOUND={len(references)}")
    print(f"INVENTORY_JSON={inventory_json}")
    print(f"INVENTORY_CSV={inventory_csv}")
    print(f"REFERENCES_CSV={references_csv}")
    print(f"SUMMARY_JSON={summary_json}")
    print(f"SUMMARY_MD={summary_md}")


if __name__ == "__main__":
    main()
