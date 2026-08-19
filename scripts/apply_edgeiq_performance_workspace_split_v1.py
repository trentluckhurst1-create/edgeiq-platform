from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

performance_path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "PerformanceWorkspace.tsx"
epi_path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "EpiWorkspaceWorkspace.tsx"
race_workspace_path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
race_file_path = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"

performance_path.write_text(
    r'''import { useEffect, useMemo, useState } from "react";
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

type PerformanceWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
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

function startHeader(start: BETA013Start): string {
  const number = start.key.replace("start_", "");
  return `S${number}`;
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
    <section className="eiq-epi-v1-summary" aria-label="Performance summary">
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

function PerformanceMatrix({
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
  const startHeaders = rows[0]?.starts ?? [];

  return (
    <section className="eiq-epi-v1-panel eiq-epi-v1-table-panel">
      <div className="eiq-epi-v1-panel__title">
        <span>Performance Matrix</span>
        <small>Current EPI, last-10 profile, trend and governed evidence status</small>
      </div>
      <div className="eiq-epi-v1-table-scroll">
        <table className="eiq-epi-v1-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>No</th>
              <th>Runner</th>
              <th>Current EPI</th>
              <th>Field Diff</th>
              {startHeaders.map((start) => (
                <th key={start.key}>{startHeader(start)}</th>
              ))}
              <th>Peak Last 10</th>
              <th>Avg Last 10</th>
              <th>Trend</th>
              <th>Starts</th>
              <th>Evidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${value(row.no)}-${value(row.horse)}`} className={row.rowStatus === "unavailable" ? "is-unavailable" : ""}>
                <td>{value(row.rank)}</td>
                <td>{value(row.no)}</td>
                <td>
                  <button type="button" className="eiq-epi-v1-horse-button" onClick={() => onSelectRow(row)}>
                    {value(row.horse)}
                  </button>
                </td>
                <td><strong>{value(row.current_epi)}</strong></td>
                <td className={diffClass(row.diff)}>{value(row.diff)}</td>
                {row.starts.map((start) => {
                  const isSelected = selectedTile?.row === row && selectedTile?.start.key === start.key;
                  return (
                    <td key={start.key}>
                      {value(start.value) ? (
                        <button
                          type="button"
                          className={`eiq-epi-v1-tile is-${start.tileClass}${isSelected ? " is-selected" : ""}`}
                          onClick={() => onSelectTile({ row, start })}
                        >
                          {value(start.value)}
                        </button>
                      ) : (
                        <span className="eiq-epi-v1-tile is-missing">-</span>
                      )}
                    </td>
                  );
                })}
                <td>{value(row.peak_last_10)}</td>
                <td>{value(row.average_last_10)}</td>
                <td>{value(row.governed_trend) || "Stable"}</td>
                <td>{validStarts(row)}</td>
                <td>{evidenceLabel(row)}</td>
                <td>{statusLabel(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="eiq-epi-v1-legend" aria-label="Performance tile context legend">
        <span><i className="is-positive" /> Strong</span>
        <span><i className="is-neutral" /> Around Benchmark</span>
        <span><i className="is-negative" /> Below Benchmark</span>
        <span><i className="is-missing" /> Not Supplied</span>
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
          <p className="eiq-epi-v1-copy">Select a populated start cell to inspect the historical race context.</p>
        )}
      </section>
      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>Performance Read</span></div>
        <dl className="eiq-epi-v1-facts">
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Available</dt><dd>{viewModel.rows.filter((row) => row.current_epi || row.starts.some((start) => start.value)).length}</dd></div>
        </dl>
      </section>
      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>Availability</span></div>
        <p className="eiq-epi-v1-copy">
          Missing performance evidence remains unavailable until supplied by the governed feed.
        </p>
      </section>
    </aside>
  );
}

export function PerformanceWorkspace({ raceKey, meetingKey = null, raceLabel = null }: PerformanceWorkspaceProps) {
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
          setError(loadError instanceof Error ? loadError.message : "Performance workspace feed failed");
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
    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">Loading governed performance matrix.</div></section>;
  }

  if (error) {
    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">{error}</div></section>;
  }

  if (!viewModel.rows.length) {
    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">Governed performance rows are not available for this race.</div></section>;
  }

  return (
    <section className="eiq-epi-v1">
      <div className="eiq-epi-v1-hero">
        <div>
          <p>PERFORMANCE</p>
          <h3>{raceLabel || "Performance Intelligence"}</h3>
          <span>Current EPI, last-10 profile, race benchmark context and governed evidence status.</span>
        </div>
        <dl>
          <div><dt>Status</dt><dd className={statusClass(viewModel.status)}>{viewModel.status}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Source Rows</dt><dd>{viewModel.source.loadedRows}</dd></div>
        </dl>
      </div>
      <SummaryStrip row={selectedRow} />
      <div className="eiq-epi-v1-grid">
        <PerformanceMatrix
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
''',
    encoding="utf-8",
)

race_workspace = race_workspace_path.read_text(encoding="utf-8")
race_workspace = race_workspace.replace(
    'import { EpiWorkspaceWorkspace } from "./EpiWorkspaceWorkspace";',
    'import { EpiWorkspaceWorkspace } from "./EpiWorkspaceWorkspace";\nimport { PerformanceWorkspace } from "./PerformanceWorkspace";',
)
race_workspace = race_workspace.replace(
    'const tabs = ["FIELD", "FORM GUIDE", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "EPI", "REVIEW"] as const;',
    'const tabs = ["FIELD", "FORM GUIDE", "PERFORMANCE", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "EPI", "REVIEW"] as const;',
)
race_workspace = race_workspace.replace(
    '''      ) : tab === "MARKET" ? (
        <MarketWorkspace
          raceBook={raceBook}
          field={field}
          meetingKey={raceBook?.official?.meetingKey ?? null}
        />''',
    '''      ) : tab === "PERFORMANCE" ? (
        <PerformanceWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
        />
      ) : tab === "MARKET" ? (
        <MarketWorkspace
          raceBook={raceBook}
          field={field}
          meetingKey={raceBook?.official?.meetingKey ?? null}
        />''',
)
race_workspace_path.write_text(race_workspace, encoding="utf-8")

race_file = race_file_path.read_text(encoding="utf-8")
race_file = race_file.replace('  performance: "EPI",', '  performance: "PERFORMANCE",')
race_file_path.write_text(race_file, encoding="utf-8")

epi = epi_path.read_text(encoding="utf-8")
replacements = {
    "function confidenceLabel(row: BETA013Row): string {": "function evidenceLabel(row: BETA013Row): string {",
    "Field ranking, last-10 profile and confidence status": "Field ranking, last-10 profile and evidence status",
    "<span>Performance Intelligence</span>": "<span>EPI Matrix</span>",
    "<th>Confidence</th>": "<th>Evidence</th>",
    "<td>{confidenceLabel(row)}</td>": "<td>{evidenceLabel(row)}</td>",
    "<div><dt>Confidence</dt><dd>{formatBenchmarkConfidence(race.selected_benchmark_confidence)}</dd></div>": "<div><dt>Evidence</dt><dd>{formatBenchmarkConfidence(race.selected_benchmark_confidence)}</dd></div>",
    "<div className=\"eiq-epi-v1-panel__title\"><span>Performance Read</span></div>": "<div className=\"eiq-epi-v1-panel__title\"><span>EPI Read</span></div>",
    "Missing performance evidence remains unavailable until supplied by the governed feed.": "Missing EPI evidence remains unavailable until supplied by the governed feed.",
    "<p>PERFORMANCE</p>": "<p>EPI</p>",
    '<h3>{raceLabel || "Performance Intelligence"}</h3>': '<h3>{raceLabel || "EPI Workspace"}</h3>',
    "EPI field ranking, last-10 profile, confidence status and benchmark race strength.": "EDGEIQ Performance Index field ranking, last-10 profile, evidence status and benchmark race strength.",
}
for old, new in replacements.items():
    epi = epi.replace(old, new)
epi_path.write_text(epi, encoding="utf-8")

print("EDGEiQ performance workspace split applied")
