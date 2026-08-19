from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STEP_NAME = "STEP201 Repository Census V1.1 Audit"

EXPECTED_FILES = {
    "csv": "STEP201_REPOSITORY_CENSUS_V1_1.csv",
    "json": "STEP201_REPOSITORY_CENSUS_V1_1.json",
    "markdown": "STEP201_REPOSITORY_CENSUS_V1_1.md",
    "summary": "STEP201_DISCOVERY_SUMMARY_V1_1.md",
    "exclusions": "STEP201_EXCLUSION_LEDGER_V1_1.csv",
    "audit": "STEP201_AUDIT_V1_1.md",
}

REQUIRED_FIELDS = {
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
}

FORBIDDEN_ROOTS = {
    "_archive_pre_git_commit",
    "checkpoints",
    "outputs",
}

FORBIDDEN_PREFIXES = (
    "public/data/",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the refined STEP201 V1.1 census."
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Repository root.",
    )
    parser.add_argument(
        "--output-root",
        default="docs/performance-intelligence-discovery",
        help="STEP201 output directory.",
    )
    return parser.parse_args()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def duplicate_values(
    rows: list[dict[str, Any]],
    field: str,
) -> list[str]:
    counts = Counter(
        str(row.get(field, ""))
        for row in rows
        if str(row.get(field, ""))
    )
    return sorted(
        value
        for value, count in counts.items()
        if count > 1
    )


def normalise_path(value: str) -> str:
    return str(value or "").replace("\\", "/").lstrip("./")


def root_name(value: str) -> str:
    path = normalise_path(value)
    return path.split("/", 1)[0].lower() if path else ""


def write_audit(
    path: Path,
    status: str,
    metrics: dict[str, int],
    findings: list[str],
) -> None:
    lines = [
        f"# {STEP_NAME}",
        "",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- Overall status: **{status}**",
        "",
        "## Metrics",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]

    for key, value in metrics.items():
        lines.append(f"| {key} | {value:,} |")

    lines.extend(["", "## Findings", ""])

    if findings:
        for finding in findings:
            lines.append(f"- {finding}")
    else:
        lines.append("- No structural or scope audit failures detected.")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Unknown producer, consumer and lifecycle status values remain permitted",
            "forensic findings. Scope exclusions are governed separately through",
            "the V1.1 exclusion ledger.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    root = Path(args.repository_root).resolve()
    output_root = (root / args.output_root).resolve()

    paths = {
        key: output_root / filename
        for key, filename in EXPECTED_FILES.items()
    }

    structural_failures: list[str] = []
    findings: list[str] = []

    for key in ("csv", "json", "markdown", "summary", "exclusions"):
        if not paths[key].exists():
            structural_failures.append(
                f"Missing required V1.1 output: {paths[key]}"
            )

    if structural_failures:
        output_root.mkdir(parents=True, exist_ok=True)
        metrics = {
            "Missing required outputs": len(structural_failures),
            "Structural failures": len(structural_failures),
        }
        write_audit(
            paths["audit"],
            "FAIL",
            metrics,
            structural_failures,
        )
        for failure in structural_failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"CREATED: {paths['audit']}")
        print("AUDIT STATUS: FAIL")
        return 1

    csv_rows = load_csv(paths["csv"])
    json_payload = load_json(paths["json"])
    json_rows = json_payload.get("assets", [])
    exclusion_rows = load_csv(paths["exclusions"])

    if not csv_rows:
        structural_failures.append("V1.1 CSV contains zero assets.")

    if not isinstance(json_rows, list) or not json_rows:
        structural_failures.append("V1.1 JSON contains zero assets.")

    if len(csv_rows) != len(json_rows):
        structural_failures.append(
            "CSV and JSON retained counts differ: "
            f"CSV={len(csv_rows):,}, JSON={len(json_rows):,}."
        )

    if csv_rows:
        missing_fields = REQUIRED_FIELDS - set(csv_rows[0].keys())
        if missing_fields:
            structural_failures.append(
                "CSV missing required fields: "
                + ", ".join(sorted(missing_fields))
            )

    duplicate_ids = duplicate_values(csv_rows, "asset_id")
    duplicate_paths = duplicate_values(csv_rows, "repository_path")

    if duplicate_ids:
        structural_failures.append(
            f"Duplicate asset IDs detected: {len(duplicate_ids):,}."
        )

    if duplicate_paths:
        structural_failures.append(
            f"Duplicate repository paths detected: {len(duplicate_paths):,}."
        )

    missing_repository_assets: list[str] = []
    forbidden_root_rows: list[str] = []
    forbidden_prefix_rows: list[str] = []
    blank_reasons = 0

    for row in csv_rows:
        repository_path = normalise_path(
            row.get("repository_path", "")
        )

        if not repository_path:
            missing_repository_assets.append("<blank>")
        elif not (root / Path(repository_path)).exists():
            missing_repository_assets.append(repository_path)

        if root_name(repository_path) in FORBIDDEN_ROOTS:
            forbidden_root_rows.append(repository_path)

        lowered = repository_path.lower()
        if any(lowered.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            forbidden_prefix_rows.append(repository_path)

        if not row.get("inclusion_reason", "").strip():
            blank_reasons += 1

    if missing_repository_assets:
        structural_failures.append(
            "V1.1 references missing repository assets: "
            f"{len(missing_repository_assets):,}."
        )

    if forbidden_root_rows:
        structural_failures.append(
            "Forbidden generated/preserved roots remain in V1.1: "
            f"{len(forbidden_root_rows):,}."
        )

    if forbidden_prefix_rows:
        structural_failures.append(
            "Forbidden runtime path prefixes remain in V1.1: "
            f"{len(forbidden_prefix_rows):,}."
        )

    if blank_reasons:
        structural_failures.append(
            f"Assets missing inclusion reasons: {blank_reasons:,}."
        )

    input_count = int(json_payload.get("input_asset_count", 0))
    included_count = int(json_payload.get("included_asset_count", 0))
    excluded_count = int(json_payload.get("excluded_asset_count", 0))

    if included_count != len(csv_rows):
        structural_failures.append(
            "JSON included_asset_count does not match CSV rows."
        )

    if excluded_count != len(exclusion_rows):
        structural_failures.append(
            "JSON excluded_asset_count does not match exclusion ledger."
        )

    if input_count != included_count + excluded_count:
        structural_failures.append(
            "Input count does not equal included plus excluded counts."
        )

    unknown_statuses = sum(
        1
        for row in csv_rows
        if row.get("status") == "Unknown"
    )
    unresolved_dataset_producers = sum(
        1
        for row in csv_rows
        if row.get("asset_type") == "Dataset"
        and row.get("producer") == "Unknown"
    )
    unresolved_consumers = sum(
        1
        for row in csv_rows
        if row.get("consumers") == "Unknown"
    )

    duplicate_names = duplicate_values(csv_rows, "name")

    findings.extend(
        [
            f"Duplicate filenames across distinct paths: {len(duplicate_names):,}.",
            f"Unknown lifecycle statuses: {unknown_statuses:,}.",
            (
                "Datasets with unresolved producers: "
                f"{unresolved_dataset_producers:,}."
            ),
            f"Assets with unresolved consumers: {unresolved_consumers:,}.",
        ]
    )

    findings.extend(structural_failures)

    metrics = {
        "First-pass assets": input_count,
        "Canonical assets retained": len(csv_rows),
        "Assets excluded": len(exclusion_rows),
        "CSV assets": len(csv_rows),
        "JSON assets": len(json_rows),
        "Duplicate asset IDs": len(duplicate_ids),
        "Duplicate repository paths": len(duplicate_paths),
        "Duplicate filenames": len(duplicate_names),
        "Forbidden-root assets": len(forbidden_root_rows),
        "Forbidden-prefix assets": len(forbidden_prefix_rows),
        "Missing inclusion reasons": blank_reasons,
        "Missing repository assets": len(missing_repository_assets),
        "Unknown lifecycle statuses": unknown_statuses,
        "Datasets with unresolved producers": unresolved_dataset_producers,
        "Assets with unresolved consumers": unresolved_consumers,
        "Structural failures": len(structural_failures),
    }

    status = "PASS" if not structural_failures else "FAIL"

    write_audit(
        paths["audit"],
        status,
        metrics,
        findings,
    )

    print(f"STEP: {STEP_NAME}")
    print(f"FIRST-PASS ASSETS: {input_count:,}")
    print(f"CANONICAL ASSETS RETAINED: {len(csv_rows):,}")
    print(f"ASSETS EXCLUDED: {len(exclusion_rows):,}")
    print(f"DUPLICATE ASSET IDS: {len(duplicate_ids):,}")
    print(f"DUPLICATE PATHS: {len(duplicate_paths):,}")
    print(f"DUPLICATE FILENAMES: {len(duplicate_names):,}")
    print(f"FORBIDDEN-ROOT ASSETS: {len(forbidden_root_rows):,}")
    print(f"FORBIDDEN-PREFIX ASSETS: {len(forbidden_prefix_rows):,}")
    print(f"MISSING INCLUSION REASONS: {blank_reasons:,}")
    print(f"MISSING REPOSITORY ASSETS: {len(missing_repository_assets):,}")
    print(f"UNKNOWN STATUSES: {unknown_statuses:,}")
    print(
        "UNRESOLVED DATASET PRODUCERS: "
        f"{unresolved_dataset_producers:,}"
    )
    print(f"UNRESOLVED CONSUMERS: {unresolved_consumers:,}")
    print(f"STRUCTURAL FAILURES: {len(structural_failures):,}")
    print(f"CREATED: {paths['audit']}")
    print(f"AUDIT STATUS: {status}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
