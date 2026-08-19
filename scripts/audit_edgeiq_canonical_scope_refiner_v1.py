from __future__ import annotations

import csv
import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "canonical-scope-refiner-v1"

REFINED_REGISTRY_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_REFINED_V1.csv"
EXCLUSIONS_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_SCOPE_EXCLUSIONS_V1.csv"
RETAINED_FAILURES_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_SCOPE_RETAINED_PARSE_FAILURES_V1.csv"
SUMMARY_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_SCOPE_REFINER_SUMMARY_V1.json"
REPORT_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_SCOPE_REFINER_REPORT_V1.md"

REQUIRED = [
    REFINED_REGISTRY_PATH,
    EXCLUSIONS_PATH,
    RETAINED_FAILURES_PATH,
    SUMMARY_PATH,
    REPORT_PATH,
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fail(message: str) -> int:
    print("AUDIT_VERDICT=FAIL")
    print(f"AUDIT_FAILURE={message}")
    return 1


def main() -> int:
    for path in REQUIRED:
        if not path.exists():
            return fail(f"Missing output: {path}")
        if path.stat().st_size == 0:
            return fail(f"Empty output: {path}")

    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    refined = read_csv(REFINED_REGISTRY_PATH)
    exclusions = read_csv(EXCLUSIONS_PATH)
    retained = read_csv(RETAINED_FAILURES_PATH)

    if summary.get("verdict") != "PASS":
        return fail(f"Summary verdict is {summary.get('verdict')}")

    before = int(summary["canonical_builder_count_before"])
    after = int(summary["canonical_builder_count_after"])
    excluded = int(summary["canonical_scope_exclusion_count"])
    retained_count = int(summary["retained_canonical_parse_failure_count"])
    input_failures = int(summary["input_canonical_parse_failure_count"])

    actual_after = sum(
        1 for row in refined if row.get("classification", "").upper() == "CANONICAL"
    )
    if actual_after != after:
        return fail(f"Refined canonical count mismatch: csv={actual_after} summary={after}")

    if before - excluded != after:
        return fail("Before/exclusion/after counts do not reconcile")

    if len(exclusions) != excluded:
        return fail("Exclusion CSV count does not reconcile")

    if len(retained) != retained_count:
        return fail("Retained failure CSV count does not reconcile")

    if excluded + retained_count != input_failures:
        return fail("Failure population does not reconcile")

    exclusion_ids = {row["builder_id"] for row in exclusions}
    retained_ids = {row["builder_id"] for row in retained}
    if exclusion_ids & retained_ids:
        return fail("A builder appears in both exclusions and retained failures")

    refined_by_id = {row.get("builder_id", ""): row for row in refined}
    for builder_id in exclusion_ids:
        row = refined_by_id.get(builder_id)
        if not row:
            return fail(f"Excluded builder missing from refined registry: {builder_id}")
        if row.get("classification", "").upper() == "CANONICAL":
            return fail(f"Excluded builder remains canonical: {builder_id}")

    for builder_id in retained_ids:
        row = refined_by_id.get(builder_id)
        if not row:
            return fail(f"Retained builder missing from refined registry: {builder_id}")
        if row.get("classification", "").upper() != "CANONICAL":
            return fail(f"Retained builder no longer canonical: {builder_id}")

    report = REPORT_PATH.read_text(encoding="utf-8")
    for heading in [
        "# EDGEIQ Canonical Scope Refiner V1",
        "## Executive Summary",
        "## Scope Policy",
        "## Exclusions by Classification",
        "## Retained Failures by Classification",
        "## Governance Result",
    ]:
        if heading not in report:
            return fail(f"Report missing section: {heading}")

    print("EDGEIQ CANONICAL SCOPE REFINER V1 AUDIT")
    print("AUDIT_VERDICT=PASS")
    print(f"CANONICAL_BEFORE={before}")
    print(f"CANONICAL_AFTER={after}")
    print(f"SCOPE_EXCLUSIONS={excluded}")
    print(f"RETAINED_CANONICAL_FAILURES={retained_count}")
    print(
        "REFINED_CANONICAL_PARSE_HEALTH_PERCENT="
        f"{summary['estimated_refined_canonical_parse_health_percentage']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
