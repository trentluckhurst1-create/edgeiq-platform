from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

COMPONENT = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingWorkspace.tsx"
)

CSS = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "styles"
    / "edgeiqOsV2.css"
)

component = COMPONENT.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")
original_component = component


# ============================================================
# 1. REMOVE SELECTED RACE DETAILS RENDER
# ============================================================

component, selected_render_count = re.subn(
    r'''
    ^[ \t]*
    <SelectedRacePanel
    \s+selected=\{selected\}
    \s*/>
    [ \t]*\r?\n
    ''',
    "",
    component,
    count=1,
    flags=re.MULTILINE | re.VERBOSE,
)

if selected_render_count != 1:
    raise RuntimeError(
        f"Expected one SelectedRacePanel render, removed "
        f"{selected_render_count}. No files were written."
    )


# ============================================================
# 2. REMOVE SELECTED RACE DETAILS FUNCTION
# ============================================================

component, selected_function_count = re.subn(
    r'''
    \nfunction\ SelectedRacePanel
    \(
      .*?
    \)
    \s*\{
      .*?
    \n\}
    \n
    (?=
      \n
      (?:
        function\ |
        export\ function\
      )
    )
    ''',
    "\n",
    component,
    count=1,
    flags=re.DOTALL | re.VERBOSE,
)

if selected_function_count != 1:
    raise RuntimeError(
        f"Expected one SelectedRacePanel function, removed "
        f"{selected_function_count}. No files were written."
    )


# Remove its now-unused selected result declaration if present.
component = re.sub(
    r'''
    ^[ \t]*const\ selected\s*=
    .*?
    ;[ \t]*\r?\n
    ''',
    "",
    component,
    count=1,
    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
)


# ============================================================
# 3. REMOVE TRACK AND OPEN HEADERS
# ============================================================

for heading in ("TRACK", "OPEN"):
    component, count = re.subn(
        rf'''
        ^[ \t]*<th>{heading}</th>[ \t]*\r?\n
        ''',
        "",
        component,
        count=1,
        flags=re.MULTILINE | re.VERBOSE,
    )

    if count != 1:
        raise RuntimeError(
            f"Expected one {heading} table heading, removed {count}. "
            "No files were written."
        )


# ============================================================
# 4. REMOVE DUPLICATED RACE-NAME SECONDARY LINE
# ============================================================

component, secondary_count = re.subn(
    r'''
    ^[ \t]*
    \{row\.secondary
      \s*\?
      \s*<small>\{row\.secondary\}</small>
      \s*:\s*null
    \}
    [ \t]*\r?\n
    ''',
    "",
    component,
    count=1,
    flags=re.MULTILINE | re.VERBOSE,
)

if secondary_count != 1:
    raise RuntimeError(
        f"Expected one duplicated race secondary line, removed "
        f"{secondary_count}. No files were written."
    )


# ============================================================
# 5. REMOVE TRACK VALUE CELL
# ============================================================

track_cell_patterns = (
    r'''
    ^[ \t]*<td>
      \{row\.track\}
    </td>[ \t]*\r?\n
    ''',
    r'''
    ^[ \t]*<td>
      \{valueOrUnavailable\(row\.track\)\}
    </td>[ \t]*\r?\n
    ''',
    r'''
    ^[ \t]*<td>
      \{valueOrUnavailable\(row\.trackCondition\)\}
    </td>[ \t]*\r?\n
    ''',
    r'''
    ^[ \t]*<td[^>]*>
      \{row\.trackCondition\}
    </td>[ \t]*\r?\n
    ''',
)

track_cell_removed = 0

for pattern in track_cell_patterns:
    component, count = re.subn(
        pattern,
        "",
        component,
        count=1,
        flags=re.MULTILINE | re.VERBOSE,
    )

    track_cell_removed += count

    if count:
        break

if track_cell_removed != 1:
    raise RuntimeError(
        "The race-table Track value cell was not identified. "
        "No files were written."
    )


# ============================================================
# 6. CAPTURE AND REMOVE OPEN BUTTON CELL
# ============================================================

open_cell_pattern = re.compile(
    r'''
    ^[ \t]*<td>\s*
    <button
      .*?
      className="eiq-meeting-v1-open"
      .*?
      onClick=\{
        \(event\)\s*=>\s*\{
          .*?
          onOpenRace\(
            (?P<argument>[^;]+?)
          \);
          .*?
        \}
      \}
      .*?
    >
      .*?
    </button>
    \s*</td>[ \t]*\r?\n
    ''',
    flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
)

open_match = open_cell_pattern.search(component)

if not open_match:
    raise RuntimeError(
        "The existing race Open button cell was not identified. "
        "No files were written."
    )

open_argument = open_match.group("argument").strip()

component = (
    component[:open_match.start()]
    + component[open_match.end():]
)


# ============================================================
# 7. MAKE ENTIRE ROW OPEN THE RACE
# ============================================================

old_row_click = (
    '                onClick={() => onSelectRace(row.raceKey)}'
)

new_row_click = f'''                role="button"
                tabIndex={{0}}
                aria-label={{`Open ${{row.raceLabel}} ${{row.raceName}}`}}
                onClick={{() => {{
                  onSelectRace(row.raceKey);
                  onOpenRace({open_argument});
                }}}}
                onKeyDown={{(event) => {{
                  if (event.key === "Enter" || event.key === " ") {{
                    event.preventDefault();
                    onSelectRace(row.raceKey);
                    onOpenRace({open_argument});
                  }}
                }}}}'''

if old_row_click not in component:
    raise RuntimeError(
        "The current race-row click handler was not found. "
        "No files were written."
    )

component = component.replace(
    old_row_click,
    new_row_click,
    1,
)


# ============================================================
# 8. CHANGE R1 TO 1
# ============================================================

race_number_replacements = (
    ("                <td>{row.raceLabel}</td>",
     "                <td>{row.raceNumber}</td>"),
    ("                <td>R{row.raceNumber}</td>",
     "                <td>{row.raceNumber}</td>"),
)

race_number_changed = False

for old, new in race_number_replacements:
    if old in component:
        component = component.replace(old, new, 1)
        race_number_changed = True
        break

if not race_number_changed:
    raise RuntimeError(
        "The race-number table cell was not identified. "
        "No files were written."
    )


# ============================================================
# 9. VALIDATE SOURCE BEFORE WRITING
# ============================================================

for forbidden in (
    "function SelectedRacePanel(",
    "<SelectedRacePanel",
    "<th>TRACK</th>",
    "<th>OPEN</th>",
    'className="eiq-meeting-v1-open"',
    "{row.secondary ?",
):
    if forbidden in component:
        raise RuntimeError(
            f"Old Races content still remains: {forbidden}"
        )

for required in (
    'role="button"',
    'tabIndex={0}',
    "onOpenRace(",
    "<td>{row.raceNumber}</td>",
    "<th>FIELD</th>",
    "<th>SCR</th>",
):
    if required not in component:
        raise RuntimeError(
            f"Required Races change was not installed: {required}"
        )

if component == original_component:
    raise RuntimeError(
        "No Meeting Races component changes were produced."
    )


# ============================================================
# 10. RACES TABLE CSS
# ============================================================

css_marker = "/* EDGEIQ MEETING RACES CLEANUP V1 */"

css_block = r'''

/* EDGEIQ MEETING RACES CLEANUP V1 */
.eiq-meeting-v1-table {
  width: 100%;
  table-layout: fixed;
}

.eiq-meeting-v1-table th,
.eiq-meeting-v1-table td {
  padding: 13px 12px;
  vertical-align: middle;
}

.eiq-meeting-v1-table th:nth-child(1),
.eiq-meeting-v1-table td:nth-child(1) {
  width: 7%;
}

.eiq-meeting-v1-table th:nth-child(2),
.eiq-meeting-v1-table td:nth-child(2) {
  width: 10%;
  white-space: nowrap;
}

.eiq-meeting-v1-table th:nth-child(3),
.eiq-meeting-v1-table td:nth-child(3) {
  width: 39%;
  text-align: left;
}

.eiq-meeting-v1-table th:nth-child(4),
.eiq-meeting-v1-table td:nth-child(4) {
  width: 11%;
}

.eiq-meeting-v1-table th:nth-child(5),
.eiq-meeting-v1-table td:nth-child(5) {
  width: 15%;
}

.eiq-meeting-v1-table th:nth-child(6),
.eiq-meeting-v1-table td:nth-child(6),
.eiq-meeting-v1-table th:nth-child(7),
.eiq-meeting-v1-table td:nth-child(7) {
  width: 9%;
}

.eiq-meeting-v1-table tbody tr {
  cursor: pointer;
  transition:
    background-color 120ms ease,
    box-shadow 120ms ease;
}

.eiq-meeting-v1-table tbody tr:hover {
  background: #f3f7ff;
}

.eiq-meeting-v1-table tbody tr.is-selected {
  background: #edf3ff;
  box-shadow: inset 3px 0 0 #3569d4;
}

.eiq-meeting-v1-table tbody tr:focus-visible {
  outline: 2px solid #3569d4;
  outline-offset: -2px;
}

.eiq-meeting-v1-table td:nth-child(3) strong {
  display: block;
  font-size: 12px;
  line-height: 1.35;
}

.eiq-meeting-v1-table td:nth-child(3) small {
  display: none !important;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"


COMPONENT.write_text(
    component,
    encoding="utf-8",
)

CSS.write_text(
    css,
    encoding="utf-8",
)

print("EDGEIQ_MEETING_RACES_CLEANUP_V1_APPLIED")
print("removed=SELECTED_RACE_DETAILS")
print("removed=TRACK_COLUMN")
print("removed=OPEN_COLUMN")
print("removed=DUPLICATED_RACE_SECONDARY_LINE")
print("row_action=OPEN_RACE")
print("race_number=NUMERIC_ONLY")
print("selected_row=PALE_BLUE_WITH_BLUE_EDGE")
print(f"component={COMPONENT}")
print(f"css={CSS}")
