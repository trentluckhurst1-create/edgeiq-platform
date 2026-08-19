from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "scratchingsFeed.ts"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingScratchingsWorkspace.tsx"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_scratchings_downstream_refresh_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_scratchings_downstream_refresh_v1_audit.txt"

service = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""
component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""

checks = {
    "downstream_status_type_present": "export type DownstreamStatus" in service,
    "map_refresh_status_exposed": "mapStatus" in service and "MAP Refresh Status" in component,
    "race_shape_refresh_status_exposed": "raceShapeStatus" in service and "Race Shape Refresh Status" in component,
    "active_field_updated_flag_exposed": "activeFieldUpdated" in service,
    "effective_barriers_updated_flag_exposed": "effectiveBarriersUpdated" in service,
    "react_does_not_calculate_map_or_shape": all(
        token not in component
        for token in ["buildRaceShape", "calculateRaceShape", "buildSpeedMap", "calculateSpeedMap"]
    ),
    "unavailable_pending_status_allowed": all(status in service for status in ["PENDING", "UNAVAILABLE", "NOT_REQUIRED"]),
}

payload = {
    "status": "EDGEIQ_SCRATCHINGS_DOWNSTREAM_REFRESH_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_SCRATCHINGS_DOWNSTREAM_REFRESH_V1_AUDIT_FAIL",
    "checks": checks,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
