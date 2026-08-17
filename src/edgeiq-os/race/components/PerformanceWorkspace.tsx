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

import {
  EiqBadge,
  EiqButton,
  EiqDataTable,
  EiqEmptyState,
  EiqPanel,
  EiqSectionHeader,
  EiqSidePanel,
  EiqStatusBadge,
} from "../../design-system/v1";



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

  if (text.includes("no governed") || text.includes("not")) return "is-pending";

  return "is-current";

}



function DetailPanel({ cell }: { cell: PerformanceHeatCell | null }) {

  const entries = Object.entries(cell?.context ?? {}).filter(([, detail]) => detail);

  return (

    <EiqSidePanel className="eiq-v1-analytical-side-panel">

      <EiqSectionHeader eyebrow="Run Detail" title="Historical start context" />

        {cell && entries.length ? (

          <dl className="eiq-v1-side-facts">

            {entries.map(([label, detail]) => (

              <div key={label}><dt>{label}</dt><dd>{detail}</dd></div>

            ))}

          </dl>

        ) : (

          <p className="eiq-v1-analytical-copy">Select a populated historical cell to inspect available run detail.</p>

        )}

    </EiqSidePanel>

  );

}

function PerformanceModules({ fallback = false, currentEpiCount = 0 }: { fallback?: boolean; currentEpiCount?: number }) {
  const modules = fallback
    ? ["FIELD EPI MATRIX", "PERFORMANCE DNA", "PEAK PERFORMANCES", "TRENDS & PROFILES", "RECORD BOOK", "SECTIONALS"].map((label, index) => [
        label,
        index === 0 ? `${currentEpiCount} governed EPR rows` : "Historical data unavailable",
      ])
    : [
        ["FIELD EPI MATRIX", "Quick field scan"],
        ["PERFORMANCE DNA", "Single horse analysis"],
        ["PEAK PERFORMANCES", "Top runs in career"],
        ["TRENDS & PROFILES", "Performance analytics"],
        ["RECORD BOOK", "Career bests"],
        ["SECTIONALS", "Speed and sectional data"],
      ];

  return (
    <section className="eiq-v1-module-tabs" aria-label="Performance modules">
      {modules.map(([label, description], index) => (
        <button key={label} type="button" className={index === 0 ? "is-active" : ""}>
          <strong>{label}</strong>
          <span>{description}</span>
        </button>
      ))}
    </section>
  );
}

function PerformanceToolbar({
  status,
  rows,
  historicalRuns,
  extended = false,
}: {
  status: string;
  rows: number;
  historicalRuns: string | number;
  extended?: boolean;
}) {
  const options = extended ? ["EPI", "ERI", "EARLY SPEED", "LATE SPEED", "SUITABILITY", "FORM MOMENTUM"] : ["EPI", "ERI", "EARLY SPEED", "LATE SPEED"];
  return (
    <EiqPanel density="compact" className="eiq-v1-control-bar">
      <div className="eiq-v1-control-group">
        <span>Metric View</span>
        {options.map((option, index) => (
          <EiqButton key={option} size="compact" variant={index === 0 ? "primary" : "secondary"} aria-pressed={index === 0}>
            {option}
          </EiqButton>
        ))}
      </div>
      <dl className="eiq-v1-inline-facts">
        <div><dt>Status</dt><dd><EiqStatusBadge status={status} /></dd></div>
        <div><dt>Rows</dt><dd>{rows}</dd></div>
        <div><dt>Historical Runs</dt><dd>{historicalRuns}</dd></div>
      </dl>
    </EiqPanel>
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

    return () => {

      cancelled = true;

    };

  }, [raceKey]);



  useEffect(() => {

    setSelectedCell(null);

  }, [raceKey]);



  const epiViewModel = useMemo(() => buildEpiWorkspaceViewModel(raceKey, epiRows, meetingKey), [raceKey, epiRows, meetingKey]);

  const viewModel = useMemo(() => buildPerformanceWorkspaceViewModel(epiViewModel.rows, performanceContext), [epiViewModel.rows, performanceContext]);



  if (loading) {

    return <EiqEmptyState title="Loading governed performance history" />;

  }



  if (error) {

    return <EiqEmptyState title="Performance workspace unavailable" detail={error} />;

  }



  if (!viewModel.rows.length) {
    const fallbackField = Array.isArray(field) ? field.slice(0, 30) : [];

    const normalizeRunnerName = (input: unknown): string =>
      String(input ?? "")
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, "");

    const epiByRunner = new Map<string, any>();

    for (const row of epiViewModel.rows ?? []) {
      const candidate = row as any;

      const runnerName = firstText(
        candidate?.runnerName,
        candidate?.runner,
        candidate?.horse,
        candidate?.horseName,
        candidate?.canonicalHorseName,
        candidate?.canonical_horse_name,
      );

      const normalized = normalizeRunnerName(runnerName);

      if (normalized) {
        epiByRunner.set(normalized, candidate);
      }
    }

    const currentEpiCount = fallbackField.reduce((count, runner, index) => {
      const display = runnerDisplay(runner, index);
      return count + (epiByRunner.has(normalizeRunnerName(display.horse)) ? 1 : 0);
    }, 0);

    return (
      <section className="eiq-performance-v3-workspace eiq-v1-analytical-workspace">
        <PerformanceModules fallback currentEpiCount={currentEpiCount} />

        <PerformanceToolbar
          status={currentEpiCount ? `Current EPR ${currentEpiCount}/${fallbackField.length}` : "No governed EPR available"}
          rows={fallbackField.length}
          historicalRuns="Unavailable"
        />

        <EiqPanel className="eiq-v1-analytical-table-panel">
          <EiqSectionHeader
            eyebrow="Performance Matrix"
            title="Field EPR Matrix"
            meta={<EiqBadge tone={currentEpiCount ? "success" : "warning"}>{currentEpiCount} governed rows</EiqBadge>}
          />

          <EiqDataTable
            density="analytical"
            className="eiq-performance-v3-table"
            wrapperProps={{ className: "eiq-v1-analytical-table-scroll" }}
          >
              <thead>
                <tr>
                  <th>No</th>
                  <th>Silk</th>
                  <th>Horse</th>
                  <th>EPR</th>
                  <th>Avg</th>
                  <th>Last</th>
                  {HISTORY_COLUMNS.map((column) => <th key={column}>{column}</th>)}
                </tr>
              </thead>
              <tbody>
                {fallbackField.length ? fallbackField.map((runner, index) => {
                  const display = runnerDisplay(runner, index);
                  const epiRow = epiByRunner.get(normalizeRunnerName(display.horse));

                  const epiValue = firstText(
                    epiRow?.current_epi,
                    epiRow?.epi,
                    epiRow?.epiValue,
                    epiRow?.epi_value,
                    epiRow?.value,
                    epiRow?.rating,
                  );

                  return (
                    <tr key={`${display.no}-${display.horse}`}>
                      <td>{display.no}</td>
                      <td>
                        <span className="eiq-performance-v3-silk is-empty" aria-hidden="true" />
                      </td>
                      <td><strong>{display.horse}</strong></td>
                      <td>{epiValue || (epiRow ? "Available" : "Unavailable")}</td>
                      <td>?</td>
                      <td>?</td>
                      {HISTORY_COLUMNS.map((column) => (
                        <td key={`${display.no}-${column}`}>
                          <span className="eiq-v1-analytical-tile is-missing">-</span>
                        </td>
                      ))}
                    </tr>
                  );
                }) : (
                  <tr>
                    <td colSpan={6 + HISTORY_COLUMNS.length}>
                      Select a race with declared runners to populate the performance matrix.
                    </td>
                  </tr>
                )}
              </tbody>
          </EiqDataTable>

          <div className="eiq-v1-analytical-legend" aria-label="Performance heat map legend">
            <span><i className="is-positive" /> Strong</span>
            <span><i className="is-neutral" /> Around benchmark</span>
            <span><i className="is-negative" /> Below benchmark</span>
            <span><i className="is-missing" /> Historical run unavailable</span>
          </div>
        </EiqPanel>
      </section>
    );
  }



  return (

    <section className="eiq-performance-v3-workspace eiq-v1-analytical-workspace">
      <PerformanceModules />

      <PerformanceToolbar
        status={viewModel.sourceSummary}
        rows={viewModel.rows.length}
        historicalRuns={viewModel.historicalRuns}
        extended
      />
      <div className="eiq-v1-analytical-grid">

        <EiqPanel className="eiq-v1-analytical-table-panel">

          <EiqSectionHeader
            eyebrow="Performance Matrix"
            title="Field EPR Matrix"
            meta={<EiqBadge tone={statusClass(viewModel.sourceSummary) === "is-current" ? "success" : "warning"}>{viewModel.historicalRuns} historical runs</EiqBadge>}
          />

          <EiqDataTable
            density="analytical"
            className="eiq-performance-v3-table"
            wrapperProps={{ className: "eiq-v1-analytical-table-scroll" }}
          >

              <thead>

                <tr>

                  <th>No</th>

                  <th>Silk</th>

                  <th>Horse</th>

                  <th>EPR</th>

                  <th>Avg</th>

                  <th>Last</th>

                  {HISTORY_COLUMNS.map((column) => <th key={column}>{column}</th>)}

                </tr>

              </thead>

              <tbody>

                {viewModel.rows.map((row) => (

                  <tr key={row.key}>

                    <td>{row.no}</td>

                    <td><span className="eiq-performance-v3-silk is-empty" aria-hidden="true" /></td>

                    <td><strong>{row.runner}</strong></td>

                    <td className="eiq-performance-v3-epi">{value(row.epi) || "-"}</td>

                    <td>{value(row.avg) || "-"}</td>

                    <td>{value(row.last) || "-"}</td>

                    {HISTORY_COLUMNS.map((column, index) => {

                      const cell = row.cells[index];

                      return (

                        <td key={`${row.key}-${column}`}>

                          {cell?.value ? (

                            <button

                              type="button"

                              className={`eiq-v1-analytical-tile is-${cell.tileClass}${selectedCell === cell ? " is-selected" : ""}`}

                              title={Object.entries(cell.context).filter(([, detail]) => detail).map(([label, detail]) => `${label}: ${detail}`).join("\n")}

                              onClick={() => setSelectedCell(cell)}

                            >

                              {cell.value}

                            </button>

                          ) : (

                            <span className="eiq-v1-analytical-tile is-missing">-</span>

                          )}

                        </td>

                      );

                    })}

                  </tr>

                ))}

              </tbody>

          </EiqDataTable>

          <div className="eiq-v1-analytical-legend" aria-label="Performance heat map legend">

            <span><i className="is-positive" /> Strong</span>

            <span><i className="is-neutral" /> Around benchmark</span>

            <span><i className="is-negative" /> Below benchmark</span>

            <span><i className="is-missing" /> Not supplied</span>

          </div>

        </EiqPanel>

        <DetailPanel cell={selectedCell} />

      </div>

    </section>

  );

}

