from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_edgeiq_overview_terminal_feed_v1.py"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "OverviewWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "overviewFeed.ts"
FEED = ROOT / "public" / "data" / "edgeiq_overview_terminal_feed_v1.csv"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_overview_intelligence_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_overview_intelligence_v1_audit.txt"

builder = BUILDER.read_text(encoding="utf-8", errors="replace") if BUILDER.exists() else ""
component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""
service = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""

rows = []
if FEED.exists():
    with FEED.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle))

prohibited = ["best bet", "tip", "selection", "guarantee", "watch", "avoid"]
component_lower = component.lower()
feed_text = " ".join(" ".join(row.values()).lower() for row in rows)

checks = {
    "builder_exists": BUILDER.exists(),
    "service_exists": SERVICE.exists(),
    "component_exists": COMPONENT.exists(),
    "builder_uses_governed_sources": "edgeiq_current_race_intelligence_v1.json" in builder and "edgeiq_three_day_product_catalog_v1.json" in builder,
    "builder_emits_pending_not_fake": "Pending" in builder and "unavailable" in builder,
    "component_does_not_fetch_source_intelligence_json": "edgeiq_current_race_intelligence_v1.json" not in component,
    "component_uses_terminal_service": "loadOverviewTerminalFeed" in component and "buildOverviewViewModel" in component,
    "service_rejects_large_feeds": "> 10000" in service and "rejected oversized overview feed" in service,
    "no_react_map_counting": "mapCounts" not in component and "projectedMapZone" not in component,
    "no_prohibited_language": not any(word in component_lower or word in feed_text for word in prohibited),
}

payload = {
    "status": "EDGEIQ_OVERVIEW_INTELLIGENCE_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_OVERVIEW_INTELLIGENCE_V1_AUDIT_FAIL",
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
