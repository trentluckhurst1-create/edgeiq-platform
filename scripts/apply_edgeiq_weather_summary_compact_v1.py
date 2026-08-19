from pathlib import Path
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

COMPONENT = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingWeatherWorkspace.tsx"
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

# Remove Source and Updated At from arrays that feed the Weather Summary.
patterns = (
    r'^[ \t]*\[\s*["\'`]SOURCE["\'`]\s*,.*?\],[ \t]*\r?\n',
    r'^[ \t]*\[\s*["\'`]UPDATED AT["\'`]\s*,.*?\],[ \t]*\r?\n',
)

removed = 0

for pattern in patterns:
    component, count = re.subn(
        pattern,
        "",
        component,
        count=1,
        flags=re.MULTILINE,
    )
    removed += count

# If the fields are produced inline rather than through an array,
# filter them at the summary-grid rendering point.
if removed < 2:
    map_pattern = re.compile(
        r'''
        \{(?P<expression>[A-Za-z0-9_.]+)\.map\(\(item\)\s*=>\s*\(
        (?P<body>.*?)
        \)\)\}
        ''',
        flags=re.DOTALL | re.VERBOSE,
    )

    candidates = list(map_pattern.finditer(component))

    for match in candidates:
        body = match.group("body")

        if (
            "item.label" not in body
            or "item.value" not in body
            or "eiq-weather" not in component[
                max(0, match.start() - 500):match.start()
            ]
        ):
            continue

        expression = match.group("expression")

        replacement = (
            "{"
            + expression
            + '.filter((item) => !["SOURCE", "UPDATED AT"].includes('
            + "item.label.trim().toUpperCase()"
            + "))"
            + ".map((item) => ("
            + body
            + "))}"
        )

        component = (
            component[:match.start()]
            + replacement
            + component[match.end():]
        )

        removed = 2
        break

if removed < 2:
    raise RuntimeError(
        "Could not safely identify both Source and Updated At fields. "
        "No files were written."
    )

# Validate the visible field definitions are gone.
for forbidden in (
    '["SOURCE",',
    '["UPDATED AT",',
    "['SOURCE',",
    "['UPDATED AT',",
):
    if forbidden in component.upper():
        raise RuntimeError(
            f"Weather Summary field still remains: {forbidden}"
        )

css_marker = "/* EDGEIQ WEATHER SUMMARY COMPACT V1 */"

css_block = r'''

/* EDGEIQ WEATHER SUMMARY COMPACT V1 */
.eiq-weather-v1-summary-grid {
  display: grid !important;
  grid-template-columns: repeat(8, minmax(0, 1fr)) !important;
  width: 100%;
  overflow: visible;
}

.eiq-weather-v1-summary-grid > div {
  min-width: 0;
}

.eiq-weather-v1-summary-grid dt,
.eiq-weather-v1-summary-grid dd {
  white-space: normal;
}

@media (max-width: 1100px) {
  .eiq-weather-v1-summary-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  }
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"

if component == original_component:
    raise RuntimeError("No Weather component change was produced.")

COMPONENT.write_text(component, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")

print("EDGEIQ_WEATHER_SUMMARY_COMPACT_V1_APPLIED")
print("removed=SOURCE")
print("removed=UPDATED_AT")
print("summary_columns=8")
print(f"component={COMPONENT}")
print(f"css={CSS}")
