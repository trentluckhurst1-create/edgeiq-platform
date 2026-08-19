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

original_component = component

# Remove summaryOrder from its declaration through "] as const;".
summary_start = component.find("const summaryOrder = [")

if summary_start == -1:
    raise RuntimeError("summaryOrder start not found.")

summary_end_marker = "] as const;"
summary_end = component.find(summary_end_marker, summary_start)

if summary_end == -1:
    raise RuntimeError("summaryOrder end not found.")

summary_end += len(summary_end_marker)

while summary_end < len(component) and component[summary_end] in "\r\n":
    summary_end += 1

component = component[:summary_start] + component[summary_end:]


# Remove the real summary JSX section using matching section depth.
opening_tag = (
    '<section className="eiq-meetings-engineering__summary" '
    'aria-label="Day summary">'
)

section_start = component.find(opening_tag)

if section_start == -1:
    raise RuntimeError("Day summary section opening tag not found.")

cursor = section_start
depth = 0
section_end = None

while cursor < len(component):
    next_open = component.find("<section", cursor)
    next_close = component.find("</section>", cursor)

    if next_close == -1:
        raise RuntimeError("Could not locate closing section tag.")

    if next_open != -1 and next_open < next_close:
        depth += 1
        cursor = next_open + len("<section")
    else:
        depth -= 1
        cursor = next_close + len("</section>")

        if depth == 0:
            section_end = cursor
            break

if section_end is None:
    raise RuntimeError("Could not resolve Day summary section boundary.")

while section_end < len(component) and component[section_end] in "\r\n":
    section_end += 1

component = component[:section_start] + component[section_end:]


# Remove exact headings.
for heading in (
    "<th>DECLARED</th>",
    "<th>SCRATCHINGS</th>",
    "<th>STATUS</th>",
    "<th>EDGEiQ READ</th>",
):
    if component.count(heading) != 1:
        raise RuntimeError(
            f"Expected exactly one {heading}, found {component.count(heading)}."
        )

    component = component.replace(heading, "", 1)


# Remove exact simple row cells.
for cell in (
    "<td>{meeting.declared}</td>",
    "<td>{meeting.scratchings}</td>",
    "<td>{meeting.status}</td>",
):
    if component.count(cell) != 1:
        raise RuntimeError(
            f"Expected exactly one {cell}, found {component.count(cell)}."
        )

    component = component.replace(cell, "", 1)


# Remove the EDGEiQ Read cell using its unique content.
edge_content = '<span>{meeting.edgeiqRead.join(" / ")}</span>'
edge_position = component.find(edge_content)

if edge_position == -1:
    raise RuntimeError("EDGEiQ Read row content not found.")

cell_start = component.rfind("<td", 0, edge_position)
cell_end = component.find("</td>", edge_position)

if cell_start == -1 or cell_end == -1:
    raise RuntimeError("EDGEiQ Read table cell boundaries not found.")

cell_end += len("</td>")
component = component[:cell_start] + component[cell_end:]


# Final source validation before writing.
for forbidden in (
    "summaryOrder",
    "eiq-meetings-engineering__summary",
    "<th>DECLARED</th>",
    "<th>SCRATCHINGS</th>",
    "<th>STATUS</th>",
    "<th>EDGEiQ READ</th>",
    "{meeting.declared}",
    "{meeting.scratchings}",
    "{meeting.status}",
    'meeting.edgeiqRead.join(" / ")',
):
    if forbidden in component:
        raise RuntimeError(f"Removal validation failed: {forbidden}")


css_marker = "/* EDGEIQ MEETINGS COMPACT TABLE V2 */"

css_block = r'''

/* EDGEIQ MEETINGS COMPACT TABLE V2 */
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
  box-sizing: border-box;
  padding: 9px 6px;
  font-size: 11px;
  line-height: 1.25;
  white-space: normal;
  overflow-wrap: anywhere;
}

.eiq-meetings-engineering__table th {
  font-size: 9px;
  letter-spacing: 0.035em;
  white-space: nowrap;
}

.eiq-meetings-engineering__table th:nth-child(1),
.eiq-meetings-engineering__table td:nth-child(1) {
  width: 8%;
}

.eiq-meetings-engineering__table th:nth-child(2),
.eiq-meetings-engineering__table td:nth-child(2) {
  width: 15%;
}

.eiq-meetings-engineering__table th:nth-child(3),
.eiq-meetings-engineering__table td:nth-child(3) {
  width: 7%;
}

.eiq-meetings-engineering__table th:nth-child(4),
.eiq-meetings-engineering__table td:nth-child(4) {
  width: 9%;
}

.eiq-meetings-engineering__table th:nth-child(5),
.eiq-meetings-engineering__table td:nth-child(5) {
  width: 9%;
}

.eiq-meetings-engineering__table th:nth-child(6),
.eiq-meetings-engineering__table td:nth-child(6) {
  width: 12%;
}

.eiq-meetings-engineering__table th:nth-child(7),
.eiq-meetings-engineering__table td:nth-child(7) {
  width: 10%;
}

.eiq-meetings-engineering__table th:nth-child(8),
.eiq-meetings-engineering__table td:nth-child(8) {
  width: 9%;
}

.eiq-meetings-engineering__table th:nth-child(9),
.eiq-meetings-engineering__table td:nth-child(9) {
  width: 6%;
}

.eiq-meetings-engineering__table th:nth-child(10),
.eiq-meetings-engineering__table td:nth-child(10),
.eiq-meetings-engineering__table th:nth-child(11),
.eiq-meetings-engineering__table td:nth-child(11),
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
  padding-inline: 4px;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"

if component == original_component:
    raise RuntimeError("No component changes were produced.")

component_path.write_text(component, encoding="utf-8")
css_path.write_text(css, encoding="utf-8")

print("EDGEIQ_MEETINGS_COMPACT_TABLE_V2_APPLIED")
print("summary_strip_removed=1")
print("columns_removed=DECLARED,SCRATCHINGS,STATUS,EDGEIQ_READ")
