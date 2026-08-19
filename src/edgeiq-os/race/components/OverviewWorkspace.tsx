import { useEffect, useMemo, useState } from "react";

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

  field?: any[];

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



const SUMMARY_SECTIONS = ["Race Environment", "MAP / Race Shape", "Field Intelligence"] as const;

const INTEREST_SECTIONS = ["Race Environment", "MAP / Race Shape", "Field Intelligence", "EDGEiQ Race Read", "Key Race Questions"] as const;



function value(rowValue: unknown): string {

  const text = String(rowValue ?? "").trim();

  if (!text || text === "-" || text === "null" || text === "undefined" || text.toLowerCase() === "none") return "";

  return text;

}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (text && text !== "-" && text.toLowerCase() !== "null" && text.toLowerCase() !== "undefined") return text;
  }
  return "";
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

            <thead><tr><th>NO</th><th>RUNNER</th><th>BAR</th><th>JOCKEY</th><th>EPI</th><th>MARKET</th><th>STATUS</th></tr></thead>

            <tbody>

              {rows.map((row) => {

                const mapRow = mapByNo.get(value(row.no));

                return (

                  <tr key={`${value(row.no)}-${value(row.horse)}`}>

                    <td>{display(row.no, "")}</td>

                    <td><strong>{display(row.horse)}</strong></td>

                    <td>{display(mapRow?.barrier)}</td>

                    <td>Unavailable</td>

                    <td>{display(row.current_epi)}</td>

                    <td>Unavailable</td>

                    <td className={statusClass(row.rowStatus || mapRow?.row_status)}>{display(row.rowStatus || mapRow?.row_status, "Unavailable").replace(/_/g, " ")}</td>

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



export function OverviewWorkspace({ raceKey, meetingKey = null, raceLabel = null, field = [], onOpenTab }: OverviewWorkspaceProps) {

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
    const fallbackField = Array.isArray(field) ? field.slice(0, 12) : [];
    return (
      <section className="eiq-overview-v1 eiq-overview-v3">
        <div className="eiq-overview-v1-hero"><div><p>OVERVIEW</p><h3>{raceLabel || "Race Overview"}</h3><span>Race shell, runner board and next-action structure are available while specialist reads are pending.</span></div><dl><div><dt>Overview</dt><dd>Pending</dd></div><div><dt>Field</dt><dd>{fallbackField.length}</dd></div><div><dt>Map</dt><dd>Pending</dd></div></dl></div>
        <div className="eiq-overview-v3-layout eiq-overview-pixel-v1__layout"><main>
          <div className="eiq-overview-v3-two-up">
            <section className="eiq-overview-v1-card"><span>Tempo Profile</span><strong>Pending</strong><small>Race-shape rows are not matched yet.</small></section>
            <section className="eiq-overview-v1-card"><span>EPI Top 3</span><strong>Pending</strong><small>EPI rows are not matched yet.</small></section>
          </div>
          <section className="eiq-overview-v1-panel"><div className="eiq-overview-v1-panel__title"><span>Runner Board</span><small>Declared runners remain visible for race navigation</small></div><div className="eiq-overview-v1-table-scroll"><table className="eiq-overview-v1-table"><thead><tr><th>No</th><th>Runner</th><th>Current EPI</th><th>Trend</th></tr></thead><tbody>{fallbackField.length ? fallbackField.map((runner, index) => { const no = firstText(runner?.official?.number, runner?.number, runner?.runnerNumber, runner?.saddlecloth, runner?.no, index + 1); const horse = firstText(runner?.official?.runner, runner?.runner, runner?.horse, runner?.runnerName, runner?.name, "Runner pending"); return <tr key={`${no}-${horse}`}><td>{no}</td><td><strong>{horse}</strong></td><td>Pending</td><td>Pending</td></tr>; }) : <tr><td colSpan={4}>Select a race with declared runners to populate the runner board.</td></tr>}</tbody></table></div></section>
        </main><aside className="eiq-overview-v1-side"><section className="eiq-overview-v1-panel"><div className="eiq-overview-v1-panel__title"><span>What Matters Today</span></div><p className="eiq-overview-v1-copy">Race-level overview rows are pending; use FIELD, FORM GUIDE and MAP for available race structure.</p></section></aside></div>
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



      <div className="eiq-overview-v3-layout eiq-overview-pixel-v1__layout">

        <main>

          <div className="eiq-overview-v3-two-up">

            <SpeedMapPreview rows={selectedMapRows} onOpenTab={onOpenTab} />

            <EpiSnapshot rows={epiViewModel.rows} context={performanceContext} onOpenTab={onOpenTab} />

          </div>

          <RunnerBoard epiRows={epiViewModel.rows} mapRows={selectedMapRows} />

        </main>

      </div>

    </section>

  );

}

