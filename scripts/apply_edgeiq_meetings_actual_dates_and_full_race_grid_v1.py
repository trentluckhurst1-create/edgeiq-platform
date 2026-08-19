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

day_button_pattern = re.compile(
    r'''
    <span>\{day\.label\}</span>
    \s*
    <small>\{day\.displayDate\}</small>
    ''',
    re.VERBOSE,
)

component, replacement_count = day_button_pattern.subn(
    "<span>{day.displayDate}</span>",
    component,
    count=1,
)

if replacement_count != 1:
    raise RuntimeError(
        "Expected one Meetings day-button label block, "
        f"found {replacement_count}. No files were written."
    )

if "<span>{day.label}</span>" in component:
    raise RuntimeError(
        "Old TODAY/TOMORROW/DAY +2 label render still remains."
    )

if "<small>{day.displayDate}</small>" in component:
    raise RuntimeError(
        "Duplicated small date render still remains."
    )

css_marker = "/* EDGEIQ MEETINGS ACTUAL DATES AND FULL RACE GRID V1 */"

css_block = r'''

/* EDGEIQ MEETINGS ACTUAL DATES AND FULL RACE GRID V1 */
.eiq-meetings-engineering__days button {
  min-width: 190px;
  min-height: 46px;
  display: flex;
  align-items: center;
  padding: 10px 14px;
}

.eiq-meetings-engineering__days button span {
  font-size: 11px;
  line-height: 1.3;
  white-space: nowrap;
}

.eiq-meetings-engineering__race-strip {
  overflow: visible;
}

.eiq-meetings-engineering__race-list {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  grid-auto-flow: row;
  grid-auto-columns: unset;
  gap: 8px;
  overflow: visible;
  padding: 12px 12px 14px;
}

.eiq-meetings-engineering__race-list article {
  min-width: 0;
  width: 100%;
}

.eiq-meetings-engineering__race-list button {
  min-width: 0;
}

.eiq-meetings-engineering__race-list dl {
  min-width: 0;
}

.eiq-meetings-engineering__race-list dl div {
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 5px;
}

.eiq-meetings-engineering__race-list dt {
  font-size: 9px;
}

.eiq-meetings-engineering__race-list dd {
  min-width: 0;
  font-size: 11px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

@media (max-width: 1250px) {
  .eiq-meetings-engineering__race-list {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .eiq-meetings-engineering__race-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .eiq-meetings-engineering__days {
    width: 100%;
  }

  .eiq-meetings-engineering__days button {
    min-width: 0;
    flex: 1;
  }

  .eiq-meetings-engineering__days button span {
    white-space: normal;
  }
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"

if component == original_component:
    raise RuntimeError("No Meetings component change was produced.")

component_path.write_text(component, encoding="utf-8")
css_path.write_text(css, encoding="utf-8")

print("EDGEIQ_MEETINGS_ACTUAL_DATES_AND_FULL_RACE_GRID_V1_APPLIED")
print("day_tabs=FULL_DAY_AND_DATE")
print("duplicate_day_date_removed=1")
print("race_grid_columns=8")
print("horizontal_race_scroll_removed=1")
print(f"component={component_path}")
print(f"css={css_path}")
