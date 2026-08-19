from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "public" / "data" / "edgeiq_weather_engineering_build_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_weather_engineering_build_v1_audit.txt"
MEETING = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWeatherWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "weatherFeed.ts"

audits = [
    "audit_edgeiq_weather_data_contract_v2.py",
    "audit_edgeiq_weather_visual_structure_v1.py",
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
    "meeting_workspace_mounts_weather": 'tab === "WEATHER"' in meeting_text and "MeetingWeatherWorkspace" in meeting_text,
    "pending_state_replaced": meeting_text.find('tab === "WEATHER"') != -1
    and meeting_text.find('tab === "WEATHER"') < meeting_text.find("activePending ?"),
    "no_radar_or_confidence": "radar" not in service_text.lower()
    and "forecast confidence" not in service_text.lower()
    and "confidence score" not in service_text.lower(),
    "all_child_audits_passed": all(item["passed"] for item in results.values()),
}

payload = {
    "status": "EDGEIQ_WEATHER_ENGINEERING_BUILD_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_WEATHER_ENGINEERING_BUILD_V1_AUDIT_FAIL",
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
