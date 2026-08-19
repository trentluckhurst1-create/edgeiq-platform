from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")

tsx_backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_INVESTIGATION_WORKBENCH_20260709.tsx")
css_backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_INVESTIGATION_WORKBENCH_20260709.css")

tsx_backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")
css_backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

content = r'''import { useMemo, useState } from "react";
import { RaceFileService } from "../services/RaceFileService";
import { CompareWorkspace } from "../compare/CompareWorkspace";

const file = RaceFileService.buildRaceBook();
const primary = file.field[0];

type WorkbenchMode = "history" | "evidence" | "compare";

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

function importance(run: any): string {
  const s = score(run);
  if (s >= 88) return "PRIMARY";
  if (s >= 76) return "HIGH";
  if (s >= 62) return "MEDIUM";
  if (s >= 45) return "LOW";
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

function reasonList(run: any): string[] {
  const assignment = run?.professionalForm?.assignment ?? {};
  const reasons = assignment.reasons ?? [];
  if (reasons.length) return reasons.map((x: string) => clean(x));
  return ["Closest available historical assignment", "Useful race-strength reference", "Relevant performance context"];
}

function counterList(run: any): string[] {
  const assignment = run?.professionalForm?.assignment ?? {};
  const watch = assignment.watch ?? [];
  if (watch.length) return watch.map((x: string) => clean(x));
  return ["Confirm distance transfer", "Check track condition", "Validate pressure profile"];
}

function RunInvestigationReport({ run }: { run: any }) {
  const form = run.professionalForm ?? {};
  const official = form.official ?? {};
  const evidence = form.evidence ?? {};
  const assignment = form.assignment ?? {};

  return (
    <tr className="eiq-form-report-row">
      <td colSpan={19}>
        <section className="eiq-investigation-report">
          <header>
            <div>
              <span>EDGEIQ Investigation</span>
              <strong>Why this run matters</strong>
              <p>{narrative(run)}</p>
            </div>
            <aside>
              <b>{importance(run)}</b>
              <em>{score(run)}% assignment match</em>
            </aside>
          </header>

          <div className="eiq-investigation-grid">
            <article className="eiq-investigation-primary">
              <span>Why EDGEIQ opened this run</span>
              <ul>
                {reasonList(run).map((reason) => <li key={reason}>{reason}</li>)}
              </ul>
            </article>

            <article>
              <span>Counter Evidence</span>
              <ul>
                {counterList(run).map((risk) => <li key={risk}>{risk}</li>)}
              </ul>
            </article>

            <article>
              <span>Evidence Confidence</span>
              <strong>{clean(assignment.evidenceConfidence ?? importance(run))}</strong>
              <p>Confidence is earned from similarity to today’s assignment, race strength, pressure, tempo and the number of unanswered contradictions.</p>
            </article>
          </div>

          <div className="eiq-investigation-metrics">
            <article><span>Run Rating™</span><strong>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)}</strong><em>{ratingBand(evidence.runRating?.overall ?? run.edgeiqRunRating)}</em></article>
            <article><span>Race Strength™</span><strong>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</strong><em>{ratingBand(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</em></article>
            <article><span>Pressure</span><strong>{clean(evidence.pressure)}</strong><em>Today comparison</em></article>
            <article><span>Tempo</span><strong>{clean(evidence.tempo)}</strong><em>Race speed</em></article>
            <article><span>RaceFlow™</span><strong>{clean(evidence.raceFlow)}</strong><em>Shape reference</em></article>
            <article><span>RunnerDNA™</span><strong>{clean(evidence.runnerDNA)}</strong><em>Profile fit</em></article>
          </div>

          <div className="eiq-investigation-record">
            <span>Official Race Record</span>
            <dl>
              <div><dt>Date</dt><dd>{clean(official.date)}</dd></div>
              <div><dt>Track</dt><dd>{clean(official.track)}</dd></div>
              <div><dt>Distance</dt><dd>{clean(official.distance)}</dd></div>
              <div><dt>Class</dt><dd>{clean(official.raceClass)}</dd></div>
              <div><dt>Condition</dt><dd>{clean(official.condition)}</dd></div>
              <div><dt>Barrier</dt><dd>{clean(official.barrier)}</dd></div>
              <div><dt>Weight</dt><dd>{clean(official.weight)}</dd></div>
              <div><dt>Jockey</dt><dd>{clean(official.jockey)}</dd></div>
              <div><dt>SP</dt><dd>{clean(official.sp)}</dd></div>
              <div><dt>Finish</dt><dd>{clean(official.finish)}</dd></div>
              <div><dt>Margin</dt><dd>{clean(official.margin)}</dd></div>
              <div><dt>Field</dt><dd>{clean(official.fieldSize)}</dd></div>
            </dl>
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
    <div className="eiq-professional-form-table eiq-investigation-table">
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
            <th>Evidence</th>
            <th>Use</th>
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
                  <td><b>{importance(run)}</b><em>{score(run)}% match</em></td>
                  <td>{importance(run) === "PRIMARY" ? "Use" : importance(run) === "BACKGROUND" ? "Context" : "Review"}</td>
                  <td>{narrative(run)}</td>
                </tr>
                {isOpen ? <RunInvestigationReport key={`${key}-report`} run={run} /> : null}
              </>
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
    <section className="eiq-form-workbench eiq-investigation-workbench">
      <section className="eiq-investigation-brief">
        <div>
          <span>Today’s Assignment</span>
          <strong>Can this horse reproduce its {bestRun ? `${clean(bestRun.professionalForm?.official?.track)} ${clean(bestRun.professionalForm?.official?.raceClass)}` : "best historical"} run under today’s pressure profile?</strong>
          <p>{clean(file.raceBook.official.meeting)} R{clean(file.raceBook.official.raceNumber)} · {clean(file.raceBook.official.distance)} · {clean(file.raceBook.official.trackCondition)} · {clean(file.raceBook.intelligence.raceFlow)} shape · {clean(file.raceBook.intelligence.pressure)} pressure</p>
        </div>
        <article>
          <span>Primary Evidence</span>
          <strong>{bestRun ? `${clean(bestRun.professionalForm?.official?.date)} · ${clean(bestRun.professionalForm?.official?.track)} · ${clean(bestRun.professionalForm?.official?.distance)}` : "Evidence building"}</strong>
          <p>{bestRun ? narrative(bestRun) : "No historical run selected."}</p>
        </article>
        <article>
          <span>Counter Evidence</span>
          <strong>{bestRun ? verdict(bestRun) : "Pending"}</strong>
          <p>{bestRun ? counterList(bestRun).slice(0, 2).join(" · ") : "Validate distance, track and pressure before deciding."}</p>
        </article>
      </section>

      {primary ? (
        <>
          <section className="eiq-analyst-ribbon">
            <div>
              <span>Runner Investigation</span>
              <strong>{clean(primary.official.runner)}</strong>
            </div>
            <dl>
              <div><dt>Trainer</dt><dd>{clean(primary.official.trainer)}</dd></div>
              <div><dt>Jockey</dt><dd>{clean(primary.official.jockey)}</dd></div>
              <div><dt>Barrier</dt><dd>{clean(primary.official.barrier)}</dd></div>
              <div><dt>Weight</dt><dd>{clean(primary.official.weight)}</dd></div>
              <div><dt>Market</dt><dd>{clean(primary.official.market)}</dd></div>
              <div><dt>DNA</dt><dd>{clean(primary.runnerDNA)}</dd></div>
              <div><dt>Evidence</dt><dd>{bestRun ? importance(bestRun) : "Pending"}</dd></div>
            </dl>
          </section>

          <section className="eiq-start-investigation">
            <div>
              <span>Analyst Summary</span>
              <strong>{bestRun ? `${importance(bestRun)} evidence · ${score(bestRun)}% assignment match` : "Evidence still building"}</strong>
              <p>{bestRun ? "Start with the highlighted historical run. Open it, inspect the counter evidence, then decide whether to compare or trace the evidence." : "No historical runs available."}</p>
            </div>
            <button type="button" onClick={() => document.querySelector(".eiq-investigation-table")?.scrollIntoView({ behavior: "smooth", block: "start" })}>
              Start Investigation →
            </button>
          </section>

          <section className="eiq-form-toolbar">
            <div>
              <span>Professional Historical Form</span>
              <strong>Official form · evidence importance · today’s assignment</strong>
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
'''

tsx.write_text(content, encoding="utf-8")

style = r'''

/* EDGEIQ FORM DESK — INVESTIGATION WORKBENCH V6 */
.eiq-investigation-workbench {
  max-width: 1640px !important;
  margin: 0 auto !important;
  padding: 18px 22px 36px !important;
  --eiq-soft-teal: #73c8b8;
  --eiq-soft-line: rgba(115,200,184,.15);
  --eiq-soft-fill: rgba(115,200,184,.045);
}

.eiq-investigation-brief,
.eiq-analyst-ribbon,
.eiq-start-investigation,
.eiq-investigation-report,
.eiq-investigation-record,
.eiq-investigation-metrics article {
  border-color: var(--eiq-soft-line) !important;
}

.eiq-investigation-brief {
  display: grid;
  grid-template-columns: 1.35fr .85fr .72fr;
  border: 1px solid var(--eiq-soft-line);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(3,8,10,.72);
}

.eiq-investigation-brief > div,
.eiq-investigation-brief > article {
  min-height: 128px;
  padding: 20px 22px;
  border-right: 1px solid var(--eiq-soft-line);
}

.eiq-investigation-brief > article:last-child {
  border-right: 0;
}

.eiq-investigation-workbench span,
.eiq-investigation-workbench dt {
  color: var(--eiq-soft-teal) !important;
}

.eiq-investigation-brief span,
.eiq-analyst-ribbon span,
.eiq-start-investigation span,
.eiq-investigation-report span {
  display: block;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .16em;
  text-transform: uppercase;
}

.eiq-investigation-brief strong {
  display: block;
  margin-top: 10px;
  color: #f4f8f8;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.28;
}

.eiq-investigation-brief article strong {
  font-size: 14px;
}

.eiq-investigation-brief p,
.eiq-start-investigation p,
.eiq-investigation-report p {
  margin: 8px 0 0;
  color: rgba(244,248,248,.66);
  font-size: 12px;
  line-height: 1.45;
}

.eiq-analyst-ribbon {
  display: grid;
  grid-template-columns: 280px minmax(0,1fr);
  margin-top: 14px;
  border: 1px solid var(--eiq-soft-line);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(3,8,10,.62);
}

.eiq-analyst-ribbon > div {
  padding: 17px 18px;
  border-right: 1px solid var(--eiq-soft-line);
}

.eiq-analyst-ribbon > div strong {
  display: block;
  margin-top: 8px;
  color: #f4f8f8;
  font-size: 22px;
}

.eiq-analyst-ribbon dl {
  display: grid;
  grid-template-columns: repeat(7, minmax(0,1fr));
  margin: 0;
}

.eiq-analyst-ribbon dl div {
  padding: 17px 14px;
  border-right: 1px solid rgba(115,200,184,.10);
}

.eiq-analyst-ribbon dl div:last-child {
  border-right: 0;
}

.eiq-analyst-ribbon dt {
  font-size: 9px;
  font-weight: 900;
  letter-spacing: .14em;
  text-transform: uppercase;
}

.eiq-analyst-ribbon dd {
  margin: 8px 0 0;
  color: #f4f8f8;
  font-size: 13px;
  font-weight: 800;
}

.eiq-start-investigation {
  display: grid;
  grid-template-columns: minmax(0,1fr) auto;
  align-items: center;
  gap: 20px;
  margin-top: 14px;
  padding: 16px 18px;
  border: 1px solid var(--eiq-soft-line);
  border-radius: 10px;
  background: rgba(3,8,10,.58);
}

.eiq-start-investigation strong {
  display: block;
  margin-top: 8px;
  color: #f4f8f8;
  font-size: 16px;
}

.eiq-start-investigation button {
  height: 40px;
  padding: 0 18px;
  border: 1px solid rgba(115,200,184,.28);
  border-radius: 999px;
  background: var(--eiq-soft-fill);
  color: var(--eiq-soft-teal);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.eiq-investigation-table table {
  min-width: 1500px !important;
  table-layout: fixed !important;
}

.eiq-investigation-table th:nth-child(1), .eiq-investigation-table td:nth-child(1) { width: 34px !important; }
.eiq-investigation-table th:nth-child(2), .eiq-investigation-table td:nth-child(2) { width: 92px !important; }
.eiq-investigation-table th:nth-child(3), .eiq-investigation-table td:nth-child(3) { width: 68px !important; }
.eiq-investigation-table th:nth-child(4), .eiq-investigation-table td:nth-child(4) { width: 70px !important; }
.eiq-investigation-table th:nth-child(5), .eiq-investigation-table td:nth-child(5) { width: 72px !important; }
.eiq-investigation-table th:nth-child(6), .eiq-investigation-table td:nth-child(6) { width: 76px !important; }
.eiq-investigation-table th:nth-child(7), .eiq-investigation-table td:nth-child(7) { width: 48px !important; }
.eiq-investigation-table th:nth-child(8), .eiq-investigation-table td:nth-child(8) { width: 62px !important; }
.eiq-investigation-table th:nth-child(9), .eiq-investigation-table td:nth-child(9) { width: 90px !important; }
.eiq-investigation-table th:nth-child(10), .eiq-investigation-table td:nth-child(10) { width: 64px !important; }
.eiq-investigation-table th:nth-child(11), .eiq-investigation-table td:nth-child(11) { width: 54px !important; }
.eiq-investigation-table th:nth-child(12), .eiq-investigation-table td:nth-child(12) { width: 70px !important; }
.eiq-investigation-table th:nth-child(13), .eiq-investigation-table td:nth-child(13) { width: 76px !important; }
.eiq-investigation-table th:nth-child(14), .eiq-investigation-table td:nth-child(14) { width: 86px !important; }
.eiq-investigation-table th:nth-child(15), .eiq-investigation-table td:nth-child(15) { width: 74px !important; }
.eiq-investigation-table th:nth-child(16), .eiq-investigation-table td:nth-child(16) { width: 70px !important; }
.eiq-investigation-table th:nth-child(17), .eiq-investigation-table td:nth-child(17) { width: 104px !important; }
.eiq-investigation-table th:nth-child(18), .eiq-investigation-table td:nth-child(18) { width: 74px !important; }
.eiq-investigation-table th:nth-child(19), .eiq-investigation-table td:nth-child(19) { width: 270px !important; }

.eiq-investigation-table td:nth-child(19) {
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.eiq-investigation-report {
  padding: 18px !important;
  border-left: 3px solid rgba(115,200,184,.68) !important;
  background: rgba(3,8,10,.72) !important;
}

.eiq-investigation-report header {
  display: grid;
  grid-template-columns: minmax(0,1fr) 150px;
  align-items: start;
  gap: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(115,200,184,.12);
}

.eiq-investigation-report header strong {
  display: block;
  margin-top: 7px;
  color: #f4f8f8;
  font-size: 18px;
}

.eiq-investigation-report header aside {
  text-align: right;
}

.eiq-investigation-report header b {
  display: block;
  color: var(--eiq-soft-teal);
  font-size: 22px;
  letter-spacing: .04em;
}

.eiq-investigation-report header em {
  display: block;
  margin-top: 3px;
  color: rgba(244,248,248,.6);
  font-size: 10px;
  font-style: normal;
  font-weight: 900;
  text-transform: uppercase;
}

.eiq-investigation-grid {
  display: grid;
  grid-template-columns: 1fr 1fr .9fr;
  gap: 12px;
  margin-top: 14px;
}

.eiq-investigation-grid article,
.eiq-investigation-record {
  padding: 15px;
  border: 1px solid rgba(115,200,184,.12);
  background: rgba(255,255,255,.018);
}

.eiq-investigation-grid strong {
  display: block;
  margin-top: 10px;
  color: #f4f8f8;
  font-size: 15px;
}

.eiq-investigation-grid ul {
  display: grid;
  gap: 8px;
  margin: 12px 0 0;
  padding-left: 16px;
  color: rgba(244,248,248,.82);
  font-size: 12px;
}

.eiq-investigation-metrics {
  display: grid;
  grid-template-columns: repeat(6, minmax(0,1fr));
  gap: 10px;
  margin-top: 12px;
}

.eiq-investigation-metrics article {
  min-height: 78px;
  padding: 12px;
  border: 1px solid rgba(115,200,184,.12);
  background: rgba(255,255,255,.018);
}

.eiq-investigation-metrics strong {
  display: block;
  margin-top: 8px;
  color: #f4f8f8;
  font-size: 15px;
}

.eiq-investigation-metrics em {
  display: block;
  margin-top: 3px;
  color: rgba(244,248,248,.58);
  font-size: 10px;
  font-style: normal;
  font-weight: 900;
  text-transform: uppercase;
}

.eiq-investigation-record {
  margin-top: 12px;
}

.eiq-investigation-record dl {
  display: grid;
  grid-template-columns: repeat(12, minmax(0,1fr));
  gap: 10px;
  margin: 12px 0 0;
}

.eiq-investigation-record dt {
  font-size: 9px;
  font-weight: 900;
  text-transform: uppercase;
}

.eiq-investigation-record dd {
  margin: 4px 0 0;
  color: #f4f8f8;
  font-size: 12px;
  font-weight: 800;
}

.eiq-investigation-report footer {
  display: flex;
  gap: 10px;
  justify-content: flex-start;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(115,200,184,.12);
}

.eiq-investigation-report footer button {
  height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(115,200,184,.22);
  border-radius: 999px;
  background: rgba(115,200,184,.045);
  color: var(--eiq-soft-teal);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

@media (max-width: 1350px) {
  .eiq-investigation-brief,
  .eiq-analyst-ribbon,
  .eiq-start-investigation,
  .eiq-investigation-grid {
    grid-template-columns: 1fr;
  }

  .eiq-analyst-ribbon dl,
  .eiq-investigation-metrics,
  .eiq-investigation-record dl {
    grid-template-columns: repeat(2, minmax(0,1fr));
  }
}
'''

existing = css.read_text(encoding="utf-8")
if "EDGEIQ FORM DESK — INVESTIGATION WORKBENCH V6" not in existing:
    existing += style
css.write_text(existing, encoding="utf-8")

print("[EDGEIQ] Investigation Workbench V6 applied")
print(f"[EDGEIQ] TSX checkpoint: {tsx_backup}")
print(f"[EDGEIQ] CSS checkpoint: {css_backup}")
