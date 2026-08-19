from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/platform-registry-v1/product-feed-registry-v1"

REGISTRY = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_V1.csv"
DUPLICATES = OUT / "EDGEIQ_PRODUCT_FEED_DUPLICATE_OWNERSHIP_V1.csv"
UNOWNED = OUT / "EDGEIQ_PRODUCT_FEED_UNOWNED_PUBLIC_FILES_V1.csv"
OWNER_PROFILE = OUT / "EDGEIQ_PRODUCT_FEED_OWNER_PROFILE_V1.csv"
FORMAT_PROFILE = OUT / "EDGEIQ_PRODUCT_FEED_FORMAT_PROFILE_V1.csv"
SUMMARY = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_SUMMARY_V1.json"
REPORT = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_REPORT_V1.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fail(message: str) -> int:
    print("AUDIT_VERDICT=FAIL")
    print(f"AUDIT_FAILURE={message}")
    return 1


def main() -> int:
    required = [REGISTRY, DUPLICATES, UNOWNED, OWNER_PROFILE, FORMAT_PROFILE, SUMMARY, REPORT]
    for path in required:
        if not path.exists() or path.stat().st_size == 0:
            return fail(f"Missing or empty output: {path}")

    registry = read_csv(REGISTRY)
    duplicates = read_csv(DUPLICATES)
    unowned = read_csv(UNOWNED)
    owners = read_csv(OWNER_PROFILE)
    formats = read_csv(FORMAT_PROFILE)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    if summary.get("verdict") != "PASS":
        return fail(f"Builder verdict is {summary.get('verdict')}")
    if not registry:
        return fail("Product feed registry is empty")
    if int(summary["owned_feed_count"]) <= 0:
        return fail("No canonical feed owners were resolved")
    if len(registry) != int(summary["product_feed_count"]):
        return fail("Feed count mismatch")
    if len(duplicates) != int(summary["duplicate_ownership_feed_count"]):
        return fail("Duplicate ownership count mismatch")
    if len(unowned) != int(summary["unowned_materialised_feed_count"]):
        return fail("Unowned feed count mismatch")
    if len(owners) != int(summary["feed_owner_builder_count"]):
        return fail("Owner profile count mismatch")
    if sum(int(row["feed_count"]) for row in formats) != len(registry):
        return fail("Format profile does not reconcile")

    feed_ids = [row["feed_id"] for row in registry]
    feed_paths = [row["feed_path"].lower() for row in registry]
    if len(feed_ids) != len(set(feed_ids)):
        return fail("Duplicate feed IDs")
    if len(feed_paths) != len(set(feed_paths)):
        return fail("Duplicate feed paths")

    duplicate_paths = {row["feed_path"].lower() for row in duplicates}
    for row in registry:
        expected_duplicate = int(row["owner_count"]) > 1
        actual_duplicate = row["feed_path"].lower() in duplicate_paths
        if expected_duplicate != actual_duplicate:
            return fail(f"Duplicate ownership reconciliation failed: {row['feed_path']}")

    unowned_paths = {row["feed_path"].lower() for row in unowned}
    for row in registry:
        expected_unowned = row["file_exists"] == "true" and int(row["owner_count"]) == 0
        actual_unowned = row["feed_path"].lower() in unowned_paths
        if expected_unowned != actual_unowned:
            return fail(f"Unowned feed reconciliation failed: {row['feed_path']}")

    report = REPORT.read_text(encoding="utf-8")
    for heading in [
        "# EDGEIQ Product Feed Registry V1",
        "## Executive Summary",
        "## Governance Contract",
        "## Feed Categories",
        "## Governance Exceptions",
        "## Acceptance",
    ]:
        if heading not in report:
            return fail(f"Report missing section: {heading}")

    print("EDGEIQ PRODUCT FEED REGISTRY V1 AUDIT")
    print("AUDIT_VERDICT=PASS")
    print(f"PRODUCT_FEEDS={len(registry)}")
    print(f"OWNED_FEEDS={summary['owned_feed_count']}")
    print(f"UNOWNED_MATERIALISED_FEEDS={len(unowned)}")
    print(f"DUPLICATE_OWNERSHIP_FEEDS={len(duplicates)}")
    print(f"OWNERSHIP_COVERAGE_PERCENT={summary['ownership_coverage_percentage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
