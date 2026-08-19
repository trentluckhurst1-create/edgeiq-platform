from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingScratchingsWorkspace.tsx"
MEETING = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_scratchings_visual_structure_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_scratchings_visual_structure_v1_audit.txt"

workspace = WORKSPACE.read_text(encoding="utf-8", errors="replace") if WORKSPACE.exists() else ""
meeting = MEETING.read_text(encoding="utf-8", errors="replace") if MEETING.exists() else ""
css = CSS.read_text(encoding="utf-8", errors="replace") if CSS.exists() else ""

summary_labels = [
    "TOTAL SCRATCHINGS",
    "RACES AFFECTED",
    "NEW SINCE",
    "FIELDS MATERIALLY CHANGED",
    "EMERGENCIES PROMOTED",
    "LATEST UPDATE",
]
table_columns = [
    "RACE",
    "NO",
    "SILK",
    "HORSE",
    "TRAINER",
    "JOCKEY",
    "SCRATCHED AT",
    "REASON",
    "SOURCE",
    "STATUS",
]
timeline_columns = ["TIME", "RACE", "HORSE", "EVENT", "REASON", "SOURCE", "PROCESSED"]
impact_fields = [
    "Original Barrier",
    "Effective Barrier Before Event",
    "Effective Barrier After Event",
    "Field Size Before",
    "Field Size After",
    "Emergency Promotion",
    "MAP Refresh Status",
    "Race Shape Refresh Status",
    "Official Source",
    "Official Timestamp",
]

checks = {
    "component_exists": WORKSPACE.exists(),
    "scratchings_tab_is_not_pending": 'tab === "SCRATCHINGS"' in meeting and "MeetingScratchingsWorkspace" in meeting,
    "header_copy_present": "Official meeting scratchings and field changes" in workspace,
    "summary_labels_present": all(label in workspace for label in summary_labels),
    "filter_controls_present": all(label in workspace for label in ["ALL RACES", "ALL STATUS", "SEARCH HORSE / TRAINER / JOCKEY"]),
    "table_columns_present": all(column in workspace for column in table_columns),
    "timeline_columns_present": all(column in workspace for column in timeline_columns),
    "impact_fields_present": all(field in workspace for field in impact_fields),
    "data_freshness_present": "DATA FRESHNESS" in workspace,
    "light_css_present": "#ffffff" in css and "eiq-scratchings-v1" in css,
    "no_dark_warning_scratching_cards": "warning" not in workspace.lower() and "eiq-dark" not in css,
}

payload = {
    "status": "EDGEIQ_SCRATCHINGS_VISUAL_STRUCTURE_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_SCRATCHINGS_VISUAL_STRUCTURE_V1_AUDIT_FAIL",
    "checks": checks,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
