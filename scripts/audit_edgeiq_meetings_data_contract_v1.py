from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WINDOW = ROOT / "public" / "data" / "edgeiq_three_day_window_v1.json"
CATALOG = ROOT / "public" / "data" / "edgeiq_three_day_product_catalog_v1.json"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingsFeed.ts"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_meetings_data_contract_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_meetings_data_contract_v1_audit.txt"

REQUIRED_KEYS = ["TODAY", "TOMORROW", "DAY_PLUS_2"]
REQUIRED_COLUMNS = [
    "SELECT",
    "MEETING",
    "STATE",
    "RAIL",
    "TRACK",
    "WEATHER",
    "WIND",
    "TEMP",
    "RACES",
    "DECLARED",
    "SCRATCHINGS",
    "FIRST",
    "LAST",
    "STATUS",
    "EDGEiQ READ",
    "OPEN",
]


def add(checks: list[dict[str, str]], name: str, passed: bool, detail: str) -> None:
    checks.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    checks: list[dict[str, str]] = []
    window = load_json(WINDOW)
    catalog = load_json(CATALOG)
    component = COMPONENT.read_text(encoding="utf-8")
    service = SERVICE.read_text(encoding="utf-8")

    keys = [item.get("key") for item in window.get("dates", [])]
    add(checks, "canonical_window_exists", WINDOW.exists(), str(WINDOW))
    add(checks, "canonical_window_keys", keys == REQUIRED_KEYS, f"keys={keys}")
    add(checks, "service_loads_window", "edgeiq_three_day_window_v1.json" in service, "window service URL")
    add(checks, "component_no_browser_date", "new Date" not in component and "Date.now" not in component, "React does not calculate dates")
    add(checks, "component_no_catalog_date_selection", "catalog.dates" not in component and "selectedDate" not in component, "No legacy catalogue date state")
    add(checks, "service_exports_day_view_model", "MeetingsDayViewModel" in service and "MeetingSummaryViewModel" in service, "typed view models")
    add(checks, "service_owns_edgeiq_read", "buildEdgeiqRead" in service and "edgeiqRead" in service, "EDGEiQ Read shaped in service")
    add(checks, "component_renders_required_columns", all(col in component for col in REQUIRED_COLUMNS), "|".join(REQUIRED_COLUMNS))

    meetings = catalog.get("meetings", [])
    races = [race for meeting in meetings for race in meeting.get("races", [])]
    runners = [runner for race in races for runner in race.get("runners", [])]
    date_coverage = sorted({meeting.get("date") for meeting in meetings if meeting.get("date")})
    add(checks, "catalog_has_meetings", len(meetings) > 0, f"meetings={len(meetings)}")
    add(checks, "catalog_has_races", len(races) > 0, f"races={len(races)}")
    add(checks, "catalog_has_runners", len(runners) > 0, f"runners={len(runners)}")
    add(checks, "catalog_dates_match_window", date_coverage == [item.get("date") for item in window.get("dates", []) if item.get("date") and item.get("date") in date_coverage], f"coverage={date_coverage}")

    status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    result = {
        "status": f"EDGEIQ_MEETINGS_DATA_CONTRACT_V1_AUDIT_{status}",
        "checks": checks,
        "catalog_counts": {
            "meetings": len(meetings),
            "races": len(races),
            "runners": len(runners),
        },
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
