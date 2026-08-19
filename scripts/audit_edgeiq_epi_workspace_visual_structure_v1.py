from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "EpiWorkspaceWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "epiWorkspaceFeed.ts"
STYLE = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
RACE_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_epi_workspace_visual_structure_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_epi_workspace_visual_structure_v1_audit.txt"

component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""
service = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""
style = STYLE.read_text(encoding="utf-8", errors="replace") if STYLE.exists() else ""
race_workspace = RACE_WORKSPACE.read_text(encoding="utf-8", errors="replace") if RACE_WORKSPACE.exists() else ""
epi_style = style[style.find(".eiq-epi-v1") :] if ".eiq-epi-v1" in style else ""

locked_headers = ["Current EPI", "Rank", "Field Avg", "Diff", "START 10", "START 1"]
hover_fields = ["DATE", "TRACK", "MEETING / RACE", "DISTANCE", "CLASS", "CONDITION", "BARRIER", "WEIGHT", "JOCKEY", "TRAINER", "FINISH", "MARGIN", "SP", "EPI", "ERI", "8-6", "6-4", "4-2", "2-F", "SOURCE", "VERSION / TIMESTAMP"]

checks = {
    "component_exists": COMPONENT.exists(),
    "service_exists": SERVICE.exists(),
    "scoped_epi_class": "eiq-epi-v1" in component and ".eiq-epi-v1" in style,
    "race_workspace_mounts_epi": "EpiWorkspaceWorkspace" in race_workspace and '"EPI"' in race_workspace,
    "locked_headers_visible": all(label in component for label in locked_headers),
    "hover_fields_visible": all(label in component for label in hover_fields),
    "keyboard_focus_supported": "onFocus" in component and "aria-label" in component,
    "large_feed_guard": "> 10000" in service and "rejected oversized EPI workspace feed" in service,
    "light_design_tokens": "#fff" in epi_style and "#e5e8ee" in epi_style and "#1f5fd6" in epi_style,
    "no_gradients": "linear-gradient" not in epi_style and "radial-gradient" not in epi_style,
    "no_dark_terminal_panel": "#020508" not in epi_style and "#071018" not in epi_style,
    "no_prohibited_ui_language": not re.search(r"\b(TIP|BET|SELECTION|WATCH|AVOID|STAR|MEDAL)\b", component, re.IGNORECASE),
}

payload = {
    "status": "EDGEIQ_EPI_WORKSPACE_VISUAL_STRUCTURE_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_EPI_WORKSPACE_VISUAL_STRUCTURE_V1_AUDIT_FAIL",
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
