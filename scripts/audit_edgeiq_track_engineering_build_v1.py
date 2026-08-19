from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "public" / "data" / "edgeiq_track_engineering_build_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_track_engineering_build_v1_audit.txt"
MEETING = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingTrackWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "trackFeed.ts"

audits = [
    "audit_edgeiq_track_data_contract_v1.py",
    "audit_edgeiq_track_historical_comparison_v1.py",
    "audit_edgeiq_track_visual_structure_v1.py",
]

results = {}
for audit in audits:
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / audit)], cwd=ROOT, text=True, capture_output=True)
    results[audit] = {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "passed": proc.returncode == 0 and "PASS" in proc.stdout,
    }

meeting_text = MEETING.read_text(encoding="utf-8", errors="replace") if MEETING.exists() else ""
service_text = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""

checks = {
    "component_exists": COMPONENT.exists(),
    "service_exists": SERVICE.exists(),
    "meeting_workspace_mounts_track": 'tab === "TRACK"' in meeting_text and "MeetingTrackWorkspace" in meeting_text,
    "pending_state_replaced": meeting_text.find('tab === "TRACK"') != -1
    and meeting_text.find('tab === "TRACK"') < meeting_text.find("activePending ?"),
    "react_loads_terminal_feeds_only": all(
        feed in service_text
        for feed in [
            "edgeiq_vic_official_track_conditions_v1.json",
            "edgeiq_track_map_manifest_v1.csv",
            "edgeiq_current_true_track_feed_v1.csv",
            "edgeiq_track_profile_v2.csv",
            "edgeiq_track_intelligence_profile_v2.csv",
        ]
    ),
    "all_child_audits_passed": all(item["passed"] for item in results.values()),
}

payload = {
    "status": "EDGEIQ_TRACK_ENGINEERING_BUILD_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_TRACK_ENGINEERING_BUILD_V1_AUDIT_FAIL",
    "checks": checks,
    "audits": results,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join(
        [
            payload["status"],
            "",
            "Checks:",
            *[f"{key}: {value}" for key, value in checks.items()],
            "",
            "Child audits:",
            *[f"{name}: {result['stdout'] or result['stderr']}" for name, result in results.items()],
        ]
    ),
    encoding="utf-8",
)
print(payload["status"])
