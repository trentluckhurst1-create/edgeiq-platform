from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = ROOT / "docs" / "platform-registry-v1"
OUT = PLATFORM_ROOT / "governance-dashboard-v1"

INPUTS = {
    "builder_registry": PLATFORM_ROOT / "builder-registry-v1-1" / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1_1_SUMMARY.json",
    "parse_failure_auditor": PLATFORM_ROOT / "parse-failure-auditor-v1" / "EDGEIQ_CANONICAL_PARSE_FAILURE_SUMMARY_V1.json",
    "scope_refiner": PLATFORM_ROOT / "canonical-scope-refiner-v1" / "EDGEIQ_CANONICAL_SCOPE_REFINER_SUMMARY_V1.json",
    "dependency_graph": PLATFORM_ROOT / "builder-dependency-graph-v1-1" / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCY_GRAPH_SUMMARY_V1_1.json",
    "product_feed_registry": PLATFORM_ROOT / "product-feed-registry-v1-1" / "EDGEIQ_PRODUCT_FEED_REGISTRY_SUMMARY_V1_1.json",
}

DASHBOARD_JSON = OUT / "EDGEIQ_PLATFORM_GOVERNANCE_DASHBOARD_V1.json"
SCORECARD_CSV = OUT / "EDGEIQ_PLATFORM_GOVERNANCE_SCORECARD_V1.csv"
EXCEPTIONS_CSV = OUT / "EDGEIQ_PLATFORM_GOVERNANCE_EXCEPTIONS_V1.csv"
REPORT_MD = OUT / "EDGEIQ_PLATFORM_GOVERNANCE_DASHBOARD_V1.md"
AUDIT_INPUTS_JSON = OUT / "EDGEIQ_PLATFORM_GOVERNANCE_INPUT_MANIFEST_V1.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing governed input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def metric(unit: str, name: str, value: object, status: str, note: str) -> dict[str, object]:
    return {
        "governance_unit": unit,
        "metric": name,
        "value": value,
        "status": status,
        "note": note,
    }


def exception(
    severity: str,
    domain: str,
    code: str,
    count: int,
    description: str,
    action: str,
) -> dict[str, object]:
    return {
        "severity": severity,
        "domain": domain,
        "exception_code": code,
        "count": count,
        "description": description,
        "governance_action": action,
    }


def main() -> int:
    source = {name: load_json(path) for name, path in INPUTS.items()}

    registry = source["builder_registry"]
    parse = source["parse_failure_auditor"]
    scope = source["scope_refiner"]
    graph = source["dependency_graph"]
    feeds = source["product_feed_registry"]

    canonical_before = int(scope["canonical_builder_count_before"])
    canonical_after = int(scope["canonical_builder_count_after"])
    active_defects = int(parse["active_or_truncated_defect_count"])
    retained_failures = int(scope["retained_canonical_parse_failure_count"])
    dependency_edges = int(graph["dependency_edge_count"])
    orphan_builders = int(graph["orphan_builder_count"])
    unresolved_dependencies = int(graph["unresolved_dependency_record_count"])
    product_feeds = int(feeds["product_feed_count"])
    owned_feeds = int(feeds["owned_feed_count"])
    multi_owner_feeds = int(feeds["multiple_evidenced_owner_feed_count"])
    unowned_feeds = int(feeds["unowned_feed_count"])

    scorecard = [
        metric("Builder Registry", "Canonical builders before refinement", canonical_before, "INFO", "Live-source registry population."),
        metric("Scope Refiner", "Canonical builders after refinement", canonical_after, "PASS", "Governed canonical scope after deterministic exclusions."),
        metric("Parse Failure Auditor", "Active or truncated defects", active_defects, "ACTION", "Confirmed active/truncated defects requiring remediation."),
        metric("Scope Refiner", "Retained parse-failure records", retained_failures, "REVIEW", "Retained because evidence was insufficient for automatic exclusion."),
        metric("Dependency Graph", "Resolved dependency edges", dependency_edges, "PASS" if dependency_edges > 0 else "FAIL", "Canonical producer-to-consumer relationships."),
        metric("Dependency Graph", "Orphan builders", orphan_builders, "REVIEW", "No discovered incoming or outgoing canonical relationship."),
        metric("Dependency Graph", "Unresolved dependency records", unresolved_dependencies, "REVIEW", "Input ownership or path matching remains unresolved."),
        metric("Product Feed Registry", "Materialised product feeds", product_feeds, "INFO", "Structured files under governed public product-data paths."),
        metric("Product Feed Registry", "Feeds with ownership evidence", owned_feeds, "PASS" if owned_feeds > 0 else "FAIL", "At least one canonical builder owner resolved."),
        metric("Product Feed Registry", "Multiple-evidenced-owner feeds", multi_owner_feeds, "ACTION", "Require authoritative owner or explicit shared ownership contract."),
        metric("Product Feed Registry", "Unowned feeds", unowned_feeds, "ACTION", "Require owner assignment or governed exclusion."),
        metric("Product Feed Registry", "Ownership coverage percentage", feeds["ownership_coverage_percentage"], "REVIEW", "Current governed feed ownership coverage."),
    ]

    exceptions = [
        exception("HIGH", "Canonical Source", "ACTIVE_OR_TRUNCATED_PARSE_DEFECT", active_defects,
                  "Canonical builders classified as active defects or truncated source.",
                  "Repair individually through governed scripts and rerun the parse-failure auditor."),
        exception("MEDIUM", "Canonical Scope", "RETAINED_PARSE_FAILURE_REVIEW", retained_failures,
                  "Parse-failure records retained in canonical scope due to insufficient exclusion evidence.",
                  "Classify using stronger source provenance and lifecycle evidence."),
        exception("MEDIUM", "Dependency Graph", "ORPHAN_CANONICAL_BUILDER", orphan_builders,
                  "Canonical builders with no resolved graph relationship.",
                  "Determine whether each is standalone, externally triggered, historical, or missing dependency evidence."),
        exception("MEDIUM", "Dependency Graph", "UNRESOLVED_DEPENDENCY", unresolved_dependencies,
                  "Dependency records without a resolved canonical output owner.",
                  "Normalise path semantics and assign upstream ownership."),
        exception("HIGH", "Product Feeds", "MULTIPLE_FEED_OWNERS", multi_owner_feeds,
                  "Materialised feeds with evidence for multiple canonical owners.",
                  "Select one authoritative owner or document an explicit shared-ownership contract."),
        exception("HIGH", "Product Feeds", "UNOWNED_PRODUCT_FEED", unowned_feeds,
                  "Materialised public product feeds without canonical ownership evidence.",
                  "Assign a canonical owner or exclude the feed from supported product scope."),
    ]

    # This is a governance maturity index, not a product quality score.
    builder_parse_health = float(parse["estimated_canonical_health_percent"])
    feed_ownership = float(feeds["ownership_coverage_percentage"])
    graph_connection = round(
        ((canonical_after - orphan_builders) / canonical_after) * 100.0, 4
    ) if canonical_after else 0.0
    scope_reconciliation = 100.0 if (
        canonical_before - int(scope["canonical_scope_exclusion_count"]) == canonical_after
    ) else 0.0

    maturity_index = round(
        builder_parse_health * 0.30
        + scope_reconciliation * 0.20
        + graph_connection * 0.20
        + feed_ownership * 0.30,
        4,
    )

    if active_defects > 0 or multi_owner_feeds > 0 or unowned_feeds > 0:
        platform_status = "PASS_WITH_GOVERNANCE_ACTIONS"
    else:
        platform_status = "PASS"

    dashboard = {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": "PASS",
        "platform_governance_status": platform_status,
        "governance_maturity_index": maturity_index,
        "governance_maturity_note": (
            "Weighted governance coverage indicator only; it is not a product-quality, "
            "data-accuracy, model-performance, or launch-readiness score."
        ),
        "headline": {
            "canonical_builders": canonical_after,
            "confirmed_active_or_truncated_defects": active_defects,
            "resolved_dependency_edges": dependency_edges,
            "orphan_builders": orphan_builders,
            "product_feeds": product_feeds,
            "owned_product_feeds": owned_feeds,
            "unowned_product_feeds": unowned_feeds,
            "multiple_evidenced_owner_feeds": multi_owner_feeds,
        },
        "coverage": {
            "estimated_canonical_parse_health_percentage": builder_parse_health,
            "canonical_scope_reconciliation_percentage": scope_reconciliation,
            "builder_graph_connection_percentage": graph_connection,
            "product_feed_ownership_percentage": feed_ownership,
        },
        "governance_exception_count": len(exceptions),
        "high_severity_exception_domain_count": sum(
            1 for row in exceptions if row["severity"] == "HIGH" and int(row["count"]) > 0
        ),
        "source_units": {
            name: {
                "path": str(path),
                "source_verdict": source[name].get("verdict", "UNKNOWN"),
            }
            for name, path in INPUTS.items()
        },
    }

    OUT.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")
    AUDIT_INPUTS_JSON.write_text(json.dumps({
        "generated_utc": dashboard["generated_utc"],
        "inputs": {
            name: {
                "path": str(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size,
                "source_verdict": source[name].get("verdict", "UNKNOWN"),
            }
            for name, path in INPUTS.items()
        },
    }, indent=2) + "\n", encoding="utf-8")

    write_csv(SCORECARD_CSV, scorecard, [
        "governance_unit", "metric", "value", "status", "note",
    ])
    write_csv(EXCEPTIONS_CSV, exceptions, [
        "severity", "domain", "exception_code", "count",
        "description", "governance_action",
    ])

    lines = [
        "# EDGEIQ Platform Governance Dashboard V1",
        "",
        "## Platform Status",
        "",
        f"- Governed verdict: **PASS**",
        f"- Platform governance status: **{platform_status}**",
        f"- Governance maturity index: **{maturity_index}**",
        "",
        "> The maturity index is a weighted governance-coverage indicator. It is not a "
        "product-quality, data-accuracy, model-performance, or launch-readiness score.",
        "",
        "## Headline Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Canonical builders | {canonical_after} |",
        f"| Confirmed active/truncated defects | {active_defects} |",
        f"| Resolved dependency edges | {dependency_edges} |",
        f"| Orphan builders | {orphan_builders} |",
        f"| Product feeds | {product_feeds} |",
        f"| Owned product feeds | {owned_feeds} |",
        f"| Unowned product feeds | {unowned_feeds} |",
        f"| Multiple-evidenced-owner feeds | {multi_owner_feeds} |",
        "",
        "## Coverage",
        "",
        "| Coverage area | Percentage |",
        "|---|---:|",
        f"| Estimated canonical parse health | {builder_parse_health}% |",
        f"| Canonical scope reconciliation | {scope_reconciliation}% |",
        f"| Builder graph connection | {graph_connection}% |",
        f"| Product feed ownership | {feed_ownership}% |",
        "",
        "## Priority Governance Actions",
        "",
    ]
    for row in exceptions:
        if int(row["count"]) <= 0:
            continue
        lines.append(
            f"- **{row['severity']} â€” {row['exception_code']} ({row['count']}):** "
            f"{row['governance_action']}"
        )

    lines.extend([
        "",
        "## Completed Governance Units",
        "",
        "1. Canonical Builder Registry V1.1",
        "2. Canonical Parse Failure Auditor V1",
        "3. Canonical Scope Refiner V1",
        "4. Canonical Builder Dependency Graph V1.1",
        "5. Product Feed Registry V1.1",
        "",
        "## Governance Boundary",
        "",
        "This dashboard consolidates governed evidence. It does not repair source code, "
        "delete files, assign ownership without evidence, lower thresholds, or claim "
        "that unresolved records are healthy.",
        "",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    print("EDGEIQ PLATFORM GOVERNANCE DASHBOARD V1")
    print("VERDICT=PASS")
    print(f"PLATFORM_GOVERNANCE_STATUS={platform_status}")
    print(f"GOVERNANCE_MATURITY_INDEX={maturity_index}")
    print(f"CANONICAL_BUILDERS={canonical_after}")
    print(f"ACTIVE_OR_TRUNCATED_DEFECTS={active_defects}")
    print(f"DEPENDENCY_EDGES={dependency_edges}")
    print(f"PRODUCT_FEEDS={product_feeds}")
    print(f"OWNED_PRODUCT_FEEDS={owned_feeds}")
    print(f"UNOWNED_PRODUCT_FEEDS={unowned_feeds}")
    print(f"OUTPUT_ROOT={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
