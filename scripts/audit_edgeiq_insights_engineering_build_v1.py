from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_edgeiq_insights_terminal_feed_v1.py"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "insightsFeed.ts"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "InsightsWorkspace.tsx"
RACE_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
FEED = ROOT / "public" / "data" / "edgeiq_insights_terminal_feed_v1.csv"
TRACE = ROOT / "public" / "data" / "edgeiq_insights_engineering_build_v1_trace.txt"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_insights_engineering_build_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_insights_engineering_build_v1_audit.txt"

service = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""
component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""
race_workspace = RACE_WORKSPACE.read_text(encoding="utf-8", errors="replace") if RACE_WORKSPACE.exists() else ""
builder = BUILDER.read_text(encoding="utf-8", errors="replace") if BUILDER.exists() else ""
rows = []
if FEED.exists():
    with FEED.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle))

checks = {
    "builder_exists": BUILDER.exists(),
    "service_exists": SERVICE.exists(),
    "component_exists": COMPONENT.exists(),
    "feed_exists": FEED.exists(),
    "trace_exists": TRACE.exists(),
    "feed_under_frontend_limit": len(rows) <= 10000,
    "service_rejects_large_feeds": "> 10000" in service and "rejected oversized insights feed" in service,
    "component_display_only": "buildInsightsViewModel" in component and "loadInsightsTerminalFeed" in component,
    "race_workspace_uses_component": "InsightsWorkspace" in race_workspace and '"INSIGHTS"' in race_workspace,
    "builder_owns_insights": "first_public_reason" in builder and "build_cards" in builder,
    "no_warehouse_fetch": "edgeiq_results_master" not in service and "speed_master" not in service and "warehouse" not in service.lower(),
}

payload = {
    "status": "EDGEIQ_INSIGHTS_ENGINEERING_BUILD_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_INSIGHTS_ENGINEERING_BUILD_V1_AUDIT_FAIL",
    "checks": checks,
    "rows": len(rows),
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], f"rows={len(rows)}", "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
if payload["status"].endswith("FAIL"):
    raise SystemExit(1)
