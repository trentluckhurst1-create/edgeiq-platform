from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


STEP = "STEP201 Repository Census V1.2 Final Audit"

FILES = {
    "csv": "STEP201_REPOSITORY_CENSUS_V1_2.csv",
    "json": "STEP201_REPOSITORY_CENSUS_V1_2.json",
    "markdown": "STEP201_REPOSITORY_CENSUS_V1_2.md",
    "summary": "STEP201_DISCOVERY_SUMMARY_V1_2.md",
    "exclusions": "STEP201_EXCLUSION_LEDGER_V1_2.csv",
    "audit": "STEP201_AUDIT_V1_2.md",
}

FORBIDDEN_ASSET_TYPES = {"Dataset"}

FORBIDDEN_PATH_TOKENS = (
    "/archive/",
    "/audits/",
    "/backups/",
    "/checkpoints/",
    "/evidence/",
    "/migration-backups/",
    "/outputs/",
    "/prototypes/",
    "/run-logs/",
    "/runs/",
    "/snapshots/",
)

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--output-root",
        default="docs/performance-intelligence-discovery",
    )
    return parser.parse_args()


def normalise(value: str) -> str:
    return str(value or "").replace("\\", "/").lstrip("./")


def duplicates(rows: list[dict[str, str]], field: str) -> list[str]:
    counts = Counter(
        row.get(field, "")
        for row in rows
        if row.get(field, "")
    )
    return sorted(
        value for value, count in counts.items() if count > 1
    )


def write_audit(
    path: Path,
    status: str,
    metrics: dict[str, int],
    findings: list[str],
) -> None:
    lines = [
        f"# {STEP}",
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
        lines.append("- No final structural or scope failures detected.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    root = Path(args.repository_root).resolve()
    output_root = (root / args.output_root).resolve()
    paths = {
        key: output_root / filename
        for key, filename in FILES.items()
    }

    failures: list[str] = []

    for key in ("csv", "json", "markdown", "summary", "exclusions"):
        if not paths[key].exists():
            failures.append(f"Missing output: {paths[key]}")

    if failures:
        output_root.mkdir(parents=True, exist_ok=True)
        write_audit(
            paths["audit"],
            "FAIL",
            {
                "Missing outputs": len(failures),
                "Structural failures": len(failures),
            },
            failures,
        )
        print("AUDIT STATUS: FAIL")
        return 1

    with paths["csv"].open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        csv_rows = list(csv.DictReader(handle))

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    json_rows = payload.get("assets", [])

    with paths["exclusions"].open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        exclusion_rows = list(csv.DictReader(handle))

    if not csv_rows:
        failures.append("Final census contains zero rows.")

    if len(csv_rows) != len(json_rows):
        failures.append("CSV and JSON row counts differ.")

    if csv_rows:
        missing_fields = REQUIRED_FIELDS - set(csv_rows[0].keys())
        if missing_fields:
            failures.append(
                "Missing required fields: "
                + ", ".join(sorted(missing_fields))
            )

    duplicate_ids = duplicates(csv_rows, "asset_id")
    duplicate_paths = duplicates(csv_rows, "repository_path")
    duplicate_names = duplicates(csv_rows, "name")

    if duplicate_ids:
        failures.append(
            f"Duplicate asset IDs detected: {len(duplicate_ids):,}."
        )

    if duplicate_paths:
        failures.append(
            f"Duplicate paths detected: {len(duplicate_paths):,}."
        )

    missing_assets = []
    forbidden_type_rows = []
    forbidden_path_rows = []
    blank_inclusion_reasons = 0

    for row in csv_rows:
        path_text = normalise(row.get("repository_path", ""))
        padded = f"/{path_text.lower()}/"

        if not path_text or not (root / Path(path_text)).exists():
            missing_assets.append(path_text or "<blank>")

        if row.get("asset_type") in FORBIDDEN_ASSET_TYPES:
            forbidden_type_rows.append(path_text)

        if any(token in padded for token in FORBIDDEN_PATH_TOKENS):
            forbidden_path_rows.append(path_text)

        if not row.get("inclusion_reason", "").strip():
            blank_inclusion_reasons += 1

    if missing_assets:
        failures.append(
            f"Missing repository assets: {len(missing_assets):,}."
        )

    if forbidden_type_rows:
        failures.append(
            f"Dataset rows remain in final census: {len(forbidden_type_rows):,}."
        )

    if forbidden_path_rows:
        failures.append(
            f"Generated or preserved paths remain: {len(forbidden_path_rows):,}."
        )

    if blank_inclusion_reasons:
        failures.append(
            f"Blank inclusion reasons: {blank_inclusion_reasons:,}."
        )

    input_count = int(payload.get("input_asset_count", 0))
    included_count = int(payload.get("included_asset_count", 0))
    excluded_count = int(payload.get("excluded_asset_count", 0))

    if included_count != len(csv_rows):
        failures.append("JSON included count differs from CSV.")

    if excluded_count != len(exclusion_rows):
        failures.append("JSON excluded count differs from ledger.")

    if input_count != included_count + excluded_count:
        failures.append(
            "Input count does not equal included plus excluded."
        )

    unknown_statuses = sum(
        1 for row in csv_rows if row.get("status") == "Unknown"
    )
    unresolved_consumers = sum(
        1 for row in csv_rows if row.get("consumers") == "Unknown"
    )

    metrics = {
        "V1.1 assets reviewed": input_count,
        "Final canonical assets": len(csv_rows),
        "V1.2 exclusions": len(exclusion_rows),
        "CSV assets": len(csv_rows),
        "JSON assets": len(json_rows),
        "Duplicate asset IDs": len(duplicate_ids),
        "Duplicate paths": len(duplicate_paths),
        "Duplicate filenames": len(duplicate_names),
        "Dataset rows": len(forbidden_type_rows),
        "Generated/preserved path rows": len(forbidden_path_rows),
        "Missing repository assets": len(missing_assets),
        "Missing inclusion reasons": blank_inclusion_reasons,
        "Unknown lifecycle statuses": unknown_statuses,
        "Unresolved consumers": unresolved_consumers,
        "Structural failures": len(failures),
    }

    findings = [
        f"Duplicate filenames across distinct paths: {len(duplicate_names):,}.",
        f"Unknown lifecycle statuses: {unknown_statuses:,}.",
        f"Assets with unresolved consumers: {unresolved_consumers:,}.",
    ]
    findings.extend(failures)

    status = "PASS" if not failures else "FAIL"

    write_audit(
        paths["audit"],
        status,
        metrics,
        findings,
    )

    print(f"STEP: {STEP}")
    print(f"V1.1 ASSETS REVIEWED: {input_count:,}")
    print(f"FINAL CANONICAL ASSETS: {len(csv_rows):,}")
    print(f"V1.2 EXCLUSIONS: {len(exclusion_rows):,}")
    print(f"DUPLICATE ASSET IDS: {len(duplicate_ids):,}")
    print(f"DUPLICATE PATHS: {len(duplicate_paths):,}")
    print(f"DUPLICATE FILENAMES: {len(duplicate_names):,}")
    print(f"DATASET ROWS: {len(forbidden_type_rows):,}")
    print(
        "GENERATED/PRESERVED PATH ROWS: "
        f"{len(forbidden_path_rows):,}"
    )
    print(f"MISSING REPOSITORY ASSETS: {len(missing_assets):,}")
    print(f"MISSING INCLUSION REASONS: {blank_inclusion_reasons:,}")
    print(f"UNKNOWN STATUSES: {unknown_statuses:,}")
    print(f"UNRESOLVED CONSUMERS: {unresolved_consumers:,}")
    print(f"STRUCTURAL FAILURES: {len(failures):,}")
    print(f"CREATED: {paths['audit']}")
    print(f"AUDIT STATUS: {status}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
