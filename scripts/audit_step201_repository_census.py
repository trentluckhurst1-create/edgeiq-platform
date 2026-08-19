from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STEP_NAME = "STEP201 Repository Performance Intelligence Census Audit"

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
    "notes",
}

EXPECTED_OUTPUTS = {
    "csv": "STEP201_REPOSITORY_CENSUS.csv",
    "json": "STEP201_REPOSITORY_CENSUS.json",
    "markdown": "STEP201_REPOSITORY_CENSUS.md",
    "summary": "STEP201_DISCOVERY_SUMMARY.md",
    "audit": "STEP201_AUDIT.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the governed STEP201 repository census."
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Repository root. Defaults to current working directory.",
    )
    parser.add_argument(
        "--output-root",
        default="docs/performance-intelligence-discovery",
        help="Directory containing STEP201 outputs.",
    )
    return parser.parse_args()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def duplicate_values(rows: list[dict[str, Any]], field: str) -> list[str]:
    values = [str(row.get(field, "")) for row in rows]
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if value and count > 1)


def write_audit(
    path: Path,
    status: str,
    findings: list[str],
    metrics: dict[str, int],
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
        lines.append("- No structural audit failures detected.")

    lines.extend(
        [
            "",
            "## Governance Interpretation",
            "",
            "Unknown producers, consumers, domains and statuses are permitted discovery findings.",
            "They must remain explicit and must not be replaced with assumptions.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.repository_root).resolve()
    output_root = (root / args.output_root).resolve()

    csv_path = output_root / EXPECTED_OUTPUTS["csv"]
    json_path = output_root / EXPECTED_OUTPUTS["json"]
    markdown_path = output_root / EXPECTED_OUTPUTS["markdown"]
    summary_path = output_root / EXPECTED_OUTPUTS["summary"]
    audit_path = output_root / EXPECTED_OUTPUTS["audit"]

    findings: list[str] = []
    structural_failures: list[str] = []

    print(f"STEP: {STEP_NAME}")
    print(f"OUTPUT ROOT: {output_root}")

    required_paths = [csv_path, json_path, markdown_path, summary_path]

    for path in required_paths:
        if not path.exists():
            structural_failures.append(f"Missing required output: {path}")

    if structural_failures:
        findings.extend(structural_failures)
        metrics = {
            "Required outputs missing": len(structural_failures),
        }
        output_root.mkdir(parents=True, exist_ok=True)
        write_audit(audit_path, "FAIL", findings, metrics)

        for finding in findings:
            print(f"FAIL: {finding}", file=sys.stderr)

        print(f"CREATED: {audit_path}")
        print("AUDIT STATUS: FAIL")
        return 1

    csv_rows = load_csv(csv_path)
    json_payload = load_json(json_path)
    json_rows = json_payload.get("assets", [])

    if not csv_rows:
        structural_failures.append("CSV census contains zero assets.")

    if not isinstance(json_rows, list) or not json_rows:
        structural_failures.append("JSON census contains zero assets.")

    if len(csv_rows) != len(json_rows):
        structural_failures.append(
            "CSV and JSON asset counts differ: "
            f"CSV={len(csv_rows):,}, JSON={len(json_rows):,}."
        )

    if csv_rows:
        csv_fields = set(csv_rows[0].keys())
        missing_fields = sorted(REQUIRED_FIELDS - csv_fields)
        if missing_fields:
            structural_failures.append(
                "CSV is missing required fields: " + ", ".join(missing_fields)
            )

    if json_rows:
        for index, row in enumerate(json_rows):
            missing = REQUIRED_FIELDS - set(row.keys())
            if missing:
                structural_failures.append(
                    f"JSON asset index {index} is missing fields: "
                    + ", ".join(sorted(missing))
                )
                break

    duplicate_asset_ids = duplicate_values(csv_rows, "asset_id")
    duplicate_paths = duplicate_values(csv_rows, "repository_path")
    duplicate_names = duplicate_values(csv_rows, "name")

    if duplicate_asset_ids:
        structural_failures.append(
            f"Duplicate asset IDs detected: {len(duplicate_asset_ids):,}."
        )

    if duplicate_paths:
        structural_failures.append(
            f"Duplicate repository paths detected: {len(duplicate_paths):,}."
        )

    invalid_paths = []
    for row in csv_rows:
        repository_path = row.get("repository_path", "")
        if not repository_path:
            invalid_paths.append("<blank>")
            continue

        candidate = root / Path(repository_path)
        if not candidate.exists():
            invalid_paths.append(repository_path)

    if invalid_paths:
        structural_failures.append(
            f"Census references missing repository assets: {len(invalid_paths):,}."
        )

    unknown_domains = sum(
        1 for row in csv_rows if row.get("domain", "") == "Unknown"
    )
    unknown_statuses = sum(
        1 for row in csv_rows if row.get("status", "") == "Unknown"
    )
    dataset_unknown_producers = sum(
        1
        for row in csv_rows
        if row.get("asset_type") == "Dataset"
        and row.get("producer") == "Unknown"
    )
    unknown_consumers = sum(
        1 for row in csv_rows if row.get("consumers") == "Unknown"
    )

    orphan_builders = sum(
        1
        for row in csv_rows
        if row.get("asset_type") == "Builder"
        and "Inferred outputs:" not in row.get("notes", "")
    )

    orphan_datasets = sum(
        1
        for row in csv_rows
        if row.get("asset_type") == "Dataset"
        and row.get("producer") == "Unknown"
        and row.get("consumers") == "Unknown"
    )

    if duplicate_names:
        findings.append(
            f"Duplicate file names across different paths: {len(duplicate_names):,}."
        )

    findings.extend(
        [
            f"Unknown domains requiring later classification: {unknown_domains:,}.",
            f"Unknown statuses requiring later classification: {unknown_statuses:,}.",
            f"Datasets with unresolved producers: {dataset_unknown_producers:,}.",
            f"Assets with unresolved consumers: {unknown_consumers:,}.",
            f"Builders without inferred outputs: {orphan_builders:,}.",
            f"Datasets with neither inferred producer nor consumer: {orphan_datasets:,}.",
        ]
    )

    findings.extend(structural_failures)

    metrics = {
        "CSV assets": len(csv_rows),
        "JSON assets": len(json_rows),
        "Duplicate asset IDs": len(duplicate_asset_ids),
        "Duplicate repository paths": len(duplicate_paths),
        "Duplicate file names": len(duplicate_names),
        "Unknown domains": unknown_domains,
        "Unknown statuses": unknown_statuses,
        "Datasets with unresolved producers": dataset_unknown_producers,
        "Assets with unresolved consumers": unknown_consumers,
        "Builders without inferred outputs": orphan_builders,
        "Fully orphaned datasets": orphan_datasets,
        "Missing referenced repository assets": len(invalid_paths),
        "Structural failures": len(structural_failures),
    }

    status = "PASS" if not structural_failures else "FAIL"
    write_audit(audit_path, status, findings, metrics)

    print(f"CSV ASSETS: {len(csv_rows):,}")
    print(f"JSON ASSETS: {len(json_rows):,}")
    print(f"DUPLICATE ASSET IDS: {len(duplicate_asset_ids):,}")
    print(f"DUPLICATE PATHS: {len(duplicate_paths):,}")
    print(f"DUPLICATE NAMES: {len(duplicate_names):,}")
    print(f"UNKNOWN DOMAINS: {unknown_domains:,}")
    print(f"UNKNOWN STATUSES: {unknown_statuses:,}")
    print(f"UNRESOLVED DATASET PRODUCERS: {dataset_unknown_producers:,}")
    print(f"UNRESOLVED CONSUMERS: {unknown_consumers:,}")
    print(f"ORPHAN BUILDERS: {orphan_builders:,}")
    print(f"ORPHAN DATASETS: {orphan_datasets:,}")
    print(f"CREATED: {audit_path}")
    print(f"AUDIT STATUS: {status}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
