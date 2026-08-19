from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingGearChangesWorkspace.tsx"
MEETING = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_gear_changes_visual_structure_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_gear_changes_visual_structure_v1_audit.txt"

workspace = WORKSPACE.read_text(encoding="utf-8", errors="replace") if WORKSPACE.exists() else ""
meeting = MEETING.read_text(encoding="utf-8", errors="replace") if MEETING.exists() else ""
css = CSS.read_text(encoding="utf-8", errors="replace") if CSS.exists() else ""

summary_labels = [
    "TOTAL GEAR CHANGES",
    "FIRST TIME",
    "GEAR ADDED",
    "GEAR REMOVED",
    "AFFECTED RUNNERS",
    "LATEST UPDATE",
]
filters = ["ALL RACES", "ALL CHANGES", "ALL STATUS", "SEARCH HORSE / CHANGE"]
table_columns = [
    "RACE",
    "NO",
    "SILK",
    "HORSE",
    "CHANGE",
    "PREVIOUS",
    "TODAY",
    "FIRST TIME",
    "COMMENT",
    "SOURCE",
]
states = [
    "Loading official gear changes",
    "Official gear changes data is currently unavailable",
    "No official gear changes have been received",
    "Official gear changes could not be loaded",
]

checks = {
    "component_exists": WORKSPACE.exists(),
    "gear_tab_is_not_pending": 'tab === "GEAR_CHANGES"' in meeting and "MeetingGearChangesWorkspace" in meeting,
    "header_copy_present": "Official gear changes and equipment updates" in workspace,
    "summary_labels_present": all(label in workspace for label in summary_labels),
    "filter_controls_present": all(label in workspace for label in filters),
    "table_columns_present": all(column in workspace for column in table_columns),
    "historical_panel_present": "OFFICIAL GEAR HISTORY" in workspace,
    "state_copy_present": all(state in workspace for state in states),
    "light_css_present": ".eiq-gear-v1" in css and "#ffffff" in css and "#f4f6f9" in css.lower(),
    "no_prohibited_interpretation": not any(term in workspace.lower() for term in ["positive gear", "negative gear", "advantage", "bet", "tip"]),
}

payload = {
    "status": "EDGEIQ_GEAR_CHANGES_VISUAL_STRUCTURE_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_GEAR_CHANGES_VISUAL_STRUCTURE_V1_AUDIT_FAIL",
    "checks": checks,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
