import { useEffect, useMemo, useState } from "react";
import {
  buildEpiWorkspaceViewModel,
  loadEpiWorkspaceTerminalFeed,
  type BETA013Row,
  type BETA013Start,
  type BETA013StartContext,
  type BETA013ViewModel,
} from "../services/epiWorkspaceFeed";
import {
  buildPerformanceIntelligenceService,
  formatBenchmarkConfidence,
  formatBenchmarkLevel,
  loadPerformanceIntelligenceFeed,
  type PerformanceIntelligenceRaceContext,
} from "../../services/performance-intelligence";

type EpiWorkspaceWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
  field?: any[];
};

type SelectedTile = {
  row: BETA013Row;
  start: BETA013Start;
};

const CONTEXT_FIELDS: Array<keyof BETA013StartContext> = [
  "DATE",
  "TRACK",
  "MEETING / RACE",
  "DISTANCE",
  "CLASS",
  "CONDITION",
  "BARRIER",
  "WEIGHT",
  "JOCKEY",
  "TRAINER",
  "FINISH",
  "MARGIN",
  "SP",
  "EPI",
  "ERI",
  "8-6",
  "6-4",
  "4-2",
  "2-F",
];

function value(rowValue: string | null | undefined): string {
  return rowValue && rowValue.trim() ? rowValue : "";
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (text && text !== "-" && text.toLowerCase() !== "null" && text.toLowerCase() !== "undefined") return text;
  }
  return "";
}

function fieldRunner(row: any, index: number): { no: string; horse: string; jockey: string; trainer: string } {
  return {
    no: firstText(row?.official?.number, row?.number, row?.runnerNumber, row?.saddlecloth, row?.no, index + 1),
    horse: firstText(row?.official?.runner, row?.runner, row?.horse, row?.runnerName, row?.name, "Runner pending"),
    jockey: firstText(row?.official?.jockey, row?.jockey, row?.jockeyName, row?.rider, "Pending"),
    trainer: firstText(row?.official?.trainer, row?.trainer, row?.trainerName, "Pending"),
  };
}

function statusClass(valueText: string | null): string {
  const text = value(valueText).toLowerCase();
  if (text.includes("pending") || text.includes("unavailable") || text.includes("empty")) return "is-pending";
  return "is-current";
}

function diffClass(valueText: string | null): string {
  const number = Number(value(valueText));
  if (Number.isNaN(number)) return "";
  if (number > 0) return "is-positive";
  if (number < 0) return "is-negative";
  return "is-neutral";
}
function validStarts(row: BETA013Row): number {
  return row.starts.filter((start) => value(start.value)).length;
}
function latestContext(row: BETA013Row): BETA013StartContext | null {
  return row.starts.find((start) => start.context)?.context ?? null;
}
function evidenceLabel(row: BETA013Row): string {
  return value(row.sourceConfidence).replace(/_/g, " ") || "Unavailable";
}
function statusLabel(row: BETA013Row): string {
  return value(row.rowStatus).replace(/_/g, " ") || (row.current_epi ? "Available" : "Insufficient Evidence");
}

function SummaryStrip({ row }: { row: BETA013Row | null }) {
  const facts = [
    ["CURRENT EPI", row?.current_epi],
    ["RACE RANK", row?.rank],
    ["FIELD AVERAGE", row?.field_avg],
    ["DIFFERENCE", row?.diff],
    ["PEAK LAST 10", row?.peak_last_10],
    ["AVERAGE LAST 10", row?.average_last_10],
    ["TREND", row?.governed_trend],
  ];
  return (
    <section className="eiq-epi-v1-summary" aria-label="Runner EPI summary">
      <div>
        <span>Selected Runner</span>
        <strong>{value(row?.horse) || "Select a runner"}</strong>
      </div>
      <dl>
        {facts.map(([label, factValue]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className={label === "DIFFERENCE" ? diffClass(factValue ?? null) : ""}>{value(factValue ?? null)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function EpiMatrix({
  rows,
  selectedTile,
  onSelectTile,
  onSelectRow,
}: {
  rows: BETA013Row[];
  selectedTile: SelectedTile | null;
  onSelectTile: (tile: SelectedTile) => void;
  onSelectRow: (row: BETA013Row) => void;
}) {
  return (
    <section className="eiq-epi-v1-panel eiq-epi-v1-table-panel">
      <div className="eiq-epi-v1-panel__title">
        <span>EPI Matrix</span>
        <small>Field ranking, last-10 profile and evidence status</small>
      </div>
      <div className="eiq-epi-v1-table-scroll">
        <table className="eiq-epi-v1-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>No</th>
              <th>Runner</th>
              <th>Jockey</th>
              <th>Trainer</th>
              <th>Current EPI</th>
              <th>Field Diff</th>
              <th>Peak Last 10</th>
              <th>Avg Last 10</th>
              <th>Trend</th>
              <th>Valid Starts</th>
              <th>Evidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${value(row.no)}-${value(row.horse)}`} className={row.rowStatus === "unavailable" ? "is-unavailable" : ""}>
                {(() => {
                  const context = latestContext(row);
                  return (
                    <>
                      <td>{value(row.rank)}</td>
                      <td>{value(row.no)}</td>
                      <td><button type="button" className="eiq-epi-v1-horse-button" onClick={() => onSelectRow(row)}>{value(row.horse)}</button></td>
                      <td>{value(context?.JOCKEY) || "Unavailable"}</td>
                      <td>{value(context?.TRAINER) || "Unavailable"}</td>
                      <td><strong>{value(row.current_epi)}</strong></td>
                      <td className={diffClass(row.diff)}>{value(row.diff)}</td>
                      <td>{value(row.peak_last_10)}</td>
                      <td>{value(row.average_last_10)}</td>
                      <td>{value(row.governed_trend) || "Stable"}</td>
                      <td>{validStarts(row)}</td>
                      <td>{evidenceLabel(row)}</td>
                      <td>{statusLabel(row)}</td>
                    </>
                  );
                })()}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="eiq-epi-v1-legend" aria-label="EPI tile context legend">
        <span><i className="is-positive" /> Exceptional</span>
        <span><i className="is-neutral" /> Above Benchmark</span>
        <span><i className="is-neutral" /> Around Benchmark</span>
        <span><i className="is-negative" /> Below Benchmark</span>
        <span><i className="is-missing" /> Insufficient Evidence</span>
      </div>
    </section>
  );
}

function RaceBenchmarkPanel({ context }: { context: PerformanceIntelligenceRaceContext | null }) {
  const race = context?.race ?? null;
  const benchmark = context?.benchmarks[0] ?? null;

  return (
    <section className="eiq-epi-v1-panel">
      <div className="eiq-epi-v1-panel__title"><span>Race Benchmark</span></div>
      {race ? (
        <>
          <dl className="eiq-epi-v1-facts">
            <div><dt>Level</dt><dd>{formatBenchmarkLevel(race.selected_benchmark_level)}</dd></div>
            <div><dt>Evidence</dt><dd>{formatBenchmarkConfidence(race.selected_benchmark_confidence)}</dd></div>
            <div><dt>Sample</dt><dd>{race.selected_benchmark_sample_size || benchmark?.sample_size || "Unavailable"}</dd></div>
            <div><dt>Benchmark Time</dt><dd>{race.benchmark_time_seconds || benchmark?.median_time_seconds || "Unavailable"}</dd></div>
          </dl>
          <p className="eiq-epi-v1-copy">{race.fallback_path || "Historical benchmark context is available for this race."}</p>
        </>
      ) : (
        <p className="eiq-epi-v1-copy">Race benchmark context is not available for this race.</p>
      )}
    </section>
  );
}

function ContextPanel({
  selectedTile,
  viewModel,
  performanceContext,
}: {
  selectedTile: SelectedTile | null;
  viewModel: BETA013ViewModel;
  performanceContext: PerformanceIntelligenceRaceContext | null;
}) {
  const context = selectedTile?.start.context ?? null;
  return (
    <aside className="eiq-epi-v1-side">
      <RaceBenchmarkPanel context={performanceContext} />
      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>Historical Start Context</span></div>
        {context ? (
          <dl className="eiq-epi-v1-context">
            {CONTEXT_FIELDS.map((field) => (
              <div key={field}>
                <dt>{field}</dt>
                <dd>{value(context[field])}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="eiq-epi-v1-copy">Select a populated EPI tile to inspect the historical race context.</p>
        )}
      </section>
      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>EPI Read</span></div>
        <dl className="eiq-epi-v1-facts">
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Available</dt><dd>{viewModel.rows.filter((row) => row.current_epi || row.starts.some((start) => start.value)).length}</dd></div>
        </dl>
      </section>
      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>Availability</span></div>
        <p className="eiq-epi-v1-copy">
          Missing EPI evidence remains unavailable until supplied by the governed feed.
        </p>
      </section>
    </aside>
  );
}

export function EpiWorkspaceWorkspace({ raceKey, meetingKey = null, raceLabel = null, field = [] }: EpiWorkspaceWorkspaceProps) {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof loadEpiWorkspaceTerminalFeed>>>([]);
  const [performanceContext, setPerformanceContext] = useState<PerformanceIntelligenceRaceContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRowKey, setSelectedRowKey] = useState<string | null>(null);
  const [selectedTile, setSelectedTile] = useState<SelectedTile | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadEpiWorkspaceTerminalFeed()
      .then((feedRows) => {
        if (!cancelled) {
          setRows(feedRows);
          setError(null);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setRows([]);
          setError(loadError instanceof Error ? loadError.message : "EPI workspace feed failed");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadPerformanceIntelligenceFeed()
      .then((feed) => {
        if (cancelled) return;
        setPerformanceContext(buildPerformanceIntelligenceService(feed).getRaceContext(raceKey));
      })
      .catch((loadError) => {
        if (!cancelled) {
          console.warn("Certified performance intelligence feed unavailable", loadError);
          setPerformanceContext(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [raceKey]);

  const viewModel = useMemo(() => buildEpiWorkspaceViewModel(raceKey, rows, meetingKey), [raceKey, rows, meetingKey]);
  const selectedRow = useMemo(
    () => viewModel.rows.find((row) => `${value(row.no)}-${value(row.horse)}` === selectedRowKey) ?? selectedTile?.row ?? viewModel.selectedRow,
    [selectedRowKey, selectedTile, viewModel.rows, viewModel.selectedRow],
  );

  useEffect(() => {
    setSelectedTile(null);
    setSelectedRowKey(null);
  }, [raceKey]);

  if (loading) {
    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">Loading governed EPI matrix.</div></section>;
  }

  if (error) {
    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">{error}</div></section>;
  }

  if (!viewModel.rows.length) {
    const fallbackField = Array.isArray(field) ? field.slice(0, 30) : [];
    return (
      <section className="eiq-epi-v1">
        <div className="eiq-epi-v1-hero">
          <div><p>EPI</p><h3>{raceLabel || "EPI Workspace"}</h3><span>EDGEIQ Performance Index structure is available while race-matched EPI rows are pending.</span></div>
          <dl><div><dt>Status</dt><dd className="is-pending">Awaiting race-matched EPI rows</dd></div><div><dt>Field</dt><dd>{fallbackField.length}</dd></div><div><dt>Source Rows</dt><dd>{rows.length}</dd></div></dl>
        </div>
        <SummaryStrip row={null} />
        <div className="eiq-epi-v1-grid">
          <section className="eiq-epi-v1-panel eiq-epi-v1-table-panel">
            <div className="eiq-epi-v1-panel__title"><span>EPI Matrix</span><small>Runner rows are visible with pending EPI fields</small></div>
            <div className="eiq-epi-v1-table-scroll"><table className="eiq-epi-v1-table"><thead><tr><th>Rank</th><th>No</th><th>Runner</th><th>Jockey</th><th>Trainer</th><th>Current EPI</th><th>Field Diff</th><th>Peak Last 10</th><th>Avg Last 10</th><th>Trend</th><th>Valid Starts</th><th>Evidence</th><th>Status</th></tr></thead><tbody>
              {fallbackField.length ? fallbackField.map((runner, index) => { const display = fieldRunner(runner, index); return (
                <tr key={`${display.no}-${display.horse}`} className="is-unavailable"><td>Pending</td><td>{display.no}</td><td><strong>{display.horse}</strong></td><td>{display.jockey}</td><td>{display.trainer}</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Awaiting row</td></tr>
              ); }) : <tr><td colSpan={13}>Select a race with declared runners to populate the EPI matrix.</td></tr>}
            </tbody></table></div>
          </section>
          <aside className="eiq-epi-v1-side">
            <RaceBenchmarkPanel context={performanceContext} />
            <section className="eiq-epi-v1-panel"><div className="eiq-epi-v1-panel__title"><span>Historical EPI</span></div><p className="eiq-epi-v1-copy">Race-matched historical EPI rows are pending for this selected race.</p></section>
            <section className="eiq-epi-v1-panel"><div className="eiq-epi-v1-panel__title"><span>Rating Explanation</span></div><p className="eiq-epi-v1-copy">No EPI value is shown until the governed feed supplies a matched row.</p></section>
          </aside>
        </div>
      </section>
    );
  }

  return (
    <section className="eiq-epi-v1">
      <div className="eiq-epi-v1-hero">
        <div>
          <p>EPI</p>
          <h3>{raceLabel || "EPI Workspace"}</h3>
          <span>EDGEIQ Performance Index field ranking, last-10 profile, evidence status and benchmark race strength.</span>
        </div>
        <dl>
          <div><dt>Status</dt><dd className={statusClass(viewModel.status)}>{viewModel.status}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Source Rows</dt><dd>{viewModel.source.loadedRows}</dd></div>
        </dl>
      </div>
      <SummaryStrip row={selectedRow} />
      <div className="eiq-epi-v1-grid">
        <EpiMatrix
          rows={viewModel.rows}
          selectedTile={selectedTile}
          onSelectTile={setSelectedTile}
          onSelectRow={(row) => setSelectedRowKey(`${value(row.no)}-${value(row.horse)}`)}
        />
        <ContextPanel selectedTile={selectedTile} viewModel={viewModel} performanceContext={performanceContext} />
      </div>
    </section>
  );
}
