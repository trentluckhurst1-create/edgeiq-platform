from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROGRAM = "EDGEIQ Performance Intelligence Discovery"
STEP = "STEP201 Repository Performance Intelligence Census V1.2"
SCHEMA_VERSION = "1.2.0"

OUTPUT_FILES = {
    "csv": "STEP201_REPOSITORY_CENSUS_V1_2.csv",
    "json": "STEP201_REPOSITORY_CENSUS_V1_2.json",
    "markdown": "STEP201_REPOSITORY_CENSUS_V1_2.md",
    "summary": "STEP201_DISCOVERY_SUMMARY_V1_2.md",
    "exclusions": "STEP201_EXCLUSION_LEDGER_V1_2.csv",
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
    "scope_shape",
    "scope_signals",
    "exclusion_reason",
]

CANONICAL_ASSET_TYPES = {
    "Builder",
    "Contract",
    "Specification",
    "Source",
    "Validation",
}

CANONICAL_PREFIXES = (
    "config/performance-intelligence/",
    "contracts/performance-intelligence/",
    "scripts/performance-intelligence/",
)

ARCHITECTURE_DOC_PREFIXES = (
    "docs/performance-intelligence/architecture/",
    "docs/performance-intelligence/canonical-identities/",
    "docs/performance-intelligence/integration/",
    "docs/performance-intelligence/inventories/",
    "docs/performance-intelligence/live-performance-engine-v2/",
    "docs/performance-intelligence/live-projection/",
    "docs/performance-intelligence/race-entry/",
    "docs/performance-intelligence/race-entry-projection/",
    "docs/performance-intelligence/standard-time-investigation/",
    "docs/performance-intelligence/standard-time-recovery/",
    "docs/performance-intelligence/standard-times/",
    "docs/performance-intelligence/ui-integration/",
    "docs/performance-intelligence/workspace-feeds/",
)

EXCLUDED_PATH_TOKENS = (
    "/archive/",
    "/audits/",
    "/backup/",
    "/backups/",
    "/checkpoints/",
    "/evidence/",
    "/latest/",
    "/migration-backups/",
    "/prototypes/",
    "/reports/",
    "/run-logs/",
    "/runs/",
    "/snapshots/",
)

EXCLUDED_NAME_TOKENS = (
    "acceptance",
    "audit",
    "candidate",
    "checkpoint",
    "comparison",
    "coverage",
    "diagnostic",
    "evidence",
    "latest",
    "manifest",
    "profile",
    "report",
    "result",
    "run_log",
    "run-log",
    "snapshot",
    "summary",
)

DOCUMENT_EXTENSIONS = {".md", ".txt"}

ARCHITECTURE_NAME_TOKENS = (
    "architecture",
    "contract",
    "design",
    "governance",
    "implementation",
    "inventory",
    "model",
    "policy",
    "registry",
    "schema",
    "spec",
    "specification",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Finalise the STEP201 canonical repository census."
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--input-profile",
        default=(
            "docs/performance-intelligence-discovery/"
            "STEP201_CANONICAL_SCOPE_PROFILE_V1_1.csv"
        ),
    )
    parser.add_argument(
        "--output-root",
        default="docs/performance-intelligence-discovery",
    )
    return parser.parse_args()


def normalise(value: str) -> str:
    return str(value or "").replace("\\", "/").lstrip("./")


def has_excluded_path_token(path_text: str) -> str | None:
    padded = f"/{normalise(path_text).lower()}/"

    for token in EXCLUDED_PATH_TOKENS:
        if token in padded:
            return token.strip("/")

    return None


def has_excluded_name_token(name: str) -> str | None:
    lowered = str(name or "").lower()

    for token in EXCLUDED_NAME_TOKENS:
        if token in lowered:
            return token

    return None


def is_architecture_document(row: dict[str, str]) -> bool:
    path_text = normalise(row.get("repository_path", "")).lower()
    extension = row.get("extension", "").lower()
    name = row.get("name", "").lower()

    if extension not in DOCUMENT_EXTENSIONS:
        return False

    if any(path_text.startswith(prefix) for prefix in ARCHITECTURE_DOC_PREFIXES):
        if any(token in name for token in EXCLUDED_NAME_TOKENS):
            return False
        return True

    return any(token in name for token in ARCHITECTURE_NAME_TOKENS)


def classify(row: dict[str, str]) -> tuple[bool, str]:
    path_text = normalise(row.get("repository_path", ""))
    lowered_path = path_text.lower()
    asset_type = row.get("asset_type", "Unknown")
    extension = row.get("extension", "").lower()
    scope_shape = row.get("scope_shape", "UNRESOLVED")

    excluded_path = has_excluded_path_token(path_text)
    if excluded_path:
        return False, f"generated or preserved path token: {excluded_path}"

    excluded_name = has_excluded_name_token(row.get("name", ""))
    if excluded_name and asset_type not in {"Builder", "Validation"}:
        return False, f"generated or evidence filename token: {excluded_name}"

    if lowered_path.startswith("docs/full-product-implementation/checkpoints/"):
        return False, "full-product implementation checkpoint artefact"

    if lowered_path.startswith("docs/full-product-implementation/screenshots/"):
        return False, "browser screenshot evidence"

    if asset_type == "Dataset":
        return False, "dataset excluded from canonical repository asset census"

    if scope_shape in {
        "LIKELY_GENERATED",
        "DOC_TREE_DATASET",
        "STRUCTURED_OR_EVIDENCE",
    }:
        return False, f"scope profile classification: {scope_shape}"

    if any(lowered_path.startswith(prefix) for prefix in CANONICAL_PREFIXES):
        return True, "canonical Performance Intelligence source path"

    if asset_type in CANONICAL_ASSET_TYPES:
        return True, f"canonical repository asset type: {asset_type}"

    if is_architecture_document(row):
        return True, "governed architecture or specification document"

    if (
        asset_type == "Documentation"
        and extension in DOCUMENT_EXTENSIONS
        and scope_shape == "LIKELY_SOURCE"
    ):
        return True, "source-oriented Performance Intelligence documentation"

    return False, "not required in final canonical source census"


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def serialise(row: dict[str, str]) -> dict[str, Any]:
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


def main() -> int:
    args = parse_args()

    root = Path(args.repository_root).resolve()
    input_path = (root / args.input_profile).resolve()
    output_root = (root / args.output_root).resolve()

    if not input_path.exists():
        print(f"ERROR: Input profile not found: {input_path}", file=sys.stderr)
        return 2

    output_root.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        print("ERROR: Input profile contains zero rows.", file=sys.stderr)
        return 3

    included: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []

    for source_row in rows:
        row = dict(source_row)
        retain, reason = classify(row)

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
                    "scope_shape": row.get("scope_shape", ""),
                    "scope_signals": row.get("scope_signals", ""),
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

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(
            {field: row.get(field, "") for field in OUTPUT_FIELDS}
            for row in included
        )

    with exclusion_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXCLUSION_FIELDS)
        writer.writeheader()
        writer.writerows(excluded)

    payload = {
        "program": PROGRAM,
        "step": STEP,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(root),
        "input_asset_count": len(rows),
        "included_asset_count": len(included),
        "excluded_asset_count": len(excluded),
        "assets": [serialise(row) for row in included],
    }

    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    markdown_lines = [
        f"# {STEP}",
        "",
        f"- Program: {PROGRAM}",
        f"- Schema version: {SCHEMA_VERSION}",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- V1.1 assets reviewed: {len(rows):,}",
        f"- Final canonical assets retained: {len(included):,}",
        f"- V1.2 exclusions: {len(excluded):,}",
        "",
        "## Final Canonical Repository Census",
        "",
        "| Asset ID | Type | Repository Path | Domain | Status | Inclusion Reason |",
        "|---|---|---|---|---|---|",
    ]

    for row in included:
        markdown_lines.append(
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

    markdown_path.write_text(
        "\n".join(markdown_lines) + "\n",
        encoding="utf-8",
    )

    type_counts = Counter(
        row.get("asset_type", "Unknown") for row in included
    )
    root_counts = Counter(
        normalise(row.get("repository_path", "")).split("/", 1)[0]
        for row in included
    )
    inclusion_counts = Counter(
        row.get("inclusion_reason", "Unknown") for row in included
    )
    exclusion_counts = Counter(
        row.get("exclusion_reason", "Unknown") for row in excluded
    )

    summary_lines = [
        f"# {STEP} ? Final Discovery Summary",
        "",
        "## Result",
        "",
        "STEP201 has been reduced to canonical repository-source scope.",
        "",
        f"- V1.1 assets reviewed: {len(rows):,}",
        f"- Final canonical assets retained: {len(included):,}",
        f"- Assets excluded from final canonical scope: {len(excluded):,}",
        "",
        "Datasets, generated reports, checkpoints, audit outputs, run logs,",
        "snapshots and evidence artefacts remain preserved in the earlier",
        "forensic census and exclusion ledgers.",
        "",
        "## Final Assets by Type",
        "",
        "| Asset Type | Count |",
        "|---|---:|",
    ]

    for key, value in type_counts.most_common():
        summary_lines.append(f"| {markdown_escape(key)} | {value:,} |")

    summary_lines.extend(
        [
            "",
            "## Final Assets by Repository Root",
            "",
            "| Root | Count |",
            "|---|---:|",
        ]
    )

    for key, value in root_counts.most_common():
        summary_lines.append(f"| {markdown_escape(key)} | {value:,} |")

    summary_lines.extend(
        [
            "",
            "## Inclusion Reasons",
            "",
            "| Reason | Count |",
            "|---|---:|",
        ]
    )

    for key, value in inclusion_counts.most_common():
        summary_lines.append(f"| {markdown_escape(key)} | {value:,} |")

    summary_lines.extend(
        [
            "",
            "## Top Exclusion Reasons",
            "",
            "| Reason | Count |",
            "|---|---:|",
        ]
    )

    for key, value in exclusion_counts.most_common(30):
        summary_lines.append(f"| {markdown_escape(key)} | {value:,} |")

    summary_path.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print(f"PROGRAM: {PROGRAM}")
    print(f"STEP: {STEP}")
    print(f"V1.1 ASSETS REVIEWED: {len(rows):,}")
    print(f"FINAL CANONICAL ASSETS: {len(included):,}")
    print(f"V1.2 EXCLUSIONS: {len(excluded):,}")
    print(f"CREATED: {csv_path}")
    print(f"CREATED: {json_path}")
    print(f"CREATED: {markdown_path}")
    print(f"CREATED: {summary_path}")
    print(f"CREATED: {exclusion_path}")
    print("FINALISATION STATUS: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
