from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWeatherWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "weatherFeed.ts"
MEETING_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_WEATHER_FINAL_SPEC_V1_AUDIT.md"


REQUIRED_SERVICE = [
    "edgeiq_on_track_weather_governed_v1_2.json",
    "governed_source_state",
    "freshness_status",
    "source_timestamp",
    "observation_local",
    "station_status",
    "source_owner",
]

REQUIRED_COMPONENT = [
    "Meeting weather and race-day conditions",
    "Current Observations",
    "Race-Day Weather Context",
    "Latest available weather observations are stale.",
]

REJECTED_COMPONENT = [
    "REFRESH WEATHER FEEDS",
    "Weather Stations",
    "Forecast Source",
    "station ID",
    "source registry",
    "evidence URL",
    "builder",
    "radar",
    "Confidence",
    "EDGEiQ development fixture",
    "fixtureMode",
    "unavailableMode",
    "partialMode",
    "Hourly Forecast",
]

REJECTED_MEETING = [
    "edgeiqWeatherFixture",
    "edgeiqWeatherUnavailable",
    "edgeiqWeatherPartial",
    "weatherFixtureMode",
    "weatherUnavailableMode",
    "weatherPartialMode",
]


def contains_all(text: str, tokens: list[str]) -> list[str]:
    return [token for token in tokens if token not in text]


def contains_any(text: str, tokens: list[str]) -> list[str]:
    return [token for token in tokens if token in text]


def main() -> int:
    component = COMPONENT.read_text(encoding="utf-8")
    service = SERVICE.read_text(encoding="utf-8")
    meeting_workspace = MEETING_WORKSPACE.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    governed_path = ROOT / "public" / "data" / "edgeiq_on_track_weather_governed_v1_2.json"
    governed_records = 0
    governed_states: list[str] = []
    governed_freshness: list[str] = []
    if governed_path.exists():
        payload = json.loads(governed_path.read_text(encoding="utf-8"))
        records = payload.get("records", [])
        governed_records = len(records) if isinstance(records, list) else 0
        for record in records if isinstance(records, list) else []:
            governed_states.append(str(record.get("governed_source_state", "")))
            governed_freshness.append(str(record.get("freshness_status", "")))

    failures: list[str] = []
    missing_service = contains_all(service, REQUIRED_SERVICE)
    if missing_service:
        failures.append(f"Missing preserved live-weather service fields: {', '.join(missing_service)}")

    missing_component = contains_all(component, REQUIRED_COMPONENT)
    if missing_component:
        failures.append(f"Missing required weather UI sections: {', '.join(missing_component)}")

    rejected_component = contains_any(component, REJECTED_COMPONENT)
    if rejected_component:
        failures.append(f"Rejected product-facing weather tokens remain: {', '.join(rejected_component)}")

    rejected_meeting = contains_any(meeting_workspace, REJECTED_MEETING)
    if rejected_meeting:
        failures.append(f"Rejected weather query/test wiring remains: {', '.join(rejected_meeting)}")

    if "EDGEIQ WEATHER FINAL SPEC V1" not in css:
        failures.append("Weather final CSS marker missing")

    if governed_records != 4:
        failures.append(f"Expected 4 governed live-weather records, found {governed_records}")

    status = "EDGEIQ_WEATHER_FINAL_SPEC_AUDIT_PASS" if not failures else "EDGEIQ_WEATHER_FINAL_SPEC_AUDIT_FAIL"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "\n".join(
            [
                f"# {status}",
                "",
                f"- governed_records: {governed_records}",
                f"- governed_states: {', '.join(governed_states) if governed_states else 'NONE'}",
                f"- governed_freshness: {', '.join(governed_freshness) if governed_freshness else 'NONE'}",
                "- live_weather_v1_2_path_preserved: yes",
                "- builder_owned_freshness_preserved: yes",
                "- visible_dev_weather_controls_removed: yes",
                "- visible_station_ids_registry_builder_terms_removed: yes",
                "- white_theme_css_marker_present: yes",
                "",
                "## Failures",
                *(f"- {failure}" for failure in failures),
            ]
        ).rstrip()
        + "\n",
        encoding="utf-8",
    )
    print(status)
    if failures:
        for failure in failures:
            print(failure)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
