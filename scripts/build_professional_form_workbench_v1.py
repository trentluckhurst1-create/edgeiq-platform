from pathlib import Path

path = Path("src/edgeiq-os/race/RaceFileV3.tsx")
backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_PRO_FORM_WORKBENCH_20260709.tsx")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

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

function Metric({ label, value }: { label: string; value: any }) {
  return (
    <article className="eiq-workbench-metric">
      <span>{label}</span>
      <strong>{clean(value)}</strong>
    </article>
  );
}

function RunIntelligenceReport({ run }: { run: any }) {
  const form = run.professionalForm ?? {};
  const official = form.official ?? {};
  const evidence = form.evidence ?? {};
  const assignment = form.assignment ?? {};

  return (
    <tr className="eiq-form-report-row">
      <td colSpan={16}>
        <section className="eiq-run-report">
          <div className="eiq-run-report__grid">
            <article>
              <span>Race Record</span>
              <strong>{clean(official.track)} · {clean(official.distance)} · {clean(official.raceClass)}</strong>
              <p>{clean(official.date)} · {clean(official.condition)} · Rail {clean(official.rail)}</p>
              <dl>
                <div><dt>Barrier</dt><dd>{clean(official.barrier)}</dd></div>
                <div><dt>Weight</dt><dd>{clean(official.weight)}</dd></div>
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
                <div><dt>Run Rating™</dt><dd>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)}</dd></div>
                <div><dt>Race Strength™</dt><dd>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</dd></div>
                <div><dt>Pressure</dt><dd>{clean(evidence.pressure)}</dd></div>
                <div><dt>Tempo</dt><dd>{clean(evidence.tempo)}</dd></div>
                <div><dt>RaceFlow™</dt><dd>{clean(evidence.raceFlow)}</dd></div>
                <div><dt>RunnerDNA™</dt><dd>{clean(evidence.runnerDNA)}</dd></div>
              </dl>
            </article>

            <article>
              <span>Today's Fit</span>
              <strong>{score(run)}% · {verdict(run)}</strong>
              <p>{clean(assignment.assessment)}</p>
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
            <th>Run Rating™</th>
            <th>Race Strength™</th>
            <th>Pressure</th>
            <th>Tempo</th>
            <th>Assignment</th>
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
                <tr
                  key={key}
                  className={isOpen ? "is-open" : ""}
                  onClick={() => setOpenKey(isOpen ? null : key)}
                >
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
                  <td>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)}</td>
                  <td>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</td>
                  <td>{clean(evidence.pressure)}</td>
                  <td>{clean(evidence.tempo)}</td>
                  <td><b>{score(run)}%</b><em>{verdict(run)}</em></td>
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
    <section className="eiq-form-workbench">
      <header className="eiq-form-workbench__header">
        <div>
          <span>EDGEIQ Form Desk</span>
          <strong>{clean(file.raceBook.official.meeting)} R{clean(file.raceBook.official.raceNumber)}</strong>
          <p>
            {clean(file.raceBook.official.raceName)} · {clean(file.raceBook.official.distance)} · {clean(file.raceBook.official.raceClass)} · {clean(file.raceBook.official.trackCondition)} · {clean(file.raceBook.official.rail)}
          </p>
        </div>
        <aside>
          <span>Today’s Assignment</span>
          <strong>{clean(file.raceBook.intelligence.raceFlow)} · {clean(file.raceBook.intelligence.pressure)}</strong>
          <p>{clean(file.raceBook.intelligence.tempo)} tempo · {clean(file.raceBook.intelligence.trackSignature)}</p>
        </aside>
      </header>

      {primary ? (
        <>
          <section className="eiq-horse-workbench-header">
            <div>
              <span>Runner Workbench</span>
              <strong>{clean(primary.official.runner)}</strong>
              <p>{clean(primary.assessment)}</p>
            </div>

            <div className="eiq-horse-workbench-metrics">
              <Metric label="Trainer" value={primary.official.trainer} />
              <Metric label="Jockey" value={primary.official.jockey} />
              <Metric label="Barrier" value={primary.official.barrier} />
              <Metric label="Weight" value={primary.official.weight} />
              <Metric label="Market" value={primary.official.market} />
              <Metric label="RunnerDNA™" value={primary.runnerDNA} />
            </div>
          </section>

          <section className="eiq-analyst-summary">
            <article>
              <span>Analyst Summary</span>
              <strong>{bestRun ? `${score(bestRun)}% assignment match from ${clean(bestRun.professionalForm?.official?.track)}` : "Evidence still building"}</strong>
              <p>{bestRun ? narrative(bestRun) : "No historical runs available for this runner."}</p>
            </article>

            <article>
              <span>Primary Historical Evidence</span>
              <strong>{bestRun ? `${clean(bestRun.professionalForm?.official?.date)} · ${clean(bestRun.professionalForm?.official?.distance)} · ${clean(bestRun.professionalForm?.official?.raceClass)}` : "—"}</strong>
              <p>{bestRun ? verdict(bestRun) : "No primary evidence selected."}</p>
            </article>

            <article>
              <span>Operational Notes</span>
              <strong>Start with evidence, then investigate</strong>
              <p>Open a run row to inspect the official record, EDGEIQ evidence, today’s fit and historical-race actions without leaving the desk.</p>
            </article>
          </section>

          <section className="eiq-form-toolbar">
            <div>
              <span>Professional Historical Form</span>
              <strong>Official form, EDGEIQ evidence, assignment fit</strong>
            </div>

            <nav>
              <button type="button" className={mode === "historical" ? "is-active" : ""} onClick={() => setMode("historical")}>Historical</button>
              <button type="button" className={mode === "evidence" ? "is-active" : ""} onClick={() => setMode("evidence")}>Evidence</button>
              <button type="button" className={mode === "compare" ? "is-active" : ""} onClick={() => setMode("compare")}>Compare</button>
              <button type="button">Columns</button>
              <button type="button">Filters</button>
              <button type="button">Search</button>
              <button type="button">Export</button>
            </nav>
          </section>

          {mode === "compare" ? (
            <CompareWorkspace />
          ) : (
            <ProfessionalFormTable runs={displayedRuns} />
          )}
        </>
      ) : null}
    </section>
  );
}
'''

path.write_text(content, encoding="utf-8")
print("[EDGEIQ] RaceFileV3 upgraded to Professional Form Workbench")
print(f"[EDGEIQ] checkpoint: {backup}")
