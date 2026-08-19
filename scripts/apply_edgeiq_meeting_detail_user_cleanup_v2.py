from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SRC = ROOT / "src"
CSS_PATH = SRC / "edgeiq-os" / "styles" / "edgeiqOsV2.css"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_component() -> Path:
    candidates: list[Path] = []

    for path in SRC.rglob("*.tsx"):
        if "CHECKPOINT" in path.name.upper():
            continue

        text = read(path)
        lower = text.lower()

        required = (
            "meeting detail",
            "meeting highlights",
            "data freshness",
            "meeting race list",
        )

        if all(marker in lower for marker in required):
            candidates.append(path)

    if len(candidates) != 1:
        print("MEETING_DETAIL_CANDIDATES")
        for candidate in candidates:
            print(candidate)

        raise RuntimeError(
            f"Expected exactly one live Meeting Detail component, found {len(candidates)}."
        )

    return candidates[0]


def tag_start(text: str, position: int, tag: str) -> int:
    matches = list(
        re.finditer(
            rf"<{re.escape(tag)}(?:\s|>)",
            text[:position],
            flags=re.IGNORECASE,
        )
    )

    if not matches:
        raise RuntimeError(f"No enclosing <{tag}> found.")

    return matches[-1].start()


def balanced_end(text: str, start: int, tag: str) -> int:
    pattern = re.compile(
        rf"</?{re.escape(tag)}(?:\s[^<>]*?)?/?>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    depth = 0

    for match in pattern.finditer(text, start):
        token = match.group(0)
        closing = token.startswith("</")
        self_closing = token.rstrip().endswith("/>")

        if closing:
            depth -= 1
            if depth == 0:
                return match.end()
        elif not self_closing:
            depth += 1

    raise RuntimeError(f"Unbalanced <{tag}> block.")


def enclosing_block(
    text: str,
    marker: str,
    allowed_tags: tuple[str, ...],
    required_terms: tuple[str, ...] = (),
) -> tuple[int, int]:
    position = text.lower().find(marker.lower())

    if position < 0:
        raise RuntimeError(f"Marker not found: {marker}")

    for tag in allowed_tags:
        try:
            start = tag_start(text, position, tag)
            end = balanced_end(text, start, tag)
            block = text[start:end]
            lower = block.lower()

            if all(term.lower() in lower for term in required_terms):
                return start, end
        except RuntimeError:
            continue

    raise RuntimeError(f"Could not isolate block containing: {marker}")


def remove_range(text: str, start: int, end: int) -> str:
    while start > 0 and text[start - 1] in " \t":
        start -= 1

    while end < len(text) and text[end] in " \t":
        end += 1

    if end < len(text) and text[end] == "\r":
        end += 1
    if end < len(text) and text[end] == "\n":
        end += 1

    return text[:start] + text[end:]


component_path = find_component()
component = read(component_path)
css = read(CSS_PATH)

original_component = component
original_css = css

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
checkpoint = (
    ROOT
    / "checkpoints"
    / f"edgeiq_meeting_detail_user_cleanup_v2_{timestamp}"
)
checkpoint.mkdir(parents=True, exist_ok=True)

shutil.copy2(component_path, checkpoint / component_path.name)
shutil.copy2(CSS_PATH, checkpoint / CSS_PATH.name)

print(f"component={component_path}")
print(f"checkpoint={checkpoint}")


# ------------------------------------------------------------
# 1. Remove upper header metrics:
# Race Count / First Race / Last Race / Runners / Status /
# Last Updated.
# ------------------------------------------------------------
start, end = enclosing_block(
    component,
    "Race Count",
    ("dl", "section", "div"),
    (
        "first race",
        "last race",
        "runners",
        "status",
        "last updated",
    ),
)
component = remove_range(component, start, end)


# ------------------------------------------------------------
# 2. Remove duplicated metrics strip below tabs.
# Find the remaining Race Count occurrence after the first removal.
# ------------------------------------------------------------
if "race count" not in component.lower():
    raise RuntimeError("Duplicate Race Count strip was not found.")

start, end = enclosing_block(
    component,
    "Race Count",
    ("section", "div", "dl"),
    (
        "first race",
        "last race",
        "runners",
        "status",
        "last updated",
    ),
)
component = remove_range(component, start, end)


# ------------------------------------------------------------
# 3. Remove Official Update card from condition cards.
# ------------------------------------------------------------
start, end = enclosing_block(
    component,
    "Official Update",
    ("div",),
)
component = remove_range(component, start, end)


# ------------------------------------------------------------
# 4. Remove the right-side user-irrelevant rail:
# Meeting Highlights / Track Map / EDGEiQ Notes / Data Freshness.
# ------------------------------------------------------------
start, end = enclosing_block(
    component,
    "Meeting Highlights",
    ("aside", "section", "div"),
    (
        "track map",
        "edgeiq notes",
        "data freshness",
    ),
)
component = remove_range(component, start, end)


# ------------------------------------------------------------
# 5. Remove Status column from race table.
# ------------------------------------------------------------
heading_patterns = [
    re.compile(r"<th>\s*STATUS\s*</th>", re.IGNORECASE),
]

heading_removed = 0

for pattern in heading_patterns:
    component, count = pattern.subn("", component, count=1)
    heading_removed += count

if heading_removed != 1:
    raise RuntimeError(
        f"Expected one Status table heading, removed {heading_removed}."
    )

status_cell_patterns = [
    re.compile(
        r'<td[^>]*>\s*\{(?:race|row)\.status\}\s*</td>',
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r'<td[^>]*>\s*<[^>]+>\s*\{(?:race|row)\.status\}\s*</[^>]+>\s*</td>',
        re.IGNORECASE | re.DOTALL,
    ),
]

status_cell_removed = 0

for pattern in status_cell_patterns:
    component, count = pattern.subn("", component, count=1)
    status_cell_removed += count

    if count:
        break

if status_cell_removed != 1:
    raise RuntimeError(
        f"Expected one race Status cell, removed {status_cell_removed}."
    )


# ------------------------------------------------------------
# Final validation before any file is written.
# ------------------------------------------------------------
for forbidden in (
    "meeting highlights",
    "data freshness",
    "no governed meeting-level notes are currently available",
    "<th>status</th>",
):
    if forbidden in component.lower():
        raise RuntimeError(f"Cleanup validation failed: {forbidden}")

if component == original_component:
    raise RuntimeError("No Meeting Detail source changes were produced.")


css_marker = "/* EDGEIQ MEETING DETAIL USER CLEANUP V2 */"

css_block = r'''

/* EDGEIQ MEETING DETAIL USER CLEANUP V2 */
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
  width: 90px;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"

component_path.write_text(component, encoding="utf-8")
CSS_PATH.write_text(css, encoding="utf-8")

print("EDGEIQ_MEETING_DETAIL_USER_CLEANUP_V2_APPLIED")
print("removed=upper_metrics")
print("removed=duplicate_metrics")
print("removed=official_update")
print("removed=right_rail")
print("removed=status_column")
