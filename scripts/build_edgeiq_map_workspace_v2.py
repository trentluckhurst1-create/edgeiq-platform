from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

MAP_PATH = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"
CSS_PATH = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"

MAP_TEXT = r'''type MapLane = "LEADERS" | "ON PACE" | "MIDFIELD" | "BACK";
type MapMode = "race" | "runner";
type ConfidenceState = "Strong evidence" | "Supported" | "Limited evidence";
type SourceState = "settling" | "profile" | "limited";

type CleanFormatter = (value: unknown) => string;
type MarketFormatter = (value: unknown) => string;
type UnknownRecord = Record<string, unknown>;

type MapWorkspaceProps = {
  raceBook: unknown;
  field: readonly unknown[];
  selectedRunner?: unknown;
  clean: CleanFormatter;
  market: MarketFormatter;
  mode?: MapMode;
  onOpenRunner?: (index: number) => void;
};

type MapObservation = {
  lane: MapLane;
  position: number;
  label: string;
};

type MapRunner = {
  index: number;
  runner: unknown;
  lane: MapLane;
  position: number | null;
  descriptor: string;
  confidence: ConfidenceState;
  source: SourceState;
  evidenceRead: string;
  barrierContext: string;
  earlyWatch: string;
};

const lanes: MapLane[] = ["LEADERS", "ON PACE", "MIDFIELD", "BACK"];

function asRecord(value: unknown): UnknownRecord {
  return value && typeof value === "object" ? (value as UnknownRecord) : {};
}

function getValue(source: unknown, path: readonly string[]): unknown {
  let current: unknown = source;
  for (const key of path) {
    current = asRecord(current)[key];
  }
  return current;
}

function getArray(source: unknown, path: readonly string[]): readonly unknown[] {
  const value = getValue(source, path);
  return Array.isArray(value) ? value : [];
}

function text(value: unknown): string {
  return String(value ?? "").trim();
}

function normal(value: unknown): string {
  return text(value).toUpperCase();
}

function hasDisplayValue(value: unknown): boolean {
  const raw = text(value);
  if (!raw) return false;
  const upper = raw.toUpperCase();
  return !["-", "NOT AVAILABLE", "NOT RECORDED", "PENDING", "MISSING", "NULL", "UNDEFINED"].includes(upper);
}

function parsePositivePosition(value: unknown): number | null {
  const match = text(value).match(/\b(\d{1,2})(?:ST|ND|RD|TH)?\b/i);
  if (!match) return null;
  const parsed = Number(match[1]);
  if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 30) return null;
  return parsed;
}

function parsePositiveNumber(value: unknown): number | null {
  const match = text(value).match(/-?\d+(\.\d+)?/);
  if (!match) return null;
  const parsed = Number(match[0]);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return parsed;
}

function laneFromPosition(position: number): MapLane {
  if (position <= 2) return "LEADERS";
  if (position <= 4) return "ON PACE";
  if (position <= 7) return "MIDFIELD";
  return "BACK";
}

function laneFromProfile(runner: unknown): MapLane | null {
  const profileText = normal([
    getValue(runner, ["runStyle"]),
    getValue(runner, ["speedProfile"]),
    getValue(runner, ["raceFlow"]),
    getValue(runner, ["runnerDNA"]),
    getValue(runner, ["assessment"]),
    getValue(runner, ["historicalRuns", "0", "raceFlowMatch"]),
  ].filter(Boolean).join(" "));

  if (!profileText) return null;
  if (profileText.includes("LEADER") || profileText.includes("EARLY")) return "LEADERS";
  if (profileText.includes("ON PACE") || profileText.includes("SPEED")) return "ON PACE";
  if (profileText.includes("MIDFIELD") || profileText.includes("BALANCED")) return "MIDFIELD";
  if (profileText.includes("BACK") || profileText.includes("CLOSER") || profileText.includes("LATE")) return "BACK";
  return null;
}

function mapObservations(runner: unknown): MapObservation[] {
  return getArray(runner, ["historicalRuns"]).slice(0, 5).flatMap((run): MapObservation[] => {
    const points: Array<[string, unknown]> = [
      ["800m", getValue(run, ["positionInRunning", "m800"])],
      ["600m", getValue(run, ["positionInRunning", "m600"])],
      ["Jump", getValue(run, ["positionInRunning", "jump"])],
    ];
    const first = points
      .map(([label, value]) => ({ label, position: parsePositivePosition(value) }))
      .find((item): item is { label: string; position: number } => item.position !== null);

    return first ? [{ label: first.label, position: first.position, lane: laneFromPosition(first.position) }] : [];
  });
}

function dominantLane(observations: readonly MapObservation[]): MapLane | null {
  if (!observations.length) return null;
  const counts = lanes.map((lane) => ({
    lane,
    count: observations.filter((item) => item.lane === lane).length,
  }));
  const best = counts.sort((a, b) => b.count - a.count || lanes.indexOf(a.lane) - lanes.indexOf(b.lane))[0];
  if (!best || best.count === 0) return null;
  return best.lane;
}

function confidenceFor(observations: readonly MapObservation[], profileLane: MapLane | null): ConfidenceState {
  if (observations.length >= 2) {
    const lane = dominantLane(observations);
    const repeated = lane ? observations.filter((item) => item.lane === lane).length >= 2 : false;
    if (repeated) return "Strong evidence";
  }
  if (observations.length >= 1 || profileLane) return "Supported";
  return "Limited evidence";
}

function descriptorFor(lane: MapLane): string {
  if (lane === "LEADERS") return "Forward";
  if (lane === "ON PACE") return "Handy";
  if (lane === "MIDFIELD") return "Midfield";
  return "Rearward";
}

function barrierBand(barrier: number | null, fieldSize: number): "inside" | "middle" | "wide" | "unknown" {
  if (barrier === null || fieldSize <= 0) return "unknown";
  const insideCut = Math.max(1, Math.ceil(fieldSize / 3));
  const wideCut = Math.max(insideCut + 1, Math.ceil((fieldSize * 2) / 3));
  if (barrier <= insideCut) return "inside";
  if (barrier >= wideCut) return "wide";
  return "middle";
}

function barrierContext(lane: MapLane, barrier: number | null, fieldSize: number, confidence: ConfidenceState): string {
  const band = barrierBand(barrier, fieldSize);
  if (band === "unknown" || confidence === "Limited evidence") return "Limited map evidence; confirm intended settling position.";
  if (band === "wide" && (lane === "LEADERS" || lane === "ON PACE")) return "Wide draw may require early work to find a forward position.";
  if (band === "inside" && (lane === "MIDFIELD" || lane === "BACK")) return "Inside draw may require clear running if settling behind horses.";
  if (band === "inside" && (lane === "LEADERS" || lane === "ON PACE")) return "Inside draw is suitable if the runner begins cleanly.";
  if (band === "wide" && lane === "BACK") return "Wide draw may allow the rider to concede position and find cover.";
  return "Draw appears workable for the expected settling position.";
}

function evidenceRead(confidence: ConfidenceState, observations: readonly MapObservation[], profileLane: MapLane | null): string {
  if (confidence === "Strong evidence") return "Recent settling pattern is repeated in the available form.";
  if (observations.length) return `Latest usable settling point: ${observations[0].label} in position ${observations[0].position}.`;
  if (profileLane) return "Position inferred from available runner profile.";
  return "Fallback placement; confirm intent through race-day evidence.";
}

function earlyWatch(lane: MapLane, barrierText: string, confidence: ConfidenceState): string {
  if (confidence === "Limited evidence") return "Limited evidence; confirm the intended settling position after the start.";
  if (barrierText.includes("Wide") && (lane === "LEADERS" || lane === "ON PACE")) return "Whether early pressure forces the runner to work across from the wide gate.";
  if (barrierText.includes("Inside") && (lane === "MIDFIELD" || lane === "BACK")) return "Whether the runner can hold position without being caught behind slower horses.";
  if (lane === "BACK") return "Whether the rider concedes position to obtain cover.";
  if (lane === "LEADERS") return "Whether the runner crosses or holds the lead without being pressured.";
  return "Whether the runner settles into its expected lane through the first 400 metres.";
}

function mapRunner(runner: unknown, index: number, fieldSize: number): MapRunner {
  const observations = mapObservations(runner);
  const profileLane = laneFromProfile(runner);
  const lane = dominantLane(observations) ?? profileLane ?? "MIDFIELD";
  const confidence = confidenceFor(observations, profileLane);
  const position = observations[0]?.position ?? null;
  const barrier = parsePositiveNumber(getValue(runner, ["official", "barrier"]));
  const context = barrierContext(lane, barrier, fieldSize, confidence);

  return {
    index,
    runner,
    lane,
    position,
    descriptor: descriptorFor(lane),
    confidence,
    source: observations.length ? "settling" : profileLane ? "profile" : "limited",
    evidenceRead: evidenceRead(confidence, observations, profileLane),
    barrierContext: context,
    earlyWatch: earlyWatch(lane, context, confidence),
  };
}

function laneRank(lane: MapLane): number {
  return lanes.indexOf(lane);
}

function runnerNumber(runner: unknown, index: number, clean: CleanFormatter): string {
  return clean(getValue(runner, ["official", "no"]) ?? getValue(runner, ["official", "number"]) ?? index + 1);
}

function activeMappedRunners(items: readonly MapRunner[]): MapRunner[] {
  return items.filter((item) => normal(getValue(item.runner, ["official", "status"])) !== "SCRATCHED");
}

function shapePressureNotes(items: readonly MapRunner[]): string[] {
  const active = activeMappedRunners(items);
  const count = (lane: MapLane) => active.filter((item) => item.lane === lane).length;
  const leaders = count("LEADERS");
  const onPace = count("ON PACE");
  const midfield = count("MIDFIELD");
  const back = count("BACK");
  const notes: string[] = [];

  if (leaders >= 2) notes.push("Multiple runners may contest the lead.");
  if (leaders + onPace >= Math.max(4, Math.ceil(active.length * 0.45))) notes.push("Forward pressure appears concentrated across the first two lanes.");
  if (leaders === 0 && onPace <= 1) notes.push("Limited natural speed is evident from the available map evidence.");
  if (back >= Math.max(3, midfield + leaders)) notes.push("A sizeable rearward group may require sustained tempo.");
  if (!notes.length) notes.push("Race shape appears balanced from the available map evidence.");
  return notes.slice(0, 3);
}

function laneConflictNote(lane: MapLane, items: readonly MapRunner[]): string | null {
  const active = activeMappedRunners(items.filter((item) => item.lane === lane));
  const supported = active.filter((item) => item.confidence !== "Limited evidence");
  if ((lane === "LEADERS" || lane === "ON PACE") && supported.length >= 2) return "Position contested";
  if (lane === "BACK" && active.length >= 4) return "Tempo dependent";
  return null;
}

function tempoFit(lane: MapLane, pressure: unknown, tempo: unknown): string {
  const pressureText = normal(pressure);
  const tempoText = normal(tempo);
  const strong = pressureText.includes("HIGH") || pressureText.includes("EXTREME") || tempoText.includes("FAST") || tempoText.includes("STRONG");
  const soft = pressureText.includes("LOW") || tempoText.includes("SLOW");

  if (strong && (lane === "MIDFIELD" || lane === "BACK")) return "Sustained tempo may bring this runner into the race.";
  if (strong && (lane === "LEADERS" || lane === "ON PACE")) return "Needs to absorb or avoid early pressure.";
  if (soft && (lane === "LEADERS" || lane === "ON PACE")) return "Can use tactical position if tempo is controlled.";
  if (soft && lane === "BACK") return "May need stronger tempo than currently indicated.";
  return "Tempo read is neutral from available race-shape data.";
}

function pressureFit(lane: MapLane, pressure: unknown): string {
  const pressureText = normal(pressure);
  if (!pressureText) return "Pressure read is not available.";
  if (pressureText.includes("HIGH") || pressureText.includes("EXTREME")) {
    return lane === "MIDFIELD" || lane === "BACK" ? "Pressure may help if the runner gets clear room." : "Pressure could make the forward spot harder to hold.";
  }
  if (pressureText.includes("LOW")) {
    return lane === "LEADERS" || lane === "ON PACE" ? "Lower pressure may assist a forward settling position." : "Lower pressure could make ground difficult to recover.";
  }
  return "Pressure read is balanced.";
}

function mapPositive(item: MapRunner): string {
  if (item.confidence === "Limited evidence") return "No firm map edge established.";
  if (item.lane === "LEADERS") return "Tactical speed is the main map positive.";
  if (item.lane === "ON PACE") return "Can settle close enough if the start is clean.";
  if (item.lane === "MIDFIELD") return "Should have settling options if the race is run evenly.";
  return "Can settle and build into the race if tempo allows.";
}

function mapRisk(item: MapRunner): string {
  if (item.confidence === "Limited evidence") return "Settling intent needs confirmation after the jump.";
  if (item.barrierContext.includes("early work")) return "May need to work early to reach its spot.";
  if (item.barrierContext.includes("clear running")) return "Traffic risk if buried behind slower horses.";
  if (item.lane === "BACK") return "May need tempo and clear running.";
  if (item.lane === "LEADERS") return "Could be vulnerable if the lead is contested.";
  return "Race shape needs to match the expected settling position.";
}

function runnerMarket(runner: unknown, market: MarketFormatter): string | null {
  const value = market(getValue(runner, ["official", "market"]));
  return hasDisplayValue(value) ? value : null;
}

function RunnerMapCard({
  item,
  clean,
  market,
  onOpenRunner,
}: {
  item: MapRunner;
  clean: CleanFormatter;
  market: MarketFormatter;
  onOpenRunner?: (index: number) => void;
}) {
  const isScratched = normal(getValue(item.runner, ["official", "status"])) === "SCRATCHED";
  const cardClass = `eiq-map-runner-card${isScratched ? " is-scratched" : ""}`;
  const marketText = runnerMarket(item.runner, market);
  const body = (
    <>
      <div className="eiq-map-runner-card__top">
        <b>{runnerNumber(item.runner, item.index, clean)}</b>
        <strong>{clean(getValue(item.runner, ["official", "runner"]))}</strong>
      </div>
      <div className="eiq-map-runner-card__middle">
        <span>Bar {clean(getValue(item.runner, ["official", "barrier"]))}</span>
        <span>{item.descriptor}</span>
      </div>
      <dl>
        <div><dt>J</dt><dd>{clean(getValue(item.runner, ["official", "jockey"]))}</dd></div>
        <div><dt>T</dt><dd>{clean(getValue(item.runner, ["official", "trainer"]))}</dd></div>
        {marketText ? <div><dt>Mkt</dt><dd>{marketText}</dd></div> : null}
      </dl>
      <em>{item.confidence}</em>
    </>
  );

  if (onOpenRunner) {
    return (
      <button type="button" className={cardClass} onClick={() => onOpenRunner(item.index)}>
        {body}
      </button>
    );
  }

  return <article className={cardClass}>{body}</article>;
}

function buildMap(field: readonly unknown[], fieldSize: number): MapRunner[] {
  return field
    .map((runner, index) => mapRunner(runner, index, fieldSize))
    .sort((a, b) => {
      const laneDiff = laneRank(a.lane) - laneRank(b.lane);
      if (laneDiff) return laneDiff;
      const confidenceDiff = ["Strong evidence", "Supported", "Limited evidence"].indexOf(a.confidence) - ["Strong evidence", "Supported", "Limited evidence"].indexOf(b.confidence);
      if (confidenceDiff) return confidenceDiff;
      const posDiff = (a.position ?? 999) - (b.position ?? 999);
      if (posDiff) return posDiff;
      return (parsePositiveNumber(getValue(a.runner, ["official", "barrier"])) ?? 999) - (parsePositiveNumber(getValue(b.runner, ["official", "barrier"])) ?? 999);
    });
}

function RaceMap({ raceBook, field, clean, market, onOpenRunner }: MapWorkspaceProps) {
  const official = getValue(raceBook, ["official"]);
  const intelligence = getValue(raceBook, ["intelligence"]);
  const fieldSize = parsePositiveNumber(getValue(official, ["fieldSize"])) ?? field.length;
  const mapped = buildMap(field, fieldSize);
  const notes = shapePressureNotes(mapped);

  return (
    <section className="eiq-map-workspace">
      <header className="eiq-map-workspace__header">
        <div>
          <span>MAP</span>
          <strong>How will this race be run?</strong>
          <p>{clean(getValue(official, ["meeting"]))} R{clean(getValue(official, ["raceNumber"]))} | {clean(getValue(official, ["distance"]))} | {clean(getValue(official, ["raceClass"]))} | {clean(getValue(official, ["trackCondition"]))}</p>
        </div>
        <aside>
          <div><span>Tempo</span><strong>{clean(getValue(intelligence, ["tempo"]))}</strong></div>
          <div><span>Pressure</span><strong>{clean(getValue(intelligence, ["pressure"]))}</strong></div>
          <div><span>Field</span><strong>{clean(fieldSize)}</strong></div>
        </aside>
      </header>

      <div className="eiq-map-workspace__body">
        <section className="eiq-speed-map">
          <div className="eiq-speed-map__title">
            <span>Traditional Speed Map</span>
            <strong>LEADERS <i /> ON PACE <i /> MIDFIELD <i /> BACK</strong>
          </div>
          <div className="eiq-speed-map__lanes">
            {lanes.map((lane) => {
              const laneRunners = mapped.filter((item) => item.lane === lane);
              const conflict = laneConflictNote(lane, mapped);
              return (
                <div key={lane} className="eiq-speed-map__lane">
                  <header>
                    <span>{lane}</span>
                    {conflict ? <em>{conflict}</em> : null}
                  </header>
                  <div>
                    {laneRunners.length ? laneRunners.map((item) => (
                      <RunnerMapCard key={`${item.index}-${text(getValue(item.runner, ["official", "runner"]))}`} item={item} clean={clean} market={market} onOpenRunner={onOpenRunner} />
                    )) : <p>No consistent settling pattern established for this lane.</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <aside className="eiq-map-side">
          <section>
            <span>Shape Pressure</span>
            <strong>{notes[0]}</strong>
            <ul>{notes.slice(1).map((note) => <li key={note}>{note}</li>)}</ul>
          </section>

          <section>
            <span>Track Read</span>
            <strong>{hasDisplayValue(getValue(intelligence, ["trackSignature"])) ? clean(getValue(intelligence, ["trackSignature"])) : clean(getValue(official, ["trackCondition"]))}</strong>
            <p>Track read uses available race-state profile only. No live bias is inferred without support.</p>
            <dl>
              <div><dt>Condition</dt><dd>{clean(getValue(official, ["trackCondition"]))}</dd></div>
              <div><dt>Rail</dt><dd>{clean(getValue(official, ["rail"]))}</dd></div>
              <div><dt>Speed Read</dt><dd>{clean(getValue(intelligence, ["speedProfile"]))}</dd></div>
              <div><dt>Confidence</dt><dd>{clean(getValue(intelligence, ["confidence"]))}</dd></div>
            </dl>
          </section>
        </aside>
      </div>
    </section>
  );
}

function RunnerMap({ raceBook, field, selectedRunner, clean, market }: MapWorkspaceProps) {
  const official = getValue(raceBook, ["official"]);
  const intelligence = getValue(raceBook, ["intelligence"]);
  const runner = selectedRunner ?? field[0];
  const fieldSize = parsePositiveNumber(getValue(official, ["fieldSize"])) ?? field.length;
  const item = mapRunner(runner, Math.max(0, field.indexOf(runner)), fieldSize);
  const marketText = runnerMarket(runner, market);
  const tempFit = tempoFit(item.lane, getValue(intelligence, ["pressure"]), getValue(intelligence, ["tempo"]));
  const pressFit = pressureFit(item.lane, getValue(intelligence, ["pressure"]));

  return (
    <section className="eiq-map-workspace eiq-map-workspace--runner">
      <header className="eiq-map-workspace__header">
        <div>
          <span>MAP</span>
          <strong>{clean(getValue(runner, ["official", "runner"]))}</strong>
          <p>{runnerNumber(runner, item.index, clean)} | Bar {clean(getValue(runner, ["official", "barrier"]))} | {clean(getValue(runner, ["official", "jockey"]))} | {clean(getValue(runner, ["official", "trainer"]))}</p>
        </div>
        <aside>
          <div><span>Expected Position</span><strong>{item.lane}</strong></div>
          <div><span>Evidence Read</span><strong>{item.confidence}</strong></div>
          {marketText ? <div><span>Market</span><strong>{marketText}</strong></div> : null}
        </aside>
      </header>

      <div className="eiq-runner-map-sequence">
        <section>
          <span>A. Expected Position</span>
          <strong>{item.lane}</strong>
          <p>{item.position !== null ? `Latest usable settling point places the runner around position ${item.position}.` : "No consistent settling pattern established from recent in-running data."}</p>
        </section>
        <section>
          <span>B. Evidence Read</span>
          <strong>{item.confidence}</strong>
          <p>{item.evidenceRead}</p>
        </section>
        <section>
          <span>C. Barrier And Early Position</span>
          <strong>Bar {clean(getValue(runner, ["official", "barrier"]))}</strong>
          <p>{item.barrierContext}</p>
        </section>
        <section>
          <span>D. Tempo And Pressure Fit</span>
          <strong>{clean(getValue(intelligence, ["tempo"]))} / {clean(getValue(intelligence, ["pressure"]))}</strong>
          <p>{tempFit} {pressFit}</p>
        </section>
        <section>
          <span>E. Map Positive / Map Risk</span>
          <strong>{mapPositive(item)}</strong>
          <p>{mapRisk(item)}</p>
        </section>
        <section>
          <span>Early Watch</span>
          <strong>First 400 metres</strong>
          <p>{item.earlyWatch}</p>
        </section>
        <section className="eiq-runner-map-sequence__summary">
          <span>Today's Map Summary</span>
          <strong>{item.descriptor} map read</strong>
          <p>{clean(getValue(runner, ["official", "runner"]))} maps in the {item.lane.toLowerCase()} group with {item.confidence.toLowerCase()}. {item.barrierContext} {item.earlyWatch}</p>
        </section>
      </div>
    </section>
  );
}

export function MapWorkspace(props: MapWorkspaceProps) {
  if (props.mode === "runner") return <RunnerMap {...props} />;
  return <RaceMap {...props} />;
}
'''

CSS_START = ".eiq-map-workspace {"
CSS_END = "/* EDGEIQ OS navigation restructure */"

CSS_TEXT = r'''.eiq-map-workspace {
  display: grid;
  gap: 12px;
}

.eiq-map-workspace__header,
.eiq-speed-map,
.eiq-map-side section,
.eiq-runner-map-sequence section {
  border: 1px solid rgba(244, 248, 248, 0.08);
  border-radius: 12px;
  background: rgba(3, 8, 10, 0.66);
}

.eiq-map-workspace__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 14px;
}

.eiq-map-workspace__header > div {
  min-width: 0;
}

.eiq-map-workspace__header span,
.eiq-speed-map__title span,
.eiq-speed-map__lane header span,
.eiq-map-side span,
.eiq-runner-map-sequence span,
.eiq-map-runner-card dt {
  display: block;
  color: #557aa8;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.13em;
  text-transform: uppercase;
}

.eiq-map-workspace__header strong,
.eiq-speed-map__title strong,
.eiq-map-side strong,
.eiq-runner-map-sequence strong {
  display: block;
  margin-top: 5px;
  color: #f4f8f8;
}

.eiq-map-workspace__header > div > strong {
  font-size: 22px;
}

.eiq-map-workspace__header p,
.eiq-map-side p,
.eiq-runner-map-sequence p {
  margin: 6px 0 0;
  color: rgba(244, 248, 248, 0.62);
  font-size: 12px;
  line-height: 1.45;
}

.eiq-map-workspace__header aside {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.eiq-map-workspace__header aside div {
  min-width: 112px;
  padding: 8px 10px;
  border: 1px solid rgba(244, 248, 248, 0.08);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.018);
}

.eiq-map-workspace__header aside strong {
  font-size: 13px;
}

.eiq-map-workspace__body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 310px;
  gap: 12px;
}

.eiq-speed-map {
  padding: 12px;
  overflow: hidden;
}

.eiq-speed-map__title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.eiq-speed-map__title strong {
  color: rgba(244, 248, 248, 0.66);
  font-size: 11px;
  font-weight: 800;
}

.eiq-speed-map__title i {
  display: inline-block;
  width: 18px;
  height: 1px;
  margin: 0 7px 3px;
  background: rgba(85, 122, 168, 0.44);
}

.eiq-speed-map__lanes {
  display: grid;
  gap: 6px;
}

.eiq-speed-map__lane {
  display: grid;
  grid-template-columns: 104px minmax(0, 1fr);
  min-height: 76px;
  border-top: 1px solid rgba(244, 248, 248, 0.07);
}

.eiq-speed-map__lane header {
  padding: 10px 9px 0 0;
}

.eiq-speed-map__lane header em {
  display: block;
  margin-top: 5px;
  color: rgba(244, 248, 248, 0.48);
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
}

.eiq-speed-map__lane > div {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
  gap: 7px;
  min-width: 0;
  padding: 7px 0;
}

.eiq-speed-map__lane > div > p {
  align-self: center;
  margin: 0;
  color: rgba(244, 248, 248, 0.5);
  font-size: 12px;
}

.eiq-map-runner-card {
  min-width: 0;
  min-height: 68px;
  padding: 8px 9px;
  border: 1px solid rgba(85, 122, 168, 0.18);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.022);
  color: inherit;
  text-align: left;
}

button.eiq-map-runner-card {
  cursor: pointer;
}

button.eiq-map-runner-card:hover {
  border-color: rgba(85, 122, 168, 0.5);
  background: rgba(85, 122, 168, 0.08);
}

.eiq-map-runner-card.is-scratched {
  opacity: 0.46;
}

.eiq-map-runner-card__top {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.eiq-map-runner-card__top b {
  flex: 0 0 24px;
  display: inline-flex;
  min-height: 24px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(85, 122, 168, 0.42);
  border-radius: 999px;
  color: #f4f8f8;
  font-size: 12px;
}

.eiq-map-runner-card__top strong {
  min-width: 0;
  color: #f4f8f8;
  font-size: 12px;
  font-weight: 900;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eiq-map-runner-card__middle {
  display: flex;
  gap: 8px;
  margin-top: 7px;
  color: rgba(244, 248, 248, 0.72);
  font-size: 11px;
  font-weight: 800;
}

.eiq-map-runner-card dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 5px 7px;
  margin: 7px 0 0;
}

.eiq-map-runner-card dd {
  margin: 2px 0 0;
  color: rgba(244, 248, 248, 0.76);
  font-size: 11px;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eiq-map-runner-card em {
  display: block;
  margin-top: 7px;
  color: rgba(244, 248, 248, 0.5);
  font-size: 11px;
  font-style: normal;
}

.eiq-map-side {
  display: grid;
  align-content: start;
  gap: 12px;
}

.eiq-map-side section {
  padding: 13px;
}

.eiq-map-side ul {
  display: grid;
  gap: 7px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  color: rgba(244, 248, 248, 0.64);
  font-size: 12px;
}

.eiq-map-side dl {
  display: grid;
  gap: 8px;
  margin: 11px 0 0;
}

.eiq-map-side dl div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(244, 248, 248, 0.07);
}

.eiq-map-side dt,
.eiq-map-side dd {
  margin: 0;
  color: rgba(244, 248, 248, 0.62);
  font-size: 12px;
}

.eiq-map-side dd {
  color: #f4f8f8;
  font-weight: 800;
}

.eiq-runner-map-sequence {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.eiq-runner-map-sequence section {
  padding: 13px;
}

.eiq-runner-map-sequence strong {
  font-size: 15px;
}

.eiq-runner-map-sequence__summary {
  grid-column: 1 / -1;
}

@media (max-width: 1180px) {
  .eiq-map-workspace__body {
    grid-template-columns: 1fr;
  }

  .eiq-runner-map-sequence {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .eiq-map-workspace__header,
  .eiq-speed-map__title {
    display: grid;
  }

  .eiq-map-workspace__header aside {
    justify-content: stretch;
  }

  .eiq-map-workspace__header aside div {
    min-width: 0;
  }

  .eiq-speed-map__lane {
    grid-template-columns: 1fr;
  }

  .eiq-runner-map-sequence {
    grid-template-columns: 1fr;
  }
}

'''


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def checkpoint(path: Path) -> Path:
    target = path.with_name(f"{path.stem}_CHECKPOINT_BEFORE_MAP_WORKSPACE_V2_{STAMP}{path.suffix}")
    target.write_text(read(path), encoding="utf-8", newline="\n")
    return target


def replace_css(css: str) -> str:
    start = css.find(CSS_START)
    end = css.find(CSS_END)
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("Expected MAP V1 CSS block was not found.")
    return css[:start] + CSS_TEXT + "\n" + css[end:]


def main() -> None:
    if not MAP_PATH.exists():
        raise RuntimeError(f"Missing MAP workspace: {MAP_PATH}")
    if not CSS_PATH.exists():
        raise RuntimeError(f"Missing stylesheet: {CSS_PATH}")

    current_map = read(MAP_PATH)
    required_markers = [
        "type MapWorkspaceProps",
        "const lanes: MapLane[]",
        "function RaceMap",
        "function RunnerMap",
        "export function MapWorkspace",
    ]
    missing = [marker for marker in required_markers if marker not in current_map]
    if missing:
        raise RuntimeError(f"MAP V1 structure not present; missing markers: {missing}")

    css = read(CSS_PATH)
    if CSS_START not in css or CSS_END not in css:
        raise RuntimeError("MAP V1 stylesheet markers not present.")

    checkpoints = [checkpoint(MAP_PATH), checkpoint(CSS_PATH)]
    write(MAP_PATH, MAP_TEXT)
    write(CSS_PATH, replace_css(css))

    print("EDGEIQ MAP WORKSPACE V2 implementation complete")
    print("Changed files:")
    print(f"- {MAP_PATH.relative_to(ROOT)}")
    print(f"- {CSS_PATH.relative_to(ROOT)}")
    print("Checkpoints:")
    for item in checkpoints:
        print(f"- {item.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
