from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")

tsx_backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_INVESTIGATION_UI_BUILD_20260709.tsx")
css_backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_INVESTIGATION_UI_BUILD_20260709.css")

tsx_backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")
css_backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

tsx.write_text(r'''import { Fragment, useMemo, useState } from "react";
import { RaceFileService } from "../services/RaceFileService";
import { CompareWorkspace } from "../compare/CompareWorkspace";

const file = RaceFileService.buildRaceBook();
const primary = file.field[0];

type WorkbenchMode = "history" | "evidence" | "compare";

function clean(value: any): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value)
    .replace(/Ã¢â€žÂ¢|â„¢/g, "™")
    .replace(/Ã‚Â·|Â·/g, "·")
    .replace(/Ã¢â‚¬â€|â€”/g, "—")
    .replace(/â€™/g, "’")
    .replace(/â†’/g, "→")
    .trim();
}

function market(value: any): string {
  const raw = clean(value);
  if (!raw || raw === "—" || raw.toUpperCase() === "MISSING") return "Not available";
  if (raw.toUpperCase() === "SCRATCHED") return "Scratched";
  const n = Number(raw);
  return Number.isFinite(n) ? `$${n.toFixed(n < 10 ? 2 : 0)}` : raw;
}

function weight(value: any): string {
  const raw = clean(value);
  return raw && raw !== "—" ? raw : "Not available";
}

function dna(value: any): string {
  const raw = clean(value);
  if (!raw || raw === "—" || raw.toUpperCase().includes("HTTP")) return "Not available";
  return raw;
}

function score(run: any): number {
  return Number(run?.professionalForm?.assignment?.score ?? 0);
}

function importance(run: any): "PRIMARY" | "SUPPORTING" | "REFERENCE" | "BACKGROUND" {
  const s = score(run);
  if (s >= 88) return "PRIMARY";
  if (s >= 76) return "SUPPORTING";
  if (s >= 62) return "REFERENCE";
  return "BACKGROUND";
}

function ratingBand(value: any): string {
  const n = Number(value ?? 0);
  if (n >= 90) return "Elite";
  if (n >= 84) return "Strong";
  if (n >= 76) return "Positive";
  if (n >= 68) return "Neutral";
  return "Caution";
}

function narrative(run: any): string {
  return clean(run?.professionalForm?.evidence?.narrative ?? "Useful historical reference. Open the run to test whether it transfers to today’s assignment.");
}

function verdict(run: any): string {
  return clean(run?.professionalForm?.assignment?.verdict ?? "Needs context");
}

function reasons(run: any): string[] {
  const list = run?.professionalForm?.assignment?.reasons ?? [];
  if (list.length) return list.map((x: string) => clean(x));
  return ["Historical race provides a usable reference point", "Performance can be tested against today’s assignment", "Race strength and run rating provide context"];
}

function changes(run: any): string[] {
  const list = run?.professionalForm?.assignment?.watch ?? [];
  if (list.length) return list.map((x: string) => clean(x));
  return ["Track, pressure and class should be checked before relying on this run", "Use as evidence, not as a standalone conclusion"];
}

function quality(run: any): string {
  const s = score(run);
  if (s >= 88) return "Strong";
  if (s >= 70) return "Useful";
  if (s >= 50) return "Limited";
  return "Weak";
}

function RatingTile({ label, value, sub }: { label: string; value: any; sub?: string }) {
  const band = ratingBand(value);
  return (
    <article className={`eiq-rating-tile is-${band.toLowerCase()}`}>
      <span>{label}</span>
      <strong>{clean(value)}</strong>
      <em>{sub ?? band}</em>
    </article>
  );
}

function EvidenceBadge({ run }: { run: any }) {
  const label = importance(run);
  return <b className={`eiq-evidence-badge is-${label.toLowerCase()}`}>{label}</b>;
}

function MatchBar({ value }: { value: number }) {
  const width = Math.max(4, Math.min(100, value));
  return (
    <div className="eiq-match-bar">
      <i style={{ width: `${width}%` }} />
      <strong>{value}%</strong>
    </div>
  );
}

function ComparisonTable({ run }: { run: any }) {
  const official = run.professionalForm?.official ?? {};
  const evidence = run.professionalForm?.evidence ?? {};
  const today = file.raceBook.official;
  const intelligence = file.raceBook.intelligence;

  const rows = [
    ["Distance", official.distance, today.distance, clean(official.distance) === clean(today.distance) ? "Same" : "Different"],
    ["Track", official.condition, today.trackCondition, clean(official.condition) === clean(today.trackCondition) ? "Same" : "Different"],
    ["Class", official.raceClass, today.raceClass, clean(official.raceClass) === clean(today.raceClass) ? "Similar" : "Check"],
    ["Barrier", official.barrier, primary?.official?.barrier, "Compare"],
    ["Weight", official.weight, primary?.official?.weight, "Compare"],
    ["Pressure", evidence.pressure, intelligence.pressure, clean(evidence.pressure) === clean(intelligence.pressure) ? "Aligned" : "Changed"],
    ["Tempo", evidence.tempo, intelligence.tempo, clean(evidence.tempo) === clean(intelligence.tempo) ? "Aligned" : "Changed"],
    ["Race Flow", evidence.raceFlow, intelligence.raceFlow, clean(evidence.raceFlow) === clean(intelligence.raceFlow) ? "Aligned" : "Changed"],
  ];

  return (
    <section className="eiq-what-changed">
      <span>What changed today</span>
      <table>
        <thead>
          <tr><th>Factor</th><th>Historical</th><th>Today</th><th>Assessment</th></tr>
        </thead>
        <tbody>
          {rows.map(([factor, historical, current, assessment]) => (
            <tr key={factor}>
              <td>{factor}</td>
              <td>{clean(historical)}</td>
              <td>{clean(current)}</td>
              <td>{assessment}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function RunInvestigationReport({ run }: { run: any }) {
  const official = run.professionalForm?.official ?? {};
  const evidence = run.professionalForm?.evidence ?? {};
  const match = score(run);

  return (
    <tr className="eiq-form-report-row">
      <td colSpan={19}>
        <section className="eiq-investigation-report-v2">
          <header>
            <div>
              <span>EDGEIQ Investigation</span>
              <strong>Can this run transfer to today?</strong>
              <p>{narrative(run)}</p>
            </div>
            <aside>
              <EvidenceBadge run={run} />
              <MatchBar value={match} />
            </aside>
          </header>

          <div className="eiq-investigation-core">
            <article>
              <span>Supported by</span>
              <ul>{reasons(run).map((x) => <li key={x}>✓ {x}</li>)}</ul>
            </article>
            <article>
              <span>Different today</span>
              <ul>{changes(run).map((x) => <li key={x}>⚠ {x}</li>)}</ul>
            </article>
            <article>
              <span>Evidence quality</span>
              <strong>{quality(run)}</strong>
              <p>{match}% assignment match. Treat this as {importance(run).toLowerCase()} evidence within the wider investigation.</p>
            </article>
          </div>

          <div className="eiq-rating-strip">
            <RatingTile label="Run Rating™" value={evidence.runRating?.overall ?? run.edgeiqRunRating} />
            <RatingTile label="Race Strength™" value={evidence.raceStrength?.overall ?? run.edgeiqRaceStrength} />
            <RatingTile label="Pressure" value={evidence.pressure} sub="Profile" />
            <RatingTile label="Tempo" value={evidence.tempo} sub="Race speed" />
            <RatingTile label="Assignment" value={match} sub={importance(run)} />
          </div>

          <ComparisonTable run={run} />

          <section className="eiq-official-record">
            <span>Official record</span>
            <dl>
              <div><dt>Date</dt><dd>{clean(official.date)}</dd></div>
              <div><dt>Track</dt><dd>{clean(official.track)}</dd></div>
              <div><dt>Distance</dt><dd>{clean(official.distance)}</dd></div>
              <div><dt>Class</dt><dd>{clean(official.raceClass)}</dd></div>
              <div><dt>Condition</dt><dd>{clean(official.condition)}</dd></div>
              <div><dt>Barrier</dt><dd>{clean(official.barrier)}</dd></div>
              <div><dt>Weight</dt><dd>{weight(official.weight)}</dd></div>
              <div><dt>Jockey</dt><dd>{clean(official.jockey)}</dd></div>
              <div><dt>SP</dt><dd>{market(official.sp)}</dd></div>
              <div><dt>Finish</dt><dd>{clean(official.finish)}</dd></div>
              <div><dt>Margin</dt><dd>{clean(official.margin)}</dd></div>
              <div><dt>Field</dt><dd>{clean(official.fieldSize)}</dd></div>
            </dl>
          </section>

          <footer>
            <button type="button">Open Race Book</button>
            <button type="button">Compare Runs</button>
            <button type="button">Evidence Trace</button>
          </footer>
        </section>
      </td>
    </tr>
  );
}

function ProfessionalFormTable({ runs }: { runs: any[] }) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  return (
    <div className="eiq-professional-form-table eiq-investigation-table-v2">
      <table>
        <thead>
          <tr>
            <th></th><th>Evidence</th><th>Date</th><th>Track</th><th>Dist</th><th>Class</th><th>Cond</th><th>Bar</th><th>Wt</th><th>Jockey</th><th>SP</th><th>Fin</th><th>Margin</th><th>Run</th><th>Race</th><th>Pressure</th><th>Tempo</th><th>Use</th><th>Why</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run: any, index: number) => {
            const key = `${run.date}-${run.track}-${run.race}-${index}`;
            const official = run.professionalForm?.official ?? {};
            const evidence = run.professionalForm?.evidence ?? {};
            const isOpen = openKey === key;

            return (
              <Fragment key={key}>
                <tr className={isOpen ? "is-open" : ""} onClick={() => setOpenKey(isOpen ? null : key)}>
                  <td>{isOpen ? "▾" : "▸"}</td>
                  <td><EvidenceBadge run={run} /></td>
                  <td>{clean(official.date)}</td>
                  <td><strong>{clean(official.track)}</strong></td>
                  <td>{clean(official.distance)}</td>
                  <td>{clean(official.raceClass)}</td>
                  <td>{clean(official.condition)}</td>
                  <td>{clean(official.barrier)}</td>
                  <td>{weight(official.weight)}</td>
                  <td>{clean(official.jockey)}</td>
                  <td>{market(official.sp)}</td>
                  <td>{clean(official.finish)}</td>
                  <td>{clean(official.margin)}</td>
                  <td><b>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)}</b><em>{ratingBand(evidence.runRating?.overall ?? run.edgeiqRunRating)}</em></td>
                  <td><b>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</b><em>{ratingBand(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</em></td>
                  <td>{clean(evidence.pressure)}</td>
                  <td>{clean(evidence.tempo)}</td>
                  <td>{importance(run) === "PRIMARY" ? "Use" : importance(run) === "BACKGROUND" ? "Context" : "Review"}</td>
                  <td>{narrative(run)}</td>
                </tr>
                {isOpen ? <RunInvestigationReport run={run} /> : null}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function RaceFileV3() {
  const [mode, setMode] = useState<WorkbenchMode>("history");

  const displayedRuns = useMemo(() => {
    if (!primary) return [];
    if (mode === "evidence") return (primary as any).evidenceRuns ?? primary.historicalRuns;
    return primary.historicalRuns;
  }, [mode]);

  const bestRun = displayedRuns[0];

  return (
    <section className="eiq-form-workbench eiq-investigation-workbench-v2">
      <section className="eiq-investigation-brief-v2">
        <div>
          <span>Today’s investigation</span>
          <strong>Can {clean(primary?.official?.runner)} reproduce its strongest historical reference under today’s conditions?</strong>
          <p>{clean(file.raceBook.official.meeting)} R{clean(file.raceBook.official.raceNumber)} · {clean(file.raceBook.official.distance)} · {clean(file.raceBook.official.trackCondition)} · {clean(file.raceBook.intelligence.pressure)} pressure</p>
        </div>
        <article>
          <span>Primary evidence</span>
          <strong>{bestRun ? `${clean(bestRun.professionalForm?.official?.track)} · ${clean(bestRun.professionalForm?.official?.distance)} · ${clean(bestRun.professionalForm?.official?.raceClass)}` : "No historical evidence"}</strong>
          <p>{bestRun ? narrative(bestRun) : "Historical evidence is not available for this runner."}</p>
        </article>
        <article>
          <span>Evidence match</span>
          {bestRun ? <MatchBar value={score(bestRun)} /> : <strong>Not available</strong>}
          <p>{bestRun ? `${quality(bestRun)} evidence quality` : "No match available"}</p>
        </article>
      </section>

      {primary ? (
        <>
          <section className="eiq-analyst-ribbon-v2">
            <div>
              <span>Runner</span>
              <strong>{clean(primary.official.runner)}</strong>
            </div>
            <dl>
              <div><dt>Trainer</dt><dd>{clean(primary.official.trainer)}</dd></div>
              <div><dt>Jockey</dt><dd>{clean(primary.official.jockey)}</dd></div>
              <div><dt>Barrier</dt><dd>{clean(primary.official.barrier)}</dd></div>
              <div><dt>Weight</dt><dd>{weight(primary.official.weight)}</dd></div>
              <div><dt>Market</dt><dd>{market(primary.official.market)}</dd></div>
              <div><dt>DNA</dt><dd>{dna(primary.runnerDNA)}</dd></div>
              <div><dt>Evidence</dt><dd>{bestRun ? importance(bestRun) : "Not available"}</dd></div>
            </dl>
          </section>

          <section className="eiq-start-investigation-v2">
            <div>
              <span>Investigation queue</span>
              <ol>
                <li className="is-done">Primary run loaded</li>
                <li className="is-done">Conditions compared</li>
                <li>Counter evidence</li>
                <li>Verdict</li>
              </ol>
            </div>
            <button type="button" onClick={() => document.querySelector(".eiq-investigation-table-v2")?.scrollIntoView({ behavior: "smooth", block: "start" })}>Start Investigation →</button>
          </section>

          <section className="eiq-form-toolbar">
            <div>
              <span>Professional historical form</span>
              <strong>Evidence hierarchy · official form · today’s comparison</strong>
            </div>
            <nav>
              <button type="button" className={mode === "history" ? "is-active" : ""} onClick={() => setMode("history")}>History</button>
              <button type="button" className={mode === "evidence" ? "is-active" : ""} onClick={() => setMode("evidence")}>Evidence</button>
              <button type="button" className={mode === "compare" ? "is-active" : ""} onClick={() => setMode("compare")}>Compare</button>
              <i />
              <button type="button">Columns</button>
              <button type="button">Filter</button>
              <button type="button">Sort</button>
              <i />
              <button type="button">Find</button>
              <button type="button">Export</button>
            </nav>
          </section>

          {mode === "compare" ? <CompareWorkspace /> : <ProfessionalFormTable runs={displayedRuns} />}
        </>
      ) : null}
    </section>
  );
}
''', encoding="utf-8")

css.write_text(css.read_text(encoding="utf-8") + r'''

/* EDGEIQ INVESTIGATION UI BUILD — V9 */
.eiq-investigation-workbench-v2 {
  --eiq-blue: #5f86b8;
  --eiq-line: rgba(95,134,184,.18);
  --eiq-panel: rgba(3,8,10,.66);
  max-width: 1680px !important;
  margin: 0 auto !important;
  padding: 18px 22px 36px !important;
}

.eiq-investigation-brief-v2,
.eiq-analyst-ribbon-v2,
.eiq-start-investigation-v2,
.eiq-investigation-table-v2,
.eiq-investigation-report-v2 {
  border: 1px solid var(--eiq-line);
  border-radius: 10px;
  background: var(--eiq-panel);
}

.eiq-investigation-brief-v2 {
  display: grid;
  grid-template-columns: 1.35fr .9fr .65fr;
  overflow: hidden;
}

.eiq-investigation-brief-v2 > div,
.eiq-investigation-brief-v2 > article {
  min-height: 126px;
  padding: 20px 22px;
  border-right: 1px solid var(--eiq-line);
}

.eiq-investigation-brief-v2 > article:last-child { border-right: 0; }

.eiq-investigation-workbench-v2 span,
.eiq-investigation-workbench-v2 dt {
  color: var(--eiq-blue) !important;
  display: block;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .16em;
  text-transform: uppercase;
}

.eiq-investigation-workbench-v2 strong {
  color: #f4f8f8;
}

.eiq-investigation-brief-v2 strong {
  display: block;
  margin-top: 9px;
  font-size: 20px;
  line-height: 1.3;
}

.eiq-investigation-brief-v2 article strong { font-size: 15px; }

.eiq-investigation-workbench-v2 p {
  margin: 8px 0 0;
  color: rgba(244,248,248,.66);
  font-size: 12px;
  line-height: 1.48;
}

.eiq-match-bar {
  display: grid;
  grid-template-columns: minmax(80px, 1fr) 48px;
  gap: 10px;
  align-items: center;
  margin-top: 12px;
}

.eiq-match-bar i {
  height: 7px;
  border-radius: 999px;
  background: var(--eiq-blue);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
}

.eiq-match-bar strong {
  font-size: 13px !important;
  text-align: right;
}

.eiq-analyst-ribbon-v2 {
  display: grid;
  grid-template-columns: 280px minmax(0,1fr);
  margin-top: 14px;
  overflow: hidden;
}

.eiq-analyst-ribbon-v2 > div {
  padding: 17px 18px;
  border-right: 1px solid var(--eiq-line);
}

.eiq-analyst-ribbon-v2 > div strong {
  display: block;
  margin-top: 8px;
  font-size: 22px;
}

.eiq-analyst-ribbon-v2 dl {
  display: grid;
  grid-template-columns: repeat(7, minmax(0,1fr));
  margin: 0;
}

.eiq-analyst-ribbon-v2 dl div {
  padding: 17px 14px;
  border-right: 1px solid rgba(95,134,184,.12);
}

.eiq-analyst-ribbon-v2 dl div:last-child { border-right: 0; }

.eiq-analyst-ribbon-v2 dd {
  margin: 8px 0 0;
  color: #f4f8f8;
  font-size: 13px;
  font-weight: 800;
}

.eiq-start-investigation-v2 {
  display: grid;
  grid-template-columns: minmax(0,1fr) auto;
  align-items: center;
  gap: 18px;
  margin-top: 14px;
  padding: 15px 18px;
}

.eiq-start-investigation-v2 ol {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
}

.eiq-start-investigation-v2 li {
  color: rgba(244,248,248,.64);
  font-size: 11px;
  font-weight: 800;
}

.eiq-start-investigation-v2 li::before {
  content: "○";
  margin-right: 6px;
  color: rgba(244,248,248,.38);
}

.eiq-start-investigation-v2 li.is-done {
  color: #f4f8f8;
}

.eiq-start-investigation-v2 li.is-done::before {
  content: "✓";
  color: var(--eiq-blue);
}

.eiq-start-investigation-v2 button,
.eiq-investigation-report-v2 footer button {
  height: 36px;
  padding: 0 15px;
  border: 1px solid rgba(95,134,184,.32);
  border-radius: 999px;
  background: rgba(95,134,184,.055);
  color: var(--eiq-blue);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.eiq-investigation-table-v2 {
  margin-top: 14px;
  overflow-x: auto;
}

.eiq-investigation-table-v2 table {
  min-width: 1580px !important;
  table-layout: fixed !important;
  border-collapse: collapse;
  width: 100%;
}

.eiq-investigation-table-v2 th {
  position: sticky;
  top: 0;
  height: 42px;
  padding: 0 10px;
  background: #05090d;
  border-bottom: 1px solid var(--eiq-line);
  color: rgba(244,248,248,.58);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .12em;
  text-align: left;
  text-transform: uppercase;
  white-space: nowrap;
}

.eiq-investigation-table-v2 td {
  height: 44px;
  padding: 0 10px;
  border-bottom: 1px solid rgba(95,134,184,.09);
  color: rgba(244,248,248,.82);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.eiq-investigation-table-v2 tbody tr:hover td,
.eiq-investigation-table-v2 tbody tr.is-open td {
  background: rgba(95,134,184,.05);
}

.eiq-investigation-table-v2 td b {
  display: block;
  color: #f4f8f8;
}

.eiq-investigation-table-v2 td em {
  display: block;
  margin-top: 2px;
  color: rgba(244,248,248,.5);
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
  text-transform: uppercase;
}

.eiq-evidence-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .08em;
  background: rgba(255,255,255,.06);
  color: #f4f8f8;
}

.eiq-evidence-badge.is-primary { background: rgba(95,134,184,.28); }
.eiq-evidence-badge.is-supporting { background: rgba(58,105,83,.38); }
.eiq-evidence-badge.is-reference { background: rgba(115,115,115,.30); }
.eiq-evidence-badge.is-background { background: rgba(244,248,248,.08); color: rgba(244,248,248,.64); }

.eiq-investigation-report-v2 {
  margin: 0;
  padding: 18px;
  border-left: 3px solid rgba(95,134,184,.72);
  border-radius: 0;
}

.eiq-investigation-report-v2 header {
  display: grid;
  grid-template-columns: minmax(0,1fr) 220px;
  gap: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--eiq-line);
}

.eiq-investigation-report-v2 header strong {
  display: block;
  margin-top: 7px;
  font-size: 19px;
}

.eiq-investigation-report-v2 header aside {
  display: grid;
  gap: 8px;
  align-content: center;
}

.eiq-investigation-core {
  display: grid;
  grid-template-columns: 1fr 1fr .85fr;
  gap: 12px;
  margin-top: 14px;
}

.eiq-investigation-core article,
.eiq-what-changed,
.eiq-official-record,
.eiq-rating-tile {
  border: 1px solid rgba(95,134,184,.14);
  background: rgba(255,255,255,.018);
}

.eiq-investigation-core article {
  padding: 15px;
}

.eiq-investigation-core ul {
  display: grid;
  gap: 8px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
  color: rgba(244,248,248,.78);
  font-size: 12px;
  line-height: 1.35;
}

.eiq-investigation-core article > strong {
  display: block;
  margin-top: 12px;
  font-size: 18px;
}

.eiq-rating-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0,1fr));
  gap: 10px;
  margin-top: 12px;
}

.eiq-rating-tile {
  min-height: 80px;
  padding: 12px;
  border-left-width: 4px;
}

.eiq-rating-tile.is-elite { border-left-color: #234f86; background: rgba(35,79,134,.22); }
.eiq-rating-tile.is-strong { border-left-color: #245c43; background: rgba(36,92,67,.20); }
.eiq-rating-tile.is-positive { border-left-color: #596847; background: rgba(89,104,71,.18); }
.eiq-rating-tile.is-neutral { border-left-color: #555; background: rgba(255,255,255,.035); }
.eiq-rating-tile.is-caution { border-left-color: #6b4b30; background: rgba(107,75,48,.18); }

.eiq-rating-tile strong {
  display: block;
  margin-top: 8px;
  font-size: 18px;
}

.eiq-rating-tile em {
  display: block;
  margin-top: 2px;
  color: rgba(244,248,248,.58);
  font-size: 10px;
  font-style: normal;
  font-weight: 900;
  text-transform: uppercase;
}

.eiq-what-changed,
.eiq-official-record {
  margin-top: 12px;
  padding: 14px;
}

.eiq-what-changed table {
  width: 100%;
  margin-top: 12px;
  border-collapse: collapse;
}

.eiq-what-changed th,
.eiq-what-changed td {
  height: 34px;
  border-bottom: 1px solid rgba(95,134,184,.10);
  color: rgba(244,248,248,.78);
  font-size: 12px;
  text-align: left;
}

.eiq-what-changed th {
  color: rgba(244,248,248,.48);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .1em;
}

.eiq-official-record dl {
  display: grid;
  grid-template-columns: repeat(12, minmax(0,1fr));
  gap: 10px;
  margin: 12px 0 0;
}

.eiq-official-record dd {
  margin: 4px 0 0;
  color: #f4f8f8;
  font-size: 12px;
  font-weight: 800;
}

.eiq-investigation-report-v2 footer {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--eiq-line);
}

@media (max-width: 1350px) {
  .eiq-investigation-brief-v2,
  .eiq-analyst-ribbon-v2,
  .eiq-start-investigation-v2,
  .eiq-investigation-core,
  .eiq-investigation-report-v2 header {
    grid-template-columns: 1fr;
  }

  .eiq-analyst-ribbon-v2 dl,
  .eiq-rating-strip,
  .eiq-official-record dl {
    grid-template-columns: repeat(2, minmax(0,1fr));
  }
}
''', encoding="utf-8")

print("[EDGEIQ] Investigation UI V9 built")
print(f"[EDGEIQ] TSX checkpoint: {tsx_backup}")
print(f"[EDGEIQ] CSS checkpoint: {css_backup}")
