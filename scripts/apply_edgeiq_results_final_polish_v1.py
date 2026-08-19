from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

COMPONENT = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingResultsWorkspace.tsx"
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


def replace_once(
    source: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = source.count(old)

    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one match, found {count}. "
            "No files were written."
        )

    return source.replace(old, new, 1)


# ============================================================
# 1. INSTALL MELBOURNE RACE-TIME FORMATTER
# ============================================================

value_function = '''function valueOrPending(value: string | number | null | undefined, pending = "Pending"): string {
  if (value === null || value === undefined || value === "") return pending;
  return String(value);
}
'''

value_function_with_time = '''function valueOrPending(value: string | number | null | undefined, pending = "Pending"): string {
  if (value === null || value === undefined || value === "") return pending;
  return String(value);
}

function formatRaceTime(
  value: string | number | null | undefined,
): string {
  if (value === null || value === undefined || value === "") {
    return "Pending";
  }

  const text = String(value).trim();

  const simpleTime = text.match(
    /^(\\d{1,2}):(\\d{2})(?::\\d{2})?\\s*(am|pm)?$/i,
  );

  if (simpleTime) {
    let hour = Number(simpleTime[1]);
    const minute = simpleTime[2];
    const suffix = simpleTime[3]?.toLowerCase();

    if (suffix) {
      return `${hour}:${minute}${suffix}`;
    }

    const period = hour >= 12 ? "pm" : "am";
    hour %= 12;

    if (hour === 0) {
      hour = 12;
    }

    return `${hour}:${minute}${period}`;
  }

  const parsed = new Date(text);

  if (Number.isNaN(parsed.getTime())) {
    return text;
  }

  return new Intl.DateTimeFormat("en-AU", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Australia/Melbourne",
  })
    .format(parsed)
    .replace(/\\s/g, "")
    .toLowerCase();
}
'''

component = replace_once(
    component,
    value_function,
    value_function_with_time,
    "Race-time formatter installation",
)


# ============================================================
# 2. SHORTEN SUMMARY LABELS
# ============================================================

component = replace_once(
    component,
    '    ["Races Completed", model.summary.racesCompleted],',
    '    ["Completed", model.summary.racesCompleted],',
    "Completed summary label",
)

component = replace_once(
    component,
    '    ["Official Results", model.summary.officialResults],',
    '    ["Official", model.summary.officialResults],',
    "Official summary label",
)

component = replace_once(
    component,
    '    ["Upcoming Races", model.summary.pendingResults],',
    '    ["Remaining", model.summary.pendingResults],',
    "Remaining summary label",
)


# ============================================================
# 3. FORMAT RACE NUMBER AND SCHEDULED TIME
# ============================================================

component = replace_once(
    component,
    "                  <td>R{row.raceNumber}</td>",
    "                  <td>{row.raceNumber}</td>",
    "Race-number display",
)

component = replace_once(
    component,
    "                  <td>{valueOrPending(row.time)}</td>",
    "                  <td>{formatRaceTime(row.time)}</td>",
    "Scheduled-time display",
)


# ============================================================
# 4. SHORTEN TABLE HEADINGS
# ============================================================

component = replace_once(
    component,
    "              <th>Stewards Report</th>",
    "              <th>Stewards</th>",
    "Stewards heading",
)

component = replace_once(
    component,
    '              <th aria-label="Official Results">Results</th>',
    '              <th aria-label="Official Results">Details</th>',
    "Details heading",
)


# ============================================================
# 5. REPLACE GENERIC DOCUMENT ICON WITH FINISHING FLAG
# ============================================================

old_icon = '''function OfficialResultsIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M5 3.75h10.5L19 7.25v13H5v-16.5Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M15.5 3.75v3.5H19M8 11h8M8 14.5h8M8 18h5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
'''

new_icon = '''function OfficialResultsIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M5.5 20.25V3.75"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M6 4.5h11.5l-2.25 3.25L17.5 11H6Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path
        d="M9 4.5v6.5M13 4.5v6.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeDasharray="2 2"
      />
    </svg>
  );
}
'''

component = replace_once(
    component,
    old_icon,
    new_icon,
    "Official Results icon",
)


# ============================================================
# 6. VALIDATE COMPONENT BEFORE WRITING
# ============================================================

required_markers = (
    "function formatRaceTime(",
    'timeZone: "Australia/Melbourne"',
    '["Completed", model.summary.racesCompleted]',
    '["Official", model.summary.officialResults]',
    '["Remaining", model.summary.pendingResults]',
    "<td>{row.raceNumber}</td>",
    "<td>{formatRaceTime(row.time)}</td>",
    "<th>Stewards</th>",
    'aria-label="Official Results">Details</th>',
)

for marker in required_markers:
    if marker not in component:
        raise RuntimeError(
            f"Required Results polish was not installed: {marker}"
        )

for forbidden in (
    '["Races Completed",',
    '["Official Results", model.summary.officialResults]',
    '["Upcoming Races",',
    "<td>R{row.raceNumber}</td>",
    "<td>{valueOrPending(row.time)}</td>",
    "<th>Stewards Report</th>",
):
    if forbidden in component:
        raise RuntimeError(
            f"Old Results display content still remains: {forbidden}"
        )

if component == original_component:
    raise RuntimeError(
        "No Results component changes were produced."
    )


# ============================================================
# 7. FINAL FIT-TO-SCREEN CSS
# ============================================================

css_marker = "/* EDGEIQ RESULTS FINAL POLISH V1 */"

css_block = r'''

/* EDGEIQ RESULTS FINAL POLISH V1 */
.eiq-results-v1-table-scroll {
  width: 100%;
  overflow-x: visible !important;
}

.eiq-results-v2-meeting-table {
  width: 100% !important;
  min-width: 0 !important;
  table-layout: fixed !important;
}

.eiq-results-v2-meeting-table th,
.eiq-results-v2-meeting-table td {
  min-width: 0;
  padding: 11px 7px !important;
  font-size: 11px;
  line-height: 1.3;
  white-space: normal;
  overflow-wrap: anywhere;
}

.eiq-results-v2-meeting-table th {
  font-size: 9px;
  letter-spacing: 0.05em;
}

.eiq-results-v2-meeting-table th:nth-child(1),
.eiq-results-v2-meeting-table td:nth-child(1) {
  width: 4.5% !important;
}

.eiq-results-v2-meeting-table th:nth-child(2),
.eiq-results-v2-meeting-table td:nth-child(2) {
  width: 7% !important;
  white-space: nowrap;
}

.eiq-results-v2-meeting-table th:nth-child(3),
.eiq-results-v2-meeting-table td:nth-child(3) {
  width: 13% !important;
  text-align: left;
}

.eiq-results-v2-meeting-table th:nth-child(4),
.eiq-results-v2-meeting-table td:nth-child(4) {
  width: 12% !important;
  text-align: left;
}

.eiq-results-v2-meeting-table th:nth-child(5),
.eiq-results-v2-meeting-table td:nth-child(5) {
  width: 13% !important;
  text-align: left;
}

.eiq-results-v2-meeting-table th:nth-child(6),
.eiq-results-v2-meeting-table td:nth-child(6) {
  width: 6% !important;
}

.eiq-results-v2-meeting-table th:nth-child(7),
.eiq-results-v2-meeting-table td:nth-child(7) {
  width: 7% !important;
}

.eiq-results-v2-meeting-table th:nth-child(8),
.eiq-results-v2-meeting-table td:nth-child(8) {
  width: 9% !important;
}

.eiq-results-v2-meeting-table th:nth-child(9),
.eiq-results-v2-meeting-table td:nth-child(9) {
  width: 10% !important;
}

.eiq-results-v2-meeting-table th:nth-child(10),
.eiq-results-v2-meeting-table td:nth-child(10) {
  width: 11.5% !important;
}

.eiq-results-v2-meeting-table th:nth-child(11),
.eiq-results-v2-meeting-table td:nth-child(11) {
  width: 7% !important;
}

.eiq-results-v2-stewards-button {
  width: 100%;
  min-width: 0 !important;
  min-height: 30px;
  padding: 6px 5px !important;
  font-size: 9px !important;
  line-height: 1.15;
  white-space: normal !important;
}

.eiq-results-v2-details-button {
  width: 31px !important;
  height: 30px !important;
  min-width: 31px;
}

.eiq-results-v2-details-button svg {
  width: 16px;
  height: 16px;
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

print("EDGEIQ_RESULTS_FINAL_POLISH_V1_APPLIED")
print("time=MELBOURNE_LOCAL_FORMAT")
print("race_number=NUMERIC_ONLY")
print("summary=COMPLETED_OFFICIAL_REMAINING")
print("heading=STEWARDS")
print("icon=FINISHING_FLAG")
print("layout=FIT_TO_SCREEN")
print(f"component={COMPONENT}")
print(f"css={CSS}")
