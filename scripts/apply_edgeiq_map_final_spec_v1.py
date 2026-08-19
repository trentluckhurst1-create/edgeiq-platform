from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP_COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"
MAP_SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "mapFeed.ts"
CSS_FILE = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
TRACE_FILE = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_MAP_TRACE_V1.md"


MAP_COMPONENT_SOURCE = r'''import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import type { ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import {
  buildMapViewModel,
  loadMapTerminalFeed,
  type BETA009Row,
  type BETA009ViewModel,
} from "../services/mapFeed";
import { resolveTrackMapAsset } from "../services/trackMapAssets";

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
  return firstText(
    official.track,
    official.meeting,
    source.track,
    source.meeting,
    source.meetingName,
  );
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
}: {
  rows: BETA009Row[];
  onOpenRunner?: (runner: RaceFieldRunner) => void;
}) {
  return (
    <section className="eiq-map-v1-panel eiq-map-v1-visual-panel">
      <div className="eiq-map-v1-panel__title">
        <span>Speed Map</span>
        <small>Right-to-left. Barrier 1 bottom. Straight blue lanes only.</small>
      </div>
      <div className="eiq-map-v1-visual" data-map-orientation="victorian-right-to-left">
        <div className="eiq-map-v1-visual__surface">
          {rows.map((row) => {
            const runner = row.runner as RaceFieldRunner | null | undefined;
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
                {hasEvidence ? <span className="eiq-map-v1-runner-line__bar" aria-hidden="true" /> : null}
                <span className="eiq-map-v1-runner-line__label">
                  <strong>{rowNumber(row)}</strong>
                  <span>{rowSpeed(row) || "No speed"}</span>
                  <em>{rowRunnerName(row)}</em>
                </span>
              </button>
            );
          })}
        </div>
        <div className="eiq-map-v1-barriers" aria-label="Barriers">
          {rows.map((row) => (
            <span key={`barrier-${rowNumber(row)}-${rowRunnerName(row)}`}>{rowValue(row.effective_barrier) || rowValue(row.barrier)}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

function MapTable({ rows }: { rows: BETA009Row[] }) {
  return (
    <section className="eiq-map-v1-panel">
      <div className="eiq-map-v1-panel__title">
        <span>Runner Map Table</span>
        <small>Governed barrier, personnel and speed read</small>
      </div>
      <div className="eiq-map-v1-table-scroll">
        <table className="eiq-map-v1-table">
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
        </table>
      </div>
    </section>
  );
}

function TrackAssetPanel({ raceBook, race }: { raceBook: RaceBook; race: ThreeDayRace }) {
  const trackName = raceTrackName(raceBook);
  const asset = resolveTrackMapAsset(trackName, race.trackCondition);
  return (
    <section className="eiq-map-v1-panel">
      <div className="eiq-map-v1-panel__title">
        <span>Track Map</span>
        <small>{asset?.canonicalTrack ?? trackName}</small>
      </div>
      {asset ? (
        <img className="eiq-map-v1-track-img" src={asset.assetPath} alt={`${asset.canonicalTrack} track map`} />
      ) : (
        <p className="eiq-map-v1-copy">Curated track map is unavailable for this meeting.</p>
      )}
    </section>
  );
}

function MapReadPanel({ viewModel, raceBook, race }: { viewModel: BETA009ViewModel; raceBook: RaceBook; race: ThreeDayRace }) {
  const mappedCount = viewModel.rows.filter((row) => rowHasMapEvidence(row)).length;
  const pendingCount = Math.max(0, viewModel.rows.length - mappedCount);

  return (
    <aside className="eiq-map-v1-side">
      <section className="eiq-map-v1-panel">
        <div className="eiq-map-v1-panel__title"><span>Race Shape Read</span></div>
        <dl className="eiq-map-v1-facts">
          <div><dt>Active Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Position Reads</dt><dd>{mappedCount}</dd></div>
          <div><dt>Awaiting Evidence</dt><dd>{pendingCount}</dd></div>
        </dl>
      </section>
      <TrackAssetPanel raceBook={raceBook} race={race} />
      <section className="eiq-map-v1-panel" data-empty-source-state={GOVERNED_UNRESOLVED_SOURCE_STATE}>
        <div className="eiq-map-v1-panel__title"><span>Map Note</span></div>
        <p className="eiq-map-v1-copy">
          Runners without governed speed evidence stay at the barrier side with no lane drawn.
        </p>
      </section>
    </aside>
  );
}

function RunnerMap({ viewModel, selectedRunner }: { viewModel: BETA009ViewModel; selectedRunner?: RaceFieldRunner | null }) {
  const row = rowForRunner(viewModel.rows, selectedRunner);
  if (!row) {
    return (
      <section className="eiq-map-v1">
        <div className="eiq-map-v1-empty">Map rows are unavailable for this runner.</div>
      </section>
    );
  }
  return (
    <section className="eiq-map-v1">
      <div className="eiq-map-v1-hero">
        <div>
          <p>MAP</p>
          <h3>{rowRunnerName(row)}</h3>
          <span>Runner-level barrier and speed-position read.</span>
        </div>
      </div>
      <div className="eiq-map-v1-runner-grid">
        <section className="eiq-map-v1-panel">
          <div className="eiq-map-v1-panel__title"><span>Runner Map</span></div>
          <dl className="eiq-map-v1-facts">
            <div><dt>Barrier</dt><dd>{rowValue(row.barrier) || "-"}</dd></div>
            <div><dt>Effective Barrier</dt><dd>{rowValue(row.effective_barrier) || "-"}</dd></div>
            <div><dt>Run Style</dt><dd>{rowValue(row.run_style) || "-"}</dd></div>
            <div><dt>Early Speed</dt><dd>{rowSpeed(row) || "-"}</dd></div>
            <div><dt>Projected Position</dt><dd>{rowValue(row.projected_position) || "-"}</dd></div>
            <div><dt>Evidence</dt><dd>{rowEvidenceLabel(row)}</dd></div>
          </dl>
        </section>
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
    return <section className="eiq-map-v1"><div className="eiq-map-v1-empty">{error}</div></section>;
  }

  if (props.selectedRunner) {
    return <RunnerMap viewModel={viewModel} selectedRunner={props.selectedRunner} />;
  }

  if (!viewModel.rows.length) {
    return (
      <section className="eiq-map-v1">
        <div className="eiq-map-v1-empty">Governed map rows are not available for this race.</div>
      </section>
    );
  }

  return (
    <section className="eiq-map-v1">
      <div className="eiq-map-v1-hero">
        <div>
          <p>MAP</p>
          <h3>How will this race be run?</h3>
          <span>Victorian orientation. Barriers right. Active runners only.</span>
        </div>
        <dl>
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Race Read</dt><dd>{viewModel.status === "current" ? "Available" : "Pending"}</dd></div>
        </dl>
      </div>
      <div className="eiq-map-v1-grid">
        <MapVisual rows={viewModel.rows} onOpenRunner={props.onOpenRunner} />
        <MapReadPanel viewModel={viewModel} raceBook={props.raceBook} race={race} />
      </div>
      <MapTable rows={viewModel.rows} />
    </section>
  );
}
'''


TRACE_SOURCE = """# EDGEiQ MAP Trace V1

## Workspace intent

MAP answers: How will this race be run?

The workspace is a governed speed-position display. It is not a replay, a barrier heat map, a coloured lane diagram, or a position simulation.

## Governed inputs

- Selected race context: `threeDayCatalog` race book and field passed into `MapWorkspace`.
- Runner identity: official race runners from the selected race context.
- Barrier and effective barrier: `edgeiq_map_terminal_feed_v1.csv` where matched, otherwise selected-race official barrier from catalog.
- Run style, early speed and projected position: `edgeiq_map_terminal_feed_v1.csv`.
- Scratchings: existing governed runner status fields from catalog/source status/market text. The service filters scratched runners before display and keeps supplied effective barriers; React does not recalculate official barriers.
- Track map asset: `trackMapAssets.ts` using the selected meeting/track name.

## Display rules implemented

- Victorian orientation is marked with `data-map-orientation=\"victorian-right-to-left\"`.
- Barriers render on the right.
- Rows are sorted by effective barrier descending, so barrier 1 renders at the bottom where present.
- Runner lanes are straight blue horizontal lines.
- Runner labels contain saddlecloth number, governed speed value when available, and horse name.
- Saddlecloth numbers are neutral text chips, not coloured backgrounds.
- Runners without speed/run-style/projected-position evidence stay at the barrier side and draw no lane.

## Known governed-data gaps

- If `edgeiq_map_terminal_feed_v1.csv` has no early speed for a runner, the label shows `No speed`.
- If no curated track map resolves for a meeting, the workspace shows an honest unavailable track-map state.
- No official sectional times are exposed in MAP.
"""


CSS_APPEND = r'''

/* EDGEiQ MAP final-spec alignment: white theme, straight blue lanes, neutral saddlecloth labels. */
.eiq-map-v1-visual-panel {
  overflow: hidden;
}

.eiq-map-v1-visual {
  grid-template-columns: minmax(0, 1fr) 64px;
  min-height: 430px;
}

.eiq-map-v1-runner-line__bar {
  left: var(--eiq-map-left);
  right: 8px;
  height: 3px;
  background: #1f5fd6;
  box-shadow: none;
}

.eiq-map-v1-runner-line__label {
  left: auto;
  max-width: min(360px, calc(100% - var(--eiq-map-left) - 16px));
  margin-left: var(--eiq-map-left);
  border-radius: 8px;
}

.eiq-map-v1-runner-line__label strong {
  min-width: 24px;
  height: 22px;
  border: 1px solid #d7dce5;
  border-radius: 6px;
  background: #ffffff;
  color: #172033;
}

.eiq-map-v1-runner-line__label span {
  min-width: 42px;
  color: #1f5fd6;
  font-size: 12px;
  font-weight: 700;
  text-align: right;
}

.eiq-map-v1-runner-line.is-unavailable .eiq-map-v1-runner-line__label {
  margin-left: 70%;
  opacity: 0.78;
}

.eiq-map-v1-runner-line.is-unavailable .eiq-map-v1-runner-line__label span {
  color: #7c8798;
  font-weight: 650;
}

.eiq-map-v1-track-img {
  display: block;
  width: 100%;
  max-height: 220px;
  object-fit: contain;
  border: 1px solid #e5e8ee;
  border-radius: 10px;
  background: #fafbfc;
}

.eiq-map-v1-silk {
  display: inline-block;
  width: 28px;
  height: 28px;
  object-fit: contain;
  vertical-align: middle;
}

.eiq-map-v1-silk-placeholder {
  color: #7c8798;
}

.eiq-map-v1-table {
  min-width: 980px;
}

.eiq-map-v1-table th:nth-child(3),
.eiq-map-v1-table td:nth-child(3) {
  min-width: 190px;
  text-align: left;
}
'''


def replace_once(source: str, old: str, new: str, label: str) -> str:
  if old not in source:
    raise RuntimeError(f"Could not find replacement target: {label}")
  return source.replace(old, new, 1)


def update_service() -> None:
  source = MAP_SERVICE.read_text(encoding="utf-8")
  if "function isScratchedRunner" not in source:
    insert_after = """function runnerNo(runner: ThreeDayRunner, index: number): string {
  return firstText(runner.official.no, runner.official.number, runner.source?.runnerNumber, runner.source?.runner_no, runner.source?.saddlecloth, index + 1);
}
"""
    insertion = insert_after + """
function isScratchedRunner(runner: ThreeDayRunner): boolean {
  const official = runner.official as Record<string, unknown>;
  const source = runner.source ?? {};
  const statusText = [
    official.status,
    source.status,
    source.runnerStatus,
    source.scratchingStatus,
    source.scratched,
    source.market,
    source.fixedOdds,
    source.price,
  ]
    .map((value) => String(value ?? "").toUpperCase())
    .join(" ");
  return statusText.includes("SCRATCH");
}
"""
    source = replace_once(source, insert_after, insertion, "insert isScratchedRunner")

  old_map = "  const shaped = race.runners.map((runner, index) => {"
  new_map = "  const activeRunners = race.runners.filter((runner) => !isScratchedRunner(runner));\n  const shaped = activeRunners.map((runner, index) => {"
  if old_map in source and "const activeRunners = race.runners.filter" not in source:
    source = source.replace(old_map, new_map, 1)

  MAP_SERVICE.write_text(source, encoding="utf-8")


def update_css() -> None:
  source = CSS_FILE.read_text(encoding="utf-8")
  if "EDGEiQ MAP final-spec alignment" not in source:
    CSS_FILE.write_text(source.rstrip() + "\n" + CSS_APPEND.lstrip(), encoding="utf-8")


def main() -> None:
  MAP_COMPONENT.write_text(MAP_COMPONENT_SOURCE, encoding="utf-8")
  update_service()
  update_css()
  TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
  TRACE_FILE.write_text(TRACE_SOURCE, encoding="utf-8")
  print("EDGEIQ_MAP_FINAL_SPEC_PATCH_APPLIED")


if __name__ == "__main__":
  main()
