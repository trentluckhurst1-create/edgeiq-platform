from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROGRAM_NAME = "EDGEIQ Performance Intelligence Discovery"
STEP_NAME = "STEP201 Repository Performance Intelligence Census"
SCHEMA_VERSION = "1.0.0"

OUTPUT_FILENAMES = {
    "csv": "STEP201_REPOSITORY_CENSUS.csv",
    "json": "STEP201_REPOSITORY_CENSUS.json",
    "markdown": "STEP201_REPOSITORY_CENSUS.md",
    "summary": "STEP201_DISCOVERY_SUMMARY.md",
}

SUPPORTED_EXTENSIONS = {
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".csv",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".sql",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".parquet",
    ".feather",
}

TEXT_EXTENSIONS = {
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".sql",
}

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".vite",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "venv",
    ".venv",
    "env",
}

KEYWORD_GROUPS = {
    "Performance Intelligence": (
        "performance intelligence",
        "performance_intelligence",
        "performance-intelligence",
        "performance fact",
        "performance_fact",
    ),
    "EPI": (
        "epi",
        "edgeiq performance index",
        "performance index",
    ),
    "Standard Time": (
        "standard time",
        "standard_time",
        "standard-time",
        "benchmark time",
        "benchmark_time",
    ),
    "Lengths v Standard": (
        "lengths v standard",
        "lengths vs standard",
        "lengths_v_standard",
        "lengths_vs_standard",
        "lvs",
    ),
    "Early Speed": (
        "early speed",
        "early_speed",
        "early-speed",
    ),
    "Late Speed": (
        "late speed",
        "late_speed",
        "late-speed",
    ),
    "Speed": (
        "speed rating",
        "speed_rating",
        "speed metric",
        "speed_metric",
        "sectional",
    ),
    "Pace": (
        "pace",
        "tempo",
    ),
    "Race Shape": (
        "race shape",
        "race_shape",
        "race-shape",
    ),
    "Suitability": (
        "suitability",
        "distance suitability",
        "track suitability",
        "going suitability",
    ),
    "Form Momentum": (
        "form momentum",
        "form_momentum",
        "momentum",
    ),
    "Ratings": (
        "rating",
        "ratings",
        "rated",
    ),
    "Benchmark": (
        "benchmark",
        "normalisation",
        "normalization",
        "normalised",
        "normalized",
    ),
    "Warehouse": (
        "warehouse",
        "fact table",
        "fact_table",
    ),
    "Identity": (
        "identity",
        "canonical horse",
        "horse code",
        "runner identity",
    ),
    "Lineage": (
        "lineage",
        "provenance",
        "source evidence",
    ),
    "Form": (
        "form guide",
        "form_guide",
        "recent form",
        "historical performance",
    ),
}

ASSET_FIELDS = [
    "asset_id",
    "asset_type",
    "name",
    "repository_path",
    "extension",
    "domain",
    "matched_keywords",
    "producer",
    "consumers",
    "status",
    "size_bytes",
    "modified_utc",
    "content_scanned",
    "notes",
]

DATASET_EXTENSIONS = {
    ".csv",
    ".json",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".parquet",
    ".feather",
}

SOURCE_EXTENSIONS = {
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".sql",
}

OUTPUT_REFERENCE_PATTERN = re.compile(
    r"""(?P<quote>["'])(?P<path>[^"'\\n\\r]+?\.(?:csv|json|sqlite3?|db|parquet|feather))(?P=quote)""",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the governed STEP201 repository census."
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Repository root. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--output-root",
        default="docs/performance-intelligence-discovery",
        help="Directory for governed STEP201 outputs.",
    )
    parser.add_argument(
        "--max-text-bytes",
        type=int,
        default=2_000_000,
        help="Maximum bytes read from an individual text file.",
    )
    return parser.parse_args()


def normalise_relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def stable_asset_id(repository_path: str) -> str:
    digest = hashlib.sha256(repository_path.lower().encode("utf-8")).hexdigest()
    return f"STEP201-{digest[:16].upper()}"


def should_exclude(path: Path, root: Path, output_root: Path) -> bool:
    try:
        relative_parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        return True

    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_parts):
        return True

    try:
        path.resolve().relative_to(output_root.resolve())
        return True
    except ValueError:
        return False


def iter_candidate_files(root: Path, output_root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if should_exclude(path, root, output_root):
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        yield path


def read_text_sample(path: Path, max_bytes: int) -> tuple[str, bool, str]:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return "", False, "Binary or structured dataset; content not scanned."

    try:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
        truncated = len(raw) > max_bytes
        raw = raw[:max_bytes]
        text = raw.decode("utf-8", errors="replace")
        note = "Text scanned."
        if truncated:
            note = f"Text scan truncated at {max_bytes:,} bytes."
        return text, True, note
    except OSError as exc:
        return "", False, f"Content scan failed: {exc}"


def keyword_matches(search_text: str) -> dict[str, list[str]]:
    lowered = search_text.lower()
    matches: dict[str, list[str]] = {}

    for domain, keywords in KEYWORD_GROUPS.items():
        found = sorted({keyword for keyword in keywords if keyword in lowered})
        if found:
            matches[domain] = found

    return matches


def classify_asset_type(path: Path) -> str:
    name = path.name.lower()
    stem = path.stem.lower()
    extension = path.suffix.lower()
    path_text = path.as_posix().lower()

    if extension in DATASET_EXTENSIONS:
        return "Dataset"

    if "audit" in stem or stem.startswith("check_") or "/audit" in path_text:
        return "Audit"

    if any(token in stem for token in ("contract", "schema")):
        return "Contract"

    if extension == ".md":
        if any(token in stem for token in ("spec", "architecture", "handover", "design")):
            return "Specification"
        return "Documentation"

    if extension in SOURCE_EXTENSIONS:
        if any(
            token in stem
            for token in (
                "build",
                "builder",
                "apply",
                "run_",
                "generate",
                "materialise",
                "materialize",
                "calculate",
                "compute",
            )
        ):
            return "Builder"
        if any(token in name for token in ("test", "validate", "validation")):
            return "Validation"
        return "Source"

    return "Other"


def derive_status(path: Path, text: str) -> str:
    combined = f"{path.as_posix()} {text[:100_000]}".lower()

    if any(token in combined for token in ("deprecated", "obsolete", "retired")):
        return "Legacy"

    if any(
        token in combined
        for token in (
            "/archive/",
            "/archived/",
            "/legacy/",
            "_legacy",
            "-legacy",
            ".bak",
            "_old",
        )
    ):
        return "Legacy"

    if any(
        token in combined
        for token in (
            "canonical",
            "current",
            "production",
            "governed",
            "active",
        )
    ):
        return "Active"

    return "Unknown"


def extract_dataset_references(text: str) -> list[str]:
    references: list[str] = []

    for match in OUTPUT_REFERENCE_PATTERN.finditer(text):
        candidate = match.group("path").replace("\\\\", "/").replace("\\", "/")
        candidate = re.sub(r"/+", "/", candidate)
        references.append(candidate)

    return sorted(set(references))


def reference_name(reference: str) -> str:
    return Path(reference).name.lower()


def infer_producers_and_consumers(
    assets: list[dict[str, Any]],
    source_references: dict[str, list[str]],
) -> None:
    datasets_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for asset in assets:
        if asset["asset_type"] == "Dataset":
            datasets_by_name[asset["name"].lower()].append(asset)

    producers_by_dataset_id: dict[str, set[str]] = defaultdict(set)
    consumers_by_dataset_id: dict[str, set[str]] = defaultdict(set)

    write_context_patterns = (
        "to_csv",
        "to_json",
        "to_parquet",
        "sqlite3.connect",
        "write_text",
        "write_bytes",
        "open(",
        "csv.writer",
        "json.dump",
    )

    read_context_patterns = (
        "read_csv",
        "read_json",
        "read_parquet",
        "sqlite3.connect",
        "open(",
        "json.load",
        "csv.reader",
    )

    assets_by_path = {asset["repository_path"]: asset for asset in assets}

    for source_path, references in source_references.items():
        source_asset = assets_by_path.get(source_path)
        if not source_asset:
            continue

        source_text_lower = source_asset.pop("_text_for_relationships", "").lower()

        for reference in references:
            ref_name = reference_name(reference)
            matching_datasets = datasets_by_name.get(ref_name, [])

            if not matching_datasets:
                continue

            occurrence_indexes = [
                match.start()
                for match in re.finditer(re.escape(ref_name), source_text_lower)
            ]

            context = ""
            if occurrence_indexes:
                fragments = []
                for index in occurrence_indexes[:20]:
                    start = max(0, index - 180)
                    end = min(len(source_text_lower), index + len(ref_name) + 180)
                    fragments.append(source_text_lower[start:end])
                context = "\n".join(fragments)

            likely_write = any(pattern in context for pattern in write_context_patterns)
            likely_read = any(pattern in context for pattern in read_context_patterns)

            source_label = source_asset["repository_path"]

            for dataset_asset in matching_datasets:
                dataset_id = dataset_asset["asset_id"]

                if source_asset["asset_type"] == "Builder" and likely_write:
                    producers_by_dataset_id[dataset_id].add(source_label)

                if likely_read or not likely_write:
                    consumers_by_dataset_id[dataset_id].add(source_label)

    for asset in assets:
        asset_id = asset["asset_id"]

        if asset["asset_type"] == "Dataset":
            producers = sorted(producers_by_dataset_id.get(asset_id, set()))
            consumers = sorted(consumers_by_dataset_id.get(asset_id, set()))

            asset["producer"] = "; ".join(producers) if producers else "Unknown"
            asset["consumers"] = "; ".join(consumers) if consumers else "Unknown"
        else:
            own_references = source_references.get(asset["repository_path"], [])
            produced_names: list[str] = []
            consumed_names: list[str] = []

            for reference in own_references:
                ref_name = reference_name(reference)
                for dataset_asset in datasets_by_name.get(ref_name, []):
                    if asset["repository_path"] in producers_by_dataset_id.get(
                        dataset_asset["asset_id"], set()
                    ):
                        produced_names.append(dataset_asset["repository_path"])

                    if asset["repository_path"] in consumers_by_dataset_id.get(
                        dataset_asset["asset_id"], set()
                    ):
                        consumed_names.append(dataset_asset["repository_path"])

            asset["producer"] = "N/A"
            asset["consumers"] = (
                "; ".join(sorted(set(consumed_names)))
                if consumed_names
                else "Unknown"
            )

            if produced_names:
                produced_text = "; ".join(sorted(set(produced_names)))
                asset["notes"] = (
                    f"{asset['notes']} Inferred outputs: {produced_text}"
                ).strip()


def determine_relevance(
    path: Path,
    text: str,
    matches: dict[str, list[str]],
) -> bool:
    path_lower = path.as_posix().lower()

    if matches:
        return True

    strong_path_tokens = (
        "performance-intelligence",
        "performance_intelligence",
        "standard-time",
        "standard_time",
        "lengths-v-standard",
        "lengths_v_standard",
        "race-shape",
        "race_shape",
        "form-momentum",
        "form_momentum",
        "suitability",
        "benchmark",
        "epi",
    )

    return any(token in path_lower for token in strong_path_tokens)


def build_asset_record(
    path: Path,
    root: Path,
    max_text_bytes: int,
) -> tuple[dict[str, Any] | None, list[str]]:
    repository_path = normalise_relative_path(path, root)
    text, content_scanned, scan_note = read_text_sample(path, max_text_bytes)
    search_text = f"{repository_path}\n{text}"
    matches = keyword_matches(search_text)

    if not determine_relevance(path, text, matches):
        return None, []

    stat = path.stat()
    domains = sorted(matches.keys())
    matched_keywords = sorted(
        {keyword for values in matches.values() for keyword in values}
    )
    references = extract_dataset_references(text)

    notes = scan_note
    if not domains:
        notes = f"{notes} Included by repository-path relevance."

    record: dict[str, Any] = {
        "asset_id": stable_asset_id(repository_path),
        "asset_type": classify_asset_type(path),
        "name": path.name,
        "repository_path": repository_path,
        "extension": path.suffix.lower(),
        "domain": "; ".join(domains) if domains else "Unknown",
        "matched_keywords": "; ".join(matched_keywords),
        "producer": "Unknown",
        "consumers": "Unknown",
        "status": derive_status(path, text),
        "size_bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat(),
        "content_scanned": content_scanned,
        "notes": notes,
        "_text_for_relationships": text,
    }

    return record, references


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_csv(path: Path, assets: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ASSET_FIELDS)
        writer.writeheader()
        for asset in assets:
            writer.writerow({field: asset.get(field, "") for field in ASSET_FIELDS})


def write_json(
    path: Path,
    assets: list[dict[str, Any]],
    root: Path,
) -> None:
    payload = {
        "program": PROGRAM_NAME,
        "step": STEP_NAME,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(root.resolve()),
        "asset_count": len(assets),
        "assets": [
            {field: asset.get(field, "") for field in ASSET_FIELDS}
            for asset in assets
        ],
    }

    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_markdown(path: Path, assets: list[dict[str, Any]]) -> None:
    lines = [
        f"# {STEP_NAME}",
        "",
        f"- Program: {PROGRAM_NAME}",
        f"- Schema version: {SCHEMA_VERSION}",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- Assets catalogued: {len(assets):,}",
        "",
        "## Repository Census",
        "",
        "| Asset ID | Type | Repository Path | Domain | Status | Producer | Consumers |",
        "|---|---|---|---|---|---|---|",
    ]

    for asset in assets:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(asset["asset_id"]),
                    markdown_escape(asset["asset_type"]),
                    markdown_escape(asset["repository_path"]),
                    markdown_escape(asset["domain"]),
                    markdown_escape(asset["status"]),
                    markdown_escape(asset["producer"]),
                    markdown_escape(asset["consumers"]),
                ]
            )
            + " |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(path: Path, assets: list[dict[str, Any]]) -> None:
    by_type = Counter(asset["asset_type"] for asset in assets)
    by_status = Counter(asset["status"] for asset in assets)
    by_domain: Counter[str] = Counter()

    for asset in assets:
        for domain in str(asset["domain"]).split("; "):
            by_domain[domain or "Unknown"] += 1

    unknown_producers = sum(
        1
        for asset in assets
        if asset["asset_type"] == "Dataset" and asset["producer"] == "Unknown"
    )
    unknown_consumers = sum(
        1
        for asset in assets
        if asset["consumers"] == "Unknown"
    )

    lines = [
        f"# {STEP_NAME} ? Discovery Summary",
        "",
        "## Result",
        "",
        "The repository census completed successfully.",
        "",
        "## Totals",
        "",
        f"- Assets catalogued: {len(assets):,}",
        f"- Dataset assets with unresolved producers: {unknown_producers:,}",
        f"- Assets with unresolved consumers: {unknown_consumers:,}",
        "",
        "Unknown relationships are discovery findings and are not treated as fabricated links.",
        "",
        "## Assets by Type",
        "",
        "| Asset Type | Count |",
        "|---|---:|",
    ]

    for key, value in sorted(by_type.items()):
        lines.append(f"| {markdown_escape(key)} | {value:,} |")

    lines.extend(
        [
            "",
            "## Assets by Status",
            "",
            "| Status | Count |",
            "|---|---:|",
        ]
    )

    for key, value in sorted(by_status.items()):
        lines.append(f"| {markdown_escape(key)} | {value:,} |")

    lines.extend(
        [
            "",
            "## Assets by Domain",
            "",
            "| Domain | Count |",
            "|---|---:|",
        ]
    )

    for key, value in sorted(by_domain.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {markdown_escape(key)} | {value:,} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.repository_root).resolve()
    output_root = (root / args.output_root).resolve()

    if not root.exists() or not root.is_dir():
        print(f"ERROR: Repository root does not exist: {root}", file=sys.stderr)
        return 2

    output_root.mkdir(parents=True, exist_ok=True)

    print(f"PROGRAM: {PROGRAM_NAME}")
    print(f"STEP: {STEP_NAME}")
    print(f"REPOSITORY ROOT: {root}")
    print(f"OUTPUT ROOT: {output_root}")
    print("SCANNING REPOSITORY...")

    assets: list[dict[str, Any]] = []
    source_references: dict[str, list[str]] = {}
    scanned_file_count = 0

    for path in iter_candidate_files(root, output_root):
        scanned_file_count += 1
        record, references = build_asset_record(path, root, args.max_text_bytes)

        if record is None:
            continue

        assets.append(record)
        source_references[record["repository_path"]] = references

    infer_producers_and_consumers(assets, source_references)

    for asset in assets:
        asset.pop("_text_for_relationships", None)

    assets.sort(
        key=lambda item: (
            item["asset_type"],
            item["domain"],
            item["repository_path"],
        )
    )

    csv_path = output_root / OUTPUT_FILENAMES["csv"]
    json_path = output_root / OUTPUT_FILENAMES["json"]
    markdown_path = output_root / OUTPUT_FILENAMES["markdown"]
    summary_path = output_root / OUTPUT_FILENAMES["summary"]

    write_csv(csv_path, assets)
    write_json(json_path, assets, root)
    write_markdown(markdown_path, assets)
    write_summary(summary_path, assets)

    print(f"FILES SCANNED: {scanned_file_count:,}")
    print(f"RELEVANT ASSETS: {len(assets):,}")
    print(f"CREATED: {csv_path}")
    print(f"CREATED: {json_path}")
    print(f"CREATED: {markdown_path}")
    print(f"CREATED: {summary_path}")
    print("BUILD STATUS: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
