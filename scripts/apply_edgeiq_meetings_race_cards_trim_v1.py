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

patterns = {
    "RESTRICTION": re.compile(
        r'''
        \s*<div>\s*
        <dt>RESTRICTION</dt>\s*
        <dd>\{race\.restriction\}</dd>\s*
        </div>
        ''',
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    ),
    "FIELD": re.compile(
        r'''
        \s*<div>\s*
        <dt>FIELD</dt>\s*
        <dd>\{race\.fieldSize\}</dd>\s*
        </div>
        ''',
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    ),
    "STATUS": re.compile(
        r'''
        \s*<div>\s*
        <dt>STATUS</dt>\s*
        <dd>\{race\.status\}</dd>\s*
        </div>
        ''',
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    ),
}

removed = {}

for label, pattern in patterns.items():
    component, count = pattern.subn("", component)
    removed[label] = count

    if count < 1:
        raise RuntimeError(
            f"{label} race-card row was not found. "
            "No files were written."
        )

for forbidden in (
    "<dt>RESTRICTION</dt>",
    "<dt>Restriction</dt>",
    "<dt>FIELD</dt>",
    "<dt>Field</dt>",
    "<dt>STATUS</dt>",
    "<dt>Status</dt>",
):
    if forbidden in component:
        raise RuntimeError(
            f"Race-card source still contains {forbidden}. "
            "No files were written."
        )

if component == original_component:
    raise RuntimeError("No race-card changes were produced.")

css_marker = "/* EDGEIQ MEETINGS RACE CARDS TRIM V1 */"

css_block = r'''

/* EDGEIQ MEETINGS RACE CARDS TRIM V1 */
.eiq-meetings-engineering__race-list article {
  min-height: 0;
}

.eiq-meetings-engineering__race-list dl {
  padding-bottom: 12px;
}

.eiq-meetings-engineering__race-list dl div {
  grid-template-columns: 68px minmax(0, 1fr);
  padding: 5px 0;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"

component_path.write_text(component, encoding="utf-8")
css_path.write_text(css, encoding="utf-8")

print("EDGEIQ_MEETINGS_RACE_CARDS_TRIM_V1_APPLIED")
print(f"restriction_rows_removed={removed['RESTRICTION']}")
print(f"field_rows_removed={removed['FIELD']}")
print(f"status_rows_removed={removed['STATUS']}")
print(f"component={component_path}")
print(f"css={css_path}")
