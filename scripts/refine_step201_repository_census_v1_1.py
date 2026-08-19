from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROGRAM_NAME = "EDGEIQ Performance Intelligence Discovery"
STEP_NAME = "STEP201 Repository Performance Intelligence Census V1.1"
SCHEMA_VERSION = "1.1.0"

OUTPUT_FILES = {
    "csv": "STEP201_REPOSITORY_CENSUS_V1_1.csv",
    "json": "STEP201_REPOSITORY_CENSUS_V1_1.json",
    "markdown": "STEP201_REPOSITORY_CENSUS_V1_1.md",
    "summary": "STEP201_DISCOVERY_SUMMARY_V1_1.md",
    "exclusions": "STEP201_EXCLUSION_LEDGER_V1_1.csv",
}

OUTPUT_FIELDS = [
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
    "inclusion_reason",
    "notes",
]

EXCLUSION_FIELDS = [
    "asset_id",
    "asset_type",
    "name",
    "repository_path",
    "domain",
    "matched_keywords",
    "exclusion_reason",
]

HARD_EXCLUDED_ROOTS = {
    ".git",
    "_archive_pre_git_commit",
    "checkpoints",
    "coverage",
    "dist",
    "node_modules",
    "outputs",
}

HARD_EXCLUDED_PATH_PREFIXES = (
    "public/data/",
)

CANONICAL_PATH_PREFIXES = (
    "config/performance-intelligence/",
    "contracts/performance-intelligence/",
    "docs/performance-intelligence/",
    "scripts/performance-intelligence/",
)

CANONICAL_PATH_TOKENS = (
    "performance-intelligence",
    "performance_intelligence",
    "standard-time",
    "standard_time",
    "lengths-v-standard",
    "lengths_v_standard",
    "lengths-vs-standard",
    "lengths_vs_standard",
    "race-shape",
    "race_shape",
    "form-momentum",
    "form_momentum",
    "early-speed",
    "early_speed",
    "late-speed",
    "late_speed",
)

STRONG_KEYWORDS = {
    "benchmark time",
    "benchmark_time",
    "canonical horse",
    "distance suitability",
    "early speed",
    "early-speed",
    "early_speed",
    "edgeiq performance index",
    "form momentum",
    "form_momentum",
    "going suitability",
    "horse code",
    "late speed",
    "late-speed",
    "late_speed",
    "lengths v standard",
    "lengths vs standard",
    "lengths_v_standard",
    "lengths_vs_standard",
    "lvs",
    "performance fact",
    "performance intelligence",
    "performance_fact",
    "performance-intelligence",
    "performance_intelligence",
    "race shape",
    "race-shape",
    "race_shape",
    "runner identity",
    "standard time",
    "standard-time",
    "standard_time",
    "track suitability",
}

WEAK_KEYWORDS = {
    "benchmark",
    "fact table",
    "fact_table",
    "form guide",
    "form_guide",
    "historical performance",
    "identity",
    "lineage",
    "momentum",
    "normalisation",
    "normalised",
    "normalization",
    "normalized",
    "pace",
    "performance index",
    "provenance",
    "rated",
    "rating",
    "ratings",
    "recent form",
    "sectional",
    "source evidence",
    "suitability",
    "tempo",
    "warehouse",
}

GOVERNANCE_TYPES = {
    "Audit",
    "Builder",
    "Contract",
    "Documentation",
    "Source",
    "Specification",
    "Validation",
}

DATA_TYPES = {
    "Dataset",
}

ALLOWED_ROOTS_FOR_MULTI_SIGNAL = {
    "config",
    "contracts",
    "data",
    "docs",
    "scripts",
    "src",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refine the STEP201 first-pass census into canonical source scope."
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Repository root.",
    )
    parser.add_argument(
        "--input-census",
        default=(
            "docs/performance-intelligence-discovery/"
            "STEP201_REPOSITORY_CENSUS.csv"
        ),
        help="First-pass census CSV.",
    )
    parser.add_argument(
        "--output-root",
        default="docs/performance-intelligence-discovery",
        help="Governed output directory.",
    )
    return parser.parse_args()


def split_values(value: str) -> list[str]:
    return [
        item.strip()
        for item in str(value or "").split(";")
        if item.strip()
    ]


def normalise_path(value: str) -> str:
    return str(value or "").replace("\\", "/").lstrip("./")


def root_name(path_text: str) -> str:
    path = normalise_path(path_text)
    return path.split("/", 1)[0] if path else ""


def hard_exclusion_reason(path_text: str) -> str | None:
    path = normalise_path(path_text)
    lowered = path.lower()
    root = root_name(lowered)

    if root in HARD_EXCLUDED_ROOTS:
        return f"excluded generated or preserved root: {root}"

    for prefix in HARD_EXCLUDED_PATH_PREFIXES:
        if lowered.startswith(prefix):
            return f"excluded runtime/generated path prefix: {prefix}"

    if "/__pycache__/" in f"/{lowered}/":
        return "excluded Python cache"

    if lowered.endswith(".pyc"):
        return "excluded compiled Python artefact"

    return None


def classify_row(row: dict[str, str]) -> tuple[bool, str]:
    path = normalise_path(row.get("repository_path", ""))
    lowered_path = path.lower()
    asset_type = row.get("asset_type", "Unknown")
    root = root_name(lowered_path)

    keywords = {
        keyword.lower()
        for keyword in split_values(row.get("matched_keywords", ""))
    }

    domains = {
        domain.lower()
        for domain in split_values(row.get("domain", ""))
        if domain.lower() != "unknown"
    }

    exclusion = hard_exclusion_reason(path)
    if exclusion:
        return False, exclusion

    for prefix in CANONICAL_PATH_PREFIXES:
        if lowered_path.startswith(prefix):
            return True, f"canonical Performance Intelligence path: {prefix}"

    if any(token in lowered_path for token in CANONICAL_PATH_TOKENS):
        return True, "strong Performance Intelligence repository-path signal"

    strong_matches = sorted(keywords & STRONG_KEYWORDS)
    weak_matches = sorted(keywords & WEAK_KEYWORDS)

    if strong_matches:
        return True, "strong domain keyword: " + "; ".join(strong_matches)

    non_weak_keywords = sorted(keywords - WEAK_KEYWORDS)

    if (
        root in ALLOWED_ROOTS_FOR_MULTI_SIGNAL
        and asset_type in GOVERNANCE_TYPES
        and len(domains) >= 2
        and len(keywords) >= 2
        and non_weak_keywords
    ):
        return True, (
            "multi-domain governed source signal: "
            + "; ".join(sorted(domains))
        )

    if (
        root in ALLOWED_ROOTS_FOR_MULTI_SIGNAL
        and asset_type in DATA_TYPES
        and len(domains) >= 2
        and len(keywords) >= 3
        and non_weak_keywords
    ):
        return True, (
            "multi-domain dataset signal: "
            + "; ".join(sorted(domains))
        )

    if keywords and keywords.issubset(WEAK_KEYWORDS):
        return False, "weak generic keywords only: " + "; ".join(weak_matches)

    if len(keywords) == 1:
        return False, "single non-canonical keyword signal"

    if root not in ALLOWED_ROOTS_FOR_MULTI_SIGNAL:
        return False, f"repository root outside canonical source scope: {root}"

    return False, "insufficient canonical Performance Intelligence evidence"


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def serialisable_asset(row: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for field in OUTPUT_FIELDS:
        value: Any = row.get(field, "")

        if field == "size_bytes":
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = 0

        if field == "content_scanned":
            value = str(value).lower() in {"true", "1", "yes"}

        result[field] = value

    return result


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(
            {
                field: row.get(field, "")
                for field in OUTPUT_FIELDS
            }
            for row in rows
        )


def write_exclusions(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXCLUSION_FIELDS)
        writer.writeheader()
        writer.writerows(
            {
                field: row.get(field, "")
                for field in EXCLUSION_FIELDS
            }
            for row in rows
        )


def write_json(
    path: Path,
    included: list[dict[str, str]],
    input_count: int,
    exclusion_count: int,
    repository_root: Path,
) -> None:
    payload = {
        "program": PROGRAM_NAME,
        "step": STEP_NAME,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(repository_root),
        "input_asset_count": input_count,
        "included_asset_count": len(included),
        "excluded_asset_count": exclusion_count,
        "assets": [serialisable_asset(row) for row in included],
    }

    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_markdown(
    path: Path,
    included: list[dict[str, str]],
    input_count: int,
    exclusion_count: int,
) -> None:
    lines = [
        f"# {STEP_NAME}",
        "",
        f"- Program: {PROGRAM_NAME}",
        f"- Schema version: {SCHEMA_VERSION}",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- First-pass assets: {input_count:,}",
        f"- Canonical-source assets retained: {len(included):,}",
        f"- Assets excluded with evidence: {exclusion_count:,}",
        "",
        "## Canonical Repository Census",
        "",
        "| Asset ID | Type | Repository Path | Domain | Status | Inclusion Reason |",
        "|---|---|---|---|---|---|",
    ]

    for row in included:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(row.get("asset_id", "")),
                    markdown_escape(row.get("asset_type", "")),
                    markdown_escape(row.get("repository_path", "")),
                    markdown_escape(row.get("domain", "")),
                    markdown_escape(row.get("status", "")),
                    markdown_escape(row.get("inclusion_reason", "")),
                ]
            )
            + " |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(
    path: Path,
    included: list[dict[str, str]],
    excluded: list[dict[str, str]],
    input_count: int,
) -> None:
    type_counts = Counter(
        row.get("asset_type", "Unknown")
        for row in included
    )
    status_counts = Counter(
        row.get("status", "Unknown")
        for row in included
    )
    root_counts = Counter(
        root_name(row.get("repository_path", ""))
        for row in included
    )
    inclusion_counts = Counter(
        row.get("inclusion_reason", "Unknown")
        for row in included
    )
    exclusion_counts = Counter(
        row.get("exclusion_reason", "Unknown")
        for row in excluded
    )

    reduction = input_count - len(included)
    reduction_pct = (
        (reduction / input_count) * 100
        if input_count
        else 0.0
    )

    lines = [
        f"# {STEP_NAME} ? Discovery Summary",
        "",
        "## Result",
        "",
        "The first-pass census was refined into canonical repository-source scope.",
        "",
        f"- First-pass assets: {input_count:,}",
        f"- Canonical-source assets retained: {len(included):,}",
        f"- Assets excluded: {len(excluded):,}",
        f"- Scope reduction: {reduction:,} ({reduction_pct:.2f}%)",
        "",
        "Every exclusion is preserved in the exclusion ledger.",
        "",
        "## Retained Assets by Type",
        "",
        "| Asset Type | Count |",
        "|---|---:|",
    ]

    for key, value in type_counts.most_common():
        lines.append(f"| {markdown_escape(key)} | {value:,} |")

    lines.extend(
        [
            "",
            "## Retained Assets by Status",
            "",
            "| Status | Count |",
            "|---|---:|",
        ]
    )

    for key, value in status_counts.most_common():
        lines.append(f"| {markdown_escape(key)} | {value:,} |")

    lines.extend(
        [
            "",
            "## Retained Assets by Repository Root",
            "",
            "| Root | Count |",
            "|---|---:|",
        ]
    )

    for key, value in root_counts.most_common():
        lines.append(f"| {markdown_escape(key)} | {value:,} |")

    lines.extend(
        [
            "",
            "## Top Inclusion Reasons",
            "",
            "| Inclusion Reason | Count |",
            "|---|---:|",
        ]
    )

    for key, value in inclusion_counts.most_common(30):
        lines.append(f"| {markdown_escape(key)} | {value:,} |")

    lines.extend(
        [
            "",
            "## Top Exclusion Reasons",
            "",
            "| Exclusion Reason | Count |",
            "|---|---:|",
        ]
    )

    for key, value in exclusion_counts.most_common(30):
        lines.append(f"| {markdown_escape(key)} | {value:,} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    repository_root = Path(args.repository_root).resolve()
    input_path = (repository_root / args.input_census).resolve()
    output_root = (repository_root / args.output_root).resolve()

    if not input_path.exists():
        print(f"ERROR: Input census not found: {input_path}", file=sys.stderr)
        return 2

    output_root.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        input_rows = list(csv.DictReader(handle))

    if not input_rows:
        print("ERROR: First-pass census contains zero rows.", file=sys.stderr)
        return 3

    included: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []

    for original_row in input_rows:
        row = dict(original_row)
        retain, reason = classify_row(row)

        if retain:
            row["inclusion_reason"] = reason
            included.append(row)
        else:
            excluded.append(
                {
                    "asset_id": row.get("asset_id", ""),
                    "asset_type": row.get("asset_type", ""),
                    "name": row.get("name", ""),
                    "repository_path": row.get("repository_path", ""),
                    "domain": row.get("domain", ""),
                    "matched_keywords": row.get("matched_keywords", ""),
                    "exclusion_reason": reason,
                }
            )

    included.sort(
        key=lambda row: (
            row.get("asset_type", ""),
            row.get("domain", ""),
            row.get("repository_path", ""),
        )
    )
    excluded.sort(
        key=lambda row: (
            row.get("exclusion_reason", ""),
            row.get("repository_path", ""),
        )
    )

    csv_path = output_root / OUTPUT_FILES["csv"]
    json_path = output_root / OUTPUT_FILES["json"]
    markdown_path = output_root / OUTPUT_FILES["markdown"]
    summary_path = output_root / OUTPUT_FILES["summary"]
    exclusion_path = output_root / OUTPUT_FILES["exclusions"]

    write_csv(csv_path, included)
    write_json(
        json_path,
        included,
        len(input_rows),
        len(excluded),
        repository_root,
    )
    write_markdown(
        markdown_path,
        included,
        len(input_rows),
        len(excluded),
    )
    write_summary(
        summary_path,
        included,
        excluded,
        len(input_rows),
    )
    write_exclusions(exclusion_path, excluded)

    reduction = len(input_rows) - len(included)
    reduction_pct = (
        (reduction / len(input_rows)) * 100
        if input_rows
        else 0.0
    )

    print(f"PROGRAM: {PROGRAM_NAME}")
    print(f"STEP: {STEP_NAME}")
    print(f"FIRST-PASS ASSETS: {len(input_rows):,}")
    print(f"CANONICAL ASSETS RETAINED: {len(included):,}")
    print(f"ASSETS EXCLUDED: {len(excluded):,}")
    print(f"SCOPE REDUCTION: {reduction:,} ({reduction_pct:.2f}%)")
    print(f"CREATED: {csv_path}")
    print(f"CREATED: {json_path}")
    print(f"CREATED: {markdown_path}")
    print(f"CREATED: {summary_path}")
    print(f"CREATED: {exclusion_path}")
    print("REFINEMENT STATUS: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
