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

header_marker = '<header className="eiq-meetings-engineering__header">'
header_start = component.find(header_marker)

if header_start == -1:
    raise RuntimeError("Meetings header was not found. No files were written.")

header_end = component.find("</header>", header_start)

if header_end == -1:
    raise RuntimeError("Meetings header closing tag was not found. No files were written.")

header_end += len("</header>")
header_block = component[header_start:header_end]

dl_start_relative = header_block.find("<dl>")

if dl_start_relative == -1:
    raise RuntimeError(
        "Meetings KPI definition list was not found inside the header. "
        "No files were written."
    )

dl_end_relative = header_block.find("</dl>", dl_start_relative)

if dl_end_relative == -1:
    raise RuntimeError(
        "Meetings KPI definition-list closing tag was not found. "
        "No files were written."
    )

dl_end_relative += len("</dl>")

new_header_block = (
    header_block[:dl_start_relative].rstrip()
    + "\n"
    + header_block[dl_end_relative:].lstrip()
)

component = (
    component[:header_start]
    + new_header_block
    + component[header_end:]
)

if component == original_component:
    raise RuntimeError("No Meetings header change was produced.")

# Confirm the top header no longer contains the KPI strip.
updated_header_end = component.find("</header>", header_start) + len("</header>")
updated_header = component[header_start:updated_header_end]

if "<dl>" in updated_header:
    raise RuntimeError(
        "The top Meetings KPI strip remains after modification. "
        "No files were written."
    )

css_marker = "/* EDGEIQ MEETINGS FINAL COMPACT LOCK V1 */"

css_block = r'''

/* EDGEIQ MEETINGS FINAL COMPACT LOCK V1 */
.eiq-meetings-engineering__header {
  align-items: center;
  min-height: 0;
  padding: 18px 20px;
}

.eiq-meetings-engineering__header > div {
  width: 100%;
}

.eiq-meetings-engineering__table th,
.eiq-meetings-engineering__table td {
  padding-top: 12px;
  padding-bottom: 12px;
}

.eiq-meetings-engineering__table th:nth-child(1),
.eiq-meetings-engineering__table td:nth-child(1) {
  width: 9%;
}

.eiq-meetings-engineering__table th:nth-child(2),
.eiq-meetings-engineering__table td:nth-child(2) {
  width: 17%;
}

.eiq-meetings-engineering__table th:nth-child(3),
.eiq-meetings-engineering__table td:nth-child(3) {
  width: 8%;
}

.eiq-meetings-engineering__table th:nth-child(4),
.eiq-meetings-engineering__table td:nth-child(4),
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
.eiq-meetings-engineering__table td:nth-child(11) {
  width: 8%;
}

.eiq-meetings-engineering__table th:nth-child(12),
.eiq-meetings-engineering__table td:nth-child(12) {
  width: 10%;
}

.eiq-meetings-engineering__select,
.eiq-meetings-engineering__open {
  min-height: 32px;
  padding-inline: 8px;
}

.eiq-meetings-engineering__table td:nth-child(2) strong {
  font-size: 12px;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"

component_path.write_text(component, encoding="utf-8")
css_path.write_text(css, encoding="utf-8")

print("EDGEIQ_MEETINGS_FINAL_COMPACT_LOCK_V1_APPLIED")
print("top_kpi_refresh_strip_removed=1")
print("table_spacing_refined=1")
print(f"component={component_path}")
print(f"css={css_path}")
