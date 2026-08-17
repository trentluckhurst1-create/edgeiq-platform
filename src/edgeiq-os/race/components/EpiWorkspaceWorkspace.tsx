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
import {
  EiqBadge,
  EiqButton,
  EiqCard,
  EiqDataTable,
  EiqEmptyState,
  EiqMetric,
  EiqPanel,
  EiqSectionHeader,
  EiqSidePanel,
  EiqStatusBadge,
} from "../../design-system/v1";

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
    ["CURRENT EPR", row?.current_epi],
    ["RACE RANK", row?.rank],
    ["FIELD AVERAGE", row?.field_avg],
    ["DIFFERENCE", row?.diff],
    ["PEAK LAST 10", row?.peak_last_10],
    ["AVERAGE LAST 10", row?.average_last_10],
    ["TREND", row?.governed_trend],
  ];
  return (
    <section className="eiq-epi-v3-summary" aria-label="Runner EPR and historical EPI summary">
      <EiqCard density="compact" className="eiq-epi-v3-summary__selected">
        <EiqMetric label="Selected Runner" value={value(row?.horse) || "Select a runner"} detail="Current EPR context" />
      </EiqCard>
      {facts.map(([label, factValue]) => (
        <EiqCard key={label} density="compact">
          <EiqMetric
            label={label}
            value={<span className={label === "DIFFERENCE" ? diffClass(factValue ?? null) : ""}>{value(factValue ?? null) || "Pending"}</span>}
          />
        </EiqCard>
      ))}
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
    <EiqPanel className="eiq-v1-analytical-table-panel">
      <EiqSectionHeader
        eyebrow="EPI Matrix"
        title="Field ranking and evidence status"
        meta={<EiqBadge tone="info">{rows.length} runners</EiqBadge>}
      />
      <EiqDataTable
        density="analytical"
        className="eiq-epi-v3-table"
        wrapperProps={{ className: "eiq-v1-analytical-table-scroll" }}
      >
          <thead>
            <tr>
              <th>Rank</th>
              <th>No</th>
              <th>Runner</th>
              <th>Jockey</th>
              <th>Trainer</th>
              <th>Current EPR</th>
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
                  const rowStatus = statusLabel(row);
                  return (
                    <>
                      <td>{value(row.rank)}</td>
                      <td>{value(row.no)}</td>
                      <td>
                        <EiqButton
                          className="eiq-epi-v3-runner-button"
                          size="compact"
                          variant="ghost"
                          onClick={() => onSelectRow(row)}
                        >
                          {value(row.horse)}
                        </EiqButton>
                      </td>
                      <td>{value(context?.JOCKEY) || "Unavailable"}</td>
                      <td>{value(context?.TRAINER) || "Unavailable"}</td>
                      <td><strong>{value(row.current_epi)}</strong></td>
                      <td className={diffClass(row.diff)}>{value(row.diff)}</td>
                      <td>{value(row.peak_last_10)}</td>
                      <td>{value(row.average_last_10)}</td>
                      <td>{value(row.governed_trend) || "Stable"}</td>
                      <td>{validStarts(row)}</td>
                      <td>{evidenceLabel(row)}</td>
                      <td><EiqStatusBadge status={rowStatus} /></td>
                    </>
                  );
                })()}
              </tr>
            ))}
          </tbody>
      </EiqDataTable>
      <div className="eiq-v1-analytical-legend" aria-label="EPI tile context legend">
        <span><i className="is-positive" /> Exceptional</span>
        <span><i className="is-neutral" /> Above Benchmark</span>
        <span><i className="is-neutral" /> Around Benchmark</span>
        <span><i className="is-negative" /> Below Benchmark</span>
        <span><i className="is-missing" /> Insufficient Evidence</span>
      </div>
    </EiqPanel>
  );
}

function RaceBenchmarkPanel({ context }: { context: PerformanceIntelligenceRaceContext | null }) {
  const race = context?.race ?? null;
  const benchmark = context?.benchmarks[0] ?? null;

  return (
    <section className="eiq-v1-side-panel-section">
      <EiqSectionHeader eyebrow="Race Benchmark" title="Benchmark context" />
      {race ? (
        <>
          <dl className="eiq-v1-side-facts">
            <div><dt>Level</dt><dd>{formatBenchmarkLevel(race.selected_benchmark_level)}</dd></div>
            <div><dt>Evidence</dt><dd>{formatBenchmarkConfidence(race.selected_benchmark_confidence)}</dd></div>
            <div><dt>Sample</dt><dd>{race.selected_benchmark_sample_size || benchmark?.sample_size || "Unavailable"}</dd></div>
            <div><dt>Benchmark Time</dt><dd>{race.benchmark_time_seconds || benchmark?.median_time_seconds || "Unavailable"}</dd></div>
          </dl>
          <p className="eiq-v1-analytical-copy">{race.fallback_path || "Historical benchmark context is available for this race."}</p>
        </>
      ) : (
        <p className="eiq-v1-analytical-copy">Race benchmark context is not available for this race.</p>
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
    <EiqSidePanel className="eiq-v1-analytical-side-panel">
      <RaceBenchmarkPanel context={performanceContext} />
      <section className="eiq-v1-side-panel-section">
        <EiqSectionHeader eyebrow="Historical Start Context" title="Selected start" />
        {context ? (
          <dl className="eiq-v1-side-facts">
            {CONTEXT_FIELDS.map((field) => (
              <div key={field}>
                <dt>{field}</dt>
                <dd>{value(context[field])}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="eiq-v1-analytical-copy">Select a populated historical EPI tile to inspect the race context.</p>
        )}
      </section>
      <section className="eiq-v1-side-panel-section">
        <EiqSectionHeader eyebrow="EPI Read" title="Availability" />
        <dl className="eiq-v1-side-facts">
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Available</dt><dd>{viewModel.rows.filter((row) => row.current_epi || row.starts.some((start) => start.value)).length}</dd></div>
        </dl>
      </section>
      <section className="eiq-v1-side-panel-section">
        <EiqSectionHeader eyebrow="Availability" title="Evidence status" />
        <p className="eiq-v1-analytical-copy">
          Missing EPR or historical EPI evidence remains unavailable until supplied by the governed feed.
        </p>
      </section>
    </EiqSidePanel>
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
    return <EiqEmptyState title="Loading governed EPI matrix" />;
  }

  if (error) {
    return <EiqEmptyState title="EPI workspace unavailable" detail={error} />;
  }

  if (!viewModel.rows.length) {
    const fallbackField = Array.isArray(field) ? field.slice(0, 30) : [];
    return (
      <section className="eiq-epi-v3-workspace eiq-v1-analytical-workspace">
        <EiqPanel className="eiq-epi-v3-intro">
          <EiqSectionHeader
            eyebrow="EPI"
            title={raceLabel || "EPI Workspace"}
            meta={<EiqStatusBadge status="Awaiting race-matched EPR rows" />}
          />
          <p className="eiq-v1-analytical-copy">EDGEIQ Performance Index structure is available while race-matched EPR rows are pending.</p>
          <dl className="eiq-v1-inline-facts">
            <div><dt>Field</dt><dd>{fallbackField.length}</dd></div>
            <div><dt>Source Rows</dt><dd>{rows.length}</dd></div>
          </dl>
        </EiqPanel>
        <SummaryStrip row={null} />
        <div className="eiq-v1-analytical-grid">
          <EiqPanel className="eiq-v1-analytical-table-panel">
            <EiqSectionHeader eyebrow="EPI Matrix" title="Runner rows with pending EPR fields" />
            <EiqDataTable density="analytical" className="eiq-epi-v3-table" wrapperProps={{ className: "eiq-v1-analytical-table-scroll" }}><thead><tr><th>Rank</th><th>No</th><th>Runner</th><th>Jockey</th><th>Trainer</th><th>Current EPR</th><th>Field Diff</th><th>Peak Last 10</th><th>Avg Last 10</th><th>Trend</th><th>Valid Starts</th><th>Evidence</th><th>Status</th></tr></thead><tbody>
              {fallbackField.length ? fallbackField.map((runner, index) => { const display = fieldRunner(runner, index); return (
                <tr key={`${display.no}-${display.horse}`} className="is-unavailable"><td>Pending</td><td>{display.no}</td><td><strong>{display.horse}</strong></td><td>{display.jockey}</td><td>{display.trainer}</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td><EiqStatusBadge status="Awaiting row" /></td></tr>
              ); }) : <tr><td colSpan={13}>Select a race with declared runners to populate the EPI matrix.</td></tr>}
            </tbody></EiqDataTable>
          </EiqPanel>
          <EiqSidePanel className="eiq-v1-analytical-side-panel">
            <RaceBenchmarkPanel context={performanceContext} />
            <section className="eiq-v1-side-panel-section"><EiqSectionHeader eyebrow="Historical EPI" title="Pending historical rows" /><p className="eiq-v1-analytical-copy">Race-matched historical EPI rows are pending for this selected race.</p></section>
            <section className="eiq-v1-side-panel-section"><EiqSectionHeader eyebrow="Rating Explanation" title="Governed feed required" /><p className="eiq-v1-analytical-copy">No EPR value is shown until the governed feed supplies a matched row.</p></section>
          </EiqSidePanel>
        </div>
      </section>
    );
  }

  return (
    <section className="eiq-epi-v3-workspace eiq-v1-analytical-workspace">
      <EiqPanel className="eiq-epi-v3-intro">
        <EiqSectionHeader
          eyebrow="EPI"
          title={raceLabel || "EPI Workspace"}
          meta={<EiqStatusBadge status={viewModel.status} />}
        />
        <p className="eiq-v1-analytical-copy">Current EPR field ranking, historical EPI profile, evidence status and benchmark race strength.</p>
        <dl className="eiq-v1-inline-facts">
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Source Rows</dt><dd>{viewModel.source.loadedRows}</dd></div>
        </dl>
      </EiqPanel>
      <SummaryStrip row={selectedRow} />
      <div className="eiq-v1-analytical-grid">
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
