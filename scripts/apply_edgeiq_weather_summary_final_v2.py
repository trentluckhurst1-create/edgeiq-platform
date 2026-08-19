from pathlib import Path

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

old_render = '''      <SummaryGrid items={model.summary} />
'''

new_render = '''      <SummaryGrid
        items={model.summary.filter(
          (item) =>
            !["SOURCE", "UPDATED AT"].includes(
              item.label.trim().toUpperCase(),
            ),
        )}
      />
'''

count = component.count(old_render)

if count != 1:
    raise RuntimeError(
        f"Expected exactly one Weather Summary render, found {count}. "
        "No files were written."
    )

component = component.replace(
    old_render,
    new_render,
    1,
)

if '<SummaryGrid items={model.summary} />' in component:
    raise RuntimeError(
        "Unfiltered Weather Summary render still remains."
    )

required = (
    'model.summary.filter(',
    '"SOURCE"',
    '"UPDATED AT"',
    'item.label.trim().toUpperCase()',
)

for marker in required:
    if marker not in component:
        raise RuntimeError(
            f"Required Weather Summary rule was not installed: {marker}"
        )

if component == original_component:
    raise RuntimeError(
        "No Weather Summary component change was produced."
    )

css_marker = "/* EDGEIQ WEATHER SUMMARY FINAL V2 */"

css_block = r'''

/* EDGEIQ WEATHER SUMMARY FINAL V2 */
.eiq-weather-v1-summary-grid {
  display: grid !important;
  grid-template-columns: repeat(8, minmax(0, 1fr)) !important;
  width: 100%;
  gap: 0;
  overflow: visible;
}

.eiq-weather-v1-summary-grid > div {
  min-width: 0;
  padding: 16px 12px;
}

.eiq-weather-v1-summary-grid dt {
  font-size: 10px;
  line-height: 1.25;
  white-space: normal;
}

.eiq-weather-v1-summary-grid dd {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.3;
  white-space: normal;
  overflow-wrap: anywhere;
}

@media (max-width: 1050px) {
  .eiq-weather-v1-summary-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  }
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

print("EDGEIQ_WEATHER_SUMMARY_FINAL_V2_APPLIED")
print("removed=SOURCE_CARD")
print("removed=UPDATED_AT_CARD")
print("summary_layout=EIGHT_COLUMNS")
print(f"component={COMPONENT}")
print(f"css={CSS}")
