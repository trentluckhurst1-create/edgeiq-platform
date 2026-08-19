from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingDetailFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
SHELL = ROOT / "src" / "edgeiq-os" / "shell" / "EdgeiqOsShell.tsx"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_meeting_races_final_polish_v2_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_meeting_races_final_polish_v2_audit.txt"
PASS_MARKER = "EDGEIQ_MEETING_RACES_FINAL_POLISH_V2_AUDIT_PASS"


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def function_block(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.find(marker)
    if start < 0:
        return ""
    next_match = re.search(r"\nfunction\s+[A-Za-z0-9_]+\(", source[start + 1 :])
    next_export = re.search(r"\nexport\s+function\s+[A-Za-z0-9_]+\(", source[start + 1 :])
    candidates = [m.start() for m in (next_match, next_export) if m is not None]
    if not candidates:
        return source[start:]
    end = start + 1 + min(candidates)
    return source[start:end]


def check(name: str, passed: bool, detail: str = "") -> dict[str, object]:
    return {"check": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def main() -> None:
    component = read(COMPONENT)
    service = read(SERVICE)
    css = read(CSS)
    shell = read(SHELL)
    condition_block = function_block(component, "MeetingConditionStrip")
    return_index = component.find("  return (\n    <section className=\"eiq-meeting-workspace")
    selected_index = component.find("  const selected = useMemo(")

    headings = re.findall(r"<th(?:\s+className=\"[^\"]+\")?>([^<]+)</th>", component)
    expected_headings = ["RACE", "TIME", "RACE NAME", "DIST", "CLASS", "FIELD", "SCR"]
    exact_heading_order = headings[:7] == expected_headings

    checks = [
        check("duplicate MeetingHeader render gone", "<MeetingHeader" not in component and "function MeetingHeader(" not in component),
        check("top EDGEiQ shell/header still exists", "EdgeiqOsShell" in shell or "edgeiq-os" in shell),
        check("condition strip display mapping helper exists", "function formatMeetingConditionLabel(" in component),
        check("condition strip uses display-label mapping", "formatMeetingConditionLabel(item.label)" in condition_block and "<span>{item.label}</span>" not in condition_block),
        check("raw service labels unchanged", all(token in service for token in ['label: "TEMPERATURE"', 'label: "RAIN 24H"', 'label: "IRRIGATION 24H"'])),
        check("Track/Open table headings absent", "<th>TRACK</th>" not in component and "<th>OPEN</th>" not in component),
        check("SelectedRacePanel absent", "SelectedRacePanel" not in component),
        check("seven final headings present in correct order", exact_heading_order, " | ".join(headings[:7])),
        check("row click handler remains", "onClick={() => {" in component and "onOpenRace(row.race, row.raceIndex)" in component),
        check("keyboard handler remains", 'event.key === "Enter" || event.key === " "' in component and "event.preventDefault()" in component),
        check("correct selected race builder remains", "buildMeetingDetailSelectedRace(" in component and "model.races.find((row)" not in component),
        check("no stale invalid row.raceNumber reference remains", "row.raceNumber" not in component),
        check("selected declaration before component return", selected_index >= 0 and return_index >= 0 and selected_index < return_index),
        check("CSS final lock marker exists exactly once", css.count("/* EDGEIQ MEETING RACES FINAL POLISH V2 */") == 1),
        check("condition strip seven-column CSS exists", "grid-template-columns: repeat(7, minmax(0, 1fr))" in css),
        check("race table overflow final lock exists", ".eiq-meeting-v1-table-scroll" in css and "overflow-x: visible !important" in css),
    ]

    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "pass_marker": PASS_MARKER if status == "PASS" else "",
        "checks": checks,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = [
        PASS_MARKER if status == "PASS" else "EDGEIQ_MEETING_RACES_FINAL_POLISH_V2_AUDIT_FAIL",
        f"status={status}",
    ]
    lines.extend(f"{item['status']}: {item['check']} {item.get('detail', '')}" for item in checks)
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    print(lines[0])
    if status != "PASS":
        for item in checks:
            if item["status"] != "PASS":
                print(f"FAIL: {item['check']} {item.get('detail', '')}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
