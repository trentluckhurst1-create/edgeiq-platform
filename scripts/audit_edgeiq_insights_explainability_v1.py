from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_edgeiq_insights_terminal_feed_v1.py"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "insightsFeed.ts"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "InsightsWorkspace.tsx"
FEED = ROOT / "public" / "data" / "edgeiq_insights_terminal_feed_v1.csv"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_insights_explainability_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_insights_explainability_v1_audit.txt"

builder = BUILDER.read_text(encoding="utf-8", errors="replace") if BUILDER.exists() else ""
service = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""
component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""
rows = []
if FEED.exists():
    with FEED.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle))

text = (component + " " + " ".join(" ".join(row.values()) for row in rows)).lower()
prohibited = ["best bet", "tip", "selection", "guarantee", "staking", "watch", "avoid"]
runner_rows = [row for row in rows if row.get("row_kind") == "runner"]
populated = [row for row in runner_rows if row.get("key_insight") or row.get("edge")]

checks = {
    "builder_exists": BUILDER.exists(),
    "service_exists": SERVICE.exists(),
    "component_exists": COMPONENT.exists(),
    "builder_uses_governed_sources": "edgeiq_current_race_intelligence_v1.json" in builder and "edgeiq_market_terminal_feed_v1.csv" in builder,
    "component_states_confidence_is_evidence_quality": "It is not winning chance" in component,
    "rows_retain_source": all(row.get("source") for row in populated),
    "rows_retain_timestamp": all(row.get("source_timestamp") for row in populated),
    "rows_retain_coverage_or_confidence": all(row.get("coverage") or row.get("confidence") for row in populated),
    "service_rejects_large_feeds": "> 10000" in service and "rejected oversized insights feed" in service,
    "no_prohibited_language": not any(word in text for word in prohibited),
}

payload = {
    "status": "EDGEIQ_INSIGHTS_EXPLAINABILITY_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_INSIGHTS_EXPLAINABILITY_V1_AUDIT_FAIL",
    "checks": checks,
    "rows": len(rows),
    "populated_runner_rows": len(populated),
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], f"rows={len(rows)}", f"populated_runner_rows={len(populated)}", "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
if payload["status"].endswith("FAIL"):
    raise SystemExit(1)
