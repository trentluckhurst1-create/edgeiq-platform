from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "trackFeed.ts"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingTrackWorkspace.tsx"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_track_historical_comparison_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_track_historical_comparison_v1_audit.txt"

service = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""
component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""

columns = ["METRIC", "TODAY", "LAST 3 MEETINGS", "LAST 10 MEETINGS"]
allowed_metrics = [
    "Inside Win %",
    "Middle Win %",
    "Wide Win %",
    "Leaders Win %",
    "On-Pace Win %",
    "Midfield Win %",
    "Backmarker Win %",
    "Lane Distribution",
    "Settling Position Distribution",
]
removed_metrics = ["Average Race Time", "Average Winning Margin"]

checks = {
    "component_exists": COMPONENT.exists(),
    "service_exists": SERVICE.exists(),
    "exact_columns_present": all(column in component for column in columns),
    "allowed_metrics_present": all(metric in service for metric in allowed_metrics),
    "removed_metrics_absent": all(metric not in service and metric not in component for metric in removed_metrics),
    "nulls_remain_unavailable": "valueOrUnavailable(row.last3Meetings)" in component
    and "valueOrUnavailable(row.last10Meetings)" in component,
    "no_react_historical_calculation": "last3Meetings:" in service and "last10Meetings:" in service,
}

payload = {
    "status": "EDGEIQ_TRACK_HISTORICAL_COMPARISON_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_TRACK_HISTORICAL_COMPARISON_V1_AUDIT_FAIL",
    "checks": checks,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
