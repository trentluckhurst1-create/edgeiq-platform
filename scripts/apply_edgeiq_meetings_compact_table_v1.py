from pathlib import Path
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

component_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingsWorkspace.tsx"
)

css_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "styles"
    / "edgeiqOsV2.css"
)

component = component_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")

original_component = component

# Remove the full eight-card summary strip.
summary_pattern = re.compile(
    r'''
\s*<section\s+className="eiq-meetings-engineering__summary">\s*
\{summaryOrder\.map\(\(\[label,\s*key\]\)\s*=>\s*\(\s*
<div\s+key=\{key\}>\s*
<span>\{label\}</span>\s*
<strong>\{activeDay\.totals\[key\]\}</strong>\s*
</div>\s*
\)\)\}\s*
</section>\s*
''',
    re.VERBOSE | re.DOTALL,
)

component, summary_count = summary_pattern.subn("\n", component, count=1)

if summary_count != 1:
    raise RuntimeError(
        f"Expected to remove one Meetings summary strip, removed {summary_count}. "
        "No files were written."
    )

# Remove the unused summaryOrder definition now that the strip is gone.
summary_order_pattern = re.compile(
    r'''
const\s+summaryOrder\s*=\s*\[\s*
.*?
\]\s+as\s+const;\s*
''',
    re.VERBOSE | re.DOTALL,
)

component, summary_order_count = summary_order_pattern.subn(
    "",
    component,
    count=1,
)

if summary_order_count != 1:
    raise RuntimeError(
        f"Expected to remove one summaryOrder definition, removed "
        f"{summary_order_count}. No files were written."
    )

# Remove the four unwanted table headings.
headings = [
    "DECLARED",
    "SCRATCHINGS",
    "STATUS",
    "EDGEiQ READ",
]

for heading in headings:
    pattern = re.compile(
        rf'\s*<th>{re.escape(heading)}</th>',
        re.IGNORECASE,
    )
    component, count = pattern.subn("", component, count=1)

    if count != 1:
        raise RuntimeError(
            f"Expected to remove heading {heading!r} once, removed {count}. "
            "No files were written."
        )

# Locate the MeetingRow implementation and remove the corresponding cells
# by their governed ViewModel properties.
cell_patterns = {
    "declared": re.compile(
        r'''
\s*<td(?:\s+className=\{[^}]*\})?>\s*
\{(?:clean\()?meeting\.declared\)?\}\s*
</td>
''',
        re.VERBOSE | re.DOTALL,
    ),
    "scratchings": re.compile(
        r'''
\s*<td(?:\s+className=\{[^}]*\})?>\s*
\{(?:clean\()?meeting\.scratchings\)?\}\s*
</td>
''',
        re.VERBOSE | re.DOTALL,
    ),
    "status": re.compile(
        r'''
\s*<td(?:\s+className=\{[^}]*\})?>\s*
\{(?:clean\()?meeting\.status\)?\}\s*
</td>
''',
        re.VERBOSE | re.DOTALL,
    ),
    "edgeiqRead": re.compile(
        r'''
\s*<td(?:\s+className=\{[^}]*\})?>\s*
\{(?:clean\()?meeting\.edgeiqRead(?:\[[^\]]+\])?\)?\}\s*
</td>
''',
        re.VERBOSE | re.DOTALL,
    ),
}

for field, pattern in cell_patterns.items():
    component, count = pattern.subn("", component, count=1)

    if count != 1:
        raise RuntimeError(
            f"Expected to remove the {field} table cell once, removed {count}. "
            "No files were written."
        )

if component == original_component:
    raise RuntimeError("No Meetings component changes were produced.")

css_marker = "/* EDGEIQ MEETINGS COMPACT TABLE V1 */"

css_block = r'''

/* EDGEIQ MEETINGS COMPACT TABLE V1 */
.eiq-meetings-engineering__summary {
  display: none;
}

.eiq-meetings-engineering__table-scroll {
  overflow-x: hidden;
  padding-bottom: 0;
}

.eiq-meetings-engineering__table {
  width: 100%;
  min-width: 0;
  table-layout: fixed;
}

.eiq-meetings-engineering__table th,
.eiq-meetings-engineering__table td {
  padding: 9px 7px;
  font-size: 11px;
  white-space: normal;
  overflow-wrap: anywhere;
}

/* SELECT */
.eiq-meetings-engineering__table th:nth-child(1),
.eiq-meetings-engineering__table td:nth-child(1) {
  width: 7%;
}

/* MEETING */
.eiq-meetings-engineering__table th:nth-child(2),
.eiq-meetings-engineering__table td:nth-child(2) {
  width: 13%;
}

/* STATE */
.eiq-meetings-engineering__table th:nth-child(3),
.eiq-meetings-engineering__table td:nth-child(3) {
  width: 7%;
}

/* RAIL */
.eiq-meetings-engineering__table th:nth-child(4),
.eiq-meetings-engineering__table td:nth-child(4) {
  width: 8%;
}

/* TRACK */
.eiq-meetings-engineering__table th:nth-child(5),
.eiq-meetings-engineering__table td:nth-child(5) {
  width: 8%;
}

/* WEATHER */
.eiq-meetings-engineering__table th:nth-child(6),
.eiq-meetings-engineering__table td:nth-child(6) {
  width: 10%;
}

/* WIND */
.eiq-meetings-engineering__table th:nth-child(7),
.eiq-meetings-engineering__table td:nth-child(7) {
  width: 9%;
}

/* TEMP */
.eiq-meetings-engineering__table th:nth-child(8),
.eiq-meetings-engineering__table td:nth-child(8) {
  width: 8%;
}

/* RACES */
.eiq-meetings-engineering__table th:nth-child(9),
.eiq-meetings-engineering__table td:nth-child(9) {
  width: 6%;
}

/* FIRST */
.eiq-meetings-engineering__table th:nth-child(10),
.eiq-meetings-engineering__table td:nth-child(10) {
  width: 8%;
}

/* LAST */
.eiq-meetings-engineering__table th:nth-child(11),
.eiq-meetings-engineering__table td:nth-child(11) {
  width: 8%;
}

/* OPEN */
.eiq-meetings-engineering__table th:nth-child(12),
.eiq-meetings-engineering__table td:nth-child(12) {
  width: 8%;
}

.eiq-meetings-engineering__table th {
  white-space: nowrap;
  font-size: 9px;
  letter-spacing: 0.045em;
}

.eiq-meetings-engineering__table td:nth-child(2) {
  text-align: left;
}

.eiq-meetings-engineering__open,
.eiq-meetings-engineering__select {
  width: 100%;
  min-width: 0;
  padding-left: 5px;
  padding-right: 5px;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"

component_path.write_text(component, encoding="utf-8")
css_path.write_text(css, encoding="utf-8")

print("EDGEIQ_MEETINGS_COMPACT_TABLE_V1_APPLIED")
print("removed_summary_strip=1")
print("removed_columns=DECLARED,SCRATCHINGS,STATUS,EDGEIQ_READ")
print(f"component={component_path}")
print(f"css={css_path}")
