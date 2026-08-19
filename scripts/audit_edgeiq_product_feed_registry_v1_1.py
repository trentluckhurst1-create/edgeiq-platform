from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/platform-registry-v1/product-feed-registry-v1-1"
REGISTRY = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_V1_1.csv"
EVIDENCE = OUT / "EDGEIQ_PRODUCT_FEED_OWNERSHIP_EVIDENCE_V1_1.csv"
AMBIGUOUS = OUT / "EDGEIQ_PRODUCT_FEED_AMBIGUOUS_OWNERSHIP_V1_1.csv"
UNOWNED = OUT / "EDGEIQ_PRODUCT_FEED_UNOWNED_PUBLIC_FILES_V1_1.csv"
SUMMARY = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_SUMMARY_V1_1.json"
REPORT = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_REPORT_V1_1.md"
SCHEMA = OUT / "EDGEIQ_PRODUCT_FEED_SOURCE_SCHEMA_PROFILE_V1_1.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fail(message: str) -> int:
    print("AUDIT_VERDICT=FAIL")
    print(f"AUDIT_FAILURE={message}")
    return 1


def main() -> int:
    for path in [REGISTRY, EVIDENCE, AMBIGUOUS, UNOWNED, SUMMARY, REPORT, SCHEMA]:
        if not path.exists() or path.stat().st_size == 0:
            return fail(f"Missing or empty output: {path}")

    registry = read_csv(REGISTRY)
    evidence = read_csv(EVIDENCE)
    unowned = read_csv(UNOWNED)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    if summary.get("verdict") != "PASS":
        return fail(f"Builder verdict is {summary.get('verdict')}")
    if not registry:
        return fail("Feed registry is empty")
    if not evidence:
        return fail("Ownership evidence is empty")
    if int(summary["owned_feed_count"]) <= 0:
        return fail("No feeds have ownership evidence")
    if len(registry) != int(summary["product_feed_count"]):
        return fail("Product feed count mismatch")
    if len(evidence) != int(summary["ownership_evidence_row_count"]):
        return fail("Ownership evidence count mismatch")
    if len(unowned) != int(summary["unowned_feed_count"]):
        return fail("Unowned feed count mismatch")

    paths = [row["feed_path"].lower() for row in registry]
    if len(paths) != len(set(paths)):
        return fail("Duplicate feed paths")

    registry_by_path = {row["feed_path"].lower(): row for row in registry}
    evidence_count_by_path: dict[str, int] = {}
    for row in evidence:
        key = row["feed_path"].lower()
        if key not in registry_by_path:
            return fail(f"Evidence references unknown feed: {row['feed_path']}")
        evidence_count_by_path[key] = evidence_count_by_path.get(key, 0) + 1

    unowned_paths = {row["feed_path"].lower() for row in unowned}
    for key, row in registry_by_path.items():
        owner_count = int(row["owner_count"])
        if owner_count != evidence_count_by_path.get(key, 0):
            return fail(f"Owner/evidence reconciliation failed: {row['feed_path']}")
        expected_unowned = owner_count == 0
        actual_unowned = key in unowned_paths
        if expected_unowned != actual_unowned:
            return fail(f"Unowned reconciliation failed: {row['feed_path']}")

    report = REPORT.read_text(encoding="utf-8")
    for heading in [
        "# EDGEIQ Product Feed Registry V1.1",
        "## Executive Summary",
        "## Correction from V1",
        "## Ambiguity Policy",
        "## Acceptance",
    ]:
        if heading not in report:
            return fail(f"Report missing section: {heading}")

    print("EDGEIQ PRODUCT FEED REGISTRY V1.1 AUDIT")
    print("AUDIT_VERDICT=PASS")
    print(f"PRODUCT_FEEDS={len(registry)}")
    print(f"OWNED_FEEDS={summary['owned_feed_count']}")
    print(f"UNOWNED_FEEDS={len(unowned)}")
    print(f"OWNERSHIP_EVIDENCE_ROWS={len(evidence)}")
    print(f"OWNERSHIP_COVERAGE_PERCENT={summary['ownership_coverage_percentage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
