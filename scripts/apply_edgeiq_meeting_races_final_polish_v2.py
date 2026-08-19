from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingDetailFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
SCRIPT = ROOT / "scripts" / "apply_edgeiq_meeting_races_final_polish_v2.py"

CHECKPOINT_NAME = f"edgeiq_meeting_races_final_polish_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
CHECKPOINT = ROOT / "checkpoints" / CHECKPOINT_NAME


def read(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"Required file missing: {path}")
    return path.read_text(encoding="utf-8")


def checkpoint_files() -> None:
    CHECKPOINT.mkdir(parents=True, exist_ok=False)
    for path in (COMPONENT, SERVICE, CSS, SCRIPT):
        if path.exists():
            target = CHECKPOINT / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def function_block(source: str, name: str) -> tuple[int, int, str]:
    marker = f"function {name}("
    start = source.find(marker)
    if start < 0:
        raise RuntimeError(f"{name} function not found.")
    next_match = re.search(r"\nfunction\s+[A-Za-z0-9_]+\(", source[start + 1 :])
    if next_match is None:
        next_export = re.search(r"\nexport\s+function\s+[A-Za-z0-9_]+\(", source[start + 1 :])
        if next_export is None:
            raise RuntimeError(f"{name} function end boundary not found.")
        end = start + 1 + next_export.start()
    else:
        end = start + 1 + next_match.start()
    return start, end, source[start:end]


def remove_meeting_header(component: str) -> str:
    if "<MeetingHeader model={model} onBackToMeetings={onBackToMeetings} />" not in component:
        if "function MeetingHeader(" not in component:
            return component
        raise RuntimeError("MeetingHeader function exists but expected render was not found.")

    component = component.replace(
        "      <MeetingHeader model={model} onBackToMeetings={onBackToMeetings} />\n",
        "",
        1,
    )

    start, end, _block = function_block(component, "MeetingHeader")
    component = component[:start] + component[end:].lstrip("\n")

    if "function MeetingHeader(" in component or "<MeetingHeader" in component:
        raise RuntimeError("Duplicate Meeting Detail header removal failed.")
    return component


def install_condition_label_mapping(component: str) -> str:
    start, end, block = function_block(component, "MeetingConditionStrip")
    if "formatMeetingConditionLabel(" not in component:
        helper = '''function formatMeetingConditionLabel(label: string): string {
  const displayLabels: Record<string, string> = {
    TEMPERATURE: "TEMP",
    "RAIN 24H": "RAIN",
    "IRRIGATION 24H": "IRRIGATION",
  };

  return displayLabels[label.trim().toUpperCase()] ?? label;
}

'''
        component = component[:start] + helper + component[start:]
        start += len(helper)
        end += len(helper)
        block = component[start:end]

    if "<span>{formatMeetingConditionLabel(item.label)}</span>" in block:
        return component

    raw = "<span>{item.label}</span>"
    if block.count(raw) != 1:
        raise RuntimeError(f"Expected one condition-strip raw label render inside MeetingConditionStrip, found {block.count(raw)}.")

    block = block.replace(raw, "<span>{formatMeetingConditionLabel(item.label)}</span>", 1)
    component = component[:start] + block + component[end:]
    start, end, block = function_block(component, "MeetingConditionStrip")
    if "<span>{item.label}</span>" in block:
        raise RuntimeError("Raw visible condition label still rendered inside MeetingConditionStrip.")
    return component


def validate_component(component: str, service: str, require_polish: bool) -> None:
    required = [
        "buildMeetingDetailSelectedRace(",
        "const selected = useMemo(",
        "MeetingDetailSelectedRace | null",
        "const selected = useMemo(",
        "selected?.row.race ?? null",
        "<th>RACE</th>",
        "<th>TIME</th>",
        '<th className="is-left">RACE NAME</th>',
        "<th>DIST</th>",
        "<th>CLASS</th>",
        "<th>FIELD</th>",
        "<th>SCR</th>",
        'role="button"',
        "tabIndex={0}",
        'event.key === "Enter" || event.key === " "',
        'row.raceLabel.replace(/^R/i, "")',
    ]
    if require_polish:
        required.append("formatMeetingConditionLabel(item.label)")
    for token in required:
        if token not in component:
            raise RuntimeError(f"Required MeetingWorkspace token missing after patch: {token}")

    forbidden = [
        "<SelectedRacePanel",
        "function SelectedRacePanel(",
        "<th>TRACK</th>",
        "<th>OPEN</th>",
        "row.raceNumber",
        "model.races.find((row)",
    ]
    for token in forbidden:
        if token in component:
            raise RuntimeError(f"Forbidden MeetingWorkspace token remains after patch: {token}")
    if require_polish:
        for token in ("function MeetingHeader(", "<MeetingHeader"):
            if token in component:
                raise RuntimeError(f"Forbidden MeetingWorkspace token remains after patch: {token}")

    if 'label: "TEMPERATURE"' not in service or 'label: "RAIN 24H"' not in service or 'label: "IRRIGATION 24H"' not in service:
        raise RuntimeError("Underlying governed condition-strip service labels were unexpectedly changed or missing.")

    return_index = component.find("  return (\n    <section className=\"eiq-meeting-workspace")
    selected_index = component.find("  const selected = useMemo(")
    if selected_index < 0 or return_index < 0 or selected_index > return_index:
        raise RuntimeError("Selected-race declaration is not before JSX return.")


def install_css(css: str) -> str:
    marker = "/* EDGEIQ MEETING RACES FINAL POLISH V2 */"
    css = re.sub(
        r"\n/\* EDGEIQ MEETING RACES FINAL POLISH V2 \*/\n.*?(?=\n/\* EDGEIQ |\Z)",
        "\n",
        css,
        flags=re.S,
    )
    block = r'''

/* EDGEIQ MEETING RACES FINAL POLISH V2 */
.eiq-meeting-v1-condition-strip {
  display: grid !important;
  grid-template-columns: repeat(7, minmax(0, 1fr)) !important;
  gap: 8px !important;
  padding: 10px !important;
  overflow: visible !important;
}

.eiq-meeting-v1-condition-strip > div {
  min-width: 0 !important;
  padding: 10px 11px !important;
  border-radius: 8px !important;
  background: #ffffff !important;
}

.eiq-meeting-v1-condition-strip span {
  font-size: 9px !important;
  line-height: 1.2 !important;
  letter-spacing: 0.06em !important;
  white-space: nowrap !important;
}

.eiq-meeting-v1-condition-strip strong {
  margin-top: 4px !important;
  font-size: 12px !important;
  line-height: 1.25 !important;
  white-space: normal !important;
  overflow-wrap: anywhere !important;
}

.eiq-meeting-v1-layout {
  display: block !important;
  margin-top: 10px !important;
}

.eiq-meeting-v1-table-scroll {
  width: 100% !important;
  overflow-x: visible !important;
}

.eiq-meeting-v1-table {
  width: 100% !important;
  min-width: 0 !important;
  table-layout: fixed !important;
}

.eiq-meeting-v1-table th,
.eiq-meeting-v1-table td {
  height: auto !important;
  min-width: 0 !important;
  padding: 10px 10px !important;
  line-height: 1.3 !important;
  vertical-align: middle !important;
  white-space: normal !important;
}

.eiq-meeting-v1-table th {
  font-size: 9px !important;
  letter-spacing: 0.06em !important;
}

.eiq-meeting-v1-table th:nth-child(1),
.eiq-meeting-v1-table td:nth-child(1) {
  width: 6.5% !important;
  text-align: center !important;
}

.eiq-meeting-v1-table th:nth-child(2),
.eiq-meeting-v1-table td:nth-child(2) {
  width: 9% !important;
  text-align: center !important;
  white-space: nowrap !important;
}

.eiq-meeting-v1-table th:nth-child(3),
.eiq-meeting-v1-table td:nth-child(3) {
  width: 47% !important;
  text-align: left !important;
}

.eiq-meeting-v1-table th:nth-child(4),
.eiq-meeting-v1-table td:nth-child(4) {
  width: 9% !important;
  text-align: center !important;
}

.eiq-meeting-v1-table th:nth-child(5),
.eiq-meeting-v1-table td:nth-child(5) {
  width: 13.5% !important;
  text-align: center !important;
}

.eiq-meeting-v1-table th:nth-child(6),
.eiq-meeting-v1-table td:nth-child(6),
.eiq-meeting-v1-table th:nth-child(7),
.eiq-meeting-v1-table td:nth-child(7) {
  width: 7.5% !important;
  text-align: center !important;
}

.eiq-meeting-v1-table tbody tr {
  cursor: pointer;
  transition: background-color 120ms ease, box-shadow 120ms ease;
}

.eiq-meeting-v1-table tbody tr:hover {
  background: #f3f7ff !important;
}

.eiq-meeting-v1-table tbody tr.is-selected {
  background: #edf3ff !important;
  box-shadow: inset 3px 0 0 #3569d4 !important;
}

.eiq-meeting-v1-table tbody tr:focus-visible {
  outline: 2px solid #3569d4 !important;
  outline-offset: -2px !important;
}

.eiq-meeting-v1-table td:nth-child(3) strong {
  display: block !important;
  color: #1a1a1a !important;
  font-size: 12px !important;
  font-weight: 750 !important;
  line-height: 1.3 !important;
}

@media (max-width: 1180px) {
  .eiq-meeting-v1-condition-strip {
    grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  }
}
'''
    css = css.rstrip() + block + "\n"
    if css.count(marker) != 1:
        raise RuntimeError("CSS final lock marker count is not exactly one.")
    return css


def main() -> None:
    component = read(COMPONENT)
    service = read(SERVICE)
    css = read(CSS)
    original_component = component
    original_css = css

    validate_component(component, service, require_polish=False)
    checkpoint_files()

    component = remove_meeting_header(component)
    component = install_condition_label_mapping(component)
    validate_component(component, service, require_polish=True)

    css = install_css(css)

    if component == original_component and css == original_css:
        raise RuntimeError("No Meeting/Races final polish v2 changes were produced.")

    COMPONENT.write_text(component, encoding="utf-8")
    CSS.write_text(css, encoding="utf-8")

    print("EDGEIQ_MEETING_RACES_FINAL_POLISH_V2_APPLIED")
    print(f"checkpoint={CHECKPOINT}")
    print("removed=duplicate Meeting Detail header/card")
    print("condition_labels=render-only shortened")
    print("race_table=seven-column final lock")


if __name__ == "__main__":
    main()
