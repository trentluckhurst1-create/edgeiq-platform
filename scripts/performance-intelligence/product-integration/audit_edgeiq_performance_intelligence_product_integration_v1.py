from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FEED = ROOT / "public" / "performance-intelligence" / "edgeiq_performance_intelligence_product_feeds_v1.json"
REPORT_DIR = ROOT / "docs" / "performance-intelligence" / "integration"
AUDIT_DIR = REPORT_DIR / "audits"
SERVICE_DIR = ROOT / "src" / "edgeiq-os" / "services" / "performance-intelligence"

REQUIRED_SERVICE_FILES = [
    SERVICE_DIR / "types.ts",
    SERVICE_DIR / "performanceIntelligenceFeed.ts",
    SERVICE_DIR / "PerformanceIntelligenceService.ts",
    SERVICE_DIR / "index.ts",
]

REQUIRED_UI_REFERENCES = {
    "EPI workspace": ROOT / "src" / "edgeiq-os" / "race" / "components" / "EpiWorkspaceWorkspace.tsx",
    "Form guide": ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx",
    "Overview": ROOT / "src" / "edgeiq-os" / "race" / "components" / "OverviewWorkspace.tsx",
    "Results": ROOT / "src" / "edgeiq-os" / "race" / "components" / "ResultsWorkspace.tsx",
    "Compare": ROOT / "src" / "edgeiq-os" / "compare" / "CompareWorkspace.tsx",
    "Insights": ROOT / "src" / "edgeiq-os" / "race" / "components" / "InsightsWorkspace.tsx",
}

FORBIDDEN_FRONTEND_LOADS = [
    "canonical_performance_facts_v0_2.csv",
    "edgeiq_results_master_v1.csv",
    "edgeiq_speed_master_v1.csv",
    "edgeiq_standardised_sectionals_v1.csv",
    "performances view",
    "879,784",
]

UNSUPPORTED_DATA_FIELDS = [
    "runner_adjusted_time_seconds",
    "runner_seconds_vs_benchmark",
    "runner_lengths_vs_benchmark",
    "official_sectional_time",
    "sectional_benchmark_seconds",
    "sectional_deviation_lengths",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    checks: list[dict[str, str]] = []

    if FEED.exists():
        feed = json.loads(FEED.read_text(encoding="utf-8"))
    else:
        feed = {}

    row_counts = {
        "race_intelligence_index": len(feed.get("race_intelligence_index", [])),
        "horse_intelligence_index": len(feed.get("horse_intelligence_index", [])),
        "historical_performance_intelligence_index": len(feed.get("historical_performance_intelligence_index", [])),
        "benchmark_explanation_index": len(feed.get("benchmark_explanation_index", [])),
    }

    checks.append({
        "check": "compact_product_feed_exists",
        "status": "PASS" if FEED.exists() else "FAIL",
        "detail": str(FEED),
    })
    checks.append({
        "check": "compact_feed_row_guard",
        "status": "PASS" if all(count <= 10000 for count in row_counts.values()) else "FAIL",
        "detail": json.dumps(row_counts, sort_keys=True),
    })

    for path in REQUIRED_SERVICE_FILES:
        checks.append({
            "check": f"service_file::{path.name}",
            "status": "PASS" if path.exists() else "FAIL",
            "detail": str(path),
        })

    ui_text = "\n".join(read_text(path) for path in REQUIRED_UI_REFERENCES.values())
    for name, path in REQUIRED_UI_REFERENCES.items():
        text = read_text(path)
        checks.append({
            "check": f"ui_wiring::{name}",
            "status": "PASS" if "performance-intelligence" in text or name == "Results" and "PerformanceIntelligence" in text else "FAIL",
            "detail": str(path),
        })

    src_text = "\n".join(read_text(path) for path in (ROOT / "src").rglob("*.ts*"))
    for forbidden in FORBIDDEN_FRONTEND_LOADS:
        checks.append({
            "check": f"frontend_warehouse_load_block::{forbidden}",
            "status": "PASS" if forbidden not in src_text else "FAIL",
            "detail": "Frontend source scan",
        })

    service_text = "\n".join(read_text(path) for path in REQUIRED_SERVICE_FILES)
    for field in UNSUPPORTED_DATA_FIELDS:
        checks.append({
            "check": f"unsupported_field_contract::{field}",
            "status": "PASS" if field in json.dumps(feed.get("manifest", {})) and field not in ui_text else "FAIL",
            "detail": "Present in manifest unsupported list and not rendered as a data field.",
        })

    status = "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL"
    report = {
        "pass_token": "EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE4_11_PRODUCT_INTEGRATION_AUDIT_PASS" if status == "PASS" else "EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE4_11_PRODUCT_INTEGRATION_AUDIT_FAIL",
        "generated_timestamp": now,
        "status": status,
        "row_counts": row_counts,
        "feed": str(FEED),
        "checks": checks,
    }

    json_path = AUDIT_DIR / "edgeiq_performance_intelligence_product_integration_audit_v1.json"
    csv_path = AUDIT_DIR / "edgeiq_performance_intelligence_product_integration_audit_v1.csv"
    md_path = REPORT_DIR / "EDGEIQ_PERFORMANCE_INTELLIGENCE_PRODUCT_INTEGRATION_FINAL_REPORT_V1.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
      writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
      writer.writeheader()
      writer.writerows(checks)

    lines = [
        "# EDGEiQ Performance Intelligence Product Integration Final Report V1",
        "",
        f"Generated: {now}",
        f"Status: {status}",
        "",
        "## Compact Feed Coverage",
        "",
    ]
    for key, count in row_counts.items():
        lines.append(f"- {key}: {count}")
    lines.extend([
        "",
        "## Integration Scope",
        "",
        "- Certified compact feed is served from `public/performance-intelligence`.",
        "- React services load compact product indexes only.",
        "- EPI, Form Guide, Overview, Results, Compare and Insights consume service lookups.",
        "- Unsupported runner-adjusted and sectional benchmark values remain unavailable.",
        "",
        "## Audit Checks",
        "",
    ])
    for row in checks:
        lines.append(f"- {row['status']}: {row['check']} - {row['detail']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(report["pass_token"])
    print(json.dumps({"status": status, "row_counts": row_counts, "json": str(json_path), "csv": str(csv_path), "report": str(md_path)}, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
