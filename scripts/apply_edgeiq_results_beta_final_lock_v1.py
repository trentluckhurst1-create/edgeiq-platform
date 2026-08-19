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
# 1. ADD TABLE-SPECIFIC DASH FORMATTER
# ============================================================

time_function_marker = '''function formatRaceTime(
  value: string | number | null | undefined,
): string {
'''

dash_function = '''function valueOrDash(
  value: string | number | null | undefined,
): string {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    String(value).trim().toLowerCase() === "pending"
  ) {
    return "—";
  }

  return String(value);
}

'''

if "function valueOrDash(" not in component:
    position = component.find(time_function_marker)

    if position < 0:
        raise RuntimeError(
            "formatRaceTime function was not found. "
            "No files were written."
        )

    component = (
        component[:position]
        + dash_function
        + component[position:]
    )


# ============================================================
# 2. REMOVE REMAINING SUMMARY CARD
# ============================================================

remaining_line = (
    '    ["Remaining", model.summary.pendingResults],\n'
)

component = replace_once(
    component,
    remaining_line,
    "",
    "Remaining summary card",
)


# ============================================================
# 3. CHANGE WORKSPACE HEADING
# ============================================================

component = replace_once(
    component,
    "          <h2>Official Results</h2>",
    "          <h2>Meeting Results</h2>",
    "Results workspace heading",
)


# ============================================================
# 4. REPLACE CLUTTERED PENDING VALUES WITH DASHES
# ============================================================

table_replacements = (
    (
        "                    {valueOrPending(row.winner)}",
        "                    {valueOrDash(row.winner)}",
        "Winner dash display",
    ),
    (
        "                    {valueOrPending(row.jockey)}",
        "                    {valueOrDash(row.jockey)}",
        "Jockey dash display",
    ),
    (
        "                    {valueOrPending(row.trainer)}",
        "                    {valueOrDash(row.trainer)}",
        "Trainer dash display",
    ),
    (
        "                  <td>{valueOrPending(row.spTab)}</td>",
        "                  <td>{valueOrDash(row.spTab)}</td>",
        "SP dash display",
    ),
    (
        "                  <td>{valueOrPending(row.margin)}</td>",
        "                  <td>{valueOrDash(row.margin)}</td>",
        "Margin dash display",
    ),
    (
        "                  <td>{valueOrPending(row.officialTime)}</td>",
        "                  <td>{valueOrDash(row.officialTime)}</td>",
        "Official Time dash display",
    ),
    (
        "                  <td>{valueOrPending(row.track)}</td>",
        "                  <td>{valueOrDash(row.track)}</td>",
        "Track dash display",
    ),
)

for old, new, label in table_replacements:
    component = replace_once(
        component,
        old,
        new,
        label,
    )


# ============================================================
# 5. CHANGE STEWARDS BUTTON TEXT TO REPORT
# ============================================================

report_button_text = '''                    >
                      Stewards Report
                    </button>
'''

compact_report_text = '''                    >
                      Report
                    </button>
'''

component = replace_once(
    component,
    report_button_text,
    compact_report_text,
    "Meeting-table Report button",
)

modal_report_text = '''          >
            Stewards Report
          </button>
'''

compact_modal_report_text = '''          >
            Report
          </button>
'''

component = replace_once(
    component,
    modal_report_text,
    compact_modal_report_text,
    "Modal Report button",
)


# ============================================================
# 6. REPLACE FINISHING FLAG WITH CLIPBOARD ICON
# ============================================================

icon_start = component.find(
    "function OfficialResultsIcon() {"
)

next_function = component.find(
    "function MeetingResultsTable(",
    icon_start,
)

if icon_start < 0 or next_function < 0:
    raise RuntimeError(
        "OfficialResultsIcon function could not be isolated. "
        "No files were written."
    )

clipboard_icon = '''function OfficialResultsIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M8.25 5.25H6.5A1.5 1.5 0 0 0 5 6.75v12A1.5 1.5 0 0 0 6.5 20.25h11a1.5 1.5 0 0 0 1.5-1.5v-12a1.5 1.5 0 0 0-1.5-1.5h-1.75"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M9 3.75h6a.75.75 0 0 1 .75.75v2.25H8.25V4.5A.75.75 0 0 1 9 3.75Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M8.5 11h7M8.5 14.5h7M8.5 18h4.25"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

'''

component = (
    component[:icon_start]
    + clipboard_icon
    + component[next_function:]
)


# ============================================================
# 7. VALIDATE COMPONENT
# ============================================================

required_markers = (
    "function valueOrDash(",
    'return "—";',
    "<h2>Meeting Results</h2>",
    "{valueOrDash(row.winner)}",
    "{valueOrDash(row.officialTime)}",
    "{valueOrDash(row.track)}",
    "M8.25 5.25H6.5",
    "<th>Stewards</th>",
    "<th aria-label=\"Official Results\">Details</th>",
)

for marker in required_markers:
    if marker not in component:
        raise RuntimeError(
            f"Required Results beta lock was not installed: {marker}"
        )

for forbidden in (
    '["Remaining", model.summary.pendingResults]',
    "<h2>Official Results</h2>",
    "{valueOrPending(row.winner)}",
    "{valueOrPending(row.officialTime)}",
    "{valueOrPending(row.track)}",
):
    if forbidden in component:
        raise RuntimeError(
            f"Old Results display still remains: {forbidden}"
        )

if component == original_component:
    raise RuntimeError(
        "No Results component changes were produced."
    )


# ============================================================
# 8. FINAL BETA CSS
# ============================================================

css_marker = "/* EDGEIQ RESULTS BETA FINAL LOCK V1 */"

css_block = r'''

/* EDGEIQ RESULTS BETA FINAL LOCK V1 */
.eiq-results-v1-summary-strip {
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
}

.eiq-results-v2-meeting-table th,
.eiq-results-v2-meeting-table td {
  vertical-align: middle;
}

.eiq-results-v2-meeting-table td:nth-child(3),
.eiq-results-v2-meeting-table td:nth-child(4),
.eiq-results-v2-meeting-table td:nth-child(5) {
  text-align: left;
}

.eiq-results-v2-meeting-table td:nth-child(6),
.eiq-results-v2-meeting-table td:nth-child(7),
.eiq-results-v2-meeting-table td:nth-child(8),
.eiq-results-v2-meeting-table td:nth-child(9) {
  color: #5f6a7d;
}

.eiq-results-v2-stewards-button {
  width: auto !important;
  min-width: 62px !important;
  min-height: 26px !important;
  padding: 4px 9px !important;
  border-color: #5d83d7 !important;
  background: #ffffff !important;
  color: #2456b8 !important;
  font-size: 9px !important;
  line-height: 1 !important;
  white-space: nowrap !important;
}

.eiq-results-v2-stewards-button:disabled {
  border-color: #d2d8e2 !important;
  background: #f8f9fb !important;
  color: #9da7b6 !important;
}

.eiq-results-v2-details-button {
  width: 29px !important;
  height: 28px !important;
  min-width: 29px !important;
  border-color: #5d83d7 !important;
  background: #ffffff !important;
  color: #2456b8 !important;
}

.eiq-results-v2-details-button:hover:not(:disabled) {
  background: #eef4ff !important;
}

.eiq-results-v2-details-button:disabled {
  border-color: #d2d8e2 !important;
  background: #f3f5f8 !important;
  color: #a5afbd !important;
}

.eiq-results-v2-details-button svg {
  width: 15px !important;
  height: 15px !important;
}

.eiq-results-v2-meeting-table th:nth-child(10),
.eiq-results-v2-meeting-table td:nth-child(10) {
  width: 8.5% !important;
}

.eiq-results-v2-meeting-table th:nth-child(11),
.eiq-results-v2-meeting-table td:nth-child(11) {
  width: 5.5% !important;
}

.eiq-results-v2-modal .eiq-results-v2-stewards-button {
  min-width: 80px !important;
  min-height: 32px !important;
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

print("EDGEIQ_RESULTS_BETA_FINAL_LOCK_V1_APPLIED")
print("heading=MEETING_RESULTS")
print("summary=COMPLETED_AND_OFFICIAL")
print("pending_values=DASH")
print("stewards_button=COMPACT_REPORT")
print("details_icon=CLIPBOARD")
print("modal=PRESERVED")
print(f"component={COMPONENT}")
print(f"css={CSS}")
