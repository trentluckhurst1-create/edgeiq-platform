import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting } from "../services/threeDayCatalog";
import {
  buildIndividualRaceResultViewModel,
  buildMeetingResultsViewModel,
  loadResultsTerminalFeed,
  type IndividualRaceResultViewModel,
  type MeetingResultsRaceRow,
  type MeetingResultsViewModel,
  type ResultsTerminalRow,
} from "../services/resultsFeed";

type MeetingResultsWorkspaceProps = {
  meeting: ThreeDayMeeting;
};

function valueOrPending(value: string | number | null | undefined, pending = "Pending"): string {
  if (value === null || value === undefined || value === "") return pending;
  return String(value);
}

function valueOrDash(
  value: string | number | null | undefined,
): string {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    String(value).trim().toLowerCase() === "pending"
  ) {
    return "-";
  }

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
    /^(\d{1,2}):(\d{2})(?::\d{2})?\s*(am|pm)?$/i,
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
    .replace(/\s/g, "")
    .toLowerCase();
}

function SummaryStrip({ model }: { model: MeetingResultsViewModel }) {
  const summary = [
    ["Completed", model.summary.racesCompleted],
    ["Resulted", model.summary.officialResults],
  ];

  return (
    <section className="eiq-results-v1-summary-strip" aria-label="Results summary">
      {summary.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{valueOrPending(value, "Unavailable")}</strong>
        </div>
      ))}
    </section>
  );
}

function internalStewardsReportPath(
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
          <strong>Results</strong>
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
              <th>Track</th>
              <th>Stewards</th>
              <th aria-label="Official Results">Details</th>
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
                  <td>{row.raceNumber}</td>
                  <td>{formatRaceTime(row.time)}</td>
                  <td className="is-left">
                    {valueOrDash(row.winner)}
                  </td>
                  <td className="is-left">
                    {valueOrDash(row.jockey)}
                  </td>
                  <td className="is-left">
                    {valueOrDash(row.trainer)}
                  </td>
                  <td>{valueOrDash(row.spTab)}</td>
                  <td>{valueOrDash(row.margin)}</td>
                  <td>{valueOrDash(row.track)}</td>

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
                      Report
                    </button>
                  </td>

                  <td>
                    <button
                      type="button"
                      className="eiq-results-v2-details-button"
                      aria-label={`Open results for race ${row.raceNumber}`}
                      title={
                        resultAvailable
                          ? "Results"
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
}

function SignedValue({ value }: { value: string | null }) {
  const SECTIONAL_TONE_CLASSES = ["is-negative", "is-positive", "is-neutral"] as const;
  if (!value) return <span>-</span>;
  const number = Number(String(value).replace(/[^\d.-]/g, ""));
  const tone = Number.isFinite(number) ? (number < 0 ? "negative" : number > 0 ? "positive" : "neutral") : "neutral";
  void SECTIONAL_TONE_CLASSES;
  return <span className={`eiq-results-v1-sectional is-${tone}`}>{value}</span>;
}

function ResultSnapshot({ result }: { result: IndividualRaceResultViewModel }) {
  return (
    <section className="eiq-results-v1-snapshot">
      {result.snapshot
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
    </section>
  );
}

function FinishingOrder({ result }: { result: IndividualRaceResultViewModel }) {
  return (
    <section className="eiq-results-v1-panel">
      <header>
        <div>
          <span>Finishing Order</span>
          <strong>{result.raceLabel} result</strong>
        </div>
      </header>
      <div className="eiq-results-v1-table-scroll">
        <table className="eiq-results-v1-table is-compact">
          <thead>
            <tr>
              <th>Pos</th>
              <th>No</th>
              <th className="is-left">Horse</th>
              <th className="is-left">Jockey</th>
              <th className="is-left">Trainer</th>
              <th>SP (TAB)</th>
              <th>Margin</th>
            </tr>
          </thead>
          <tbody>
            {result.runners.map((runner) => (
              <tr key={runner.key}>
                <td>{valueOrPending(runner.finish)}</td>
                <td>{valueOrPending(runner.no, "")}</td>
                <td className="is-left">
                  <strong>{runner.horse}</strong>
                </td>
                <td className="is-left">{valueOrPending(runner.jockey)}</td>
                <td className="is-left">{valueOrPending(runner.trainer)}</td>
                <td>{valueOrPending(runner.sp)}</td>
                <td>{valueOrPending(runner.margin)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function RunnerPerformance({ result }: { result: IndividualRaceResultViewModel }) {
  return (
    <section className="eiq-results-v1-panel is-runner-performance">
      <header>
        <div>
          <span>Runner Performance</span>
          <strong>Runner performance</strong>
          <p>Sectional values are EDGEiQ lengths versus standard. Negative is inside standard; positive is outside standard.</p>
        </div>
      </header>
      <div className="eiq-results-v1-table-scroll">
        <table className="eiq-results-v1-table">
          <thead>
            <tr>
              <th>No</th>
              <th className="is-left">Horse</th>
              <th className="is-left">Jockey</th>
              <th>Bar</th>
              <th>Wt</th>
              <th>SP</th>
              <th>Finish</th>
              <th>Margin</th>
              <th>800m</th>
              <th>600m</th>
              <th>400m</th>
              <th>200m</th>
              <th>Finish</th>
              <th>EPI</th>
              <th>ERI</th>
            </tr>
          </thead>
          <tbody>
            {result.runners.map((runner) => (
              <tr key={`${runner.key}-performance`}>
                <td>{valueOrPending(runner.no, "")}</td>
                <td className="is-left"><strong>{runner.horse}</strong></td>
                <td className="is-left">{valueOrPending(runner.jockey)}</td>
                <td>{valueOrPending(runner.barrier, "")}</td>
                <td>{valueOrPending(runner.weight, "")}</td>
                <td>{valueOrPending(runner.sp)}</td>
                <td>{valueOrPending(runner.finish)}</td>
                <td>{valueOrPending(runner.margin)}</td>
                <td><SignedValue value={runner.sectional800} /></td>
                <td><SignedValue value={runner.sectional600} /></td>
                <td><SignedValue value={runner.sectional400} /></td>
                <td><SignedValue value={runner.sectional200} /></td>
                <td><SignedValue value={runner.sectionalFinish} /></td>
                <td>{valueOrPending(runner.epi, "")}</td>
                <td>{valueOrPending(runner.eri, "")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="eiq-results-v1-note">EPI and ERI remain pending until governed speed and sectional data is available.</p>
    </section>
  );
}

function IndividualRaceResult({
  meeting,
  raceRow,
  onClose,
}: {
  meeting: ThreeDayMeeting;
  raceRow: MeetingResultsRaceRow;
  onClose: () => void;
}) {
  const result = useMemo(
    () =>
      buildIndividualRaceResultViewModel(
        meeting,
        raceRow,

      ),
    [meeting, raceRow],
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
        aria-label={`${result.raceLabel} Results`}
      >
        <header className="eiq-results-v2-modal-header">
          <div>
            <span>Results</span>
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
            aria-label="Close Results"
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
            Report
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
}

export function MeetingResultsWorkspace({ meeting }: MeetingResultsWorkspaceProps) {
  const [rows, setRows] = useState<ResultsTerminalRow[]>([]);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [resultRaceKey, setResultRaceKey] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setSourceError(null);
    loadResultsTerminalFeed()
      .then((nextRows) => {
        if (!active) return;
        setRows(nextRows);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setRows([]);
        setSourceError(error instanceof Error ? error.message : "Results terminal feed failed to load");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const model = useMemo(
    () => buildMeetingResultsViewModel(meeting, rows, { sourceError }),
    [meeting, rows, sourceError],
  );

  const selectedResultRace = model.rows.find((row) => row.raceKey === resultRaceKey) ?? null;

  if (loading) {
    return (
      <section className="eiq-results-v1">
        <div className="eiq-results-v1-empty">
          <span>RESULTS</span>
          <strong>Loading official results feed.</strong>
        </div>
      </section>
    );
  }

  return (
    <section className="eiq-results-v1" aria-label="Results">
      <header className="eiq-results-v1-header">
        <div>
          <span>RESULTS</span>
          <h2>Meeting Results</h2>
        </div>
      </header>

      <SummaryStrip model={model} />

      <MeetingResultsTable
        model={model}
        onSelectRace={setResultRaceKey}
      />

      {selectedResultRace ? (
        <IndividualRaceResult
          meeting={meeting}
          raceRow={selectedResultRace}
          onClose={() => setResultRaceKey(null)}
        />
      ) : null}
    </section>
  );
}
