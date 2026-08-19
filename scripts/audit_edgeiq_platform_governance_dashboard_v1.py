from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/platform-registry-v1/governance-dashboard-v1"

DASHBOARD = OUT / "EDGEIQ_PLATFORM_GOVERNANCE_DASHBOARD_V1.json"
SCORECARD = OUT / "EDGEIQ_PLATFORM_GOVERNANCE_SCORECARD_V1.csv"
EXCEPTIONS = OUT / "EDGEIQ_PLATFORM_GOVERNANCE_EXCEPTIONS_V1.csv"
REPORT = OUT / "EDGEIQ_PLATFORM_GOVERNANCE_DASHBOARD_V1.md"
MANIFEST = OUT / "EDGEIQ_PLATFORM_GOVERNANCE_INPUT_MANIFEST_V1.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fail(message: str) -> int:
    print("AUDIT_VERDICT=FAIL")
    print(f"AUDIT_FAILURE={message}")
    return 1


def main() -> int:
    for path in [DASHBOARD, SCORECARD, EXCEPTIONS, REPORT, MANIFEST]:
        if not path.exists() or path.stat().st_size == 0:
            return fail(f"Missing or empty output: {path}")

    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    scorecard = read_csv(SCORECARD)
    exceptions = read_csv(EXCEPTIONS)

    if dashboard.get("verdict") != "PASS":
        return fail(f"Dashboard verdict is {dashboard.get('verdict')}")
    if dashboard.get("platform_governance_status") not in {
        "PASS", "PASS_WITH_GOVERNANCE_ACTIONS"
    }:
        return fail("Unknown platform governance status")
    if not scorecard:
        return fail("Scorecard is empty")
    if not exceptions:
        return fail("Exceptions registry is empty")

    for name, item in manifest.get("inputs", {}).items():
        if not item.get("exists"):
            return fail(f"Manifest input missing: {name}")
        if int(item.get("size_bytes", 0)) <= 0:
            return fail(f"Manifest input empty: {name}")
        if item.get("source_verdict") != "PASS":
            return fail(f"Source unit did not PASS: {name}={item.get('source_verdict')}")

    headline = dashboard["headline"]
    coverage = dashboard["coverage"]

    if int(headline["canonical_builders"]) <= 0:
        return fail("Canonical builder headline is zero")
    if int(headline["resolved_dependency_edges"]) <= 0:
        return fail("Dependency graph headline is zero")
    if int(headline["product_feeds"]) <= 0:
        return fail("Product feed headline is zero")
    if int(headline["owned_product_feeds"]) <= 0:
        return fail("Owned product feed headline is zero")

    for name, value in coverage.items():
        number = float(value)
        if number < 0.0 or number > 100.0:
            return fail(f"Coverage out of range: {name}={number}")

    maturity = float(dashboard["governance_maturity_index"])
    if maturity < 0.0 or maturity > 100.0:
        return fail(f"Maturity index out of range: {maturity}")

    expected_high_domains = sum(
        1 for row in exceptions
        if row["severity"] == "HIGH" and int(row["count"]) > 0
    )
    if expected_high_domains != int(dashboard["high_severity_exception_domain_count"]):
        return fail("High-severity exception-domain count mismatch")

    report = REPORT.read_text(encoding="utf-8")
    for heading in [
        "# EDGEIQ Platform Governance Dashboard V1",
        "## Platform Status",
        "## Headline Metrics",
        "## Coverage",
        "## Priority Governance Actions",
        "## Completed Governance Units",
        "## Governance Boundary",
    ]:
        if heading not in report:
            return fail(f"Report missing section: {heading}")

    print("EDGEIQ PLATFORM GOVERNANCE DASHBOARD V1 AUDIT")
    print("AUDIT_VERDICT=PASS")
    print(f"PLATFORM_GOVERNANCE_STATUS={dashboard['platform_governance_status']}")
    print(f"GOVERNANCE_MATURITY_INDEX={dashboard['governance_maturity_index']}")
    print(f"SCORECARD_ROWS={len(scorecard)}")
    print(f"EXCEPTION_ROWS={len(exceptions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
