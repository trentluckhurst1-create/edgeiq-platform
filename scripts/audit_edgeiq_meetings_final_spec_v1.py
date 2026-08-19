from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingsFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
WINDOW = ROOT / "public" / "data" / "edgeiq_three_day_window_v1.json"
OUT_CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_meetings_final_spec_audit_v1.csv"
OUT_MD = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_MEETINGS_FINAL_SPEC_AUDIT_V1.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add(rows: list[dict[str, str]], check: str, passed: bool, detail: str) -> None:
    rows.append({
        "check": check,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    })


def main() -> int:
    component = read(COMPONENT)
    service = read(SERVICE)
    css = read(CSS)
    rows: list[dict[str, str]] = []

    required_component_tokens = [
        "selectedDayKey",
        "onDayChange",
        "onOpenMeeting",
        "onOpenRace",
        "meeting.declared",
        "meeting.scratchings",
        "meeting.weather",
        "selectedMeeting.declared",
        "selectedMeeting.scratchings",
        "trackConditionClass",
        "DECLARED",
        "WEATHER",
        "SCRATCHINGS",
    ]
    for token in required_component_tokens:
      add(rows, f"component_contains_{token}", token in component, token)

    rejected_visible_tokens = [
        "EDGEiQ Notes",
        "Weather Stations",
        "Forecast Source",
        "station ID",
        "builder status",
        "<th>RUNNERS</th>",
        "<th>FIRST</th>",
        "<th>LAST</th>",
        "<th>UPDATE</th>",
        "<th>OPEN</th>",
    ]
    for token in rejected_visible_tokens:
        add(rows, f"component_absent_{token}", token not in component, token)

    add(rows, "component_absent_confidence_label", "Confidence" not in component, "No product-facing Confidence copy in Meetings component")
    add(rows, "service_renamed_meeting_evidence_authority", "confidence:" not in service and "authority:" in service, "Meeting evidence uses authority, not Confidence wording")
    add(rows, "service_no_edgeiq_read_copy", "edgeiqRead" not in service and "buildEdgeiqRead" not in service, "Generic meeting notes removed from service model")

    for token in ["/* EDGEIQ MEETINGS FINAL SPEC V1 */", "is-firm", "is-good", "is-soft", "is-heavy"]:
        add(rows, f"css_contains_{token}", token in css, token)

    if WINDOW.exists():
        try:
            data = json.loads(WINDOW.read_text(encoding="utf-8"))
            dates = data.get("dates", [])
            keys = [item.get("key") for item in dates]
            add(rows, "three_day_window_has_three_dates", len(dates) == 3, str(keys))
            add(rows, "three_day_window_keys", {"TODAY", "TOMORROW", "DAY_PLUS_2"}.issubset(set(keys)), str(keys))
        except Exception as exc:
            add(rows, "three_day_window_parse", False, repr(exc))
    else:
        add(rows, "three_day_window_exists", False, str(WINDOW))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)

    failed = [row for row in rows if row["status"] != "PASS"]
    status = "EDGEIQ_MEETINGS_FINAL_SPEC_AUDIT_PASS" if not failed else "EDGEIQ_MEETINGS_FINAL_SPEC_AUDIT_FAIL"
    OUT_MD.write_text(
        "\n".join([
            "# EDGEiQ Meetings Final Spec Audit V1",
            "",
            f"Status: {status}",
            "",
            f"Checks: {len(rows)}",
            f"Failures: {len(failed)}",
            "",
            "## Results",
            "",
            *[f"- {row['status']}: {row['check']} - {row['detail']}" for row in rows],
            "",
        ]),
        encoding="utf-8",
    )

    print(status)
    print(f"Audit CSV: {OUT_CSV}")
    print(f"Audit MD: {OUT_MD}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
