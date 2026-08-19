from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_meetings_visual_structure_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_meetings_visual_structure_v1_audit.txt"

REQUIRED_CLASSES = [
    "eiq-meetings-engineering__header",
    "eiq-meetings-engineering__days",
    "eiq-meetings-engineering__summary",
    "eiq-meetings-engineering__grid",
    "eiq-meetings-engineering__table",
    "eiq-meetings-engineering__rail",
    "eiq-meetings-engineering__race-strip",
]

FORBIDDEN_COMPONENT_MARKERS = [
    "eiq-panel-grid",
    "eiq-meeting-card",
    "setSelectedDate",
]

SUMMARY_ORDER = [
    "MEETINGS",
    "RACES",
    "DECLARED",
    "SCRATCHINGS",
    "HEAVY TRACKS",
    "SOFT TRACKS",
    "GOOD TRACKS",
    "WEATHER ALERTS",
]


def add(checks: list[dict[str, str]], name: str, passed: bool, detail: str) -> None:
    checks.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})


def appears_in_order(text: str, values: list[str]) -> bool:
    cursor = -1
    for value in values:
        index = text.find(value, cursor + 1)
        if index <= cursor:
            return False
        cursor = index
    return True


def main() -> int:
    component = COMPONENT.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    checks: list[dict[str, str]] = []

    add(checks, "required_classes_in_component", all(item in component for item in REQUIRED_CLASSES), ",".join(REQUIRED_CLASSES))
    add(checks, "required_classes_in_css", all(item in css for item in REQUIRED_CLASSES), ",".join(REQUIRED_CLASSES))
    add(checks, "legacy_card_launcher_removed", not any(item in component for item in FORBIDDEN_COMPONENT_MARKERS), ",".join(FORBIDDEN_COMPONENT_MARKERS))
    add(checks, "summary_order_locked", appears_in_order(component, SUMMARY_ORDER), "|".join(SUMMARY_ORDER))
    add(checks, "desktop_grid_82_18", "82fr" in css and "18fr" in css and "gap: 16px" in css, "82/18 grid with 16px gap")
    add(checks, "table_min_width_scroll", "min-width: 1320px" in css and "overflow-x: auto" in css, "controlled horizontal scroll")
    add(checks, "selected_row_style", "tr.is-selected" in css and "inset 0 1px 0 #1f5fd6" in css, "blue outline selected row")
    add(checks, "selected_meeting_rail_order", appears_in_order(component, ["Today's Track", "Rail", "Weather", "Wind", "Temperature", "Rain 24h", "Irrigation 24h", "Official Update", "EDGEiQ Notes", "Open Meeting"]), "rail fields")
    add(checks, "race_strip_present", "RACES -" in component and "races scheduled" in component and "onOpenRace" in component, "race strip navigation")
    add(checks, "light_surfaces", "#ffffff" in css and "#fafbfc" in css and "#e5e8ee" in css, "MASTER-001 light tokens")

    status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    result = {
        "status": f"EDGEIQ_MEETINGS_VISUAL_STRUCTURE_V1_AUDIT_{status}",
        "checks": checks,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                result["status"],
                "",
                *[
                    f"{check['status']} {check['check']} - {check['detail']}"
                    for check in checks
                ],
            ]
        ),
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
