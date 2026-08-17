import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import type { ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import { canonicalTrackDisplayName } from "../../design-system/presentation";
import {
  buildMapViewModel,
  loadMapTerminalFeed,
  type BETA009Row,
  type BETA009ViewModel,
} from "../services/mapFeed";
import {
  EiqBadge,
  EiqDataTable,
  EiqEmptyState,
  EiqPanel,
  EiqSectionHeader,
  EiqSidePanel,
  EiqStatusBadge,
} from "../../design-system/v1";

type RaceBook = Record<string, unknown>;
type RaceFieldRunner = ThreeDayRunner & Record<string, unknown>;

type MapWorkspaceProps = {
  raceBook: RaceBook;
  field?: RaceFieldRunner[];
  selectedRunner?: RaceFieldRunner | null;
  clean: (value: unknown) => string;
  market: (value: unknown) => string;
  onOpenRunner?: (runner: RaceFieldRunner) => void;
  mode?: string;
};

const GOVERNED_UNRESOLVED_SOURCE_STATE = "UNRESOLVED";

function readValue(record: unknown, path: string[]): unknown {
  let current = record;
  for (const key of path) {
    if (current && typeof current === "object" && key in current) {
      current = (current as Record<string, unknown>)[key];
    } else {
      return undefined;
    }
  }
  return current;
}

function text(value: unknown): string {
  if (value === null || value === undefined) return "";
  const output = String(value).trim();
  return output === "-" ? "" : output;
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const output = text(value);
    if (output) return output;
  }
  return "";
}

function officialRace(raceBook: RaceBook, field: RaceFieldRunner[]): ThreeDayRace {
  const official = (raceBook.official ?? {}) as Record<string, unknown>;
  const source = (raceBook.source ?? {}) as Record<string, unknown>;
  return {
    raceKey: text(official.raceKey) || text(source.raceKey) || `${text(official.meeting)}|R${text(official.raceNumber)}`,
    raceNumber: Number(text(official.raceNumber) || text(source.raceNumber) || 0),
    raceName: text(official.raceName) || text(source.raceName) || `Race ${text(official.raceNumber)}`,
    distance: text(official.distance) || null,
    raceClass: text(official.raceClass) || null,
    raceTime: text(official.raceTime) || null,
    trackCondition: text(official.trackCondition) || text(official.condition) || null,
    rail: text(official.rail) || null,
    runners: field,
    source,
  };
}

function fieldFromRaceBook(raceBook: RaceBook): RaceFieldRunner[] {
  const value = readValue(raceBook, ["field"]);
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is RaceFieldRunner => Boolean(entry) && typeof entry === "object");
}

function raceTrackName(raceBook: RaceBook): string {
  const official = (raceBook.official ?? {}) as Record<string, unknown>;
  const source = (raceBook.source ?? {}) as Record<string, unknown>;
  return canonicalTrackDisplayName(firstText(
    official.track,
    official.meeting,
    source.track,
    source.meeting,
    source.meetingName,
  ));
}

function resolveTrackMapAsset(trackName: string): string {
  const normalised = trackName.toUpperCase().replace(/[^A-Z]/g, "");
  if (normalised.includes("FLEMINGTON")) return "/assets/tracks/flemington_edgeiq.svg";
  if (normalised.includes("CAULFIELD")) return "/assets/tracks/caulfield_edgeiq.svg";
  return "";
}

function rowValue(value: string | null): string {
  return value && value.trim() ? value : "";
}

function rowRunnerName(row: BETA009Row): string {
  return rowValue(row.horse) || "Runner";
}

function rowNumber(row: BETA009Row): string {
  return rowValue(row.no) || "";
}

function rowSpeed(row: BETA009Row): string {
  return rowValue(row.early_speed);
}

function rowEvidenceLabel(row: BETA009Row): string {
  if (row.run_style || row.early_speed || row.projected_position) return "Position read";
  return "Speed evidence unavailable";
}

function rowHasMapEvidence(row: BETA009Row): boolean {
  return Boolean(row.run_style || row.early_speed || row.projected_position);
}

function selectedRunnerName(runner?: RaceFieldRunner | null): string {
  if (!runner) return "";
  return (
    text(runner.official?.runner) ||
    text(runner.source?.horseName) ||
    text(runner.source?.runnerName) ||
    text(runner.source?.horse)
  );
}

function rowForRunner(rows: BETA009Row[], runner?: RaceFieldRunner | null): BETA009Row | null {
  const name = selectedRunnerName(runner).toUpperCase();
  if (!name) return rows[0] ?? null;
  return rows.find((row) => rowRunnerName(row).toUpperCase() === name) ?? rows[0] ?? null;
}

function barrierNumber(row: BETA009Row): number | null {
  const parsed = Number(row.effective_barrier ?? row.barrier ?? "");
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function laneLeftPercent(row: BETA009Row): number {
  const speed = Number(rowSpeed(row));
  if (Number.isFinite(speed) && speed > 0) {
    return Math.max(10, Math.min(68, 76 - speed * 0.62));
  }
  const style = rowValue(row.run_style).toUpperCase();
  if (style.includes("LEAD")) return 18;
  if (style.includes("PACE") || style.includes("FORWARD")) return 30;
  if (style.includes("MID")) return 46;
  if (style.includes("BACK")) return 62;
  return 76;
}

function mapLineStyle(row: BETA009Row): CSSProperties {
  return { "--eiq-map-left": `${laneLeftPercent(row)}%` } as CSSProperties;
}

function runnerText(row: BETA009Row, officialKey: string, sourceKeys: string[] = []): string {
  const runner = row.runner as RaceFieldRunner | null | undefined;
  if (!runner) return "";
  const official = (runner.official ?? {}) as Record<string, unknown>;
  const source = (runner.source ?? {}) as Record<string, unknown>;
  const candidates = [official[officialKey], ...sourceKeys.map((key) => source[key])];
  return firstText(...candidates);
}

function runnerJockey(row: BETA009Row): string {
  return runnerText(row, "jockey", ["jockeyName", "jockey"]);
}

function runnerTrainer(row: BETA009Row): string {
  return runnerText(row, "trainer", ["trainerName", "trainer"]);
}

function runnerWeight(row: BETA009Row): string {
  return runnerText(row, "weight", ["weight", "weightAllocated"]);
}

function runnerSilk(row: BETA009Row): string {
  return runnerText(row, "silkUrl", ["silkUrl", "silk_url", "silks", "silk"]);
}

function SilkCell({ row }: { row: BETA009Row }) {
  const silk = runnerSilk(row);
  if (!silk) return <span className="eiq-map-v1-silk-placeholder">-</span>;
  return <img className="eiq-map-v1-silk" src={silk} alt="" loading="lazy" />;
}

function MapVisual({
  rows,
  onOpenRunner,
  trackAsset,
}: {
  rows: BETA009Row[];
  onOpenRunner?: (runner: RaceFieldRunner) => void;
  trackAsset?: string;
}) {
  const barrierRows = rows.map((row) => {
    const barrier = barrierNumber(row);
    return { row, barrier };
  });

  return (
    <EiqPanel className="eiq-map-v2-visual-panel">
      <EiqSectionHeader
        eyebrow="Race Map"
        title="Predicted settling positions"
        meta={<EiqBadge tone="info">Right to left</EiqBadge>}
      />
      <div className="eiq-map-v1-direction" aria-hidden="true">
        <span>Racing direction</span>
        <strong>←</strong>
      </div>
      <div className="eiq-map-v1-visual" data-map-orientation="victorian-right-to-left">
        {trackAsset ? <img className="eiq-map-v1-track-img" src={trackAsset} alt="" loading="lazy" /> : null}
        <div className="eiq-map-v1-visual__surface">
          {barrierRows.map(({ row }) => {
            const runner = row.runner as RaceFieldRunner | null | undefined;
            const speed = rowSpeed(row);
            const hasEvidence = rowHasMapEvidence(row);
            return (
              <button
                type="button"
                className={`eiq-map-v1-runner-line${hasEvidence ? "" : " is-unavailable"}`}
                style={mapLineStyle(row)}
                key={`${rowNumber(row)}-${rowRunnerName(row)}`}
                onClick={() => runner && onOpenRunner?.(runner)}
                disabled={!runner}
                aria-label={`${rowNumber(row)} ${rowRunnerName(row)} ${rowEvidenceLabel(row)}`}
              >
                <span className="eiq-map-v1-runner-line__bar" aria-hidden="true" />
                <span className="eiq-map-v1-runner-line__label">
                  <strong>{rowNumber(row)}</strong>
                  <em>{rowRunnerName(row)}</em>
                  <span>{rowSpeed(row) || "No speed"}</span>
                </span>
              </button>
            );
          })}
        </div>
        <div className="eiq-map-v1-barriers" aria-label="Barriers">
          {barrierRows.map(({ row, barrier }) => (
            <span key={`barrier-${rowNumber(row)}-${rowRunnerName(row)}`}>{barrier ?? "-"}</span>
          ))}
        </div>
      </div>
    </EiqPanel>
  );
}

function MapTable({ rows }: { rows: BETA009Row[] }) {
  return (
    <EiqPanel className="eiq-v1-standard-table-panel">
      <EiqSectionHeader eyebrow="Runner Map Table" title="Governed barrier, personnel and speed read" />
      <EiqDataTable
        density="compact"
        className="eiq-map-v2-table"
        wrapperProps={{ className: "eiq-v1-standard-table-scroll" }}
      >
          <thead>
            <tr>
              <th>No</th>
              <th>Silks</th>
              <th>Runner</th>
              <th>Barrier</th>
              <th>Jockey</th>
              <th>Trainer</th>
              <th>Weight</th>
              <th>EPI SPD</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`table-${rowNumber(row)}-${rowRunnerName(row)}`}>
                <td>{rowNumber(row)}</td>
                <td><SilkCell row={row} /></td>
                <td><strong>{rowRunnerName(row)}</strong></td>
                <td>{rowValue(row.effective_barrier) || rowValue(row.barrier)}</td>
                <td>{runnerJockey(row) || "-"}</td>
                <td>{runnerTrainer(row) || "-"}</td>
                <td>{runnerWeight(row) || "-"}</td>
                <td>{rowSpeed(row) || "-"}</td>
              </tr>
            ))}
          </tbody>
      </EiqDataTable>
    </EiqPanel>
  );
}

function MapReadPanel({ viewModel }: { viewModel: BETA009ViewModel }) {
  const mappedRows = viewModel.rows.filter((row) => rowHasMapEvidence(row));
  const leaders = mappedRows
    .filter((row) => rowValue(row.run_style).toUpperCase().includes("LEAD"))
    .slice(0, 3);
  const onPace = mappedRows
    .filter((row) => /PACE|FORWARD/i.test(rowValue(row.run_style)))
    .slice(0, 3);
  const pendingCount = Math.max(0, viewModel.rows.length - mappedRows.length);

  return (
    <EiqSidePanel className="eiq-v1-analytical-side-panel">
      <section className="eiq-v1-side-panel-section">
        <EiqSectionHeader title="Race Shape Summary" />
        <dl className="eiq-v1-side-facts">
          <div><dt>Active Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Position Reads</dt><dd>{mappedRows.length}</dd></div>
          <div><dt>Awaiting Evidence</dt><dd>{pendingCount}</dd></div>
          <div><dt>Map Status</dt><dd><EiqStatusBadge status={viewModel.status === "current" ? "Current" : "Governed Pending"} /></dd></div>
        </dl>
      </section>
      <section className="eiq-v1-side-panel-section">
        <EiqSectionHeader title="Tactical Notes" />
        {mappedRows.length ? (
          <ul className="eiq-map-v1-notes eiq-v1-standard-list">
            <li>Settling positions use governed speed/map reads where available.</li>
            <li>Barriers are compressed after scratchings and shown high-to-low.</li>
            <li>Plain blue lanes show race orientation without heat-map colouring.</li>
          </ul>
        ) : (
          <p className="eiq-v1-analytical-copy">
            Runners without governed speed evidence stay at the barrier side. Barrier order remains available for race-shape review.
          </p>
        )}
      </section>
      <section className="eiq-v1-side-panel-section">
        <EiqSectionHeader title="Key Runner Positions" />
        <div className="eiq-map-v1-key-positions">
          <div>
            <span>Leaders</span>
            <strong>{leaders.map(rowRunnerName).join(", ") || "Pending"}</strong>
          </div>
          <div>
            <span>On pace</span>
            <strong>{onPace.map(rowRunnerName).join(", ") || "Pending"}</strong>
          </div>
          <div>
            <span>Evidence</span>
            <strong>{mappedRows.length ? "Governed map feed" : "Barrier order only"}</strong>
          </div>
        </div>
      </section>
    </EiqSidePanel>
  );
}

function RunnerMap({ viewModel, selectedRunner }: { viewModel: BETA009ViewModel; selectedRunner?: RaceFieldRunner | null }) {
  const row = rowForRunner(viewModel.rows, selectedRunner);
  if (!row) {
    return (
      <section className="eiq-map-v2-workspace eiq-v1-standard-workspace">
        <EiqEmptyState title="Map rows are unavailable for this runner." />
      </section>
    );
  }
  return (
    <section className="eiq-map-v2-workspace eiq-v1-standard-workspace">
      <EiqPanel className="eiq-map-v2-intro">
        <EiqSectionHeader eyebrow="MAP" title={rowRunnerName(row)} meta={<EiqBadge tone="info">Runner read</EiqBadge>} />
        <p className="eiq-v1-analytical-copy">Runner-level barrier and speed-position read.</p>
      </EiqPanel>
      <div className="eiq-map-v1-runner-grid eiq-v1-analytical-grid">
        <EiqPanel>
          <EiqSectionHeader title="Runner Map" />
          <dl className="eiq-v1-side-facts eiq-map-v2-runner-facts">
            <div><dt>Barrier</dt><dd>{rowValue(row.barrier) || "-"}</dd></div>
            <div><dt>Effective Barrier</dt><dd>{rowValue(row.effective_barrier) || "-"}</dd></div>
            <div><dt>Run Style</dt><dd>{rowValue(row.run_style) || "-"}</dd></div>
            <div><dt>Early Speed</dt><dd>{rowSpeed(row) || "-"}</dd></div>
            <div><dt>Projected Position</dt><dd>{rowValue(row.projected_position) || "-"}</dd></div>
            <div><dt>Evidence</dt><dd>{rowEvidenceLabel(row)}</dd></div>
          </dl>
        </EiqPanel>
        <MapTable rows={[row]} />
      </div>
    </section>
  );
}

export function MapWorkspace(props: MapWorkspaceProps) {
  const field = props.field ?? fieldFromRaceBook(props.raceBook);
  const race = useMemo(() => officialRace(props.raceBook, field), [props.raceBook, field]);
  const [rows, setRows] = useState<Awaited<ReturnType<typeof loadMapTerminalFeed>>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadMapTerminalFeed()
      .then((feedRows) => {
        if (!cancelled) {
          setRows(feedRows);
          setError(null);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setRows([]);
          setError(loadError instanceof Error ? loadError.message : "Map feed failed");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const viewModel = useMemo(() => buildMapViewModel(race, rows), [race, rows]);

  if (error) {
    return <section className="eiq-map-v2-workspace eiq-v1-standard-workspace"><EiqEmptyState title={error} /></section>;
  }

  if (props.selectedRunner) {
    return <RunnerMap viewModel={viewModel} selectedRunner={props.selectedRunner} />;
  }

  if (!viewModel.rows.length) {
    return (
      <section className="eiq-map-v2-workspace eiq-v1-standard-workspace">
        <EiqEmptyState title="Governed map rows are not available for this race." />
      </section>
    );
  }

  return (
    <section className="eiq-map-v2-workspace eiq-v1-standard-workspace">
      <EiqPanel className="eiq-map-v2-intro">
        <EiqSectionHeader
          eyebrow="MAP"
          title="How will this race be run?"
          meta={<EiqBadge tone="info">Traditional barrier map</EiqBadge>}
        />
        <p className="eiq-v1-analytical-copy">Traditional barrier map. Right-to-left travel. Plain blue lanes.</p>
        <dl className="eiq-v1-inline-facts">
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Race Read</dt><dd>{viewModel.status === "current" ? "Available" : "Pending"}</dd></div>
        </dl>
      </EiqPanel>
      <div className="eiq-map-v1-grid eiq-map-v2-grid eiq-v1-analytical-grid">
        <MapVisual rows={viewModel.rows} onOpenRunner={props.onOpenRunner} trackAsset={resolveTrackMapAsset(raceTrackName(props.raceBook))} />
        <MapReadPanel viewModel={viewModel} />
      </div>
      <MapTable rows={viewModel.rows} />
    </section>
  );
}
