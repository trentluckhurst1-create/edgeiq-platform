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


def replace_function(
    source: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
    label: str,
) -> str:
    start = source.find(start_marker)

    if start < 0:
        raise RuntimeError(
            f"{label} start marker was not found. No files were written."
        )

    end = source.find(end_marker, start)

    if end < 0:
        raise RuntimeError(
            f"{label} end marker was not found. No files were written."
        )

    return source[:start] + replacement.rstrip() + "\n\n" + source[end:]


# ============================================================
# 1. SUMMARY STRIP — REMOVE AVERAGE FIELD SIZE
# ============================================================

average_line = (
    '    ["Average Field Size", model.summary.averageFieldSize],\n'
)

count = component.count(average_line)

if count != 1:
    raise RuntimeError(
        f"Expected one Average Field Size summary line, found {count}. "
        "No files were written."
    )

component = component.replace(
    average_line,
    "",
    1,
)


# ============================================================
# 2. RESULTS TABLE — NEW USER-FACING COLUMNS AND ACTIONS
# ============================================================

new_meeting_results_table = r'''function internalStewardsReportPath(
  row: MeetingResultsRaceRow,
): string | null {
  const source = (row.race.source ?? {}) as Record<string, unknown>;

  const candidates = [
    source.stewardsReportPath,
    source.stewards_report_path,
    source.stewardsReportUrl,
    source.stewards_report_url,
  ];

  for (const candidate of candidates) {
    if (
      typeof candidate === "string" &&
      candidate.trim().startsWith("/")
    ) {
      return candidate.trim();
    }
  }

  return null;
}

function openInternalStewardsReport(
  path: string,
): void {
  window.open(
    path,
    "_blank",
    "noopener,noreferrer",
  );
}

function OfficialResultsIcon() {
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

function MeetingResultsTable({
  model,
  onSelectRace,
}: {
  model: MeetingResultsViewModel;
  onSelectRace: (raceKey: string) => void;
}) {
  return (
    <section className="eiq-results-v1-panel">
      <header>
        <div>
          <span>Meeting Results</span>
          <strong>Official Results</strong>
          <p>
            Results become available after the official race result
            is received.
          </p>
        </div>
      </header>

      <div className="eiq-results-v1-table-scroll">
        <table className="eiq-results-v1-table eiq-results-v2-meeting-table">
          <thead>
            <tr>
              <th>Race</th>
              <th>Time</th>
              <th className="is-left">Winner</th>
              <th className="is-left">Jockey</th>
              <th className="is-left">Trainer</th>
              <th>SP</th>
              <th>Margin</th>
              <th>Official Time</th>
              <th>Track</th>
              <th>Stewards Report</th>
              <th aria-label="Official Results">Results</th>
            </tr>
          </thead>

          <tbody>
            {model.rows.map((row) => {
              const reportPath = internalStewardsReportPath(row);
              const resultAvailable =
                row.status === "OFFICIAL" ||
                row.status === "UNOFFICIAL";

              return (
                <tr key={row.raceKey}>
                  <td>R{row.raceNumber}</td>
                  <td>{valueOrPending(row.time)}</td>
                  <td className="is-left">
                    {valueOrPending(row.winner)}
                  </td>
                  <td className="is-left">
                    {valueOrPending(row.jockey)}
                  </td>
                  <td className="is-left">
                    {valueOrPending(row.trainer)}
                  </td>
                  <td>{valueOrPending(row.spTab)}</td>
                  <td>{valueOrPending(row.margin)}</td>
                  <td>{valueOrPending(row.officialTime)}</td>
                  <td>{valueOrPending(row.track)}</td>

                  <td>
                    <button
                      type="button"
                      className="eiq-results-v2-stewards-button"
                      disabled={!reportPath}
                      title={
                        reportPath
                          ? "Open Stewards Report"
                          : "Available after official publication"
                      }
                      onClick={() => {
                        if (reportPath) {
                          openInternalStewardsReport(reportPath);
                        }
                      }}
                    >
                      Stewards Report
                    </button>
                  </td>

                  <td>
                    <button
                      type="button"
                      className="eiq-results-v2-details-button"
                      aria-label={`Open official results for race ${row.raceNumber}`}
                      title={
                        resultAvailable
                          ? "Official Results"
                          : "Result pending"
                      }
                      disabled={!resultAvailable}
                      onClick={() => onSelectRace(row.raceKey)}
                    >
                      <OfficialResultsIcon />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}'''

component = replace_function(
    component,
    "function MeetingResultsTable(",
    "function SignedValue(",
    new_meeting_results_table,
    "MeetingResultsTable",
)


# ============================================================
# 3. RESULT SNAPSHOT — REMOVE SOURCE METADATA
# ============================================================

old_snapshot_map = '''      {result.snapshot.map((item) => (
        <div key={item.label}>
          <span>{item.label}</span>
          <strong>{valueOrPending(item.value, "Unavailable")}</strong>
        </div>
      ))}
'''

new_snapshot_map = '''      {result.snapshot
        .filter(
          (item) =>
            !["RESULT SOURCE", "SOURCE TIMESTAMP"].includes(
              item.label.trim().toUpperCase(),
            ),
        )
        .map((item) => (
          <div key={item.label}>
            <span>{item.label}</span>
            <strong>
              {valueOrPending(item.value, "Unavailable")}
            </strong>
          </div>
        ))}
'''

count = component.count(old_snapshot_map)

if count != 1:
    raise RuntimeError(
        f"Expected one ResultSnapshot map, found {count}. "
        "No files were written."
    )

component = component.replace(
    old_snapshot_map,
    new_snapshot_map,
    1,
)


# ============================================================
# 4. REMOVE INLINE STEWARDS COMMENTS COMPONENT
# ============================================================

stewards_start = component.find(
    "function StewardsReport("
)

individual_start = component.find(
    "function IndividualRaceResult(",
    stewards_start,
)

if stewards_start < 0 or individual_start < 0:
    raise RuntimeError(
        "Could not isolate StewardsReport function. "
        "No files were written."
    )

component = (
    component[:stewards_start]
    + component[individual_start:]
)


# ============================================================
# 5. REPLACE INDIVIDUAL RESULT PAGE WITH A MODAL
# ============================================================

new_individual_result = r'''function IndividualRaceResult({
  meeting,
  raceRow,
  fixtureMode,
  onClose,
}: {
  meeting: ThreeDayMeeting;
  raceRow: MeetingResultsRaceRow;
  fixtureMode: boolean;
  onClose: () => void;
}) {
  const result = useMemo(
    () =>
      buildIndividualRaceResultViewModel(
        meeting,
        raceRow,
        { fixtureMode },
      ),
    [fixtureMode, meeting, raceRow],
  );

  const reportPath = internalStewardsReportPath(raceRow);

  return (
    <div
      className="eiq-results-v2-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target) {
          onClose();
        }
      }}
    >
      <section
        className="eiq-results-v2-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`${result.raceLabel} Official Results`}
      >
        <header className="eiq-results-v2-modal-header">
          <div>
            <span>Official Results</span>
            <h2>
              {result.raceLabel} - {result.raceName}
            </h2>
            <p>
              {result.identity
                .filter(
                  (item) =>
                    !["FIELD"].includes(
                      item.label.trim().toUpperCase(),
                    ),
                )
                .map(
                  (item) =>
                    `${item.label}: ${valueOrPending(
                      item.value,
                      "Unavailable",
                    )}`,
                )
                .join(" / ")}
            </p>
          </div>

          <button
            type="button"
            className="eiq-results-v2-modal-close-icon"
            aria-label="Close Official Results"
            onClick={onClose}
          >
            ×
          </button>
        </header>

        <div className="eiq-results-v2-modal-body">
          <ResultSnapshot result={result} />
          <FinishingOrder result={result} />
          <RunnerPerformance result={result} />
        </div>

        <footer className="eiq-results-v2-modal-footer">
          <button
            type="button"
            className="eiq-results-v2-stewards-button"
            disabled={!reportPath}
            title={
              reportPath
                ? "Open Stewards Report"
                : "Available after official publication"
            }
            onClick={() => {
              if (reportPath) {
                openInternalStewardsReport(reportPath);
              }
            }}
          >
            Stewards Report
          </button>

          <button
            type="button"
            className="eiq-results-v2-close-button"
            onClick={onClose}
          >
            Close
          </button>
        </footer>
      </section>
    </div>
  );
}'''

component = replace_function(
    component,
    "function IndividualRaceResult(",
    "function DataStatusPanel(",
    new_individual_result,
    "IndividualRaceResult",
)


# ============================================================
# 6. REMOVE DATA STATUS FUNCTION
# ============================================================

data_status_start = component.find(
    "function DataStatusPanel("
)

workspace_start = component.find(
    "export function MeetingResultsWorkspace(",
    data_status_start,
)

if data_status_start < 0 or workspace_start < 0:
    raise RuntimeError(
        "Could not isolate DataStatusPanel function. "
        "No files were written."
    )

component = (
    component[:data_status_start]
    + component[workspace_start:]
)


# ============================================================
# 7. CLEAN HEADER
# ============================================================

old_header = '''      <header className="eiq-results-v1-header">
        <div>
          <span>RESULTS</span>
          <h2>Official results and governed performance</h2>
          <p>{meeting.meeting} / {meeting.date}</p>
        </div>
      </header>
'''

new_header = '''      <header className="eiq-results-v1-header">
        <div>
          <span>RESULTS</span>
          <h2>Official Results</h2>
        </div>
      </header>
'''

count = component.count(old_header)

if count != 1:
    raise RuntimeError(
        f"Expected one Results workspace header, found {count}. "
        "No files were written."
    )

component = component.replace(
    old_header,
    new_header,
    1,
)


# ============================================================
# 8. TABLE ALWAYS REMAINS VISIBLE; MODAL OPENS ABOVE IT
# ============================================================

old_conditional = '''      {selectedResultRace ? (
        <IndividualRaceResult
          meeting={meeting}
          raceRow={selectedResultRace}
          fixtureMode={fixtureMode}
          onBack={() => setResultRaceKey(null)}
        />
      ) : (
        <>
          <SummaryStrip model={model} />
          <MeetingResultsTable model={model} selectedRaceKey={resultRaceKey} onSelectRace={setResultRaceKey} />
          <DataStatusPanel model={model} />
        </>
      )}
'''

new_conditional = '''      <SummaryStrip model={model} />

      <MeetingResultsTable
        model={model}
        onSelectRace={setResultRaceKey}
      />

      {selectedResultRace ? (
        <IndividualRaceResult
          meeting={meeting}
          raceRow={selectedResultRace}
          fixtureMode={fixtureMode}
          onClose={() => setResultRaceKey(null)}
        />
      ) : null}
'''

count = component.count(old_conditional)

if count != 1:
    raise RuntimeError(
        f"Expected one old Results conditional render, found {count}. "
        "No files were written."
    )

component = component.replace(
    old_conditional,
    new_conditional,
    1,
)


# ============================================================
# 9. VALIDATE COMPONENT BEFORE WRITING
# ============================================================

for forbidden in (
    "Average Field Size",
    "<th>Status</th>",
    "<th>Open</th>",
    "function DataStatusPanel(",
    "<DataStatusPanel",
    "function StewardsReport(",
    "<StewardsReport",
    "onBack=",
    "Official results and governed performance",
):
    if forbidden in component:
        raise RuntimeError(
            f"Old Results content still remains: {forbidden}"
        )

for required in (
    "internalStewardsReportPath(",
    "OfficialResultsIcon",
    "eiq-results-v2-modal-backdrop",
    "eiq-results-v2-stewards-button",
    "eiq-results-v2-details-button",
    "<th>Official Time</th>",
    "<th>Stewards Report</th>",
    'aria-label="Official Results"',
    "Pending speed data",
):
    if required not in component:
        raise RuntimeError(
            f"Required Results V2 content was not installed: {required}"
        )

if component == original_component:
    raise RuntimeError(
        "No Results workspace changes were produced."
    )


# ============================================================
# 10. RESULTS V2 CSS
# ============================================================

css_marker = "/* EDGEIQ RESULTS WORKSPACE V2 */"

css_block = r'''

/* EDGEIQ RESULTS WORKSPACE V2 */
.eiq-results-v1-summary-strip {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
}

.eiq-results-v1-table-scroll {
  width: 100%;
  overflow-x: auto;
}

.eiq-results-v2-meeting-table {
  width: 100%;
  min-width: 1180px;
  table-layout: fixed;
}

.eiq-results-v2-meeting-table th,
.eiq-results-v2-meeting-table td {
  padding: 12px 9px;
  vertical-align: middle;
}

.eiq-results-v2-meeting-table th:nth-child(1),
.eiq-results-v2-meeting-table td:nth-child(1) {
  width: 5%;
}

.eiq-results-v2-meeting-table th:nth-child(2),
.eiq-results-v2-meeting-table td:nth-child(2) {
  width: 7%;
}

.eiq-results-v2-meeting-table th:nth-child(3),
.eiq-results-v2-meeting-table td:nth-child(3) {
  width: 13%;
}

.eiq-results-v2-meeting-table th:nth-child(4),
.eiq-results-v2-meeting-table td:nth-child(4),
.eiq-results-v2-meeting-table th:nth-child(5),
.eiq-results-v2-meeting-table td:nth-child(5) {
  width: 12%;
}

.eiq-results-v2-meeting-table th:nth-child(6),
.eiq-results-v2-meeting-table td:nth-child(6),
.eiq-results-v2-meeting-table th:nth-child(7),
.eiq-results-v2-meeting-table td:nth-child(7) {
  width: 7%;
}

.eiq-results-v2-meeting-table th:nth-child(8),
.eiq-results-v2-meeting-table td:nth-child(8) {
  width: 9%;
}

.eiq-results-v2-meeting-table th:nth-child(9),
.eiq-results-v2-meeting-table td:nth-child(9) {
  width: 10%;
}

.eiq-results-v2-meeting-table th:nth-child(10),
.eiq-results-v2-meeting-table td:nth-child(10) {
  width: 11%;
}

.eiq-results-v2-meeting-table th:nth-child(11),
.eiq-results-v2-meeting-table td:nth-child(11) {
  width: 7%;
}

.eiq-results-v2-stewards-button {
  min-height: 32px;
  padding: 7px 10px;
  border: 1px solid #173f8f;
  border-radius: 4px;
  background: #ffffff;
  color: #173f8f;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
  cursor: pointer;
}

.eiq-results-v2-stewards-button:disabled {
  border-color: #cbd3e0;
  background: #f5f7fa;
  color: #9aa4b3;
  cursor: not-allowed;
}

.eiq-results-v2-details-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 32px;
  padding: 0;
  border: 1px solid #173f8f;
  border-radius: 4px;
  background: #173f8f;
  color: #ffffff;
  cursor: pointer;
}

.eiq-results-v2-details-button svg {
  width: 17px;
  height: 17px;
}

.eiq-results-v2-details-button:disabled {
  border-color: #cbd3e0;
  background: #e8ecf2;
  color: #9aa4b3;
  cursor: not-allowed;
}

.eiq-results-v2-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px;
  overflow-y: auto;
  background: rgba(12, 24, 47, 0.52);
  backdrop-filter: blur(5px);
}

.eiq-results-v2-modal {
  width: min(1500px, 96vw);
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  border: 1px solid #cfd7e5;
  border-radius: 8px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 24px 80px rgba(7, 21, 46, 0.28);
}

.eiq-results-v2-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 22px;
  border-bottom: 1px solid #dfe5ef;
  background: #ffffff;
}

.eiq-results-v2-modal-header span {
  color: #173f8f;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.eiq-results-v2-modal-header h2 {
  margin: 5px 0 0;
  color: #172033;
  font-size: 18px;
  font-weight: 700;
}

.eiq-results-v2-modal-header p {
  margin: 7px 0 0;
  color: #6f7a8d;
  font-size: 11px;
}

.eiq-results-v2-modal-close-icon {
  width: 34px;
  height: 34px;
  border: 1px solid #cfd7e5;
  border-radius: 4px;
  background: #ffffff;
  color: #172033;
  font-size: 23px;
  line-height: 1;
  cursor: pointer;
}

.eiq-results-v2-modal-body {
  min-height: 0;
  padding: 16px;
  overflow-y: auto;
  background: #f5f7fa;
}

.eiq-results-v2-modal-body > * + * {
  margin-top: 14px;
}

.eiq-results-v2-modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 18px;
  border-top: 1px solid #dfe5ef;
  background: #ffffff;
}

.eiq-results-v2-close-button {
  min-width: 90px;
  min-height: 34px;
  padding: 7px 16px;
  border: 1px solid #173f8f;
  border-radius: 4px;
  background: #173f8f;
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.eiq-results-v2-modal .eiq-results-v1-snapshot {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.eiq-results-v2-modal .eiq-results-v1-table {
  min-width: 960px;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"


# Write only after all validation passes.
COMPONENT.write_text(
    component,
    encoding="utf-8",
)

CSS.write_text(
    css,
    encoding="utf-8",
)

print("EDGEIQ_RESULTS_WORKSPACE_V2_APPLIED")
print("removed=AVERAGE_FIELD_SIZE")
print("removed=STATUS_COLUMN")
print("removed=OPEN_COLUMN")
print("removed=DATA_STATUS_PANEL")
print("removed=INLINE_STEWARDS_COMMENTS")
print("added=INTERNAL_STEWARDS_REPORT_BUTTON")
print("added=OFFICIAL_RESULTS_ICON")
print("added=OFFICIAL_RESULTS_MODAL")
print("ratings=CANONICAL_DATA_ONLY")
print(f"component={COMPONENT}")
print(f"css={CSS}")
