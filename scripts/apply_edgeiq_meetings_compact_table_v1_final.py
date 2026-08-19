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

original_component = component_path.read_text(encoding="utf-8")
original_css = css_path.read_text(encoding="utf-8")

component = original_component
css = original_css

# 1. Remove summaryOrder.
summary_order_pattern = re.compile(
    r'''const summaryOrder = \[
.*?
\] as const;

''',
    re.DOTALL,
)

component, count = summary_order_pattern.subn("", component, count=1)

if count != 1:
    raise RuntimeError(
        f"summaryOrder removal expected 1 match, found {count}. "
        "No files were written."
    )

# 2. Remove the full top summary-card section.
summary_section_pattern = re.compile(
    r'''
\s*<section
\s+className="eiq-meetings-engineering__summary"
(?:\s+aria-label="Day summary")?
>
.*?
</section>
''',
    re.DOTALL | re.VERBOSE,
)

component, count = summary_section_pattern.subn("", component, count=1)

if count != 1:
    raise RuntimeError(
        f"Summary section removal expected 1 match, found {count}. "
        "No files were written."
    )

# 3. Remove unwanted headings.
for heading in (
    "DECLARED",
    "SCRATCHINGS",
    "STATUS",
    "EDGEiQ READ",
):
    pattern = re.compile(
        rf'^[ \t]*<th>{re.escape(heading)}</th>[ \t]*\r?\n',
        re.MULTILINE,
    )

    component, count = pattern.subn("", component, count=1)

    if count != 1:
        raise RuntimeError(
            f"Heading {heading!r} removal expected 1 match, found {count}. "
            "No files were written."
        )

# 4. Remove simple row cells.
for field in (
    "declared",
    "scratchings",
    "status",
):
    pattern = re.compile(
        rf'^[ \t]*<td>\{{meeting\.{field}\}}</td>[ \t]*\r?\n',
        re.MULTILINE,
    )

    component, count = pattern.subn("", component, count=1)

    if count != 1:
        raise RuntimeError(
            f"Cell meeting.{field} removal expected 1 match, found {count}. "
            "No files were written."
        )

# 5. Remove EDGEiQ Read row cell.
edgeiq_cell_pattern = re.compile(
    r'''
^[ \t]*<td\s+className="is-left">\s*
<span>\{meeting\.edgeiqRead\.join\(" / "\)\}</span>\s*
</td>[ \t]*\r?\n
''',
    re.MULTILINE | re.DOTALL | re.VERBOSE,
)

component, count = edgeiq_cell_pattern.subn("", component, count=1)

if count != 1:
    raise RuntimeError(
        f"EDGEiQ Read cell removal expected 1 match, found {count}. "
        "No files were written."
    )

# 6. Validate removed source elements.
for forbidden in (
    "const summaryOrder",
    'className="eiq-meetings-engineering__summary"',
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
        raise RuntimeError(
            f"Forbidden source remains after patch: {forbidden}. "
            "No files were written."
        )

css_marker = "/* EDGEIQ MEETINGS COMPACT TABLE V1 FINAL */"

css_block = r'''

/* EDGEIQ MEETINGS COMPACT TABLE V1 FINAL */
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
  letter-spacing: 0.035em;
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
  width: 15%;
}

/* STATE */
.eiq-meetings-engineering__table th:nth-child(3),
.eiq-meetings-engineering__table td:nth-child(3) {
  width: 7%;
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
  width: 12%;
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

if component == original_component:
    raise RuntimeError("No component changes were produced.")

# Only write after every validation passes.
component_path.write_text(component, encoding="utf-8")
css_path.write_text(css, encoding="utf-8")

print("EDGEIQ_MEETINGS_COMPACT_TABLE_V1_FINAL_APPLIED")
print("removed_summary_strip=1")
print("removed_columns=DECLARED,SCRATCHINGS,STATUS,EDGEIQ_READ")
print(f"component={component_path}")
print(f"css={css_path}")
