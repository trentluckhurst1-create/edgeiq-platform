from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "weatherFeed.ts"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWeatherWorkspace.tsx"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_weather_data_contract_v2_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_weather_data_contract_v2_audit.txt"

feeds = [
    ROOT / "public" / "data" / "edgeiq_metropolitan_weather_v1.json",
    ROOT / "public" / "data" / "edgeiq_race_weather_v1.json",
]
summary_fields = [
    "CURRENT CONDITION",
    "TEMPERATURE",
    "FEELS LIKE",
    "WIND",
    "GUSTS",
    "HUMIDITY",
    "RAIN 24H",
    "RAIN PROBABILITY",
    "SOURCE",
    "UPDATED AT",
]
hourly_columns = ["TIME", "WEATHER", "TEMP (C)", "WIND (km/h)", "GUSTS (km/h)", "RAIN PROB.", "RAIN (mm)"]
impact_rows = ["TRACK IMPACT", "WIND IMPACT", "RAIN TIMING", "OVERALL OUTLOOK"]

service = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""
component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""

row_counts = {}
for feed in feeds:
    if not feed.exists():
        row_counts[feed.name] = "missing"
        continue
    payload = json.loads(feed.read_text(encoding="utf-8", errors="replace"))
    row_counts[feed.name] = len(payload.get("records", []))

checks = {
    "service_exists": SERVICE.exists(),
    "component_exists": COMPONENT.exists(),
    "summary_fields_present": all(field in service for field in summary_fields),
    "hourly_columns_present": all(column in component for column in hourly_columns),
    "impact_rows_present": all(row in service for row in impact_rows),
    "terminal_feeds_only": "edgeiq_metropolitan_weather_v1.json" in service
    and "edgeiq_race_weather_v1.json" in service,
    "frontend_row_guard_present": "> 10000" in service and "rejected oversized weather feed" in service,
    "row_counts_under_limit": all(isinstance(count, int) and count <= 10000 for count in row_counts.values()),
    "unavailable_copy_exact": "Official weather data is not currently available for this meeting." in component,
}

payload = {
    "status": "EDGEIQ_WEATHER_DATA_CONTRACT_V2_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_WEATHER_DATA_CONTRACT_V2_AUDIT_FAIL",
    "checks": checks,
    "row_counts": row_counts,
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
            "Rows:",
            *[f"{key}: {value}" for key, value in row_counts.items()],
        ]
    ),
    encoding="utf-8",
)
print(payload["status"])
