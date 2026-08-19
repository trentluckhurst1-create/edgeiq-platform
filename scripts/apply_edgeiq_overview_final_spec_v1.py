from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "OverviewWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
TRACE = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_OVERVIEW_TRACE_V1.md"

COMPONENT_TEXT = r'''import { useEffect, useMemo, useState } from "react";
import {
  buildOverviewViewModel,
  loadOverviewTerminalFeed,
  type BETA011Row,
  type BETA011ViewModel,
} from "../services/overviewFeed";
import {
  buildEpiWorkspaceViewModel,
  loadEpiWorkspaceTerminalFeed,
  type BETA013Row,
} from "../services/epiWorkspaceFeed";
import { loadMapTerminalFeed } from "../services/mapFeed";
import {
  buildPerformanceIntelligenceService,
  formatBenchmarkLevel,
  loadPerformanceIntelligenceFeed,
  type PerformanceIntelligenceRaceContext,
} from "../../services/performance-intelligence";

type OverviewWorkspaceProps = {
  raceKey?: string | null;
  meetingKey?: string | null;
  raceLabel?: string | null;
  onOpenTab?: (tab: "FORM GUIDE" | "MAP" | "MARKET" | "OVERVIEW" | "INSIGHTS" | "EPI" | "REVIEW") => void;
};

type MapTerminalRow = Awaited<ReturnType<typeof loadMapTerminalFeed>>[number];

const OPEN_TAB_MAP: Record<string, "FORM GUIDE" | "MAP" | "MARKET" | "OVERVIEW" | "INSIGHTS" | "EPI" | "REVIEW"> = {
  FORM: "FORM GUIDE",
  "FORM GUIDE": "FORM GUIDE",
  MAP: "MAP",
  MARKET: "MARKET",
  OVERVIEW: "OVERVIEW",
  INSIGHTS: "INSIGHTS",
  EPI: "EPI",
  REVIEW: "REVIEW",
};

const SUMMARY_SECTIONS = ["Race Environment", "MAP / Race Shape", "Field Intelligence", "Operational / Data State"] as const;
const INTEREST_SECTIONS = ["Race Environment", "MAP / Race Shape", "Field Intelligence", "EDGEiQ Race Read", "Key Race Questions"] as const;

function value(rowValue: unknown): string {
  const text = String(rowValue ?? "").trim();
  if (!text || text === "-" || text === "null" || text === "undefined" || text.toLowerCase() === "none") return "";
  return text;
}

function statusClass(status: unknown): string {
  const text = value(status).toLowerCase();
  if (text.includes("available") || text.includes("current")) return "is-available";
  if (text.includes("partial")) return "is-partial";
  if (text.includes("pending") || text.includes("unavailable") || text.includes("missing")) return "is-pending";
  return "";
}

function display(valueText: unknown, fallback = "Unavailable"): string {
  return value(valueText) || fallback;
}

function rowBySection(rows: BETA011Row[], section: string): BETA011Row | null {
  return rows.find((row) => value(row.section).toLowerCase() === section.toLowerCase()) ?? null;
}

function mapLane(row: MapTerminalRow): string {
  const text = `${value(row.run_style)} ${value(row.projected_position)}`.toLowerCase();
  if (text.includes("lead") || text.includes("forward")) return "Lead";
  if (text.includes("on pace") || text.includes("on-speed") || text.includes("speed")) return "On pace";
  if (text.includes("back") || text.includes("rear")) return "Back";
  if (text.includes("mid")) return "Midfield";
  return "Awaiting";
}

function currentEpiRows(rows: BETA013Row[]): BETA013Row[] {
  return rows.filter((row) => value(row.current_epi));
}

function SummaryCards({ rows, epiRows, mapRows }: { rows: BETA011Row[]; epiRows: BETA013Row[]; mapRows: MapTerminalRow[] }) {
  const rowsWithEvidence = rows.filter((row) => value(row.evidence));
  const mapEvidence = mapRows.filter((row) => value(row.run_style) || value(row.early_speed) || value(row.projected_position)).length;
  const epiAvailable = currentEpiRows(epiRows).length;
  const cards = SUMMARY_SECTIONS.map((section) => rowBySection(rows, section)).filter((row): row is BETA011Row => Boolean(row));

  return (
    <section className="eiq-overview-v3-summary" aria-label="Overview summary intelligence">
      {cards.map((row) => (
        <article className="eiq-overview-v3-card" key={value(row.section)}>
          <span>{value(row.section)}</span>
          <strong>{display(row.evidence, display(row.status, "Awaiting governed evidence"))}</strong>
          <small className={statusClass(row.status)}>{display(row.status, "Unavailable")}</small>
        </article>
      ))}
      <article className="eiq-overview-v3-card">
        <span>EPI Snapshot</span>
        <strong>{epiAvailable ? `${epiAvailable} current figures` : "Awaiting EPI figures"}</strong>
        <small>{epiRows.length ? `${epiRows.length} runners listed` : "No EPI rows"}</small>
      </article>
      <article className="eiq-overview-v3-card">
        <span>Speed Map Preview</span>
        <strong>{mapEvidence ? `${mapEvidence} position reads` : "Awaiting map evidence"}</strong>
        <small>{mapRows.length ? `${mapRows.length} active runners` : "No map rows"}</small>
      </article>
      <article className="eiq-overview-v3-card">
        <span>Race Evidence</span>
        <strong>{rowsWithEvidence.length ? `${rowsWithEvidence.length} populated reads` : "Governed reads pending"}</strong>
        <small>{rows.length ? `${rows.length} overview sections` : "No overview rows"}</small>
      </article>
    </section>
  );
}

function WhatMattersToday({ rows }: { rows: BETA011Row[] }) {
  const ordered = [...rows].sort((left, right) => {
    const leftIndex = INTEREST_SECTIONS.indexOf(value(left.section) as (typeof INTEREST_SECTIONS)[number]);
    const rightIndex = INTEREST_SECTIONS.indexOf(value(right.section) as (typeof INTEREST_SECTIONS)[number]);
    return (leftIndex < 0 ? 999 : leftIndex) - (rightIndex < 0 ? 999 : rightIndex);
  });
  const populated = ordered.filter((row) => value(row.evidence)).slice(0, 5);
  const pending = ordered.filter((row) => !value(row.evidence)).slice(0, 4);

  return (
    <section className="eiq-overview-v1-panel eiq-overview-v3-what-matters">
      <div className="eiq-overview-v1-panel__title">
        <span>What Matters Today</span>
        <small>Governed race evidence only</small>
      </div>
      {populated.length ? (
        <ul>
          {populated.map((row) => (
            <li key={`${value(row.section)}-${value(row.evidence)}`}>
              <b>{value(row.section)}</b>
              <span>{value(row.evidence)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="eiq-overview-v1-copy">The current intelligence feed has not supplied race summary evidence for this race.</p>
      )}
      {pending.length ? (
        <div className="eiq-overview-v3-inline-gaps">
          {pending.map((row) => (
            <small key={`${value(row.section)}-${value(row.status)}`}>{value(row.section)}: {display(row.status, "Pending")}</small>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function SpeedMapPreview({ rows, onOpenTab }: { rows: MapTerminalRow[]; onOpenTab?: OverviewWorkspaceProps["onOpenTab"] }) {
  const lanes = ["Lead", "On pace", "Midfield", "Back", "Awaiting"];
  const active = rows.filter((row) => value(row.horse));
  const hasEvidence = active.some((row) => value(row.run_style) || value(row.early_speed) || value(row.projected_position));

  return (
    <section className="eiq-overview-v1-panel eiq-overview-v3-map-preview">
      <div className="eiq-overview-v1-panel__title">
        <span>Speed Map Preview</span>
        <small>{hasEvidence ? "Race-shape read" : "Awaiting governed positions"}</small>
      </div>
      <div className="eiq-overview-v3-map-lanes" aria-label="Compact speed map preview">
        {lanes.map((lane) => {
          const laneRows = active.filter((row) => mapLane(row) === lane).slice(0, lane === "Awaiting" ? 6 : 4);
          if (!laneRows.length && lane === "Awaiting" && hasEvidence) return null;
          return (
            <div className="eiq-overview-v3-map-lane" key={lane}>
              <span>{lane}</span>
              <div>
                {laneRows.length ? laneRows.map((row) => (
                  <b key={`${value(row.no)}-${value(row.horse)}`}>
                    <em>{display(row.no, "")}</em>{display(row.horse)}
                  </b>
                )) : <small>No governed runners</small>}
              </div>
            </div>
          );
        })}
      </div>
      <button type="button" onClick={() => onOpenTab?.("MAP")}>Open MAP</button>
    </section>
  );
}

function EpiSnapshot({ rows, context, onOpenTab }: { rows: BETA013Row[]; context: PerformanceIntelligenceRaceContext | null; onOpenTab?: OverviewWorkspaceProps["onOpenTab"] }) {
  const available = currentEpiRows(rows);
  const topRows = (available.length ? available : rows).slice(0, 6);
  const race = context?.race ?? null;

  return (
    <section className="eiq-overview-v1-panel eiq-overview-v3-epi">
      <div className="eiq-overview-v1-panel__title">
        <span>EPI Snapshot</span>
        <small>{available.length ? "Current figures" : "Current figures unavailable"}</small>
      </div>
      <dl className="eiq-overview-v3-epi-facts">
        <div><dt>Benchmark</dt><dd>{race ? formatBenchmarkLevel(race.selected_benchmark_level) : "Unavailable"}</dd></div>
        <div><dt>Sample</dt><dd>{display(race?.selected_benchmark_sample_size)}</dd></div>
        <div><dt>Profiles</dt><dd>{context?.horses.length ?? 0}</dd></div>
      </dl>
      {topRows.length ? (
        <table className="eiq-overview-v1-table eiq-overview-v3-compact-table">
          <thead><tr><th>No</th><th>Runner</th><th>EPI</th><th>Trend</th></tr></thead>
          <tbody>
            {topRows.map((row) => (
              <tr key={`${value(row.no)}-${value(row.horse)}`}>
                <td>{display(row.no, "")}</td>
                <td><strong>{display(row.horse)}</strong></td>
                <td>{display(row.current_epi)}</td>
                <td>{display(row.governed_trend)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="eiq-overview-v1-copy">EPI terminal rows are not available for this race.</p>
      )}
      <button type="button" onClick={() => onOpenTab?.("EPI")}>Open EPI</button>
    </section>
  );
}

function RunnerBoard({ epiRows, mapRows }: { epiRows: BETA013Row[]; mapRows: MapTerminalRow[] }) {
  const mapByNo = new Map(mapRows.map((row) => [value(row.no), row]));
  const rows = epiRows.slice(0, 18);

  return (
    <section className="eiq-overview-v1-panel eiq-overview-v3-runner-board">
      <div className="eiq-overview-v1-panel__title">
        <span>Runner Board</span>
        <small>Concise race-field read</small>
      </div>
      {rows.length ? (
        <div className="eiq-overview-v1-table-scroll">
          <table className="eiq-overview-v1-table">
            <thead><tr><th>No</th><th>Runner</th><th>EPI</th><th>Early Speed</th><th>Map</th><th>Status</th></tr></thead>
            <tbody>
              {rows.map((row) => {
                const mapRow = mapByNo.get(value(row.no));
                return (
                  <tr key={`${value(row.no)}-${value(row.horse)}`}>
                    <td>{display(row.no, "")}</td>
                    <td><strong>{display(row.horse)}</strong></td>
                    <td>{display(row.current_epi)}</td>
                    <td>{display(mapRow?.early_speed)}</td>
                    <td>{display(mapRow?.run_style || mapRow?.projected_position)}</td>
                    <td className={statusClass(row.rowStatus || mapRow?.rowStatus)}>{display(row.rowStatus || mapRow?.rowStatus, "Unavailable").replace(/_/g, " ")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="eiq-overview-v1-copy">Runner board rows are not available for this race.</p>
      )}
    </section>
  );
}

function DataGaps({ rows, epiRows, mapRows }: { rows: BETA011Row[]; epiRows: BETA013Row[]; mapRows: MapTerminalRow[] }) {
  const gaps = rows.filter((row) => !value(row.evidence) || statusClass(row.status) === "is-pending").slice(0, 5);
  const epiMissing = epiRows.filter((row) => !value(row.current_epi)).length;
  const mapMissing = mapRows.filter((row) => !value(row.run_style) && !value(row.early_speed) && !value(row.projected_position)).length;

  return (
    <section className="eiq-overview-v1-panel eiq-overview-v3-gaps">
      <div className="eiq-overview-v1-panel__title">
        <span>Data Gaps</span>
        <small>Restrained unavailable state</small>
      </div>
      <ul>
        {gaps.map((row) => <li key={`${value(row.section)}-${value(row.status)}`}><b>{value(row.section)}</b><span>{display(row.status, "Pending")}</span></li>)}
        {epiMissing ? <li><b>EPI Snapshot</b><span>{epiMissing} runners awaiting current EPI</span></li> : null}
        {mapMissing ? <li><b>Speed Map</b><span>{mapMissing} runners awaiting position evidence</span></li> : null}
      </ul>
    </section>
  );
}

export function OverviewWorkspace({ raceKey, meetingKey = null, raceLabel = null, onOpenTab }: OverviewWorkspaceProps) {
  const [overviewRows, setOverviewRows] = useState<Awaited<ReturnType<typeof loadOverviewTerminalFeed>>>([]);
  const [epiRows, setEpiRows] = useState<Awaited<ReturnType<typeof loadEpiWorkspaceTerminalFeed>>>([]);
  const [mapRows, setMapRows] = useState<Awaited<ReturnType<typeof loadMapTerminalFeed>>>([]);
  const [performanceContext, setPerformanceContext] = useState<PerformanceIntelligenceRaceContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([loadOverviewTerminalFeed(), loadEpiWorkspaceTerminalFeed(), loadMapTerminalFeed()])
      .then(([loadedOverview, loadedEpi, loadedMap]) => {
        if (!cancelled) {
          setOverviewRows(loadedOverview);
          setEpiRows(loadedEpi);
          setMapRows(loadedMap);
          setError(null);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setOverviewRows([]);
          setEpiRows([]);
          setMapRows([]);
          setError(loadError instanceof Error ? loadError.message : "Overview feeds failed");
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
        if (!cancelled) setPerformanceContext(buildPerformanceIntelligenceService(feed).getRaceContext(raceKey));
      })
      .catch((loadError) => {
        console.warn("Certified performance intelligence feed unavailable", loadError);
        if (!cancelled) setPerformanceContext(null);
      });
    return () => {
      cancelled = true;
    };
  }, [raceKey]);

  const viewModel: BETA011ViewModel = useMemo(
    () => buildOverviewViewModel(raceKey, overviewRows, meetingKey),
    [raceKey, overviewRows, meetingKey],
  );
  const epiViewModel = useMemo(() => buildEpiWorkspaceViewModel(raceKey, epiRows, meetingKey), [raceKey, epiRows, meetingKey]);
  const selectedMapRows = useMemo(() => mapRows.filter((row) => value(row.race_key) === value(raceKey)), [mapRows, raceKey]);

  if (loading) {
    return <section className="eiq-overview-v1"><div className="eiq-overview-v1-empty">Loading overview evidence.</div></section>;
  }

  if (error) {
    return <section className="eiq-overview-v1"><div className="eiq-overview-v1-empty">{error}</div></section>;
  }

  if (!viewModel.rows.length && !epiViewModel.rows.length && !selectedMapRows.length) {
    return (
      <section className="eiq-overview-v1">
        <div className="eiq-overview-v1-empty">Governed overview rows are not available for this race.</div>
      </section>
    );
  }

  return (
    <section className="eiq-overview-v1 eiq-overview-v3">
      <div className="eiq-overview-v1-hero">
        <div>
          <p>OVERVIEW</p>
          <h3>{raceLabel || "Race Overview"}</h3>
          <span>Concise race summary, speed-map preview, EPI snapshot and runner board.</span>
        </div>
        <dl>
          <div><dt>Overview</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>EPI Rows</dt><dd>{epiViewModel.rows.length}</dd></div>
          <div><dt>Map Rows</dt><dd>{selectedMapRows.length}</dd></div>
        </dl>
      </div>

      <SummaryCards rows={viewModel.rows} epiRows={epiViewModel.rows} mapRows={selectedMapRows} />

      <div className="eiq-overview-v3-layout">
        <main>
          <WhatMattersToday rows={viewModel.rows} />
          <div className="eiq-overview-v3-two-up">
            <SpeedMapPreview rows={selectedMapRows} onOpenTab={onOpenTab} />
            <EpiSnapshot rows={epiViewModel.rows} context={performanceContext} onOpenTab={onOpenTab} />
          </div>
          <RunnerBoard epiRows={epiViewModel.rows} mapRows={selectedMapRows} />
        </main>
        <aside>
          <section className="eiq-overview-v1-panel">
            <div className="eiq-overview-v1-panel__title">
              <span>Race Reference</span>
              <small>Certified performance context</small>
            </div>
            <dl className="eiq-overview-v1-facts">
              <div><dt>Benchmark</dt><dd>{performanceContext?.race ? formatBenchmarkLevel(performanceContext.race.selected_benchmark_level) : "Unavailable"}</dd></div>
              <div><dt>Sample</dt><dd>{display(performanceContext?.race?.selected_benchmark_sample_size)}</dd></div>
              <div><dt>History Rows</dt><dd>{performanceContext?.historical.length ?? 0}</dd></div>
              <div><dt>Profiles</dt><dd>{performanceContext?.horses.length ?? 0}</dd></div>
            </dl>
            <p className="eiq-overview-v1-copy">{display(performanceContext?.race?.fallback_path, "Performance reference is unavailable for this race.")}</p>
          </section>
          <DataGaps rows={viewModel.rows} epiRows={epiViewModel.rows} mapRows={selectedMapRows} />
          <section className="eiq-overview-v1-panel eiq-overview-v3-actions">
            <div className="eiq-overview-v1-panel__title"><span>Open Workspace</span></div>
            {["FORM GUIDE", "MAP", "EPI", "MARKET", "INSIGHTS"].map((label) => (
              <button key={label} type="button" onClick={() => onOpenTab?.(OPEN_TAB_MAP[label])}>{label}</button>
            ))}
          </section>
        </aside>
      </div>
    </section>
  );
}
'''

CSS_MARKER = "/* EDGEIQ OVERVIEW FINAL SPEC V1 */"
CSS_TEXT = r'''
/* EDGEIQ OVERVIEW FINAL SPEC V1 */
.eiq-overview-v3 {
  display: grid;
  gap: 16px;
}

.eiq-overview-v3-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.eiq-overview-v3-card {
  display: grid;
  gap: 6px;
  min-height: 96px;
  padding: 14px 16px;
  border: 1px solid var(--edgeiq-border);
  border-radius: 14px;
  background: var(--edgeiq-surface);
  box-shadow: 0 10px 28px rgba(23, 32, 51, 0.06);
}

.eiq-overview-v3-card span,
.eiq-overview-v3-map-lane > span,
.eiq-overview-v3-inline-gaps small {
  color: var(--edgeiq-primary);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.eiq-overview-v3-card strong {
  color: var(--edgeiq-text-primary);
  font-size: 14px;
  line-height: 1.32;
}

.eiq-overview-v3-card small,
.eiq-overview-v3-map-lane small {
  color: var(--edgeiq-text-secondary);
}

.eiq-overview-v3-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  align-items: start;
}

.eiq-overview-v3-layout > main,
.eiq-overview-v3-layout > aside {
  display: grid;
  gap: 16px;
}

.eiq-overview-v3-two-up {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 16px;
}

.eiq-overview-v3-what-matters ul,
.eiq-overview-v3-gaps ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.eiq-overview-v3-what-matters li,
.eiq-overview-v3-gaps li {
  display: grid;
  grid-template-columns: 170px minmax(0, 1fr);
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--edgeiq-border-soft);
}

.eiq-overview-v3-what-matters li b,
.eiq-overview-v3-gaps li b {
  color: var(--edgeiq-text-primary);
  font-size: 12px;
}

.eiq-overview-v3-what-matters li span,
.eiq-overview-v3-gaps li span {
  color: var(--edgeiq-text-secondary);
  font-size: 13px;
}

.eiq-overview-v3-inline-gaps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.eiq-overview-v3-inline-gaps small {
  padding: 5px 8px;
  border: 1px solid var(--edgeiq-border);
  border-radius: 999px;
  background: #f8fafc;
}

.eiq-overview-v3-map-lanes {
  display: grid;
  gap: 8px;
}

.eiq-overview-v3-map-lane {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 38px;
  border-bottom: 1px solid var(--edgeiq-border-soft);
}

.eiq-overview-v3-map-lane > div {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.eiq-overview-v3-map-lane b {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 185px;
  padding: 5px 8px;
  border: 1px solid var(--edgeiq-border);
  border-radius: 999px;
  background: #fff;
  color: var(--edgeiq-text-primary);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.eiq-overview-v3-map-lane em {
  color: var(--edgeiq-text-secondary);
  font-style: normal;
  font-weight: 800;
}

.eiq-overview-v3-epi-facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0 0 12px;
}

.eiq-overview-v3-epi-facts div {
  display: grid;
  gap: 3px;
  padding: 8px;
  border: 1px solid var(--edgeiq-border);
  border-radius: 10px;
  background: #f8fafc;
}

.eiq-overview-v3-epi-facts dt {
  color: var(--edgeiq-text-secondary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.eiq-overview-v3-epi-facts dd {
  margin: 0;
  color: var(--edgeiq-text-primary);
  font-weight: 800;
}

.eiq-overview-v3-compact-table {
  min-width: 0 !important;
}

.eiq-overview-v3-map-preview button,
.eiq-overview-v3-epi button,
.eiq-overview-v3-actions button {
  justify-self: start;
  margin-top: 12px;
  border: 1px solid var(--edgeiq-border);
  border-radius: 10px;
  background: #ffffff;
  color: var(--edgeiq-primary);
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
}

.eiq-overview-v3-actions {
  display: grid;
  gap: 8px;
}

.eiq-overview-v3-actions button {
  width: 100%;
  margin: 0;
  padding: 8px 10px;
  text-align: left;
}

.eiq-overview-v3-runner-board .eiq-overview-v1-table th,
.eiq-overview-v3-runner-board .eiq-overview-v1-table td {
  white-space: nowrap;
}

@media (max-width: 1180px) {
  .eiq-overview-v3-summary,
  .eiq-overview-v3-two-up,
  .eiq-overview-v3-layout {
    grid-template-columns: 1fr;
  }
}
'''

TRACE_TEXT = r'''# EDGEiQ Overview Trace V1

## Scope

Workspace: OVERVIEW

This tranche is display-only. It does not alter pricing, EPI, ERI, EPF, map, market, overview, performance-intelligence, weather, or governed builder logic.

## Required Sections

| Display | Canonical source | Service path | Component path | Availability handling |
| --- | --- | --- | --- | --- |
| Summary intelligence cards | `public/data/edgeiq_overview_terminal_feed_v1.csv` | `src/edgeiq-os/race/services/overviewFeed.ts` | `OverviewWorkspace.tsx` | Shows governed evidence where supplied; otherwise compact status text. |
| What Matters Today | `edgeiq_overview_terminal_feed_v1.csv` | `overviewFeed.ts` | `OverviewWorkspace.tsx` | Uses supplied evidence only; no generated narrative. |
| Speed-map preview | `public/data/edgeiq_map_terminal_feed_v1.csv` | `src/edgeiq-os/race/services/mapFeed.ts` | `OverviewWorkspace.tsx` | Shows runner lanes only when governed position evidence exists; otherwise compact awaiting-evidence state. |
| EPI snapshot | `public/data/edgeiq_epi_workspace_terminal_feed_v1.csv` | `src/edgeiq-os/race/services/epiWorkspaceFeed.ts` | `OverviewWorkspace.tsx` | Shows current EPI only where supplied; unavailable remains unavailable. |
| Runner board | `edgeiq_epi_workspace_terminal_feed_v1.csv` joined visually with `edgeiq_map_terminal_feed_v1.csv` by saddlecloth number | `epiWorkspaceFeed.ts`, `mapFeed.ts` | `OverviewWorkspace.tsx` | Displays concise runner rows and governed status; no ranking or calculation. |
| Race reference | Certified performance intelligence package | `src/edgeiq-os/services/performance-intelligence` | `OverviewWorkspace.tsx` | Displays benchmark level/sample/history/profile counts; product-facing confidence is not displayed. |

## Legitimate Data Gaps Observed

Flemington R5 on the current governed three-day feed has overview rows, but current EPI figures and map position evidence are not supplied. The Overview workspace therefore shows race context and runner rows while keeping EPI and map values unavailable.

## Rejected Product Language

The previous Overview UI exposed `Confidence` and command-centre wording. This tranche removes those labels from the product-facing Overview component.
'''


def main() -> None:
    current_component = COMPONENT.read_text(encoding="utf-8")
    if "Race Command Centre" not in current_component or "formatBenchmarkConfidence" not in current_component:
        raise SystemExit("Unexpected OverviewWorkspace source state; aborting.")
    COMPONENT.write_text(COMPONENT_TEXT, encoding="utf-8")

    css_text = CSS.read_text(encoding="utf-8")
    if CSS_MARKER not in css_text:
        CSS.write_text(css_text.rstrip() + "\n\n" + CSS_TEXT.lstrip(), encoding="utf-8")
    else:
        start = css_text.index(CSS_MARKER)
        CSS.write_text(css_text[:start].rstrip() + "\n\n" + CSS_TEXT.lstrip(), encoding="utf-8")

    TRACE.parent.mkdir(parents=True, exist_ok=True)
    TRACE.write_text(TRACE_TEXT, encoding="utf-8")
    print("EDGEIQ_OVERVIEW_FINAL_SPEC_V1_APPLIED")


if __name__ == "__main__":
    main()
