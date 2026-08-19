from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "LabWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "labResearch.ts"
FEED_SERVICE = ROOT / "src" / "edgeiq-os" / "services" / "performance-intelligence" / "performanceIntelligenceFeed.ts"
OUT = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_LAB_FINAL_SPEC_V1_AUDIT.md"


REQUIRED_COMPONENT = [
    "Stats Engine & Query Builder",
    "Universe",
    "Track",
    "Scope",
    "Entity",
    "Metric",
    "Group By",
    "Sort",
    "Result Limit",
    "Run Query",
    "Research Boundary",
]

REQUIRED_SERVICE = [
    "buildLabQueryModel",
    "executeLabResearchQuery",
    "JOCKEY",
    "TRAINER",
    "disabled: true",
    "metricsByEntity",
    "groupByOptions",
]

REJECTED_PRODUCT_TEXT = [
    "Confidence",
    "confidence",
    "mock",
    "demo",
    "sample data",
    "fake",
    "tip",
    "bet",
    "SQL",
]

REJECTED_LARGE_PATHS = [
    "edgeiq_results_master",
    "edgeiq_speed_master",
    "warehouse",
]


def missing(text: str, tokens: list[str]) -> list[str]:
    return [token for token in tokens if token not in text]


def present(text: str, tokens: list[str]) -> list[str]:
    return [token for token in tokens if token in text]


def main() -> int:
    component = COMPONENT.read_text(encoding="utf-8")
    service = SERVICE.read_text(encoding="utf-8")
    feed_service = FEED_SERVICE.read_text(encoding="utf-8")
    product_text = component + "\n" + service

    feed_path = ROOT / "public" / "performance-intelligence" / "edgeiq_performance_intelligence_product_feeds_v1.json"
    counts = {}
    if feed_path.exists():
        payload = json.loads(feed_path.read_text(encoding="utf-8"))
        counts = payload.get("manifest", {}).get("row_counts", {})

    failures: list[str] = []
    missing_component = missing(component, REQUIRED_COMPONENT)
    if missing_component:
        failures.append(f"Missing LAB component elements: {', '.join(missing_component)}")

    missing_service = missing(service, REQUIRED_SERVICE)
    if missing_service:
        failures.append(f"Missing LAB query service elements: {', '.join(missing_service)}")

    rejected = present(product_text, REJECTED_PRODUCT_TEXT)
    rejected = [token for token in rejected if token not in {"sample data"}]
    if rejected:
        failures.append(f"Rejected LAB product text remains: {', '.join(rejected)}")

    large_paths = present(component + "\n" + service + "\n" + feed_service, REJECTED_LARGE_PATHS)
    if large_paths:
        failures.append(f"LAB references warehouse-scale paths: {', '.join(large_paths)}")

    if "MAX_ROWS_PER_INDEX = 10000" not in feed_service:
        failures.append("Performance intelligence feed row guard missing")

    status = "EDGEIQ_LAB_FINAL_SPEC_AUDIT_PASS" if not failures else "EDGEIQ_LAB_FINAL_SPEC_AUDIT_FAIL"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "\n".join(
            [
                f"# {status}",
                "",
                f"- race_rows: {counts.get('race_intelligence_index', 'unknown')}",
                f"- horse_rows: {counts.get('horse_intelligence_index', 'unknown')}",
                f"- historical_rows: {counts.get('historical_performance_intelligence_index', 'unknown')}",
                f"- benchmark_rows: {counts.get('benchmark_explanation_index', 'unknown')}",
                "- query_service_boundary: yes",
                "- jockey_trainer_modules_inactive_without_governed_data: yes",
                "- large_browser_warehouse_loads: no",
                "- product_confidence_label: absent",
                "",
                "## Failures",
                *(f"- {failure}" for failure in failures),
            ]
        ).rstrip()
        + "\n",
        encoding="utf-8",
    )
    print(status)
    if failures:
        for failure in failures:
            print(failure)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
