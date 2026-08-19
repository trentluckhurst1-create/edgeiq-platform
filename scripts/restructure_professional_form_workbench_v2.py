from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")

tsx_backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_WORKBENCH_RESTRUCTURE_20260709.tsx")
css_backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_WORKBENCH_RESTRUCTURE_20260709.css")

tsx_backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")
css_backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

content = r'''import { useMemo, useState } from "react";
import { RaceFileService } from "../services/RaceFileService";
import { CompareWorkspace } from "../compare/CompareWorkspace";

const file = RaceFileService.buildRaceBook();
const primary = file.field[0];

type WorkbenchMode = "historical" | "evidence" | "compare";

function clean(value: any): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value).replace(/â„¢/g, "™").replace(/Â·/g, "·").replace(/â€”/g, "—");
}

function score(run: any): number {
  return run?.professionalForm?.assignment?.score ?? 0;
}

function verdict(run: any): string {
  return clean(run?.professionalForm?.assignment?.verdict ?? "NEEDS CONTEXT");
}

function narrative(run: any): string {
  return clean(run?.professionalForm?.evidence?.narrative ?? "Background form. Useful context, but not a primary match for today.");
}

function ratingBand(value: any): string {
  const n = Number(value ?? 0);
  if (n >= 90) return "Elite";
  if (n >= 84) return "Strong";
  if (n >= 76) return "Positive";
  if (n >= 68) return "Neutral";
  return "Caution";
}

function RunIntelligenceReport({ run }: { run: any }) {
  const form = run.professionalForm ?? {};
  const official = form.official ?? {};
  const evidence = form.evidence ?? {};
  const assignment = form.assignment ?? {};

  return (
    <tr className="eiq-form-report-row">
      <td colSpan={19}>
        <section className="eiq-run-report">
          <header className="eiq-run-report__top">
            <div>
              <span>Run Intelligence Report</span>
              <strong>{clean(official.date)} · {clean(official.track)} · {clean(official.distance)} · {clean(official.raceClass)}</strong>
            </div>
            <aside>
              <b>{score(run)}%</b>
              <em>{verdict(run)}</em>
            </aside>
          </header>

          <div className="eiq-run-report__grid">
            <article>
              <span>Race Record</span>
              <dl>
                <div><dt>Condition</dt><dd>{clean(official.condition)}</dd></div>
                <div><dt>Barrier</dt><dd>{clean(official.barrier)}</dd></div>
                <div><dt>Weight</dt><dd>{clean(official.weight)}</dd></div>
                <div><dt>Jockey</dt><dd>{clean(official.jockey)}</dd></div>
                <div><dt>SP</dt><dd>{clean(official.sp)}</dd></div>
                <div><dt>Finish</dt><dd>{clean(official.finish)}</dd></div>
                <div><dt>Margin</dt><dd>{clean(official.margin)}</dd></div>
                <div><dt>Field</dt><dd>{clean(official.fieldSize)}</dd></div>
              </dl>
            </article>

            <article>
              <span>Performance Analysis</span>
              <strong>{narrative(run)}</strong>
              <dl>
                <div><dt>Run Rating™</dt><dd>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)} · {ratingBand(evidence.runRating?.overall ?? run.edgeiqRunRating)}</dd></div>
                <div><dt>Race Strength™</dt><dd>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)} · {ratingBand(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</dd></div>
                <div><dt>Pressure</dt><dd>{clean(evidence.pressure)}</dd></div>
                <div><dt>Tempo</dt><dd>{clean(evidence.tempo)}</dd></div>
                <div><dt>RaceFlow™</dt><dd>{clean(evidence.raceFlow)}</dd></div>
                <div><dt>RunnerDNA™</dt><dd>{clean(evidence.runnerDNA)}</dd></div>
              </dl>
            </article>

            <article>
              <span>Today’s Fit</span>
              <strong>{clean(assignment.assessment)}</strong>
              <div className="eiq-run-report__reasons">
                {(assignment.reasons ?? []).map((reason: string) => <em key={reason}>{clean(reason)}</em>)}
                {(assignment.watch ?? []).map((reason: string) => <em key={reason}>Watch: {clean(reason)}</em>)}
              </div>
            </article>
          </div>

          <footer>
            <button type="button">Open Historical Race Book →</button>
            <button type="button">Compare This Run →</button>
            <button type="button">Trace Evidence →</button>
          </footer>
        </section>
      </td>
    </tr>
  );
}

function ProfessionalFormTable({ runs }: { runs: any[] }) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  return (
    <div className="eiq-professional-form-table">
      <table>
        <thead>
          <tr>
            <th></th>
            <th>Date</th>
            <th>Track</th>
            <th>Dist</th>
            <th>Class</th>
            <th>Cond</th>
            <th>Bar</th>
            <th>Wt</th>
            <th>Jockey</th>
            <th>SP</th>
            <th>Fin</th>
            <th>Margin</th>
            <th>Run Rtg</th>
            <th>Race Rtg</th>
            <th>Pressure</th>
            <th>Tempo</th>
            <th>Fit</th>
            <th>Use Today</th>
            <th>Why</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run: any, index: number) => {
            const key = `${run.date}-${run.track}-${run.race}-${index}`;
            const form = run.professionalForm ?? {};
            const official = form.official ?? {};
            const evidence = form.evidence ?? {};
            const isOpen = openKey === key;
            const fit = score(run);

            return (
              <>
                <tr key={key} className={isOpen ? "is-open" : ""} onClick={() => setOpenKey(isOpen ? null : key)}>
                  <td>{isOpen ? "▾" : "▸"}</td>
                  <td>{clean(official.date)}</td>
                  <td><strong>{clean(official.track)}</strong></td>
                  <td>{clean(official.distance)}</td>
                  <td>{clean(official.raceClass)}</td>
                  <td>{clean(official.condition)}</td>
                  <td>{clean(official.barrier)}</td>
                  <td>{clean(official.weight)}</td>
                  <td>{clean(official.jockey)}</td>
                  <td>{clean(official.sp)}</td>
                  <td>{clean(official.finish)}</td>
                  <td>{clean(official.margin)}</td>
                  <td><b>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)}</b><em>{ratingBand(evidence.runRating?.overall ?? run.edgeiqRunRating)}</em></td>
                  <td><b>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</b><em>{ratingBand(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</em></td>
                  <td>{clean(evidence.pressure)}</td>
                  <td>{clean(evidence.tempo)}</td>
                  <td><b>{fit}%</b><em>{verdict(run)}</em></td>
                  <td>{fit >= 80 ? "Primary" : fit >= 60 ? "Review" : "Context"}</td>
                  <td>{narrative(run)}</td>
                </tr>
                {isOpen ? <RunIntelligenceReport key={`${key}-report`} run={run} /> : null}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function RaceFileV3() {
  const [mode, setMode] = useState<WorkbenchMode>("historical");

  const displayedRuns = useMemo(() => {
    if (!primary) return [];
    if (mode === "evidence") return (primary as any).evidenceRuns ?? primary.historicalRuns;
    return primary.historicalRuns;
  }, [mode]);

  const bestRun = displayedRuns[0];

  return (
    <section className="eiq-form-workbench eiq-form-workbench-v2">
      <section className="eiq-assignment-command">
        <div>
          <span>Today’s Assignment</span>
          <strong>{clean(file.raceBook.official.meeting)} R{clean(file.raceBook.official.raceNumber)} · {clean(file.raceBook.official.distance)} · {clean(file.raceBook.official.raceClass)}</strong>
          <p>{clean(file.raceBook.official.trackCondition)} · {clean(file.raceBook.official.rail)} · {clean(file.raceBook.intelligence.raceFlow)} race shape · {clean(file.raceBook.intelligence.pressure)} pressure</p>
        </div>
        <article>
          <span>Primary Evidence</span>
          <strong>{bestRun ? `${clean(bestRun.professionalForm?.official?.track)} · ${clean(bestRun.professionalForm?.official?.distance)} · ${clean(bestRun.professionalForm?.official?.raceClass)}` : "Evidence building"}</strong>
          <p>{bestRun ? narrative(bestRun) : "No historical run selected."}</p>
        </article>
        <article>
          <span>Key Risk</span>
          <strong>{bestRun ? verdict(bestRun) : "Pending"}</strong>
          <p>Open the professional form table to validate whether the horse has already completed today’s assignment.</p>
        </article>
      </section>

      {primary ? (
        <>
          <section className="eiq-runner-strip">
            <div className="eiq-runner-strip__horse">
              <span>Runner</span>
              <strong>{clean(primary.official.runner)}</strong>
              <p>{clean(primary.assessment)}</p>
            </div>
            <dl>
              <div><dt>Trainer</dt><dd>{clean(primary.official.trainer)}</dd></div>
              <div><dt>Jockey</dt><dd>{clean(primary.official.jockey)}</dd></div>
              <div><dt>Barrier</dt><dd>{clean(primary.official.barrier)}</dd></div>
              <div><dt>Weight</dt><dd>{clean(primary.official.weight)}</dd></div>
              <div><dt>Market</dt><dd>{clean(primary.official.market)}</dd></div>
              <div><dt>RunnerDNA™</dt><dd>{clean(primary.runnerDNA)}</dd></div>
            </dl>
          </section>

          <section className="eiq-form-action-row">
            <div>
              <span>Analyst Summary</span>
              <strong>{bestRun ? `${score(bestRun)}% assignment match · ${verdict(bestRun)}` : "Evidence still building"}</strong>
              <p>{bestRun ? "Start with the professional form table. Expand the primary run, then compare it against today’s assignment." : "No historical runs available."}</p>
            </div>
            <button type="button" onClick={() => document.querySelector(".eiq-professional-form-table")?.scrollIntoView({ behavior: "smooth", block: "start" })}>
              Continue to Professional Form →
            </button>
          </section>

          <section className="eiq-form-toolbar">
            <div>
              <span>Professional Historical Form</span>
              <strong>Official form · EDGEIQ evidence · assignment fit</strong>
            </div>
            <nav>
              <button type="button" className={mode === "historical" ? "is-active" : ""} onClick={() => setMode("historical")}>History</button>
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
'''

tsx.write_text(content, encoding="utf-8")

style = r'''

/* EDGEIQ FORM DESK — WORKBENCH RESTRUCTURE V2 */
.eiq-form-workbench-v2 {
  max-width: 1560px;
  margin: 0 auto;
  padding: 18px 22px 34px;
}

.eiq-assignment-command {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, .9fr) minmax(260px, .8fr);
  gap: 0;
  border: 1px solid rgba(90,255,220,.12);
  border-radius: 10px;
  overflow: hidden;
  background:
    radial-gradient(circle at 78% 20%, rgba(67,239,198,.07), transparent 30%),
    rgba(3,8,10,.70);
}

.eiq-assignment-command > div,
.eiq-assignment-command > article {
  min-height: 122px;
  padding: 20px 22px;
  border-right: 1px solid rgba(90,255,220,.08);
}

.eiq-assignment-command > article:last-child {
  border-right: 0;
}

.eiq-assignment-command span,
.eiq-runner-strip span,
.eiq-form-action-row span {
  display: block;
  color: #43efc6;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .16em;
  text-transform: uppercase;
}

.eiq-assignment-command strong {
  display: block;
  margin-top: 10px;
  color: #f4f8f8;
  font-size: 21px;
  font-weight: 650;
  line-height: 1.25;
}

.eiq-assignment-command article strong {
  font-size: 15px;
}

.eiq-assignment-command p,
.eiq-runner-strip p,
.eiq-form-action-row p {
  margin: 8px 0 0;
  color: rgba(244,248,248,.66);
  font-size: 12px;
  line-height: 1.45;
}

.eiq-runner-strip {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  align-items: stretch;
  margin-top: 14px;
  border: 1px solid rgba(90,255,220,.12);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(3,8,10,.62);
}

.eiq-runner-strip__horse {
  padding: 18px 20px;
  border-right: 1px solid rgba(90,255,220,.08);
}

.eiq-runner-strip__horse strong {
  display: block;
  margin-top: 9px;
  color: #f4f8f8;
  font-size: 24px;
  font-weight: 650;
  line-height: 1.1;
}

.eiq-runner-strip dl {
  display: grid;
  grid-template-columns: repeat(6, minmax(0,1fr));
  margin: 0;
}

.eiq-runner-strip dl div {
  padding: 18px 16px;
  border-right: 1px solid rgba(90,255,220,.08);
}

.eiq-runner-strip dl div:last-child {
  border-right: 0;
}

.eiq-runner-strip dt {
  color: #43efc6;
  font-size: 9px;
  font-weight: 900;
  letter-spacing: .15em;
  text-transform: uppercase;
}

.eiq-runner-strip dd {
  margin: 9px 0 0;
  color: #f4f8f8;
  font-size: 13px;
  font-weight: 800;
}

.eiq-form-action-row {
  display: grid;
  grid-template-columns: minmax(0,1fr) auto;
  align-items: center;
  gap: 20px;
  margin-top: 14px;
  padding: 18px 20px;
  border: 1px solid rgba(90,255,220,.12);
  border-radius: 10px;
  background: rgba(3,8,10,.58);
}

.eiq-form-action-row strong {
  display: block;
  margin-top: 8px;
  color: #f4f8f8;
  font-size: 17px;
}

.eiq-form-action-row button {
  height: 42px;
  padding: 0 18px;
  border: 1px solid rgba(67,239,198,.42);
  border-radius: 999px;
  background: rgba(67,239,198,.08);
  color: #43efc6;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.eiq-form-toolbar nav i {
  width: 1px;
  height: 25px;
  margin: 3px 2px;
  background: rgba(90,255,220,.14);
}

.eiq-professional-form-table {
  margin-top: 14px;
  border: 1px solid rgba(90,255,220,.12);
  border-radius: 10px;
  background: rgba(3,8,10,.66);
}

.eiq-professional-form-table table {
  min-width: 1620px;
}

.eiq-professional-form-table th:nth-child(2),
.eiq-professional-form-table td:nth-child(2),
.eiq-professional-form-table th:nth-child(3),
.eiq-professional-form-table td:nth-child(3) {
  position: sticky;
  z-index: 3;
  background: #05090d;
}

.eiq-professional-form-table th:nth-child(2),
.eiq-professional-form-table td:nth-child(2) {
  left: 0;
}

.eiq-professional-form-table th:nth-child(3),
.eiq-professional-form-table td:nth-child(3) {
  left: 96px;
}

.eiq-professional-form-table tbody tr:hover td:nth-child(2),
.eiq-professional-form-table tbody tr:hover td:nth-child(3),
.eiq-professional-form-table tbody tr.is-open td:nth-child(2),
.eiq-professional-form-table tbody tr.is-open td:nth-child(3) {
  background: #071411;
}

.eiq-professional-form-table th {
  height: 42px;
}

.eiq-professional-form-table td {
  height: 44px;
}

.eiq-professional-form-table td:nth-child(19) {
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(244,248,248,.62);
}

.eiq-run-report__top {
  display: grid;
  grid-template-columns: minmax(0,1fr) 150px;
  align-items: center;
  gap: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(90,255,220,.08);
}

.eiq-run-report__top strong {
  display: block;
  margin-top: 7px;
  color: #f4f8f8;
  font-size: 17px;
}

.eiq-run-report__top aside {
  text-align: right;
}

.eiq-run-report__top b {
  display: block;
  color: #43efc6;
  font-size: 26px;
}

.eiq-run-report__top em {
  display: block;
  color: rgba(244,248,248,.65);
  font-size: 10px;
  font-style: normal;
  font-weight: 900;
  letter-spacing: .08em;
  text-transform: uppercase;
}

@media (max-width: 1350px) {
  .eiq-assignment-command,
  .eiq-runner-strip,
  .eiq-form-action-row {
    grid-template-columns: 1fr;
  }

  .eiq-runner-strip dl {
    grid-template-columns: repeat(2, minmax(0,1fr));
  }
}
'''

existing = css.read_text(encoding="utf-8")
if "EDGEIQ FORM DESK — WORKBENCH RESTRUCTURE V2" not in existing:
    existing += style
css.write_text(existing, encoding="utf-8")

print("[EDGEIQ] Professional Form Workbench restructure V2 applied")
print(f"[EDGEIQ] TSX checkpoint: {tsx_backup}")
print(f"[EDGEIQ] CSS checkpoint: {css_backup}")
