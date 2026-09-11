import { useEffect, useMemo, useState } from "react";

import {
  buildEpiWorkspaceViewModel,
  loadEpiWorkspaceTerminalFeed,
} from "../services/epiWorkspaceFeed";
import {
  buildPerformanceIntelligenceService,
  loadPerformanceIntelligenceFeed,
  type PerformanceIntelligenceRaceContext,
} from "../../services/performance-intelligence";
import {
  buildPerformanceWorkspaceViewModel,
  type PerformanceHeatCell,
} from "../services/performanceWorkspaceViewModel";

type PerformanceWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
  field?: any[];
};

const HISTORY_COLUMNS = ["L5", "L4", "L3", "L2", "L1"];

function value(text: string | null | undefined): string {
  return text && text.trim() ? text : "";
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (text && text !== "-" && text.toLowerCase() !== "null" && text.toLowerCase() !== "undefined") return text;
  }
  return "";
}

function runnerDisplay(row: any, index: number): { no: string; horse: string } {
  const no = firstText(row?.official?.number, row?.number, row?.runnerNumber, row?.saddlecloth, row?.no, index + 1);
  const horse = firstText(row?.official?.runner, row?.runner, row?.horse, row?.runnerName, row?.name, "Runner pending");
  return { no, horse };
}

function statusClass(valueText: string): string {
  const text = valueText.toLowerCase();
  if (text.includes("no governed") || text.includes("not") || text.includes("awaiting")) return "is-pending";
  return "is-current";
}

function DetailPanel({ cell }: { cell: PerformanceHeatCell | null }) {
  const entries = Object.entries(cell?.context ?? {}).filter(([, detail]) => detail);
  return (
    <aside className="eiq-epi-v1-side">
      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>Run Detail</span></div>
        {cell && entries.length ? (
          <dl className="eiq-epi-v1-context">
            {entries.map(([label, detail]) => (
              <div key={label}><dt>{label}</dt><dd>{detail}</dd></div>
            ))}
          </dl>
        ) : (
          <p className="eiq-epi-v1-copy">Select a populated historical cell to inspect available run detail.</p>
        )}
      </section>
    </aside>
  );
}

export function PerformanceWorkspace({ raceKey, meetingKey = null, raceLabel = null, field = [] }: PerformanceWorkspaceProps) {
  const [epiRows, setEpiRows] = useState<Awaited<ReturnType<typeof loadEpiWorkspaceTerminalFeed>>>([]);
  const [performanceContext, setPerformanceContext] = useState<PerformanceIntelligenceRaceContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCell, setSelectedCell] = useState<PerformanceHeatCell | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([loadEpiWorkspaceTerminalFeed(), loadPerformanceIntelligenceFeed()])
      .then(([terminalRows, feed]) => {
        if (cancelled) return;
        setEpiRows(terminalRows);
        setPerformanceContext(buildPerformanceIntelligenceService(feed).getRaceContext(raceKey));
        setError(null);
      })
      .catch((loadError) => {
        if (!cancelled) {
          setEpiRows([]);
          setPerformanceContext(null);
          setError(loadError instanceof Error ? loadError.message : "Performance workspace feed failed");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [raceKey]);

  useEffect(() => { setSelectedCell(null); }, [raceKey]);

  const epiViewModel = useMemo(() => buildEpiWorkspaceViewModel(raceKey, epiRows, meetingKey), [raceKey, epiRows, meetingKey]);
  const viewModel = useMemo(() => buildPerformanceWorkspaceViewModel(epiViewModel.rows, performanceContext), [epiViewModel.rows, performanceContext]);

  if (loading) {
    return <section className="eiq-epi-v1"><div className="eiq-epi-v1-empty">Loading governed performance history.</div></section>;
  }

  if (!viewModel.rows.length) {
    const fallbackField = Array.isArray(field) ? field.slice(0, 30) : [];
    const availability = error ? "Performance history is not published for this race" : "Awaiting race-matched performance rows";
    return (
      <section className="eiq-epi-v1 eiq-performance-v2">
        <section className="eiq-performance-approved-modules" aria-label="Performance modules">
          {["FIELD EPI MATRIX", "PERFORMANCE DNA", "PEAK PERFORMANCES", "TRENDS & PROFILES", "RECORD BOOK", "SECTIONALS"].map((label, index) => (
            <button key={label} type="button" className={index === 0 ? "is-active" : ""}>
              <strong>{label}</strong>
              <span>{index === 0 ? "Field structure loaded" : "Awaiting race-matched rows"}</span>
            </button>
          ))}
        </section>
        <section className="eiq-performance-approved-toolbar" aria-label="Performance controls">
          <div><span>VIEW</span><button type="button" className="is-active">EPI</button><button type="button">ERI</button><button type="button">EARLY SPEED</button><button type="button">LATE SPEED</button></div>
          <dl><div><dt>Status</dt><dd className="is-pending">{availability}</dd></div><div><dt>Field</dt><dd>{fallbackField.length}</dd></div><div><dt>Historical Runs</dt><dd>Pending</dd></div></dl>
        </section>
        <section className="eiq-epi-v1-panel eiq-epi-v1-table-panel">
          <div className="eiq-epi-v1-panel__title"><span>Performance Matrix</span><small>Runner structure is visible while race-matched history is pending</small></div>
          <div className="eiq-epi-v1-table-scroll">
            <table className="eiq-epi-v1-table eiq-performance-v2-table"><thead><tr><th>NO</th><th>SILK</th><th>HORSE</th><th>EPI</th><th>AVG</th><th>LAST</th>{HISTORY_COLUMNS.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>
              {fallbackField.length ? fallbackField.map((runner, index) => { const display = runnerDisplay(runner, index); return (
                <tr key={`${display.no}-${display.horse}`}><td>{display.no}</td><td><span className="eiq-performance-v2-silk is-empty" aria-hidden="true" /></td><td><strong>{display.horse}</strong></td><td>Pending</td><td>Pending</td><td>Pending</td>{HISTORY_COLUMNS.map((column) => <td key={`${display.no}-${column}`}><span className="eiq-epi-v1-tile is-missing">-</span></td>)}</tr>
              ); }) : <tr><td colSpan={6 + HISTORY_COLUMNS.length}>No declared runners are available for the performance matrix.</td></tr>}
            </tbody></table>
          </div>
          <div className="eiq-epi-v1-legend" aria-label="Performance heat map legend"><span><i className="is-positive" /> Strong</span><span><i className="is-neutral" /> Around benchmark</span><span><i className="is-negative" /> Below benchmark</span><span><i className="is-missing" /> Awaiting row</span></div>
        </section>
      </section>
    );
  }

  return (
    <section className="eiq-epi-v1 eiq-performance-v2">
      <section className="eiq-performance-approved-modules" aria-label="Performance modules">
        {[
          ["FIELD EPI MATRIX", "Quick field scan"],
          ["PERFORMANCE DNA", "Single horse analysis"],
          ["PEAK PERFORMANCES", "Top runs in career"],
          ["TRENDS & PROFILES", "Performance analytics"],
          ["RECORD BOOK", "Career bests"],
          ["SECTIONALS", "Speed and sectional data"],
        ].map(([label, description], index) => (
          <button key={label} type="button" className={index === 0 ? "is-active" : ""}>
            <strong>{label}</strong>
            <span>{description}</span>
          </button>
        ))}
      </section>

      <section className="eiq-performance-approved-toolbar" aria-label="Performance controls">
        <div>
          <span>VIEW</span>
          <button type="button" className="is-active">EPI</button>
          <button type="button">ERI</button>
          <button type="button">EARLY SPEED</button>
          <button type="button">LATE SPEED</button>
          <button type="button">SUITABILITY</button>
          <button type="button">FORM MOMENTUM</button>
        </div>
        <dl>
          <div><dt>Status</dt><dd className={statusClass(viewModel.sourceSummary)}>{viewModel.sourceSummary}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Historical Runs</dt><dd>{viewModel.historicalRuns}</dd></div>
        </dl>
      </section>
      <div className="eiq-epi-v1-grid">
        <section className="eiq-epi-v1-panel eiq-epi-v1-table-panel">
          <div className="eiq-epi-v1-panel__title"><span>Performance Matrix</span><small>NO / SILK / HORSE / EPI / AVG / LAST / historical runs</small></div>
          <div className="eiq-epi-v1-table-scroll">
            <table className="eiq-epi-v1-table eiq-performance-v2-table">
              <thead><tr><th>NO</th><th>SILK</th><th>HORSE</th><th>EPI</th><th>AVG</th><th>LAST</th>{HISTORY_COLUMNS.map((column) => <th key={column}>{column}</th>)}</tr></thead>
              <tbody>
                {viewModel.rows.map((row) => (
                  <tr key={row.key}>
                    <td>{row.no}</td>
                    <td><span className="eiq-performance-v2-silk is-empty" aria-hidden="true" /></td>
                    <td><strong>{row.runner}</strong></td>
                    <td className="eiq-performance-v2-epi">{value(row.epi) || "-"}</td>
                    <td>{value(row.avg) || "-"}</td>
                    <td>{value(row.last) || "-"}</td>
                    {HISTORY_COLUMNS.map((column, index) => {
                      const cell = row.cells[index];
                      return (
                        <td key={`${row.key}-${column}`}>
                          {cell?.value ? (
                            <button type="button" className={`eiq-epi-v1-tile is-${cell.tileClass}${selectedCell === cell ? " is-selected" : ""}`} title={Object.entries(cell.context).filter(([, detail]) => detail).map(([label, detail]) => `${label}: ${detail}`).join("\n")} onClick={() => setSelectedCell(cell)}>{cell.value}</button>
                          ) : <span className="eiq-epi-v1-tile is-missing">-</span>}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="eiq-epi-v1-legend" aria-label="Performance heat map legend"><span><i className="is-positive" /> Strong</span><span><i className="is-neutral" /> Around benchmark</span><span><i className="is-negative" /> Below benchmark</span><span><i className="is-missing" /> Not supplied</span></div>
        </section>
        <DetailPanel cell={selectedCell} />
      </div>
    </section>
  );
}
