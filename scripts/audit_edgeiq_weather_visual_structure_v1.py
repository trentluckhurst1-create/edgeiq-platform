from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWeatherWorkspace.tsx"
MEETING = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_weather_visual_structure_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_weather_visual_structure_v1_audit.txt"

workspace = WORKSPACE.read_text(encoding="utf-8", errors="replace") if WORKSPACE.exists() else ""
meeting = MEETING.read_text(encoding="utf-8", errors="replace") if MEETING.exists() else ""
css = CSS.read_text(encoding="utf-8", errors="replace") if CSS.exists() else ""

required_sections = ["Weather Summary", "Hourly Forecast", "Race-Day Impact", "Source State", "Weather Notes"]
required_copy = [
    "Official weather data is not currently available for this meeting.",
    "Hourly weather data unavailable.",
    "Loading official weather data",
]
prohibited = ["radar", "forecast confidence", "confidence score", "confidence bar"]

checks = {
    "component_exists": WORKSPACE.exists(),
    "weather_tab_is_not_pending": 'tab === "WEATHER"' in meeting and "MeetingWeatherWorkspace" in meeting,
    "sections_present": all(section in workspace for section in required_sections),
    "state_copy_present": all(copy in workspace for copy in required_copy),
    "prohibited_terms_absent": not any(term in workspace.lower() for term in prohibited),
    "light_css_present": ".eiq-weather-v1" in css and "#ffffff" in css and "#f4f6f9" in css.lower(),
    "no_gradient_or_glow": "gradient" not in css[css.find(".eiq-weather-v1") :].lower()
    and "glow" not in css[css.find(".eiq-weather-v1") :].lower(),
}

payload = {
    "status": "EDGEIQ_WEATHER_VISUAL_STRUCTURE_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_WEATHER_VISUAL_STRUCTURE_V1_AUDIT_FAIL",
    "checks": checks,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
