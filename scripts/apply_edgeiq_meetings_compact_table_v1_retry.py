from pathlib import Path

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

# Remove the summaryOrder definition exactly.
summary_order = '''const summaryOrder = [
  ["MEETINGS", "meetings"],
  ["RACES", "races"],
  ["DECLARED", "declared"],
  ["SCRATCHINGS", "scratchings"],
  ["HEAVY TRACKS", "heavyTracks"],
  ["SOFT TRACKS", "softTracks"],
  ["GOOD TRACKS", "goodTracks"],
  ["WEATHER ALERTS", "weatherAlerts"],
] as const;

'''

if summary_order not in component:
    raise RuntimeError(
        "Exact summaryOrder definition not found. No files were written."
    )

component = component.replace(summary_order, "", 1)

# Remove the complete summary section by its JSX class boundary.
summary_start = '<section className="eiq-meetings-engineering__summary">'
start_index = component.find(summary_start)

if start_index < 0:
    raise RuntimeError(
        "Meetings summary section start was not found. No files were written."
    )

summary_end = component.find("</section>", start_index)

if summary_end < 0:
    raise RuntimeError(
        "Meetings summary section end was not found. No files were written."
    )

summary_end += len("</section>")
component = component[:start_index] + component[summary_end:]

# Remove the selected table headings exactly.
headings = [
    "                    <th>DECLARED</th>\n",
    "                    <th>SCRATCHINGS</th>\n",
    "                    <th>STATUS</th>\n",
    "                    <th>EDGEiQ READ</th>\n",
]

for heading in headings:
    if heading not in component:
        raise RuntimeError(
            f"Expected heading not found: {heading.strip()}. "
            "No files were written."
        )
    component = component.replace(heading, "", 1)

# Remove the selected MeetingRow cells exactly.
cells = [
    "      <td>{meeting.declared}</td>\n",
    "      <td>{meeting.scratchings}</td>\n",
    "      <td>{meeting.status}</td>\n",
    '''      <td className="is-left">
        <span>{meeting.edgeiqRead.join(" / ")}</span>
      </td>
''',
]

for cell in cells:
    if cell not in component:
        raise RuntimeError(
            "Expected MeetingRow cell was not found: "
            f"{cell.strip()[:80]}. No files were written."
        )
    component = component.replace(cell, "", 1)

css_marker = "/* EDGEIQ MEETINGS COMPACT TABLE V1 RETRY */"

css_block = r'''

/* EDGEIQ MEETINGS COMPACT TABLE V1 RETRY */
.eiq-meetings-engineering__table-scroll {
  overflow-x: hidden;
  padding-bottom: 0;
  scrollbar-gutter: auto;
}

.eiq-meetings-engineering__table {
  width: 100%;
  min-width: 0;
  table-layout: fixed;
}

.eiq-meetings-engineering__table th,
.eiq-meetings-engineering__table td {
  box-sizing: border-box;
  padding: 9px 6px;
  font-size: 11px;
  line-height: 1.25;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: normal;
}

.eiq-meetings-engineering__table th {
  font-size: 9px;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

/* SELECT */
.eiq-meetings-engineering__table th:nth-child(1),
.eiq-meetings-engineering__table td:nth-child(1) {
  width: 8%;
}

/* MEETING */
.eiq-meetings-engineering__table th:nth-child(2),
.eiq-meetings-engineering__table td:nth-child(2) {
  width: 14%;
}

/* STATE */
.eiq-meetings-engineering__table th:nth-child(3),
.eiq-meetings-engineering__table td:nth-child(3) {
  width: 8%;
}

/* RAIL */
.eiq-meetings-engineering__table th:nth-child(4),
.eiq-meetings-engineering__table td:nth-child(4) {
  width: 9%;
}

/* TRACK */
.eiq-meetings-engineering__table th:nth-child(5),
.eiq-meetings-engineering__table td:nth-child(5) {
  width: 9%;
}

/* WEATHER */
.eiq-meetings-engineering__table th:nth-child(6),
.eiq-meetings-engineering__table td:nth-child(6) {
  width: 11%;
}

/* WIND */
.eiq-meetings-engineering__table th:nth-child(7),
.eiq-meetings-engineering__table td:nth-child(7) {
  width: 10%;
}

/* TEMP */
.eiq-meetings-engineering__table th:nth-child(8),
.eiq-meetings-engineering__table td:nth-child(8) {
  width: 9%;
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

.eiq-meetings-engineering__table td:nth-child(2) {
  text-align: left;
}

.eiq-meetings-engineering__select,
.eiq-meetings-engineering__open {
  width: 100%;
  min-width: 0;
  padding: 0 4px;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"

component_path.write_text(component, encoding="utf-8")
css_path.write_text(css, encoding="utf-8")

print("EDGEIQ_MEETINGS_COMPACT_TABLE_V1_RETRY_APPLIED")
print("removed_summary_strip=1")
print("removed_columns=DECLARED,SCRATCHINGS,STATUS,EDGEIQ_READ")
print(f"component={component_path}")
print(f"css={css_path}")
