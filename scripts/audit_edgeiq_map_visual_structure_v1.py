from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_map_visual_structure_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_map_visual_structure_v1_audit.txt"

component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""
css = CSS.read_text(encoding="utf-8", errors="replace") if CSS.exists() else ""

prohibited_component_phrases = [
    "RACING DIRECTION",
    "LEAD / FORWARD",
    "BARRIERS / START",
    "eiq-speed-map-v3",
    "laneFromPosition",
    "profileLane",
    "mapObservations",
    "buildMapRunner",
    "projectionEndpoint",
]

checks = {
    "component_exists": COMPONENT.exists(),
    "uses_map_v1_scope": "eiq-map-v1" in component and ".eiq-map-v1" in css,
    "uses_service_view_model": "buildMapViewModel" in component and "loadMapTerminalFeed" in component,
    "locked_columns_visible": all(
        phrase in component
        for phrase in ["No", "Horse", "Barrier", "Effective Barrier", "Run Style", "Early Speed", "Projected Position"]
    ),
    "no_direction_arrow_copy": "direction" not in component.lower() and "racing direction" not in component.lower(),
    "no_barrier_group_labels": all(phrase not in component for phrase in ["LEAD / FORWARD", "ON PACE", "MIDFIELD", "REARWARD", "BARRIERS / START"]),
    "no_old_map_component_calculations": all(phrase not in component for phrase in prohibited_component_phrases),
    "light_design_tokens_present": all(token in css for token in ["#ffffff", "#fafbfc", "#e5e8ee", "#1f5fd6", "#1a1a1a"]),
    "no_vertical_table_dividers_in_new_table": "border-right" not in css[css.find(".eiq-map-v1-table") : css.find(".eiq-map-v1-empty")],
}

payload = {
    "status": "EDGEIQ_MAP_VISUAL_STRUCTURE_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_MAP_VISUAL_STRUCTURE_V1_AUDIT_FAIL",
    "checks": checks,
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
if payload["status"].endswith("FAIL"):
    raise SystemExit(1)
