from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SRC = ROOT / "src"
CSS_PATH = SRC / "edgeiq-os" / "styles" / "edgeiqOsV2.css"

def find_component() -> Path:
    candidates = []

    for path in SRC.rglob("*.tsx"):
        text = path.read_text(encoding="utf-8", errors="replace")

        if (
            "MEETING DETAIL" in text
            and "MEETING HIGHLIGHTS" in text
            and "DATA FRESHNESS" in text
        ):
            candidates.append(path)

    if len(candidates) != 1:
        raise RuntimeError(
            "Expected exactly one Meeting Detail component, found "
            f"{len(candidates)}: {[str(path) for path in candidates]}"
        )

    return candidates[0]

def find_tag_start(text: str, position: int, tag: str) -> int:
    pattern = re.compile(rf"<{re.escape(tag)}(?:\s|>)", re.IGNORECASE)
    starts = [match.start() for match in pattern.finditer(text, 0, position)]

    if not starts:
        raise RuntimeError(
            f"Could not find an enclosing <{tag}> before position {position}."
        )

    return starts[-1]

def find_balanced_tag_end(text: str, start: int, tag: str) -> int:
    token_pattern = re.compile(
        rf"</?{re.escape(tag)}(?:\s[^<>]*?)?/?>",
        re.IGNORECASE | re.DOTALL,
    )

    depth = 0

    for match in token_pattern.finditer(text, start):
        token = match.group(0)
        is_close = token.startswith("</")
        is_self_closing = token.rstrip().endswith("/>")

        if is_close:
            depth -= 1
            if depth == 0:
                return match.end()
        elif not is_self_closing:
            depth += 1

    raise RuntimeError(f"Could not resolve closing </{tag}> tag.")

def enclosing_tag(text: str, needle: str, tag: str) -> tuple[int, int]:
    position = text.find(needle)

    if position < 0:
        raise RuntimeError(f"Required marker not found: {needle}")

    start = find_tag_start(text, position, tag)
    end = find_balanced_tag_end(text, start, tag)

    if not (start <= position < end):
        raise RuntimeError(
            f"Marker {needle!r} is not inside resolved <{tag}> block."
        )

    return start, end

def remove_block(text: str, start: int, end: int) -> str:
    while start > 0 and text[start - 1] in " \t":
        start -= 1

    while end < len(text) and text[end] in " \t":
        end += 1

    if end < len(text) and text[end] == "\r":
        end += 1
    if end < len(text) and text[end] == "\n":
        end += 1

    return text[:start] + text[end:]

def remove_card_by_label(text: str, label: str) -> str:
    marker_patterns = [
        f"<dt>{label}</dt>",
        f"<span>{label}</span>",
        f"<strong>{label}</strong>",
    ]

    marker = next((item for item in marker_patterns if item in text), None)

    if marker is None:
        raise RuntimeError(f"Card label not found: {label}")

    start, end = enclosing_tag(text, marker, "div")
    return remove_block(text, start, end)

component_path = find_component()
component = component_path.read_text(encoding="utf-8")
original_component = component

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
checkpoint = (
    ROOT
    / "checkpoints"
    / f"edgeiq_meeting_detail_user_only_v1_{timestamp}"
)
checkpoint.mkdir(parents=True, exist_ok=True)

shutil.copy2(component_path, checkpoint / component_path.name)
shutil.copy2(CSS_PATH, checkpoint / CSS_PATH.name)

# ------------------------------------------------------------------
# 1. Remove the upper header metric group.
# The first image retains only Meeting Detail / venue / date.
# ------------------------------------------------------------------
race_count_markers = [
    "<dt>Race Count</dt>",
    "<dt>RACE COUNT</dt>",
    "<span>RACE COUNT</span>",
]

race_count_marker = next(
    (marker for marker in race_count_markers if marker in component),
    None,
)

if race_count_marker is None:
    raise RuntimeError("Upper Race Count metric marker was not found.")

metric_position = component.find(race_count_marker)

# Prefer the enclosing DL, otherwise enclosing section/div.
metric_removed = False

for tag in ("dl", "section", "div"):
    try:
        start, end = enclosing_tag(component, race_count_marker, tag)
        block = component[start:end]

        if (
            "FIRST RACE" in block.upper()
            and "LAST RACE" in block.upper()
            and "RUNNERS" in block.upper()
            and "STATUS" in block.upper()
        ):
            component = remove_block(component, start, end)
            metric_removed = True
            break
    except RuntimeError:
        continue

if not metric_removed:
    raise RuntimeError("Could not isolate the upper Meeting Detail metric group.")

# ------------------------------------------------------------------
# 2. Remove the duplicate summary strip beneath the navigation tabs.
# It contains Race Count / First Race / Last Race / Runners / Status /
# Last Updated.
# ------------------------------------------------------------------
duplicate_marker = next(
    (
        marker
        for marker in race_count_markers
        if marker in component
    ),
    None,
)

if duplicate_marker is None:
    raise RuntimeError("Duplicate Race Count summary marker was not found.")

duplicate_removed = False

for tag in ("section", "div", "dl"):
    try:
        start, end = enclosing_tag(component, duplicate_marker, tag)
        block = component[start:end]
        upper = block.upper()

        if (
            "FIRST RACE" in upper
            and "LAST RACE" in upper
            and "RUNNERS" in upper
            and "LAST UPDATED" in upper
        ):
            component = remove_block(component, start, end)
            duplicate_removed = True
            break
    except RuntimeError:
        continue

if not duplicate_removed:
    raise RuntimeError("Could not isolate the duplicate summary strip.")

# ------------------------------------------------------------------
# 3. Remove Official Update from the conditions row.
# ------------------------------------------------------------------
official_markers = [
    "<dt>Official Update</dt>",
    "<dt>OFFICIAL UPDATE</dt>",
    "<span>OFFICIAL UPDATE</span>",
]

official_marker = next(
    (marker for marker in official_markers if marker in component),
    None,
)

if official_marker is None:
    raise RuntimeError("Official Update condition card was not found.")

start, end = enclosing_tag(component, official_marker, "div")
component = remove_block(component, start, end)

# ------------------------------------------------------------------
# 4. Remove the entire right-hand information rail.
# This removes Meeting Highlights, Track Map, EDGEiQ Notes and
# Data Freshness in one governed UI-only change.
# ------------------------------------------------------------------
rail_marker = "MEETING HIGHLIGHTS"

if rail_marker not in component:
    raise RuntimeError("Meeting Highlights rail marker was not found.")

rail_removed = False

for tag in ("aside", "section", "div"):
    try:
        start, end = enclosing_tag(component, rail_marker, tag)
        block = component[start:end]
        upper = block.upper()

        if (
            "MEETING HIGHLIGHTS" in upper
            and "DATA FRESHNESS" in upper
            and "EDGEIQ NOTES" in upper
        ):
            component = remove_block(component, start, end)
            rail_removed = True
            break
    except RuntimeError:
        continue

if not rail_removed:
    raise RuntimeError("Could not isolate the Meeting Detail right rail.")

# ------------------------------------------------------------------
# 5. Remove Status from the race list table only.
# ------------------------------------------------------------------
status_headings = [
    "<th>STATUS</th>",
    "<th>Status</th>",
]

status_heading = next(
    (heading for heading in status_headings if heading in component),
    None,
)

if status_heading is None:
    raise RuntimeError("Race-list Status heading was not found.")

if component.count(status_heading) != 1:
    raise RuntimeError(
        f"Expected one race-list Status heading, found "
        f"{component.count(status_heading)}."
    )

component = component.replace(status_heading, "", 1)

status_cell_patterns = [
    re.compile(
        r'<td(?:\s+className=\{[^{}]*\})?>\s*\{race\.status\}\s*</td>',
        re.DOTALL,
    ),
    re.compile(
        r'<td(?:\s+className="[^"]*")?>\s*\{race\.status\}\s*</td>',
        re.DOTALL,
    ),
]

status_cell_removed = False

for pattern in status_cell_patterns:
    component, count = pattern.subn("", component, count=1)

    if count == 1:
        status_cell_removed = True
        break

if not status_cell_removed:
    raise RuntimeError("Race-list race.status cell was not found.")

# ------------------------------------------------------------------
# Final validation before writing.
# ------------------------------------------------------------------
for forbidden in (
    "MEETING HIGHLIGHTS",
    "DATA FRESHNESS",
    "No governed meeting-level notes are currently available",
    "<th>STATUS</th>",
    "<th>Status</th>",
    "{race.status}",
):
    if forbidden in component:
        raise RuntimeError(
            f"Meeting Detail cleanup validation failed: {forbidden}"
        )

if component == original_component:
    raise RuntimeError("No Meeting Detail component changes were produced.")

css = CSS_PATH.read_text(encoding="utf-8")

css_marker = "/* EDGEIQ MEETING DETAIL USER-ONLY V1 */"

css_block = r'''

/* EDGEIQ MEETING DETAIL USER-ONLY V1 */
.eiq-meeting-detail-engineering__grid,
.eiq-meeting-detail__grid,
.eiq-meeting-detail-layout,
.eiq-meeting-detail-workspace__grid {
  grid-template-columns: minmax(0, 1fr) !important;
}

.eiq-meeting-detail-engineering__main,
.eiq-meeting-detail__main,
.eiq-meeting-detail-workspace__main {
  width: 100%;
  min-width: 0;
}

.eiq-meeting-detail-engineering table,
.eiq-meeting-detail-workspace table {
  width: 100%;
  table-layout: fixed;
}

.eiq-meeting-detail-engineering table th:last-child,
.eiq-meeting-detail-engineering table td:last-child,
.eiq-meeting-detail-workspace table th:last-child,
.eiq-meeting-detail-workspace table td:last-child {
  width: 88px;
}

.eiq-meeting-detail-engineering__conditions,
.eiq-meeting-detail-workspace__conditions {
  grid-template-columns: repeat(7, minmax(0, 1fr));
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"

component_path.write_text(component, encoding="utf-8")
CSS_PATH.write_text(css, encoding="utf-8")

print("EDGEIQ_MEETING_DETAIL_USER_ONLY_V1_APPLIED")
print(f"component={component_path}")
print(f"css={CSS_PATH}")
print(f"checkpoint={checkpoint}")
print("removed=upper_metrics")
print("removed=duplicate_summary")
print("removed=official_update_card")
print("removed=right_information_rail")
print("removed=race_status_column")
