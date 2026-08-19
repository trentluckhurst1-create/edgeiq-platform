from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingTrackWorkspace.tsx"
MEETING = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_track_visual_structure_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_track_visual_structure_v1_audit.txt"

workspace = WORKSPACE.read_text(encoding="utf-8", errors="replace") if WORKSPACE.exists() else ""
meeting = MEETING.read_text(encoding="utf-8", errors="replace") if MEETING.exists() else ""
css = CSS.read_text(encoding="utf-8", errors="replace") if CSS.exists() else ""

required_sections = [
    "Track Condition",
    "Rail Position and Track Map",
    "Track Details",
    "Track Pattern Analysis",
    "Historical Comparison",
    "Track Notes",
    "Contextual Operational Rail",
]
missing_state_copy = [
    "Curated track map unavailable",
    "Track pattern evidence unavailable",
    "Track notes unavailable",
    "Loading official track profile",
]
prohibited = ["Track Bias", "TRACK RECORD", "CLASS RECORD", "dark terminal", "star", "medal"]

checks = {
    "component_exists": WORKSPACE.exists(),
    "track_tab_is_not_pending": 'tab === "TRACK"' in meeting and "MeetingTrackWorkspace" in meeting,
    "sections_present": all(section in workspace for section in required_sections),
    "missing_states_present": all(copy in workspace for copy in missing_state_copy),
    "table_columns_present": all(column in workspace for column in ["METRIC", "TODAY", "LAST 3 MEETINGS", "LAST 10 MEETINGS"]),
    "light_css_present": ".eiq-track-v1" in css and "#ffffff" in css and "#f4f6f9" in css.lower(),
    "prohibited_terms_absent": not any(term.lower() in workspace.lower() for term in prohibited),
    "no_gradient_or_glow": "gradient" not in css[css.find(".eiq-track-v1") :].lower()
    and "glow" not in css[css.find(".eiq-track-v1") :].lower(),
}

payload = {
    "status": "EDGEIQ_TRACK_VISUAL_STRUCTURE_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_TRACK_VISUAL_STRUCTURE_V1_AUDIT_FAIL",
    "checks": checks,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
