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

    <section className="eiq-overview-v4-summary" aria-label="Overview summary intelligence">

      {cards.map((row) => (

        <EiqCard density="compact" className="eiq-overview-v4-card" key={value(row.section)}>
          <EiqMetric
            label={value(row.section)}
            value={display(row.evidence, display(row.status, "Awaiting governed evidence"))}
            detail={<EiqStatusBadge status={display(row.status, "Unavailable")} />}
          />
        </EiqCard>

      ))}

      <EiqCard density="compact" className="eiq-overview-v4-card">
        <EiqMetric
          label="EPI Snapshot"
          value={epiAvailable ? `${epiAvailable} current figures` : "Awaiting EPR figures"}
          detail={epiRows.length ? `${epiRows.length} runners listed` : "No EPR rows"}
        />
      </EiqCard>

      <EiqCard density="compact" className="eiq-overview-v4-card">
        <EiqMetric
          label="Speed Map Preview"
          value={mapEvidence ? `${mapEvidence} position reads` : "Awaiting map evidence"}
          detail={mapRows.length ? `${mapRows.length} active runners` : "No map rows"}
        />
      </EiqCard>

      <EiqCard density="compact" className="eiq-overview-v4-card">
        <EiqMetric
          label="Race Evidence"
          value={rowsWithEvidence.length ? `${rowsWithEvidence.length} populated reads` : "Governed reads pending"}
          detail={rows.length ? `${rows.length} overview sections` : "No overview rows"}
        />
      </EiqCard>

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

    <EiqPanel className="eiq-overview-v4-panel eiq-overview-v3-what-matters">
      <EiqSectionHeader eyebrow="What Matters Today" title="Governed race evidence only" />

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

        <p className="eiq-v1-analytical-copy">The current intelligence feed has not supplied race summary evidence for this race.</p>

      )}

      {pending.length ? (

        <div className="eiq-overview-v3-inline-gaps">

          {pending.map((row) => (

            <small key={`${value(row.section)}-${value(row.status)}`}>{value(row.section)}: {display(row.status, "Pending")}</small>

          ))}

        </div>

      ) : null}

    </EiqPanel>

  );

}



function SpeedMapPreview({ rows, onOpenTab }: { rows: MapTerminalRow[]; onOpenTab?: OverviewWorkspaceProps["onOpenTab"] }) {

  const lanes = ["Lead", "On pace", "Midfield", "Back", "Awaiting"];

  const active = rows.filter((row) => value(row.horse));

  const hasEvidence = active.some((row) => value(row.run_style) || value(row.early_speed) || value(row.projected_position));



  return (

    <EiqPanel className="eiq-overview-v4-panel eiq-overview-v3-map-preview">
      <EiqSectionHeader
        eyebrow="Speed Map Preview"
        title={hasEvidence ? "Race-shape read" : "Awaiting governed positions"}
      />

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

      <EiqButton size="compact" onClick={() => onOpenTab?.("MAP")}>Open MAP</EiqButton>

    </EiqPanel>

  );

}



function EpiSnapshot({ rows, context, onOpenTab }: { rows: BETA013Row[]; context: PerformanceIntelligenceRaceContext | null; onOpenTab?: OverviewWorkspaceProps["onOpenTab"] }) {

  const available = currentEpiRows(rows);

  const topRows = (available.length ? available : rows).slice(0, 6);

  const race = context?.race ?? null;



  return (

    <EiqPanel className="eiq-overview-v4-panel eiq-overview-v3-epi">
      <EiqSectionHeader
        eyebrow="EPI Snapshot"
        title={available.length ? "Current figures" : "Current figures unavailable"}
      />

      <dl className="eiq-overview-v3-epi-facts">

        <div><dt>Benchmark</dt><dd>{race ? formatBenchmarkLevel(race.selected_benchmark_level) : "Unavailable"}</dd></div>

        <div><dt>Sample</dt><dd>{display(race?.selected_benchmark_sample_size)}</dd></div>

        <div><dt>Profiles</dt><dd>{context?.horses.length ?? 0}</dd></div>

      </dl>

      {topRows.length ? (

        <EiqDataTable
          density="dense"
          className="eiq-overview-v4-compact-table"
          wrapperProps={{ className: "eiq-v1-standard-table-scroll eiq-overview-v4-compact-table-scroll" }}
        >

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

        </EiqDataTable>

      ) : (

        <p className="eiq-v1-analytical-copy">EPI terminal rows are not available for this race.</p>

      )}

      <EiqButton size="compact" onClick={() => onOpenTab?.("EPI")}>Open EPI</EiqButton>

    </EiqPanel>

  );

}



function RunnerBoard({ epiRows, mapRows }: { epiRows: BETA013Row[]; mapRows: MapTerminalRow[] }) {

  const mapByNo = new Map(mapRows.map((row) => [value(row.no), row]));

  const rows = epiRows.slice(0, 18);



  return (

    <EiqPanel className="eiq-v1-standard-table-panel eiq-overview-v3-runner-board">
      <EiqSectionHeader eyebrow="Runner Board" title="Concise race-field read" />

      {rows.length ? (

        <EiqDataTable
          density="compact"
          className="eiq-overview-v4-runner-table"
          wrapperProps={{ className: "eiq-v1-standard-table-scroll" }}
        >

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

        </EiqDataTable>

      ) : (

        <p className="eiq-v1-analytical-copy">Runner board rows are not available for this race.</p>

      )}

    </EiqPanel>

  );

}



function DataGaps({ rows, epiRows, mapRows }: { rows: BETA011Row[]; epiRows: BETA013Row[]; mapRows: MapTerminalRow[] }) {

  const gaps = rows.filter((row) => !value(row.evidence) || statusClass(row.status) === "is-pending").slice(0, 5);

  const epiMissing = epiRows.filter((row) => !value(row.current_epi)).length;

  const mapMissing = mapRows.filter((row) => !value(row.run_style) && !value(row.early_speed) && !value(row.projected_position)).length;



  return (

    <EiqPanel className="eiq-overview-v4-panel eiq-overview-v3-gaps">
      <EiqSectionHeader eyebrow="Data Gaps" title="Restrained unavailable state" />

      <ul>

        {gaps.map((row) => <li key={`${value(row.section)}-${value(row.status)}`}><b>{value(row.section)}</b><span>{display(row.status, "Pending")}</span></li>)}

        {epiMissing ? <li><b>EPR Snapshot</b><span>{epiMissing} runners awaiting current EPR</span></li> : null}

        {mapMissing ? <li><b>Speed Map</b><span>{mapMissing} runners awaiting position evidence</span></li> : null}

      </ul>

    </EiqPanel>

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

    return <section className="eiq-overview-v4-workspace eiq-v1-standard-workspace"><EiqEmptyState title="Loading overview evidence." /></section>;

  }



  if (error) {

    return <section className="eiq-overview-v4-workspace eiq-v1-standard-workspace"><EiqEmptyState title={error} /></section>;

  }



  if (!viewModel.rows.length && !epiViewModel.rows.length && !selectedMapRows.length) {
    const fallbackField = Array.isArray(field) ? field.slice(0, 12) : [];
    return (
      <section className="eiq-overview-v4-workspace eiq-v1-standard-workspace">
        <EiqPanel className="eiq-overview-v4-intro"><EiqSectionHeader eyebrow="OVERVIEW" title={raceLabel || "Race Overview"} meta={<EiqBadge tone="warning">Pending</EiqBadge>} /><p className="eiq-v1-analytical-copy">Race shell, runner board and next-action structure are available while specialist reads are pending.</p><dl className="eiq-v1-inline-facts"><div><dt>Overview</dt><dd>Pending</dd></div><div><dt>Field</dt><dd>{fallbackField.length}</dd></div><div><dt>Map</dt><dd>Pending</dd></div></dl></EiqPanel>
        <div className="eiq-overview-v4-layout"><main>
          <div className="eiq-overview-v3-two-up">
            <EiqCard><EiqMetric label="Tempo Profile" value="Pending" detail="Race-shape rows are not matched yet." /></EiqCard>
            <EiqCard><EiqMetric label="EPR Top 3" value="Pending" detail="EPR rows are not matched yet." /></EiqCard>
          </div>
          <EiqPanel className="eiq-v1-standard-table-panel"><EiqSectionHeader eyebrow="Runner Board" title="Declared runners remain visible for race navigation" /><EiqDataTable density="compact" className="eiq-overview-v4-runner-table" wrapperProps={{ className: "eiq-v1-standard-table-scroll" }}><thead><tr><th>No</th><th>Runner</th><th>Current EPR</th><th>Trend</th></tr></thead><tbody>{fallbackField.length ? fallbackField.map((runner, index) => { const no = firstText(runner?.official?.number, runner?.number, runner?.runnerNumber, runner?.saddlecloth, runner?.no, index + 1); const horse = firstText(runner?.official?.runner, runner?.runner, runner?.horse, runner?.runnerName, runner?.name, "Runner pending"); return <tr key={`${no}-${horse}`}><td>{no}</td><td><strong>{horse}</strong></td><td>Pending</td><td>Pending</td></tr>; }) : <tr><td colSpan={4}>Select a race with declared runners to populate the runner board.</td></tr>}</tbody></EiqDataTable></EiqPanel>
        </main><EiqSidePanel className="eiq-v1-analytical-side-panel"><section className="eiq-v1-side-panel-section"><EiqSectionHeader title="What Matters Today" /><p className="eiq-v1-analytical-copy">Race-level overview rows are pending; use FIELD, FORM GUIDE and MAP for available race structure.</p></section></EiqSidePanel></div>
      </section>
    );
  }



  return (

    <section className="eiq-overview-v4-workspace eiq-v1-standard-workspace">

      <EiqPanel className="eiq-overview-v4-intro">
        <EiqSectionHeader
          eyebrow="OVERVIEW"
          title={raceLabel || "Race Overview"}
          meta={<EiqBadge tone="info">Race summary</EiqBadge>}
        />
        <p className="eiq-v1-analytical-copy">Concise race summary, speed-map preview, EPI snapshot and runner board.</p>
        <dl className="eiq-v1-inline-facts">

          <div><dt>Overview</dt><dd>{viewModel.rows.length}</dd></div>

          <div><dt>EPI Rows</dt><dd>{epiViewModel.rows.length}</dd></div>

          <div><dt>Map Rows</dt><dd>{selectedMapRows.length}</dd></div>

        </dl>

      </EiqPanel>



      <SummaryCards rows={viewModel.rows} epiRows={epiViewModel.rows} mapRows={selectedMapRows} />



      <div className="eiq-overview-v4-layout">

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
