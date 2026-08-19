from __future__ import annotations

from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


MAP_WORKSPACE_TSX = r'''import type { CSSProperties } from "react";

type RaceBook = Record<string, unknown>;
type RaceFieldRunner = Record<string, unknown>;

type MapWorkspaceProps = {
  raceBook: RaceBook;
  field?: RaceFieldRunner[];
  selectedRunner?: RaceFieldRunner | null;
  clean: (value: unknown) => string;
  market: (value: unknown) => string;
  onOpenRunner?: (runner: RaceFieldRunner) => void;
  mode?: string;
};

type MapLane = "LEADERS" | "ON PACE" | "MIDFIELD" | "BACK";
type MapConfidence = "Strong evidence" | "Supported" | "Limited evidence";
type MapSource = "settling-pattern" | "single-settling" | "profile" | "shared-template" | "limited";

type MapObservation = {
  label: string;
  position: number;
};

type MapRunner = {
  runner: RaceFieldRunner;
  fieldIndex: number;
  runnerName: string;
  number: string;
  barrier: number | null;
  barrierSort: number;
  jockey: string;
  trainer: string;
  weight: string;
  marketText: string;
  lane: MapLane;
  descriptor: string;
  confidence: MapConfidence;
  source: MapSource;
  evidenceRead: string;
  settlingPosition: number | null;
  scratched: boolean;
};

const LANE_LABELS: Record<MapLane, string> = {
  LEADERS: "Leader",
  "ON PACE": "On pace",
  MIDFIELD: "Midfield",
  BACK: "Back",
};

const PROJECTION_END: Record<MapLane, number> = {
  LEADERS: 14,
  "ON PACE": 34,
  MIDFIELD: 58,
  BACK: 78,
};

const ZONE_LABELS = ["LEAD / FORWARD", "ON PACE", "MIDFIELD", "REARWARD", "BARRIERS / START"];

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

function toText(value: unknown, fallback = "-"): string {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text.length ? text : fallback;
}

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const match = value.match(/-?\d+(?:\.\d+)?/);
    if (match) {
      const parsed = Number(match[0]);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}

function runnerName(runner: RaceFieldRunner): string {
  return toText(readValue(runner, ["horse", "name"]), "Runner");
}

function runnerNumber(runner: RaceFieldRunner): string {
  return toText(readValue(runner, ["official", "number"]), "-");
}

function runnerBarrier(runner: RaceFieldRunner): number | null {
  const barrier = toNumber(readValue(runner, ["official", "barrier"]));
  if (barrier && barrier > 0) return barrier;
  return null;
}

function runnerJockey(runner: RaceFieldRunner): string {
  return toText(readValue(runner, ["connections", "jockey"]), "-");
}

function runnerTrainer(runner: RaceFieldRunner): string {
  return toText(readValue(runner, ["connections", "trainer"]), "-");
}

function runnerWeight(runner: RaceFieldRunner): string {
  return toText(readValue(runner, ["official", "weight"]), "-");
}

function marketText(runner: RaceFieldRunner, market: (value: unknown) => string): string {
  const value = readValue(runner, ["market", "price"]);
  const text = market(value);
  if (text && text !== "-") return text;
  return toText(value, "Pending");
}

function isScratched(runner: RaceFieldRunner): boolean {
  const officialStatus = toText(readValue(runner, ["official", "status"]), "").toUpperCase();
  const marketStatus = toText(readValue(runner, ["market", "status"]), "").toUpperCase();
  const price = toText(readValue(runner, ["market", "price"]), "").toUpperCase();
  return officialStatus.includes("SCRATCH") || marketStatus.includes("SCRATCH") || price.includes("SCRATCH");
}

function fieldFromRaceBook(raceBook: RaceBook): RaceFieldRunner[] {
  const value = readValue(raceBook, ["field"]);
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is RaceFieldRunner => Boolean(entry) && typeof entry === "object");
}

function laneFromPosition(position: number): MapLane {
  if (position <= 2) return "LEADERS";
  if (position <= 4) return "ON PACE";
  if (position <= 7) return "MIDFIELD";
  return "BACK";
}

function profileLane(runner: RaceFieldRunner): MapLane | null {
  const profile = [
    readValue(runner, ["profile", "runStyle"]),
    readValue(runner, ["profile", "settling"]),
    readValue(runner, ["dna", "runStyle"]),
  ]
    .map((value) => toText(value, "").toUpperCase())
    .find(Boolean);

  if (!profile) return null;
  if (profile.includes("LEAD")) return "LEADERS";
  if (profile.includes("PACE") || profile.includes("SPEED")) return "ON PACE";
  if (profile.includes("BACK") || profile.includes("REAR") || profile.includes("CLOSE")) return "BACK";
  if (profile.includes("MID")) return "MIDFIELD";
  return null;
}

function mapObservations(runner: RaceFieldRunner): MapObservation[] {
  const runs = readValue(runner, ["historicalRuns"]);
  if (!Array.isArray(runs)) return [];
  return runs.flatMap((run, runIndex) => {
    const candidates = [
      ["positionInRunning", "jump"],
      ["positionInRunning", "m800"],
      ["positionInRunning", "m600"],
      ["positionInRunning", "m400"],
    ];
    return candidates
      .map((path, index) => {
        const position = toNumber(readValue(run, path));
        if (!position || position <= 0) return null;
        return {
          label: `R${runIndex + 1}-${index + 1}`,
          position,
        };
      })
      .filter((entry): entry is MapObservation => Boolean(entry));
  });
}

function observationSignature(runner: RaceFieldRunner): string {
  const observations = mapObservations(runner);
  if (!observations.length) return "";
  return observations.map((observation) => `${observation.label}:${observation.position}`).join("|");
}

function sharedTemplateSignatures(field: RaceFieldRunner[]): Set<string> {
  const active = field.filter((runner) => !isScratched(runner));
  const counts = new Map<string, number>();
  active.forEach((runner) => {
    const signature = observationSignature(runner);
    if (!signature) return;
    counts.set(signature, (counts.get(signature) ?? 0) + 1);
  });
  const shared = new Set<string>();
  counts.forEach((count, signature) => {
    if (active.length >= 4 && count / active.length >= 0.6) {
      shared.add(signature);
    }
  });
  return shared;
}

function laneFromObservations(observations: MapObservation[]): { lane: MapLane; position: number | null } | null {
  if (!observations.length) return null;
  const average =
    observations.reduce((total, observation) => total + observation.position, 0) / observations.length;
  return { lane: laneFromPosition(average), position: Math.round(average) };
}

function confidenceFor(
  observations: MapObservation[],
  hasProfile: boolean,
  usesSharedTemplate: boolean,
): MapConfidence {
  if (usesSharedTemplate) return "Limited evidence";
  if (observations.length >= 3) return "Strong evidence";
  if (observations.length > 0 || hasProfile) return "Supported";
  return "Limited evidence";
}

function sourceFor(observations: MapObservation[], hasProfile: boolean, usesSharedTemplate: boolean): MapSource {
  if (usesSharedTemplate) return "shared-template";
  if (observations.length >= 3) return "settling-pattern";
  if (observations.length > 0) return "single-settling";
  if (hasProfile) return "profile";
  return "limited";
}

function evidenceRead(source: MapSource, lane: MapLane, scratched: boolean): string {
  if (scratched) return "Scratched runner retained at listed barrier.";
  if (source === "shared-template") {
    return "Shared default settling pattern detected; treat map read as limited until race-specific evidence improves.";
  }
  if (source === "limited") return "No reliable settling pattern available; position held as a conservative map read.";
  if (source === "profile") return `Run-style profile points to ${LANE_LABELS[lane].toLowerCase()}.`;
  return `Recent in-running evidence points to ${LANE_LABELS[lane].toLowerCase()}.`;
}

function buildMapRunner(
  runner: RaceFieldRunner,
  fieldIndex: number,
  market: (value: unknown) => string,
  sharedTemplates: Set<string>,
): MapRunner {
  const observations = mapObservations(runner);
  const profile = profileLane(runner);
  const observed = laneFromObservations(observations);
  const signature = observationSignature(runner);
  const scratched = isScratched(runner);
  const usesSharedTemplate = Boolean(signature && sharedTemplates.has(signature));
  const lane = observed?.lane ?? profile ?? "MIDFIELD";
  const confidence = confidenceFor(observations, Boolean(profile), usesSharedTemplate);
  const source = sourceFor(observations, Boolean(profile), usesSharedTemplate);
  const barrier = runnerBarrier(runner);

  return {
    runner,
    fieldIndex,
    runnerName: runnerName(runner),
    number: runnerNumber(runner),
    barrier,
    barrierSort: barrier ?? -1,
    jockey: runnerJockey(runner),
    trainer: runnerTrainer(runner),
    weight: runnerWeight(runner),
    marketText: marketText(runner, market),
    lane,
    descriptor: LANE_LABELS[lane],
    confidence,
    source,
    evidenceRead: evidenceRead(source, lane, scratched),
    settlingPosition: observed?.position ?? null,
    scratched,
  };
}

function buildMapRows(field: RaceFieldRunner[], market: (value: unknown) => string): MapRunner[] {
  const sharedTemplates = sharedTemplateSignatures(field);
  return field
    .map((runner, index) => buildMapRunner(runner, index, market, sharedTemplates))
    .sort((a, b) => {
      if (a.barrierSort !== b.barrierSort) return b.barrierSort - a.barrierSort;
      return Number(a.number) - Number(b.number);
    });
}

function projectionEndpoint(item: MapRunner): number {
  const base = PROJECTION_END[item.lane];
  if (item.scratched) return Math.min(86, base + 10);
  if (item.confidence === "Limited evidence") return base;
  const position = item.settlingPosition;
  if (!position) return base;
  const adjustment =
    item.lane === "LEADERS"
      ? Math.max(-4, Math.min(4, (position - 1) * 4))
      : item.lane === "ON PACE"
        ? Math.max(-4, Math.min(4, (position - 3) * 2))
        : item.lane === "MIDFIELD"
          ? Math.max(-5, Math.min(5, (position - 6) * 2))
          : Math.max(-3, Math.min(7, (position - 9) * 2));
  return Math.max(10, Math.min(84, base + adjustment));
}

function projectionStyle(item: MapRunner): CSSProperties {
  return {
    "--map-end": `${projectionEndpoint(item)}%`,
  } as CSSProperties;
}

function fieldStats(rows: MapRunner[]) {
  const active = rows.filter((row) => !row.scratched);
  const counts = active.reduce(
    (memo, row) => {
      memo[row.lane] += 1;
      memo.confidence[row.confidence] += 1;
      memo.source[row.source] += 1;
      return memo;
    },
    {
      LEADERS: 0,
      "ON PACE": 0,
      MIDFIELD: 0,
      BACK: 0,
      confidence: {
        "Strong evidence": 0,
        Supported: 0,
        "Limited evidence": 0,
      } as Record<MapConfidence, number>,
      source: {
        "settling-pattern": 0,
        "single-settling": 0,
        profile: 0,
        "shared-template": 0,
        limited: 0,
      } as Record<MapSource, number>,
    },
  );
  const pressure =
    counts.LEADERS + counts["ON PACE"] >= 5
      ? "High"
      : counts.LEADERS + counts["ON PACE"] >= 3
        ? "Moderate"
        : "Controlled";
  return { active, counts, pressure };
}

function shapePressureNotes(rows: MapRunner[]): string[] {
  const { active, counts, pressure } = fieldStats(rows);
  const notes = [
    `${pressure} early pressure from ${counts.LEADERS} leader profile and ${counts["ON PACE"]} on-pace profiles.`,
    `${counts.MIDFIELD} runners map through midfield; ${counts.BACK} map rearward.`,
  ];
  if (active.length && counts.source["shared-template"] / active.length >= 0.6) {
    notes.push("Shared default in-running evidence detected; map confidence held conservatively.");
  } else if (counts.confidence["Strong evidence"] > counts.confidence["Limited evidence"]) {
    notes.push("Settling evidence is strongest for the main speed positions.");
  } else {
    notes.push("Limited runner-specific speed evidence; review map with caution.");
  }
  return notes;
}

function trackRead(raceBook: RaceBook, rows: MapRunner[], clean: (value: unknown) => string): string[] {
  const track = clean(readValue(raceBook, ["race", "track"]));
  const condition = clean(readValue(raceBook, ["race", "condition"]));
  const rail = clean(readValue(raceBook, ["race", "rail"]));
  const { pressure } = fieldStats(rows);
  return [
    `${track || "Track"} is read as ${condition || "current condition"} with rail ${rail || "not stated"}.`,
    `${pressure} tempo read should be treated as a race-shape guide, not a price signal.`,
  ];
}

function MapZoneHeader() {
  return (
    <div className="eiq-speed-map-v3__zones" aria-hidden="true">
      {ZONE_LABELS.map((label) => (
        <span key={label}>{label}</span>
      ))}
    </div>
  );
}

function EvidenceKey() {
  return (
    <div className="eiq-map-evidence-key">
      <span><i className="is-strong" /> Strong evidence</span>
      <span><i className="is-supported" /> Supported</span>
      <span><i className="is-limited" /> Limited evidence</span>
    </div>
  );
}

function SpeedMapRow({ item, onOpenRunner }: { item: MapRunner; onOpenRunner?: (runner: RaceFieldRunner) => void }) {
  const rowClass = [
    "eiq-speed-map-v3__row",
    `is-${item.lane.toLowerCase().replace(/\s+/g, "-")}`,
    `is-${item.confidence.toLowerCase().replace(/\s+/g, "-")}`,
    item.scratched ? "is-scratched" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={rowClass} style={projectionStyle(item)}>
      <div className="eiq-speed-map-v3__track">
        <div className="eiq-speed-map-v3__projection" />
        <button
          type="button"
          className="eiq-speed-map-v3__runner"
          onClick={() => onOpenRunner?.(item.runner)}
          title={item.evidenceRead}
        >
          <span className="eiq-speed-map-v3__number">{item.number}</span>
          <span className="eiq-speed-map-v3__name">{item.runnerName}</span>
          <span className="eiq-speed-map-v3__meta">
            {item.descriptor} | {item.confidence}
          </span>
        </button>
      </div>
      <div className="eiq-speed-map-v3__barrier" aria-label={`Barrier ${item.barrier ?? "-"}`}>
        <span>{item.barrier ?? "-"}</span>
      </div>
    </div>
  );
}

function SpeedMapTable({ rows }: { rows: MapRunner[] }) {
  return (
    <section className="eiq-map-panel eiq-map-table-panel">
      <div className="eiq-map-panel__header">
        <span>Runner Map Table</span>
        <small>Barrier anchored | right-to-left</small>
      </div>
      <div className="eiq-map-table">
        <div className="eiq-map-table__head">
          <span>No</span>
          <span>Runner</span>
          <span>Barrier</span>
          <span>Jockey</span>
          <span>Trainer</span>
          <span>Weight</span>
          <span>Map</span>
          <span>Market</span>
        </div>
        {rows.map((row) => (
          <div className={row.scratched ? "is-scratched" : ""} key={`${row.number}-${row.runnerName}`}>
            <span>{row.number}</span>
            <strong>{row.runnerName}</strong>
            <span>{row.barrier ?? "-"}</span>
            <span>{row.jockey}</span>
            <span>{row.trainer}</span>
            <span>{row.weight}</span>
            <span>{row.descriptor}</span>
            <span>{row.marketText}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function RaceMap({ raceBook, field, clean, market, onOpenRunner }: MapWorkspaceProps) {
  const rows = buildMapRows(field ?? fieldFromRaceBook(raceBook), market);
  const { active, counts, pressure } = fieldStats(rows);

  return (
    <section className="eiq-map-workspace">
      <div className="eiq-map-workspace__header">
        <div>
          <p className="eiq-map-kicker">MAP</p>
          <h3>How will this race be run?</h3>
          <span>Victorian orientation | Barrier/start side right | Racing direction left</span>
        </div>
        <div className="eiq-map-summary-strip">
          <span><strong>{pressure}</strong><small>Tempo pressure</small></span>
          <span><strong>{active.length}</strong><small>Active runners</small></span>
          <span><strong>{counts.confidence["Limited evidence"]}</strong><small>Limited reads</small></span>
        </div>
      </div>

      <div className="eiq-map-layout-v3">
        <section className="eiq-barrier-map-panel">
          <div className="eiq-barrier-map-panel__header">
            <div>
              <span>Speed Map</span>
              <small>Rows are anchored to actual listed barriers.</small>
            </div>
            <strong>RACING DIRECTION &lt;-</strong>
          </div>
          <MapZoneHeader />
          <div className="eiq-speed-map-v3">
            <div className="eiq-speed-map-v3__start-label">BARRIERS</div>
            {rows.map((item) => (
              <SpeedMapRow item={item} key={`${item.number}-${item.runnerName}`} onOpenRunner={onOpenRunner} />
            ))}
          </div>
          <EvidenceKey />
        </section>

        <aside className="eiq-map-side-stack">
          <section className="eiq-map-panel">
            <div className="eiq-map-panel__header"><span>Shape Pressure</span></div>
            <ul className="eiq-map-notes">
              {shapePressureNotes(rows).map((note) => <li key={note}>{note}</li>)}
            </ul>
          </section>
          <section className="eiq-map-panel">
            <div className="eiq-map-panel__header"><span>Track Read</span></div>
            <ul className="eiq-map-notes">
              {trackRead(raceBook, rows, clean).map((note) => <li key={note}>{note}</li>)}
            </ul>
          </section>
          <section className="eiq-map-panel">
            <div className="eiq-map-panel__header"><span>Evidence Mix</span></div>
            <div className="eiq-map-source-grid">
              <span>Settling</span><strong>{counts.source["settling-pattern"]}</strong>
              <span>Single read</span><strong>{counts.source["single-settling"]}</strong>
              <span>Profile</span><strong>{counts.source.profile}</strong>
              <span>Shared pattern</span><strong>{counts.source["shared-template"]}</strong>
              <span>Limited</span><strong>{counts.source.limited}</strong>
            </div>
          </section>
        </aside>
      </div>

      <SpeedMapTable rows={rows} />
    </section>
  );
}

function RunnerMiniMap({ item }: { item: MapRunner }) {
  return (
    <div className="eiq-runner-mini-map" style={projectionStyle(item)}>
      <MapZoneHeader />
      <div className="eiq-runner-mini-map__track">
        <div className="eiq-runner-mini-map__projection" />
        <div className="eiq-runner-mini-map__runner">
          <span>{item.number}</span>
          <strong>{item.runnerName}</strong>
          <small>{item.descriptor}</small>
        </div>
        <div className="eiq-runner-mini-map__barrier">B{item.barrier ?? "-"}</div>
      </div>
      <div className="eiq-runner-mini-map__direction">RACING DIRECTION &lt;-</div>
    </div>
  );
}

function RunnerMap({ raceBook, field, selectedRunner, clean, market }: MapWorkspaceProps) {
  const rows = buildMapRows(field ?? fieldFromRaceBook(raceBook), market);
  const selectedName = selectedRunner ? runnerName(selectedRunner) : "";
  const item =
    rows.find((row) => row.runner === selectedRunner) ??
    rows.find((row) => row.runnerName === selectedName) ??
    rows[0];

  if (!item) {
    return (
      <section className="eiq-map-workspace">
        <div className="eiq-map-empty">No runner map evidence is available for this race.</div>
      </section>
    );
  }

  return (
    <section className="eiq-map-workspace eiq-map-workspace--runner">
      <div className="eiq-map-workspace__header">
        <div>
          <p className="eiq-map-kicker">MAP</p>
          <h3>{item.runnerName}</h3>
          <span>Expected settling position and barrier path.</span>
        </div>
        <div className="eiq-map-summary-strip">
          <span><strong>{item.descriptor}</strong><small>Expected position</small></span>
          <span><strong>B{item.barrier ?? "-"}</strong><small>Barrier</small></span>
          <span><strong>{item.confidence}</strong><small>Evidence</small></span>
        </div>
      </div>

      <div className="eiq-runner-map-grid">
        <section className="eiq-map-panel">
          <div className="eiq-map-panel__header">
            <span>Runner Speed Map</span>
            <small>Barrier right | projection left</small>
          </div>
          <RunnerMiniMap item={item} />
        </section>
        <section className="eiq-map-panel">
          <div className="eiq-map-panel__header"><span>Today's Map Summary</span></div>
          <div className="eiq-runner-map-facts">
            <span>Barrier</span><strong>{item.barrier ?? "-"}</strong>
            <span>Map note</span><strong>{item.evidenceRead}</strong>
            <span>Tempo fit</span><strong>{item.lane === "LEADERS" || item.lane === "ON PACE" ? "Depends on pressure" : "Tempo dependent"}</strong>
            <span>Pressure fit</span><strong>{item.confidence === "Limited evidence" ? "Limited evidence" : "Supported by settling data"}</strong>
            <span>Map positive</span><strong>{item.lane === "LEADERS" ? "Can use early position" : "Settling pattern defined"}</strong>
            <span>Map risk</span><strong>{item.scratched ? "Scratched" : item.confidence === "Limited evidence" ? "Evidence depth" : "Race pressure"}</strong>
          </div>
        </section>
        <section className="eiq-map-panel">
          <div className="eiq-map-panel__header"><span>Race Context</span></div>
          <ul className="eiq-map-notes">
            {trackRead(raceBook, rows, clean).map((note) => <li key={note}>{note}</li>)}
          </ul>
        </section>
      </div>
    </section>
  );
}

export function MapWorkspace(props: MapWorkspaceProps) {
  if (props.selectedRunner) {
    return <RunnerMap {...props} />;
  }
  return <RaceMap {...props} />;
}
'''


MAP_CSS = r'''.eiq-map-workspace {
  display: grid;
  gap: 14px;
}

.eiq-map-workspace__header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 18px;
  border: 1px solid rgba(51, 128, 138, 0.28);
  background:
    radial-gradient(circle at 85% 20%, rgba(51, 128, 138, 0.16), transparent 32%),
    rgba(3, 8, 10, 0.68);
  border-radius: 14px;
}

.eiq-map-kicker {
  margin: 0 0 6px;
  color: #3d7f87;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.24em;
}

.eiq-map-workspace__header h3 {
  margin: 0 0 5px;
  font-size: 24px;
  font-weight: 650;
  letter-spacing: 0.02em;
}

.eiq-map-workspace__header span,
.eiq-map-workspace__header small {
  color: rgba(238, 248, 246, 0.68);
  font-size: 12px;
}

.eiq-map-summary-strip {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.eiq-map-summary-strip span {
  min-width: 112px;
  padding: 9px 11px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: rgba(4, 14, 17, 0.76);
}

.eiq-map-summary-strip strong,
.eiq-map-summary-strip small {
  display: block;
}

.eiq-map-summary-strip strong {
  color: #eef8f6;
  font-size: 15px;
  font-weight: 700;
}

.eiq-map-summary-strip small {
  margin-top: 3px;
  color: rgba(238, 248, 246, 0.58);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.eiq-map-layout-v3 {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 14px;
  align-items: start;
}

.eiq-barrier-map-panel,
.eiq-map-panel {
  border: 1px solid rgba(51, 128, 138, 0.24);
  border-radius: 14px;
  background: rgba(3, 8, 10, 0.68);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.eiq-barrier-map-panel {
  padding: 14px;
  overflow: hidden;
}

.eiq-barrier-map-panel__header,
.eiq-map-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  color: #3d7f87;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.eiq-barrier-map-panel__header small,
.eiq-map-panel__header small {
  display: block;
  margin-top: 4px;
  color: rgba(238, 248, 246, 0.5);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
}

.eiq-barrier-map-panel__header strong {
  color: #5d9da4;
  white-space: nowrap;
}

.eiq-speed-map-v3__zones {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  padding-right: 72px;
  margin-bottom: 8px;
  color: rgba(238, 248, 246, 0.54);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.eiq-speed-map-v3 {
  position: relative;
  display: grid;
  gap: 6px;
}

.eiq-speed-map-v3::before {
  content: "";
  position: absolute;
  inset: 0 72px 0 0;
  background:
    linear-gradient(to right, rgba(51, 128, 138, 0.08), transparent 1px) 0 0 / 20% 100%,
    linear-gradient(to bottom, rgba(255, 255, 255, 0.035), transparent 1px) 0 0 / 100% 44px;
  pointer-events: none;
}

.eiq-speed-map-v3__start-label {
  position: absolute;
  top: -24px;
  right: 3px;
  width: 60px;
  text-align: center;
  color: rgba(238, 248, 246, 0.62);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.eiq-speed-map-v3__row {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 58px;
  gap: 10px;
  min-height: 40px;
  align-items: center;
}

.eiq-speed-map-v3__track {
  position: relative;
  height: 34px;
}

.eiq-speed-map-v3__projection {
  position: absolute;
  top: 15px;
  left: var(--map-end);
  right: 8px;
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(to left, rgba(61, 127, 135, 0.88), rgba(47, 115, 124, 0.4));
  box-shadow: 0 0 10px rgba(51, 128, 138, 0.16);
}

.eiq-speed-map-v3__row.is-limited-evidence .eiq-speed-map-v3__projection {
  background: linear-gradient(to left, rgba(115, 132, 135, 0.62), rgba(72, 85, 88, 0.28));
  box-shadow: none;
}

.eiq-speed-map-v3__row.is-scratched .eiq-speed-map-v3__projection,
.eiq-speed-map-v3__row.is-scratched .eiq-speed-map-v3__runner,
.eiq-speed-map-v3__row.is-scratched .eiq-speed-map-v3__barrier {
  opacity: 0.42;
  filter: grayscale(0.7);
}

.eiq-speed-map-v3__runner {
  position: absolute;
  left: var(--map-end);
  top: 2px;
  display: grid;
  grid-template-columns: auto 1fr;
  column-gap: 7px;
  align-items: center;
  min-width: 176px;
  max-width: 250px;
  padding: 5px 8px;
  border: 1px solid rgba(51, 128, 138, 0.34);
  border-radius: 999px;
  background: rgba(5, 18, 21, 0.92);
  color: #eef8f6;
  text-align: left;
  cursor: pointer;
}

.eiq-speed-map-v3__runner:hover {
  border-color: rgba(61, 127, 135, 0.74);
  background: rgba(8, 29, 33, 0.96);
}

.eiq-speed-map-v3__number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #33808a;
  color: #061112;
  font-size: 11px;
  font-weight: 900;
}

.eiq-speed-map-v3__name {
  min-width: 0;
  overflow: hidden;
  color: #eef8f6;
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eiq-speed-map-v3__meta {
  grid-column: 2;
  margin-top: -2px;
  overflow: hidden;
  color: rgba(238, 248, 246, 0.54);
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eiq-speed-map-v3__barrier {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  border-left: 1px solid rgba(51, 128, 138, 0.3);
}

.eiq-speed-map-v3__barrier span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 28px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.045);
  color: #eef8f6;
  font-size: 13px;
  font-weight: 800;
}

.eiq-map-evidence-key {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  margin-top: 12px;
  color: rgba(238, 248, 246, 0.6);
  font-size: 11px;
}

.eiq-map-evidence-key span {
  display: inline-flex;
  gap: 7px;
  align-items: center;
}

.eiq-map-evidence-key i {
  width: 26px;
  height: 3px;
  border-radius: 999px;
  background: #33808a;
}

.eiq-map-evidence-key .is-supported {
  background: rgba(61, 127, 135, 0.58);
}

.eiq-map-evidence-key .is-limited {
  background: rgba(115, 132, 135, 0.46);
}

.eiq-map-side-stack {
  display: grid;
  gap: 12px;
}

.eiq-map-panel {
  padding: 14px;
}

.eiq-map-notes {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.eiq-map-notes li {
  color: rgba(238, 248, 246, 0.75);
  font-size: 12px;
  line-height: 1.45;
}

.eiq-map-source-grid {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px 12px;
  color: rgba(238, 248, 246, 0.64);
  font-size: 12px;
}

.eiq-map-source-grid strong {
  color: #eef8f6;
}

.eiq-map-table-panel {
  padding: 14px;
}

.eiq-map-table {
  display: grid;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
}

.eiq-map-table__head,
.eiq-map-table > div:not(.eiq-map-table__head) {
  display: grid;
  grid-template-columns: 52px minmax(160px, 1.5fr) 78px minmax(120px, 1fr) minmax(130px, 1fr) 78px 98px 88px;
  align-items: center;
}

.eiq-map-table__head span,
.eiq-map-table > div:not(.eiq-map-table__head) span,
.eiq-map-table > div:not(.eiq-map-table__head) strong {
  padding: 8px 10px;
  border-right: 1px solid rgba(255, 255, 255, 0.055);
  color: rgba(238, 248, 246, 0.74);
  font-size: 12px;
}

.eiq-map-table__head span {
  background: rgba(255, 255, 255, 0.035);
  color: rgba(238, 248, 246, 0.64);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-map-table > div:not(.eiq-map-table__head) {
  border-top: 1px solid rgba(255, 255, 255, 0.045);
}

.eiq-map-table > div.is-scratched {
  opacity: 0.45;
}

.eiq-map-table strong {
  color: #eef8f6 !important;
}

.eiq-runner-map-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.9fr) minmax(260px, 0.7fr);
  gap: 14px;
}

.eiq-runner-mini-map {
  display: grid;
  gap: 10px;
}

.eiq-runner-mini-map .eiq-speed-map-v3__zones {
  padding-right: 58px;
}

.eiq-runner-mini-map__track {
  position: relative;
  height: 82px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  background:
    linear-gradient(to right, rgba(51, 128, 138, 0.08), transparent 1px) 0 0 / 20% 100%,
    rgba(2, 7, 9, 0.55);
}

.eiq-runner-mini-map__projection {
  position: absolute;
  top: 40px;
  left: var(--map-end);
  right: 48px;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(to left, rgba(61, 127, 135, 0.88), rgba(47, 115, 124, 0.34));
}

.eiq-runner-mini-map__runner {
  position: absolute;
  left: var(--map-end);
  top: 24px;
  display: inline-grid;
  grid-template-columns: auto 1fr;
  column-gap: 8px;
  align-items: center;
  min-width: 170px;
  padding: 7px 9px;
  border: 1px solid rgba(51, 128, 138, 0.34);
  border-radius: 999px;
  background: rgba(5, 18, 21, 0.94);
}

.eiq-runner-mini-map__runner span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 23px;
  height: 23px;
  border-radius: 50%;
  background: #33808a;
  color: #061112;
  font-weight: 900;
}

.eiq-runner-mini-map__runner strong,
.eiq-runner-mini-map__runner small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eiq-runner-mini-map__runner strong {
  color: #eef8f6;
  font-size: 12px;
}

.eiq-runner-mini-map__runner small {
  color: rgba(238, 248, 246, 0.58);
  font-size: 10px;
}

.eiq-runner-mini-map__barrier {
  position: absolute;
  top: 22px;
  right: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 36px;
  border-left: 1px solid rgba(51, 128, 138, 0.35);
  color: #eef8f6;
  font-weight: 900;
}

.eiq-runner-mini-map__direction {
  color: #5d9da4;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-align: center;
}

.eiq-runner-map-facts {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 9px 12px;
  color: rgba(238, 248, 246, 0.66);
  font-size: 12px;
}

.eiq-runner-map-facts strong {
  color: #eef8f6;
  font-weight: 650;
}

.eiq-map-empty {
  padding: 18px;
  border: 1px solid rgba(51, 128, 138, 0.24);
  border-radius: 12px;
  background: rgba(3, 8, 10, 0.68);
  color: rgba(238, 248, 246, 0.72);
}

@media (max-width: 1280px) {
  .eiq-map-layout-v3,
  .eiq-runner-map-grid {
    grid-template-columns: 1fr;
  }

  .eiq-map-table {
    overflow-x: auto;
  }
}

'''


def checkpoint(path: Path) -> Path:
  backup = path.with_name(f"{path.stem}_CHECKPOINT_BEFORE_MAP_WORKSPACE_V3_{STAMP}{path.suffix}")
  backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
  return backup


def replace_css_block(css: str) -> str:
  start = css.find(".eiq-map-workspace {")
  end_marker = "/* EDGEIQ OS navigation restructure */"
  end = css.find(end_marker, start)
  if start == -1 or end == -1:
    raise RuntimeError("Could not find existing MAP workspace CSS block.")
  return css[:start] + MAP_CSS + "\n" + css[end:]


def main() -> None:
  if not COMPONENT.exists():
    raise FileNotFoundError(COMPONENT)
  if not CSS.exists():
    raise FileNotFoundError(CSS)

  checkpoints = [checkpoint(COMPONENT), checkpoint(CSS)]

  previous = COMPONENT.read_text(encoding="utf-8")
  if "eiq-speed-map__lanes" not in previous and "eiq-speed-map-v3" not in previous:
    raise RuntimeError("MapWorkspace does not look like the expected V2/V3 source.")

  COMPONENT.write_text(MAP_WORKSPACE_TSX, encoding="utf-8")
  CSS.write_text(replace_css_block(CSS.read_text(encoding="utf-8")), encoding="utf-8")

  print("EDGEIQ_MAP_WORKSPACE_V3_BUILD_SCRIPT_PASS")
  print("Checkpoints:")
  for item in checkpoints:
    print(f"- {item}")
  print(f"Updated: {COMPONENT}")
  print(f"Updated: {CSS}")


if __name__ == "__main__":
  main()

